"""GLM-Coding Pro 抢购工具 API 路由"""

import logging
import threading
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.schemas.glm_coding_rusher_schemas import (
    RusherConfigRequest, RusherConfigResponse,
    LoginStatusResponse, RusherStatusResponse, PaymentInfoResponse,
    RusherLogItem, RusherLogListResponse,
    LoginRequest, StartRequest,
    TaskSummary, TaskDetail, TaskListResponse,
)
from app.services.glm_coding_rusher_service import (
    open_login_window, check_login_valid, state_file_exists, get_state_path,
    validate_config, ConfigError,
    get_task_status, get_task_logs, start_rush, stop_rush,
    close_payment_window,
    next_sale_time, format_countdown,
    list_task_records, get_task_logs_from_db,
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
        payment_url=task.get("payment_url"),
        payment_state_file=task.get("payment_state_file"),
    )


@router.get("/payment-info", response_model=PaymentInfoResponse)
def payment_info():
    """获取支付信息"""
    task = get_task_status()
    payment_url = task.get("payment_url")
    has_payment = bool(payment_url and task.get("current_phase") == "awaiting_payment")

    from app.services.glm_coding_rusher_service import _payment_browser
    browser_alive = _payment_browser is not None

    if has_payment:
        return PaymentInfoResponse(
            has_payment=True,
            payment_url=payment_url,
            browser_alive=browser_alive,
            message="请在弹出的浏览器窗口中完成支付",
        )
    return PaymentInfoResponse(
        has_payment=False,
        payment_url=None,
        browser_alive=browser_alive,
        message="暂无待支付的订单",
    )


@router.post("/close-payment")
def close_payment():
    """手动关闭支付浏览器"""
    return close_payment_window()
@router.get("/logs")
def logs(limit: int = 100, task_id: str = None):
    """获取抢购日志"""
    items = get_task_logs(task_id=task_id, limit=limit)
    return RusherLogListResponse(
        items=[RusherLogItem(**item) for item in items],
        total=len(items),
    )


@router.get("/tasks", response_model=TaskListResponse)
def tasks(limit: int = 50):
    """获取抢购任务记录列表"""
    records = list_task_records(limit=limit)
    summaries = [
        TaskSummary(
            id=r["id"],
            result=r["result"],
            target_package=r["target_package"],
            started_at=r["started_at"],
            ended_at=r["ended_at"],
            refresh_count=r["refresh_count"],
            payment_url=r["payment_url"],
        )
        for r in records
    ]
    return TaskListResponse(items=summaries, total=len(summaries))


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def task_detail(task_id: str):
    """获取单个任务详情"""
    records = list_task_records(limit=1000)
    matched = next((r for r in records if r["id"] == task_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskDetail(**matched)


@router.get("/tasks/{task_id}/logs", response_model=RusherLogListResponse)
def task_logs(task_id: str, limit: int = 500):
    """获取指定任务的日志（从 DB 查询）"""
    items = get_task_logs_from_db(task_id=task_id, limit=limit)
    return RusherLogListResponse(
        items=[RusherLogItem(**item) for item in items],
        total=len(items),
    )
