"""维度地图 API — 通用「世界树下钻打标」(兴趣 / 健康 / 地理 ...)

按 dimension 选择对应分类树与配置 (见 services/dimension_taxonomy)。
提供: 树获取 / 打标 / 自定义节点 / 派生结果 / 写回对应维度画像并热重载。
"""
import re
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.dimension_taxonomy import (
    DIMENSION_REGISTRY, get_children, get_path,
    is_external_node, get_external_parent, get_external_name,
    build_external_index_for, mark_file_path,
)
from services.ai_mentor import ai_available

router = APIRouter(prefix="/api/interest-map", tags=["维度地图"])

MAP_DIR = Path.home() / ".life-workbench" / "profile"


# ========== 请求体 ==========
class TagBody(BaseModel):
    dimension: str           # interests / health / location ...
    node_id: str
    mark: str                # "like" | "skill" | "know" | "want" | "learning" | "tried" | "" (空=取消)


class CustomNodeBody(BaseModel):
    dimension: str
    parent_id: str
    name: str


# ========== 读取/写入标注 ==========
# 可叠加的认知/关系状态集。一个节点可同时持多种状态。
MARK_STATES = ("like", "skill", "know", "want", "learning", "tried")


def _load_marks(dimension: str) -> dict:
    """读取标注。返回 { node_id: {state: bool, ...} }。

    状态 (认知/关系梯度, 由热到冷):
      skill(擅长/有经验) > like(关注/感兴趣) > tried(已体验/经历过) >
      learning(在学/进行中) > want(想了解) > know(知道/听说过, 未参与)。
    兼容旧格式 {"node_id": "like" | "skill"} —— 自动迁移为集合形式。
    """
    f = mark_file_path(dimension)
    if not f.exists():
        return {}
    try:
        raw = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    migrated = {}
    for nid, v in raw.items():
        if isinstance(v, dict):
            states = {s: bool(v.get(s)) for s in MARK_STATES if v.get(s)}
            if states:
                migrated[nid] = states
        elif v in ("like", "skill"):
            migrated[nid] = {"like": v == "like", "skill": v == "skill"}
    return migrated


def _save_marks(dimension: str, marks: dict):
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    mark_file_path(dimension).write_text(
        yaml.safe_dump(marks, allow_unicode=True), encoding="utf-8")


def _custom_nodes(dimension: str) -> dict:
    f = MAP_DIR / f"interest_custom_{dimension}.yaml"
    if f.exists():
        try:
            return yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def _merge_custom_into_index(dimension: str) -> dict:
    custom = _custom_nodes(dimension)
    cfg = DIMENSION_REGISTRY.get(dimension, {})
    index = cfg.get("index", {})
    extra = {}
    for cid, info in custom.items():
        pid = info.get("parent_id")
        if pid not in index and pid not in extra:
            continue
        parent_path = index[pid]["path"] if pid in index else extra[pid]["path"]
        depth = index[pid]["depth"] + 1 if pid in index else extra[pid]["depth"] + 1
        extra[cid] = {
            "id": cid, "name": info["name"], "parent_id": pid,
            "depth": depth, "path": parent_path + [info["name"]],
            "has_children": False, "custom": True,
        }
    return extra


# ========== 路由 ==========
class MentorBody(BaseModel):
    dimension: str | None = None   # 指定维度; 不传则对全部维度汇总分析
    force_fresh: bool = False      # True=忽略缓存/增量, 强制实时调 LLM 全新生成


