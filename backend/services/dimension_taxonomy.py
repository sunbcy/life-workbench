"""
通用维度分类树框架 (Dimension Taxonomy)

把「世界树下钻打标」范式从 interests 单一维度泛化为任意维度通用能力。
每个维度在注册表中声明:
  - tree:        该维度的内置种子树 (结构与 WORLD_TREE 一致)
  - mark_file:   标注持久化文件名 (存于 ~/.life-workbench/profile/)
  - target_dim:  派生结果写回的画像维度 yaml (如 interests / health / location)
  - derive:      派生函数 (marks, custom) -> {keywords, skill_keywords, ...}
  - apply:       把派生结果写回 target_dim 对应字段的回调

这样前端只需一套通用下钻组件, 后端按 dimension 选择对应树与配置,
新增一个维度的「地图打标」只需在注册表加一条 + 一棵种子树。
"""

import os
from pathlib import Path

PROFILE_DIR = Path.home() / ".life-workbench" / "profile"


# ============================================================
# 外部职业分类 API 适配器 (可选, 仅 interests 维度使用)
# ============================================================
class ExternalTaxonomyProvider:
    """外部分类 API 适配器基类。

    当内置树某节点没有 children 时, 引擎会尝试调用 provider 拉取更细的叶子。
    子类需实现 fetch_children(node_id) -> list[{"id","name","has_children"}]。
    """

    def reachable(self) -> bool:
        return True

    def fetch_children(self, node_id: str) -> list[dict]:  # pragma: no cover
        raise NotImplementedError


_EXTERNAL_PROVIDER: ExternalTaxonomyProvider | None = None


def register_external_provider(provider: ExternalTaxonomyProvider | None):
    global _EXTERNAL_PROVIDER
    _EXTERNAL_PROVIDER = provider


def get_external_provider() -> ExternalTaxonomyProvider | None:
    return _EXTERNAL_PROVIDER


# ============================================================
# 树索引工具
# ============================================================
def _index_tree(nodes, parent=None, acc=None):
    if acc is None:
        acc = {}
    for n in nodes:
        pid = parent["id"] if parent else None
        depth = (parent["depth"] + 1) if parent else 0
        path = (parent["path"] + [n["name"]]) if parent else [n["name"]]
        rec = {
            "id": n["id"], "name": n["name"],
            "parent_id": pid, "depth": depth, "path": path,
            "has_children": bool(n.get("children")),
        }
        acc[n["id"]] = rec
        if n.get("children"):
            _index_tree(n["children"], rec, acc)
    return acc


def _find_raw(nodes, node_id):
    class _W:
        pass
    def walk(ns):
        for n in ns:
            if n["id"] == node_id:
                return n
            if n.get("children"):
                r = walk(n["children"])
                if r:
                    return r
        return None
    return walk(nodes)


# ============================================================
# 维度注册表
# ============================================================
# 实际树定义见各维度模块 (interests_tree / health_tree / location_tree)
DIMENSION_REGISTRY: dict = {}


def register_dimension(key: str, config: dict):
    """注册一个维度分类树配置。

    config = {
        "name": "兴趣与技能",
        "tree": [...],                       # 内置种子树
        "mark_file": "interest_map.yaml",    # 标注存储
        "target_dim": "interests",           # 写回的维度 yaml
        "provider": None,                    # 可选的外部 provider
        "derive": callable,                  # (marks, custom, index) -> derived dict
        "apply": callable,                   # (derived, dim_data) -> dim_data (就地修改)
    }
    """
    config["index"] = _index_tree(config["tree"])
    if config.get("provider") and config["provider"].reachable():
        # provider 节点缓存
        config["_ext_index"] = {}
    DIMENSION_REGISTRY[key] = config


def get_dimension(key: str) -> dict | None:
    return DIMENSION_REGISTRY.get(key)


def list_dimensions() -> list[str]:
    return list(DIMENSION_REGISTRY.keys())


