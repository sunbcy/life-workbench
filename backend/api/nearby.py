"""周边资源 API 路由"""
from fastapi import APIRouter, Query
from services import create_nearby_service, geolocation
from services.recommendation import get_engine

router = APIRouter(prefix="/api/nearby", tags=["周边资源"])

nearby_service = create_nearby_service()


@router.get("/categories")
async def get_categories():
    """获取周边资源分类"""
    data = await nearby_service.get_categories()
    return {"code": 0, "data": data}


@router.get("/resources")
async def get_resources(
    category: str = Query("all", description="分类ID"),
    keyword: str = Query("", description="搜索关键词"),
    sort: str = Query("distance", description="排序: distance / rating / popularity"),
    radius: float = Query(3.0, description="搜索半径(公里)"),
    personalized: bool = Query(True, description="是否启用个性化推荐"),
):
    """获取周边资源列表（基于用户真实位置计算距离，含个性化推荐评分）"""
    result = await nearby_service.get_resources(
        category=category, keyword=keyword, sort=sort, radius=radius
    )
    resources = result["resources"]
    resource_crs = result.get("resource_crs", "wgs84")

    # 用用户真实位置重算距离
    # resource_crs 标记资源坐标坐标系(高德=gcj02/百度=bd09/mock=wgs84)，
    # 据此把用户 WGS-84 坐标对齐后再算距，消除跨坐标系偏移。
    geolocation.apply_real_distance(resources, resource_crs=resource_crs)

    # 按指定半径过滤
    filtered = [r for r in resources if r["distance"] <= radius]

    # 兜底：真实 API 无数据时 mock 资源的坐标可能远离用户当前位置
    # 若过滤后为空，放宽距离限制（按距离排序取前 N 条），保证页面有内容
    if not filtered and resources:
        resources.sort(key=lambda r: r["distance"])
        resources = resources[:12]  # 取最近的 12 条
    else:
        resources = filtered

    if sort == "distance":
        resources.sort(key=lambda r: r["distance"])
    elif sort == "rating":
        resources.sort(key=lambda r: r["rating"], reverse=True)
    elif sort == "popularity":
        resources.sort(key=lambda r: r["review_count"], reverse=True)

    if personalized and resources:
        engine = get_engine()
        resources = engine.recommend(resources, "nearby")

    return {
        "code": 0,
        "data": resources,
        "total": len(resources),
        "location": geolocation.get_location(),
    }


@router.get("/resources/{resource_id}")
async def get_resource_detail(resource_id: int):
    """获取资源详情"""
    detail = await nearby_service.get_resource_detail(resource_id)
    if detail:
        return {"code": 0, "data": detail}
    return {"code": 404, "message": "资源不存在"}
