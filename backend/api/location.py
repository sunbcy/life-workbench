"""实时定位 API 路由"""
import asyncio
import logging
from fastapi import APIRouter
from pydantic import BaseModel

from services import geolocation

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/location", tags=["定位"])

# 定位相关同步调用总超时（秒）。do_detect 内部最坏串行阻塞可达 10~20s，
# 但绝对不应无限占住线程池。兜底超时后取消等待，避免极端弱网/死锁下
# 线程池被占满、连累其他需要 to_thread 的请求全部排队饿死。
LOCATION_TASK_TIMEOUT = 25.0
REVERSE_GEOCODE_TIMEOUT = 15.0


class LocationIn(BaseModel):
    lat: float
    lng: float
    city: str | None = None
    district: str | None = None
    source: str | None = None  # device(设备GPS) / ip(网络IP) / config(默认)


@router.get("")
async def get_location():
    """获取当前位置（默认来自 config，或由前端上报的真实位置）"""
    log.info("定位请求: get")
    return {"code": 0, "data": geolocation.get_location()}


@router.post("")
async def set_location(body: LocationIn):
    """上报用户真实位置（来自前端设备/网络定位）"""
    log.info("定位请求: set source=%s", body.source)
    loc = geolocation.set_location(
        body.lat, body.lng, body.city, body.district, body.source
    )
    return {"code": 0, "data": loc}


# ========== 后端主动定位（Android Termux / PC） ==========

@router.post("/detect")
async def detect_location():
    """后端自动检测当前设备位置

    Android/Termux 环境:
      依次尝试 termux-location (GPS) → dumpsys location → IP 定位
    PC 环境:
      直接使用 IP 网络定位

    返回定位结果并自动更新 geolocation 模块的当前位置。
    """
    try:
        from services.termux_location import detect_location as do_detect
    except ImportError as e:
        return {"code": 500, "message": f"定位模块加载失败: {e}"}

    try:
        # 关键修复：do_detect 内部是同步阻塞调用
        # (subprocess.run termux-location + 串行 httpx.get + urllib 逆地理编码，
        # 最坏串行阻塞可达 10~20s)。若直接在 asyncio 事件循环里执行，
        # 会卡死整个 worker，使所有请求（含 RSS 抓取）无响应，
        # 在 termux 后台/弱网环境下极易被 Android LMK 杀掉进程。
        # 用 to_thread 把它挪到线程池，事件循环得以继续处理其他请求；
        # 外层再套 wait_for 总超时，防止极端弱网/死锁下线程池被占满饿死其他请求。
        result = await asyncio.wait_for(
            asyncio.to_thread(do_detect, use_gps=True, use_network=True),
            timeout=LOCATION_TASK_TIMEOUT,
        )
    except asyncio.TimeoutError:
        log.warning("后端自动定位超时（%ss）", LOCATION_TASK_TIMEOUT)
        return {"code": 504, "message": "定位超时，请检查网络或定位权限后重试"}
    except Exception as e:
        log.warning("后端自动定位失败: %s", e)
        return {"code": 500, "message": f"定位失败: {e}"}

    # 同步更新 geolocation 模块的当前位置
    # 逆地理编码可能因网络原因失败返回空字符串，此时保留旧地名
    new_city = result.get("city") or None
    new_district = result.get("district") or None

    geolocation.set_location(
        lat=result["lat"],
        lng=result["lng"],
        city=new_city,
        district=new_district,
        source=result.get("source", "backend"),
    )

    log.info("后端自动定位成功: %s %s (source=%s)", new_city, new_district, result.get("source"))
    return {
        "code": 0,
        "data": {
            **result,
            "updated_at": geolocation.get_location()["updated_at"],
        },
    }


class ReverseGeocodeIn(BaseModel):
    lat: float
    lng: float


@router.post("/reverse-geocode")
async def reverse_geocode(body: ReverseGeocodeIn):
    """轻量逆地理编码 — 仅用坐标范围匹配坐标→地名，不触发完整定位流水线

    前端浏览器 GPS 拿到坐标后调此接口纠正区名，避免 Nominatim 返回不准。
    """
    from services.termux_location import _shenzhen_district_match

    city, district = _shenzhen_district_match(body.lat, body.lng)
    if city:
        return {
            "code": 0,
            "data": {"city": city, "district": district, "method": "coordinate-match"},
        }

    # 坐标不在已知范围（非深圳），尝试 Nominatim（urllib 同步网络调用，
    # 同样需用 to_thread 避免阻塞事件循环，并套 wait_for 防止线程池被占满）
    from services.termux_location import _reverse_geocode
    try:
        city, district = await asyncio.wait_for(
            asyncio.to_thread(_reverse_geocode, body.lat, body.lng),
            timeout=REVERSE_GEOCODE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        log.warning("逆地理编码超时（%ss）", REVERSE_GEOCODE_TIMEOUT)
        return {
            "code": 504,
            "data": {"city": "", "district": "", "method": "timeout"},
            "message": "逆地理编码超时",
        }
    except Exception as e:
        log.warning("逆地理编码失败: %s", e)
        return {
            "code": 500,
            "data": {"city": "", "district": "", "method": "error"},
            "message": f"逆地理编码失败: {e}",
        }
    return {
        "code": 0,
        "data": {"city": city or "", "district": district or "", "method": "nominatim" if city else "unknown"},
    }


@router.get("/detect/info")
async def detect_location_info():
    """查看定位环境信息（不实际定位）

    返回:
      - is_android: 是否在 Android/Termux 环境
      - available_methods: 可用的定位方式列表
    """
    from services.termux_location import _is_android, _run

    is_android = _is_android()
    methods = []

    if is_android:
        # 检查 termux-location 是否可用
        rc, _, _ = _run(["which", "termux-location"], timeout=3.0)
        if rc == 0:
            methods.append("termux-gps (Termux:API)")
        else:
            methods.append("termux-gps (需安装: pkg install termux-api)")

        # dumpsys 通常都可用
        rc, _, _ = _run(["which", "dumpsys"], timeout=3.0)
        if rc == 0:
            methods.append("android-dumpsys")

    methods.append("ip-geolocation (网络IP定位)")
    methods.append("config (config.yaml 默认位置)")

    return {
        "code": 0,
        "data": {
            "is_android": is_android,
            "available_methods": methods,
            "current_location": geolocation.get_location(),
        },
    }
