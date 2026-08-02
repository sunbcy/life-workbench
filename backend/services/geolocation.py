"""
实时定位服务

保存用户「设备 / 网络」的当前位置，并提供基于经纬度的真实距离计算(haversine)。
默认位置来自 config.yaml，前端上报真实坐标后自动覆盖。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from . import get_config

# 默认位置（config.yaml 中的模拟位置）
_cfg = get_config().get("location", {})
_current: dict = {
    "lat": float(_cfg.get("latitude", 22.5431)),
    "lng": float(_cfg.get("longitude", 113.9298)),
    "city": _cfg.get("city", "深圳"),
    "district": _cfg.get("district", "南山区"),
    "source": "config",
}
_updated_at: Optional[str] = None


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """两点间大圆距离(公里)"""
    R = 6371.0088  # 地球平均半径(km)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_location() -> dict:
    return {**_current, "updated_at": _updated_at}


def set_location(
    lat: float,
    lng: float,
    city: Optional[str] = None,
    district: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """更新当前位置（来自设备 GPS 或网络 IP 定位）"""
    global _updated_at
    _current["lat"] = float(lat)
    _current["lng"] = float(lng)
    if city is not None:
        _current["city"] = city
    if district is not None:
        _current["district"] = district
    if source is not None:
        _current["source"] = source
    _updated_at = datetime.now(timezone(timedelta(hours=8))).isoformat()
    return get_location()


def distance_from_current(lat: Optional[float], lng: Optional[float]) -> Optional[float]:
    """从当前位置到指定坐标的距离(公里)；坐标缺失返回 None"""
    if lat is None or lng is None:
        return None
    return haversine(_current["lat"], _current["lng"], float(lat), float(lng))


def apply_real_distance(resources: list[dict], resource_crs: str = "wgs84") -> list[dict]:
    """为带 lat/lng 的周边资源重算真实距离，写回 distance 字段。

    resource_crs: 资源坐标所用坐标系
      - "wgs84" (默认): 与用户坐标同系(设备 GPS)，直接 haversine；
      - "gcj02": 高德/腾讯(火星坐标)，先把用户 WGS-84 当前坐标转为 GCJ-02 再算距；
      - "bd09": 百度坐标，先把用户坐标转 BD-09 再算距。
    这样可消除不同坐标系之间的几十~上百米偏移。
    """
    from .poi.coord import wgs84_to_gcj02, wgs84_to_bd09

    cur_lat, cur_lng = _current["lat"], _current["lng"]
    if resource_crs == "gcj02":
        cur_lat, cur_lng = wgs84_to_gcj02(cur_lat, cur_lng)
    elif resource_crs == "bd09":
        cur_lat, cur_lng = wgs84_to_bd09(cur_lat, cur_lng)

    for r in resources:
        d = distance_between(cur_lat, cur_lng, r.get("lat"), r.get("lng"))
        if d is not None:
            r["distance"] = round(d, 1)
    return resources


def distance_between(lat1: float, lng1: float, lat2: Optional[float], lng2: Optional[float]) -> Optional[float]:
    """从 (lat1,lng1) 到指定坐标的距离(公里)；目标坐标缺失返回 None"""
    if lat2 is None or lng2 is None:
        return None
    return haversine(lat1, lng1, float(lat2), float(lng2))
