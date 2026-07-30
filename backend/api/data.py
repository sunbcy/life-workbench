"""
模拟数据模块 - 提供丰富的演示数据
"""

# ========== 天气数据 ==========
weather_data = {
    "current": {
        "temperature": 32,
        "feels_like": 36,
        "humidity": 75,
        "condition": "晴间多云",
        "icon": "partly-cloudy",
        "wind_speed": 12,
        "wind_direction": "东南风",
        "uv_index": 8,
        "visibility": 10,
        "aqi": 45,
        "aqi_level": "优"
    },
    "forecast": [
        {"day": "今天", "high": 34, "low": 27, "condition": "晴间多云", "icon": "partly-cloudy", "rain_prob": 20},
        {"day": "明天", "high": 33, "low": 26, "condition": "雷阵雨", "icon": "thunderstorm", "rain_prob": 70},
        {"day": "后天", "high": 31, "low": 25, "condition": "小雨", "icon": "rainy", "rain_prob": 85},
        {"day": "周六", "high": 33, "low": 27, "condition": "多云", "icon": "cloudy", "rain_prob": 30},
        {"day": "周日", "high": 35, "low": 28, "condition": "晴天", "icon": "sunny", "rain_prob": 5},
        {"day": "周一", "high": 34, "low": 27, "condition": "晴间多云", "icon": "partly-cloudy", "rain_prob": 15},
        {"day": "周二", "high": 32, "low": 26, "condition": "阵雨", "icon": "shower", "rain_prob": 60},
    ],
    "alerts": [
        {"level": "黄色", "type": "高温", "message": "当前高温黄色预警，请注意防暑降温"}
    ]
}

# ========== 比价数据 ==========
price_categories = [
    {"id": "all", "name": "全部", "icon": "🛒"},
    {"id": "fresh", "name": "生鲜果蔬", "icon": "🥬"},
    {"id": "meat", "name": "肉禽蛋奶", "icon": "🥩"},
    {"id": "grain", "name": "粮油调味", "icon": "🌾"},
    {"id": "snack", "name": "零食饮料", "icon": "🍿"},
    {"id": "daily", "name": "日用百货", "icon": "🧴"},
    {"id": "digital", "name": "数码家电", "icon": "📱"},
    {"id": "health", "name": "健康保健", "icon": "💊"},
]

stores = [
    {"id": "walmart", "name": "沃尔玛", "logo": "🏪", "delivery_fee": 5.0, "min_order": 39},
    {"id": "hema", "name": "盒马鲜生", "logo": "🦛", "delivery_fee": 0, "min_order": 0},
    {"id": "meituan", "name": "美团优选", "logo": "🛵", "delivery_fee": 3.0, "min_order": 15},
    {"id": "pupu", "name": "朴朴超市", "logo": "🥬", "delivery_fee": 0, "min_order": 19},
    {"id": "dingdong", "name": "叮咚买菜", "logo": "🐟", "delivery_fee": 0, "min_order": 0},
    {"id": "yonghui", "name": "永辉超市", "logo": "🏬", "delivery_fee": 4.0, "min_order": 29},
]

