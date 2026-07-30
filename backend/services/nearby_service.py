"""
周边资源服务 - Mock 实现（未来可扩展高德/百度地图 POI 实现）
"""


class MockNearbyService:
    """使用内置 mock 数据"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def get_categories(self) -> list[dict]:
        from api.data import nearby_categories
        return nearby_categories

    async def get_resources(
        self, category: str = "all", keyword: str = "",
        sort: str = "distance", radius: float = 5.0
    ) -> dict:
        from api.data import nearby_resources
        resources = list(nearby_resources)

        resources = [r for r in resources if r["distance"] <= radius]
        if category and category != "all":
            resources = [r for r in resources if r["category"] == category]
        if keyword:
            kw = keyword.lower()
            resources = [
                r for r in resources
                if kw in r["name"].lower() or kw in r["address"].lower()
                or any(kw in t.lower() for t in r.get("tags", []))
            ]
        if sort == "distance":
            resources.sort(key=lambda r: r["distance"])
        elif sort == "rating":
            resources.sort(key=lambda r: r["rating"], reverse=True)
        elif sort == "popularity":
            resources.sort(key=lambda r: r["review_count"], reverse=True)

        return {"resources": resources, "total": len(resources)}

    async def get_resource_detail(self, resource_id: int) -> dict | None:
        from api.data import nearby_resources
        for r in nearby_resources:
            if r["id"] == resource_id:
                return r
        return None
