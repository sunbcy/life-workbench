"""
Termux / Android 原生定位适配层

在 Android Termux 环境中通过多种策略获取实时位置：
  1. termux-location (Termux:API) — 调用 Android GPS/网络定位，秒级精度
  2. Android dumpsys location — 读取系统缓存的最后已知位置
  3. IP 网络定位 — 免费 HTTP API 兜底

PC / 非 Android 环境会自动跳过 Android 专用方法，直接走 IP 定位。
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Optional

log = logging.getLogger(__name__)


# ----------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------

def _run(cmd: list[str], timeout: float = 8.0) -> tuple[int, str, str]:
    """运行命令，返回 (returncode, stdout, stderr)"""
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -2, "", "timeout"
    except Exception as e:
        return -3, "", str(e)


def _is_android() -> bool:
    """检测是否运行在 Android / Termux 环境"""
    import os
    # Termux 特征：有 /data/data/com.termux 路径且有 termux-setup-storage 等
    home = os.path.expanduser("~")
    return (
        "com.termux" in home
        or os.path.isdir("/data/data/com.termux")
        or "ANDROID_ROOT" in os.environ
        or "ANDROID_DATA" in os.environ
    )


# ----------------------------------------------------------------
# Termux:API 定位 — 需要安装 pkg install termux-api
# ----------------------------------------------------------------

def _termux_location(timeout: float = 10.0) -> Optional[dict]:
    """通过 termux-location 获取 GPS 坐标

    返回:
        {"lat": 22.5431, "lng": 113.9298, "accuracy": 15.0,
         "provider": "gps", "source": "termux-gps"} 或 None
    """
    rc, stdout, stderr = _run(
        ["termux-location"],
        timeout=timeout,
    )
    if rc != 0:
        if rc == -1:
            log.debug("termux-location 未安装，跳过 GPS 定位")
        else:
            log.debug(
                "termux-location 失败 (rc=%d): %s",
                rc,
                stderr[:200] if stderr else "(无输出)",
            )
        return None

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        log.warning("termux-location 返回非 JSON: %s", stdout[:200])
        return None

    lat = data.get("latitude")
    lng = data.get("longitude")
    if lat is None or lng is None:
        log.debug("termux-location 返回无有效坐标: %s", list(data.keys())[:5])
        return None

    provider = data.get("provider", "unknown")
    accuracy = data.get("accuracy")

    log.info(
        "Termux GPS 定位成功: %.5f, %.5f (provider=%s, accuracy=%s)",
        lat, lng, provider, accuracy,
    )
    return {
        "lat": float(lat),
        "lng": float(lng),
        "accuracy": float(accuracy) if accuracy is not None else None,
        "provider": provider,
        "source": "termux-gps",
    }


# ----------------------------------------------------------------
# Android dumpsys 定位 — 读取系统最后已知位置（无需额外权限）
# ----------------------------------------------------------------

def _dumpsys_location() -> Optional[dict]:
    """通过 `dumpsys location` 解析 Android 系统缓存位置

    优势: 不需要安装 Termux:API，不需要前台 GPS 请求。
    局限: 精度可能较低（网络定位），且坐标可能是很久之前的。
    """
    # Android 上 dumpsys 在 /system/bin，通常不在 Termux PATH 中
    rc, stdout, stderr = _run(
        ["/system/bin/dumpsys", "location"],
        timeout=5.0,
    )
    if rc != 0 or not stdout:
        return None

    # 解析 "Last Known Locations" 块
    # 格式示例:
    #   gps: Location[gps 22.543100,113.929800 hAcc=15.0 ...]
    #   network: Location[network 22.540000,113.930000 hAcc=50.0 ...]

    import re
    # 匹配 Location[provider lat,lng ...] 格式
    pattern = re.compile(
        r"Location\[(\w+)\s+([\d.]+),([\d.]+)\s+.*?hAcc=([\d.]+)"
    )

    best: dict | None = None
    best_acc = float("inf")

    for m in pattern.finditer(stdout):
        provider = m.group(1)
        lat = float(m.group(2))
        lng = float(m.group(3))
        h_acc = float(m.group(4))

        # 过滤异常值 (不在中国大陆范围内)
        if not (18 <= lat <= 54 and 73 <= lng <= 136):
            continue

        # GPS 优先（即使精度稍差），同等 provider 选精度最高
        score = h_acc + (0 if provider == "gps" else 100)
        if score < best_acc:
            best_acc = score
            best = {
                "lat": lat,
                "lng": lng,
                "accuracy": h_acc,
                "provider": provider,
                "source": "android-dumpsys",
            }

    if best:
        log.info(
            "Android dumpsys 定位: %.5f, %.5f (provider=%s, accuracy=%s)",
            best["lat"], best["lng"], best["provider"], best["accuracy"],
        )
    return best


# ----------------------------------------------------------------
# IP 网络定位 — PC 和 Android 通用兜底
# ----------------------------------------------------------------

def _ip_geolocation() -> Optional[dict]:
    """通过网络 IP 获取粗略位置（免费，无需 API Key）

    使用同步 httpx 客户端避免 asyncio 嵌套调用问题。
    """
    import httpx

    urls = [
        "https://ipapi.co/json/",
        "https://ipwhois.app/json/",
        "https://ipinfo.io/json",
    ]

    for url in urls:
        try:
            resp = httpx.get(url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()

            lat = float(data.get("latitude", 0))
            lng = float(data.get("longitude", 0))
            if lat == 0 and lng == 0:
                continue

            result = {
                "lat": lat,
                "lng": lng,
                "accuracy": None,
                "provider": "ip",
                "source": f"ip-{url.split('/')[2]}",
                "city": data.get("city", ""),
                "district": data.get("region", ""),
                "country": data.get("country_name", data.get("country", "")),
            }
            log.info("IP 定位成功: %.5f, %.5f (%s, %s %s)",
                     result["lat"], result["lng"],
                     result["source"], result.get("city", ""), result.get("district", ""))
            return result
        except Exception:
            continue

    return None


# ----------------------------------------------------------------
# 统一入口
# ----------------------------------------------------------------

def detect_location(
    use_gps: bool = True,
    use_network: bool = True,
) -> dict:
    """自动检测当前设备位置，按优先级依次尝试

    Android/Termux:
      1. termux-location (Termux:API GPS)
      2. dumpsys location (Android 系统位置缓存)
      3. IP 网络定位

    PC / 其他:
      直接走 IP 网络定位

    返回:
        {"lat": 22.5431, "lng": 113.9298, "source": "termux-gps",
         "provider": "gps", "city": "深圳", "district": "南山区",
         "accuracy": 15.0}
    """
    if not _is_android():
        log.info("非 Android 环境，使用 IP 网络定位")
        result = _ip_geolocation()
        if result:
            return result
        raise RuntimeError("IP 定位失败，请手动设置位置")

    # Android 环境: 依次尝试
    if use_gps:
        # 1. Termux:API GPS
        gps = _termux_location(timeout=10.0)
        if gps:
            # 逆地理编码获取城市名
            city, district = _reverse_geocode(gps["lat"], gps["lng"])
            gps["city"] = city
            gps["district"] = district
            return gps

        # 2. Android dumpsys
        sys_loc = _dumpsys_location()
        if sys_loc:
            city, district = _reverse_geocode(sys_loc["lat"], sys_loc["lng"])
            sys_loc["city"] = city
            sys_loc["district"] = district
            return sys_loc

    # 3. IP 兜底
    if use_network:
        ip = _ip_geolocation()
        if ip:
            return ip

    raise RuntimeError(
        "无法获取位置。请检查:\n"
        "  - Termux: pkg install termux-api && termux-location\n"
        "  - 或授予 Termux 定位权限 (Android 设置 → 应用 → Termux → 权限)\n"
        "  - 或手动在 config.yaml 中设置默认位置"
    )


# ----------------------------------------------------------------
# 逆地理编码 (坐标 → 地址)
# ----------------------------------------------------------------

def _reverse_geocode(lat: float, lng: float) -> tuple[str, str]:
    """坐标转城市/区县名

    依次尝试多个逆地理服务，避免单点网络故障导致返回空值。
    """
    import urllib.request
    import urllib.error

    # 方案 1: Nominatim (OpenStreetMap, 免费, 精度最高)
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?format=jsonv2&lat={lat}&lon={lng}&accept-language=zh-CN"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "LifeWorkbench/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        addr = data.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("county") or addr.get("state") or ""
        district = addr.get("suburb") or addr.get("city_district") or addr.get("county") or addr.get("district") or ""
        if city or district:
            log.info("逆地理(Nominatim): %s, %s → %s · %s", lat, lng, city, district)
            return city, district
    except Exception as e:
        log.debug("逆地理 Nominatim 失败: %s", e)

    # 方案 2: 坐标范围硬匹配（深圳各行政区大致范围，作为最终兜底）
    city, district = _shenzhen_district_match(lat, lng)
    if city:
        log.info("逆地理(坐标匹配): %s, %s → %s · %s", lat, lng, city, district)
    return city, district


def _shenzhen_district_match(lat: float, lng: float) -> tuple[str, str]:
    """深圳行政区坐标范围粗略匹配

    各行政区大致经纬度范围（矩形近似）：
      南山区: 22.47-22.57N, 113.87-114.05E
      福田区: 22.50-22.57N, 114.03-114.10E
      罗湖区: 22.53-22.58N, 114.10-114.15E
      宝安区: 22.52-22.83N, 113.77-113.93E
      龙华区: 22.60-22.74N, 113.93-114.08E
      龙岗区: 22.57-22.84N, 114.08-114.39E
      光明区: 22.74-22.83N, 113.85-114.00E
      坪山区: 22.65-22.79N, 114.30-114.43E
      盐田区: 22.54-22.61N, 114.20-114.30E
    """
    # 中国大陆范围检查
    if not (18 <= lat <= 54 and 73 <= lng <= 136):
        return "", ""

    districts = [
        ("南山区", 22.47, 22.57, 113.87, 114.05),
        ("福田区", 22.50, 22.57, 114.03, 114.10),
        ("罗湖区", 22.53, 22.58, 114.10, 114.15),
        ("宝安区", 22.52, 22.83, 113.77, 113.93),
        ("龙华区", 22.60, 22.74, 113.93, 114.08),
        ("龙岗区", 22.57, 22.84, 114.08, 114.39),
        ("光明区", 22.74, 22.83, 113.85, 114.00),
        ("坪山区", 22.65, 22.79, 114.30, 114.43),
        ("盐田区", 22.54, 22.61, 114.20, 114.30),
    ]

    for name, lat_min, lat_max, lng_min, lng_max in districts:
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            return "深圳", name

    # 深圳范围大致判断（不精确到区）
    if 22.45 <= lat <= 22.85 and 113.75 <= lng <= 114.45:
        return "深圳", ""

    return "", ""
