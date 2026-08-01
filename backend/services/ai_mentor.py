"""能力画像引擎 — 基于用户在「兴趣/技能/知识...」地图上的打标与逐层路径,

为 AI 提供一份「能力向量画像」，用于:
  1. 客观刻画用户当前已掌握 / 有潜力 / 空白的能力结构（不夸大、不鼓励、不编造）。
  2. 明确「基于现有能力，用户现在能独立做成哪些事」。
  3. 作为距离计算的基线：当用户写下目标 / 想法时，AI 可据此从「路径距离」角度
     判断该目标离用户当前能力有多远、最短补足路径是什么。

- 配置了 ai.api_key 时: 调用 OpenAI 兼容的 /chat/completions 接口。
- 未配置时: 自动降级为本地启发式画像, 保证功能始终可用 (无需外部依赖)。

注意: 这里不是「职业规划导师」，不做鼓励式说教；它是用户的「能力结构说明」，
供用户本人及下游 AI 推理使用。
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import httpx
from . import get_config
from services.dimension_taxonomy import DIMENSION_REGISTRY

# 画像报告缓存目录 (与打标文件同 profile 目录)
_CACHE_DIR = Path.home() / ".life-workbench" / "profile" / "mentor_cache"


def _marks_fingerprint(marks: dict) -> str:
    """对标记状态做稳定指纹 (节点 id + 状态集合)，用于判断是否变化。"""
    norm = {k: sorted(v for v in (vals or {}) if vals.get(v))
            for k, vals in marks.items() if vals}
    blob = json.dumps(norm, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _cache_path(dimension: str, fingerprint: str) -> Path:
    return _CACHE_DIR / f"{dimension}.{fingerprint}.md"


def _is_valid_report(report: str) -> bool:
    """校验报告是否有效 (避免把空响应 / 占位垃圾 / 被截断的残片写入或命中缓存)。

    判定为无效: 过短、没有 Markdown 标题、命中已知占位残余模板，
    或以"半成品句尾"收尾（典型表现：LLM 因 max_tokens 不足被硬截断，
    如结尾是「深度至第」「- 」「（」等未闭合片段）。
    """
    if not report or len(report.strip()) < 120:
        return False
    if "## " not in report:
        return False
    # 已知坏占位残余 (早期某次 LLM 返回的模板碎片)
    _bad_markers = ("【全新报告】", "【增量修订版报告】", "本次更新：模")
    if any(m in report for m in _bad_markers):
        return False
    # 截断残片判定：以"明显没说完"的片段收尾，说明 LLM 输出被 max_tokens 截断
    _tail = report.rstrip()
    _last_line = _tail.split("\n")[-1].rstrip()
    # 结尾若停在以下"未完成"模式上，基本可断定被截断
    _truncation_tails = (
        "深度至第", "（深度至第", "（深度",  # 「深度至第 N 层」未写完
        "- ", "· ", "、", "，", "（", "：", "——",
        "### ", "## ", "#### ",
        "」下", "」中", "「",
    )
    for t in _truncation_tails:
        if _tail.endswith(t) or _last_line.endswith(t):
            return False
    # 列表项空壳：最后一行只有 "-"/"·" 等标记而无内容，明显被截断
    if _last_line.strip() in ("-", "·", "*", "•", ">"):
        return False
    # 括号/方括号未闭合也算截断
    if _tail.count("（") > _tail.count("）"):
        return False
    if _tail.count("「") > _tail.count("」"):
        return False
    if _tail.endswith("]"):
        # 行尾孤立 ] 多半是 markdown 列表项 [精通] 被截断，或 JSON 残留
        return False
    return True


def load_cached_mentor(dimension: str, marks: dict) -> str | None:
    """标签指纹未变时返回缓存报告；否则 None。

    若命中缓存但内容无效（占位/过短），视为未命中，交由实时生成覆盖之。
    """
    fp = _marks_fingerprint(marks)
    p = _cache_path(dimension, fp)
    if p.exists():
        try:
            txt = p.read_text(encoding="utf-8")
            if _is_valid_report(txt):
                return txt
            # 坏缓存：删除，避免反复命中
            try:
                p.unlink()
            except Exception:
                pass
        except Exception:
            return None
    return None


def save_cached_mentor(dimension: str, marks: dict, report: str):
    """写入缓存报告 (按指纹分文件, 旧指纹文件自然失效可手动清理)。

    同时把本次的 marks + report 写入 last.json, 供下一次做增量 diff。
    """
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fp = _marks_fingerprint(marks)
        _cache_path(dimension, fp).write_text(report, encoding="utf-8")
        (_CACHE_DIR / f"{dimension}.last.json").write_text(
            json.dumps({"marks": marks, "report": report}, ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        pass


def load_last_mentor(dimension: str) -> tuple[dict, str] | None:
    """读取上一次生成的 marks + report (用于增量分析)。无或无效则返回 None。"""
    p = _CACHE_DIR / f"{dimension}.last.json"
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            rep = d.get("report", "")
            # 坏底稿不参与增量（增量基于坏底稿只会越改越糟）
            if not _is_valid_report(rep):
                try:
                    p.unlink()
                except Exception:
                    pass
                return None
            return d.get("marks", {}), rep
        except Exception:
            return None
    return None


# ========== 历史画像记录 (本地持久化, 供前端「查看历史」调用) ==========
def _history_path(dimension: str) -> Path:
    return _CACHE_DIR / f"{dimension}.history.json"


def load_history(dimension: str) -> list:
    """读取该维度的历史画像记录列表 (按时间倒序由调用方处理)。

    每条记录结构:
      { id, created_at, mode, ai, report,
        goal: {goal_input, mode, result} | None }
    """
    p = _history_path(dimension)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8")) or []
        return [r for r in data if isinstance(r, dict)]
    except Exception:
        return []


def _save_history(dimension: str, records: list):
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _history_path(dimension).write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def append_mentor_history(dimension: str, *, mode: str, ai: bool, report: str) -> dict:
    """追加一条新的画像历史记录 (goal 留空, 待后续目标测算关联)。"""
    import time
    if not _is_valid_report(report):
        return {}
    records = load_history(dimension)
    rec = {
        "id": f"{int(time.time() * 1000)}",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode, "ai": bool(ai), "report": report, "goal": None,
    }
    records.append(rec)
    # 仅保留最近 50 条, 防止无界增长
    if len(records) > 50:
        records = records[-50:]
    _save_history(dimension, records)
    return rec


def attach_goal_to_history(dimension: str, *, goal_input: str, goal_mode: str,
                           goal_result: dict) -> dict | None:
    """把一次目标测算关联到该维度「最新一条」画像历史记录 (若其 goal 为空)。

    若最新一条记录已有 goal, 则新建一条仅含 goal 的记录。
    返回被写入的记录 (便于前端定位)。
    """
    records = load_history(dimension)
    if records and records[-1].get("goal") is None:
        records[-1]["goal"] = {
            "goal_input": goal_input, "mode": goal_mode, "result": goal_result,
        }
        _save_history(dimension, records)
        return records[-1]
    # 最新一条已含 goal: 新建一条记录 (画像留空仅存目标测算)
    import time
    rec = {
        "id": f"{int(time.time() * 1000)}",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "", "ai": bool(goal_result.get("ai", False)),
        "report": "", "goal": {
            "goal_input": goal_input, "mode": goal_mode, "result": goal_result,
        },
    }
    records.append(rec)
    if len(records) > 50:
        records = records[-50:]
    _save_history(dimension, records)
    return rec

SYSTEM_PROMPT = """你是一个「能力画像引擎」，不是职业规划导师，不要使用鼓励、说教或营销口吻。
你的唯一任务：基于用户主动在能力树上打标的节点及其层级路径，先回答「他是一个什么样的人」，
再客观还原能力结构，并输出一份可被下游 AI 用来「计算目标距离」的画像。

