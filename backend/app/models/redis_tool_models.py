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