@router.post("/mentor")
async def mentor_report(body: MentorBody):
    """AI 职业导师报告: 基于用户打标数据生成客观、准确、鼓舞人心的总结与分析。

    不传 dimension 时, 对全部已打标维度汇总; 否则只分析单个维度。
    无 AI key 时自动降级为本地启发式总结。

    两种模式 (前端两个按钮分别对应):
      - force_fresh=False (快速画像): 标签指纹未变则命中缓存 (0 token);
        否则将上一次报告 + 标签增减 diff 交给 LLM 做增量更新。自动、省 token。
      - force_fresh=True  (深度分析): 完全忽略缓存与上次报告, 强制实时调大模型
        基于当前打标全新生成, 用户主动掌控结果质量与来源。

    返回 data.mode: cached | incremental | full (首次全量) | fresh (强制实时)
    """
    from services.ai_mentor import (
        mentor_report as gen_report,
        load_cached_mentor, load_last_mentor,
    )

    dims = ([body.dimension] if body.dimension else list(DIMENSION_REGISTRY.keys()))
    # 过滤掉完全没有打标的维度 (避免空分析)
    active = []
    for d in dims:
        if d not in DIMENSION_REGISTRY:
            continue
        if _load_marks(d):
            active.append(d)
    if not active:
        return {"code": 0, "data": {
            "report": "你还没有在任何维度上打标。先去左侧树里点亮几个节点"
                      "（感兴趣 / 精通 / 在学…），回来我就能为你画一幅能力画像。",
            "ai": ai_available(),
            "mode": "empty",
        }}

    parts = []
    meta_flags = {"cached": False, "incremental": False, "fresh": False, "full": False}
    if len(active) > 1:
        parts.append("# 你的跨维度能力总览\n")
    for d in active:
        cfg = DIMENSION_REGISTRY[d]
        marks = _load_marks(d)
        custom = _custom_nodes(d)
        ext_index = build_external_index_for(d)
        derived = cfg["derive"](marks, custom, ext_index)
        # 给 paths 补上完整可读路径
        for p in derived.get("paths", []):
            p["path"] = get_path(d, p["node_id"])

        if body.force_fresh:
            # 深度分析: 忽略缓存与上次报告, 直接全量调 LLM 重新生成
            meta_flags["fresh"] = True
            report = gen_report(
                d, cfg["name"], marks,
                derived.get("paths", []), derived.get("leaves", []),
                derived.get("keywords", []),
                derived.get("sibling_gaps", []),
            )
        else:
            # 1) 标签未变 -> 命中缓存 (省 token)
            cached = load_cached_mentor(d, marks)
            if cached is not None:
                report = cached
                meta_flags["cached"] = True
            else:
                # 2) 标签有变 -> 取上次报告做增量
                prev = load_last_mentor(d)
                prev_report = prev[1] if prev else None
                prev_marks = prev[0] if prev else None
                if prev_report:
                    meta_flags["incremental"] = True
                else:
                    meta_flags["full"] = True
                report = gen_report(
                    d, cfg["name"], marks,
                    derived.get("paths", []), derived.get("leaves", []),
                    derived.get("keywords", []),
                    derived.get("sibling_gaps", []),
                    prev_report=prev_report, prev_marks=prev_marks,
                )
        if len(active) > 1:
            report = f"## ▎{cfg['name']}\n\n" + report
        parts.append(report)

    # 单一维度时以该维度 mode 为准; 多维度时若含 fresh 则整体视为 fresh
    if meta_flags["fresh"]:
        mode = "fresh"
    elif meta_flags["cached"]:
        mode = "cached"
    elif meta_flags["incremental"]:
        mode = "incremental"
    else:
        mode = "full"

    report_text = "\n\n".join(parts)

    # 持久化本次画像到本地历史 (供前端「查看历史」调用); 空/占位报告不入库
    if mode != "empty":
        try:
            from services.ai_mentor import append_mentor_history
            append_mentor_history(
                (body.dimension or "all"),
                mode=mode, ai=ai_available(), report=report_text)
        except Exception:
            pass

    return {"code": 0, "data": {
        "report": report_text,
        "ai": ai_available(),
        "mode": mode,
        "cached": mode == "cached",
        "incremental": mode == "incremental",
    }}


class GoalBody(BaseModel):
    goal: str                       # 用户写下的目标 / 想法 (自然语言)


# ========== 画像历史记录 (前端「查看历史」调用) ==========
class MentorHistoryGoalBody(BaseModel):
    dimension: str | None = None    # 与画像生成时一致 (不传=all)
    goal_input: str                 # 用户写下的目标文本
    goal_mode: str                  # local-hard / llm-semantic / local-fallback
    goal_result: dict               # 目标测算完整结果