你输出的内容必须严格基于用户真实打标的数据，绝不臆造他没标记的技能。
语气：中性、精确、像一份工程化的能力清单。

请按以下结构输出（Markdown）：

## 一、你是一个什么样的人（结论画像）
- 用 2~4 句话给出对这个人整体的、基于数据的判断：他的认知风格、能力原型、驱动力。
  （例如「你是典型的跨界构建者：以软件工程为根基，向硬件/嵌入式与语言学双向延伸，
  且对基础科学保持广泛好奇；你不满足于消费知识，习惯亲手做出东西。」）
- 归纳 1~3 个「人格-能力原型」标签（如：系统型构建者 / 广博探索者 / 跨界连接者 / 深度专精者 / 动手实践派），
  每个标签后用「依据：」列出支撑它的真实打标（节点名 + 掌握度）。
- 判断他的「主根系」在哪（最深耕、最成体系的 1~2 条线）与「发散方向」（向外探出的支线）。

## 二、能力结构画像（基于真实打标）
- 用「掌握度梯度」分层列出：精通(可独立交付) / 熟练(做过项目) / 在学(进行中) / 感兴趣(关注) / 听说过(认知边缘)。
- 对每个有打标的分支，给出其「路径深度」（已下钻到第几层）与「末梢节点」名称，体现结构的精细度。

## 三、当前能力可独立支撑的事项
- 基于「精通 + 熟练」节点组合，推断用户现在就能独立做成的具体事项（3~6 条，要具体，例如「能用 X 搭一个 Y」）。
- 区分：可独立完成 vs 需要协作/补课的。

## 四、潜力区与空白区（距离向量的两端）
- 潜力区：用户已「感兴趣/在学」但尚未「精通」的节点，是最近的可被点亮的方向。
- 空白区：与用户主干路径相邻、却完全未打标的关键节点，说明若要延伸到某目标可能缺什么。

## 五、给下游 AI 的距离提示
- 用一句话说明：当用户提出某个目标时，应如何用「路径距离」判断远近——
  同主线路径越深越近；跨分支需要补的中间节点越多越远。
- 给出一个「最短补足路径」的示例（从用户最近的潜力节点到某个 plausible 目标）。

