"""周边资源 API 路由"""
import logging
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from services import create_nearby_service, geolocation
from services.recommendation import get_engine

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nearby", tags=["周边资源"])

nearby_service = create_nearby_service()


# ========== 到店记录（用户对卡片的自标注） ==========
class VisitIn(BaseModel):
    resource_id: str
    action: str                          # visited | not_visited | experience
    resource_name: str = ""
    taste: str = ""                      # good | bad（仅 experience）
    note: str = ""


@router.post("/visit")
async def record_visit(body: VisitIn):
    """记录用户对某周边资源的到店标记/体验（去过/没去过/好吃不好吃）。"""
    from services import place_visits
    try:
        place_visits.record_visit(
            resource_id=body.resource_id,
            action=body.action,
            resource_name=body.resource_name,
            taste=body.taste,
            note=body.note,
        )
    except ValueError as e:
        return {"code": 400, "message": str(e)}
    except Exception as e:
        log.warning("到店记录失败: %s", e)
    return {"code": 0, "message": "ok"}


@router.get("/visit/summary")
async def visit_summary(ids: str = Query("", description="逗号分隔的 resource_id 列表")):
    """批量查询卡片的到店状态（来过/好评收藏/喜爱度）。前端列表渲染后注入。"""
    from services import place_visits
    id_list = [x for x in ids.split(",") if x.strip()] if ids else None
    try:
        data = place_visits.get_summary(id_list)
    except Exception as e:
        log.warning("到店状态查询失败: %s", e)
        data = {}
    return {"code": 0, "data": data}


# ========== 需求中心交互 ==========
class NeedIn(BaseModel):
    text: str = ""                       # 语音/文字输入（与 tapped_tags 二选一/并用）
    tapped_tags: list[str] = []          # 折叠多级点选直接给的 item_tag
    use_llm: bool = False                # 是否启用 C 路径 LLM 语义解析（消耗 token）
    radius: float = 3.0                  # 搜索半径(公里)
    personalized: bool = True            # 是否启用个性化推荐
    states: dict = {}                    # A 路径：前端勾选的用户状态（饿/渴/缺水…）


@router.post("/need")
async def need_search(body: NeedIn):
    """需求中心检索：把用户需求(文字/点选)解析为物品标签，多召回源展开后聚合排序。

    每次都会自动携带隐含上下文信封（时间/坐标/用户状态/偏好），
    A 路径零 token；use_llm=True 且有 key 时启用 LLM 语义解析（自动降级回 A）。
    """
    from services.need_context import build_context, set_states, active_state_labels
    from services.need_resolver import resolve_to_queries

    # 1) 上下文信封（自动携带隐含输入）
    context = build_context()

    # 2) A 路径：写入用户勾选状态（即时持久化，跨天清零由 need_context 保证）
    if body.states:
        try:
            set_states(body.states)
            context["user_state"] = body.states
        except Exception as e:
            log.warning("用户状态写入失败（不影响检索）: %s", e)

    # 3) 解析 + 多召回源
    resolved = resolve_to_queries(
        text=body.text,
        use_llm=body.use_llm,
        context=context,
        tapped_tags=body.tapped_tags,
    )

    # 4) 执行召回：把 queries 全部并发拉取并聚合去重
    queries = resolved["queries"]
    fallback_keyword = resolved.get("fallback_keyword")

    # 兜底：未命中任何 item_tag 时，用用户原话作为关键词全文召回
    if not queries and fallback_keyword:
        queries = [{"category": "", "keyword": fallback_keyword}]

    aggregated: dict[int, dict] = {}
    if queries:
        import asyncio
        results = await asyncio.gather(
            *[_fetch_for_query(q, body.radius) for q in queries],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                log.warning("需求召回单源失败: %s", r)
                continue
            for item in r:
                rid = item.get("id")
                if rid is None:
                    continue
                # 同 id 已存在则保留（多召回源覆盖同一地点属正常）
                if rid not in aggregated:
                    aggregated[rid] = item

    resources = list(aggregated.values())
    resource_crs = nearby_service._crs_of(nearby_service.provider)

    # 5) 真实距离重算 + 半径过滤
    geolocation.apply_real_distance(resources, resource_crs=resource_crs)
    resources = [r for r in resources if r["distance"] <= body.radius]

    # 6) 排序：默认按距离（需求中心以"可达性"为先），个性化作为加分
    resources.sort(key=lambda r: r["distance"])
    if body.personalized and resources:
        try:
            engine = get_engine()
            # 用上下文信封里的状态补充到用户向量（让"渴"影响推荐解释）
            resources = engine.recommend(resources, "nearby")
        except Exception as e:
            log.warning("需求检索个性化失败（降级距离排序）: %s", e)

    return {
        "code": 0,
        "data": resources,
        "total": len(resources),
        "mode": resolved["mode"],
        "item_tags": resolved["item_tags"],
        "reason": resolved["reason"],
        "context": {
            "time_slot_label": context.get("time_slot_label", ""),
            "location_label": (
                f"{context['location'].get('city', '')}"
                f"{context['location'].get('district', '')}"
            ),
            "user_state_labels": active_state_labels(context),
        },
        "location": geolocation.get_location(),
    }


async def _fetch_for_query(query: dict, radius: float) -> list[dict]:
    """对单个召回源查询执行 POI 搜索（复用 NearbyService 的 provider + 回退逻辑）。"""
    result = await nearby_service.get_resources(
        category=query.get("category") or "all",
        keyword=query.get("keyword", ""),
        sort="distance",
        radius=radius,
    )
    return result["resources"]


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
