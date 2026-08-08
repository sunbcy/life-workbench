"""天气 API 路由"""
import logging
from fastapi import APIRouter
from services import create_weather_service, geolocation

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weather", tags=["天气"])

# 服务实例（模块加载时创建，通过重启或 reload_config 切换数据源）
weather_service = create_weather_service()


def _apply_real_location() -> None:
    """将实时定位（设备/网络/IP 上报）传入天气服务，覆盖配置里的固定 LocationID。

    前端会经 POST /api/location 上报真实经纬度，geolocation 服务据此维护当前位置；
    此处把它同步给天气服务，使天气随真实位置变化。
    """
    loc = geolocation.get_location()
    lat = loc.get("lat")
    lng = loc.get("lng")
    if lat is not None and lng is not None:
        weather_service.set_location(lat, lng)
    if loc.get("city"):
        weather_service.set_place_name(loc.get("city"), loc.get("district"))


@router.get("/current")
async def get_current_weather():
    """获取当前天气（基于真实定位位置）"""
    log.info("天气请求: current")
    _apply_real_location()
    data = await weather_service.get_current()
    return {"code": 0, "data": data}


@router.get("/forecast")
async def get_forecast():
    """获取天气预报（基于真实定位位置）"""
    log.info("天气请求: forecast")
    _apply_real_location()
    data = await weather_service.get_forecast()
    return {"code": 0, "data": data}


@router.get("/alerts")
async def get_alerts():
    """获取天气预警（基于真实定位位置）"""
    log.info("天气请求: alerts")
    _apply_real_location()
    data = await weather_service.get_alerts()
    return {"code": 0, "data": data}


@router.get("/full")
async def get_full_weather():
    """获取完整天气信息（基于真实定位位置）"""
    log.info("天气请求: full")
    _apply_real_location()
    data = await weather_service.get_full()
    return {"code": 0, "data": data}
