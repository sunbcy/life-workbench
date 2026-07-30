"""
天气服务 - Mock 实现 + 和风天气 (QWeather) 真实 API 实现
"""

import logging
from datetime import datetime

log = logging.getLogger(__name__)


# ============================================================
# Mock 天气服务
# ============================================================

class MockWeatherService:
    """使用内置 mock 数据"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def get_current(self) -> dict:
        from api.data import weather_data
        return weather_data["current"]

    async def get_forecast(self) -> list[dict]:
        from api.data import weather_data
        return weather_data["forecast"]

    async def get_alerts(self) -> list[dict]:
        from api.data import weather_data
        return weather_data["alerts"]

    async def get_full(self) -> dict:
        from api.data import weather_data
        return weather_data


# ============================================================
# 和风天气 (QWeather) 真实 API 服务
# ============================================================

QWATHER_BASE = "https://devapi.qweather.com/v7"

# 和风天气 condition code → 中文映射
CONDITION_MAP = {
    "100": "晴", "101": "多云", "102": "少云", "103": "晴间多云",
    "104": "阴",
    "300": "阵雨", "301": "强阵雨", "302": "雷阵雨", "303": "强雷阵雨",
    "304": "雷阵雨伴有冰雹", "305": "小雨", "306": "中雨", "307": "大雨",
    "308": "极端降雨", "309": "毛毛雨/细雨", "310": "暴雨", "311": "大暴雨",
    "312": "特大暴雨", "313": "冻雨", "314": "小到中雨", "315": "中到大雨",
    "316": "大到暴雨", "317": "暴雨到大暴雨", "318": "大暴雨到特大暴雨",
    "399": "雨",
    "400": "小雪", "401": "中雪", "402": "大雪", "403": "暴雪",
    "404": "雨夹雪", "405": "雨雪天气", "406": "阵雨夹雪", "407": "阵雪",
    "408": "小到中雪", "409": "中到大雪", "410": "大到暴雪", "499": "雪",
    "500": "薄雾", "501": "雾", "502": "霾", "503": "扬沙", "504": "浮尘",
    "507": "沙尘暴", "508": "强沙尘暴", "509": "浓雾", "510": "强浓雾",
    "511": "中度霾", "512": "重度霾", "513": "严重霾", "514": "大雾",
    "515": "特强浓雾",
    "900": "热", "901": "冷", "999": "未知",
}

# 和风天气 icon → 本地 icon 映射
ICON_MAP = {
    "100": "sunny", "101": "cloudy", "102": "partly-cloudy", "103": "partly-cloudy",
    "104": "cloudy",
    "300": "shower", "301": "shower", "302": "thunderstorm", "303": "thunderstorm",
    "304": "thunderstorm", "305": "rainy", "306": "rainy", "307": "rainy",
    "308": "rainy", "309": "rainy", "310": "rainy", "311": "rainy",
    "312": "rainy", "313": "rainy", "314": "rainy", "315": "rainy",
    "316": "rainy", "317": "rainy", "318": "rainy", "399": "rainy",
    "400": "snowy", "401": "snowy", "402": "snowy", "403": "snowy",
    "404": "snowy", "405": "snowy", "406": "snowy", "407": "snowy",
    "408": "snowy", "409": "snowy", "410": "snowy", "499": "snowy",
    "500": "cloudy", "501": "cloudy", "502": "cloudy", "503": "cloudy",
    "504": "cloudy", "507": "cloudy", "508": "cloudy", "509": "cloudy",
    "510": "cloudy", "511": "cloudy", "512": "cloudy", "513": "cloudy",
    "514": "cloudy", "515": "cloudy",
    "900": "sunny", "901": "snowy", "999": "cloudy",
}


class QWeatherService:
    """和风天气 API v7 实现"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.location_id = self.config.get("location_id", "101280604")

    @property
    def _params(self) -> dict:
        return {"location": self.location_id, "key": self.api_key}

    async def _fetch(self, endpoint: str) -> dict:
        """调用和风天气 API"""
        import httpx
        url = f"{QWATHER_BASE}/{endpoint}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=self._params)
            resp.raise_for_status()
            return resp.json()

    async def get_current(self) -> dict:
        """获取当前天气"""
        try:
            data = await self._fetch("weather/now")
            now = data["now"]
            return {
                "temperature": int(now["temp"]),
                "feels_like": int(now["feelsLike"]),
                "humidity": int(now["humidity"]),
                "condition": CONDITION_MAP.get(now.get("icon", ""), now.get("text", "未知")),
                "icon": ICON_MAP.get(now.get("icon", ""), "cloudy"),
                "wind_speed": int(now.get("windSpeed", 0)),
                "wind_direction": now.get("windDir", "未知"),
                "uv_index": 0,  # 和风 now API 不含 UV，需单独调用
                "visibility": int(now.get("vis", "10")),
                "aqi": 0,  # 需单独调用 air/v7/now
                "aqi_level": "未知",
            }
        except Exception as e:
            log.warning(f"和风天气 API 调用失败，回退到 mock: {e}")
            return await MockWeatherService().get_current()

    async def get_forecast(self) -> list[dict]:
        """获取7天预报"""
        try:
            data = await self._fetch("weather/7d")
            forecast = []
            for day in data.get("daily", []):
                forecast.append({
                    "day": _fmt_day(day.get("fxDate", "")),
                    "high": int(day["tempMax"]),
                    "low": int(day["tempMin"]),
                    "condition": CONDITION_MAP.get(day.get("iconDay", ""), day.get("textDay", "未知")),
                    "icon": ICON_MAP.get(day.get("iconDay", ""), "cloudy"),
                    "rain_prob": int(day.get("pop", 0) or 0),
                })
            return forecast
        except Exception as e:
            log.warning(f"和风天气预报 API 失败，回退到 mock: {e}")
            return await MockWeatherService().get_forecast()

    async def get_alerts(self) -> list[dict]:
        """获取天气预警"""
        try:
            data = await self._fetch("warning/now")
            alerts = []
            for w in data.get("warning", []):
                alerts.append({
                    "level": w.get("severity", "未知"),
                    "type": w.get("typeName", "未知"),
                    "message": w.get("text", ""),
                })
            return alerts if alerts else [{"level": "正常", "type": "无预警", "message": "当前无气象预警"}]
        except Exception as e:
            log.warning(f"和风天气预警 API 失败，回退到 mock: {e}")
            return await MockWeatherService().get_alerts()

    async def get_full(self) -> dict:
        """获取完整天气信息"""
        current = await self.get_current()
        forecast = await self.get_forecast()
        alerts = await self.get_alerts()
        return {
            "current": current,
            "forecast": forecast,
            "alerts": alerts,
        }


def _fmt_day(date_str: str) -> str:
    """将 2026-07-30 转为 '今天'/'明天'/'后天'/周X"""
    if not date_str:
        return ""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().date()
        delta = (d.date() - today).days
        if delta == 0:
            return "今天"
        elif delta == 1:
            return "明天"
        elif delta == 2:
            return "后天"
        else:
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return weekdays[d.weekday()]
    except (ValueError, AttributeError):
        return date_str
