"""
健康领域分类树 (Health Taxonomy)

参考医学/健康管理知识体系, 内置一棵可下钻的健康领域种子树。
用户沿树细分、在节点上打标 (关注 / 擅长), 引擎据此反推健康兴趣路径与末梢,
并派生出 health 画像的 health_concerns / preferred_exercise 等字段, 立即影响推荐。

节点结构同 interests 树: { "id": "health.cardio", "name": "心血管", "children": [...] }
标注结构 (存于 health_map.yaml): { "<node_id>": "like" | "skill" }
  - like  = 关注此健康领域  -> 写入 health_concerns
  - skill = 擅长/有经验     -> 写入 preferred_exercise / 运动相关
"""

HEALTH_TREE = [
    {
        "id": "health.body", "name": "身体机能", "children": [
            {"id": "health.body.cardio", "name": "心血管", "children": [
                {"id": "health.body.cardio.bp", "name": "高血压"},
                {"id": "health.body.cardio.arr", "name": "心律失常"},
            ]},
            {"id": "health.body.metabolic", "name": "代谢内分泌", "children": [
                {"id": "health.body.metabolic.diabetes", "name": "糖尿病"},
                {"id": "health.body.metabolic.thyroid", "name": "甲状腺"},
            ]},
            {"id": "health.body.resp", "name": "呼吸系统", "children": [
                {"id": "health.body.resp.asthma", "name": "哮喘"},
                {"id": "health.body.resp.allergy", "name": "过敏"},
            ]},
            {"id": "health.body.digest", "name": "消化肠胃"},
            {"id": "health.body.sleep", "name": "睡眠", "children": [
                {"id": "health.body.sleep.insomnia", "name": "失眠"},
                {"id": "health.body.sleep.apnea", "name": "睡眠呼吸暂停"},
            ]},
            {"id": "health.body.immuno", "name": "免疫提升"},
        ]
    },
    {
        "id": "health.nutri", "name": "营养膳食", "children": [
            {"id": "health.nutri.weight", "name": "体重管理", "children": [
                {"id": "health.nutri.weight.loss", "name": "减脂"},
                {"id": "health.nutri.weight.gain", "name": "增肌"},
            ]},
            {"id": "health.nutri.diet", "name": "饮食模式", "children": [
                {"id": "health.nutri.diet.lowcarb", "name": "低碳/生酮"},
                {"id": "health.nutri.diet.medit", "name": "地中海饮食"},
                {"id": "health.nutri.diet.veg", "name": "素食"},
            ]},
            {"id": "health.nutri.supp", "name": "营养补充", "children": [
                {"id": "health.nutri.supp.protein", "name": "蛋白粉"},
                {"id": "health.nutri.supp.vit", "name": "维生素"},
            ]},
        ]
    },
    {
        "id": "health.exercise", "name": "运动健身", "children": [
            {"id": "health.exercise.cardio", "name": "有氧", "children": [
                {"id": "health.exercise.cardio.run", "name": "跑步"},
                {"id": "health.exercise.cardio.cycle", "name": "骑行"},
                {"id": "health.exercise.cardio.swim", "name": "游泳"},
            ]},
            {"id": "health.exercise.strength", "name": "力量训练", "children": [
                {"id": "health.exercise.strength.free", "name": "自由重量"},
                {"id": "health.exercise.strength.ci", "name": "器械"},
            ]},
            {"id": "health.exercise.mind", "name": "身心运动", "children": [
                {"id": "health.exercise.mind.yoga", "name": "瑜伽"},
                {"id": "health.exercise.mind.pilates", "name": "普拉提"},
                {"id": "health.exercise.mind.taichi", "name": "太极"},
            ]},
            {"id": "health.exercise.team", "name": "团队球类", "children": [
                {"id": "health.exercise.team.basket", "name": "篮球"},
                {"id": "health.exercise.team.foot", "name": "足球"},
            ]},
        ]
    },
    {
        "id": "health.mind", "name": "心理健康", "children": [
            {"id": "health.mind.stress", "name": "压力管理"},
            {"id": "health.mind.anxiety", "name": "焦虑/抑郁"},
            {"id": "health.mind.focus", "name": "专注力"},
            {"id": "health.mind.meditation", "name": "正念冥想"},
        ]
    },
    {
        "id": "health.prevent", "name": "预防与体检", "children": [
            {"id": "health.prevent.screen", "name": "癌症筛查"},
            {"id": "health.prevent.vaccine", "name": "疫苗接种"},
            {"id": "health.prevent.check", "name": "定期体检"},
        ]
    },
    {
        "id": "health.tcm", "name": "中医养生", "children": [
            {"id": "health.tcm.accu", "name": "针灸推拿"},
            {"id": "health.tcm.herb", "name": "中药调理"},
            {"id": "health.tcm.qigong", "name": "气功"},
        ]
    },
]


