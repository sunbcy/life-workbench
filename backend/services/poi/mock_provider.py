"""
Mock 周边资源数据源（内置深圳南山数据，作为真实 API 的兜底）
"""
from .base import BasePOIProvider


class MockPOIProvider(BasePOIProvider):
    async def search(self, lat, lng, radius_m, category, keyword):
        from api.data import nearby_resources

        resources = [dict(r) for r in nearby_resources]
        if category and category != "all":
            resources = [r for r in resources if r["category"] == category]
        if keyword:
            kw = keyword.lower()
            resources = [
                r for r in resources
                if kw in r["name"].lower() or kw in r["address"].lower()
                or any(kw in t.lower() for t in r.get("tags", []))
            ]
        return resources

    async def get_categories(self):
        from api.data import nearby_categories
        return nearby_categories
