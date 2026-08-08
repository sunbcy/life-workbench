"""新闻资讯 API 路由"""
import logging
import time
from collections import defaultdict, deque
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from services import create_news_service
from services.news_service import MockNewsService
from services.recommendation import get_engine, reload_engine
from services import feedback_store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["新闻资讯"])

news_service = create_news_service()

# ============================================================
# 轻量级内存限流（按客户端 IP，零第三方依赖）
# 滑动窗口：每个 IP 在 WINDOW 秒内最多允许 MAX_REQUESTS 次请求
# ============================================================
_RATE_WINDOW = 60        # 滑动窗口时长（秒）
_RATE_MAX_REQUESTS = 120  # 单 IP 窗口内最大请求数（覆盖正常无限滚动 + 预热的余量）
_RATE_BUCKETS: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    """返回 True 表示触发限流（应拒绝）"""
    now = time.time()
    bucket = _RATE_BUCKETS[ip]
    while bucket and now - bucket[0] > _RATE_WINDOW:  # 清理过期时间戳
        bucket.popleft()
    if not bucket:  # 顺手清理空桶，避免内存无限增长
        _RATE_BUCKETS.pop(ip, None)
    if len(bucket) >= _RATE_MAX_REQUESTS:
        return True
    bucket.append(now)
    return False


# 分页防护常量
MAX_PAGE_SIZE = 50   # 单次返回条数硬上限（集中管理）
MAX_PAGE = 100       # 最大页码，避免翻到天文数字页码


@router.get("/categories")
async def get_categories():
    """获取新闻分类"""
    log.info("新闻请求: categories")
    data = await news_service.get_categories()
    return {"code": 0, "data": data}


@router.get("/sources")
async def get_sources(
    request: Request,
    category: str = Query("all", description="分类ID，筛选该分类下可用来源"),
):
    """获取某分类下所有可用来源名称（基于缓存，不受分页影响）"""
    if _rate_limited(_client_ip(request)):
        return {"code": 429, "message": "请求过于频繁，请稍后再试", "data": []}
    log.info("新闻请求: sources category=%s", category)
    data = await news_service.get_sources(category=category)
    return {"code": 0, "data": data}


@router.get("/channels")
async def get_channels(request: Request):
    """获取待接入渠道清单（前端「更多来源」入口，标注 pending）。

    返回业界做本地资讯聚合的常见补充手段（微信/头条/微博/抖音/直爬/商业API），
    当前均未在 config.yaml 启用，仅保留入口并标注待接入，便于后续按需接入。
    """
    if _rate_limited(_client_ip(request)):
        return {"code": 429, "message": "请求过于频繁，请稍后再试", "data": []}
    log.info("新闻请求: channels")
    data = news_service.get_channels()
    return {"code": 0, "data": data}


@router.get("/articles")
async def get_articles(
    request: Request,
    category: str = Query("all", description="分类ID"),
    keyword: str = Query("", description="搜索关键词"),
    sort: str = Query("latest", description="排序: latest / popular / trending"),
    page: int = Query(1, ge=1, le=MAX_PAGE, description="页码"),
    page_size: int = Query(10, ge=1, le=MAX_PAGE_SIZE, description="每页数量"),
    source: str = Query("", description="按来源名称筛选"),
    geo_scope: str = Query("", description="地理圈层: district(区) / city(市)，用于当地新闻按影响范围优先"),
    personalized: bool = Query(True, description="是否启用个性化推荐"),
):
    """获取新闻列表（含个性化推荐评分）

    geo_scope 说明（维度一 & 维度二）：
      - district : 仅收区/市粒度新闻，按「影响范围」优先（区 > 市），热点式向用户集中；
      - city     : 地理圈层扩大到全市（含市名即可，区仍优先）；
      - 空       : 不过滤，仅做影响范围评分。
    """
    if _rate_limited(_client_ip(request)):
        return {"code": 429, "message": "请求过于频繁，请稍后再试", "data": [], "total": 0}
    log.info("新闻请求: articles category=%s keyword=%s page=%s geo_scope=%s", category, keyword, page, geo_scope)
    result = await news_service.get_articles(
        category=category, keyword=keyword, sort=sort,
        page=page, page_size=page_size, source=source, geo_scope=geo_scope
    )
    # 个性化评分。采用 Feedly「优先收件箱」模式：
    #   - 第 1 页：时间线顺序保持不变，但把命中画像的高分文章抽到最前面置顶，
    #     使个性化真正影响可见性（此前只打分不重排，Ranker 形同虚设）。
    #   - 第 2 页及以后：只打分不重排。翻页时再置顶会让同一篇文章
    #     在滚动过程中反复跳位，破坏无限滚动的连续性。
    if personalized and result.get("articles"):
        engine = get_engine()
        result["articles"] = engine.recommend(
            result["articles"],
            "news",
            mode="priority" if page == 1 else "score_only",
        )
    return {
        "code": 0,
        "data": result["articles"],
        "total": result["total"],
        "page": result.get("page", page),
        "page_size": result.get("page_size", page_size),
        "has_more": result.get("has_more", False),
    }


