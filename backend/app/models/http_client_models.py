"""
HTTP Client 数据模型 - 支持完整的 API 工作区功能
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============= Collection Models =============

class CollectionBase(BaseModel):
    """请求集合基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="集合名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    workspace_id: str = Field(default="default", description="工作区 ID")
    parent_id: Optional[str] = Field(None, description="父集合 ID（支持嵌套）")
    sort_order: int = Field(default=0, description="排序")


class CollectionCreate(CollectionBase):
    """创建集合请求"""
    pass


class CollectionUpdate(BaseModel):
    """更新集合请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = None


class Collection(CollectionBase):
    """请求集合响应"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= HTTP Request Models =============

class HttpRequestBase(BaseModel):
    """HTTP 请求基础模型"""
    collection_id: str = Field(..., description="所属集合 ID")
    name: str = Field(..., min_length=1, max_length=100, description="请求名称")
    method: str = Field(default="GET", max_length=10, description="HTTP 方法")
    url: str = Field(..., description="请求 URL（可包含变量如 {{baseUrl}}）")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    params: Dict[str, str] = Field(default_factory=dict, description="查询参数")
    body_type: str = Field(default="none", description="请求体类型：json/form/raw/none")
    body: Optional[str] = Field(None, description="请求体")
    auth_type: str = Field(default="none", description="认证类型：bearer/basic/apikey/none")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="认证配置")
    description: str = Field(default="", max_length=5000, description="请求描述（Markdown）")
    sort_order: int = Field(default=0, description="排序")


class HttpRequestCreate(HttpRequestBase):
    """创建 HTTP 请求请求"""
    pass


class HttpRequestUpdate(BaseModel):
    """更新 HTTP 请求请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    method: Optional[str] = Field(None, max_length=10)
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    body_type: Optional[str] = None
    body: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(None, max_length=5000)
    sort_order: Optional[int] = None


class HttpRequest(HttpRequestBase):
    """HTTP 请求响应"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Environment Models =============

class EnvironmentBase(BaseModel):
    """环境变量基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="环境名称")
    workspace_id: str = Field(default="default", description="工作区 ID")
    variables: Dict[str, str] = Field(default_factory=dict, description="变量名 -> 值")
    is_active: bool = Field(default=False, description="是否激活")


class EnvironmentCreate(EnvironmentBase):
    """创建环境变量请求"""
    pass


class EnvironmentUpdate(BaseModel):
    """更新环境变量请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    variables: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class Environment(EnvironmentBase):
    """环境变量响应"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Request History Models =============

class RequestHistoryBase(BaseModel):
    """请求历史基础模型"""
    user_id: str = Field(..., description="用户 ID")
    request_id: Optional[str] = Field(None, description="关联的请求 ID（可选）")
    method: str = Field(..., max_length=10, description="HTTP 方法")
    url: str = Field(..., description="请求 URL")
    status_code: int = Field(..., description="响应状态码")
    response_time: int = Field(..., description="响应时间（毫秒）")
    request_data: Dict[str, Any] = Field(default_factory=dict, description="请求数据快照")
    response_data: Dict[str, Any] = Field(default_factory=dict, description="响应数据快照")


class RequestHistoryCreate(RequestHistoryBase):
    """创建请求历史请求"""
    pass


class RequestHistory(RequestHistoryBase):
    """请求历史响应"""
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ============= Send Request Models =============

class SendRequestRequest(BaseModel):
    """发送请求请求体"""
    method: str = Field(..., max_length=10, description="HTTP 方法")
    url: str = Field(..., description="目标 URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    params: Dict[str, str] = Field(default_factory=dict, description="查询参数")
    body_type: str = Field(default="none", description="请求体类型")
    body: Optional[str] = Field(None, description="请求体")
    timeout: int = Field(default=30000, description="超时时间（毫秒）")
    follow_redirects: bool = Field(default=True, description="是否跟随重定向")
    workspace_id: str = Field(default="default", description="工作区 ID")


class SendRequestResponse(BaseModel):
    """发送请求响应"""
    status_code: int
    headers: Dict[str, str]
    body: str
    response_time: int  # 毫秒
    content_type: Optional[str] = None


# ============= Import/Export Models =============

class ImportResult(BaseModel):
    """导入结果"""
    success: bool
    imported_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)


class CurlImportRequest(BaseModel):
    """cURL 导入请求体"""
    curl_command: str = Field(..., min_length=1, description="cURL 命令")
    collection_id: str = Field(..., description="目标集合 ID")
    name: str = Field(default="Imported Request", max_length=100, description="请求名称")


class ExportData(BaseModel):
    """导出数据"""
    collections: List[Collection]
    requests: List[HttpRequest]
    environments: List[Environment]


# ============= Sync Models =============

class SyncPushRequest(BaseModel):
    """推送同步请求"""
    entities: List[Dict[str, Any]] = Field(..., description="实体数据列表")
    entity_type: str = Field(..., description="实体类型：collection/request/environment")


class SyncPullResponse(BaseModel):
    """拉取同步响应"""
    entities: List[Dict[str, Any]]
    last_sync_time: datetime


class SyncStatusResponse(BaseModel):
    """同步状态响应"""
    is_synced: bool
    last_sync_time: Optional[datetime] = None
    pending_changes: int = 0