# ============================================================
# 通用查询 (基于注册表, 支持外部 provider 回退)
# ============================================================
def get_children(dimension: str, node_id: str | None) -> list[dict]:
    cfg = DIMENSION_REGISTRY.get(dimension)
    if not cfg:
        return []
    tree = cfg["tree"]
    index = cfg["index"]
    if node_id is None:
        return [{
            "id": n["id"], "name": n["name"],
            "has_children": bool(n.get("children")), "depth": 0,
        } for n in tree]
    node = index.get(node_id)
    if not node:
        return _external_children(dimension, node_id)
    raw = _find_raw(tree, node_id)
    if raw and raw.get("children"):
        return [{
            "id": c["id"], "name": c["name"],
            "has_children": bool(c.get("children")),
            "depth": index[c["id"]]["depth"],
        } for c in raw["children"]]
    return _external_children(dimension, node_id)


def _external_children(dimension: str, node_id: str) -> list[dict]:
    cfg = DIMENSION_REGISTRY.get(dimension)
    if not cfg:
        return []
    provider = cfg.get("provider")
    if provider is None or not provider.reachable():
        return []
    try:
        leaves = provider.fetch_children(node_id)
    except Exception:
        return []
    ext = cfg.setdefault("_ext_index", {})
    out = []
    for d in leaves:
        ext[d["id"]] = {"name": d["name"], "parent_id": node_id}
        out.append({
            "id": d["id"], "name": d["name"],
            "has_children": bool(d.get("has_children", False)),
            "depth": cfg["index"][node_id]["depth"] + 1,
            "external": True,
        })
    return out


def get_node(dimension: str, node_id: str) -> dict | None:
    cfg = DIMENSION_REGISTRY.get(dimension)
    return cfg["index"].get(node_id) if cfg else None


def get_path(dimension: str, node_id: str) -> list[dict]:
    cfg = DIMENSION_REGISTRY.get(dimension)
    if not cfg:
        return []
    index = cfg["index"]
    node = index.get(node_id)
    if not node:
        return []
    ids = [node_id]
    pid = node["parent_id"]
    while pid:
        ids.insert(0, pid)
        pid = index[pid]["parent_id"]
    return [{"id": index[i]["id"], "name": index[i]["name"]} for i in ids]


def is_external_node(dimension: str, node_id: str) -> bool:
    cfg = DIMENSION_REGISTRY.get(dimension)
    return bool(cfg and node_id in cfg.get("_ext_index", {}))


def get_external_parent(dimension: str, node_id: str) -> str | None:
    cfg = DIMENSION_REGISTRY.get(dimension)
    rec = cfg.get("_ext_index", {}).get(node_id) if cfg else None
    return rec["parent_id"] if rec else None


def get_external_name(dimension: str, node_id: str) -> str | None:
    cfg = DIMENSION_REGISTRY.get(dimension)
    rec = cfg.get("_ext_index", {}).get(node_id) if cfg else None
    return rec["name"] if rec else None


def _path_ids_in(node_id: str, index: dict) -> list[str]:
    node = index.get(node_id)
    if not node:
        return []
    ids = [node_id]
    pid = node["parent_id"]
    while pid and pid in index:
        ids.insert(0, pid)
        pid = index[pid]["parent_id"]
    return ids


def build_external_index_for(dimension: str) -> dict:
    """返回该维度外部节点缓存 {id: {name, parent_id}} (供派生路径计算)"""
    cfg = DIMENSION_REGISTRY.get(dimension)
    return dict(cfg.get("_ext_index", {})) if cfg else {}


def mark_file_path(dimension: str) -> Path:
    cfg = DIMENSION_REGISTRY.get(dimension)
    fname = cfg["mark_file"] if cfg else f"{dimension}_map.yaml"
    return PROFILE_DIR / fname


