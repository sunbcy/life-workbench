"""
百度地图 POI 数据源（Place API）

文档: https://lbsyun.baidu.com/index.php?title=webapi/place-api
- 周边搜索: /place/v2/search (radius + location + query/tag)
- 坐标体系: 百度使用 BD-09，需将设备 WGS-84 坐标转换后请求
- 返回的 location 为 BD-09，写回前转回 WGS-84 以统一距离计算
"""
import httpx

from .base import BasePOIProvider, BAIDU_TAGS
from .coord import wgs84_to_bd09, bd09_to_wgs84


class BaiduPOIProvider(BasePOIProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        ds = config.get("datasource", {}).get("nearby", {})
        self.api_key = ds.get("baidu_key") or config.get("baidu", {}).get("api_key", "")
        self.base = "https://api.map.baidu.com/place/v2/search"

    async def search(self, lat, lng, radius_m, category, keyword):
        if not self.api_key:
            return []
        # 设备 WGS-84 -> 百度 BD-09
        blat, blng = wgs84_to_bd09(lat, lng)
        params = {
            "ak": self.api_key,
            "output": "json",
            "location": f"{blat:.6f},{blng:.6f}",
            "radius": int(radius_m),
            "scope": 2,          # scope=2 返回详细字段（含 rating）
            "page_size": 20,
            "page_num": 0,
        }
        if category and category != "all":
            params["tag"] = BAIDU_TAGS.get(category, "")
            params["query"] = keyword or BAIDU_TAGS.get(category, "")
        else:
            params["query"] = keyword or "美食|购物|医院|银行|教育|休闲娱乐"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.base, params=params)
                data = resp.json()
        except Exception:
            return []

        if data.get("status") != 0:
            return []

        resources = []
        for i, p in enumerate(data.get("results", [])):
            loc = p.get("location", {}) or {}
            plat, plng = loc.get("lat"), loc.get("lng")
            if plat is None or plng is None:
                continue
            # BD-09 -> WGS-84，统一坐标系
            wlat, wlng = bd09_to_wgs84(plat, plng)

            address = p.get("address", "") or (
                f'{p.get("province", "")}{p.get("city", "")}{p.get("area", "")}'
            ).strip()
            tags = [t for t in (p.get("tags", "") or "").split(",") if t][:3]

            resources.append({
                "id": 200000 + i,
                "name": p.get("name", "未知地点"),
                "category": category if category != "all" else "service",
                "icon": self.icon_for(category if category != "all" else "service"),
                "distance": 0,  # API 层 haversine 重算
                "address": address,
                "rating": self._to_float(p.get("rating")),
                "review_count": 0,
                "open_status": "营业中",
                "hours": "查看详情" if p.get("detail") else "未知",
                "tags": tags,
                "phone": p.get("telephone") or None,
                "features": [],
                "lat": wlat,
                "lng": wlng,
                "source": "baidu",
            })
        return resources