@router.get("/mentor-history")
async def list_mentor_history(dimension: str | None = None):
    """列出历史画像记录 (按时间倒序)。

    返回 data.list: [{ id, created_at, mode, ai, preview, has_goal, goal_input, goal_mode }]
    preview 为报告前若干字符, 便于列表展示。
    """
    from services.ai_mentor import load_history
    dim = dimension or "all"
    recs = load_history(dim)
    recs = list(reversed(recs))  # 最新在前
    out = []
    for r in recs:
        rep = r.get("report", "") or ""
        out.append({
            "id": r.get("id"),
            "created_at": r.get("created_at"),
            "mode": r.get("mode") or "",
            "ai": bool(r.get("ai")),
            "preview": rep[:80].replace("\n", " ").strip(),
            "has_goal": bool(r.get("goal")),
            "goal_input": (r.get("goal") or {}).get("goal_input", ""),
            "goal_mode": (r.get("goal") or {}).get("mode", ""),
        })
    return {"code": 0, "data": {"list": out}}


@router.get("/mentor-history/{dimension}/{record_id}")
async def get_mentor_history(dimension: str, record_id: str):
    """获取单条历史画像记录完整内容 (含画像报告与关联的目标测算)。"""
    from services.ai_mentor import load_history
    recs = load_history(dimension)
    for r in recs:
        if r.get("id") == record_id:
            return {"code": 0, "data": r}
    raise HTTPException(status_code=404, detail="历史记录不存在")


@router.post("/mentor-history/goal")
async def save_mentor_history_goal(body: MentorHistoryGoalBody):
    """把一次目标测算关联到该维度最新一条画像历史记录 (若其 goal 为空)。

    用于前端在「目标距离」面板算完后, 将结果回写进历史, 使历史记录同时保有
    画像与对应的目标测算, 供后续「查看历史」一键调用。
    """
    from services.ai_mentor import attach_goal_to_history
    dim = body.dimension or "all"
    rec = attach_goal_to_history(
        dim, goal_input=body.goal_input, goal_mode=body.goal_mode,
        goal_result=body.goal_result)
    return {"code": 0, "data": rec or {}}


@router.post("/goal")
async def goal_distance(body: GoalBody):
    """基于能力画像计算「目标 → 当前能力」的路径距离, 给出最短补足路径。

    纯本地、可解释: 在全部维度树上匹配目标节点, 计算其与用户已打标集合的最小树距离。
    """
    from services.ai_mentor import goal_analysis

    if not body.goal or not body.goal.strip():
        raise HTTPException(status_code=400, detail="目标不能为空")
    result = goal_analysis(body.goal.strip())
    return {"code": 0, "data": result}


class GoalSemanticBody(BaseModel):
    goal: str                       # 用户写下的目标 / 想法 (投影式描述)
    force_llm: bool = False         # True=忽略本地硬匹配, 强制实时调 LLM 投影解析
    dimension: str | None = None    # 用户当前所在维度 (聚焦提示)


@router.post("/goal-semantic")
async def goal_semantic(body: GoalSemanticBody):
    """目标投影解析 + 跨空间距离向量。

    两种模式 (前端两个按钮分别对应):
      - force_llm=False (快速测算): 目标能在能力树上硬匹配时直接返回本地树距离 (秒回 0 token);
        仅当硬匹配失败 (投影式目标) 才调 LLM / 本地启发式降级。
      - force_llm=True  (深度解析): 忽略本地硬匹配, 强制实时调大模型把目标投影解析为
        能力维度 + 跨空间距离向量, 用户主动掌控结果质量与来源。

    返回 data.mode: local-hard (本地树距离) | llm-semantic (LLM 投影) | local-fallback (本地启发式)
    """
    from services.ai_mentor import semantic_goal_analysis

    if not body.goal or not body.goal.strip():
        raise HTTPException(status_code=400, detail="目标不能为空")
    result = semantic_goal_analysis(body.goal.strip(),
                                    force_llm=body.force_llm,
                                    dimension=body.dimension)
    result["ai"] = ai_available()
    # 持久化目标测算到历史 (关联到该维度最新一条画像记录)
    try:
        from services.ai_mentor import attach_goal_to_history
        attach_goal_to_history(
            (body.dimension or "all"), goal_input=body.goal.strip(),
            goal_mode=result.get("mode", ""), goal_result=result)
    except Exception:
        pass
    return {"code": 0, "data": result}