语言：简体中文。第二人称「你」。不要寒暄，不要「我期待你」，直接给结构化事实。"""

LOCAL_FALLBACK_INTRO = """（当前未配置 AI 接口，以下为基于你打标数据的本地能力画像；
配置 config.yaml 的 ai.api_key 后将升级为 LLM 深度分析。）"""


def _ai_cfg() -> dict:
    return (get_config().get("ai") or {})


def ai_available() -> bool:
    return bool(_ai_cfg().get("api_key"))


class LLMEmptyResponse(Exception):
    """LLM 返回了空内容（偶发）。"""


def _call_llm_once(user_prompt: str, timeout: int) -> str:
    cfg = _ai_cfg()
    base_url = (cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    api_key = cfg["api_key"]
    model = cfg.get("model") or "gpt-4o-mini"
    # 推理模型 (DeepSeek-R1 / v4-pro / 带 reasoner 等) 会把大量 token 耗在
    # reasoning_content 上，正式 content 常常为空或被 max_tokens 截断。
    # 这类模型需要更大的总生成上限，且要回退读取 reasoning_content。
    is_reasoning = any(k in (model or "").lower()
                      for k in ("reason", "r1", "v4-pro", "v3-pro", "think"))
    max_tokens = 8000 if is_reasoning else 4000
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
            "temperature": 0.5,
            "max_tokens": max_tokens,
        }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data.get("choices", [{}])[0].get("message", {})
        content = (msg.get("content") or "").strip()
        # 兼容推理模型：content 为空时回退 reasoning_content（其尾部通常含结论）
        if not content:
            reason = (msg.get("reasoning_content") or "").strip()
            if reason:
                content = reason
        if not content:
            raise LLMEmptyResponse("LLM 返回了空内容")
        return content


def _call_llm(user_prompt: str, timeout: int = 60) -> str:
    """调用 LLM；偶发空响应时重试一次，仍失败则抛错让上层降级。"""
    try:
        return _call_llm_once(user_prompt, timeout)
    except LLMEmptyResponse:
        # 重试一次（部分 provider 偶发空 completion）
        return _call_llm_once(user_prompt, timeout)


def _local_report(dimension: str, profile: dict) -> str:
    """无 AI key 时的本地能力画像 (客观、无导师口吻)。"""
    lines = [LOCAL_FALLBACK_INTRO, ""]
    marks = profile.get("marks", {})
    if not marks:
        return "\n".join(lines + ["你在这个维度上还没有任何打标。"
                                  "先去左侧树里逐层下钻、点亮节点（精通/在学/感兴趣…），"
                                  "我才能构建你的能力向量画像。"])

    from collections import Counter, defaultdict
    state_counter = Counter()
    by_state = defaultdict(list)   # state -> [path_str, ...]
    paths_map = {}                 # node_id -> path(names)
    roots = defaultdict(lambda: {"n": 0, "skill": 0, "tried": 0, "depth": 0})
    for nid, st in marks.items():
        p = next((x for x in profile.get("paths", []) if x["node_id"] == nid), None)
        path = [seg["name"] for seg in p["path"]] if p else [nid]
        paths_map[nid] = path
        path_str = " > ".join(path)
        for s, v in st.items():
            if v:
                state_counter[s] += 1
                by_state[s].append(path_str)
        # 主根系统计 (顶级分支)
        if path:
            r = roots[path[0]]
            r["n"] += 1
            if st.get("skill"):
                r["skill"] += 1
            if st.get("tried"):
                r["tried"] += 1
            r["depth"] = max(r["depth"], len(path))

    name = profile.get("name", dimension)

    # ===== 一、你是一个什么样的人 (结论画像) =====
    lines.append(f"## 一、你是一个什么样的人（基于真实打标 · {name}）")
    # 主根系: 节点最多 or 掌握最深的顶级分支
    ranked = sorted(roots.items(), key=lambda kv: (kv[1]["skill"] + kv[1]["tried"], kv[1]["n"]), reverse=True)
    main_root = ranked[0] if ranked else ("（无）", {"n": 0})
    # 发散方向: 除了主根以外的顶级分支
    other_roots = [k for k, _ in ranked[1:5]]
    # 原型判断
    n_branches = len([k for k, v in roots.items() if v["n"] > 0])
    has_made = state_counter.get("tried", 0) > 0
    deep = any(v["depth"] >= 4 for v in roots.values())
    proto = []
    if n_branches >= 3:
        proto.append("跨界连接者")
    if main_root[1]["skill"] > 0 and deep:
        proto.append("系统型构建者")
    if state_counter.get("like", 0) >= state_counter.get("skill", 0) and state_counter.get("like", 0) > 3:
        proto.append("广博探索者")
    if has_made:
        proto.append("动手实践派")
    if not proto:
        proto.append("成长中的学习者")
    proto_str = "、".join(proto)

    if n_branches >= 3:
        style = f"且明显向 {n_branches} 个领域发散，是「扎根主业、横向探索」的跨界型个体"
    elif main_root[1]["depth"] >= 4:
        style = "且在该线上下钻很深，是「单线纵深」的专精型个体"
    else:
        style = "目前尚在搭建能力骨架的早期阶段"
    lines.append(f"- **整体判断**：你以「{main_root[0]}」为能力主根系"
                 f"（覆盖 {main_root[1]['n']} 个节点、{main_root[1]['skill']} 项精通、{main_root[1]['tried']} 项做过项目），"
                 + (f"并向「{'、'.join(other_roots)}」等方向发散，" if other_roots else "")
                 + f"{style}。")
    lines.append(f"- **人格-能力原型**：{proto_str}")
    for pr in proto[:2]:
        if pr == "跨界连接者":
            ev = "、".join(other_roots[:3]) or "多分支打标"
            lines.append(f"  - 依据（{pr}）：你在 {n_branches} 个以上不同领域都有打标，而非孤立深耕单一线。")
        elif pr == "系统型构建者":
            lines.append(f"  - 依据（{pr}）：主根系「{main_root[0]}」已下钻到 {main_root[1]['depth']} 层、含 {main_root[1]['skill']} 项精通，具备体系化交付力。")
        elif pr == "广博探索者":
            lines.append(f"  - 依据（{pr}）：「感兴趣」标记 {state_counter.get('like',0)} 项 多于「精通」{state_counter.get('skill',0)} 项，好奇心驱动明显。")
        elif pr == "动手实践派":
            lines.append(f"  - 依据（{pr}）：有 {state_counter.get('tried',0)} 项「已体验/做过项目」记录，偏好亲手验证。")
    lines.append("")

    # ===== 二、能力结构画像 =====
    lines.append("## 二、能力结构画像（基于真实打标）")
    lines.append(f"- 共打标 **{len(marks)}** 个节点，分布于 {n_branches} 个顶级分支。")
    grad = [("skill", "精通(可独立交付)"), ("tried", "熟练(做过项目)"),
            ("learning", "在学(进行中)"), ("like", "感兴趣(关注)"),
            ("want", "想学"), ("know", "听说过(认知边缘)")]
    for s, label in grad:
        items = by_state.get(s, [])
        if items:
            show = "、".join(items[:10]) + ("…" if len(items) > 10 else "")
            lines.append(f"- **{label}**：{len(items)} 项 — {show}")
    lines.append("")

    leaves = profile.get("leaves", [])
    lines.append("## 三、当前能力可独立支撑的事项")
    if by_state.get("skill") or by_state.get("tried"):
        lines.append(f"- 基于你的「精通/熟练」节点，你现在就能独立交付与"
                     f"「{'、'.join((by_state.get('skill') or by_state.get('tried'))[:6])}」"
                     f"相关的事项。")
    else:
        lines.append("- 目前还没有「精通/熟练」节点，独立交付能力尚在积累中；"
                     "建议先把一条最感兴趣的线推到「做过项目」的程度。")
    if by_state.get("learning"):
        lines.append(f"- 你正在学的「{'、'.join(by_state['learning'][:4])}」一旦完成，"
                     "将把可支撑事项向前推进一档。")
    lines.append("")

    lines.append("## 四、潜力区与空白区")
    if by_state.get("like") or by_state.get("learning") or by_state.get("want"):
        near = "、".join((by_state.get("learning") or []) + (by_state.get("like") or [])[:6])
        lines.append(f"- **潜力区（最近可点亮）**：{near or '（无）'} "
                     "—— 这些是你已关注但尚未精通的方向，补足成本最低。")
    else:
        lines.append("- 潜力区：当前没有「感兴趣/在学」标记，所有精力都在已掌握区。")
    lines.append("- **空白区（全局未接触）**：与你的主干路径相邻、却完全未打标的关键节点，"
                 "将是你延伸到新目标时的主要距离来源；可在树上继续下钻暴露它们。")
    lines.append("")

    # ===== 四·五、同层未触达区（高置信「不熟悉」信号）=====
    gaps = profile.get("sibling_gaps") or []
    if gaps:
        lines.append("## 四·五、同层未触达区（高置信「不熟悉」信号 · 请务必纳入判断）")
        lines.append("- 以下节点同父兄弟中你已标记了大部分、却唯独漏标了它们；"
                     "这比「完全没碰过该范畴」更能说明你**明确知道但没接触**——"
                     "是精确的「不熟悉」边界，做全局判断时不要误以为你对该父范畴整体熟悉：")
        for g in gaps[:15]:
            lines.append(
                f"- 在「{g['parent']}」下（{g['marked_count']}/{g['total_count']} 已标）："
                f"你大概率没接触过 **{'、'.join(g['unmarked_siblings'])}**"
                f"（已标的是：{('、'.join(g['marked_siblings']))}）")
        lines.append("")
    else:
        lines.append("## 四·五、同层未触达区")
        lines.append("- 当前没有明显的「同层漏标」信号（即没有「大部分兄弟已标、个别漏标」的情况）。")
        lines.append("")

    lines.append("## 五、给下游 AI 的距离提示")
    lines.append("- 当用户提出目标时，请用「路径距离」判断：目标节点与用户已打标节点"
                 "在树上的最近公共祖先越深、路径越短 => 距离越近；跨分支需补的中间节点越多 => 距离越远。")
    lines.append("- 最短补足路径示例：从用户最近的潜力节点出发，沿树向下/向旁补齐中间节点，"
                 "直到抵达目标所在的分支末梢。")
    return "\n".join(lines)


def _format_gaps(gaps: list) -> str:
    """把 sibling_gaps 渲染为可读文本块。"""
    if not gaps:
        return ""
    lines = []
    for g in gaps[:15]:
        lines.append(
            f"- 在「{g['parent']}」下，{g['marked_count']}/{g['total_count']} 已标"
            f"（{('、'.join(g['marked_siblings']))}），"
            f"未标（大概率不熟悉）：{'、'.join(g['unmarked_siblings'])}"
        )
    return "\n".join(lines)


def mentor_report(dimension: str, name: str, marks: dict,
                  paths: list, leaves: list, keywords: list,
                  sibling_gaps: list | None = None,
                  prev_report: str | None = None,
                  prev_marks: dict | None = None) -> str:
    """生成能力画像（无导师口吻）。

    marks:   {node_id: {state: bool, ...}}
    paths:   derived["paths"]  (含 node_id/mark/path)
    leaves:  derived["leaves"]
    keywords: derived["keywords"]
    sibling_gaps: derived["sibling_gaps"]（同层负向推断）
    prev_report: 上一次分析得到的报告文本 (用于增量更新, 节省 token)
    prev_marks:  上一次分析时的标记状态 (用于计算标签增减 diff)
    """
    def fmt_mark(st: dict) -> str:
        order = [("skill", "精通"), ("tried", "熟练"), ("learning", "在学"),
                 ("like", "感兴趣"), ("want", "想学"), ("know", "听说过")]
        return "/".join(lbl for k, lbl in order if st.get(k))

    node_lines = []
    for nid, st in marks.items():
        p = next((x for x in paths if x["node_id"] == nid), None)
        path_str = " > ".join(seg["name"] for seg in p["path"]) if p else nid
        node_lines.append(f"- [{fmt_mark(st)}] {path_str}")
    node_block = "\n".join(node_lines) if node_lines else "（暂无打标）"

    leaf_names = "、".join(l["name"] for l in leaves[:20])
    kw = "、".join(keywords[:25]) if keywords else "（无）"

    # 同层负向推断: 大部分兄弟已标却漏标的节点 => 高置信度「不熟悉/未接触」
    gaps = sibling_gaps or []
    gap_block = _format_gaps(gaps)

    # ===== 计算标签增减 diff (用于增量 prompt) =====
    diff_block = ""
    if prev_marks is not None:
        cur = {k: set(v for v in (vals or {}) if vals.get(v))
               for k, vals in marks.items() if vals}
        old = {k: set(v for v in (vals or {}) if vals.get(v))
               for k, vals in prev_marks.items() if vals}
        added, removed = [], []
        for k in set(cur) - set(old):
            p = next((x for x in paths if x["node_id"] == k), None)
            name_s = " > ".join(seg["name"] for seg in p["path"]) if p else k
            added.append(f"+ [{fmt_mark({s: True for s in cur[k]})}] {name_s}")
        for k in set(old) - set(cur):
            name_s = k
            removed.append(f"- [{fmt_mark({s: True for s in old[k]})}] {name_s}")
        for k in set(cur) & set(old):
            if cur[k] != old[k]:
                p = next((x for x in paths if x["node_id"] == k), None)
                name_s = " > ".join(seg["name"] for seg in p["path"]) if p else k
                added.append(f"~ [{fmt_mark({s: True for s in cur[k]})}] {name_s} "
                             f"(原: {fmt_mark({s: True for s in old[k]})})")
        if added or removed:
            diff_block = "## 本次标签变更（相对上次分析）\n" + "\n".join(added + removed)

    incremental = bool(prev_report and (diff_block or prev_marks is None))
    if incremental:
        user_prompt = f"""以下是用户「{name}」维度**当前**的打标数据（节点路径 + 标记状态 + 路径深度）：

