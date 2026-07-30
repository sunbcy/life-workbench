"""
向量化引擎 — 将用户画像和内容项转换为特征向量
"""

import math
import re
from datetime import datetime, timezone, timedelta

TZ_CHINA = timezone(timedelta(hours=8))

# 维度权重（与 profile_loader 保持一致）
DIM_WEIGHTS = {
    "interests": 0.30, "location": 0.20, "schedule": 0.15,
    "preferences": 0.12, "health": 0.10, "social": 0.08, "budget": 0.05,
}


class UserVectorizer:
    """将用户 profile 转换为特征向量"""

    def vectorize(self, profile: dict) -> dict:
        """返回结构化的用户向量"""
        return {
            "interests": self._interests_vector(profile.get("interests", {})),
            "location": self._location_vector(profile.get("location", {})),
            "schedule": self._schedule_vector(profile.get("schedule", {})),
            "preferences": self._preferences_vector(profile.get("preferences", {})),
            "health": self._health_vector(profile.get("health", {})),
            "social": self._social_vector(profile.get("social", {})),
            "budget": self._budget_vector(profile.get("budget", {})),
        }

    def _interests_vector(self, data: dict) -> dict:
        skills = {s.get("name", "").lower(): s.get("level", 3) / 5.0
                  for s in data.get("skills", [])}
        hobbies = [h.get("name", "").lower() for h in data.get("hobbies", [])]
        goals = [g.get("topic", "").lower() for g in data.get("learning_goals", [])]
        tracking = {t.get("keyword", "").lower(): t.get("weight", 0.5)
                    for t in data.get("tracking_topics", [])}
        excluded = set(e.lower() for e in data.get("excluded_topics", []))
        return {
            "skills": skills, "hobbies": hobbies, "goals": goals,
            "tracking": tracking, "excluded": excluded,
        }

    def _location_vector(self, data: dict) -> dict:
        home = data.get("home", {})
        work = data.get("work", {})
        frequent = []
        for p in data.get("frequent_places", []):
            frequent.append({
                "lat": p.get("lat"), "lng": p.get("lng"),
                "category": p.get("category", ""),
                "name": p.get("name", "").lower(),
            })
        radii = data.get("search_radius_km", {})
        return {
            "home": {"lat": home.get("lat"), "lng": home.get("lng")},
            "work": {"lat": work.get("lat"), "lng": work.get("lng")},
            "frequent": frequent,
            "radius_default": radii.get("default", 3.0),
        }

    def _schedule_vector(self, data: dict) -> dict:
        routine = data.get("routine", {})
        now = datetime.now(TZ_CHINA)
        hour = now.hour
        weekday = now.weekday()  # 0=Mon, 6=Sun
        is_weekend = weekday >= 5

        # 判断当前是否空闲
        slots = routine.get("weekend" if is_weekend else "weekday", [])
        currently_free = False
        current_activity = "unknown"
        for s in slots:
            try:
                start_h, start_m = map(int, s["slot"].split("-")[0].split(":"))
                end_h, end_m = map(int, s["slot"].split("-")[1].split(":"))
                start_min = start_h * 60 + start_m
                end_min = end_h * 60 + end_m
                now_min = hour * 60 + datetime.now(TZ_CHINA).minute
                if start_min <= now_min < end_min:
                    currently_free = s.get("availability") == "free"
                    current_activity = s.get("activity", "unknown")
                    break
            except (ValueError, IndexError):
                continue

        return {
            "is_weekend": is_weekend,
            "currently_free": currently_free,
            "current_activity": current_activity,
            "hour": hour,
        }

    def _preferences_vector(self, data: dict) -> dict:
        food = data.get("food", {})
        shopping = data.get("shopping", {})
        entertainment = data.get("entertainment", {})
        return {
            "preferred_stores": [s.lower() for s in shopping.get("preferred_stores", [])],
            "priority_categories": [c.lower() for c in shopping.get("priority_categories", [])],
            "cuisines": {c.get("name", "").lower(): c.get("weight", 0.5)
                        for c in food.get("cuisines", [])},
            "avoided_cuisines": [c.lower() for c in food.get("avoided_cuisines", [])],
            "entertainment_types": {t.get("name", "").lower(): t.get("weight", 0.5)
                                    for t in entertainment.get("types", [])},
            "dietary": food.get("dietary_restrictions", []),
        }

    def _health_vector(self, data: dict) -> dict:
        basic = data.get("basic_info", {})
        fitness = data.get("fitness", {})
        return {
            "age": basic.get("age", 30),
            "exercise_freq": fitness.get("weekly_exercise_frequency", 0),
            "preferred_exercise": [e.lower() for e in fitness.get("preferred_exercise", [])],
            "activity_level": fitness.get("activity_level", "moderate"),
            "concerns": [c.lower() for c in data.get("health_concerns", [])],
            "goals": [g.get("type", "").lower() for g in data.get("health_goals", [])],
        }

    def _social_vector(self, data: dict) -> dict:
        personality = data.get("personality", {})
        crowd = data.get("crowd_preference", {})
        activities = data.get("social_activities", {})
        return {
            "introvert_extrovert": personality.get("introvert_extrovert", 0.5),
            "crowd_tolerance": personality.get("crowd_tolerance", "medium"),
            "preferred_activities": [a.get("type", "").lower()
                                     for a in activities.get("preferred", [])],
            "max_crowd_level": crowd.get("max_crowd_level", 5),
            "peak_avoidance": crowd.get("peak_hour_avoidance", False),
        }

    def _budget_vector(self, data: dict) -> dict:
        monthly = data.get("monthly_budget", {})
        sensitivity = data.get("price_sensitivity", {})
        alerts = data.get("alert_thresholds", {})
        return {
            "monthly_total": sum(v for v in monthly.values() if isinstance(v, (int, float))),
            "sensitivity": sensitivity,
            "price_drop_threshold": alerts.get("price_drop_pct", 15),
        }


class ItemVectorizer:
    """将内容项转换为特征向量"""

    def vectorize(self, item: dict, item_type: str = "news") -> dict:
        if item_type == "news":
            return self._news_vector(item)
        elif item_type == "product":
            return self._product_vector(item)
        elif item_type == "nearby":
            return self._nearby_vector(item)
        return {}

    def _news_vector(self, item: dict) -> dict:
        title = (item.get("title") or "").lower()
        summary = (item.get("summary") or "").lower()
        tags = [t.lower() for t in item.get("tags", [])]
        category = (item.get("category") or "").lower()
        return {
            "text": f"{title} {summary}",
            "tags": tags,
            "category": category,
            "is_trending": item.get("trending", False),
            "published_at": item.get("published_at", ""),
        }

    def _product_vector(self, item: dict) -> dict:
        name = (item.get("name") or "").lower()
        category = (item.get("category") or "").lower()
        prices = item.get("prices", [])
        min_price = min((p.get("price", float("inf")) for p in prices), default=0)
        return {
            "text": name,
            "category": category,
            "min_price": min_price,
            "trend": item.get("trend", "stable"),
            "trend_pct": item.get("trend_pct", 0),
        }

    def _nearby_vector(self, item: dict) -> dict:
        name = (item.get("name") or "").lower()
        address = (item.get("address") or "").lower()
        category = (item.get("category") or "").lower()
        tags = [t.lower() for t in item.get("tags", [])]
        features = [f.lower() for f in item.get("features", [])]
        return {
            "text": f"{name} {address}",
            "category": category,
            "tags": tags,
            "features": features,
            "distance_km": item.get("distance", 5.0),
            "rating": item.get("rating", 0),
            "review_count": item.get("review_count", 0),
        }