price_products = [
    {
        "id": 1, "name": "智利车厘子 JJ级 2.5kg", "category": "fresh",
        "image": "🍒", "unit": "箱/2.5kg",
        "prices": [
            {"store_id": "walmart", "price": 199, "original": 259, "in_stock": True, "promotion": "满299减50"},
            {"store_id": "hema", "price": 219, "original": 239, "in_stock": True, "promotion": None},
            {"store_id": "meituan", "price": 189, "original": 249, "in_stock": True, "promotion": "新人减20"},
            {"store_id": "pupu", "price": 209, "original": 229, "in_stock": False, "promotion": None},
            {"store_id": "dingdong", "price": 195, "original": 245, "in_stock": True, "promotion": "满99减15"},
            {"store_id": "yonghui", "price": 215, "original": 235, "in_stock": True, "promotion": "会员95折"},
        ],
        "trend": "down", "trend_pct": -8.5, "lowest_store": "美团优选", "lowest_price": 189
    },
    {
        "id": 2, "name": "澳洲和牛 M5牛排 200g×3", "category": "meat",
        "image": "🥩", "unit": "份/600g",
        "prices": [
            {"store_id": "walmart", "price": 168, "original": 188, "in_stock": True, "promotion": "第二件半价"},
            {"store_id": "hema", "price": 179, "original": 179, "in_stock": True, "promotion": None},
            {"store_id": "meituan", "price": 159, "original": 199, "in_stock": True, "promotion": "限时特惠"},
            {"store_id": "pupu", "price": 175, "original": 185, "in_stock": True, "promotion": None},
            {"store_id": "dingdong", "price": 165, "original": 195, "in_stock": True, "promotion": "满128减20"},
            {"store_id": "yonghui", "price": 182, "original": 192, "in_stock": True, "promotion": None},
        ],
        "trend": "up", "trend_pct": 5.2, "lowest_store": "美团优选", "lowest_price": 159
    },
    {
        "id": 3, "name": "五常大米 稻花香2号 5kg", "category": "grain",
        "image": "🍚", "unit": "袋/5kg",
        "prices": [
            {"store_id": "walmart", "price": 59.9, "original": 69.9, "in_stock": True, "promotion": None},
            {"store_id": "hema", "price": 65, "original": 65, "in_stock": True, "promotion": "满99减10"},
            {"store_id": "meituan", "price": 49.9, "original": 59.9, "in_stock": True, "promotion": "团购价"},
            {"store_id": "pupu", "price": 55, "original": 62, "in_stock": True, "promotion": None},
            {"store_id": "dingdong", "price": 52.9, "original": 58.9, "in_stock": True, "promotion": None},
            {"store_id": "yonghui", "price": 56.9, "original": 66.9, "in_stock": True, "promotion": "会员95折"},
        ],
        "trend": "stable", "trend_pct": 0.3, "lowest_store": "美团优选", "lowest_price": 49.9
    },
    {
        "id": 4, "name": "伊利安慕希原味酸奶 205g×12", "category": "snack",
        "image": "🥛", "unit": "箱/12盒",
        "prices": [
            {"store_id": "walmart", "price": 54.9, "original": 66, "in_stock": True, "promotion": "买2箱减10"},
            {"store_id": "hema", "price": 59.9, "original": 59.9, "in_stock": True, "promotion": None},
            {"store_id": "meituan", "price": 49.9, "original": 62, "in_stock": True, "promotion": "爆品秒杀"},
            {"store_id": "pupu", "price": 52.9, "original": 58, "in_stock": True, "promotion": None},
            {"store_id": "dingdong", "price": 55.9, "original": 65, "in_stock": True, "promotion": None},
            {"store_id": "yonghui", "price": 57.9, "original": 63.9, "in_stock": True, "promotion": "会员95折"},
        ],
        "trend": "down", "trend_pct": -3.8, "lowest_store": "美团优选", "lowest_price": 49.9
    },
    {
        "id": 5, "name": "维达超韧抽纸 3层×100抽×24包", "category": "daily",
        "image": "🧻", "unit": "箱/24包",
        "prices": [
            {"store_id": "walmart", "price": 49.9, "original": 59.9, "in_stock": True, "promotion": "满99减20"},
            {"store_id": "hema", "price": 55.9, "original": 55.9, "in_stock": True, "promotion": None},
            {"store_id": "meituan", "price": 42.9, "original": 52.9, "in_stock": True, "promotion": "拼团价"},
            {"store_id": "pupu", "price": 46.9, "original": 56.9, "in_stock": True, "promotion": None},
            {"store_id": "dingdong", "price": 48.9, "original": 58.9, "in_stock": True, "promotion": None},
            {"store_id": "yonghui", "price": 51.9, "original": 54.9, "in_stock": True, "promotion": None},
        ],
        "trend": "down", "trend_pct": -6.2, "lowest_store": "美团优选", "lowest_price": 42.9
    },
    {
        "id": 6, "name": "AirPods Pro 2 无线耳机", "category": "digital",
        "image": "🎧", "unit": "副",
        "prices": [
            {"store_id": "walmart", "price": 1699, "original": 1899, "in_stock": True, "promotion": "618大促"},
            {"store_id": "hema", "price": 1799, "original": 1899, "in_stock": True, "promotion": None},
            {"store_id": "meituan", "price": 1659, "original": 1899, "in_stock": True, "promotion": "限时补贴"},
            {"store_id": "pupu", "price": 1899, "original": 1899, "in_stock": False, "promotion": None},
            {"store_id": "dingdong", "price": 1899, "original": 1899, "in_stock": False, "promotion": None},
            {"store_id": "yonghui", "price": 1749, "original": 1999, "in_stock": True, "promotion": "会员价"},
        ],
        "trend": "down", "trend_pct": -5.8, "lowest_store": "美团优选", "lowest_price": 1659
    },
    {
        "id": 7, "name": "深海鳕鱼 冷冻 500g", "category": "fresh",
        "image": "🐟", "unit": "袋/500g",
        "prices": [
            {"store_id": "walmart", "price": 39.9, "original": 45.9, "in_stock": True, "promotion": None},
            {"store_id": "hema", "price": 42.9, "original": 42.9, "in_stock": True, "promotion": "买2送1"},
            {"store_id": "meituan", "price": 35.9, "original": 42.9, "in_stock": True, "promotion": "限时特价"},
            {"store_id": "pupu", "price": 38.9, "original": 44.9, "in_stock": True, "promotion": None},
            {"store_id": "dingdong", "price": 36.9, "original": 43.9, "in_stock": True, "promotion": "满99减15"},
            {"store_id": "yonghui", "price": 41.9, "original": 46.9, "in_stock": True, "promotion": None},
        ],
        "trend": "stable", "trend_pct": -0.5, "lowest_store": "美团优选", "lowest_price": 35.9
    },
    {
        "id": 8, "name": "善存多维复合维生素 120粒", "category": "health",
        "image": "💊", "unit": "瓶/120粒",
        "prices": [
            {"store_id": "walmart", "price": 159, "original": 189, "in_stock": True, "promotion": "第二件半价"},
            {"store_id": "hema", "price": 169, "original": 189, "in_stock": True, "promotion": None},
            {"store_id": "meituan", "price": 149, "original": 179, "in_stock": True, "promotion": "满299减50"},
            {"store_id": "pupu", "price": 165, "original": 185, "in_stock": True, "promotion": None},
            {"store_id": "dingdong", "price": 155, "original": 195, "in_stock": True, "promotion": None},
            {"store_id": "yonghui", "price": 175, "original": 195, "in_stock": True, "promotion": "会员95折"},
        ],
        "trend": "up", "trend_pct": 2.1, "lowest_store": "美团优选", "lowest_price": 149
    },
]