{node_block}

能力末梢（最细叶子节点）：{leaf_names or '（无）'}
派生关键词：{kw}

## 同层负向推断（重要：不要忽略）
{gap_block or '（无同层漏标信号）'}

{diff_block}

---

## 你上一次生成的能力画像（请在此基础上做【增量更新】，不要从头重写）

{prev_report}

---

请基于【当前打标数据】与【标签变更】，对上面的旧画像做最小化增量修订：
- 仅修改受本次标签增减影响的部分（新增的能力/潜力/空白区、状态变化的节点）；
- 未受影响的部分原样保留，不要重写；
- 在文末用「> 🔁 本次更新：…」标注本次具体改了哪些点（新增/移除/状态变化了哪些标签）。
保留原有 Markdown 结构与「同层未触达区」章节。"""
    else:
        user_prompt = f"""以下是用户在「{name}」维度上主动打标的全部数据（节点路径 + 标记状态 + 路径深度）：

{node_block}

能力末梢（最细叶子节点）：{leaf_names or '（无）'}
派生关键词：{kw}

## 同层负向推断（重要：不要忽略）
以下列出了「同父节点下、用户已标记了大部分兄弟却漏标了个别兄弟」的情况。
这些漏标兄弟是**高置信度的「用户不熟悉/从没摸过」信号**，不应被误判为「用户对该范畴整体熟悉」。
{gap_block or '（无同层漏标信号）'}

