from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum

class RedisKeyType(str, Enum):
    STRING = "string"
    LIST = "list"
    SET = "set"
    ZSET = "zset"
    HASH = "hash"
    NONE = "none"

class RedisConfigBase(BaseModel):
    alias: str = Field(..., min_length=2, max_length=32, description="配置别名")
    host: str = Field(..., description="主机地址")
    port: int = Field(6379, ge=1, le=65535, description="端口号")
    username: Optional[str] = Field(None, description="用户名")
    db: int = Field(0, ge=0, le=15, description="数据库索引")
    group_name: Optional[str] = Field(None, max_length=50, description="分组名称")
    is_active: bool = Field(True, description="是否激活")

class CreateRedisRequest(RedisConfigBase):
    password: Optional[str] = Field(None, description="密码")

class UpdateRedisRequest(BaseModel):
    alias: Optional[str] = Field(None, min_length=2, max_length=32)
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None
    db: Optional[int] = Field(None, ge=0, le=15)
    group_name: Optional[str] = None
    is_active: Optional[bool] = None

class RedisConfigResponse(RedisConfigBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

class TestConnectionRequest(BaseModel):
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    db: int = 0

class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    elapsed_ms: Optional[float] = None
    version: Optional[str] = None

class RedisKeyInfo(BaseModel):
    key: str
    type: str
    ttl: int
    size: Optional[int] = None

class RedisKeyContent(BaseModel):
    key: str
    type: str
    ttl: int
    value: Any
    memory_usage: Optional[int] = None

class KeyOperationRequest(BaseModel):
    key: str
    type: RedisKeyType
    value: Any
    ttl: Optional[int] = -1

class KeyDeleteRequest(BaseModel):
    keys: List[str]

class KeyTTLRequest(BaseModel):
    key: str
    ttl: int = Field(..., ge=-1, description="TTL 秒数，-1 表示永不过期")

class KeyPersistRequest(BaseModel):
    key: str

class KeysScanRequest(BaseModel):
    pattern: str = Field("*", description="Key 模式")
    key_type: Optional[str] = Field(None, description="Key 类型过滤")
    cursor: int = Field(0, ge=0, description="SCAN cursor")
    count: int = Field(20, ge=1, le=1000, description="每次返回数量")

class KeysScanResponse(BaseModel):
    cursor: int
    keys: List[RedisKeyInfo]
    has_more: bool

class KeyExportRequest(BaseModel):
    keys: List[str]
    format: str = Field("json", description="导出格式")

class KeyExportResponse(BaseModel):
    data: str
    count: int

class KeyImportRequest(BaseModel):
    data: str
    format: str = Field("json", description="导入格式")
    overwrite: bool = Field(False, description="是否覆盖已存在的 key")

class KeyImportResponse(BaseModel):
    success_count: int
    failed_count: int
    errors: List[Dict[str, str]] = []

class LuaScriptRequest(BaseModel):
    script: str
    keys: List[str] = Field(default_factory=list, description="KEYS 参数")
    args: List[Any] = Field(default_factory=list, description="ARGV 参数")

class LuaScriptResponse(BaseModel):
    result: Any
    execution_time_ms: float

class ScriptTemplate(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    script: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class CreateScriptTemplateRequest(BaseModel):
    name: str
    description: str
    script: str

class UpdateScriptTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script: Optional[str] = None

class CLICommandRequest(BaseModel):
    command: str = Field(..., description="Redis CLI 命令")

class CLICommandResponse(BaseModel):
    result: Any
    error: Optional[str] = None
    execution_time_ms: float


class BatchTTLRequest(BaseModel):
    keys: List[str]
    ttl: int = Field(..., ge=-1, description="TTL 秒数，-1 表示永久")


class BatchRenameRequest(BaseModel):
    keys: List[str]
    pattern: str = Field(..., description="匹配模式，支持 * 通配符")
    replacement: str = Field(..., description="替换字符串")


class MonitorInfo(BaseModel):
    used_memory: int
    used_memory_human: str
    used_memory_rss: int
    used_memory_peak: int
    connected_clients: int
    maxclients: int
    keyspace_hits: int
    keyspace_misses: int
    hit_rate: float
    ops_per_sec: int
    db_keyspace: Dict[str, Dict[str, int]]


class SlowLogEntry(BaseModel):
    id: int
    timestamp: int
    duration_ms: int
    command: str


class SlowLogResponse(BaseModel):
    entries: List[SlowLogEntry]


class StreamEntry(BaseModel):
    id: str
    fields: Dict[str, str]


class StreamInfo(BaseModel):
    length: int
    entries: List[StreamEntry]
    groups: List[Dict[str, Any]]


class StreamOperationRequest(BaseModel):
    action: str = Field(..., description="add|delete|trim|create_group|destroy_group")
    entry_id: Optional[str] = None
    fields: Optional[Dict[str, str]] = None
    group_name: Optional[str] = None
    trim_count: Optional[int] = None


class BitmapInfo(BaseModel):
    bit_count: int
    size_in_bytes: int
    bit_length: int


class BitmapOperationRequest(BaseModel):
    action: str = Field(..., description="getbit|setbit|bitcount|bitpos")
    offset: Optional[int] = None
    value: Optional[int] = Field(None, ge=0, le=1)
    start: Optional[int] = None
    end: Optional[int] = None


class HyperLogLogInfo(BaseModel):
    cardinality: int


class HyperLogLogOperationRequest(BaseModel):
    action: str = Field(..., description="add|count|merge")
    elements: Optional[List[str]] = None
    source_keys: Optional[List[str]] = None


class GeoPoint(BaseModel):
    member: str
    longitude: float
    latitude: float


class GeoInfo(BaseModel):
    members: List[GeoPoint]


class GeoOperationRequest(BaseModel):
    action: str = Field(..., description="add|dist|radius|pos")
    member: Optional[str] = None
    member2: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    radius: Optional[float] = None
    unit: Optional[str] = Field("km", description="m|km|mi|ft")


class RedisConfigItem(BaseModel):
    key: str
    value: str
    editable: bool = False


class RedisConfigUpdateRequest(BaseModel):
    key: str
    value: str


class ReplicationInfo(BaseModel):
    role: str
    connected_slaves: int
    master_replid: Optional[str] = None
    master_repl_offset: Optional[int] = None
    slave_info: List[Dict[str, Any]] = []


class FlushRequest(BaseModel):
    mode: str = Field(..., description="db|all")
    db: Optional[int] = None


class MigrateRequest(BaseModel):
    source_config_id: str
    target_config_id: str
    pattern: str = "*"
    replace: bool = False


class MigrateResponse(BaseModel):
    migrated_count: int
    failed_count: int
    errors: List[str] = []


class BigKeyInfo(BaseModel):
    key: str
    type: str
    memory_usage: int
    ttl: int


class BigKeysResponse(BaseModel):
    keys: List[BigKeyInfo]
