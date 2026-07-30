"""天气 API 路由"""
from fastapi import APIRouter
from services import create_weather_service

router = APIRouter(prefix="/api/weather", tags=["天气"])

# 服务实例（模块加载时创建，通过重启或 reload_config 切换数据源）
weather_service = create_weather_service()


@router.get("/current")
async def get_current_weather():
    """获取当前天气"""
    data = await weather_service.get_current()
    return {"code": 0, "data": data}


@router.get("/forecast")
async def get_forecast():
    """获取天气预报"""
    data = await weather_service.get_forecast()
    return {"code": 0, "data": data}


@router.get("/alerts")
async def get_alerts():
    """获取天气预警"""
    data = await weather_service.get_alerts()
    return {"code": 0, "data": data}


@router.get("/full")
async def get_full_weather():
    """获取完整天气信息"""
    data = await weather_service.get_full()
    return {"code": 0, "data": data}