请基于以上真实数据，输出该用户的能力结构画像（按 SYSTEM 要求的四段结构），
重点回答：他现在能做什么、潜力区与空白区在哪（含同层未触达区）、目标距离应如何计算。
在「空白区」分析中必须显式纳入上面的同层漏标节点，作为精确的「不熟悉」边界。"""

    if ai_available():
        try:
            raw = _call_llm(user_prompt)
            if _is_valid_report(raw):
                report = raw
            else:
                # LLM 返回了无效内容（占位碎片 / 被 max_tokens 截断的残片）：
                # 先重试一次完整生成（可能只是偶发截断），仍失败再降级本地画像。
                try:
                    raw2 = _call_llm(user_prompt)
                    if _is_valid_report(raw2):
                        report = raw2
                    else:
                        raise ValueError("retry-still-invalid")
                except Exception:
                    report = ("> ⚠️ AI 返回内容无效（过短 / 占位模板 / 被截断），"
                              "已降级为本地能力画像。\n\n") + _local_report(
                        dimension, {"name": name, "marks": marks, "paths": paths,
                                    "leaves": leaves, "sibling_gaps": gaps})
        except Exception as e:
            report = (f"> ⚠️ AI 接口调用失败（{type(e).__name__}: {e}），"
                      f"已降级为本地能力画像。\n\n") + _local_report(
                dimension, {"name": name, "marks": marks, "paths": paths,
                            "leaves": leaves, "sibling_gaps": gaps})
    else:
        report = _local_report(dimension, {"name": name, "marks": marks, "paths": paths,
                                           "leaves": leaves, "sibling_gaps": gaps})
    # 仅当报告有效时才写缓存（坏内容不污染缓存，下次会自动重生成）
    if _is_valid_report(report):
        save_cached_mentor(dimension, marks, report)
    return report


# ========== 目标 → 路径距离分析 ==========
def _goal_candidates(goal_text: str) -> list:
    """在全部维度树上, 找出与目标文本相关的候选节点 (名称/路径包含匹配)。

    支持整句多 token: 把目标按中英文/空格/标点拆词, 任意 token 命中即纳入,
    命中 token 数越多、名字越精确, 排名越靠前。
    """
    import re
    text = goal_text.strip().lower()
    if not text:
        return []
    tokens = [t for t in re.split(r"[\s,，。、/\\()-]+", text) if len(t) >= 2]
    if not tokens:
        tokens = [text]

    seen = {}
    for dim, cfg in DIMENSION_REGISTRY.items():
        index = cfg.get("index", {})
        for nid, info in index.items():
            name = info.get("name", "").lower()
            path_str = " > ".join(seg.lower() for seg in info.get("path", []))
            hit = 0
            exact = False
            for tok in tokens:
                if tok == name or tok in name or name in tok:
                    hit += 1
                    if tok == name:
                        exact = True
                elif tok in path_str:
                    hit += 1
            if hit == 0:
                continue
            score = hit * 2 + (3 if exact else 0)
            if nid in seen:
                seen[nid]["score"] = max(seen[nid]["score"], score)
            else:
                seen[nid] = {
                    "dim": dim, "dim_name": cfg.get("name", dim),
                    "node_id": nid, "name": info.get("name", ""),
                    "path": info.get("path", []), "depth": info.get("depth", 0),
                    "score": score,
                }
    cands = sorted(seen.values(), key=lambda c: (c["score"], c["depth"]), reverse=True)
    return cands[:5]


def _tree_distance(goal_path: list, mark_path: list) -> int:
    """两条路径(节点名列表)的树距离: 总长 - 2*公共前缀长度。"""
    i = 0
    while i < len(goal_path) and i < len(mark_path) and goal_path[i] == mark_path[i]:
        i += 1
    return len(goal_path) + len(mark_path) - 2 * i


def goal_analysis(goal_text: str) -> dict:
    """分析用户目标相对当前能力画像的「路径距离」, 给出最短补足路径。

    纯本地、可解释 (不依赖 LLM)。
    """
    from services.dimension_taxonomy import DIMENSION_REGISTRY

    cands = _goal_candidates(goal_text)
    if not cands:
        return {
            "matched": False,
            "message": "在现有能力树上没找到与目标直接对应的节点。"
                       "试着用树里已有的词描述你的目标（例如「机器学习」「嵌入式开发」），"
                       "或继续在树上补充相关分支，我就能计算距离。",
            "nearest": None, "distance": None, "fill_path": [],
        }

    # 汇总用户全部维度的已打标路径
    all_mark_paths = []
    from api.interest_map import _load_marks
    for dim, cfg in DIMENSION_REGISTRY.items():
        marks = _load_marks(dim)
        index = cfg.get("index", {})
        for nid in marks:
            if nid in index:
                all_mark_paths.append({
                    "dim": dim, "name": index[nid].get("name", ""),
                    "path": index[nid].get("path", []),
                    "mark": marks[nid],
                })

    def mark_label(m: dict) -> str:
        order = [("skill", "精通"), ("tried", "熟练"), ("learning", "在学"),
                 ("like", "感兴趣"), ("want", "想学"), ("know", "听说过")]
        return "/".join(l for k, l in order if m.get(k))

    # 对每个候选目标节点都算「到最近已打标节点」的最小树距离, 取全局最近
    best_overall = None
    for goal in cands:
        goal_path = goal["path"]
        if not all_mark_paths:
            return {
                "matched": True, "nearest": goal["name"], "distance": None,
                "fill_path": goal_path,
                "message": f"找到目标节点「{goal['name']}」（{goal['dim_name']}）。"
                           "但你目前没有任何打标，无法计算距离——先去点亮能力树再说。",
            }
        best = None
        for mp in all_mark_paths:
            d = _tree_distance(goal_path, mp["path"])
            if best is None or d < best["distance"]:
                best = {"name": mp["name"], "dim": mp["dim"],
                        "mark": mp["mark"], "distance": d, "path": mp["path"],
                        "goal": goal}
        if best_overall is None or best["distance"] < best_overall["distance"]:
            best_overall = best

    best = best_overall
    goal = best["goal"]
    goal_path = goal["path"]

    # 构造最短补足路径
    i = 0
    while (i < len(best["path"]) and i < len(goal_path)
           and best["path"][i] == goal_path[i]):
        i += 1
    fill = goal_path[i:]

    dist = best["distance"]
    if dist == 0:
        level = "已在你能力内"
    elif dist <= 2:
        level = "很近（同分支，补 1~2 个节点即可）"
    elif dist <= 4:
        level = "中等（需要跨一两层延伸）"
    else:
        level = "较远（需跨分支系统补足）"

    return {
        "matched": True,
        "goal": goal["name"],
        "goal_dim": goal["dim_name"],
        "nearest": best["name"],
        "nearest_mark": mark_label(best["mark"]),
        "distance": dist,
        "level": level,
        "fill_path": fill,
        "message": (
            f"目标「{goal['name']}」（{goal['dim_name']}）与你当前最近的已打标节点"
            f"「{best['name']}（{mark_label(best['mark'])}）」的树距离为 **{dist}**，"
            f"属于「{level}」。"
            + (f"最短补足路径：{' → '.join(fill)}。" if fill else "你已具备该能力，可直接推进。")
        ),
    }


# ========== 目标语义解析 + 跨空间距离向量 (投影式描述) ==========
SEMANTIC_GOAL_PROMPT = """你是「能力目标投影解析引擎」，不是职业规划导师，不要使用鼓励、说教或营销口吻。
用户的某个目标（可能是一段比喻/投影式、非结构化的描述，见图/视频/文字）未必能在现有能力树上找到同名节点，
你需要自己反向探知它真正代表的能力维度，再与用户的多维度能力向量做距离计算。

