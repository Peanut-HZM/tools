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
    error_code: Optional[str] = None  # 错误分类码，供前端 i18n 精确匹配
    elapsed_ms: Optional[float] = None
    version: Optional[str] = None


class SQLExecutionRequest(BaseModel):
    db_config_id: str
    sql: str
    params: Optional[Dict[str, Any]] = None
    database_name: Optional[str] = None  # Override database name
    schema_name: Optional[str] = None  # Schema name for PostgreSQL
    page: Optional[int] = Field(None, ge=1, description="Page number for pagination")
    page_size: Optional[int] = Field(
        None, ge=1, le=1000, description="Page size for pagination"
    )


class SQLExecutionResult(BaseModel):
    success: bool
    sql_type: Optional[str] = None
    affected_rows: Optional[int] = None
    execution_time_ms: float
    error_message: Optional[str] = None
    result_data: Optional[List[Dict[str, Any]]] = None  # For SELECT
    columns: Optional[List[str]] = None  # Column names


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
    db_alias: Optional[str] = None  # Enriched field


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
    schema_name: Optional[str] = None
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


class QueryTableDataRequest(BaseModel):
    """表数据查询请求体（用于 POST /databases/{id}/tables/{table}/data）"""

    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    where: Optional[str] = None
    order_by: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)


class SearchResult(BaseModel):
    database: str
    table: str
    type: str  # 'table' or 'view'


# ============ 数据导入导出模型 ============


class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    SQL = "sql"


class ExportDataRequest(BaseModel):
    sql: str
    format: ExportFormat = Field(ExportFormat.CSV, description="导出格式")
    database_name: Optional[str] = None


class ExportDataResponse(BaseModel):
    file_name: str
    file_size: int
    content: Optional[str] = None  # CSV/JSON/SQL 内容
    download_url: Optional[str] = None  # Excel 文件下载 URL
    row_count: int


class ImportDataRequest(BaseModel):
    content: str  # 文件内容（CSV/JSON）或 Base64 编码（Excel）
    format: ExportFormat
    table_name: str
    database_name: Optional[str] = None
    overwrite: bool = Field(False, description="是否清空表后导入")
    is_base64: bool = Field(False, description="是否 Base64 编码")


class ImportDataResponse(BaseModel):
    success: bool
    imported_rows: int
    skipped_rows: int
    errors: List[Dict[str, str]] = []


# ============ 执行计划分析模型 ============


class ExplainPlanRequest(BaseModel):
    sql: str
    database_name: Optional[str] = None


class ExplainPlanStep(BaseModel):
    id: int
    select_type: Optional[str]
    table: Optional[str]
    partitions: Optional[str]
    type: Optional[str]
    possible_keys: Optional[str]
    key: Optional[str]
    key_len: Optional[str]
    ref: Optional[str]
    rows: Optional[int]
    filtered: Optional[float]
    extra: Optional[str]


class ExplainPlanResponse(BaseModel):
    success: bool
    plan: List[ExplainPlanStep]
    analysis: Optional[str] = None  # 性能分析建议
    execution_time_ms: float


# ============ 表数据预览模型 ============


class TablePreviewRequest(BaseModel):
    database_name: str
    table_name: str
    schema_name: Optional[str] = None  # PostgreSQL schema 支持
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=1000)
    order_by: Optional[str] = None
    filter_conditions: Optional[Dict[str, Any]] = None


class TablePreviewResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    has_more: bool


# ============ SQL 自动补全模型 ============


class AutoCompleteRequest(BaseModel):
    query: str
    database_name: Optional[str] = None
    schema_name: Optional[str] = None  # PostgreSQL schema 支持
    position: int = Field(0, description="光标位置")


class AutoCompleteItem(BaseModel):
    label: str
    kind: str  # table, column, keyword, function, etc.
    detail: Optional[str] = None
    insert_text: Optional[str] = None


class AutoCompleteResponse(BaseModel):
    suggestions: List[AutoCompleteItem]


# ============ 备份恢复模型 ============


class BackupMode(str, Enum):
    STRUCTURE_AND_DATA = "structure_and_data"
    STRUCTURE_ONLY = "structure_only"
    DATA_ONLY = "data_only"