@router.get("/export")
async def export_all_yaml():
    """一键导出全部维度的标注 / 自定义节点 / 派生结果 (YAML)。

    返回可下载的 .yaml 文件 (Content-Disposition), 包含每个已注册维度的:
      - marks:       用户打标状态 {node_id: {state: bool}}
      - custom_nodes: 用户自定义子节点
      - derived:     实时派生结果 (路径/末梢/关键词/认知层级 ...)
    """
    from datetime import datetime
    bundle: dict = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "dimensions": {},
    }
    for key, cfg in DIMENSION_REGISTRY.items():
        marks = _load_marks(key)
        custom = _custom_nodes(key)
        ext_index = build_external_index_for(key)
        derived = cfg["derive"](marks, custom, ext_index)
        bundle["dimensions"][key] = {
            "name": cfg["name"],
            "marks": marks,
            "custom_nodes": custom,
            "derived": derived,
        }
    text = yaml.safe_dump(bundle, allow_unicode=True, sort_keys=False)
    from fastapi.responses import Response
    return Response(
        content=text,
        media_type="application/x-yaml",
        headers={"Content-Disposition": "attachment; filename=\"life-workbench-profile.yaml\""},
    )


@router.get("/dimensions")
async def list_dimensions():
    """返回所有已注册的可下钻维度"""
    return {"code": 0, "data": [
        {"key": k, "name": cfg["name"]} for k, cfg in DIMENSION_REGISTRY.items()
    ]}


@router.get("/tree")
async def get_tree(dimension: str, node_id: str | None = None):
    """获取某维度某节点的子节点"""
    if dimension not in DIMENSION_REGISTRY:
        raise HTTPException(status_code=404, detail="未知维度")
    children = get_children(dimension, node_id)
    # 合并用户自定义子节点
    if node_id is not None:
        for cid, info in _custom_nodes(dimension).items():
            if info.get("parent_id") == node_id:
                children.append({
                    "id": cid, "name": info["name"], "has_children": False,
                    "depth": (DIMENSION_REGISTRY[dimension]["index"]
                              .get(node_id, {}).get("depth", 0) + 1),
                    "custom": True,
                })
    return {"code": 0, "data": children}


@router.get("/path/{dimension}/{node_id}")
async def node_path(dimension: str, node_id: str):
    """获取从根到节点的路径 (支持内置 / 自定义 / 外部节点)"""
    if dimension not in DIMENSION_REGISTRY:
        raise HTTPException(status_code=404, detail="未知维度")
    cfg = DIMENSION_REGISTRY[dimension]
    index = cfg["index"]
    # 内置
    if node_id in index:
        return {"code": 0, "data": get_path(dimension, node_id)}
    # 自定义
    extra = _merge_custom_into_index(dimension)
    if node_id in extra:
        ids = [node_id]
        pid = extra[node_id]["parent_id"]
        while pid:
            ids.insert(0, pid)
            if pid in index:
                pid = index[pid]["parent_id"]
            elif pid in extra:
                pid = extra[pid]["parent_id"]
            else:
                break
        path = []
        for i in ids:
            if i in index:
                path.append({"id": i, "name": index[i]["name"]})
            elif i in extra:
                path.append({"id": i, "name": extra[i]["name"]})
        return {"code": 0, "data": path}
    # 外部
    if is_external_node(dimension, node_id):
        ids = [node_id]
        pid = get_external_parent(dimension, node_id)
        while pid:
            ids.insert(0, pid)
            if pid in index:
                pid = index[pid]["parent_id"]
            elif is_external_node(dimension, pid):
                pid = get_external_parent(dimension, pid)
            else:
                break
        path = []
        for i in ids:
            if i in index:
                path.append({"id": i, "name": index[i]["name"]})
            elif is_external_node(dimension, i):
                path.append({"id": i, "name": get_external_name(dimension, i)})
        return {"code": 0, "data": path}
    raise HTTPException(status_code=404, detail="节点不存在")


@router.get("/marks")
async def get_marks(dimension: str):
    """获取用户标注 + 自定义节点 + 派生结果"""
    if dimension not in DIMENSION_REGISTRY:
        raise HTTPException(status_code=404, detail="未知维度")
    marks = _load_marks(dimension)
    custom = _custom_nodes(dimension)
    cfg = DIMENSION_REGISTRY[dimension]
    ext_index = build_external_index_for(dimension)
    derived = cfg["derive"](marks, custom, ext_index)
    return {
        "code": 0,
        "data": {"marks": marks, "custom_nodes": custom, "derived": derived},
    }


