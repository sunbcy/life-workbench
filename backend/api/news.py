"""新闻资讯 API 路由"""
from fastapi import APIRouter, Query
from services import create_news_service
from services.recommendation import get_engine

router = APIRouter(prefix="/api/news", tags=["新闻资讯"])

news_service = create_news_service()


@router.get("/categories")
async def get_categories():
    """获取新闻分类"""
    data = await news_service.get_categories()
    return {"code": 0, "data": data}


@router.get("/articles")
async def get_articles(
    category: str = Query("all", description="分类ID"),
    keyword: str = Query("", description="搜索关键词"),
    sort: str = Query("latest", description="排序: latest / popular / trending"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    personalized: bool = Query(True, description="是否启用个性化推荐"),
):
    """获取新闻列表（含个性化推荐评分）"""
    result = await news_service.get_articles(
        category=category, keyword=keyword, sort=sort,
        page=page, page_size=page_size
    )
    # 个性化评分
    if personalized and result.get("articles"):
        engine = get_engine()
        result["articles"] = engine.recommend(result["articles"], "news")
    return {
        "code": 0,
        "data": result["articles"],
        "total": result["total"],
        "page": result.get("page", page),
        "page_size": result.get("page_size", page_size),
        "has_more": result.get("has_more", False),
    }


@router.get("/trending")
async def get_trending():
    """获取热门话题"""
    data = await news_service.get_trending()
    return {"code": 0, "data": data}
