"""
HTTP Client 数据模型 - 支持完整的 API 工作区功能
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any, Union, Literal
from datetime import datetime


# ============= Key-Value 条目（支持启用/禁用与描述） =============

class KeyValueItem(BaseModel):
    """Key-Value 单条目（Headers / Params / urlencoded 通用）"""
    key: str = Field(default="", max_length=512, description="键名")
    value: str = Field(default="", max_length=100_000, description="值（支持 {{变量}}）")
    enabled: bool = Field(default=True, description="是否启用（禁用后不发送）")
    description: str = Field(default="", max_length=500, description="描述")


KeyValueInput = Union[Dict[str, str], List[KeyValueItem], None]


def normalize_kv(value: KeyValueInput) -> List[KeyValueItem]:
    """将 dict 或 list 形式的键值对统一归一化为 List[KeyValueItem]

    兼容历史数据（DB 中 headers/params 为 dict 格式）与新格式（list，支持启用/禁用）。
    """
    if value is None:
        return []
    if isinstance(value, dict):
        return [
            KeyValueItem(key=str(k), value=str(v), enabled=True, description="")
            for k, v in value.items()
            if k
        ]
    result: List[KeyValueItem] = []
    for item in value:
        if isinstance(item, KeyValueItem):
            result.append(item)
        elif isinstance(item, dict):
            # 过滤 dict 中 key 为空的条目
            if not str(item.get("key", "")):
                continue
            result.append(KeyValueItem(
                key=str(item.get("key", "")),
                value=str(item.get("value", "")),
                enabled=bool(item.get("enabled", True)),
                description=str(item.get("description", "") or ""),
            ))
    return result


def kv_to_list_payload(items: List[KeyValueItem]) -> List[Dict[str, Any]]:
    """序列化为可存储的 list 格式"""
    return [
        {"key": i.key, "value": i.value, "enabled": i.enabled, "description": i.description}
        for i in items
    ]


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
    parent_id: Optional[str] = None


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
    headers: KeyValueInput = Field(default_factory=list, description="请求头（dict 或 list 格式）")
    params: KeyValueInput = Field(default_factory=list, description="查询参数（dict 或 list 格式）")
    body_type: str = Field(
        default="none",
        description="请求体类型：json/xml/form/form-data/raw/binary/graphql/none",
    )
    body: Optional[str] = Field(None, description="请求体文本内容")
    form_data: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="form-data 条目（key/value/type/description）"
    )
    auth_type: str = Field(default="none", description="认证类型：bearer/basic/apikey/digest/none")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="认证配置")
    extract_variables: List[Dict[str, Any]] = Field(
        default_factory=list, description="后置提取变量规则"
    )
    assertions: List[Dict[str, Any]] = Field(
        default_factory=list, description="后置断言规则"
    )
    description: str = Field(default="", max_length=5000, description="请求描述（Markdown）")
    sort_order: int = Field(default=0, description="排序")

    @field_validator("headers", "params", mode="after")
    @classmethod
    def normalize_headers_params(cls, v):
        return kv_to_list_payload(normalize_kv(v))


class HttpRequestCreate(HttpRequestBase):
    """创建 HTTP 请求请求"""
    pass


class HttpRequestUpdate(BaseModel):
    """更新 HTTP 请求请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    method: Optional[str] = Field(None, max_length=10)
    url: Optional[str] = None
    headers: Optional[KeyValueInput] = None
    params: Optional[KeyValueInput] = None
    body_type: Optional[str] = None
    body: Optional[str] = None
    form_data: Optional[List[Dict[str, Any]]] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    extract_variables: Optional[List[Dict[str, Any]]] = None
    assertions: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = Field(None, max_length=5000)
    sort_order: Optional[int] = None

    @field_validator("headers", "params", mode="after")
    @classmethod
    def normalize_headers_params(cls, v):
        if v is None:
            return None
        return kv_to_list_payload(normalize_kv(v))


