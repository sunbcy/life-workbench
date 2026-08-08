"""
到店记录存储与聚合 — 周边资源的用户自标注层

让用户对每一张周边资源卡片做轻量交互：
  - visited      : 去过（标记"来过"）
  - not_visited  : 明确没去过 / 不想去（区分于"尚未记录"）
  - experience   : 到店体验记录（好吃/不好吃 + 自由文本笔记）

系统据此在卡片上展示：
  - 是否来过 (visited)
  - 是否有好评收藏 (has_good_taste)
  - 自行盘定的喜爱程度 (love_score, [-1,1])

设计：
  - 与 feedback.jsonl（新闻隐式反馈）平级，独立存于 ~/.life-workbench/place_visits.jsonl，
    不污染新闻画像，也不污染用户状态 state.jsonl。
  - 追加写 JSONL + TTL 聚合缓存，复用 feedback_store 的成熟模式。
  - 任何读写失败都静默降级，绝不阻塞周边主链路。
  - 零 token：纯本地逻辑，不涉及 LLM。
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

TZ_CHINA = timezone(timedelta(hours=8))

# 允许的动作
ACTIONS = {"visited", "not_visited", "experience"}
# 体验口味
TASTE_GOOD = "good"
TASTE_BAD = "bad"

_write_lock = threading.Lock()

# 聚合缓存（列表接口每次请求都查，全量重算会拖慢）
_AGG_TTL_SECONDS = 60
_agg_cache: dict | None = None
_agg_cache_at: float = 0.0


def visits_path() -> Path:
    base = os.environ.get("LIFE_WORKBENCH_HOME")
    root = Path(base) if base else Path.home() / ".life-workbench"
    return root / "place_visits.jsonl"


# ============================================================
# 写入
# ============================================================

def record_visit(
    resource_id: str,
    action: str,
    resource_name: str = "",
    taste: str = "",
    note: str = "",
) -> dict:
    """追加一条到店记录事件。

    action: visited | not_visited | experience
    taste : good | bad（仅 action=experience 时有效）
    note  : 自由文本笔记（如"牛肉面好吃"、"服务差"）
    """
    if action not in ACTIONS:
        raise ValueError(f"未知的到店动作: {action}")

    event = {
        "resource_id": str(resource_id),
        "resource_name": (resource_name or "")[:80],
        "action": action,
        "taste": taste if action == "experience" and taste in (TASTE_GOOD, TASTE_BAD) else "",
        "note": (note or "")[:300],
        "ts": datetime.now(TZ_CHINA).isoformat(timespec="seconds"),
    }

    path = visits_path()
    try:
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("到店记录写入失败: %s", e)

    invalidate_cache()
    return event


def invalidate_cache() -> None:
    global _agg_cache, _agg_cache_at
    _agg_cache = None
    _agg_cache_at = 0.0


# ============================================================
# 读取与聚合
# ============================================================

def load_events(limit: int = 10000) -> list[dict]:
    path = visits_path()
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
                    continue
    except OSError as e:
        log.warning("到店记录读取失败: %s", e)
        return []
    return events[-limit:]


def _aggregate(events: list[dict] | None = None) -> dict[str, dict]:
    """把事件流聚合成 {resource_id: 卡片状态}。

    盘定规则（可解释、轻量）：
      visited=True         : 来过
      not_visited=True     : 明确没去过/不想去（压制喜爱度）
      experience(good)     : 好评收藏 +1
      experience(bad)      : 差评 -1
      love_score = clamp(0.5*visited - 0.2*not_visited
                         + 0.3*good_cnt - 0.4*bad_cnt, -1, 1)
    多次体验累加，星级映射：love_score>=0.5 -> ❤️喜爱；>0 -> 👍还行；
      <0 -> 👎不推荐；not_visited -> 🚫暂不考虑。
    """
    if events is None:
        events = load_events()
    out: dict[str, dict] = {}

    for ev in events:
        rid = str(ev.get("resource_id", ""))
        if not rid:
            continue
        s = out.setdefault(rid, {
            "visited": False,
            "visited_at": None,
            "not_visited": False,
            "good_cnt": 0,
            "bad_cnt": 0,
            "note_count": 0,
            "last_note": "",
            "last_taste": "",
        })
        action = ev.get("action", "")
        ts = ev.get("ts", "")
        if action == "visited":
            s["visited"] = True
            s["visited_at"] = ts
        elif action == "not_visited":
            s["not_visited"] = True
        elif action == "experience":
            s["note_count"] += 1
            s["last_note"] = ev.get("note", "") or s["last_note"]
            taste = ev.get("taste", "")
            s["last_taste"] = taste or s["last_taste"]
            if taste == TASTE_GOOD:
                s["good_cnt"] += 1
            elif taste == TASTE_BAD:
                s["bad_cnt"] += 1

    # 盘定喜爱度 + 派生展示字段
    for rid, s in out.items():
        score = (
            0.5 * (1 if s["visited"] else 0)
            - 0.2 * (1 if s["not_visited"] else 0)
            + 0.3 * s["good_cnt"]
            - 0.4 * s["bad_cnt"]
        )
        s["love_score"] = round(max(-1.0, min(1.0, score)), 3)
        s["has_good_taste"] = s["good_cnt"] > 0
        s["has_bad_taste"] = s["bad_cnt"] > 0
        # 展示等级
        if s["not_visited"] and s["love_score"] <= 0:
            s["love_level"] = "skip"          # 🚫 暂不考虑
        elif s["love_score"] >= 0.5:
            s["love_level"] = "love"          # ❤️ 喜爱
        elif s["love_score"] > 0:
            s["love_level"] = "like"          # 👍 还行
        elif s["love_score"] < 0:
            s["love_level"] = "dislike"       # 👎 不推荐
        else:
            s["love_level"] = "neutral"       # 仅标记来过，无评价
    return out


def get_summary(resource_ids: list[str] | None = None) -> dict[str, dict]:
    """批量查询卡片状态（带 TTL 缓存）。

    resource_ids 为空时返回全量聚合（调试用）。
    返回 {resource_id: {visited, visited_at, not_visited, has_good_taste,
            has_bad_taste, love_score, love_level, note_count, last_note, last_taste}}
    """
    global _agg_cache, _agg_cache_at
    import time as _time
    now = _time.time()
    if _agg_cache is not None and (now - _agg_cache_at) < _AGG_TTL_SECONDS:
        agg = _agg_cache
    else:
        try:
            agg = _aggregate()
        except Exception as e:
            log.warning("到店记录聚合失败: %s", e)
            agg = {}
        _agg_cache = agg
        _agg_cache_at = now

    if resource_ids is None:
        return agg
    want = {str(r) for r in resource_ids}
    return {rid: s for rid, s in agg.items() if rid in want}


def stats() -> dict:
    """到店记录概览（调试/展示）"""
    events = load_events()
    agg = _aggregate(events)
    visited = sum(1 for s in agg.values() if s["visited"])
    good = sum(1 for s in agg.values() if s["has_good_taste"])
    bad = sum(1 for s in agg.values() if s["has_bad_taste"])
    return {
        "total_events": len(events),
        "tracked_places": len(agg),
        "visited": visited,
        "good_tasted": good,
        "bad_tasted": bad,
    }
