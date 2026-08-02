"""
天气服务 - Mock 实现 + 和风天气 (QWeather) 真实 API 实现
"""

import logging
import traceback as _traceback
import json as _json
from datetime import datetime

log = logging.getLogger(__name__)

# 可通过环境变量开启调试模式（打印完整请求/响应）
DEBUG = False  # 设为 True 可在成功时也打印请求详情


# ============================================================
# Mock 天气服务
# ============================================================

class MockWeatherService:
    """使用内置 mock 数据"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def set_location(self, lat: float, lng: float) -> None:
        """接收实时经纬度（mock 模式下不实际查询，仅记录）"""
        self._lat = lat
        self._lng = lng

    def set_place_name(self, city: str | None, district: str | None = None) -> None:
        """接收实时地名（mock 模式下不实际查询，仅记录）"""
        self._city = city
        self._district = district

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
# 和风天气 (QWeather) 真实 API 服务 — 支持 JWT + API Key 双模式
# ============================================================

import time as _time
from services._qweather_jwt import qweather_jwt as _qweather_jwt

# 默认 API 基地址（和风天气可能为每个开发者分配独立 host）
QWATHER_DEFAULT_HOST = "https://devapi.qweather.com/v7"

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


class QWeatherError(Exception):
    """和风天气 API 错误基类"""


class QWeatherPermissionError(QWeatherError):
    """订阅权限不足 (403 No permission) — 当前套餐不含此端点"""


def _safe_json_or_text(data: bytes | str) -> str:
    """尝试将响应体解析为 JSON 并格式化，失败则返回原始文本"""
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            return f"<binary {len(data)} bytes>"
    else:
        text = str(data)
    try:
        obj = _json.loads(text)
        return _json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return text[:2000]  # 截断过长文本


def _format_traceback(exc: Exception, *, prefix: str = "") -> str:
    """格式化异常信息，包含完整调用栈"""
    tb_lines = _traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_text = "".join(tb_lines).rstrip()
    if prefix:
        tb_text = f"{prefix}\n{tb_text}"
    return tb_text


class QWeatherService:
    """和风天气 API v7 实现
    支持两种认证方式：
      - JWT (推荐): Ed25519 签名, Authorization: Bearer <token>
      - API Key (旧): URL 参数 ?key=xxx 或 X-QW-Api-Key 头
    当 api_key 为空且配置了 private_key 时自动使用 JWT。
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.location_id = self.config.get("location_id", "101280604")
        # 实时经纬度：由前端设备/网络定位上报后写入，覆盖固定 location_id
        self._lat: float | None = None
        self._lng: float | None = None
        self._city: str | None = None
        self._district: str | None = None


        # JWT 配置
        self._use_jwt = False
        self._jwt_token: str | None = None
        self._jwt_expiry: float = 0

        auth_method = self.config.get("auth_method", "")
        self._project_id = self.config.get("project_id", "")
        self._credential_id = self.config.get("credential_id", "")
        self._private_key = self.config.get("private_key", "").strip()
        self._api_host = self.config.get("api_host", "").strip()

        # 判断认证方式: 显式 jwt 或 有私钥但无 api_key
        if auth_method == "jwt" or (self._private_key and not self.api_key):
            if self._private_key and self._project_id and self._credential_id:
                self._use_jwt = True
                log.info("QWeather 使用 JWT 认证 (Ed25519)")
            else:
                missing = []
                if not self._private_key:
                    missing.append("private_key")
                if not self._project_id:
                    missing.append("project_id")
                if not self._credential_id:
                    missing.append("credential_id")
                log.warning(
                    "QWeather JWT 配置不完整，缺少: %s。回退到 API Key 或 mock",
                    ", ".join(missing),
                )

    def set_location(self, lat: float, lng: float) -> None:
        """写入实时经纬度（来自设备/网络定位），优先于配置中的固定 location_id"""
        self._lat = float(lat)
        self._lng = float(lng)

    def set_place_name(self, city: str | None, district: str | None = None) -> None:
        """写入实时地名（用于日志/展示，不影响查询参数）"""
        self._city = city
        self._district = district

    @property
    def _location_param(self) -> str:
        """和风天气 location 参数：优先使用实时经纬度 (lat,lng)，否则回退配置 location_id"""
        if self._lat is not None and self._lng is not None:
            return f"{self._lat:.4f},{self._lng:.4f}"
        return self.location_id

    @property
    def _base_url(self) -> str:
        """API 基地址: 自定义 host 或默认"""
        if self._api_host:
            host = self._api_host.rstrip("/")
            return f"https://{host}/v7" if "/v7" not in host else f"https://{host}"
        return QWATHER_DEFAULT_HOST

    def _generate_jwt(self) -> str:
        """生成和风天气 JWT Token (Ed25519 签名, 有效期 15 分钟, 纯 Python 实现)"""
        return _qweather_jwt(
            project_id=self._project_id,
            credential_id=self._credential_id,
            private_key_pem=self._private_key,
            ttl=900,
        )

    def _get_jwt(self) -> str:
        """获取有效的 JWT Token（缓存到过期前 60 秒）"""
        now = _time.time()
        if self._jwt_token is None or now > self._jwt_expiry - 60:
            self._jwt_token = self._generate_jwt()
            self._jwt_expiry = now + 900
            log.debug(
                "JWT token 已刷新 (project=%s, cred=%s, expiry=+900s)",
                self._project_id,
                self._credential_id,
            )
        return self._jwt_token

    # ----------------------------------------------------------------
    # 核心请求方法 — 带完整 traceback 和 HTTP 调试日志
    # ----------------------------------------------------------------

    async def _fetch(self, endpoint: str) -> dict:
        """调用和风天气 API，失败时输出完整 traceback + HTTP 请求/响应详情"""
        import httpx

        url = f"{self._base_url}/{endpoint}"
        headers = {}
        location_param = self._location_param
        params = {"location": location_param}

        if self._use_jwt:
            token = self._get_jwt()
            headers["Authorization"] = f"Bearer {token}"
            auth_method = "JWT"
        else:
            params["key"] = self.api_key
            headers["X-QW-Api-Key"] = self.api_key
            auth_method = "API Key"

        # 构建日志用的请求摘要（隐藏敏感信息）
        req_summary = (
            f"GET {url}\n"
            f"  Auth: {auth_method}\n"
            f"  Params: location={location_param}"
            + (f", key={self.api_key[:8]}..." if not self._use_jwt and self.api_key else "")
            + f"\n  Host header target: {url.split('/')[2]}"
        )

        if DEBUG:
            log.info("和风天气请求:\n%s\n  Headers: %s", req_summary, {
                k: (v[:20] + "..." if k == "Authorization" else v)
                for k, v in headers.items()
            })

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params, headers=headers)

            # 成功
            if resp.is_success:
                if DEBUG:
                    body_preview = _safe_json_or_text(resp.content)[:300]
                    log.info(
                        "和风天气响应 [%d]:\n  URL: %s\n  Body: %s",
                        resp.status_code, url, body_preview,
                    )
                return resp.json()

            # ---- HTTP 错误处理 ----

            error_body = _safe_json_or_text(resp.content)

            # 检测「订阅权限不足」403 — 这是预期中的情况，不用 error 级别
            if resp.status_code == 403 and "No permission" in error_body:
                log.info(
                    "和风天气 [%d] 当前订阅不含此端点 (%s)，跳过\n"
                    "  提示: 升级订阅后可获取此数据\n"
                    "  URL: %s",
                    resp.status_code, endpoint, url,
                )
                raise QWeatherPermissionError(
                    f"端点 '{endpoint}' 需要更高订阅等级。"
                    f"详情: {_json.loads(error_body).get('error', {}).get('detail', error_body)}"
                    if error_body.startswith("{") else
                    f"端点 '{endpoint}' 需要更高订阅等级"
                )

            # 其他 HTTP 错误
            log.error(
                "和风天气 API 返回错误 [%d %s]\n"
                "  URL: %s\n"
                "  Auth: %s\n"
                "  Response Headers: %s\n"
                "  Response Body:\n%s",
                resp.status_code, resp.reason_phrase,
                url,
                auth_method,
                dict(resp.headers),
                error_body,
            )
            resp.raise_for_status()

        except QWeatherPermissionError:
            # 权限错误直接向上抛，让调用方决定如何处理
            raise

        except httpx.HTTPStatusError as e:
            # raise_for_status 触发的异常
            log.error(
                "和风天气 HTTP 错误 — 完整 traceback:\n%s\n"
                "请求摘要:\n%s",
                _format_traceback(e),
                req_summary,
            )
            raise

        except (httpx.RequestError, httpx.TimeoutException) as e:
            log.error(
                "和风天气 网络/超时错误 — 完整 traceback:\n%s\n"
                "请求摘要:\n%s",
                _format_traceback(e),
                req_summary,
            )
            raise

        except Exception as e:
            log.error(
                "和风天气 未知错误 — 完整 traceback:\n%s\n"
                "请求摘要:\n%s",
                _format_traceback(e),
                req_summary,
            )
            raise

        # unreachable，满足类型检查
        raise RuntimeError("unreachable")

    # ----------------------------------------------------------------
    # 天气数据获取 — 每个方法带独立 traceback + mock 回退
    # ----------------------------------------------------------------

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
                "uv_index": 0,
                "visibility": int(now.get("vis", "10")),
                "aqi": 0,
                "aqi_level": "未知",
            }
        except Exception as e:
            log.warning(
                "和风天气「实况」获取失败，回退到 mock。Traceback:\n%s",
                _format_traceback(e),
            )
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
            log.warning(
                "和风天气「7天预报」获取失败，回退到 mock。Traceback:\n%s",
                _format_traceback(e),
            )
            return await MockWeatherService().get_forecast()

    async def get_alerts(self) -> list[dict]:
        """获取天气预警

        注意: 预警 API (warning/now) 是付费端点，免费订阅会返回 403。
        此时不显示 mock 数据，而是如实告知用户需要升级订阅。
        """
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
        except QWeatherPermissionError as e:
            log.info("预警功能不可用: %s", e)
            return [{"level": "info", "type": "功能未开通", "message": "天气预警需要升级和风天气订阅套餐"}]
        except Exception as e:
            log.warning(
                "和风天气「预警」获取失败，回退到 mock。Traceback:\n%s",
                _format_traceback(e),
            )
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