class HttpRequest(HttpRequestBase):
    """HTTP 请求响应"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def normalize_from_db(cls, data):
        """从 DB ORM/RealDictRow 读取时，将 dict 格式的 headers/params 归一化为 list"""
        if isinstance(data, dict):
            data["headers"] = kv_to_list_payload(normalize_kv(data.get("headers")))
            data["params"] = kv_to_list_payload(normalize_kv(data.get("params")))
        return data


# ============= Environment Models =============

class EnvironmentBase(BaseModel):
    """环境变量基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="环境名称")
    workspace_id: str = Field(default="default", description="工作区 ID")
    base_url: str = Field(default="", max_length=512, description="前置 URL（baseUrl），接口路径以 / 开头时自动拼接")
    variables: Dict[str, str] = Field(default_factory=dict, description="变量名 -> 值")
    is_active: bool = Field(default=False, description="是否激活")


class EnvironmentCreate(EnvironmentBase):
    """创建环境变量请求"""
    pass


class EnvironmentUpdate(BaseModel):
    """更新环境变量请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    base_url: Optional[str] = Field(None, max_length=512)
    variables: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class Environment(EnvironmentBase):
    """环境变量响应"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def normalize_base_url(cls, data):
        """兼容 DB 中不存在 base_url 列的历史行"""
        if isinstance(data, dict) and data.get("base_url") is None:
            data["base_url"] = ""
        return data


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

class FormDataEntry(BaseModel):
    """Form-data 单条目（强类型校验，防止 header-injection 和 DoS）"""
    key: str = Field(..., min_length=1, max_length=256, description="字段名（不可包含 \\r\\n\\\"）")
    value: Optional[str] = Field(default=None, max_length=35_000_000, description="字段值；file 类型时为 base64 data URL")
    type: Literal['text', 'file'] = Field(default='text', description="条目类型")
    enabled: bool = Field(default=True, description="是否启用")
    description: Optional[str] = Field(default=None, max_length=500, description="描述")


class AssertionRule(BaseModel):
    """可视化断言规则"""
    source: Literal['status', 'header', 'body_json', 'body_text', 'response_time'] = Field(
        default='status', description="断言对象来源：状态码/响应头/响应正文(JSON)/响应正文(文本)/耗时"
    )
    expression: str = Field(default="", max_length=500, description="提取表达式：JSONPath / Header 名 / 文本匹配")
    operator: Literal[
        'equal', 'not_equal', 'contains', 'not_contains',
        'greater_than', 'less_than', 'greater_or_equal', 'less_or_equal',
        'is_empty', 'not_empty', 'exists', 'not_exists',
        'regex_match', 'starts_with', 'ends_with',
    ] = Field(default='equal', description="比较方式")
    value: str = Field(default="", max_length=2000, description="断言目标值（支持 {{变量}}）")
    name: str = Field(default="", max_length=200, description="断言名称（可选，便于识别）")
    enabled: bool = Field(default=True, description="是否启用")


class ExtractVariableRule(BaseModel):
    """后置提取变量规则"""
    name: str = Field(..., min_length=1, max_length=100, description="目标变量名")
    source: Literal['body_json', 'body_text', 'header', 'status', 'response_time'] = Field(
        default='body_json', description="提取来源：响应 JSON（JSONPath）/ 响应文本（正则）/ 响应头 / 状态码 / 耗时"
    )
    expression: str = Field(default="", max_length=500, description="提取表达式：JSONPath / 正则 / Header 名")
    index: Optional[int] = Field(default=None, description="多匹配时取第几项（0 开始，空为全部/第一项）")
    enabled: bool = Field(default=True, description="是否启用")


