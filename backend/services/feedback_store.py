"""
隐式反馈存储与聚合

设计依据:
  - Hu, Koren & Volinsky (2008) "Collaborative Filtering for Implicit Feedback
    Datasets": 隐式反馈没有「评分」，只有「置信度」。行为强度越高，
    我们对该偏好的置信度越高。这里用 ACTION_WEIGHTS 表达置信度。
  - Koren (2009) "Collaborative Filtering with Temporal Dynamics": 兴趣会漂移，
    旧行为必须衰减。这里用 exp(-λΔt)，半衰期默认 14 天。

存储: 追加写 JSONL（~/.life-workbench/feedback.jsonl），
      单用户场景下无需数据库，且天然保留原始事件流便于日后重算。
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

TZ_CHINA = timezone(timedelta(hours=8))

# ============================================================
# 行为权重（正负信号）
# ============================================================
ACTION_WEIGHTS: dict[str, float] = {
    "impression":   0.0,    # 仅曝光，不表态（保留事件用于日后算 CTR）
    "click":        0.10,   # 点开详情
    "dwell":        0.20,   # 有效停留（由 dwell_ms 触发，见 MIN_DWELL_MS）
    "open_link":    0.30,   # 跳转原文——最强正信号
    "like":         0.40,   # 显式点赞
    "not_interested": -0.50,  # 显式负反馈
}

# 停留多久才算「有效阅读」，低于此值视为误点
MIN_DWELL_MS = 3000
# 单次事件的停留加成上限（防止挂着页面刷权重）
MAX_DWELL_BONUS = 0.20
# 达到加成上限所需的停留时长
DWELL_SATURATE_MS = 60_000

# 时间衰减：半衰期 14 天
HALF_LIFE_DAYS = 14.0
DECAY_LAMBDA = math.log(2) / HALF_LIFE_DAYS

# 聚合产出的关键词上限与最低权重门槛
MAX_IMPLICIT_TOPICS = 40
MIN_ABS_WEIGHT = 0.05
# 单个关键词的权重钳制范围（避免隐式信号盖过显式画像）
WEIGHT_CLAMP = 1.0

# 无意义的通用标签，不纳入兴趣建模
STOPWORD_TAGS = {
    "news", "all", "综合", "资讯", "新闻", "文章", "其他", "未分类",
}

_write_lock = threading.Lock()

# 聚合结果缓存：每次打分都全量重算 JSONL 会拖慢列表接口
_AGG_TTL_SECONDS = 60
_agg_cache: dict[str, float] | None = None
_agg_cache_at: float = 0.0


def invalidate_cache() -> None:
    """使隐式画像缓存失效（写入新事件后调用）"""
    global _agg_cache, _agg_cache_at
    _agg_cache = None
    _agg_cache_at = 0.0


def feedback_path() -> Path:
    """反馈事件文件路径（可用环境变量覆盖，便于测试）"""
    base = os.environ.get("LIFE_WORKBENCH_HOME")
    root = Path(base) if base else Path.home() / ".life-workbench"
    return root / "feedback.jsonl"


# ============================================================
# 写入
# ============================================================

def record_event(
    article_id: str,
    action: str,
    dwell_ms: int = 0,
    tags: list[str] | None = None,
    category: str = "",
    title: str = "",
) -> dict:
    """追加一条反馈事件。

    Returns:
        实际落盘的事件 dict
    """
    event = {
        "article_id": str(article_id),
        "action": action,
        "dwell_ms": max(0, int(dwell_ms or 0)),
        "tags": _normalize_tags(tags),
        "category": (category or "").strip().lower(),
        "title": (title or "")[:200],
        "ts": datetime.now(TZ_CHINA).isoformat(timespec="seconds"),
    }

    path = feedback_path()
    try:
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as e:
        # 埋点失败绝不能影响主链路
        log.warning(f"反馈事件写入失败: {e}")

    invalidate_cache()
    return event


def _normalize_tags(tags: list[str] | None) -> list[str]:
    """标签归一化：小写、去空白、去停用词、限长去重"""
    if not tags:
        return []
    out: list[str] = []
    for t in tags:
        if not isinstance(t, str):
            continue
        tag = t.strip().lower()
        if not tag or len(tag) > 20 or tag in STOPWORD_TAGS:
            continue
        if tag not in out:
            out.append(tag)
        if len(out) >= 10:
            break
    return out


# ============================================================
# 读取与聚合
# ============================================================

def load_events(limit: int = 5000) -> list[dict]:
    """读取最近 limit 条事件（文件不存在时返回空）"""
    path = feedback_path()
    if not path.exists():
        return []
    events: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # 跳过损坏行，不中断
    except OSError as e:
        log.warning(f"反馈事件读取失败: {e}")
        return []
    return events[-limit:]


def _event_weight(event: dict) -> float:
    """单条事件的原始权重（未衰减）"""
    action = event.get("action", "")
    weight = ACTION_WEIGHTS.get(action, 0.0)

    # 停留时长加成：仅对正向行为生效，且需超过有效阅读门槛
    dwell = event.get("dwell_ms", 0) or 0
    if weight > 0 and dwell >= MIN_DWELL_MS:
        ratio = min(dwell / DWELL_SATURATE_MS, 1.0)
        weight += MAX_DWELL_BONUS * ratio

    return weight


def _decay(ts_str: str, now: datetime) -> float:
    """时间衰减因子 exp(-λΔt)，Δt 单位为天"""
    try:
        ts = datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return 0.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=TZ_CHINA)
    days = (now - ts).total_seconds() / 86400
    if days < 0:
        days = 0.0
    return math.exp(-DECAY_LAMBDA * days)


def aggregate_implicit_topics(events: list[dict] | None = None) -> dict[str, float]:
    """把行为事件流聚合成 {关键词: 权重} 的隐式兴趣画像。

    weight(kw) = Σ_events  action_weight × exp(-λ·Δt)

    正权重 = 感兴趣，负权重 = 反感（来自 not_interested）。
    结果按绝对值排序取 Top-N，并钳制到 [-1, 1]。
    """
    if events is None:
        events = load_events()
    if not events:
        return {}

    now = datetime.now(TZ_CHINA)
    scores: dict[str, float] = {}

    for ev in events:
        base = _event_weight(ev)
        if base == 0.0:
            continue
        decay = _decay(ev.get("ts", ""), now)
        if decay <= 0.001:
            continue  # 太久远，忽略
        contribution = base * decay

        # 标签与分类都作为兴趣载体；分类信号弱一些（更宽泛）
        for tag in ev.get("tags", []) or []:
            scores[tag] = scores.get(tag, 0.0) + contribution
        category = ev.get("category", "")
        if category and category not in STOPWORD_TAGS:
            scores[category] = scores.get(category, 0.0) + contribution * 0.5

    # 过滤微弱信号 + 钳制 + 取 Top-N
    filtered = {
        k: max(-WEIGHT_CLAMP, min(WEIGHT_CLAMP, round(v, 4)))
        for k, v in scores.items()
        if abs(v) >= MIN_ABS_WEIGHT
    }
    top = sorted(filtered.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return dict(top[:MAX_IMPLICIT_TOPICS])


def get_implicit_topics() -> dict[str, float]:
    """带 TTL 缓存的隐式画像读取（推荐引擎打分链路使用）。

    列表接口每次请求都会构建用户向量，若每次都全量读 JSONL 并重算，
    在事件积累后会成为明显开销。这里用 60s 缓存兜住热路径。
    """
    global _agg_cache, _agg_cache_at
    import time as _time

    now = _time.time()
    if _agg_cache is not None and (now - _agg_cache_at) < _AGG_TTL_SECONDS:
        return _agg_cache

    try:
        _agg_cache = aggregate_implicit_topics()
    except Exception as e:
        log.warning(f"隐式画像聚合失败: {e}")
        _agg_cache = {}
    _agg_cache_at = now
    return _agg_cache


def stats() -> dict:
    """反馈数据概览（供前端/调试展示）"""
    events = load_events()
    by_action: dict[str, int] = {}
    for ev in events:
        a = ev.get("action", "unknown")
        by_action[a] = by_action.get(a, 0) + 1

    topics = aggregate_implicit_topics(events)
    positive = {k: v for k, v in topics.items() if v > 0}
    negative = {k: v for k, v in topics.items() if v < 0}

    return {
        "total_events": len(events),
        "by_action": by_action,
        "half_life_days": HALF_LIFE_DAYS,
        "implicit_topics": topics,
        "positive_count": len(positive),
        "negative_count": len(negative),
        "top_positive": sorted(positive.items(), key=lambda kv: -kv[1])[:10],
        "top_negative": sorted(negative.items(), key=lambda kv: kv[1])[:10],
    }
