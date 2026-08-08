"""
需求中心交互 — 隐含上下文信封 (Context Envelope)

每次用户表达周边需求（喝、吃、玩、缺水…）时，系统自动携带的隐含输入：
  - time_slot : 当前时段（早餐/午餐/下午茶/晚餐/宵夜/深夜/其他）
  - location  : 用户精确坐标（WGS-84）+ 地名
  - user_state: 用户当前状态（饿/渴/缺水/当日含糖过高），由前端轻量勾选（A）
               或 LLM 推断（C，默认关）写入 state.jsonl
  - prefs     : 来自推荐画像的轻量偏好（口味/安静偏好等）

状态持久化：
  - 与 feedback 平级，存于 ~/.life-workbench/state.jsonl（可用 LIFE_WORKBENCH_HOME 覆盖）
  - 每日首次访问自动跨天清零（用户状态是当日内短期生理/饮食状态，不应跨天累积）

设计原则：
  - 零 token：A 路径纯本地读写，不涉及任何 LLM 调用；
  - 容错：任何读取失败都降级为空状态，绝不阻塞主链路。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

TZ_CHINA = timezone(timedelta(hours=8))

_write_lock = threading.Lock()

# 用户状态可选值（前端勾选条使用）
STATE_KEYS = {
    "hungry": "饿",
    "thirsty": "渴",
    "lacking_water": "缺水",
    "sugar_high": "当日含糖过高",
    "tired": "疲惫",
    "want_explore": "想探索",
}

# 反向：中文标签 -> key（供 C 路径 LLM 输出对齐）
STATE_LABEL_TO_KEY = {v: k for k, v in STATE_KEYS.items()}


def state_path() -> Path:
    """用户短期状态文件路径（与 feedback.jsonl 平级）"""
    base = os.environ.get("LIFE_WORKBENCH_HOME")
    root = Path(base) if base else Path.home() / ".life-workbench"
    return root / "state.jsonl"


def _today_str() -> str:
    return datetime.now(TZ_CHINA).strftime("%Y-%m-%d")


def _load_state() -> dict:
    """读取最新一条当日状态；跨天则视为无状态。"""
    path = state_path()
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("date") == _today_str():
                return rec
            break  # 遇到非今日的旧记录即可停止（文件按时间追加）
    except OSError as e:
        log.warning("读取用户状态失败: %s", e)
    return {}


def _save_state(states: dict[str, bool]) -> None:
    """追加一条当日状态快照（不覆盖历史，便于日后按天分析）。"""
    rec = {
        "date": _today_str(),
        "ts": datetime.now(TZ_CHINA).isoformat(timespec="seconds"),
        "states": {k: bool(v) for k, v in states.items() if k in STATE_KEYS},
    }
    path = state_path()
    try:
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("写入用户状态失败: %s", e)


def get_states() -> dict[str, bool]:
    """当前生效的用户状态（仅当日）；返回 key->bool 字典。"""
    rec = _load_state()
    return rec.get("states", {}) or {}


def set_states(states: dict[str, bool]) -> dict[str, bool]:
    """更新用户状态并落盘（A 路径：前端勾选）。"""
    normalized = {k: bool(v) for k, v in states.items() if k in STATE_KEYS}
    _save_state(normalized)
    return normalized


def _time_slot(hour: int) -> str:
    """把小时映射为餐饮/活动时段标签。"""
    if 5 <= hour < 9:
        return "breakfast"
    if 9 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "lunch"
    if 14 <= hour < 17:
        return "afternoon_tea"
    if 17 <= hour < 21:
        return "dinner"
    if 21 <= hour < 24:
        return "supper"
    return "late_night"


TIME_SLOT_LABELS = {
    "breakfast": "早餐",
    "morning": "上午",
    "lunch": "午餐",
    "afternoon_tea": "下午茶",
    "dinner": "晚餐",
    "supper": "宵夜",
    "late_night": "深夜",
}


def build_context() -> dict:
    """打包本次需求的隐含上下文信封。

    供 need_resolver 与 API 层复用，保证每次检索都自动带上：
      时间 / 坐标 / 用户状态 / 轻量偏好。
    不抛异常；任何子项失败都降级为安全默认值。
    """
    from . import geolocation

    loc = geolocation.get_location()
    now = datetime.now(TZ_CHINA)
    hour = now.hour

    # 轻量偏好：从推荐画像取少量稳定字段（不触发全量重算）
    prefs: dict = {}
    try:
        from .recommendation import get_engine
        profile = get_engine().profile
        prefs = {
            "cuisines": list((profile.get("preferences", {}) or {}).get("cuisines", {}).keys()),
            "introvert_extrovert": (profile.get("social", {}) or {}).get("introvert_extrovert", 0.5),
        }
    except Exception as e:  # 画像未就绪绝不能阻塞
        log.debug("构建需求上下文时画像读取降级: %s", e)

    return {
        "time_slot": _time_slot(hour),
        "time_slot_label": TIME_SLOT_LABELS.get(_time_slot(hour), "其他"),
        "hour": hour,
        "is_weekend": now.weekday() >= 5,
        "location": {
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "city": loc.get("city", ""),
            "district": loc.get("district", ""),
            "source": loc.get("source", "config"),
        },
        "user_state": get_states(),
        "prefs": prefs,
    }


def active_state_labels(context: dict) -> list[str]:
    """从上下文信封中提取当前被勾选/推断的状态中文标签列表。"""
    states = context.get("user_state", {}) or {}
    return [STATE_KEYS[k] for k, v in states.items() if v]
