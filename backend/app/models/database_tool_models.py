from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum

class DatabaseType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    MARIADB = "mariadb"

class Environment(str, Enum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"

class DatabaseConfigBase(BaseModel):
    alias: str = Field(..., min_length=2, max_length=32, description="配置别名")
    db_type: DatabaseType = Field(..., description="数据库类型")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., ge=1, le=65535, description="端口号")
    database_name: Optional[str] = Field(None, description="数据库名")
    username: str = Field(..., description="用户名")
    environment: Optional[Environment] = Field(None, description="环境标签")
    group_name: Optional[str] = Field(None, max_length=50, description="分组名称")
    charset: Optional[str] = Field("utf8mb4", description="字符集")
    connect_timeout: Optional[int] = Field(10, description="连接超时（秒）")
    max_pool_size: Optional[int] = Field(10, description="最大连接池大小")
    ssl_mode: Optional[str] = Field(None, description="SSL模式")
    ssl_cert_path: Optional[str] = Field(None, description="SSL证书路径")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="额外配置")
    is_active: bool = Field(True, description="是否激活")

class CreateDatabaseRequest(DatabaseConfigBase):
    password: str = Field(..., description="密码")

class UpdateDatabaseRequest(BaseModel):
    alias: Optional[str] = Field(None, min_length=2, max_length=32)
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    environment: Optional[Environment] = None
    group_name: Optional[str] = None
    charset: Optional[str] = None
    connect_timeout: Optional[int] = None
    max_pool_size: Optional[int] = None
    ssl_mode: Optional[str] = None
    ssl_cert_path: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class DatabaseConfigResponse(DatabaseConfigBase):
    id: str
    user_id: str
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    password: Optional[str] = None

class TestConnectionRequest(BaseModel):
    db_type: DatabaseType
    host: str
    port: int
    database_name: Optional[str] = None
    username: str
    password: str
    ssl_mode: Optional[str] = None
    ssl_cert_path: Optional[str] = None

class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    elapsed_ms: Optional[float] = None
    version: Optional[str] = None

class SQLExecutionRequest(BaseModel):
    db_config_id: str
    sql: str
    params: Optional[Dict[str, Any]] = None
    database_name: Optional[str] = None # Override database name
    page: Optional[int] = Field(None, ge=1, description="Page number for pagination")
    page_size: Optional[int] = Field(None, ge=1, le=1000, description="Page size for pagination")

class SQLExecutionResult(BaseModel):
    success: bool
    sql_type: Optional[str] = None
    affected_rows: Optional[int] = None
    execution_time_ms: float
    error_message: Optional[str] = None
    result_data: Optional[List[Dict[str, Any]]] = None # For SELECT
    columns: Optional[List[str]] = None # Column names
    
class ExecutionHistory(BaseModel):
    id: str
    user_id: str
    db_config_id: str
    sql_statement: str
    sql_type: Optional[str]
    execution_status: str
    affected_rows: Optional[int]
    execution_time_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    db_alias: Optional[str] = None # Enriched field

class TableSchema(BaseModel):
    table_name: str
    comment: Optional[str] = None
    columns: List[Dict[str, Any]]
    primary_key: Optional[List[str]]
    indexes: Optional[List[Dict[str, Any]]]
    foreign_keys: Optional[List[Dict[str, Any]]]

class ColumnDefinition(BaseModel):
    name: str
    type: str
    length: Optional[str] = None
    nullable: bool = True
    default_value: Optional[str] = None
    comment: Optional[str] = None
    primary_key: bool = False
    auto_increment: bool = False

class TableModificationRequest(BaseModel):
    database_name: str
    table_name: str
    new_table_name: Optional[str] = None
    columns: List[ColumnDefinition]
    comment: Optional[str] = None

class TableData(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int

class SearchResult(BaseModel):
    database: str
    table: str
    type: str # 'table' or 'view'
