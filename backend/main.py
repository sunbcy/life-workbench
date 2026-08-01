"""
生活工作台 - FastAPI 主入口
基于位置的生活比价与资源发现平台
"""
import yaml
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.price_compare import router as price_router
from api.nearby import router as nearby_router
from api.news import router as news_router
from api.weather import router as weather_router
from api.profile import router as profile_router
from api.feed import router as feed_router
from api.location import router as location_router
from api.interest_map import router as interest_map_router
from api.data import dashboard_stats, quick_actions
from services.recommendation import get_engine

# 注册维度分类树 (interests / health / location ...) 到通用框架
# 这些模块在导入时会调用 register_dimension, 供 /api/interest-map 路由使用
import services.interest_tree  # noqa: F401
import services.health_tree    # noqa: F401
import services.location_tree  # noqa: F401
import services.knowledge_tree # noqa: F401


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()
app = FastAPI(
    title=config["app"]["name"],
    version=config["app"]["version"],
    description=config["app"]["description"],
)

# CORS 中间件 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(price_router)
app.include_router(nearby_router)
app.include_router(news_router)
app.include_router(weather_router)
app.include_router(profile_router)
app.include_router(feed_router)
app.include_router(location_router)
app.include_router(interest_map_router)

# 初始化推荐引擎（启动时加载用户画像）
# 注意：print 内容不要带 emoji，否则在 Windows GBK 终端会抛 UnicodeEncodeError 导致进程退出
try:
    get_engine()
    print("[OK] 推荐引擎已初始化 - 用户画像已加载")
except Exception as e:
    print(f"[WARN] 推荐引擎初始化失败: {e}")


# ========== 仪表盘 API ==========

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """获取仪表盘统计数据"""
    return {"code": 0, "data": dashboard_stats}


@app.get("/api/dashboard/actions")
async def get_quick_actions():
    """获取快捷操作"""
    return {"code": 0, "data": quick_actions}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": config["app"]["version"],
        "location": config["location"]["city"],
    }


@app.get("/")
async def root():
    """根路径 - 重定向到前端"""
    return {
        "message": f"欢迎使用{config['app']['name']} API",
        "version": config["app"]["version"],
        "docs": "/docs",
        "frontend": "http://localhost:5173",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=config["server"]["reload"],
    )
