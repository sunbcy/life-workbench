"""实时定位 API 路由"""
from fastapi import APIRouter
from pydantic import BaseModel

from services import geolocation

router = APIRouter(prefix="/api/location", tags=["定位"])


class LocationIn(BaseModel):
    lat: float
    lng: float
    city: str | None = None
    district: str | None = None
    source: str | None = None  # device(设备GPS) / ip(网络IP) / config(默认)


@router.get("")
async def get_location():
    """获取当前位置（默认来自 config，或由前端上报的真实位置）"""
    return {"code": 0, "data": geolocation.get_location()}


@router.post("")
async def set_location(body: LocationIn):
    """上报用户真实位置（来自前端设备/网络定位）"""
    loc = geolocation.set_location(
        body.lat, body.lng, body.city, body.district, body.source
    )
    return {"code": 0, "data": loc}
