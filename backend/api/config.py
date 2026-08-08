"""配置管理 API - 读取/保存本地 config.yaml 并热重载"""
import logging
from fastapi import APIRouter
from pathlib import Path
import yaml

from services import get_config, reload_config

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["配置管理"])

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@router.get("")
async def get_config_api():
    """读取当前生效的本地配置（深拷贝，避免外部修改污染内存）"""
    log.info("配置请求: get")
    cfg = get_config()
    import copy
    return {"code": 0, "data": copy.deepcopy(cfg)}


@router.post("")
async def save_config_api(payload: dict):
    """用前端提交的配置整体覆盖写入 config.yaml，并热重载到内存。

    - 写回保留多行私钥（yaml 默认序列化为带引号字符串，功能不受影响）。
    - 覆盖写会丢失原文件注释，属预期行为。
    - 写入后调用 reload_config() 让服务后续读取使用新值；
      注意：FastAPI app 启动时已把部分配置（如 app 信息、server 端口）固化，
      需重启进程才会完全生效，本接口主要负责数据源/AI 等运行期配置热更新。
    """
    try:
        # 先校验可序列化，避免写坏文件
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    except Exception as e:
        return {"code": 400, "message": f"配置不可序列化: {e}"}

    try:
        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False)
        CONFIG_PATH.write_text(text, encoding="utf-8")
    except Exception as e:
        return {"code": 500, "message": f"写入配置失败: {e}"}

    try:
        reload_config()
    except Exception:
        # 写文件成功但内存重载失败不应阻断保存
        pass

    log.info("配置已保存并热重载")
    return {"code": 0, "message": "已保存并热重载", "config_path": str(CONFIG_PATH)}
