"""
需求中心交互 — 需求解析器 (Need Resolver)

把用户的一句自然语言/语音/文字输入（或一次折叠点选）解析成一组
「物品标签 (item_tag)」，再由 item_tag 映射到多个 POI 召回源（分类 + 关键词）。

两条路径：
  A 起步（零 token）: 本地意图树 + 关键词词典。覆盖高频口语化表达
     - "水/喝水/渴"           -> water
     - "吃/饿/饭/午餐/晚餐"    -> food
     - "喝奶茶/咖啡"          -> drink(非纯水)
     - "逛/玩/探索/无聊"      -> explore
     - "买/超市/便利店"        -> market
     - "药店/医院/不舒服"      -> health
     等。解析为 item_tag 列表后交给 item_tag_to_queries 展开多召回源。
  C 演进（可选, 默认关）: 当 use_llm=True 且配置了 LLM key 时，
     把输入 + 上下文信封交给 LLM 做语义解析，输出结构化 item_tag 与理由。
     失败自动降级回 A 路径，绝不因 AI 不可用而阻塞。

item_tag -> 多召回源：每个物品标签展开成 {category, keyword} 组合，
  以「常见物品为导向」——例如 water 同时召回：
     - 超市(关键词: 水/饮用水/矿泉水)
     - 便利店(关键词: 水)
     - 餐饮(关键词: 饮品/饮料)  [大概率卖水的地点]
     - 供水站/水站(关键词: 桶装水)
  这样"水"标签就覆盖附近所有卖水、或大概率卖水的地点。

此模块纯函数居多、无 IO，便于测试与复用。
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

# ============================================================
# 物品标签 (item_tag) 定义
# ============================================================
ITEM_TAGS = {
    "water": "水",
    "drink": "饮品",
    "food": "食物",
    "snack": "零食",
    "explore": "探索",
    "market": "购物",
    "health": "健康医疗",
    "cafe": "咖啡",
    "rest": "休息",
}

# ============================================================
# A 路径：本地意图树 / 关键词词典
# ============================================================
# 每条约匹配规则: (匹配词列表, item_tag)
_INTENT_RULES: list[tuple[list[str], str]] = [
    (["水", "喝水", "渴", "矿泉水", "饮用水", "桶装水"], "water"),
    (["奶茶", "咖啡", "饮料", "果汁", "喝"], "drink"),
    (["咖啡馆", "咖啡店", "cafe", "星巴克", "瑞幸"], "cafe"),
    (["吃", "饭", "饿", "午餐", "晚餐", "早餐", "宵夜", "美食", "餐厅", "饭店", "食堂", "外卖"], "food"),
    (["零食", "小吃", "宵夜", "麻辣烫", "烧烤", "甜品", "蛋糕"], "snack"),
    (["逛", "玩", "探索", "无聊", "散步", "公园", "景点", "溜达"], "explore"),
    (["买", "购物", "超市", "便利店", "商场", "日用品", "东西"], "market"),
    (["药", "医院", "不舒服", "生病", "药店", "诊所", "急诊", "头疼", "发烧"], "health"),
    (["休息", "坐坐", "咖啡馆", "书店", "安静", "充电", "放松"], "rest"),
]

# 折叠点选按钮直接映射到 item_tag（前端多级点选用）
TAP_TAGS = {
    "喝": ["water", "drink"],
    "吃": ["food", "snack"],
    "玩": ["explore", "rest"],
    "买": ["market"],
    "医": ["health"],
}


def resolve_text(text: str, use_llm: bool = False, context: Optional[dict] = None) -> dict:
    """把用户输入解析为 item_tag 列表。

    Returns:
        {
          "mode": "local" | "llm-semantic" | "llm-fallback",
          "item_tags": [...],
          "raw": str,                       # 原始输入
          "reason": str,                    # 解析说明（便于前端展示"为什么")
        }
    """
    text = (text or "").strip()
    if not text:
        return {"mode": "local", "item_tags": [], "raw": "", "reason": "空输入"}

    # C 路径：LLM 语义解析（可选）
    if use_llm:
        try:
            return _resolve_by_llm(text, context or {})
        except Exception as e:
            log.warning("需求 LLM 解析失败，降级本地: %s", e)
            # 落回 A 路径

    return _resolve_local(text)


def _resolve_local(text: str) -> dict:
    """A 路径：本地意图树关键词匹配（零 token）。"""
    lowered = text.lower()
    matched: list[str] = []
    hit_words: list[str] = []

    for words, tag in _INTENT_RULES:
        for w in words:
            # 中文按包含匹配；英文词按小写包含匹配
            if w.lower() in lowered:
                if tag not in matched:
                    matched.append(tag)
                hit_words.append(w)
                break

    if not matched:
        # 兜底：把整句当作关键词直接搜（让用户原话进入召回）
        return {
            "mode": "local",
            "item_tags": [],
            "raw": text,
            "reason": "未命中预设意图，已按原文关键词检索",
            "fallback_keyword": text,
        }

    return {
        "mode": "local",
        "item_tags": matched,
        "raw": text,
        "reason": f"命中关键词 {hit_words} -> 物品标签 {matched}",
    }


def _resolve_by_llm(text: str, context: dict) -> dict:
    """C 路径：LLM 语义解析（消耗 token）。失败抛错交给上层降级。"""
    from services.ai_mentor import _call_llm_json

    ctx_desc = _context_hint(context)
    prompt = (
        "你是生活助手的「需求解析」模块。用户用口语表达了一个周边需求，"
        "请把它解析为一组“物品标签”(item_tag)，并给出简短理由。\n\n"
        "可用 item_tag 与含义：\n"
        + "\n".join(f"- {k}: {v}" for k, v in ITEM_TAGS.items())
        + "\n\n当前隐含上下文（仅供理解，不要输出）：\n"
        + ctx_desc
        + "\n\n用户输入：\n"
        + text
        + "\n\n请只输出 JSON："
        '{"item_tags": ["water"], "reason": "用户说渴了，需要水"}'
    )
    data = _call_llm_json(prompt, timeout=30)
    tags = [t for t in data.get("item_tags", []) if t in ITEM_TAGS]
    if not tags:
        raise ValueError("LLM 未返回有效 item_tag")
    return {
        "mode": "llm-semantic",
        "item_tags": tags,
        "raw": text,
        "reason": data.get("reason", "LLM 语义解析"),
    }


def _context_hint(context: dict) -> str:
    """把上下文信封压缩成给 LLM 的简短提示（仅 C 路径用）。"""
    if not context:
        return "（无）"
    parts = []
    parts.append(f"时段: {context.get('time_slot_label', '未知')}")
    loc = context.get("location", {})
    if loc.get("district"):
        parts.append(f"位置: {loc.get('city')}{loc.get('district')}")
    states = context.get("user_state", {})
    if states:
        from .need_context import active_state_labels
        labels = active_state_labels({"user_state": states})
        if labels:
            parts.append(f"用户状态: {', '.join(labels)}")
    return "；".join(parts)


# ============================================================
# item_tag -> 多召回源
# ============================================================
# 每个 item_tag 展开为多个 {category, keyword} 召回源。
# category 为空串 "" 表示不限定分类、仅用 keyword 全文召回。
# 以「常见物品为导向」：water 覆盖所有卖水/大概率卖水的地点。
_ITEM_TAG_QUERIES: dict[str, list[dict]] = {
    "water": [
        {"category": "market", "keyword": "水 矿泉水 饮用水"},
        {"category": "market", "keyword": "便利店 水"},
        {"category": "food", "keyword": "饮品 饮料 水"},
        {"category": "", "keyword": "水站 桶装水"},
    ],
    "drink": [
        {"category": "food", "keyword": "奶茶 饮料 果汁"},
        {"category": "market", "keyword": "饮品 饮料"},
        {"category": "", "keyword": "奶茶店 饮品店"},
    ],
    "cafe": [
        {"category": "food", "keyword": "咖啡 咖啡馆"},
        {"category": "", "keyword": "星巴克 瑞幸 咖啡店"},
    ],
    "food": [
        {"category": "food", "keyword": ""},
        {"category": "market", "keyword": "熟食 快餐 便当"},
        {"category": "", "keyword": "餐厅 饭店 食堂"},
    ],
    "snack": [
        {"category": "food", "keyword": "小吃 零食 甜品"},
        {"category": "market", "keyword": "零食 便利店"},
    ],
    "explore": [
        {"category": "entertainment", "keyword": ""},
        {"category": "service", "keyword": "景点 公园"},
        {"category": "", "keyword": "公园 展览 书店"},
    ],
    "rest": [
        {"category": "food", "keyword": "咖啡 茶 书店"},
        {"category": "entertainment", "keyword": "公园"},
        {"category": "", "keyword": "安静 咖啡馆 茶馆"},
    ],
    "market": [
        {"category": "market", "keyword": ""},
        {"category": "", "keyword": "超市 便利店 商场"},
    ],
    "health": [
        {"category": "hospital", "keyword": ""},
        {"category": "service", "keyword": "药店 药房"},
        {"category": "", "keyword": "药店 诊所"},
    ],
}


def item_tag_to_queries(tag: str) -> list[dict]:
    """把单个 item_tag 展开为多个 POI 召回源查询。"""
    return list(_ITEM_TAG_QUERIES.get(tag, [{"category": "", "keyword": ITEM_TAGS.get(tag, tag)}]))


def resolve_to_queries(
    text: str,
    use_llm: bool = False,
    context: Optional[dict] = None,
    tapped_tags: Optional[list[str]] = None,
) -> dict:
    """端到端：输入 -> 解析 -> 多召回源查询列表。

    Args:
        text: 用户文字/语音输入
        use_llm: 是否启用 C 路径 LLM 解析
        context: 上下文信封（来自 need_context.build_context）
        tapped_tags: 折叠多级点选直接给出的 item_tag（与 text 二选一/并用）
    Returns:
        {
          "mode": ...,
          "item_tags": [...],
          "reason": ...,
          "queries": [ {category, keyword}, ... ],   # 去重后的召回源
          "fallback_keyword": str|None,
        }
    """
    # 折叠点选优先并入
    tags: list[str] = list(tapped_tags or [])
    parsed = resolve_text(text, use_llm=use_llm, context=context)
    mode = parsed["mode"]
    reason = parsed.get("reason", "")
    fallback_keyword = parsed.get("fallback_keyword")

    for t in parsed.get("item_tags", []):
        if t not in tags:
            tags.append(t)

    queries: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for tag in tags:
        for q in item_tag_to_queries(tag):
            key = (q["category"], q["keyword"])
            if key not in seen:
                seen.add(key)
                queries.append(q)

    return {
        "mode": mode,
        "item_tags": tags,
        "reason": reason,
        "queries": queries,
        "fallback_keyword": fallback_keyword,
    }
