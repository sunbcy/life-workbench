"""
Profile 加载器 — 从本地 YAML 文件读取用户画像
"""

import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# 7 个维度的权重配置
DIMENSION_WEIGHTS = {
    "interests":    0.30,
    "location":     0.20,
    "schedule":     0.15,
    "preferences":  0.12,
    "health":       0.10,
    "social":       0.08,
    "budget":       0.05,
}

DIMENSION_LABELS = {
    "interests":    {"name": "兴趣与技能", "icon": "💡", "tier": "core"},
    "location":     {"name": "地理位置", "icon": "📍", "tier": "core"},
    "schedule":     {"name": "时间日程", "icon": "🕐", "tier": "important"},
    "preferences":  {"name": "消费偏好", "icon": "🛒", "tier": "important"},
    "health":       {"name": "健康数据", "icon": "❤️", "tier": "auxiliary"},
    "social":       {"name": "社交偏好", "icon": "👥", "tier": "auxiliary"},
    "budget":       {"name": "预算限制", "icon": "💰", "tier": "reference"},
}


class ProfileLoader:
    """加载和管理本地 profile 文件"""

    def __init__(self, profile_dir: str = "~/.life-workbench/profile"):
        self.profile_dir = Path(os.path.expanduser(profile_dir))
        self.profile: dict = {}
        self._loaded: set[str] = set()

    def load_all(self) -> dict:
        """加载所有 profile 文件"""
        for dim in DIMENSION_WEIGHTS:
            self._load_dimension(dim)
        return self.profile

    def _load_dimension(self, dim: str):
        """加载单个维度"""
        import yaml
        filepath = self.profile_dir / f"{dim}.yaml"
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.profile[dim] = yaml.safe_load(f) or {}
                self._loaded.add(dim)
                log.info(f"Profile loaded: {dim} ({DIMENSION_LABELS[dim]['name']})")
            except Exception as e:
                log.warning(f"Failed to load profile '{dim}': {e}")
                self.profile[dim] = {}
        else:
            log.debug(f"Profile file not found: {filepath} (will use empty defaults)")
            self.profile[dim] = {}
            self._loaded.add(dim)

    def summary(self) -> dict:
        """返回脱敏的画像摘要（不暴露原始数据）"""
        result = {
            "dimensions": [],
            "total_weight": 0.0,
            "activated_count": 0,
        }
        for dim, weight in DIMENSION_WEIGHTS.items():
            data = self.profile.get(dim, {})
            is_active = bool(data) and dim in self._loaded
            label = DIMENSION_LABELS[dim]

            dim_summary = {
                "key": dim,
                "name": label["name"],
                "icon": label["icon"],
                "tier": label["tier"],
                "weight": weight,
                "weight_pct": f"{weight * 100:.0f}%",
                "active": is_active,
                # 只暴露结构性的摘要，不暴露具体值
                "fields_count": self._count_fields(data),
                "highlights": self._extract_highlights(dim, data),
            }
            result["dimensions"].append(dim_summary)
            if is_active:
                result["activated_count"] += 1
                result["total_weight"] += weight

        return result

    def dimensions_status(self) -> list[dict]:
        """返回各维度权重和激活状态"""
        return [
            {
                "key": dim,
                "name": DIMENSION_LABELS[dim]["name"],
                "icon": DIMENSION_LABELS[dim]["icon"],
                "tier": DIMENSION_LABELS[dim]["tier"],
                "weight": weight,
                "active": bool(self.profile.get(dim, {})) and dim in self._loaded,
            }
            for dim, weight in DIMENSION_WEIGHTS.items()
        ]

    @staticmethod
    def _count_fields(data: dict, depth: int = 0) -> int:
        """递归统计非空字段数"""
        if depth > 3:
            return 0
        count = 0
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, (dict, list)):
                    count += ProfileLoader._count_fields(v, depth + 1)
                elif v is not None and v != "":
                    count += 1
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    count += ProfileLoader._count_fields(item, depth + 1)
        return count

    @staticmethod
    def _extract_highlights(dim: str, data: dict) -> list[str]:
        """提取画像亮点标签（脱敏展示）"""
        highlights = []
        if not data:
            return highlights

        if dim == "interests":
            for s in data.get("skills", [])[:3]:
                level = s.get('level', 3)
                level_bar = '⭐' * min(level, 5)
                highlights.append(f"💻 {s.get('name', '')} {level_bar}")
            for t in data.get("tracking_topics", [])[:3]:
                w = t.get('weight', 0.5)
                hot = '🔥' if w >= 0.8 else '🔍'
                highlights.append(f"{hot} 关注「{t.get('keyword', '')}」")
            for g in data.get("learning_goals", [])[:2]:
                highlights.append(f"📖 学习「{g.get('topic', '')}」")

        elif dim == "location":
            home = data.get("home", {})
            if home.get("address"):
                highlights.append(f"🏠 家: {home.get('address', '')[:20]}...")
            elif home.get("label"):
                highlights.append(f"🏠 {home.get('label', '家')}")
            work = data.get("work", {})
            if work.get("address"):
                highlights.append(f"🏢 公司: {work.get('address', '')[:20]}...")
            elif work.get("label"):
                highlights.append(f"🏢 {work.get('label', '公司')}")
            commute = data.get("commute", {})
            if commute:
                highlights.append(f"🚇 通勤: {commute.get('mode', '')}约{commute.get('home_to_work_min', '?')}分钟")
            for p in data.get("frequent_places", [])[:2]:
                highlights.append(f"📍 {p.get('name', '')} ({p.get('category', '')})")

        elif dim == "schedule":
            routine = data.get("routine", {})
            for day_type in ["weekday", "weekend"]:
                slots = routine.get(day_type, [])
                free_slots = [s for s in slots if s.get("availability") == "free"]
                if free_slots:
                    day_label = "工作日" if day_type == "weekday" else "周末"
                    times = [s.get('slot', '') for s in free_slots[:3]]
                    highlights.append(f"🕐 {day_label}空闲: {', '.join(times)}")
            # Fallback
            if not highlights:
                weekday = routine.get("weekday", [])
                free_slots = [s for s in weekday if s.get("availability") == "free"]
                if free_slots:
                    highlights.append(f"🕐 {len(free_slots)}个空闲时段")

        elif dim == "preferences":
            # 购物
            shop = data.get("shopping", {})
            stores = shop.get("preferred_stores", [])
            if stores:
                highlights.append(f"🛒 常用: {', '.join(stores[:4])}")
            cats = shop.get("priority_categories", [])
            if cats:
                highlights.append(f"📦 优先品类: {', '.join(cats[:3])}")
            # 饮食
            food = data.get("food", {})
            cuisines = food.get("cuisines", [])
            for c in cuisines[:3]:
                w = c.get('weight', 0.5)
                highlights.append(f"🍽️ {c.get('name', '')}" + (" ❤️" if w >= 0.9 else ""))
            # 娱乐
            ent = data.get("entertainment", {})
            ent_types = ent.get("types", [])
            if ent_types:
                names = [t.get('name', '') for t in ent_types[:3]]
                highlights.append(f"🎬 娱乐: {', '.join(names)}")

        elif dim == "health":
            basic = data.get("basic_info", {})
            if basic.get("age"):
                gender = basic.get("gender", "")
                gender_label = {"male": "♂️", "female": "♀️"}.get(gender, "")
                highlights.append(f"👤 {basic['age']}岁 {gender_label} | {basic.get('height_cm', '?')}cm/{basic.get('weight_kg', '?')}kg")
            fitness = data.get("fitness", {})
            if fitness:
                freq = fitness.get("weekly_exercise_frequency", 0)
                exercises = fitness.get("preferred_exercise", [])
                if freq > 0:
                    highlights.append(f"🏃 每周运动{freq}次: {', '.join(exercises[:3])}")
            goals = data.get("health_goals", [])
            for g in goals[:2]:
                highlights.append(f"🎯 {g.get('target', '')}")
            concerns = data.get("health_concerns", [])
            if concerns:
                highlights.append(f"⚕️ 关注: {', '.join(concerns[:3])}")
            sleep = data.get("sleep_schedule", {})
            if sleep:
                highlights.append(f"😴 {sleep.get('target_bedtime', '?')} - {sleep.get('target_wakeup', '?')}")

        elif dim == "social":
            pers = data.get("personality", {})
            ie = pers.get("introvert_extrovert")
            if ie is not None:
                if ie < 0.35:
                    label = "内向型 😊"
                elif ie > 0.65:
                    label = "外向型 🎉"
                else:
                    label = "平衡型 ⚖️"
                highlights.append(f"🧠 性格: {label}")
            crowd = data.get("crowd_preference", {})
            if crowd.get("peak_hour_avoidance"):
                highlights.append("🚫 避开高峰期拥挤")
            activities = data.get("social_activities", {}).get("preferred", [])
            for a in activities[:3]:
                highlights.append(f"👋 喜欢「{a.get('type', '')}」")

        elif dim == "budget":
            monthly = data.get("monthly_budget", {})
            total = sum(v for v in monthly.values() if isinstance(v, (int, float)))
            if total > 0:
                highlights.append(f"💳 月预算约 ¥{int(total):,}")
            # 分类预算
            for cat, amount in sorted(monthly.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)[:3]:
                if isinstance(amount, (int, float)) and amount > 0:
                    highlights.append(f"  └ {cat}: ¥{int(amount):,}")
            sensitivity = data.get("price_sensitivity", {})
            if sensitivity:
                high_sens = [k for k, v in sensitivity.items() if v == "high"]
                if high_sens:
                    highlights.append(f"💰 价格敏感品类: {', '.join(high_sens[:3])}")
            alerts = data.get("alert_thresholds", {})
            if alerts.get("price_drop_pct"):
                highlights.append(f"🔔 降价{alerts['price_drop_pct']}%时提醒")

        return highlights[:8]  # 每个维度最多8个标签（原为3个）
