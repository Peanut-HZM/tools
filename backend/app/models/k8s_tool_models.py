"""K8s 控制台工具的 Pydantic 请求/响应 DTO 模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============ 连接配置创建 / 更新 ============

class CreateK8sManualRequest(BaseModel):
    """手动填写创建单条 K8s 连接配置"""
    name: str = Field(..., min_length=1, max_length=128, description="显示名")
    server: str = Field(..., min_length=1, max_length=512, description="API server URL")
    auth_type: str = Field(..., pattern="^(bearer_token|client_cert|basic_auth)$")
    # bearer_token 模式
    token: Optional[str] = Field(None, max_length=65536)
    # client_cert 模式
    client_cert: Optional[str] = Field(None, max_length=65536)
    client_key: Optional[str] = Field(None, max_length=65536)
    # basic_auth 模式
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    # 可选
    ca_cert: Optional[str] = Field(None, max_length=65536, description="集群 CA 证书（自签名）")
    namespace_filter: List[str] = Field(default_factory=list, description="只暴露指定 namespace")


class CreateK8sPasteRequest(BaseModel):
    """粘贴 kubeconfig 文本批量创建"""
    kubeconfig_text: str = Field(..., min_length=1, max_length=1_048_576)
    namespace_filter: List[str] = Field(default_factory=list)


class CreateK8sUploadRequest(BaseModel):
    """上传 kubeconfig 文件批量创建（文件由路由层处理，此处只是元数据）"""
    filename: str = Field(..., max_length=255)
    namespace_filter: List[str] = Field(default_factory=list)


class UpdateK8sRequest(BaseModel):
    """更新连接配置（仅允许改 name / namespace_filter）"""
    id: str = Field(..., min_length=1, max_length=64)
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    namespace_filter: Optional[List[str]] = None


class DeleteK8sRequest(BaseModel):
    """删除连接配置请求"""
    id: str = Field(..., min_length=1, max_length=64)


class UpdateK8sAuthRequest(BaseModel):
    """更新连接认证信息请求"""
    id: str = Field(..., min_length=1, max_length=64)
    token: Optional[str] = None  # bearer_token
    client_cert: Optional[str] = None  # client_cert
    client_key: Optional[str] = None  # client_cert
    username: Optional[str] = None  # basic_auth
    password: Optional[str] = None  # basic_auth
    ca_cert: Optional[str] = None  # 所有类型通用


# ============ 响应 ============

class K8sConfigResponse(BaseModel):
    """连接配置响应（脱敏：不含敏感字段原文）"""
    id: str
    user_id: str
    name: str
    source_type: str
    cluster_name: str
    context_name: str
    server: str
    auth_type: str
    has_auth_data: bool = Field(description="是否已配置认证信息")
    has_ca_cert: bool = Field(description="是否已配置 CA 证书")
    namespace_filter: List[str]
    is_metrics_available: bool
    last_test_at: Optional[datetime] = None
    last_test_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class K8sConnectionHealth(BaseModel):
    """连通性测试返回"""
    reachable: bool
    server_version: Optional[str] = None
    is_metrics_available: bool = False
    error: Optional[str] = None
    tested_at: datetime


# ============ 错误 ============

class K8sError(BaseModel):
    """K8s API 统一错误格式"""
    code: str = Field(description="CONNECTION_FAILED | FORBIDDEN | NOT_FOUND | METRICS_UNAVAILABLE | TIMEOUT")
    message: str
    k8s_reason: str = ""
    status_code: Optional[int] = None


class K8sApiException(Exception):
    """K8s API 异常，携带 K8sError 详情"""

    def __init__(self, error: K8sError):
        self.error = error
        super().__init__(error.message)


# ============ 资源查询响应 ============

class K8sNamespaceInfo(BaseModel):
    """Namespace 信息"""
    name: str
    status: str
    created_at: Optional[datetime] = None


class K8sPodSummary(BaseModel):
    """Pod 列表摘要"""
    name: str
    namespace: str
    status: str
    phase: str
    ready: str            # 如 "2/2"
    restarts: int
    node: str
    pod_ip: Optional[str] = None
    created_at: Optional[datetime] = None
    containers: List[str] = Field(default_factory=list)


class K8sPodDetail(BaseModel):
    """Pod 完整详情"""
    name: str
    namespace: str
    uid: str
    phase: str
    status: str
    node: str
    pod_ip: Optional[str] = None
    host_ip: Optional[str] = None
    qos_class: Optional[str] = None
    created_at: Optional[datetime] = None
    labels: dict = Field(default_factory=dict)
    annotations: dict = Field(default_factory=dict)
    containers: list = Field(default_factory=list)  # List[K8sContainerInfo]
    init_containers: list = Field(default_factory=list)
    conditions: list = Field(default_factory=list)
    owner_references: list = Field(default_factory=list)


class K8sContainerInfo(BaseModel):
    """容器详细信息"""
    name: str
    image: str
    ready: bool
    state: str            # running | waiting | terminated
    state_detail: str     # 具体原因（如 CrashLoopBackOff）
    restart_count: int
    started_at: Optional[datetime] = None
    resources_requests: dict = Field(default_factory=dict)
    resources_limits: dict = Field(default_factory=dict)


class K8sNodeSummary(BaseModel):
    """节点摘要信息"""
    name: str
    status: str           # Ready / NotReady
    roles: List[str]
    version: str          # kubelet 版本
    os_image: str
    kernel_version: str
    container_runtime: str
    created_at: Optional[datetime] = None
    conditions: list = Field(default_factory=list)
    capacity_cpu: Optional[str] = None
    capacity_memory: Optional[str] = None


class K8sWorkloadSummary(BaseModel):
    """工作负载摘要"""
    name: str
    namespace: str
    kind: str             # Deployment / ReplicaSet / StatefulSet / DaemonSet / Job / CronJob
    ready: str            # 如 "3/3"
    desired: int
    available: int
    images: List[str]
    created_at: Optional[datetime] = None
    labels: dict = Field(default_factory=dict)


class K8sEventInfo(BaseModel):
    """K8s 事件信息"""
    type: str             # Normal / Warning
    reason: str
    message: str
    object_kind: str
    object_name: str
    object_namespace: str
    count: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


class K8sMetricsPoint(BaseModel):
    """单个时间点的 CPU/内存指标"""
    timestamp: datetime
    cpu_usage_cores: float
    memory_usage_bytes: int


class K8sMetricsResponse(BaseModel):
    """资源指标响应"""
    available: bool
    cpu_usage_cores: Optional[float] = None
    memory_usage_bytes: Optional[int] = None
    cpu_request_ratio: Optional[float] = None
    memory_request_ratio: Optional[float] = None
    message: Optional[str] = None
