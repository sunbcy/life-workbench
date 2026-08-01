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

        # 层级祖先泛化匹配: 用户标了某叶子节点 (如 Vue),
        # 内容虽未直接提及该叶子, 但命中其祖先路径词 (如 "前端开发"), 仍给分。
        # 规则: 精确度 > 泛化度, 故祖先命中分数低于精确 topic 命中,
        #       且离叶子越近的祖先权重越高 (depth 衰减)。
        ancestors = uv.get("ancestors", {})
        if ancestors:
            best_anc_score = 0.0
            best_anc_word = ""
            for leaf, ancestor_words in ancestors.items():
                # 自身叶词已在 tracking 精确匹配过, 这里跳过
                if leaf in text or any(leaf in t for t in tags):
                    continue
                # ancestor_words = [根 ... 父]; 从最近的父(末尾)向根遍历,
                # 越靠近叶子的祖先权重越高: 父 0.55 > 祖父 0.45 > ...
                for depth_from_leaf, idx in enumerate(
                        range(len(ancestor_words) - 1, -1, -1), start=1):
                    anc = ancestor_words[idx]
                    if anc in text or any(anc in t for t in tags):
                        anc_score = max(0.0, 0.55 - 0.1 * (depth_from_leaf - 1))
                        if anc_score > best_anc_score:
                            best_anc_score = anc_score
                            best_anc_word = anc
                        break  # 该叶子只取最近命中的祖先
            if best_anc_word and best_anc_score > max_topic_score:
                # 仅在未精确命中时作为补充信号
                if not matched_topic:
                    reasons.append(f"与你兴趣领域的「{best_anc_word}」方向相关")
                max_topic_score = max(max_topic_score, best_anc_score)

        # 技能匹配 (权重最高: 擅长 > 想了解)
        skills = uv.get("skills", {})
        skill_score = 0.0
        matched_skill = ""
        for skill_name, level_score in skills.items():
            if skill_name in text or any(skill_name in t for t in tags):
                if level_score > skill_score:
                    skill_score = level_score
                    matched_skill = skill_name
        if skill_score > 0.5:
            reasons.append(f"与你的擅长领域「{matched_skill}」相关")

        # 弱信号: 知道 / 想了解 / 在学 / 已体验 (权重由低到高, 均低于 skill 与 tracking)
        weak_bands = (
            ("know", "知道", "知道"),
            ("want", "想了解", "想了解"),
            ("learning", "在学", "正在学习"),
            ("tried", "已体验", "已体验过"),
        )
        weak_score = 0.0
        for key, label, verb in weak_bands:
            for kw, w in uv.get(key, {}).items():
                if kw in text or any(kw in t for t in tags):
                    if w > weak_score:
                        weak_score = w
                        reasons.append(f"你{verb}的「{kw}」相关内容")

        # 爱好匹配
        hobbies = uv.get("hobbies", [])
        hobby_hits = sum(1 for h in hobbies if h in text)
        hobby_score = min(hobby_hits / max(len(hobbies), 1), 1.0) * 0.7

        # 目标匹配
        goals = uv.get("goals", [])
        goal_hits = sum(1 for g in goals if g in text)
        goal_score = min(goal_hits / max(len(goals), 1), 1.0) * 0.8

        combined = max(max_topic_score, skill_score, weak_score, hobby_score, goal_score)
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

        # 层级祖先泛化匹配: 用户标了某健康叶子 (如 高血压),
        # 内容虽未直接提及该叶子, 但命中其祖先路径词 (如 心血管), 仍给分。
        ancestors = uv.get("ancestors", {})
        if ancestors:
            best_anc_score = 0.0
            best_anc_word = ""
            for leaf, ancestor_words in ancestors.items():
                if leaf in text:
                    continue
                for depth_from_leaf, idx in enumerate(
                        range(len(ancestor_words) - 1, -1, -1), start=1):
                    anc = ancestor_words[idx]
                    if anc in text:
                        anc_score = max(0.0, 0.5 - 0.1 * (depth_from_leaf - 1))
                        if anc_score > best_anc_score:
                            best_anc_score = anc_score
                            best_anc_word = anc
                        break
            if best_anc_word:
                reasons.append(f"与你健康关注的「{best_anc_word}」领域相关")
                return round(best_anc_score, 3), reasons

        return 0.0, []

    def _social_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """社交偏好匹配 (增强版)

        利用画像中的:
          - introvert_extrovert (0~1 内向/外向)
          - crowd_tolerance (low/medium/high)
          - max_crowd_level (1~10 可接受的拥挤上限)
          - peak_hour_avoidance (是否避开高峰)
          - preferred_activities (偏好的社交活动类型)
        与内容项的:
          - crowd_level (1~10 预估拥挤度, 可选)
          - peak_hour (是否高峰时段, 可选)
          - features / tags / text (关键词兜底)
          - category (周边分类, 如 entertainment/food)
        做精细化匹配, 不再只靠关键词二分。
        """
        text = iv.get("text", "")
        tags = iv.get("tags", [])
        features = iv.get("features", [])
        category = iv.get("category", "")
        all_text = f"{text} {' '.join(tags)} {' '.join(features)}"
        reasons = []

        ie = uv.get("introvert_extrovert", 0.5)
        crowd_tol = uv.get("crowd_tolerance", "medium")
        max_crowd = uv.get("max_crowd_level", 5)
        peak_avoid = uv.get("peak_avoidance", False)
        preferred = uv.get("preferred_activities", [])

        # 内容项的拥挤度 / 高峰标记 (由数据源提供, 缺省时回退关键词推断)
        item_crowd = iv.get("crowd_level")
        item_peak = iv.get("peak_hour")

        crowd_keywords = ["聚会", "派对", "音乐节", "夜市", "酒吧", "夜店", "演唱会", "嘉年华"]
        quiet_keywords = ["书店", "图书馆", "咖啡", "茶室", "展览", "画廊", "公园", "冥想"]
        is_crowded = item_peak or any(kw in all_text for kw in crowd_keywords)
        is_quiet = any(kw in all_text for kw in quiet_keywords)

        # 1) 偏好社交活动类型命中 → 强信号
        for act in preferred:
            if act and act in all_text:
                reasons.append(f"你喜欢的「{act}」活动")
                return 0.9, reasons

        # 2) 基于拥挤度数值的精细匹配 (若有结构化字段)
        if item_crowd is not None:
            if item_crowd <= max_crowd:
                base = 0.6
            else:
                # 超过可接受上限 → 按超出幅度衰减
                over = (item_crowd - max_crowd) / max(10 - max_crowd, 1)
                base = max(0.1, 0.5 - over * 0.4)
                if base < 0.3:
                    reasons.append("该地点可能过于拥挤")
                    return round(base, 3), reasons
            # 外向型偏好热闹, 内向型偏好安静
            if ie > 0.6 and is_crowded:
                base = min(0.9, base + 0.2)
                reasons.append("热闹的氛围适合你")
            elif ie < 0.4 and is_quiet:
                base = min(0.9, base + 0.2)
                reasons.append("安静的氛围适合你")
            elif ie < 0.4 and is_crowded:
                base = max(0.1, base - 0.3)
                reasons.append("该场所偏喧闹")
            return round(base, 3), reasons

        # 3) 关键词兜底 (无结构化拥挤度时)
        if ie < 0.4 and is_quiet:
            reasons.append("安静的氛围适合你")
            return 0.7, reasons
        elif ie > 0.6 and is_crowded:
            reasons.append("热闹的氛围适合你")
            return 0.7, reasons
        elif ie < 0.4 and is_crowded:
            return 0.1, []
        elif is_quiet or is_crowded:
            return 0.4, []

        return 0.0, []

    def _budget_match(self, uv: dict, iv: dict, item_type: str) -> tuple[float, list[str]]:
        """预算匹配 (增强版)

        - product: 价格敏感度品类 + 降价阈值 (原逻辑保留)
        - nearby:  餐饮/娱乐按画像月预算的价格带给分; 超过用户可承受上限则压分
        - news:    预算/省钱/理财类话题轻量加分
        """
        reasons = []
        sensitivity = uv.get("sensitivity", {})
        monthly = uv.get("monthly_budget", {})
        threshold = uv.get("price_drop_threshold", 15)

        if item_type == "product":
            min_price = iv.get("min_price", 0)
            category = iv.get("category", "")
            cat_sens = sensitivity.get(category, "medium")
            if cat_sens == "high" and min_price > 0:
                return 0.6, ["你对价格敏感，此商品多家比价中"]
            elif cat_sens == "medium":
                return 0.3, []
            return 0.0, []

        if item_type == "nearby":
            # 优先用结构化人均消费; 否则回退文本中的价格提示
            avg_price = iv.get("avg_price")
            if avg_price is None:
                import re
                m = re.search(r"人均[约]?(\d+)", iv.get("text", ""))
                avg_price = int(m.group(1)) if m else None
            # 只对餐饮/娱乐类用预算约束
            budget_cat = {
                "food": monthly.get("dining_out", 0),
                "entertainment": monthly.get("entertainment", 0),
            }.get(iv.get("category", ""), 0)
            if avg_price is None or budget_cat <= 0:
                return 0.0, []
            # 单次人均相对月预算的占比阈值: 餐饮<=8% / 娱乐<=15% 视为友好
            ratio = avg_price / budget_cat
            if iv.get("category") == "food":
                if ratio <= 0.08:
                    return 0.6, [f"人均¥{avg_price}，契合你的餐饮预算"]
                elif ratio <= 0.15:
                    return 0.35, []
                return 0.1, ["超出你的餐饮预算区间"]
            else:  # entertainment
                if ratio <= 0.15:
                    return 0.55, [f"人均¥{avg_price}，契合你的娱乐预算"]
                elif ratio <= 0.3:
                    return 0.3, []
                return 0.1, ["超出你的娱乐预算区间"]

        if item_type == "news":
            text = iv.get("text", "")
            budget_kw = ["省钱", "理财", "预算", "优惠", "折扣", "薅羊毛", "消费降级"]
            if any(kw in text for kw in budget_kw):
                return 0.4, ["与你关注的预算/省钱话题相关"]
            return 0.0, []

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
