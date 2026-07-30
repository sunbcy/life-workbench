"""
坐标系转换工具

设备 GPS (navigator.geolocation) 返回的是 WGS-84 坐标；
- 高德地图使用 GCJ-02（火星坐标）
- 百度地图使用 BD-09

调用地图 API 前需把 WGS-84 转换为对应坐标系；从 API 拿回的坐标再转回 WGS-84，
以便与用户坐标做统一 haversine 距离计算。
"""
import math

a = 6378245.0                      # 长半轴
ee = 0.00669342162296594323        # 偏心率平方
x_pi = math.pi * 3000.0 / 180.0


def _out_of_china(lat: float, lng: float) -> bool:
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(lng: float, lat: float) -> float:
    ret = (-100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat
           + 0.1 * lng * lat + 0.2 * (lng * lng) ** 0.5)
    ret += (20.0 * math.sin(6.0 * lng * math.pi)
            + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi)
            + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi)
            + 320.0 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng: float, lat: float) -> float:
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * (lng * lng) ** 0.5
    ret += (20.0 * math.sin(6.0 * lng * math.pi)
            + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi)
            + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi)
            + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lat: float, lng: float):
    if _out_of_china(lat, lng):
        return lat, lng
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lat + dlat, lng + dlng


def gcj02_to_wgs84(lat: float, lng: float):
    glat, glng = wgs84_to_gcj02(lat, lng)
    return lat * 2 - glat, lng * 2 - glng


def gcj02_to_bd09(lat: float, lng: float):
    z = (lng * lng + lat * lat) ** 0.5 + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * x_pi)
    return z * math.sin(theta) + 0.006, z * math.cos(theta) + 0.006


def bd09_to_gcj02(lat: float, lng: float):
    x = lng - 0.006
    y = lat - 0.006
    z = (x * x + y * y) ** 0.5 - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gg_lng = z * math.cos(theta)
    gg_lat = z * math.sin(theta)
    return gg_lat, gg_lng


def wgs84_to_bd09(lat: float, lng: float):
    glat, glng = wgs84_to_gcj02(lat, lng)
    return gcj02_to_bd09(glat, glng)


def bd09_to_wgs84(lat: float, lng: float):
    glat, glng = bd09_to_gcj02(lat, lng)
    return gcj02_to_wgs84(glat, glng)