# ========== 周边资源数据 ==========
nearby_categories = [
    {"id": "all", "name": "全部", "icon": "📍"},
    {"id": "food", "name": "美食餐饮", "icon": "🍜"},
    {"id": "market", "name": "商超市场", "icon": "🏪"},
    {"id": "hospital", "name": "医疗健康", "icon": "🏥"},
    {"id": "bank", "name": "银行金融", "icon": "🏦"},
    {"id": "education", "name": "教育培训", "icon": "📚"},
    {"id": "entertainment", "name": "休闲娱乐", "icon": "🎬"},
    {"id": "service", "name": "生活服务", "icon": "🔧"},
    {"id": "transport", "name": "交通出行", "icon": "🚇"},
]

nearby_resources = [
    {
        "id": 1, "name": "海岸城购物中心", "category": "market",
        "icon": "🏬", "distance": 1.2, "address": "南山区文心五路33号",
        "rating": 4.6, "review_count": 12830,
        "open_status": "营业中", "hours": "10:00-22:00",
        "tags": ["购物", "餐饮", "影院", "停车"],
        "phone": "0755-8635-8888",
        "features": ["免费WiFi", "停车场", "母婴室", "无障碍通道"]
    },
    {
        "id": 2, "name": "深圳湾公园", "category": "entertainment",
        "icon": "🌳", "distance": 2.5, "address": "南山区望海路",
        "rating": 4.8, "review_count": 25600,
        "open_status": "开放中", "hours": "06:00-23:00",
        "tags": ["公园", "跑步", "骑行", "观鸟"],
        "phone": None,
        "features": ["免费开放", "停车场", "自行车道", "观景平台"]
    },
    {
        "id": 3, "name": "华中科技大学协和深圳医院", "category": "hospital",
        "icon": "🏥", "distance": 3.1, "address": "南山区桃园路89号",
        "rating": 4.3, "review_count": 5200,
        "open_status": "24小时", "hours": "全天",
        "tags": ["三甲医院", "急诊", "体检"],
        "phone": "0755-2655-3333",
        "features": ["急诊24h", "在线挂号", "医保定点"]
    },
    {
        "id": 4, "name": "招商银行(南山支行)", "category": "bank",
        "icon": "🏦", "distance": 0.8, "address": "南山区南海大道1019号",
        "rating": 4.2, "review_count": 890,
        "open_status": "营业中", "hours": "09:00-17:00",
        "tags": ["银行", "理财", "外汇"],
        "phone": "0755-2688-6666",
        "features": ["24hATM", "理财专区", "VIP室"]
    },
    {
        "id": 5, "name": "深圳图书馆(南山分馆)", "category": "education",
        "icon": "📚", "distance": 2.8, "address": "南山区常兴路176号",
        "rating": 4.7, "review_count": 3800,
        "open_status": "开放中", "hours": "09:00-21:00",
        "tags": ["图书馆", "自习", "WiFi", "借阅"],
        "phone": "0755-2654-1234",
        "features": ["免费WiFi", "自习室", "自助借还", "儿童区"]
    },
    {
        "id": 6, "name": "盒马鲜生(南山店)", "category": "market",
        "icon": "🦛", "distance": 0.5, "address": "南山区科技南路18号",
        "rating": 4.5, "review_count": 6700,
        "open_status": "营业中", "hours": "09:00-22:00",
        "tags": ["生鲜", "超市", "配送"],
        "phone": "0755-2690-2222",
        "features": ["30分钟达", "堂食区", "活海鲜", "会员积分"]
    },
    {
        "id": 7, "name": "海底捞火锅(海岸城店)", "category": "food",
        "icon": "🍲", "distance": 1.3, "address": "南山区文心五路33号海岸城4F",
        "rating": 4.6, "review_count": 15200,
        "open_status": "营业中", "hours": "11:00-03:00",
        "tags": ["火锅", "聚会", "美甲", "等位茶点"],
        "phone": "0755-8652-7777",
        "features": ["深夜营业", "包厢", "美甲服务", "免费停车"]
    },
    {
        "id": 8, "name": "地铁2号线-科苑站", "category": "transport",
        "icon": "🚇", "distance": 0.6, "address": "南山区科苑南路",
        "rating": 4.4, "review_count": 2100,
        "open_status": "运营中", "hours": "06:30-23:30",
        "tags": ["地铁", "2号线"],
        "phone": None,
        "features": ["无障碍电梯", "充值网点", "便利店"]
    },
    {
        "id": 9, "name": "超级猩猩健身(科技园店)", "category": "entertainment",
        "icon": "💪", "distance": 0.9, "address": "南山区科技南路28号",
        "rating": 4.7, "review_count": 4300,
        "open_status": "营业中", "hours": "06:00-23:00",
        "tags": ["健身", "团课", "按次付费"],
        "phone": "400-893-6666",
        "features": ["按次付费", "智能门禁", "淋浴", "储物柜"]
    },
    {
        "id": 10, "name": "顺丰快递(科技园营业部)", "category": "service",
        "icon": "📦", "distance": 0.7, "address": "南山区科技路15号",
        "rating": 4.3, "review_count": 1200,
        "open_status": "营业中", "hours": "08:00-20:00",
        "tags": ["快递", "寄件", "收件"],
        "phone": "95338",
        "features": ["上门取件", "自助寄件柜", "包装服务"]
    },
    {
        "id": 11, "name": "万象天地", "category": "market",
        "icon": "🏬", "distance": 3.2, "address": "南山区深南大道9668号",
        "rating": 4.7, "review_count": 21000,
        "open_status": "营业中", "hours": "10:00-22:00",
        "tags": ["购物中心", "网红打卡", "美食广场"],
        "phone": "0755-8668-6666",
        "features": ["停车场", "母婴室", "充电桩", "导购服务"]
    },
    {
        "id": 12, "name": "深圳湾体育中心", "category": "entertainment",
        "icon": "🏟️", "distance": 2.9, "address": "南山区滨海大道3001号",
        "rating": 4.5, "review_count": 8400,
        "open_status": "营业中", "hours": "06:00-22:00",
        "tags": ["体育", "游泳", "羽毛球", "健身"],
        "phone": "0755-8628-9999",
        "features": ["游泳馆", "羽毛球馆", "健身房", "停车场"]
    },
]

