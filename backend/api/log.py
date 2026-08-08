"""后端日志级别控制接口。

前端「后端日志」开关调用：
- GET  /api/logs/level  -> 查询当前级别（'INFO' / 'WARNING' ...）
- POST /api/logs/level  -> 设置级别（body: {"level": "INFO"|"WARNING"|"DEBUG"|"ERROR"}）

前端只关心“开/关”两态：开=INFO（打印每个接口的请求日志与业务 info），
关=WARNING（仅错误）。其它级别也允许，便于调试。
"""
import logging
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from services.log_config import get_level, set_level_by_name

router = APIRouter(prefix="/api/logs", tags=["日志"])

# 前端开关映射：开=INFO，关=WARNING
ON_LEVEL = "INFO"
OFF_LEVEL = "WARNING"


class LogLevelIn(BaseModel):
    level: str = OFF_LEVEL


@router.get("/level")
async def get_log_level():
    return {"code": 0, "data": {"level": logging.getLevelName(get_level())}}


@router.post("/level")
async def set_log_level(body: LogLevelIn):
    try:
        level = set_level_by_name(body.level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": {"level": logging.getLevelName(level)}}
