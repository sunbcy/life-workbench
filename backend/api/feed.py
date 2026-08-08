"""个性化推荐流 API 路由"""
import logging
from fastapi import APIRouter, Query
from services.recommendation import get_engine

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feed", tags=["个性化推荐"])


@router.get("/personalized")
async def get_personalized_feed(
    size: int = Query(15, ge=1, le=50, description="返回条数"),
    mix: str = Query("balanced", description="混合策略: balanced / trending / personal"),
):
    """
    统一个性化推荐流 - 混合新闻、商品、周边资源
    按 composite_score 降序排列
    """
    log.info("推荐流请求: size=%s mix=%s", size, mix)
    engine = get_engine()

    # 收集所有类型的内容
    from api.data import news_articles, price_products, nearby_resources

    all_items = []

    # 新闻
    for a in news_articles:
        all_items.append({**a, "_type": "news"})

    # 商品
    for p in price_products:
        all_items.append({**p, "_type": "product"})

    # 周边
    for r in nearby_resources:
        all_items.append({**r, "_type": "nearby"})

    # 个性化评分：一次性计算用户向量后批量打分
    # （逐条 engine.recommend 会把用户画像向量重算 30+ 次，是此接口变慢的主因）
    # 先按用户真实位置重算周边资源的 distance，使地理位置评分基于真实距离
    from services import geolocation
    geolocation.apply_real_distance(all_items)
    engine.score_mixed(all_items)

    # 根据策略调整权重
    for item in all_items:
        rec = item.get("_recommendation", {})
        if mix == "trending":
            # 加重趋势权重
            rec["composite_score"] = round(
                0.2 * rec["relevance_score"] + 0.6 * rec["trending_score"] + 0.2 * rec["freshness_score"], 3
            )
        elif mix == "personal":
            # 加重个人匹配
            rec["composite_score"] = round(
                0.7 * rec["relevance_score"] + 0.15 * rec["trending_score"] + 0.15 * rec["freshness_score"], 3
            )

    # 排序
    all_items.sort(
        key=lambda x: x.get("_recommendation", {}).get("composite_score", 0),
        reverse=True,
    )

    feed = all_items[:size]

    return {
        "code": 0,
        "data": feed,
        "total": len(feed),
        "strategy": mix,
    }