# 周边资源近似坐标（深圳南山各点，用于基于用户真实位置的 haversine 距离计算）
_RESOURCE_COORDS = {
    1: (22.5226, 113.9350),   # 海岸城购物中心
    2: (22.4820, 113.9500),   # 深圳湾公园
    3: (22.5310, 113.9300),   # 协和深圳医院
    4: (22.5190, 113.9290),   # 招商银行南山支行
    5: (22.5330, 113.9250),   # 深圳图书馆南山分馆
    6: (22.5400, 113.9450),   # 盒马鲜生南山店
    7: (22.5226, 113.9350),   # 海底捞海岸城店
    8: (22.5100, 113.9500),   # 地铁2号线科苑站
    9: (22.5400, 113.9460),   # 超级猩猩科技园店
    10: (22.5410, 113.9440),  # 顺丰科技园营业部
    11: (22.5450, 113.9600),  # 万象天地
    12: (22.4800, 113.9550),  # 深圳湾体育中心
}
for _r in nearby_resources:
    _c = _RESOURCE_COORDS.get(_r["id"])
    if _c:
        _r.setdefault("lat", _c[0])
        _r.setdefault("lng", _c[1])

# ========== 新闻资讯数据 ==========
news_categories = [
    {"id": "all", "name": "推荐", "icon": "⭐"},
    {"id": "local", "name": "本地", "icon": "📍"},
    {"id": "tech", "name": "科技", "icon": "💻"},
    {"id": "finance", "name": "财经", "icon": "📈"},
    {"id": "life", "name": "生活", "icon": "🏠"},
    {"id": "health", "name": "健康", "icon": "❤️"},
]

