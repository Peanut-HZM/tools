"""
服务器监控数据模型 - 服务器/指标/告警相关请求与响应结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateMonitorServerRequest(BaseModel):
    """新建监控服务器请求"""
    name: str = Field(..., min_length=1, max_length=64)
    server_type: str = Field("ssh", pattern="^(local|ssh)$")
    host: Optional[str] = Field(None, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)
    group_name: Optional[str] = Field(None, max_length=64)


class UpdateMonitorServerRequest(BaseModel):
    """更新监控服务器请求（全部可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)
    group_name: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, pattern="^(enabled|disabled)$")


class MonitorServerResponse(BaseModel):
    """监控服务器响应"""
    id: str
    user_id: str
    name: str
    server_type: str
    host: str = ""
    port: int = 22
    username: str = ""
    group_name: Optional[str] = None
    status: str
    last_error: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    metric: Optional[dict] = None  # 最近一次采集指标（列表接口嵌入）


class ImportSSHRequest(BaseModel):
    """从 SSH 配置导入请求"""
    ssh_config_id: str = Field(..., min_length=1, max_length=64)


class TestMonitorServerRequest(BaseModel):
    """测试监控服务器连接请求"""
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)


class AlertRuleCreateRequest(BaseModel):
    """新建告警规则请求"""
    server_id: str = Field("all", min_length=1, max_length=64)
    metric: str = Field(..., pattern="^(cpu_percent|memory_percent|disk_percent|load_avg|net_recv_rate|net_sent_rate)$")
    operator: str = Field(..., pattern="^(>|>=|<|<=)$")
    threshold: float = Field(..., ge=0, le=1000000)
    duration: int = Field(3, ge=1, le=60)
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    """更新告警规则请求（全部可选）"""
    server_id: Optional[str] = None
    metric: Optional[str] = Field(None, pattern="^(cpu_percent|memory_percent|disk_percent|load_avg|net_recv_rate|net_sent_rate)$")
    operator: Optional[str] = Field(None, pattern="^(>|>=|<|<=)$")
    threshold: Optional[float] = Field(None, ge=0, le=1000000)
    duration: Optional[int] = Field(None, ge=1, le=60)
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    """告警规则响应"""
    id: str
    user_id: str
    server_id: str
    metric: str
    operator: str
    threshold: float
    duration: int
    enabled: bool
    created_at: datetime


class AlertLogResponse(BaseModel):
    """告警触发记录响应"""
    id: int
    rule_id: str
    server_id: str
    server_name: str
    metric: str
    actual_value: float
    status: str
    is_read: bool
    notified_at: datetime


class MonitorSettings(BaseModel):
    """监控设置"""
    webhook_url: Optional[str] = Field("", max_length=500)
    collect_interval: int = Field(30, ge=10, le=300)


class ServiceActionRequest(BaseModel):
    """服务操作请求"""
    action: str = Field(..., pattern="^(start|stop|restart)$")
