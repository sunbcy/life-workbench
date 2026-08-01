"""
地理关注分类树 (Location / Region Taxonomy)

把「世界树下钻」范式应用到 location 维度: 用户沿地理层级
(城市 → 城区 → 商圈/场景) 下钻打标, 标记自己「关注/常去」的区域,
引擎据此派生 location 画像的 frequent_regions (区域标签),
让资讯/周边推荐能命中这些地理关注点。

注意: 这与现有「家/公司坐标 + 距离计算」并存 —
坐标用于精确距离排序, 本树用于「语义化地理兴趣」(如关注"南山科技园"相关资讯)。

节点结构: { "id": "loc.sz.nanshan", "name": "南山", "children": [...] }
标注: { "<node_id>": "like" | "skill" }
  - like  = 关注/常去此区域 -> 写入 frequent_regions
  - skill = 熟悉/通勤此区域
"""

LOCATION_TREE = [
    {
        "id": "loc.sz", "name": "深圳", "children": [
            {"id": "loc.sz.nanshan", "name": "南山", "children": [
                {"id": "loc.sz.nanshan.tech", "name": "科技园"},
                {"id": "loc.sz.nanshan.houhai", "name": "后海"},
                {"id": "loc.sz.nanshan.shekkou", "name": "蛇口"},
                {"id": "loc.sz.nanshan.uni", "name": "大学城"},
            ]},
            {"id": "loc.sz.futian", "name": "福田", "children": [
                {"id": "loc.sz.futian.cbd", "name": "CBD"},
                {"id": "loc.sz.futian.chegong", "name": "车公庙"},
                {"id": "loc.sz.futian.huaqiang", "name": "华强北"},
            ]},
            {"id": "loc.sz.baoan", "name": "宝安", "children": [
                {"id": "loc.sz.baoan.xixiang", "name": "西乡"},
                {"id": "loc.sz.baoan.airport", "name": "机场"},
            ]},
            {"id": "loc.sz.luohu", "name": "罗湖", "children": [
                {"id": "loc.sz.luohu.dongmen", "name": "东门"},
                {"id": "loc.sz.luohu.cao", "name": "草埔"},
            ]},
            {"id": "loc.sz.longgang", "name": "龙岗"},
            {"id": "loc.sz.longhua", "name": "龙华"},
        ]
    },
    {
        "id": "loc.guangzhou", "name": "广州", "children": [
            {"id": "loc.guangzhou.tianhe", "name": "天河"},
            {"id": "loc.guangzhou.yuexiu", "name": "越秀"},
            {"id": "loc.guangzhou.panyu", "name": "番禺"},
        ]
    },
    {
        "id": "loc.scene", "name": "常去场景", "children": [
            {"id": "loc.scene.home", "name": "居家周边"},
            {"id": "loc.scene.work", "name": "办公周边"},
            {"id": "loc.scene.transit", "name": "通勤沿线"},
            {"id": "loc.scene.travel", "name": "出差/旅行城市", "children": [
                {"id": "loc.scene.travel.beijing", "name": "北京"},
                {"id": "loc.scene.travel.shanghai", "name": "上海"},
                {"id": "loc.scene.travel.hangzhou", "name": "杭州"},
            ]},
        ]
    },
]


def _build_all_index(custom: dict, ext_index: dict) -> dict:
    from services.dimension_taxonomy import _index_tree
    all_index = _index_tree(LOCATION_TREE)
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


def derive_location(marks: dict, custom: dict, ext_index: dict | None = None) -> dict:
    """从地理标注派生路径/末梢/区域关键词。"""
    from services.dimension_taxonomy import _path_ids_in, compute_sibling_gaps
    all_index = _build_all_index(custom, ext_index or {})

    paths = []
    leaves = []
    regions = set()      # 关注的地理区域标签
    keywords = set()
    want_set = set()
    learning_set = set()
    tried_set = set()
    know_set = set()

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
        # 任一状态都计入区域标签 (关注/熟悉/知道/想了解/在学/体验过 都与你相关)
        regions.add(node["name"])
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
        "regions": sorted(regions),
        "know": sorted(know_set),
        "want": sorted(want_set),
        "learning": sorted(learning_set),
        "tried": sorted(tried_set),
        "sibling_gaps": compute_sibling_gaps("location", marks, custom, ext_index),
    }


def apply_location(derived: dict, dim_data: dict) -> dict:
    """把派生区域标签写回 location.yaml 的 frequent_regions。"""
    existing = dim_data.get("frequent_regions", [])
    existing = [r for r in existing if not (isinstance(r, dict) and r.get("_derived"))]
    derived_regions = [{"name": r, "_derived": True} for r in derived["regions"]]
    dim_data["frequent_regions"] = existing + derived_regions
    return dim_data


from services.dimension_taxonomy import register_dimension  # noqa: E402

register_dimension("location", {
    "name": "地理关注",
    "tree": LOCATION_TREE,
    "mark_file": "location_map.yaml",
    "target_dim": "location",
    "provider": None,
    "derive": derive_location,
    "apply": apply_location,
})
