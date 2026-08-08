"""比价 API 路由"""
import logging
from fastapi import APIRouter, Query
from services import create_price_service
from services.recommendation import get_engine

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/price", tags=["比价"])

price_service = create_price_service()


@router.get("/categories")
async def get_categories():
    """获取商品分类列表"""
    log.info("比价请求: categories")
    data = await price_service.get_categories()
    return {"code": 0, "data": data}


@router.get("/stores")
async def get_stores():
    """获取比价商家列表"""
    log.info("比价请求: stores")
    data = await price_service.get_stores()
    return {"code": 0, "data": data}


@router.get("/products")
async def get_products(
    category: str = Query("all", description="分类ID"),
    keyword: str = Query("", description="搜索关键词"),
    sort: str = Query("default", description="排序方式: default / price_asc / price_desc / discount"),
    personalized: bool = Query(True, description="是否启用个性化推荐"),
):
    """获取比价商品列表（含个性化推荐评分）"""
    log.info("比价请求: products category=%s keyword=%s sort=%s", category, keyword, sort)
    result = await price_service.get_products(category=category, keyword=keyword, sort=sort)
    products = result["products"]
    if personalized and products:
        engine = get_engine()
        products = engine.recommend(products, "product")
    return {"code": 0, "data": products, "total": result["total"]}


@router.get("/products/{product_id}")
async def get_product_detail(product_id: int):
    """获取商品详情及所有商家价格"""
    log.info("比价请求: product_detail id=%s", product_id)
    detail = await price_service.get_product_detail(product_id)
    if detail:
        return {"code": 0, "data": detail}
    return {"code": 404, "message": "商品不存在"}


@router.get("/alerts")
async def get_price_alerts():
    """获取价格提醒列表"""
    log.info("比价请求: alerts")
    data = await price_service.get_alerts()
    return {"code": 0, "data": data}
