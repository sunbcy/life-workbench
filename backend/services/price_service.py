"""
比价服务 - Mock 实现（未来可扩展电商爬虫实现）
"""


class MockPriceService:
    """使用内置 mock 数据"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def get_categories(self) -> list[dict]:
        from api.data import price_categories
        return price_categories

    async def get_stores(self) -> list[dict]:
        from api.data import stores
        return stores

    async def get_products(
        self, category: str = "all", keyword: str = "", sort: str = "default"
    ) -> dict:
        from api.data import price_products
        products = list(price_products)

        if category and category != "all":
            products = [p for p in products if p["category"] == category]
        if keyword:
            kw = keyword.lower()
            products = [p for p in products if kw in p["name"].lower()]
        if sort == "price_asc":
            products.sort(key=lambda p: p["lowest_price"])
        elif sort == "price_desc":
            products.sort(key=lambda p: p["lowest_price"], reverse=True)
        elif sort == "discount":
            products.sort(key=lambda p: p["trend_pct"])

        return {"products": products, "total": len(products)}

    async def get_product_detail(self, product_id: int) -> dict | None:
        from api.data import price_products, stores
        for product in price_products:
            if product["id"] == product_id:
                prices_with_store = []
                for price in product["prices"]:
                    store_info = next((s for s in stores if s["id"] == price["store_id"]), None)
                    prices_with_store.append({**price, "store": store_info})
                return {**product, "prices": prices_with_store}
        return None

    async def get_alerts(self) -> list[dict]:
        from api.data import price_alerts
        return price_alerts