class BackupDatabaseRequest(BaseModel):
    database_name: str
    backup_format: str = Field("sql", description="备份格式：sql")
    backup_mode: BackupMode = Field(BackupMode.STRUCTURE_AND_DATA, description="备份模式")
    tables: Optional[List[str]] = None  # 指定表，为空则备份所有表
    include_drop: bool = Field(False, description="是否包含 DROP TABLE 语句")
    include_if_not_exists: bool = Field(True, description="是否包含 IF NOT EXISTS")


class BackupDatabaseResponse(BaseModel):
    backup_id: str
    file_name: str
    file_size: int
    download_url: str
    created_at: datetime
    tables_count: int
    backup_mode: str
    status: str = Field("success", description="备份状态: success | partial | failed")


class BackupRecordResponse(BaseModel):
    """备份记录响应"""
    id: str
    config_id: str
    database_name: str
    file_name: str
    file_size: int
    backup_mode: str
    tables_count: int
    tables_list: Optional[List[str]] = None
    status: str
    error_message: Optional[str] = None
    created_at: str
    downloaded_count: int = 0


class RestoreDatabaseRequest(BaseModel):
    backup_file_content: str  # SQL 文件内容
    target_database: str
    tables: Optional[List[str]] = None  # 指定恢复的表


class RestoreDatabaseResponse(BaseModel):
    success: bool
    restored_tables: List[str]
    total_rows: int
    execution_time_ms: float
    errors: List[str] = []


# ============ 表详情模型 ============


class ColumnDetail(BaseModel):
    name: str
    type: str
    length: Optional[str] = None
    nullable: bool = True
    default_value: Optional[str] = None
    comment: Optional[str] = None
    primary_key: bool = False
    auto_increment: bool = False
    ordinal_position: int = 0


class IndexDetail(BaseModel):
    name: str
    unique: bool = False
    primary: bool = False
    columns: List[str] = []


class ForeignKeyDetail(BaseModel):
    name: str
    constrained_columns: List[str] = []
    referred_table: str
    referred_columns: List[str] = []


class TableDetailResponse(BaseModel):
    table_name: str
    comment: Optional[str] = None
    columns: List[ColumnDetail] = []
    indexes: List[IndexDetail] = []
    foreign_keys: List[ForeignKeyDetail] = []
    row_count: Optional[int] = None


# ============ 批量删除模型 ============


class BatchDeleteRequest(BaseModel):
    database_name: Optional[str] = Field(
        None, description="数据库名称（多数据库连接时使用）"
    )
    schema_name: Optional[str] = Field(
        None, description="Schema名称（PostgreSQL多schema时使用）"
    )
    primary_keys: List[str] = Field(..., min_length=1, description="主键列名列表")
    key_values: List[Dict[str, Any]] = Field(
        ..., min_length=1, description="每行的主键值"
    )


class BatchDeleteResult(BaseModel):
    success: bool
    deleted_count: int = Field(..., description="成功删除行数")
    failed_count: int = Field(default=0, description="失败行数")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: float = Field(..., description="执行耗时（毫秒）")


class InsertRowRequest(BaseModel):
    """插入单行数据请求"""

    database_name: Optional[str] = Field(None, description="数据库名称")
    schema_name: Optional[str] = Field(None, description="Schema名称（PostgreSQL多schema时使用）")
    columns: Dict[str, Any] = Field(..., description="列名与值的映射")


class UpdateRowRequest(BaseModel):
    """更新单行数据请求（基于主键）"""

    database_name: Optional[str] = Field(None, description="数据库名称")
    schema_name: Optional[str] = Field(None, description="Schema名称（PostgreSQL多schema时使用）")
    primary_keys: List[str] = Field(..., description="主键列名列表")
    key_values: Dict[str, Any] = Field(..., description="主键列的值")
    columns: Dict[str, Any] = Field(..., description="需要更新的列名与值映射")


class RowOperationResult(BaseModel):
    """行操作结果"""

    success: bool
    affected_rows: int = Field(default=0, description="影响行数")
    execution_time_ms: float = Field(default=0, description="执行耗时（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")


# ============ 显示偏好模型 ============


class DisplayPreference(BaseModel):
    visible_connections: Optional[List[str]] = Field(
        None, description="null=全部显示, 数组=仅显示这些连接"
    )
    visible_databases: Optional[Dict[str, List[str]]] = Field(
        None, description='{"config_id": ["db1"]} 每个连接可见的数据库'
    )


class DisplayPreferenceResponse(DisplayPreference):
    updated_at: Optional[datetime] = None