news_articles = [
    {
        "id": 1, "category": "local",
        "title": "深圳地铁13号线一期工程预计年底开通，南山到宝安仅需20分钟",
        "summary": "深圳地铁13号线一期工程目前已完成90%的轨道铺设工作，预计今年12月正式开通运营。届时从南山到宝安的通勤时间将缩短至20分钟以内。",
        "source": "深圳新闻网", "author": "陈记者",
        "published_at": "2026-07-29T08:30:00",
        "image": "🚇",
        "tags": ["交通", "地铁", "民生"],
        "read_count": 15000,
        "trending": True
    },
    {
        "id": 2, "category": "tech",
        "title": "华为发布最新鸿蒙5.0系统，全场景分布式能力再升级",
        "summary": "华为今日正式发布鸿蒙5.0操作系统，新系统在AI能力、跨设备协同、安全隐私等方面实现了重大突破，已适配超过200款智能设备。",
        "source": "科技日报", "author": "李编辑",
        "published_at": "2026-07-29T07:15:00",
        "image": "📱",
        "tags": ["华为", "鸿蒙", "操作系统", "AI"],
        "read_count": 32000,
        "trending": True
    },
    {
        "id": 3, "category": "local",
        "title": "南山区发放新一轮消费券，覆盖餐饮、零售、文旅三大领域",
        "summary": "南山区政府宣布从7月30日起发放总额5000万元的消费券，可在辖区内2000余家商户使用，单笔最高可减200元。",
        "source": "南山日报", "author": "王记者",
        "published_at": "2026-07-29T06:45:00",
        "image": "🎫",
        "tags": ["消费券", "民生", "南山"],
        "read_count": 28000,
        "trending": True
    },
    {
        "id": 4, "category": "finance",
        "title": "央行宣布降准0.25个百分点，释放长期流动性约6000亿元",
        "summary": "中国人民银行决定自2026年8月15日起下调金融机构存款准备金率0.25个百分点，此次降准将有效降低社会融资成本，支持实体经济发展。",
        "source": "财经网", "author": "张分析师",
        "published_at": "2026-07-28T16:00:00",
        "image": "📊",
        "tags": ["央行", "降准", "金融"],
        "read_count": 45000,
        "trending": True
    },
    {
        "id": 5, "category": "life",
        "title": "夏季高温防暑攻略：这5种食物最解暑，第3种你可能没想到",
        "summary": "夏季高温来袭，除了空调和冷饮，饮食调节也是防暑的关键。营养师推荐西瓜、绿豆、冬瓜、苦瓜和薄荷这5种天然解暑食材。",
        "source": "健康生活", "author": "刘营养师",
        "published_at": "2026-07-28T14:20:00",
        "image": "🍉",
        "tags": ["健康", "饮食", "夏季"],
        "read_count": 52000,
        "trending": True
    },
    {
        "id": 6, "category": "tech",
        "title": "深圳AI产业规模突破8000亿，大模型企业数量位居全国第一",
        "summary": "据统计，深圳市人工智能产业规模已突破8000亿元，拥有超过3000家AI相关企业，其中大模型领域企业数量占全国总数的35%，位居全国首位。",
        "source": "深圳特区报", "author": "赵记者",
        "published_at": "2026-07-28T11:00:00",
        "image": "🤖",
        "tags": ["AI", "深圳", "产业"],
        "read_count": 18000,
        "trending": False
    },
    {
        "id": 7, "category": "health",
        "title": "国家卫健委发布新版居民膳食指南，建议每日饮奶300-500ml",
        "summary": "新版《中国居民膳食指南(2026)》正式发布，首次将饮奶量建议从300ml提高至300-500ml，同时强调了全谷物摄入和减盐减油的重要性。",
        "source": "健康报", "author": "孙医生",
        "published_at": "2026-07-28T09:30:00",
        "image": "🥗",
        "tags": ["健康", "饮食", "指南"],
        "read_count": 35000,
        "trending": False
    },
    {
        "id": 8, "category": "local",
        "title": "深圳湾超级总部基地新地标封顶，将成为深圳第一高楼",
        "summary": "深圳湾超级总部基地核心建筑今日完成主体结构封顶，建筑高度达498米，建成后将成为深圳新的城市地标和第一高楼。",
        "source": "深圳晚报", "author": "周记者",
        "published_at": "2026-07-27T15:45:00",
        "image": "🏗️",
        "tags": ["建筑", "深圳湾", "地标"],
        "read_count": 22000,
        "trending": False
    },
    {
        "id": 9, "category": "finance",
        "title": "A股三大指数全线上涨，半导体板块领涨大盘",
        "summary": "今日A股市场表现强势，沪指涨1.2%，深成指涨1.8%，创业板指涨2.5%。半导体、AI概念、新能源板块涨幅居前，市场成交额突破1.2万亿元。",
        "source": "证券时报", "author": "林编辑",
        "published_at": "2026-07-27T15:00:00",
        "image": "📈",
        "tags": ["A股", "半导体", "AI"],
        "read_count": 40000,
        "trending": False
    },
    {
        "id": 10, "category": "life",
        "title": "深圳8月文化活动汇总：音乐节、艺术展、话剧演出精彩纷呈",
        "summary": "8月深圳将迎来丰富多彩的文化活动，包括深圳湾音乐节、当代艺术博物馆新展、《哈姆雷特》话剧巡演等，为市民提供多元化的文化体验。",
        "source": "深圳文娱", "author": "吴编辑",
        "published_at": "2026-07-27T10:30:00",
        "image": "🎭",
        "tags": ["文化", "演出", "展览"],
        "read_count": 9500,
        "trending": False
    },
    {
        "id": 11, "category": "tech",
        "title": "比亚迪发布第二代刀片电池，续航突破1000公里",
        "summary": "比亚迪今日发布第二代刀片电池技术，能量密度提升40%，支持整车续航突破1000公里，同时将充电时间缩短至15分钟(10%-80%)。",
        "source": "新能源汽车报", "author": "郑记者",
        "published_at": "2026-07-26T14:00:00",
        "image": "🔋",
        "tags": ["新能源", "电池", "比亚迪"],
        "read_count": 55000,
        "trending": False
    },
    {
        "id": 12, "category": "health",
        "title": "夏季游泳安全提醒：这4个泳池安全隐患要注意",
        "summary": "随着夏季游泳人数增多，泳池安全问题再次引发关注。专家提醒要注意水质卫生、防滑防摔、儿童看护以及游泳后的个人清洁消毒。",
        "source": "健康时报", "author": "马医师",
        "published_at": "2026-07-26T08:00:00",
        "image": "🏊",
        "tags": ["游泳", "安全", "夏季"],
        "read_count": 12000,
        "trending": False
    },
]