你的唯一任务：把目标投影解析成一组能力维度，并把每个维度映射到用户能力树上，计算"目标空间"到"用户空间"的距离向量。

输出必须严格遵循下方 JSON 结构（只返回 JSON，不要任何额外文字）：
{
  "target_summary": "用一句话概括这个目标点的真实含义",
  "target_archetypes": ["目标态人格原型1", "目标态人格原型2"],
  "dimensions": [
    {
      "name": "目标能力维度名",
      "meaning": "该维度真实要求什么",
      "required": "所需核心技能/知识/工具",
      "hidden_barrier": "隐性门槛（时间/设备/圈子/身体/资金/心态）",
      "nearest_user_node": "用户能力树上最近的已打标节点（找不到写 null）",
      "nearest_distance": 0到7的整数(0=已在能力内,1-2很近,3-4中等,5+较远),
      "fill_path": ["从最近节点出发到达该维度需补齐的中间节点（含目标维度本身）"],
      "note": "补充说明"
    }
  ],
  "approach_path": ["从用户现状到目标态的整体关键里程碑，用 -> 串联的若干字符串"],
  "first_steps": ["3~5条可立即开始的具体行动建议"],
  "baseline_note": "对目标做了合理外推，并明确标注了'推断'与'用户数据'边界的说明"
}

