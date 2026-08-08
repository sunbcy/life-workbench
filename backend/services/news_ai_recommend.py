"""
资讯中心 — 维度三：基于用户画像的「深度 AI 新闻推荐」

从社会/生活视角解析用户画像，推断其潜在诉求（关注领域、通勤、健康、省钱…），
再据此对新闻做深度排序，并为每条命中新闻生成「诉求标签 + 推荐理由」。

设计原则（与全站一致）：
  - 零 token 优先：本地启发式解析诉求 + 本地诉求匹配，功能始终可用；
  - LLM 增强：配置了 ai.api_key 时，对 top-K 候选调用一次 LLM 生成更自然、
    更具洞察力的推荐理由（深度），失败自动降级回本地理由，绝不阻塞。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)
TZ_CHINA = timezone(timedelta(hours=8))


class NewsAIRecommender:
    """基于画像诉求的新闻深度推荐器"""

    def __init__(self):
        self._profile: dict = {}

    # ------------------------------------------------------------
    # 1) 解析用户诉求（从画像反推「你可能需要什么」）
    # ------------------------------------------------------------
    def analyze_needs(self, profile: dict | None = None) -> list[dict]:
        """从用户画像解析潜在诉求。

        返回 [{topic, reason, weight, category}]，weight ∈ (0,1]，
        category 用于前端分组展示（关注/健康/通勤/省钱…）。
        """
        if profile is None:
            try:
                from services.recommendation import get_engine
                profile = get_engine().profile
            except Exception:
                profile = {}
        self._profile = profile or {}

        needs: list[dict] = []

        # 1) 显式关注话题（权重最高）
        for t in self._get(profile, "interests", "tracking_topics", []):
            kw = (t.get("keyword") or "").strip()
            if kw:
                needs.append({
                    "topic": kw, "weight": float(t.get("weight", 0.5)),
                    "category": "关注", "reason": f"你在主动追踪「{kw}」话题",
                })
        # 2) 技能 / 在学
        for s in self._get(profile, "interests", "skills", []):
            name = (s.get("name") or "").strip()
            if name:
                needs.append({
                    "topic": name, "weight": 0.5 + 0.1 * int(s.get("level", 3)),
                    "category": "技能", "reason": f"你具备/精进「{name}」技能，相关内容值得关注",
                })
        for g in self._get(profile, "interests", "learning_goals", []):
            topic = (g.get("topic") or "").strip()
            if topic:
                needs.append({
                    "topic": topic, "weight": 0.55,
                    "category": "学习", "reason": f"你的学习目标含「{topic}」",
                })
        # 3) 健康关注（隐性诉求：你可能关心健康类资讯）
        for c in self._get(profile, "health", "health_concerns", []):
            c = (c or "").strip()
            if c:
                needs.append({
                    "topic": c, "weight": 0.6,
                    "category": "健康", "reason": f"你的健康关注项含「{c}」",
                })
        # 4) 通勤诉求：有 home/work 坐标即推断「通勤族」诉求
        loc = self._get(profile, "location", "commute", {}) or {}
        if self._get(profile, "location", "home", {}) and self._get(profile, "location", "work", {}):
            needs.append({
                "topic": "通勤出行", "weight": 0.45,
                "category": "通勤", "reason": f"你有固定通勤（{loc.get('mode','交通')}约{loc.get('home_to_work_min','?')}分钟），交通/天气类新闻影响日常",
            })
        # 5) 省钱诉求：价格敏感或预算紧张
        sens = self._get(profile, "budget", "price_sensitivity", {}) or {}
        if any(v == "high" for v in sens.values()):
            needs.append({
                "topic": "省钱优惠", "weight": 0.4,
                "category": "省钱", "reason": "你对价格敏感，优惠/理财类资讯有实际价值",
            })
        # 去重保序（同 topic 取最高权重）
        seen: dict[str, dict] = {}
        for n in needs:
            key = n["topic"].lower()
            if key not in seen or n["weight"] > seen[key]["weight"]:
                seen[key] = n
        return sorted(seen.values(), key=lambda x: x["weight"], reverse=True)

    # ------------------------------------------------------------
    # 2) 深度推荐：对新闻按诉求匹配排序 + 生成理由
    # ------------------------------------------------------------
    def recommend(
        self, articles: list[dict], use_llm: bool = True, top_k: int = 12
    ) -> tuple[list[dict], list[dict]]:
        """对新闻做深度诉求推荐。

        Returns:
            (ranked_articles, needs)
          ranked_articles 每项附加：
            _needs      : 命中的诉求标签列表 ["AI", "通勤出行"]
            _need_reason: 本地生成的推荐理由（一句话）
            _ai_reason  : LLM 生成的深度理由（若可用，否则与本地相同）
            _need_score : 诉求匹配分 [0,1]
        """
        needs = self.analyze_needs(self._profile)
        if not needs:
            # 无画像：退化为按新鲜度，不强行推荐
            for a in articles:
                a = dict(a)
                a["_needs"], a["_need_reason"], a["_ai_reason"], a["_need_score"] = [], "", "", 0.0
            articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)
            return articles, needs

        need_index = [(n["topic"].lower(), n) for n in needs]

        scored: list[dict] = []
        for a in articles:
            a = dict(a)
            title = (a.get("title") or "").lower()
            summary = (a.get("summary") or "").lower()
            tags = [t.lower() for t in a.get("tags", [])]
            blob = f"{title} {summary} {' '.join(tags)}"

            hit_needs: list[str] = []
            local_reason_parts: list[str] = []
            best_w = 0.0
            for kw, n in need_index:
                if not kw:
                    continue
                if kw in blob:
                    if n["topic"] not in hit_needs:
                        hit_needs.append(n["topic"])
                    local_reason_parts.append(n["reason"])
                    best_w = max(best_w, n["weight"])
            # 诉求匹配分：命中数 × 最高权重，封顶 1.0；未命中给 0（不强行置顶）
            if hit_needs:
                raw = min(1.0, best_w * (0.6 + 0.2 * len(hit_needs)))
            else:
                raw = 0.0
            # 轻微新鲜度补偿：完全未命中诉求的，按时间自然流动（避免全沉底）
            fresh = self._freshness(a.get("published_at", ""))
            a["_need_score"] = round(raw, 3)
            a["_needs"] = hit_needs
            a["_need_reason"] = "；".join(local_reason_parts[:2])
            a["_ai_reason"] = a["_need_reason"]
            a["_fresh_bonus"] = 0.15 * fresh if raw == 0 else 0.0
            scored.append(a)

        # 排序：诉求分优先，同分新近优先
        scored.sort(key=lambda a: (a["_need_score"] + a.get("_fresh_bonus", 0), a.get("published_at", "")), reverse=True)

        # 3) LLM 增强：对 top-K 命中诉求的候选，生成更自然的深度理由
        if use_llm:
            self._enrich_with_llm(scored, needs, top_k)

        return scored, needs

    # ------------------------------------------------------------
    def _enrich_with_llm(self, scored: list[dict], needs: list[dict], top_k: int) -> None:
        """调用 LLM 为 top-K 候选生成深度推荐理由（失败静默降级）。"""
        try:
            from services.ai_mentor import ai_available, _call_llm_json
        except Exception:
            return
        if not ai_available():
            return

        # 仅取有诉求命中的前 top_k 篇，控 token
        candidates = [a for a in scored if a.get("_needs")][:top_k]
        if not candidates:
            return

        news_block = "\n".join(
            f"{i+1}. [id={a.get('id')}] 《{a.get('title','')}》"
            f" 摘要: { (a.get('summary','') or '')[:80] }"
            for i, a in enumerate(candidates)
        )
        needs_block = "\n".join(
            f"- 「{n['topic']}」({n['category']})：{n['reason']}" for n in needs[:12]
        )
        prompt = (
            "你是资讯助手的「深度推荐」模块。下面是某用户的画像诉求，以及一批候选新闻。\n"
            "请为每一条候选新闻判断：它最契合用户哪几个诉求（从给定诉求中选取），"
            "并用一句中文（≤40字）说明「为什么推荐给这位用户」——要基于诉求与新闻内容的关联，"
            "体现洞察，不要空话。\n\n"
            "用户诉求：\n" + needs_block + "\n\n"
            "候选新闻：\n" + news_block + "\n\n"
            "请只输出 JSON：\n"
            '{"items":[{"id":"<新闻id>","needs":["诉求1"],"reason":"一句话理由"}]}'
        )
        try:
            data = _call_llm_json(prompt, timeout=30)
            mapping = {str(it.get("id")): it for it in data.get("items", [])}
            for a in candidates:
                it = mapping.get(str(a.get("id")))
                if it and it.get("reason"):
                    a["_ai_reason"] = it["reason"]
                    if it.get("needs"):
                        # LLM 可能补充更精准的诉求标签
                        a["_needs"] = list(dict.fromkeys(list(it["needs"]) + list(a["_needs"])))
        except Exception as e:
            log.warning("资讯深度推荐 LLM 增强失败，沿用本地理由: %s", e)

    # ------------------------------------------------------------
    @staticmethod
    def _freshness(published: str) -> float:
        if not published:
            return 0.5
        try:
            pt = datetime.fromisoformat(published)
            if pt.tzinfo is None:
                pt = pt.replace(tzinfo=TZ_CHINA)
            hours = (datetime.now(TZ_CHINA) - pt).total_seconds() / 3600
            return max(0.05, 0.5 ** (hours / 48))  # 48h 半衰期
        except (ValueError, TypeError):
            return 0.5

    def _get(self, d: dict, *keys, default=None):
        # 兼容调用习惯：self._get(profile, "a", "b", []) 时，
        # 末位非字符串参数（[], {} 等）视作 default（避免 *keys 吞掉它）。
        if keys and not isinstance(keys[-1], str):
            default = keys[-1]
            keys = keys[:-1]
        cur = d
        if not isinstance(cur, dict):
            return default
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k)
            if cur is None:
                return default
        return cur
