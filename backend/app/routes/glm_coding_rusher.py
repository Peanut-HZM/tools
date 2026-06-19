"""GLM-Coding Pro 抢购工具 API 路由"""

import logging
import threading
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.schemas.glm_coding_rusher_schemas import (
    RusherConfigRequest, RusherConfigResponse,
    LoginStatusResponse, RusherStatusResponse,
    RusherLogItem, RusherLogListResponse,
    LoginRequest, StartRequest,
)
from app.services.glm_coding_rusher_service import (
    open_login_window, check_login_valid, state_file_exists, get_state_path,
    validate_config, ConfigError,
    get_task_status, get_task_logs, start_rush, stop_rush,
    next_sale_time, format_countdown,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/glm-coding-rusher", tags=["GLM-Coding 抢购"])


# 内存配置（简化版，生产环境应存数据库）
_config_store = {
    "target_package": "pro",
    "sale_time": "10:00",
    "preheat_seconds": 90,
    "refresh_interval_ms": 500,
    "timeout_seconds": 60,
    "headless": False,
}
_config_lock = threading.Lock()


@router.post("/login")
def login(request: LoginRequest):
    """启动浏览器登录"""
    # 在后台线程中执行，避免阻塞 API
    def _run():
        open_login_window(headless=request.headless)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return {"success": True, "message": "登录窗口已打开，请在浏览器中完成登录"}


@router.get("/login-status", response_model=LoginStatusResponse)
def login_status():
    """检查登录状态"""
    exists = state_file_exists()
    if not exists:
        return LoginStatusResponse(
            logged_in=False, state_file_exists=False, message="未登录"
        )

    result = check_login_valid()
    return LoginStatusResponse(
        logged_in=result["valid"],
        state_file_exists=True,
        message=result["message"],
    )


@router.post("/config", response_model=RusherConfigResponse)
def save_config(request: RusherConfigRequest):
    """保存抢购配置"""
    config_dict = request.model_dump()
    try:
        validate_config(config_dict)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    with _config_lock:
        _config_store.update(config_dict)

    return RusherConfigResponse(**_config_store)


@router.get("/config", response_model=RusherConfigResponse)
def get_config():
    """获取当前配置"""
    with _config_lock:
        return RusherConfigResponse(**_config_store)


@router.post("/start")
def start(request: StartRequest = None):
    """启动抢购任务"""
    with _config_lock:
        config = dict(_config_store)

    if request and request.config_override:
        override = request.config_override.model_dump()
        try:
            validate_config(override)
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        config.update(override)

    try:
        validate_config(config)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = start_rush(config)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])

    return result


@router.post("/stop")
def stop():
    """停止抢购任务"""
    return stop_rush()


@router.get("/status", response_model=RusherStatusResponse)
def status():
    """获取抢购状态"""
    task = get_task_status()
    sale_time = _config_store.get("sale_time", "10:00")
    nxt = next_sale_time(sale_time)
    countdown = int((nxt - datetime.now()).total_seconds())

    return RusherStatusResponse(
        is_running=task["is_running"],
        current_phase=task["current_phase"],
        message=task["message"],
        next_sale_time=nxt.strftime("%Y-%m-%d %H:%M:%S"),
        countdown_seconds=countdown,
        last_error=task.get("last_error"),
    )


@router.get("/logs", response_model=RusherLogListResponse)
def logs(limit: int = 100):
    """获取抢购日志"""
    items = get_task_logs(limit=limit)
    return RusherLogListResponse(
        items=[RusherLogItem(**item) for item in items],
        total=len(items),
    )
