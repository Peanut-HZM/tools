from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum

class RedisConfigBase(BaseModel):
    alias: str = Field(..., min_length=2, max_length=32, description="配置别名")
    host: str = Field(..., description="主机地址")
    port: int = Field(6379, ge=1, le=65535, description="端口号")
    username: Optional[str] = Field(None, description="用户名")
    db: int = Field(0, ge=0, description="数据库索引")
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
    db: Optional[int] = None
    group_name: Optional[str] = None
    is_active: Optional[bool] = None

class RedisConfigResponse(RedisConfigBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    # Password not returned

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

class RedisKeyType(str, Enum):
    STRING = "string"
    LIST = "list"
    SET = "set"
    ZSET = "zset"
    HASH = "hash"
    NONE = "none"

class RedisKeyInfo(BaseModel):
    key: str
    type: str
    ttl: int
    size: Optional[int] = None # Length of list/set/hash or size of string

class RedisKeyContent(BaseModel):
    key: str
    type: str
    ttl: int
    value: Any # Depends on type: str, list, dict, etc.

class KeyOperationRequest(BaseModel):
    key: str
    type: RedisKeyType
    value: Any
    ttl: Optional[int] = -1

class KeyDeleteRequest(BaseModel):
    keys: List[str]
