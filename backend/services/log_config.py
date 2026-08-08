"""集中式日志配置（单例）。

工程常用做法：
- 全工程统一用一个 root logger，模块内通过 logging.getLogger(__name__) 取子 logger；
- 仅在此处挂载一次 handler 与 formatter（避免重复 addHandler 导致日志重复）；
- 支持运行时切换 level（开=DEBUG/INFO，关=WARNING），并持久化到磁盘，重启仍生效；
- 后端默认关闭详细日志（level=WARNING），前端「后端日志」开关打开时切到 INFO。

默认关而不是开，避免在弱网/移动设备上产生大量无意义的请求日志。
"""
import logging
import os
from pathlib import Path

# 持久化文件路径（与 config.yaml 同级目录）
_LEVEL_FILE = Path(__file__).resolve().parent.parent / "log_level.txt"

_DEFAULT_LEVEL = logging.WARNING  # 默认只显示 WARNING 及以上（即“关闭详细日志”）
_CONFIGURED = False

# 全局 handler 引用，便于切换 level 时只改 logger 级别即可
_root = logging.getLogger("life_workbench")


def _read_persisted_level() -> int:
    try:
        if _LEVEL_FILE.exists():
            val = _LEVEL_FILE.read_text(encoding="utf-8").strip().upper()
            return logging.getLevelName(val)
    except Exception:
        pass
    return _DEFAULT_LEVEL


def _write_persisted_level(level: int) -> None:
    try:
        _LEVEL_FILE.write_text(logging.getLevelName(level), encoding="utf-8")
    except Exception:
        pass


def configure_logging() -> None:
    """初始化 logger（幂等，仅执行一次）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    _root.setLevel(logging.DEBUG)  # 根保持 DEBUG，由 handler 控制实际输出阈值

    handler = logging.StreamHandler()
    handler.setLevel(_read_persisted_level())
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(fmt)
    # 防止第三方库（uvicorn 等）的日志被重复处理
    _root.propagate = False
    _root.addHandler(handler)

    _CONFIGURED = True
    logging.getLogger(__name__).info("日志系统已初始化，当前级别=%s", logging.getLevelName(handler.level))


def get_level() -> int:
    """返回当前生效的日志级别。"""
    if not _root.handlers:
        return _read_persisted_level()
    return _root.handlers[0].level


def set_level(level: int) -> int:
    """运行时切换日志级别（持久化），返回切换后的级别。"""
    configure_logging()
    for h in _root.handlers:
        h.setLevel(level)
    _write_persisted_level(level)
    logging.getLogger(__name__).info("日志级别已切换为 %s", logging.getLevelName(level))
    return level


def set_level_by_name(name: str) -> int:
    level = logging.getLevelName(name.strip().upper())
    if not isinstance(level, int):
        raise ValueError(f"未知日志级别: {name}")
    return set_level(level)


def log_entry(func):
    """轻量装饰器：在接口进入时打印一行 INFO 日志（方法 路由函数名）。

    用法：
        @router.get("/x")
        @log_entry
        async def handler(...): ...
    """
    import functools

    sig = getattr(func, "__name__", "handler")

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logging.getLogger("life_workbench.api").info("接口调用: %s", sig)
        return await func(*args, **kwargs)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logging.getLogger("life_workbench.api").info("接口调用: %s", sig)
        return func(*args, **kwargs)

    return async_wrapper if _is_coroutine(func) else sync_wrapper


def _is_coroutine(func) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(func)