def _build_all_index(custom: dict, ext_index: dict) -> dict:
    from services.dimension_taxonomy import _index_tree
    all_index = _index_tree(HEALTH_TREE)
    for cid, info in custom.items():
        pid = info.get("parent_id")
        if pid in all_index:
            ppath = all_index[pid]["path"]
            pdepth = all_index[pid]["depth"]
            all_index[cid] = {
                "id": cid, "name": info["name"], "parent_id": pid,
                "depth": pdepth + 1, "path": ppath + [info["name"]],
            }
    for cid, rec in ext_index.items():
        pid = rec["parent_id"]
        if pid in all_index:
            ppath = all_index[pid]["path"]
            pdepth = all_index[pid]["depth"]
            all_index[cid] = {
                "id": cid, "name": rec["name"], "parent_id": pid,
                "depth": pdepth + 1, "path": ppath + [rec["name"]],
            }
    return all_index


def derive_health(marks: dict, custom: dict, ext_index: dict | None = None) -> dict:
    """从健康标注派生路径/末梢/关键词, 并区分「关注」(concern) 与「运动」(exercise)。"""
    from services.dimension_taxonomy import _path_ids_in, compute_sibling_gaps
    all_index = _build_all_index(custom, ext_index or {})

    paths = []
    leaves = []
    concerns = set()      # 关注的健康领域 -> health_concerns
    exercises = set()     # 运动相关 -> preferred_exercise
    keywords = set()
    want_set = set()
    learning_set = set()
    tried_set = set()
    know_set = set()

    # 判定某节点是否属于「运动健身」分支
    def is_exercise_branch(nid: str) -> bool:
        node = all_index.get(nid)
        if not node:
            return False
        return any(seg == "运动健身" for seg in node["path"])

    for nid, m in marks.items():
        if not isinstance(m, dict):
            continue
        states = {s: bool(m.get(s)) for s in ("like", "skill", "know", "want", "learning", "tried")}
        if not any(states.values()):
            continue
        node = all_index.get(nid)
        if not node:
            continue
        paths.append({
            "node_id": nid, "mark": states,
            "path": [{"id": i, "name": all_index[i]["name"]} for i in _path_ids_in(nid, all_index)],
        })
        has_marked_child = any(
            k.startswith(nid + ".") and isinstance(v, dict)
            and any(v.get(s) for s in ("like", "skill", "know", "want", "learning", "tried"))
            for k, v in marks.items()
        )
        if not has_marked_child:
            leaves.append({"id": nid, "name": node["name"], "mark": states})
        keywords.add(node["name"])
        for p in node["path"]:
            keywords.add(p)
        # 任一状态都计入派生字段 (关注/擅长/知道/想了解/在学/体验过 都算与你相关)
        if is_exercise_branch(nid):
            exercises.add(node["name"])
        else:
            concerns.add(node["name"])
        if states.get("know"):
            know_set.add(node["name"])
        if states.get("want"):
            want_set.add(node["name"])
        if states.get("learning"):
            learning_set.add(node["name"])
        if states.get("tried"):
            tried_set.add(node["name"])

    return {
        "paths": paths,
        "leaves": leaves,
        "keywords": sorted(keywords),
        "concerns": sorted(concerns),
        "exercises": sorted(exercises),
        "know": sorted(know_set),
        "want": sorted(want_set),
        "learning": sorted(learning_set),
        "tried": sorted(tried_set),
        "sibling_gaps": compute_sibling_gaps("health", marks, custom, ext_index),
    }


def apply_health(derived: dict, dim_data: dict) -> dict:
    """把派生结果写回 health.yaml 的 health_concerns / preferred_exercise。"""
    existing_concerns = dim_data.get("health_concerns", [])
    existing_concerns = [c for c in existing_concerns
                         if not (isinstance(c, dict) and c.get("_derived"))]
    derived_concerns = [{"name": c, "_derived": True} for c in derived["concerns"]]
    dim_data["health_concerns"] = existing_concerns + derived_concerns

    existing_ex = dim_data.get("preferred_exercise", [])
    existing_ex = [e for e in existing_ex
                   if not (isinstance(e, dict) and e.get("_derived"))]
    derived_ex = [{"name": e, "_derived": True} for e in derived["exercises"]]
    dim_data["preferred_exercise"] = existing_ex + derived_ex
    return dim_data


# 注册到通用框架
from services.dimension_taxonomy import register_dimension  # noqa: E402

register_dimension("health", {
    "name": "健康关注",
    "tree": HEALTH_TREE,
    "mark_file": "health_map.yaml",
    "target_dim": "health",
    "provider": None,
    "derive": derive_health,
    "apply": apply_health,
})
