"""
周边资源服务

委托给可插拔的 POI 数据源（高德 / 百度 / Mock）。
- 按用户「真实位置」(WGS-84) 请求周边 POI；
- 真实数据源未配置 Key 或请求失败时，自动回退到 Mock，保证页面可用；
- 结果做 5 分钟内存缓存，降低地图 API 调用频率。
"""
from __future__ import annotations

import time
from typing import Optional

from . import get_config, geolocation
from .poi import create_poi_provider, MockPOIProvider


class NearbyService:
    def __init__(self, config: dict | None = None):
        self.config = config or get_config()
        self.provider = create_poi_provider(self.config)
        self._cache: dict = {}
        self._cache_ttl = 300  # 秒

    async def get_categories(self) -> list[dict]:
        return await self.provider.get_categories()

    def _crs_of(self, provider) -> str:
        """给定 provider 实例返回其坐标系（用于与用户 WGS-84 坐标对齐距离计算）"""
        from .poi.amap_provider import AmapPOIProvider
        from .poi.baidu_provider import BaiduPOIProvider

        if isinstance(provider, AmapPOIProvider):
            return "gcj02"
        if isinstance(provider, BaiduPOIProvider):
            return "bd09"
        return "wgs84"

    async def get_resources(
        self, category: str = "all", keyword: str = "",
        sort: str = "distance", radius: float = 5.0
    ) -> dict:
        loc = geolocation.get_location()
        lat, lng = loc["lat"], loc["lng"]
        radius_m = int(radius * 1000)

        cache_key = (
            type(self.provider).__name__,
            round(lat, 4), round(lng, 4), radius_m, category, keyword,
        )
        now = time.time()
        hit = self._cache.get(cache_key)
        if hit and now - hit[1] < self._cache_ttl:
            resources, used_crs = hit[0], hit[2]
        else:
            used_provider = self.provider
            resources = await self._fetch(self.provider, lat, lng, radius_m, category, keyword)
            # 真实数据源失败/无数据 -> 自动回退 Mock（坐标系随之变为 wgs84）
            if not resources and not isinstance(self.provider, MockPOIProvider):
                used_provider = MockPOIProvider(self.config)
                resources = await self._fetch(
                    used_provider, lat, lng, radius_m, category, keyword
                )
            used_crs = self._crs_of(used_provider)
            self._cache[cache_key] = (resources, now, used_crs)

        return {
            "resources": resources,
            "total": len(resources),
            "resource_crs": used_crs,
        }

    async def _fetch(self, provider, lat, lng, radius_m, category, keyword) -> list[dict]:
        try:
            return await provider.search(lat, lng, radius_m, category, keyword)
        except Exception:
            return []

    async def get_resource_detail(self, resource_id: int) -> Optional[dict]:
        from api.data import nearby_resources
        for r in nearby_resources:
            if r["id"] == resource_id:
                return r
        return None