@router.get("/recommend")
async def get_recommend(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="返回条数"),
    use_llm: bool = Query(True, description="是否调用 LLM 生成深度推荐理由（未配置则自动降级本地）"),
):
    """维度三：基于用户画像诉求的「深度 AI 新闻推荐」。

    从社会/生活视角解析用户画像，推断潜在诉求（关注领域/健康/通勤/省钱…），
    据此对新闻做深度排序，并为每条命中新闻生成「诉求标签 + 推荐理由」。
    LLM 仅用于增强理由，未配置 api_key 时自动降级本地启发式，功能始终可用。
    """
    if _rate_limited(_client_ip(request)):
        return {"code": 429, "message": "请求过于频繁，请稍后再试", "data": [], "needs": []}
    log.info("新闻请求: recommend limit=%s use_llm=%s", limit, use_llm)
    try:
        articles = await news_service._get_cached_articles()
    except Exception as e:
        log.warning("推荐读取缓存失败，回退 mock: %s", e)
        articles = []
    if not articles:
        articles = (await MockNewsService().get_articles(page_size=limit)).get("articles", [])

    from services.news_ai_recommend import NewsAIRecommender
    recommender = NewsAIRecommender()
    ranked, needs = recommender.recommend(articles, use_llm=use_llm, top_k=12)

    # 剔除无诉求命中的（深度推荐只呈现「为你而推」），保留前 limit 条
    personalized = [a for a in ranked if a.get("_needs")]
    if not personalized:
        # 极端情况下（画像为空且无任何命中）回退展示最新，避免空列表
        personalized = ranked
    personalized = personalized[:limit]

    # 序列化时剥离内部字段，仅保留前端需要的推荐信号
    out = []
    for a in personalized:
        item = dict(a)
        item["_needs"] = a.get("_needs", [])
        item["_ai_reason"] = a.get("_ai_reason", "")
        item["_need_score"] = a.get("_need_score", 0.0)
        out.append(item)

    return {
        "code": 0,
        "data": out,
        "needs": [
            {"topic": n["topic"], "category": n["category"], "weight": round(n["weight"], 2), "reason": n["reason"]}
            for n in needs
        ],
        "total": len(out),
    }


@router.get("/trending")
async def get_trending():
    """获取热门话题"""
    data = await news_service.get_trending()
    return {"code": 0, "data": data}


# ============================================================
# 隐式反馈埋点
# ============================================================

class FeedbackBody(BaseModel):
    """一条用户行为事件"""
    article_id: str = Field(..., max_length=64)
    action: str = Field(..., description="click / dwell / open_link / like / not_interested / impression")
    dwell_ms: int = Field(0, ge=0, le=3_600_000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    category: str = Field("", max_length=32)
    title: str = Field("", max_length=200)


@router.post("/feedback")
async def post_feedback(body: FeedbackBody, request: Request):
    """记录一条用户行为反馈（点击 / 停留 / 跳原文 / 不感兴趣）。

    埋点是「尽力而为」的旁路：任何异常都不应影响前端主流程，
    因此这里统一吞掉错误并返回 code 0。
    """
    if _rate_limited(_client_ip(request)):
        return {"code": 429, "message": "请求过于频繁，请稍后再试"}

    if body.action not in feedback_store.ACTION_WEIGHTS:
        return {"code": 400, "message": f"未知的 action: {body.action}"}

    try:
        feedback_store.record_event(
            article_id=body.article_id,
            action=body.action,
            dwell_ms=body.dwell_ms,
            tags=body.tags,
            category=body.category,
            title=body.title,
        )
        # 负反馈影响面大（会压制整类内容），立即热更新画像；
        # 其余正向信号靠 TTL 自然生效，避免每次点击都重算。
        if body.action == "not_interested":
            reload_engine()
    except Exception:
        pass

    return {"code": 0, "message": "ok"}


@router.get("/feedback/stats")
async def get_feedback_stats():
    """查看隐式画像的聚合结果（调试 / 前端展示「系统学到了什么」）"""
    try:
        return {"code": 0, "data": feedback_store.stats()}
    except Exception as e:
        return {"code": 500, "message": str(e), "data": {}}
