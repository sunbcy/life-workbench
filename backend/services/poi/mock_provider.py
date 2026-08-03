"""
Mock 周边资源数据源

当真实 API (高德/百度) 不可用时自动回退到此 provider。
根据用户当前位置动态生成模拟周边地点，不再是硬编码南山数据。
"""
import random
from .base import BasePOIProvider


class MockPOIProvider(BasePOIProvider):
    async def search(self, lat, lng, radius_m, category, keyword):
        """根据用户坐标动态生成模拟周边资源

        确保即使用户在宝安区/福田区等不同位置，都能看到"附近"的模拟地点。
        """
        from services import geolocation

        loc = geolocation.get_location()
        user_district = loc.get("district", "南山区")
        user_city = loc.get("city", "深圳")

        # 如果坐标匹配模块给出了区名，优先使用
        from services.termux_location import _shenzhen_district_match
        matched_city, matched_district = _shenzhen_district_match(lat, lng)
        if matched_district:
            user_district = matched_district
        if matched_city:
            user_city = matched_city

        district = user_district or "附近"
        city = user_city or "深圳"

        # 基于用户坐标动态生成周边地点
        templates = self._templates(district, city)
        resources = []
        for i, t in enumerate(templates):
            # 在用户周围随机偏移（50m ~ radius_m）
            angle = random.uniform(0, 360)
            offset_m = random.uniform(80, max(radius_m * 0.8, 500))
            offset_deg = offset_m / 111320.0  # 纬度1度≈111.32km
            dlat = offset_deg * random.choice([1, -1]) * (0.5 + random.random() * 0.5)
            dlng = offset_deg * random.choice([1, -1]) * (0.5 + random.random() * 0.5) / abs(
                __import__("math").cos(__import__("math").radians(lat)) + 0.001
            )

            rlat = lat + dlat
            rlng = lng + dlng
            distance = round(
                __import__("math").sqrt(dlat**2 + (dlng * __import__("math").cos(__import__("math").radians(lat)))**2) * 111.32,
                1,
            )

            resources.append({
                "id": 200000 + i,
                "name": t["name"],
                "category": t["category"],
                "icon": t["icon"],
                "distance": distance,
                "address": t["address"].format(district=district),
                "rating": t["rating"],
                "review_count": t["review_count"],
                "open_status": t["open_status"],
                "hours": t["hours"],
                "tags": t["tags"],
                "phone": t["phone"],
                "features": t["features"],
                "lat": round(rlat, 6),
                "lng": round(rlng, 6),
                "source": "mock-adaptive",
            })

        # 按距离过滤/排序
        resources = [r for r in resources if r["distance"] <= radius_m / 1000.0]
        resources.sort(key=lambda r: r["distance"])

        # 分类过滤
        if category and category != "all":
            resources = [r for r in resources if r["category"] == category]

        # 关键词过滤
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

    @staticmethod
    def _templates(district: str, city: str) -> list[dict]:
        """返回周边地点模板 — 地址动态填入用户所在区"""
        return [
            {
                "name": f"{district}购物中心",
                "category": "market",
                "icon": "🏬",
                "address": f"{city}{district}商业大道88号",
                "rating": 4.5,
                "review_count": 8300,
                "open_status": "营业中",
                "hours": "10:00-22:00",
                "tags": ["购物", "餐饮", "影院"],
                "phone": "0755-8888-6666",
                "features": ["免费WiFi", "停车场", "母婴室"],
            },
            {
                "name": f"{district}中心公园",
                "category": "entertainment",
                "icon": "🌳",
                "address": f"{city}{district}公园路1号",
                "rating": 4.7,
                "review_count": 15600,
                "open_status": "开放中",
                "hours": "06:00-23:00",
                "tags": ["公园", "跑步", "骑行"],
                "phone": None,
                "features": ["免费开放", "停车场", "自行车道"],
            },
            {
                "name": f"{district}人民医院",
                "category": "hospital",
                "icon": "🏥",
                "address": f"{city}{district}健康路100号",
                "rating": 4.2,
                "review_count": 4200,
                "open_status": "24小时",
                "hours": "全天",
                "tags": ["综合医院", "急诊"],
                "phone": "0755-8888-1200",
                "features": ["急诊24h", "在线挂号", "医保定点"],
            },
            {
                "name": "招商银行(分行营业部)",
                "category": "bank",
                "icon": "🏦",
                "address": f"{city}{district}金融街8号",
                "rating": 4.3,
                "review_count": 890,
                "open_status": "营业中",
                "hours": "09:00-17:00",
                "tags": ["银行", "理财"],
                "phone": "0755-8888-8888",
                "features": ["24hATM", "理财专区"],
            },
            {
                "name": f"{district}图书馆",
                "category": "education",
                "icon": "📚",
                "address": f"{city}{district}文化路56号",
                "rating": 4.6,
                "review_count": 3200,
                "open_status": "开放中",
                "hours": "09:00-21:00",
                "tags": ["图书馆", "自习", "WiFi"],
                "phone": "0755-8888-1234",
                "features": ["免费WiFi", "自习室", "自助借还"],
            },
            {
                "name": "盒马鲜生(门店)",
                "category": "market",
                "icon": "🦛",
                "address": f"{city}{district}生活路22号",
                "rating": 4.4,
                "review_count": 5700,
                "open_status": "营业中",
                "hours": "09:00-22:00",
                "tags": ["生鲜", "超市", "配送"],
                "phone": "0755-8888-2222",
                "features": ["30分钟达", "堂食区"],
            },
            {
                "name": f"{district}老牌茶餐厅",
                "category": "food",
                "icon": "🍜",
                "address": f"{city}{district}美食街15号",
                "rating": 4.5,
                "review_count": 2200,
                "open_status": "营业中",
                "hours": "07:00-23:00",
                "tags": ["茶餐厅", "粤菜", "早茶"],
                "phone": "0755-8888-3333",
                "features": ["包厢", "免费停车"],
            },
            {
                "name": "地铁站(出入口)",
                "category": "transport",
                "icon": "🚇",
                "address": f"{city}{district}主干道与建设路交叉口",
                "rating": 4.3,
                "review_count": 1500,
                "open_status": "运营中",
                "hours": "06:30-23:30",
                "tags": ["地铁", "交通枢纽"],
                "phone": None,
                "features": ["无障碍电梯", "充值网点"],
            },
            {
                "name": f"{district}健身房",
                "category": "entertainment",
                "icon": "💪",
                "address": f"{city}{district}体育路10号",
                "rating": 4.6,
                "review_count": 1800,
                "open_status": "营业中",
                "hours": "06:00-23:00",
                "tags": ["健身", "团课", "私教"],
                "phone": "400-888-6666",
                "features": ["淋浴", "储物柜", "免费停车"],
            },
            {
                "name": "顺丰快递(营业部)",
                "category": "service",
                "icon": "📦",
                "address": f"{city}{district}工业路3号",
                "rating": 4.2,
                "review_count": 900,
                "open_status": "营业中",
                "hours": "08:00-20:00",
                "tags": ["快递", "寄件", "收件"],
                "phone": "95338",
                "features": ["上门取件", "自助寄件柜"],
            },
            {
                "name": f"{district}社区超市",
                "category": "market",
                "icon": "🛒",
                "address": f"{city}{district}居民区底商12号",
                "rating": 4.1,
                "review_count": 600,
                "open_status": "营业中",
                "hours": "07:00-23:00",
                "tags": ["便利店", "日用品"],
                "phone": None,
                "features": ["24h", "支持外卖"],
            },
            {
                "name": f"{district}麻辣烫",
                "category": "food",
                "icon": "🍲",
                "address": f"{city}{district}小吃街8号",
                "rating": 4.4,
                "review_count": 3100,
                "open_status": "营业中",
                "hours": "10:00-02:00",
                "tags": ["麻辣烫", "宵夜", "平价"],
                "phone": None,
                "features": ["深夜营业", "外卖"],
            },
        ]
