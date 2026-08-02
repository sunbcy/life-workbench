"""用户画像 API 路由"""
from pathlib import Path
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.recommendation import get_engine, reload_engine

router = APIRouter(prefix="/api/profile", tags=["用户画像"])

# Profile 文件目录
PROFILE_DIR = Path.home() / ".life-workbench" / "profile"

# 合法的维度名称
VALID_DIMENSIONS = [
    "interests", "location", "schedule", "preferences",
    "health", "social", "budget",
]

# ========== 维度模板 ==========
DIMENSION_TEMPLATES = {
    "interests": """# ============================================================
# 兴趣与技能 Profile  (推荐权重: 30% - 核心维度)
# ============================================================
# 定义你的技能、爱好、学习目标和长期关注话题。
# 推荐引擎会优先匹配与这些关键词相关的内容。

# ---- 技能 (专业能力，影响科技/行业资讯推荐) ----
skills:
  # level: 1=入门  2=初级  3=中级  4=高级  5=专家
  - name: "填写你的技能"
    level: 3
    category: "programming"

# ---- 爱好 (影响生活/娱乐/活动推荐) ----
hobbies:
  # frequency: daily / weekly / monthly / occasionally
  - name: "填写你的爱好"
    frequency: "weekly"
    category: "fitness"

# ---- 学习目标 (影响教育资源、课程推荐) ----
learning_goals:
  # priority: high / medium / low
  - topic: "填写学习目标"
    priority: "medium"

# ---- 长期关注话题 (持续匹配相关资讯) ----
# weight: 1.0=极度关注  0.5=一般关注
tracking_topics:
  - keyword: "填写关注的话题"
    weight: 0.8

# ---- 排除话题 (自动过滤) ----
excluded_topics:
  - "填写想屏蔽的话题"
""",
    "location": """# ============================================================
# 地理位置 Profile  (推荐权重: 20% - 核心维度)
# ============================================================
# 精确的地理位置信息，驱动周边推荐、通勤资讯、搜索半径。
# 经纬度可通过高德/百度地图拾取: https://lbs.amap.com/tools/picker

# ---- 家 ----
home:
  address: "填写家庭地址"
  lat: 22.5431
  lng: 113.9298
  label: "家"

# ---- 公司 ----
work:
  address: "填写公司地址"
  lat: 22.5370
  lng: 113.9517
  label: "公司"

# ---- 常去地点 ----
frequent_places:
  - name: "填写地点名"
    lat: 22.5180
    lng: 113.9460
    frequency: "weekly"       # daily / weekly / biweekly / monthly
    category: "entertainment" # food / shopping / entertainment / health / education

# ---- 通勤 ----
commute:
  mode: "地铁"               # 地铁 / 开车 / 公交 / 步行 / 骑行
  home_to_work_min: 30

# ---- 搜索半径 (各品类推荐范围) ----
search_radius_km:
  default: 3.0
  food: 2.0
  shopping: 5.0
  entertainment: 8.0
  health: 3.0
""",
    "schedule": """# ============================================================
# 时间日程 Profile  (推荐权重: 15% - 重要维度)
# ============================================================
# 定义你每周的例行安排，影响推荐时机和类型。
# slot 格式: HH:MM-HH:MM
# availability: free(空闲,可接受推荐) / busy(忙碌,减少推荐)

routine:
  # ---- 工作日 ----
  weekday:
    - slot: "09:00-12:00"
      activity: "工作时间"
      availability: "busy"
    - slot: "12:00-13:30"
      activity: "午休"
      availability: "free"
    - slot: "13:30-18:30"
      activity: "工作时间"
      availability: "busy"
    - slot: "19:30-22:30"
      activity: "自由时间"
      availability: "free"

  # ---- 周末 ----
  weekend:
    - slot: "08:00-12:00"
      activity: "晨间活动"
      availability: "free"
    - slot: "12:00-22:00"
      activity: "全天自由"
      availability: "free"
""",
    "preferences": """# ============================================================
# 消费偏好 Profile  (推荐权重: 12% - 重要维度)
# ============================================================
# 定义你的购物习惯、饮食口味和娱乐偏好。
# 直接影响比价商品排序和周边餐饮/活动推荐。

# ---- 购物偏好 ----
shopping:
  preferred_stores:
    - "填写常去的超市/平台"
  priority_categories:
    - "填写优先关注的品类"
  avoided_categories:
    - "填写不感兴趣的品类"

# ---- 饮食口味 ----
food:
  cuisines:
    - { name: "填写喜欢的菜系", weight: 1.0 }
  avoided_cuisines:
    - "填写忌口的菜系"
  dietary_restrictions:
    - "填写饮食限制"

# ---- 娱乐偏好 ----
entertainment:
  types:
    - { name: "填写娱乐类型", weight: 0.9 }
  avoided_types:
    - "填写不喜欢的娱乐"
""",
    "health": """# ============================================================
# 健康数据 Profile  (推荐权重: 10% - 辅助维度)
# ============================================================
# 健康相关数据，影响饮食、运动、健康资讯推荐。

# ---- 基本信息 ----
basic_info:
  age: 25
  gender: "male"             # male / female / other
  height_cm: 170
  weight_kg: 65

# ---- 运动健身 ----
fitness:
  weekly_exercise_frequency: 2
  preferred_exercise:
    - "填写喜欢的运动"
  activity_level: "moderate"  # sedentary / light / moderate / active / very_active

# ---- 健康目标 ----
health_goals:
  - type: "weight_maintenance"
    target: "填写健康目标"

# ---- 健康关注项 ----
health_concerns:
  - "填写健康关注项"

# ---- 饮食目标 ----
diet_goals:
  calorie_target: 2000
  protein_ratio: 0.25
  preferred_diet: "均衡"      # 均衡 / 低碳 / 高蛋白 / 素食

# ---- 睡眠 ----
sleep_schedule:
  target_bedtime: "23:30"
  target_wakeup: "07:30"
""",
    "social": """# ============================================================
# 社交偏好 Profile  (推荐权重: 8% - 辅助维度)
# ============================================================
# 社交倾向影响活动推荐和场所选择。

# ---- 性格 ----
personality:
  introvert_extrovert: 0.5     # 0=极度内向  0.5=平衡  1=极度外向
  crowd_tolerance: "medium"    # low / medium / high

# ---- 人群偏好 ----
crowd_preference:
  max_crowd_level: 5           # 1-10, 10=最拥挤
  peak_hour_avoidance: false   # 是否避开高峰

# ---- 社交活动偏好 ----
social_activities:
  preferred:
    - type: "填写社交活动类型"
    - type: "填写社交活动类型"
""",
    "budget": """# ============================================================
# 预算限制 Profile  (推荐权重: 5% - 参考维度)
# ============================================================
# 月度预算和价格敏感度，影响比价推荐强度。

# ---- 月度预算 (元) ----
monthly_budget:
  groceries: 2000
  dining_out: 1500
  shopping: 1000
  entertainment: 800
  transport: 500
  health: 500

# ---- 价格敏感度 (high/medium/low) ----
price_sensitivity:
  groceries: "high"
  dining_out: "medium"
  shopping: "high"
  digital_products: "high"
  entertainment: "low"

# ---- 降价提醒阈值 ----
alert_thresholds:
  price_drop_pct: 15           # 降价超过此百分比时提醒
  target_save_monthly: 500     # 月度省钱目标
""",
}


