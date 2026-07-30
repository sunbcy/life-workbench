"""
高德地图 POI 数据源（Web 服务 API）

文档: https://lbs.amap.com/api/webservice/guide/api/search
- 周边搜索: /v3/place/around
- 坐标体系: 高德使用 GCJ-02，需将设备 WGS-84 坐标转换后请求
- 返回的 location 为 GCJ-02，写回前转回 WGS-84 以统一距离计算
"""
import httpx

from .base import BasePOIProvider, AMAP_TYPES
from .coord import wgs84_to_gcj02, gcj02_to_wgs84


class AmapPOIProvider(BasePOIProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        ds = config.get("datasource", {}).get("nearby", {})
        self.api_key = ds.get("amap_key") or config.get("amap", {}).get("api_key", "")
        self.base = "https://restapi.amap.com/v3/place/around"

    async def search(self, lat, lng, radius_m, category, keyword):
        if not self.api_key:
            return []
        # 设备 WGS-84 -> 高德 GCJ-02
        glat, glng = wgs84_to_gcj02(lat, lng)
        params = {
            "key": self.api_key,
            "location": f"{glng:.6f},{glat:.6f}",
            "radius": int(radius_m),
            "offset": 25,
            "page": 1,
            "output": "json",
            "sortrule": "distance",
            "extensions": "base",
        }
        if category and category != "all":
            params["types"] = AMAP_TYPES.get(category, "")
        if keyword:
            params["keywords"] = keyword

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.base, params=params)
                data = resp.json()
        except Exception:
            return []

        if data.get("status") != "1":
            return []

        resources = []
        for i, p in enumerate(data.get("pois", [])):
            loc = p.get("location", "")
            if "," not in loc:
                continue
            lng_s, lat_s = loc.split(",")
            try:
                plat, plng = float(lat_s), float(lng_s)
            except ValueError:
                continue
            # GCJ-02 -> WGS-84，统一坐标系
            wlat, wlng = gcj02_to_wgs84(plat, plng)

            biz = p.get("biz_ext", {}) or {}
            rating = self._to_float(biz.get("rating"))
            poi_type = p.get("type", "") or ""
            tags = [t for t in poi_type.split(";") if t][:3]
            top_cat = poi_type.split(";")[0] if poi_type else ""

            resources.append({
                "id": 100000 + i,
                "name": p.get("name", "未知地点"),
                "category": category if category != "all" else (top_cat or "service"),
                "icon": self.icon_for(category if category != "all" else "service"),
                "distance": 0,  # API 层 haversine 重算
                "address": p.get("address") or (f'{p.get("adname", "")}').strip(),
                "rating": rating,
                "review_count": int(self._to_float(p.get("poiweight"))),
                "open_status": "营业中",
                "hours": "查看详情",
                "tags": tags,
                "phone": p.get("tel") or None,
                "features": [],
                "lat": wlat,
                "lng": wlng,
                "source": "amap",
            })
        return resources
