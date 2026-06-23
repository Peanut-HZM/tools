"""GLM-Coding Pro 抢购工具 Pydantic 模型"""

import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RusherConfigRequest(BaseModel):
    """配置请求"""
    target_package: str = Field(default="pro", description="目标套餐")
    sale_time: str = Field(default="10:00", description="每天开抢时间 HH:MM")
    preheat_seconds: int = Field(default=90, ge=30, description="提前预热秒数")
    refresh_interval_ms: int = Field(default=500, ge=200, description="刷新间隔毫秒")
    timeout_seconds: int = Field(default=60, ge=10, le=600, description="抢购超时秒数")
    headless: bool = Field(default=False, description="是否无头浏览器")


class RusherConfigResponse(BaseModel):
    """配置响应"""
    target_package: str
    sale_time: str
    preheat_seconds: int
    refresh_interval_ms: int
    timeout_seconds: int
    headless: bool


class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    logged_in: bool
    state_file_exists: bool
    login_time: Optional[str] = None
    message: str


class RusherStatusResponse(BaseModel):
    """抢购状态响应"""
    is_running: bool
    current_phase: str = Field(description="idle|preheating|refreshing|clicking|awaiting_payment|success|failed")
    message: str
    next_sale_time: Optional[str] = None
    countdown_seconds: Optional[int] = None
    last_error: Optional[str] = None
    payment_url: Optional[str] = None
    payment_state_file: Optional[str] = None


class PaymentInfoResponse(BaseModel):
    """支付信息响应"""
    has_payment: bool
    payment_url: Optional[str] = None
    browser_alive: bool
    message: str


class RusherLogItem(BaseModel):
    """日志条目"""
    id: str
    task_id: str
    phase: str
    message: str
    created_at: datetime


class RusherLogListResponse(BaseModel):
    """日志列表响应"""
    items: List[RusherLogItem]
    total: int


class LoginRequest(BaseModel):
    """登录请求"""
    headless: bool = Field(default=False, description="是否无头浏览器登录（调试用）")


class StartRequest(BaseModel):
    """启动抢购请求"""
    config_override: Optional[RusherConfigRequest] = None


class TaskSummary(BaseModel):
    """抢购任务摘要"""
    id: str
    result: str
    target_package: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    refresh_count: int
    payment_url: Optional[str] = None


class TaskDetail(TaskSummary):
    """抢购任务详情（含完整配置快照）"""
    config_snapshot: dict


class TaskListResponse(BaseModel):
    """抢购任务列表响应"""
    items: List[TaskSummary]
    total: int