def build_ancestors(dimension: str, marks: dict, custom: dict, ext_index: dict | None = None) -> dict:
    """通用「已标节点 → 祖先路径词」映射, 供引擎做层级泛化匹配。

    返回: { "<节点名 lower>": ["父", "祖父", ...] }  (祖先词, 不含自身)
    若维度注册了专用 interest_ancestors 风格的回调 (在 cfg 中可选 "ancestors"),
    则优先使用; 否则用通用实现 (基于 cfg["index"])。
    """
    cfg = DIMENSION_REGISTRY.get(dimension)
    if not cfg:
        return {}
    # 优先调用维度自带的 ancestors 回调 (如 interests 的 interest_ancestors)
    cb = cfg.get("ancestors")
    if cb:
        return cb(marks, custom, ext_index or {})
    # 通用实现
    index = cfg["index"]
    all_index = dict(index)
    for cid, info in custom.items():
        pid = info.get("parent_id")
        if pid in all_index:
            ppath = all_index[pid]["path"]
            all_index[cid] = {
                "id": cid, "name": info["name"], "parent_id": pid,
                "depth": all_index[pid]["depth"] + 1, "path": ppath + [info["name"]],
            }
    for cid, rec in (ext_index or {}).items():
        pid = rec["parent_id"]
        if pid in all_index:
            ppath = all_index[pid]["path"]
            all_index[cid] = {
                "id": cid, "name": rec["name"], "parent_id": pid,
                "depth": all_index[pid]["depth"] + 1, "path": ppath + [rec["name"]],
            }
    result: dict[str, list[str]] = {}
    for nid, m in marks.items():
        if not isinstance(m, dict):
            continue
        if not any(m.get(s) for s in ("like", "skill", "know", "want", "learning", "tried")):
            continue
        node = all_index.get(nid)
        if not node:
            continue
        ancestors = [p.lower() for p in node["path"][:-1]]
        if ancestors:
            result[node["name"].lower()] = ancestors
    return result


def compute_sibling_gaps(dimension: str, marks: dict, custom: dict,
                         ext_index: dict | None = None) -> list[dict]:
    """计算「同层负向推断」信息。

    核心逻辑：当某父节点下存在多个同级兄弟，且用户已标记了其中大部分、
    却漏标了个别兄弟时，这些「未标记兄弟」是高置信度的「用户不熟悉/未接触」信号。
    若不显式记录，全局画像会错误地认为用户对该父范畴整体熟悉，造成信息损失。

    返回列表，每条:
      {
        "parent":   父节点名,
        "parent_id": 父节点 id,
        "depth":    该层深度,
        "marked_siblings":   [已标兄弟名...],
        "unmarked_siblings": [未标兄弟名...],   # 即「大概率不熟悉」, 仅含有 children 或叶子
        "marked_count": int,
        "total_count": int,
        "ratio": float,                          # 已标/总数, 越高越说明漏标=不熟悉
      }
    仅当 total_count >= 3 且 ratio >= 0.5 且存在 unmarked 时才纳入（噪声过滤）。
    """
    cfg = DIMENSION_REGISTRY.get(dimension)
    if not cfg:
        return []
    from services.interest_tree import _build_all_index  # 通用: 各维度模块都提供
    try:
        all_index = _build_all_index(custom, ext_index or {})
    except Exception:
        index = cfg.get("index", {})
        all_index = dict(index)
        for cid, info in custom.items():
            pid = info.get("parent_id")
            if pid in all_index:
                all_index[cid] = {**info, "name": info["name"],
                                  "path": all_index[pid].get("path", []) + [info["name"]]}
        for cid, rec in (ext_index or {}).items():
            pid = rec.get("parent_id")
            if pid in all_index:
                all_index[cid] = {**rec, "name": rec["name"],
                                  "path": all_index[pid].get("path", []) + [rec["name"]]}

    def is_marked(nid: str) -> bool:
        m = marks.get(nid)
        return bool(m) and isinstance(m, dict) and any(
            m.get(s) for s in ("like", "skill", "know", "want", "learning", "tried"))

    # 按父节点分组兄弟
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)
    for nid, rec in all_index.items():
        pid = rec.get("parent_id")
        if pid is not None and pid in all_index:
            groups[pid].append(nid)

    gaps = []
    for pid, sibs in groups.items():
        total = len(sibs)
        if total < 3:
            continue
        marked = [all_index[s]["name"] for s in sibs if is_marked(s)]
        unmarked = [all_index[s]["name"] for s in sibs if not is_marked(s)]
        if not unmarked:
            continue
        ratio = len(marked) / total
        if ratio < 0.5:
            continue
        gaps.append({
            "parent": all_index[pid]["name"],
            "parent_id": pid,
            "depth": all_index[pid]["depth"],
            "marked_siblings": marked,
            "unmarked_siblings": unmarked,
            "marked_count": len(marked),
            "total_count": total,
            "ratio": round(ratio, 2),
        })
    # 按 ratio 降序、未标数升序, 突出「几乎全标却漏一两个」的最强信号
    gaps.sort(key=lambda g: (-g["ratio"], g["unmarked_siblings"]))
    return gaps
