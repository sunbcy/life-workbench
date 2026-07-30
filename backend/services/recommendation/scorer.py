"""
评分器 — 计算用户向量与内容向量之间的综合匹配分数

公式:
    final_score = 0.45 × personal_relevance + 0.30 × trending_score + 0.25 × freshness_score

    personal_relevance = Σ(weight_dim × similarity_dim(user, item))
"""

import math
import re
from datetime import datetime, timezone, timedelta

TZ_CHINA = timezone(timedelta(hours=8))

# 维度权重
DIM_WEIGHTS = {
    "interests": 0.30, "location": 0.20, "schedule": 0.15,
    "preferences": 0.12, "health": 0.10, "social": 0.08, "budget": 0.05,
}

WEIGHT_PERSONAL = 0.45
WEIGHT_TRENDING = 0.30
WEIGHT_FRESHNESS = 0.25


class Scorer:
    """综合评分"""

    def score(self, user_vector: dict, item_vector: dict, item: dict, item_type: str = "news") -> dict:
        """
        计算综合推荐分数
        返回 {relevance_score, trending_score, freshness_score, composite_score, match_dimensions, match_reasons}
        """
        # 计算各维度相似度及匹配原因
        dim_scores = {}
        all_reasons = []

        # 兴趣维度 (权重最高)
        int_score, int_reasons = self._interests_match(user_vector.get("interests", {}), item_vector, item_type)
        dim_scores["interests"] = int_score
        all_reasons.extend(int_reasons)

        # 地理位置维度
        loc_score, loc_reasons = self._location_match(user_vector.get("location", {}), item_vector, item_type)
        dim_scores["location"] = loc_score
        all_reasons.extend(loc_reasons)

        # 日程维度
        sch_score, sch_reasons = self._schedule_match(user_vector.get("schedule", {}), item_vector, item_type)
        dim_scores["schedule"] = sch_score
        all_reasons.extend(sch_reasons)

        # 偏好维度
        pre_score, pre_reasons = self._preferences_match(user_vector.get("preferences", {}), item_vector, item_type)
        dim_scores["preferences"] = pre_score
        all_reasons.extend(pre_reasons)

        # 健康维度
        hlt_score, hlt_reasons = self._health_match(user_vector.get("health", {}), item_vector, item_type)
        dim_scores["health"] = hlt_score
        all_reasons.extend(hlt_reasons)

        # 社交维度
        soc_score, soc_reasons = self._social_match(user_vector.get("social", {}), item_vector, item_type)
        dim_scores["social"] = soc_score
        all_reasons.extend(soc_reasons)

        # 预算维度
        bud_score, bud_reasons = self._budget_match(user_vector.get("budget", {}), item_vector, item_type)
        dim_scores["budget"] = bud_score
        all_reasons.extend(bud_reasons)

        # 加权个人相关性
        personal_relevance = sum(
            DIM_WEIGHTS.get(dim, 0) * score
            for dim, score in dim_scores.items()
        )

        # 匹配维度（得分 > 0.3 的维度）
        match_dimensions = [
            dim for dim, score in dim_scores.items()
            if score > 0.3
        ]

        # 流行度评分
        trending_score = self._trending_score(item, item_type)

        # 新鲜度评分
        freshness_score = self._freshness_score(item, item_type)

        # 综合评分
        composite_score = (
            WEIGHT_PERSONAL * personal_relevance +
            WEIGHT_TRENDING * trending_score +
            WEIGHT_FRESHNESS * freshness_score
        )

        return {
            "relevance_score": round(personal_relevance, 3),
            "trending_score": round(trending_score, 3),
            "freshness_score": round(freshness_score, 3),
            "composite_score": round(composite_score, 3),
            "match_dimensions": match_dimensions,
            "match_reasons": all_reasons[:3],     # 最多3条原因
            "personalized": personal_relevance > 0.2,
        }

    # ============================================================
    # 各维度匹配函数
    # ============================================================

    def _interests_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """兴趣匹配 - 基于关键词和标签的 Jaccard + 加权匹配"""
        reasons = []
        text = iv.get("text", "")
        tags = iv.get("tags", [])
        category = iv.get("category", "")

        # 检查排除话题
        excluded = uv.get("excluded", set())
        for ex in excluded:
            if ex in text:
                return 0.0, []

        # 追踪话题匹配
        tracking = uv.get("tracking", {})
        max_topic_score = 0.0
        matched_topic = ""
        for keyword, weight in tracking.items():
            if keyword in text or any(keyword in t for t in tags):
                score = weight * 1.0
                if score > max_topic_score:
                    max_topic_score = score
                    matched_topic = keyword

        if matched_topic:
            reasons.append(f"与你关注的'{matched_topic}'话题相关")

        # 技能匹配
        skills = uv.get("skills", {})
        skill_score = 0.0
        for skill_name, level_score in skills.items():
            if skill_name in text:
                skill_score = max(skill_score, level_score)
        if skill_score > 0.5:
            reasons.append("与你的技能领域相关")

        # 爱好匹配
        hobbies = uv.get("hobbies", [])
        hobby_hits = sum(1 for h in hobbies if h in text)
        hobby_score = min(hobby_hits / max(len(hobbies), 1), 1.0) * 0.7

        # 目标匹配
        goals = uv.get("goals", [])
        goal_hits = sum(1 for g in goals if g in text)
        goal_score = min(goal_hits / max(len(goals), 1), 1.0) * 0.8

        combined = max(max_topic_score, skill_score, hobby_score, goal_score)
        return combined, reasons

    def _location_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """地理位置匹配"""
        reasons = []
        if item_type != "nearby":
            # 非周边内容，检查是否有地理相关性
            text = iv.get("text", "")
            # 简单检测深圳相关内容
            shenzhen_keywords = ["深圳", "南山", "福田", "宝安", "罗湖", "龙华", "龙岗", "蛇口"]
            for kw in shenzhen_keywords:
                if kw in text:
                    return 0.6, ["与你所在城市(深圳)相关"]
            return 0.0, []

        # 周边资源：距离归一化
        distance = iv.get("distance_km", 5.0)
        radius = uv.get("radius_default", 3.0)
        # 在半径内 → 高分；半径外指数衰减
        if distance <= radius:
            score = 1.0 - (distance / radius) * 0.5  # 0.5-1.0
        else:
            score = max(0, 0.5 * math.exp(-(distance - radius) / radius))

        if distance < 1.0:
            reasons.append(f"距离仅{int(distance * 1000)}m，步行可达")
        elif distance < radius:
            reasons.append(f"距离{distance:.1f}km，在{radius}km范围内")

        return score, reasons

    def _schedule_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """日程时间匹配"""
        reasons = []
        is_free = uv.get("currently_free", True)
        is_weekend = uv.get("is_weekend", False)
        hour = uv.get("hour", 12)

        # 根据空闲状态调整
        if item_type == "nearby":
            if is_free:
                score = 0.7
                if is_weekend:
                    score = 0.9
                    reasons.append("周末空闲，适合外出探索")
                else:
                    if 11 <= hour <= 13:
                        score = 0.85
                        reasons.append("午休时间，适合附近觅食")
                    elif 18 <= hour <= 22:
                        score = 0.8
                        reasons.append("晚间空闲，可以考虑周边活动")
            else:
                score = 0.2  # 忙碌时降低周边推荐
        else:
            # 资讯/比价：任何时间都可
            score = 0.5
            if is_free and is_weekend:
                score = 0.7
                reasons.append("周末闲暇，可以深度阅读")

        return score, reasons

    def _preferences_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """消费偏好匹配"""
        reasons = []
        text = iv.get("text", "")
        tags = iv.get("tags", [])
        category = iv.get("category", "")
        all_text = f"{text} {' '.join(tags)} {category}"

        score = 0.0

        if item_type == "product":
            # 优先品类匹配
            priority_cats = uv.get("priority_categories", [])
            for pc in priority_cats:
                if pc in category:
                    score = max(score, 0.8)
                    reasons.append(f"你优先关注的'{pc}'品类")
                    break

        elif item_type == "nearby" or item_type == "news":
            # 饮食口味匹配
            cuisines = uv.get("cuisines", {})
            for cuisine, weight in cuisines.items():
                if cuisine in all_text:
                    score = max(score, weight)
            if score > 0.7:
                reasons.append("符合你的口味偏好")

            # 娱乐类型匹配
            ent_types = uv.get("entertainment_types", {})
            for etype, weight in ent_types.items():
                if etype in all_text:
                    score = max(score, weight)
            if score > 0.7:
                reasons.append("符合你的娱乐偏好")

        return score, reasons

    def _health_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """健康数据匹配"""
        text = iv.get("text", "")
        reasons = []

        concerns = uv.get("concerns", [])
        hits = sum(1 for c in concerns if c in text)
        if hits > 0:
            score = min(hits * 0.4, 1.0)
            reasons.append("与你的健康关注项相关")
            return score, reasons

        # 运动相关
        exercises = uv.get("preferred_exercise", [])
        hits = sum(1 for e in exercises if e in text)
        if hits > 0:
            return 0.6, ["与你的运动偏好相关"]

        return 0.0, []

    def _social_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """社交偏好匹配"""
        text = iv.get("text", "")
        tags = iv.get("tags", [])
        features = iv.get("features", [])
        all_text = f"{text} {' '.join(tags)} {' '.join(features)}"
        reasons = []

        # 内向/外向影响推荐
        ie = uv.get("introvert_extrovert", 0.5)
        crowd_tol = uv.get("crowd_tolerance", "medium")

        # 检查是否是大型活动/热闹场所
        crowd_keywords = ["聚会", "派对", "音乐节", "夜市", "酒吧", "夜店", "演唱会"]
        quiet_keywords = ["书店", "图书馆", "咖啡", "茶室", "展览", "画廊", "公园"]

        is_crowded = any(kw in all_text for kw in crowd_keywords)
        is_quiet = any(kw in all_text for kw in quiet_keywords)

        if ie < 0.4 and is_quiet:  # 内向型 + 安静场所
            reasons.append("安静的氛围适合你")
            return 0.7, reasons
        elif ie > 0.6 and is_crowded:  # 外向型 + 热闹场所
            reasons.append("热闹的氛围适合你")
            return 0.7, reasons
        elif ie < 0.4 and is_crowded:
            return 0.1, []  # 内向型不推荐喧闹场所
        elif is_quiet or is_crowded:
            return 0.4, []

        return 0.0, []

    def _budget_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """预算匹配"""
        reasons = []
        if item_type != "product":
            return 0.0, []

        min_price = iv.get("min_price", 0)
        sensitivity = uv.get("sensitivity", {})
        category = iv.get("category", "")

        # 根据品类敏感度判断
        cat_sens = sensitivity.get(category, "medium")
        if cat_sens == "high" and min_price > 0:
            price_drop = uv.get("price_drop_threshold", 15)
            # 降价趋势商品给高分
            return 0.6, ["你对价格敏感，此商品多家比价中"]
        elif cat_sens == "medium":
            return 0.3, []

        return 0.0, []

    # ============================================================
    # 通用评分函数
    # ============================================================

    def _trending_score(self, item: dict, item_type: str) -> float:
        """计算流行度 / 趋势得分"""
        if item_type == "news":
            if item.get("trending"):
                return 1.0
            read_count = item.get("read_count", 0)
            if read_count > 30000:
                return 0.9
            elif read_count > 10000:
                return 0.7
            elif read_count > 5000:
                return 0.5
            return 0.3
        elif item_type == "product":
            trend = item.get("trend", "stable")
            trend_pct = abs(item.get("trend_pct", 0))
            if trend == "down" and trend_pct > 5:
                return 0.9  # 降价热门
            elif trend_pct > 10:
                return 0.7
            return 0.5
        elif item_type == "nearby":
            rating = item.get("rating", 0)
            reviews = item.get("review_count", 0)
            score = 0.3
            if rating >= 4.5:
                score += 0.3
            if reviews > 10000:
                score += 0.3
            elif reviews > 1000:
                score += 0.2
            return min(score, 1.0)
        return 0.5

    def _freshness_score(self, item: dict, item_type: str) -> float:
        """计算新鲜度得分 (指数衰减)"""
        published = item.get("published_at", "")
        if not published:
            return 0.5

        try:
            if isinstance(published, str):
                pub_time = datetime.fromisoformat(published)
            else:
                return 0.5

            now = datetime.now(TZ_CHINA)
            # 确保时区一致
            if pub_time.tzinfo is None:
                pub_time = pub_time.replace(tzinfo=TZ_CHINA)
            elif pub_time.tzinfo != TZ_CHINA:
                pub_time = pub_time.astimezone(TZ_CHINA)

            hours_ago = (now - pub_time).total_seconds() / 3600
            # 指数衰减，半衰期 24 小时
            score = math.exp(-0.029 * hours_ago)  # ln(2)/24 ≈ 0.029
            return max(0.05, score)
        except (ValueError, TypeError):
            return 0.5