class RawProfileUpdate(BaseModel):
    content: str


# ========== 快捷画像编辑: 直接更新 interests.yaml 顶层字段 ==========
class InterestsFieldsUpdate(BaseModel):
    learning_goals: list | None = None
    tracking_topics: list | None = None
    excluded_topics: list | None = None
    hobbies: list | None = None


@router.get("/summary")
async def get_profile_summary():
    """获取用户画像摘要（脱敏，不暴露原始数据）"""
    engine = get_engine()
    return {"code": 0, "data": engine.profile_summary}


@router.get("/dimensions")
async def get_dimensions():
    """获取各维度的权重和激活状态"""
    engine = get_engine()
    return {"code": 0, "data": engine.dimensions}


@router.post("/reload")
async def reload_profile():
    """重新加载本地 profile 文件"""
    reload_engine()
    engine = get_engine()
    return {
        "code": 0,
        "message": "Profile 已重新加载",
        "data": engine.profile_summary,
    }


# ========== 读写原始 YAML 文件 ==========

@router.get("/interests")
async def get_interests_fields():
    """读取 interests.yaml 的顶层意图字段(结构化, 供快捷编辑表单回填)。

    自动过滤树派生 (_derived) 项, 仅返回用户手填项。
    """
    file_path = PROFILE_DIR / "interests.yaml"

    if not file_path.exists():
        return {
            "code": 0,
            "data": {
                "learning_goals": [],
                "tracking_topics": [],
                "excluded_topics": [],
                "hobbies": [],
                "is_new": True,
            },
        }

    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")

    def _user_items(items):
        """保留非派生的手写项"""
        if not isinstance(items, list):
            return []
        return [i for i in items if not (isinstance(i, dict) and i.get("_derived"))]

    return {
        "code": 0,
        "data": {
            "learning_goals": _user_items(data.get("learning_goals", [])),
            "tracking_topics": _user_items(data.get("tracking_topics", [])),
            "excluded_topics": [e for e in data.get("excluded_topics", []) if isinstance(e, str)],
            "hobbies": _user_items(data.get("hobbies", [])),
            "is_new": False,
        },
    }