# ========== 仪表盘数据 ==========
dashboard_stats = {
    "price_saved_today": 86.5,
    "price_saved_this_month": 1280.3,
    "nearby_places": 128,
    "unread_news": 15,
    "active_alerts": 3,
}

price_alerts = [
    {"id": 1, "product": "智利车厘子", "target_price": 180, "current_best": 189, "store": "美团优选", "status": "watching"},
    {"id": 2, "product": "五常大米 5kg", "target_price": 45, "current_best": 49.9, "store": "美团优选", "status": "watching"},
    {"id": 3, "product": "善存多维维生素", "target_price": 140, "current_best": 149, "store": "美团优选", "status": "watching"},
]

quick_actions = [
    {"id": "scan_price", "name": "扫码比价", "icon": "📷", "color": "bg-blue-500"},
    {"id": "nearby", "name": "周边探索", "icon": "🗺️", "color": "bg-green-500"},
    {"id": "news", "name": "今日资讯", "icon": "📰", "color": "bg-purple-500"},
    {"id": "weather", "name": "天气预报", "icon": "🌤️", "color": "bg-orange-500"},
    {"id": "alert", "name": "价格提醒", "icon": "🔔", "color": "bg-red-500"},
    {"id": "favorite", "name": "我的收藏", "icon": "⭐", "color": "bg-yellow-500"},
]
