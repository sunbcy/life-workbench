"""
POI 数据源抽象基类与公共分类映射

各 provider（高德 / 百度 / Mock）都归一化为统一的 NearbyResource 结构：
  { id, name, category, icon, distance, address, rating, review_count,
    open_status, hours, tags, phone, features, lat, lng, source }

其中 distance 由 API 层基于用户真实坐标用 haversine 重算，provider 统一填 0。
"""
from abc import ABC, abstractmethod
from typing import Optional


# 分类 -> 图标（统一对外展示）
CATEGORY_ICON = {
    "food": "🍜",
    "market": "🏪",
    "hospital": "🏥",
    "bank": "🏦",
    "education": "📚",
    "entertainment": "🎬",
    "service": "🔧",
    "transport": "🚇",
}

# 分类 -> 高德 POI 分类编码（一级大类）
AMAP_TYPES = {
    "food": "050000",          # 餐饮服务
    "market": "060000",        # 购物服务
    "hospital": "090000",      # 医疗保健
    "bank": "080000",          # 金融保险
    "education": "140000",     # 科教文化
    "entertainment": "110000", # 风景名胜
    "service": "070000",       # 生活服务
    "transport": "150000",     # 交通设施
}

# 分类 -> 百度 POI tag
BAIDU_TAGS = {
    "food": "美食",
    "market": "购物",
    "hospital": "医院",
    "bank": "银行",
    "education": "教育培训",
    "entertainment": "休闲娱乐",
    "service": "生活服务",
    "transport": "交通",
}


class BasePOIProvider(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def search(
        self, lat: float, lng: float, radius_m: int, category: str, keyword: str
    ) -> list[dict]:
        """返回归一化后的周边资源列表（lat/lng 必须为 WGS-84）。"""
        ...

    async def get_categories(self) -> list[dict]:
        """分类维度与数据源无关，统一复用内置分类。"""
        from api.data import nearby_categories
        return nearby_categories

    @staticmethod
    def icon_for(category: str) -> str:
        return CATEGORY_ICON.get(category, "📍")

    @staticmethod
    def _to_float(v, default: float = 0.0) -> float:
        try:
            if v in (None, "", "[]", "{}"):
                return default
            return float(v)
        except (ValueError, TypeError):
            return default
