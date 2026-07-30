"""周边资源 API 路由"""
from fastapi import APIRouter, Query
from services import create_nearby_service
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
    radius: float = Query(5.0, description="搜索半径(公里)"),
    personalized: bool = Query(True, description="是否启用个性化推荐"),
):
    """获取周边资源列表（含个性化推荐评分）"""
    result = await nearby_service.get_resources(
        category=category, keyword=keyword, sort=sort, radius=radius
    )
    resources = result["resources"]
    if personalized and resources:
        engine = get_engine()
        resources = engine.recommend(resources, "nearby")
    return {"code": 0, "data": resources, "total": result["total"]}


@router.get("/resources/{resource_id}")
async def get_resource_detail(resource_id: int):
    """获取资源详情"""
    detail = await nearby_service.get_resource_detail(resource_id)
    if detail:
        return {"code": 0, "data": detail}
    return {"code": 404, "message": "资源不存在"}