@router.post("/tag")
async def tag_node(body: TagBody):
    """打标 / 取消打标, 派生写回对应维度画像并热重载。

    like 与 skill 可独立叠加: 同一节点可同时「感兴趣」+「擅长」。
    再次发送同名 mark 则取消该标记; 当 like/skill 全部取消时移除该节点。
    """
    if body.dimension not in DIMENSION_REGISTRY:
        raise HTTPException(status_code=404, detail="未知维度")
    cfg = DIMENSION_REGISTRY[body.dimension]
    custom = _custom_nodes(body.dimension)
    ext_index = build_external_index_for(body.dimension)
    node_exists = (
        body.node_id in cfg["index"]
        or body.node_id in custom
        or is_external_node(body.dimension, body.node_id)
    )
    if not node_exists:
        raise HTTPException(status_code=404, detail="节点不存在")
    if body.mark not in MARK_STATES and body.mark != "":
        raise HTTPException(status_code=400, detail=f"mark 必须是 {MARK_STATES} 之一或 ''")

    marks = _load_marks(body.dimension)
    cur = dict(marks.get(body.node_id, {}))  # {state: bool, ...}
    if body.mark == "":
        # 取消全部标记
        marks.pop(body.node_id, None)
    else:
        # 切换该单项状态 (存在则取消, 不存在则置为 True)
        if cur.get(body.mark):
            cur.pop(body.mark, None)
        else:
            cur[body.mark] = True
        if cur:
            marks[body.node_id] = cur
        else:
            marks.pop(body.node_id, None)
    _save_marks(body.dimension, marks)

    # 同步派生到对应维度画像
    derived = cfg["derive"](marks, custom, ext_index)
    _apply_to_dimension(body.dimension, cfg, derived)

    # 热重载推荐引擎, 让派生兴趣立即生效
    from services.recommendation import reload_engine
    reload_engine()

    return {"code": 0, "data": {"marks": marks, "derived": derived}}


@router.post("/custom-node")
async def add_custom_node(body: CustomNodeBody):
    """在 parent_id 下新增自定义子节点 (id 自动生成)"""
    if body.dimension not in DIMENSION_REGISTRY:
        raise HTTPException(status_code=404, detail="未知维度")
    cfg = DIMENSION_REGISTRY[body.dimension]
    if (body.parent_id not in cfg["index"]
            and body.parent_id not in _custom_nodes(body.dimension)
            and not is_external_node(body.dimension, body.parent_id)):
        raise HTTPException(status_code=404, detail="父节点不存在")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")

    custom = _custom_nodes(body.dimension)
    slug = re.sub(r"[^\w一-鿿]", "_", body.name.strip())
    cid = f"{body.parent_id}.{slug}"
    if cid in custom:
        return {"code": 0, "data": {"id": cid, "name": custom[cid]["name"], "exists": True}}
    custom[cid] = {"name": body.name.strip(), "parent_id": body.parent_id}
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    (MAP_DIR / f"interest_custom_{body.dimension}.yaml").write_text(
        yaml.safe_dump(custom, allow_unicode=True),
        encoding="utf-8",
    )
    from services.recommendation import reload_engine
    if _load_marks(body.dimension):
        reload_engine()
    return {"code": 0, "data": {"id": cid, "name": body.name.strip(), "exists": False}}


# ========== 写回对应维度画像 ==========
def dimension_ancestors(dimension: str) -> dict:
    """读取该维度标注, 构建 {节点名: [祖先词...]} 映射 (供引擎层级泛化)。

    供 services/recommendation/vectorizer 在向量层注入, 使引擎
    在内容只命中祖先路径词时也能泛化命中 (如标了 Vue 没标前端的文章)。
    """
    if dimension not in DIMENSION_REGISTRY:
        return {}
    marks = _load_marks(dimension)
    custom = _custom_nodes(dimension)
    ext_index = build_external_index_for(dimension)
    from services.dimension_taxonomy import build_ancestors
    return build_ancestors(dimension, marks, custom, ext_index)


def _apply_to_dimension(dimension: str, cfg: dict, derived: dict):
    """调用该维度的 apply 回调, 把派生结果写回 <target_dim>.yaml"""
    target = cfg["target_dim"]
    f = MAP_DIR / f"{target}.yaml"
    data = {}
    if f.exists():
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    data = cfg["apply"](derived, data)
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