约束：
- 所有距离判断必须基于用户真实打标数据；用户没标记的维度，nearest_user_node 写 null、nearest_distance 写 5~7。
- 特别重要：能力向量里包含「同层未触达区」（某父节点下大部分兄弟已标、却漏标了个别兄弟）。
  这些漏标兄弟是高置信度的「用户不熟悉/未接触」信号。若目标维度正好落在这种漏标节点上，
  nearest_user_node 应写该父节点（而非 null），nearest_distance 写 4~5（比纯空白近、但明显不熟悉）。
- 对目标做合理外推，但在 baseline_note 中说明哪些是推断。
- 语气中性、工程化。"""


def _build_user_capability_block() -> str:
    """汇总全部维度的已打标路径与状态，构造给 LLM 的用户能力向量文本。"""
    from api.interest_map import _load_marks, _custom_nodes
    from services.dimension_taxonomy import DIMENSION_REGISTRY, build_external_index_for

    blocks = []
    for dim, cfg in DIMENSION_REGISTRY.items():
        marks = _load_marks(dim)
        if not marks:
            continue
        index = cfg.get("index", {})
        ext = build_external_index_for(dim)
        lines = []
        for nid, st in marks.items():
            rec = index.get(nid) or ext.get(nid)
            if not rec:
                continue
            path = rec.get("path", [nid])
            labels = "/".join(
                l for k, l in [("skill", "精通"), ("tried", "熟练"), ("learning", "在学"),
                               ("like", "感兴趣"), ("want", "想学"), ("know", "听说过")]
                if st.get(k)
            )
            lines.append(f"- [{labels}] {' > '.join(path)}")
        if lines:
            blocks.append(f"【{cfg.get('name', dim)}】\n" + "\n".join(lines))
        # 同层负向推断: 大部分兄弟已标却漏标的节点 => 高置信「不熟悉」
        from services.dimension_taxonomy import compute_sibling_gaps
        gaps = compute_sibling_gaps(dim, marks, _custom_nodes(dim), ext)
        if gaps:
            gap_lines = ["\n[同层未触达区 · 高置信「不熟悉」信号 — 不要误判为整体熟悉]"]
            for g in gaps[:15]:
                gap_lines.append(
                    f"- 在「{g['parent']}」下（{g['marked_count']}/{g['total_count']} 已标），"
                    f"你大概率没接触过：{'、'.join(g['unmarked_siblings'])}"
                )
            blocks.append("\n".join(gap_lines))
    return "\n\n".join(blocks) if blocks else "（用户当前没有任何打标）"


def _call_llm_json(user_prompt: str, timeout: int = 90) -> dict:
    """调用 LLM 并尽力解析出 JSON。失败抛错。"""
    import json
    cfg = _ai_cfg()
    base_url = (cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    api_key = cfg["api_key"]
    model = cfg.get("model") or "gpt-4o-mini"
    # 推理模型 (DeepSeek-R1 / v4-pro ...) 需更大生成上限，且正式 content 可能为空
    is_reasoning = any(k in (model or "").lower()
                      for k in ("reason", "r1", "v4-pro", "v3-pro", "think"))
    max_tokens = 8000 if is_reasoning else 4000
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SEMANTIC_GOAL_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        msg = resp.json().get("choices", [{}])[0].get("message", {})
        content = (msg.get("content") or "").strip()
        # 兼容推理模型：content 为空时回退 reasoning_content
        if not content:
            reason = (msg.get("reasoning_content") or "").strip()
            if reason:
                content = reason
        if not content:
            raise LLMEmptyResponse("LLM 返回了空内容")
    # 去除可能的 ```json 包裹
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    # 容错：从文本中提取第一个 { 到最后一个 }，避免推理模型在前后夹带说明文字
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        s, e = content.find("{"), content.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(content[s:e + 1])
        raise


def semantic_goal_analysis(goal_text: str, force_llm: bool = False,
                           dimension: str | None = None) -> dict:
    """目标投影解析 + 跨空间距离向量。

    两种模式 (前端两个按钮分别对应):
      - force_llm=False (快速测算): 先走本地硬匹配 (树距离, 秒回 0 token);
        仅当硬匹配失败 (投影式目标) 才调 LLM 或本地启发式降级。
      - force_llm=True  (深度解析): 忽略本地硬匹配, 强制实时调大模型把目标
        投影解析为能力维度 + 跨空间距离向量, 用户主动掌控结果质量与来源。

    dimension: 用户当前所在维度 (仅作聚焦提示, 投影解析本身跨维度)。
    无 AI key 时: 用本地启发式降级, 仍给出维度拆解与距离估算。
    """
    # 1) 快速测算: 本地硬匹配优先 (除非强制 LLM)
    if not force_llm:
        hard = goal_analysis(goal_text)
        if hard.get("matched") and hard.get("distance") is not None:
            hard["mode"] = "local-hard"
            hard["focus_dimension"] = dimension
            return hard

    cap_block = _build_user_capability_block()
    user_prompt = f"""下面是用户当前的多维度能力向量（节点路径 + 标记状态）：