class SendRequestRequest(BaseModel):
    """发送请求请求体"""
    method: str = Field(..., max_length=10, description="HTTP 方法")
    url: str = Field(..., description="目标 URL")
    headers: KeyValueInput = Field(default_factory=dict, description="请求头（dict 或 list）")
    params: KeyValueInput = Field(default_factory=dict, description="查询参数（dict 或 list）")
    body_type: str = Field(
        default="none",
        description="请求体类型：json|xml|form|form-data|raw|binary|graphql|none",
    )
    body: Optional[str] = Field(None, description="请求体；binary 类型时为 base64 data URL")
    form_data: Optional[List[FormDataEntry]] = Field(
        default=None,
        max_length=100,
        description="form-data 条目列表，最多 100 项；file 类型 value 为 base64 data URL",
    )
    auth_type: str = Field(default="none", description="认证类型：bearer/basic/apikey/none")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="认证配置")
    assertions: List[AssertionRule] = Field(default_factory=list, description="断言规则（发送后执行）")
    extract_variables: List[ExtractVariableRule] = Field(
        default_factory=list, description="提取变量规则（发送后执行，结果写入激活环境）"
    )
    request_id: Optional[str] = Field(default=None, description="关联的已保存请求 ID（历史记录用）")
    timeout: int = Field(default=30000, description="超时时间（毫秒）")
    follow_redirects: bool = Field(default=True, description="是否跟随重定向")
    workspace_id: str = Field(default="default", description="工作区 ID")

    @field_validator("headers", "params", mode="after")
    @classmethod
    def normalize_headers_params(cls, v):
        return kv_to_list_payload(normalize_kv(v))


class AssertionResult(BaseModel):
    """单条断言执行结果"""
    name: str = Field(default="", description="断言名称")
    source: str = Field(default="", description="断言来源")
    expression: str = Field(default="", description="提取表达式")
    operator: str = Field(default="", description="比较方式")
    expected: str = Field(default="", description="期望值")
    actual: str = Field(default="", description="实际值")
    passed: bool = Field(default=False, description="是否通过")
    message: str = Field(default="", description="附加说明（如提取失败原因）")


class SendRequestResponse(BaseModel):
    """发送请求响应"""
    status_code: int
    status_text: str = Field(default="", description="状态码描述")
    headers: Dict[str, str]
    body: str
    response_time: int  # 毫秒
    size: int = Field(default=0, description="响应体字节数")
    content_type: Optional[str] = None
    request_url: str = Field(default="", description="实际发送的最终 URL（含 query）")
    request_headers: Dict[str, str] = Field(default_factory=dict, description="实际发送的请求头（含认证注入）")
    extracted_variables: Dict[str, str] = Field(default_factory=dict, description="提取变量执行结果")
    assertion_results: List[AssertionResult] = Field(default_factory=list, description="断言执行结果")
    error: Optional[str] = Field(default=None, description="网络错误信息（连接失败/超时等）")


# ============= Import/Export Models =============

class ImportResult(BaseModel):
    """导入结果"""
    success: bool
    imported_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)
    collection_id: Optional[str] = None


class CurlImportRequest(BaseModel):
    """cURL 导入请求体"""
    curl_command: str = Field(..., min_length=1, description="cURL 命令")
    collection_id: str = Field(..., description="目标集合 ID")
    name: str = Field(default="Imported Request", max_length=100, description="请求名称")


class CurlParseResult(BaseModel):
    """cURL 解析结果（不落库，供前端预览/快速填充）"""
    method: str
    url: str
    headers: List[Dict[str, Any]]
    params: List[Dict[str, Any]]
    body: Optional[str] = None
    body_type: str = "none"
    auth_type: str = "none"
    auth_config: Dict[str, Any] = Field(default_factory=dict)


class OpenApiImportRequest(BaseModel):
    """OpenAPI/Swagger 导入请求体"""
    spec: str = Field(..., min_length=1, description="OpenAPI/Swagger JSON 或 YAML 文本")
    collection_id: str = Field(..., description="目标集合 ID")
    import_path_params: bool = Field(default=True, description="是否将 path 参数合并进 URL")


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