@router.get("/raw/{dimension}")
async def get_raw_profile(dimension: str):
    """读取某个维度的 YAML 内容。文件不存在时返回模板。"""
    if dimension not in VALID_DIMENSIONS:
        raise HTTPException(status_code=400, detail=f"无效的维度: {dimension}")

    file_path = PROFILE_DIR / f"{dimension}.yaml"
    if file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8")
            return {"code": 0, "data": {"dimension": dimension, "content": content, "is_new": False}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取失败: {e}")

    # 文件不存在 → 返回模板
    template = DIMENSION_TEMPLATES.get(dimension, "# 请填写配置\n")
    return {"code": 0, "data": {"dimension": dimension, "content": template, "is_new": True}}


@router.put("/raw/{dimension}")
async def update_raw_profile(dimension: str, body: RawProfileUpdate):
    """更新/创建某个维度的 YAML 文件并热重载"""
    if dimension not in VALID_DIMENSIONS:
        raise HTTPException(status_code=400, detail=f"无效的维度: {dimension}")

    # 验证 YAML 语法
    try:
        yaml.safe_load(body.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 语法错误: {e}")

    # 确保目录存在
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    file_path = PROFILE_DIR / f"{dimension}.yaml"
    try:
        file_path.write_text(body.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")

    # 热重载推荐引擎
    reload_engine()
    engine = get_engine()

    return {
        "code": 0,
        "message": f"{dimension}.yaml 已保存并重载",
        "data": engine.profile_summary,
    }


# ========== 一键初始化 ==========

@router.put("/interests/fields")
async def update_interests_fields(body: InterestsFieldsUpdate):
    """快捷画像编辑: 直接更新 interests.yaml 的顶层意图字段并热重载。

    仅覆盖传入的字段, 保留 skills / 树派生结果 / 其它字段不变。
    列表字段会整体替换(方便表单维护)。
    """
    import copy

    file_path = PROFILE_DIR / "interests.yaml"
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # 读取现有数据 (不存在则基于模板解析)
    if file_path.exists():
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取失败: {e}")
    else:
        data = yaml.safe_load(DIMENSION_TEMPLATES["interests"]) or {}

    if not isinstance(data, dict):
        data = {}

    field_map = {
        "learning_goals": body.learning_goals,
        "tracking_topics": body.tracking_topics,
        "excluded_topics": body.excluded_topics,
        "hobbies": body.hobbies,
    }

    updated = []
    for key, value in field_map.items():
        if value is None:
            continue
        # 对 list[dict] 字段: 保留树派生 (_derived) 项 + 用户手填表单项
        # 对 list[str]  字段: 直接整体替换 (excluded_topics 无派生项)
        existing = data.get(key, [])
        merged = list(value)
        if (
            isinstance(existing, list)
            and existing
            and isinstance(existing[0], dict)
            and isinstance(value, list)
            and (value and isinstance(value[0], dict))
        ):
            derived = [e for e in existing if isinstance(e, dict) and e.get("_derived")]
            merged = derived + list(value)
        data[key] = copy.deepcopy(merged)
        updated.append(key)

    # 写回 (保持顺序: 用现有内容追加未出现的键)
    try:
        file_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")

    reload_engine()
    engine = get_engine()

    return {
        "code": 0,
        "message": f"已更新字段: {', '.join(updated) or '无'}",
        "data": engine.profile_summary,
    }




@router.post("/init-all")
async def init_all_dimensions():
    """一键初始化全部 7 个维度的 profile 文件（已存在的不会被覆盖）"""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    created = []
    skipped = []

    for dim in VALID_DIMENSIONS:
        file_path = PROFILE_DIR / f"{dim}.yaml"
        if file_path.exists():
            skipped.append(dim)
        else:
            template = DIMENSION_TEMPLATES.get(dim, "# 请填写配置\n")
            file_path.write_text(template, encoding="utf-8")
            created.append(dim)

    reload_engine()
    engine = get_engine()

    return {
        "code": 0,
        "message": f"初始化完成: 新建 {len(created)} 个, 跳过 {len(skipped)} 个",
        "data": {
            "created": created,
            "skipped": skipped,
            "summary": engine.profile_summary,
        },
    }