{cap_block}

用户描述的目标（投影式，未必能在能力树上直接找到同名节点）：
「{goal_text}」

请按 SYSTEM 要求的 JSON 结构，完成目标投影解析与跨空间距离向量计算。"""

    # 2) 有 AI key -> 调 LLM
    if ai_available():
        try:
            data = _call_llm_json(user_prompt)
            data["mode"] = "llm-semantic"
            data["matched"] = True
            data["goal_input"] = goal_text
            data["focus_dimension"] = dimension
            return data
        except Exception as e:
            return {
                "mode": "local-fallback",
                "matched": True,
                "goal_input": goal_text,
                "focus_dimension": dimension,
                "error": f"AI 接口调用失败（{type(e).__name__}: {e}），已降级为本地启发式解析。",
                **_local_semantic_fallback(goal_text, cap_block),
            }

    # 3) 无 AI key -> 本地启发式降级
    return {
        "mode": "local-fallback",
        "matched": True,
        "goal_input": goal_text,
        "focus_dimension": dimension,
        "note": "当前未配置 ai.api_key，以下为基于你打标数据的本地启发式解析；"
                "配置后升级为 LLM 深度解析。",
        **_local_semantic_fallback(goal_text, cap_block),
    }


def _local_semantic_fallback(goal_text: str, cap_block: str) -> dict:
    """无 LLM 时的本地投影解析降级：基于关键词命中 + 维度常识外推。"""
    text = goal_text.lower()
    # 简易维度词典: 关键词 -> (维度名, 所需技能, 隐性门槛)
    DIM_DICT = [
        ("硬件/电路/PCB/电子/焊接/原型", "全栈硬件开发", "模拟/数字电路、PCB设计、焊接、电源管理", "设备(示波器/焊台)、元器件渠道"),
        ("嵌入式/单片机/MCU/ESP32/树莓派/RTOS/固件", "嵌入式系统", "MCU、RTOS、驱动、通信协议、低功耗", "调试周期长，需底层思维"),
        ("机械/3D/打印/结构/外壳/传动", "机械结构与制造", "3D建模、3D打印、CAD、材料力学", "打印机/加工厂资源"),
        ("视觉/AI/机器学习/深度学习/CV/神经网络", "计算机视觉/AI", "CV、深度学习、模型部署、边缘推理", "算力、数据集"),
        ("软件/编程/后端/前端/APP/全栈/代码", "全栈软件整合", "通信协议、后端、前端、数据库", "架构能力"),
        ("项目/交付/产品/造物/独立", "独立项目交付", "项目管理、需求取舍、版本控制", "时间管理、抗孤独"),
        ("视频/内容/创作/UP主/博客/分享", "技术内容创作", "视频制作、叙事、社区运营", "表达欲与持续输出"),
    ]
    matched_dims = []
    for keys, name, req, barrier in DIM_DICT:
        for k in keys.split("/"):
            if k.strip() and k.strip() in text:
                matched_dims.append((name, req, barrier))
                break
    if not matched_dims:
        matched_dims = [("通用能力", "见目标描述", "需结合具体领域判断")]

    # 判断用户是否已有相关根: 在 cap_block 中粗略看是否有相似词
    dims = []
    for name, req, barrier in matched_dims:
        # 最近节点: 找 cap_block 中包含相关 root 词
        nearest = None
        for probe in ("软件开发", "硬件", "嵌入式", "机械", "视觉", "AI", "视频", "项目"):
            if probe in cap_block and any(p in name for p in ("软件", "硬件", "嵌入式", "机械", "视觉", "AI", "视频", "项目")):
                nearest = probe
                break
        dist = 0 if nearest else 6
        if nearest is None:
            dist = 6
        elif nearest in ("软件开发",) and name in ("全栈软件整合",):
            dist = 1
        else:
            dist = 4
        dims.append({
            "name": name,
            "meaning": f"目标要求具备「{name}」能力",
            "required": req,
            "hidden_barrier": barrier,
            "nearest_user_node": nearest,
            "nearest_distance": dist,
            "fill_path": [name] if dist >= 4 else [nearest, name],
            "note": "本地启发式推断" if nearest is None else "基于现有根外推",
        })
    return {
        "target_summary": f"目标「{goal_text}」被本地解析为以下能力维度的组合",
        "target_archetypes": ["（本地启发式，配置AI后更精确）"],
        "dimensions": dims,
        "approach_path": ["现有能力根", "→ 补齐最近缺口", "→ 目标态"],
        "first_steps": [f"从「{d['name']}」入手，先做一个最小可行性项目" for d in dims[:3]],
        "baseline_note": "本地降级：仅依据关键词命中做维度推断，未做深度语义解析；"
                        "配置 ai.api_key 后将由 LLM 基于通用知识做完整投影解析。",
    }
