import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam, Body
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

from app.middleware.auth_middleware import get_current_user_id, get_current_user
from app.models.database_tool_models import (
    DatabaseConfigResponse,
    CreateDatabaseRequest,
    UpdateDatabaseRequest,
    TestConnectionRequest,
    ConnectionTestResult,
    SQLExecutionRequest,
    SQLExecutionResult,
    ExecutionHistory,
    TableSchema,
    TableData,
    TableModificationRequest,
    ExportDataRequest,
    ExportDataResponse,
    ExportFormat,
    ImportDataRequest,
    ImportDataResponse,
    ExplainPlanRequest,
    ExplainPlanResponse,
    TablePreviewRequest,
    TablePreviewResponse,
    AutoCompleteRequest,
    AutoCompleteResponse,
    BackupDatabaseRequest,
    BackupDatabaseResponse,
    BackupRecordResponse,
    RestoreDatabaseRequest,
    RestoreDatabaseResponse,
    TableDetailResponse,
    BatchDeleteRequest,
    BatchDeleteResult,
    InsertRowRequest,
    UpdateRowRequest,
    RowOperationResult,
    DisplayPreference,
    DisplayPreferenceResponse,
    QueryTableDataRequest,
)
from fastapi.responses import FileResponse
from pathlib import Path
from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE, _LIST_CACHE
from app.utils.db_error_mapper import map_connection_error

router = APIRouter(prefix="/database-tool", tags=["database-tool"])


def _raise_connection_error(e: Exception) -> None:
    """将连接相关异常转为带 error_code 的 HTTPException。

    仅用于路由层 except Exception 分支，保持 HTTP detail 结构统一。
    """
    error_code, zh_msg = map_connection_error(str(e))
    raise HTTPException(
        status_code=500,
        detail={"error_code": error_code, "message": zh_msg, "raw": str(e)},
    ) from e


# --------------------------------------------------------------------------
# Database Configs
# --------------------------------------------------------------------------


@router.get("/databases", response_model=List[DatabaseConfigResponse])
async def get_databases(
    include_password: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
    current_user=Depends(get_current_user),
):
    """Get all database configurations for the current user"""
    if include_password and getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=403, detail="Permission denied: Admin access required"
        )
    try:
        return DatabaseToolService.get_all_configs(
            user_id, include_password=include_password
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/databases", response_model=DatabaseConfigResponse)
async def create_database(
    request: CreateDatabaseRequest, user_id: str = Depends(get_current_user_id)
):
    """Create a new database configuration"""
    try:
        return DatabaseToolService.create_config(user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases/{id}", response_model=DatabaseConfigResponse)
async def get_database(
    id: str = PathParam(..., description="Configuration ID"),
    include_password: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
    current_user=Depends(get_current_user),
):
    """Get a specific database configuration"""
    if include_password and getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=403, detail="Permission denied: Admin access required"
        )
    config = DatabaseToolService.get_config(
        id, user_id, include_password=include_password
    )
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.put("/databases/{id}", response_model=DatabaseConfigResponse)
async def update_database(
    request: UpdateDatabaseRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Update a database configuration"""
    try:
        config = DatabaseToolService.update_config(id, user_id, request)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        # 清除该配置下所有数据库的结构缓存（连接信息可能已变更）
        _STRUCTURE_CACHE.invalidate_prefix(f"{id}:")
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/databases/{id}")
async def delete_database(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a database configuration"""
    try:
        success = DatabaseToolService.delete_config(id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found")
        # 删除配置时清除该配置下所有数据库的结构缓存
        _STRUCTURE_CACHE.invalidate_prefix(f"{id}:")
        return {"message": "Configuration deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/databases/test", response_model=ConnectionTestResult)
async def test_connection(
    request: TestConnectionRequest, user_id: str = Depends(get_current_user_id)
):
    """Test database connection with provided details"""
    return DatabaseToolService.test_connection(request)


@router.post("/databases/{id}/decrypt-password", response_model=Dict[str, str])
async def decrypt_password(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Decrypt and return the password for a database config (owner only)"""
    from app.utils.encryption import EncryptionUtils

    config_row = DatabaseToolService._get_config_with_password(id, user_id)
    if not config_row:
        raise HTTPException(status_code=404, detail="Configuration not found")

    try:
        plaintext = EncryptionUtils.decrypt(config_row["password_encrypted"])
        return {"password": plaintext}
    except Exception as e:
        logger.error("Failed to decrypt password for config %s: %s", id, str(e))
        raise HTTPException(status_code=500, detail="Failed to decrypt password")


@router.post("/databases/{id}/test", response_model=ConnectionTestResult)
async def test_connection_by_id(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Test database connection for an existing configuration"""
    return DatabaseToolService.test_connection_by_id(id, user_id)


@router.get("/databases/{id}/databases", response_model=List[str])
async def get_databases_list(
    id: str = PathParam(..., description="Configuration ID"),
    skip_cache: bool = Query(False, description="跳过缓存强制刷新"),
    user_id: str = Depends(get_current_user_id),
):
    """List databases for a connection"""
    try:
        return DatabaseToolService.get_databases_list(user_id, id, skip_cache=skip_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/schemas", response_model=List[str])
async def get_schemas_list(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: Optional[str] = Query(None, description="Database Name (PostgreSQL)"),
    skip_cache: bool = Query(False, description="跳过缓存强制刷新"),
    user_id: str = Depends(get_current_user_id),
):
    """List schemas for a specific database (PostgreSQL)"""
    try:
        return DatabaseToolService.get_schemas_list(
            user_id, id, database_name, skip_cache=skip_cache
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/all-schemas", response_model=Dict[str, List[str]])
async def get_all_schemas(
    id: str = PathParam(..., description="Configuration ID"),
    skip_cache: bool = Query(False, description="跳过缓存强制刷新"),
    user_id: str = Depends(get_current_user_id),
):
    """并行返回某 PG 连接下所有库的 schema（搜索用）"""
    try:
        return DatabaseToolService.get_all_schemas(user_id, id, skip_cache=skip_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/structure", response_model=Dict[str, List[Dict[str, Any]]])
async def get_database_structure(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL only)"),
    user_id: str = Depends(get_current_user_id),
):
    """Get structure (tables, views) for a specific database/schema"""
    try:
        return DatabaseToolService.get_database_structure(user_id, id, database_name, schema_name)
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/tables/{table}/ddl", response_model=str)
async def get_table_ddl(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: str = Query(..., description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL)"),
    user_id: str = Depends(get_current_user_id),
):
    """Get DDL for a table"""
    try:
        return DatabaseToolService.generate_ddl(user_id, id, table, database_name, schema_name)
    except Exception as e:
        _raise_connection_error(e)


@router.post("/databases/{id}/tables/modify", response_model=bool)
async def modify_table_structure(
    request: TableModificationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Modify table structure"""
    try:
        result = DatabaseToolService.modify_table_structure(user_id, id, request)
        if result:
            schema_suffix = f":{request.schema_name}" if request.schema_name else ""
            _STRUCTURE_CACHE.invalidate(f"{id}:{request.database_name}{schema_suffix}")
        return result
    except Exception as e:
        _raise_connection_error(e)


@router.delete("/databases/{id}/all-tables", response_model=bool)
async def delete_all_tables(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id),
):
    """Delete all tables in a database"""
    try:
        result = DatabaseToolService.delete_all_tables(user_id, id, database_name)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{database_name}")
        return result
    except Exception as e:
        _raise_connection_error(e)


@router.post("/databases/{id}/truncate-all-tables", response_model=bool)
async def truncate_all_tables(
    id: str = PathParam(..., description="Configuration ID"),
    request: dict = Body(..., description="Request body with database_name"),
    user_id: str = Depends(get_current_user_id),
):
    """Truncate all tables in a database"""
    try:
        database_name = request.get("database_name")
        if not database_name:
            raise HTTPException(status_code=400, detail="database_name is required")
        result = DatabaseToolService.truncate_all_tables(user_id, id, database_name)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{database_name}")
        return result
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/ddl", response_model=str)
async def get_database_ddl(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id),
):
    """Get DDL for all tables in a database"""
    try:
        return DatabaseToolService.generate_all_tables_ddl(user_id, id, database_name)
    except Exception as e:
        _raise_connection_error(e)


@router.post("/databases/{id}/search", response_model=List[Dict[str, str]])
async def search_tables(
    id: str = PathParam(..., description="Configuration ID"),
    request: dict = Body(..., description="Request body"),
    user_id: str = Depends(get_current_user_id),
):
    """Search for tables/views matching keyword"""
    try:
        keyword = request.get("keyword")
        if not keyword:
            return []
        return DatabaseToolService.search_tables(user_id, id, keyword)
    except Exception as e:
        # Don't fail search, just log and return empty
        logger.error("Search error: %s", e)
        return []


# --------------------------------------------------------------------------
# Database Administration (DDL)
# --------------------------------------------------------------------------


@router.post("/databases/{id}/databases", response_model=bool)
async def create_database_instance(
    request: dict = Body(..., description="Request body"),
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new database on the server"""
    try:
        name = request.get("name")
        charset = request.get("charset", "utf8mb4")
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        result = DatabaseToolService.create_database_instance(user_id, id, name, charset)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{name}")
            _LIST_CACHE.invalidate_prefix(f"databases:{id}")
            _LIST_CACHE.invalidate_prefix(f"all_schemas:{id}")
        return result
    except Exception as e:
        _raise_connection_error(e)


@router.delete("/databases/{id}/databases/{name}", response_model=bool)
async def drop_database_instance(
    id: str = PathParam(..., description="Configuration ID"),
    name: str = PathParam(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id),
):
    """Drop a database on the server"""
    try:
        result = DatabaseToolService.drop_database_instance(user_id, id, name)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{name}")
            _LIST_CACHE.invalidate_prefix(f"databases:{id}")
            _LIST_CACHE.invalidate_prefix(f"schemas:{id}:{name}")
            _LIST_CACHE.invalidate_prefix(f"all_schemas:{id}")
        return result
    except Exception as e:
        _raise_connection_error(e)


@router.delete("/databases/{id}/tables/{table}", response_model=bool)
async def drop_table_instance(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id),
):
    """Drop a table"""
    try:
        result = DatabaseToolService.drop_table_instance(
            user_id, id, database_name, table
        )
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{database_name}")
        return result
    except Exception as e:
        _raise_connection_error(e)


@router.post("/databases/{id}/tables/{table}/truncate", response_model=bool)
async def truncate_table_instance(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: dict = Body(..., description="Request body with database_name"),
    user_id: str = Depends(get_current_user_id),
):
    """Truncate a table"""
    try:
        database_name = request.get("database_name")
        if not database_name:
            raise HTTPException(status_code=400, detail="database_name is required")
        result = DatabaseToolService.truncate_table_instance(
            user_id, id, database_name, table
        )
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{database_name}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        _raise_connection_error(e)


# --------------------------------------------------------------------------
# SQL Execution
# --------------------------------------------------------------------------


@router.post("/execute", response_model=SQLExecutionResult)
async def execute_sql(
    request: SQLExecutionRequest, user_id: str = Depends(get_current_user_id)
):
    """Execute SQL statement"""
    try:
        return DatabaseToolService.execute_sql(user_id, request)
    except Exception as e:
        _raise_connection_error(e)


@router.get("/history", response_model=List[ExecutionHistory])
async def get_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """Get execution history"""
    return DatabaseToolService.get_history(user_id, limit, offset)


# --------------------------------------------------------------------------
# Schema Browsing
# --------------------------------------------------------------------------


@router.get("/databases/{id}/tables", response_model=List[str])
async def get_tables(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Get all tables in the database"""
    try:
        return DatabaseToolService.get_tables(user_id, id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/tables/{table}/schema", response_model=TableSchema)
async def get_table_schema(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: Optional[str] = Query(None, description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL only)"),
    user_id: str = Depends(get_current_user_id),
):
    """Get table schema structure"""
    try:
        return DatabaseToolService.get_table_schema(user_id, id, table, database_name, schema_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.post("/databases/{id}/tables/{table}/data", response_model=SQLExecutionResult)
async def query_table_data(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    body: QueryTableDataRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """Query table data with filtering and sorting"""
    try:
        return DatabaseToolService.query_table_data(
            user_id,
            id,
            table,
            database_name=body.database_name,
            schema_name=body.schema_name,
            where_clause=body.where,
            order_by_clause=body.order_by,
            page=body.page,
            page_size=body.page_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


# ============ 数据导入导出 API ============


@router.post("/configs/{id}/export", response_model=ExportDataResponse)
async def export_data(
    request: ExportDataRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Export query result data"""
    try:
        return DatabaseToolService.export_data(user_id, id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.post("/configs/{id}/import", response_model=ImportDataResponse)
async def import_data(
    request: ImportDataRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Import data from file"""
    try:
        return DatabaseToolService.import_data(user_id, id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


# ============ 执行计划分析 API ============


@router.post("/configs/{id}/explain", response_model=ExplainPlanResponse)
async def explain_plan(
    request: ExplainPlanRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Analyze SQL execution plan"""
    try:
        return DatabaseToolService.explain_plan(user_id, id, request)
    except Exception as e:
        _raise_connection_error(e)


# ============ 表数据预览 API ============


@router.post(
    "/configs/{id}/tables/{table}/preview", response_model=TablePreviewResponse
)
async def table_preview(
    request: TablePreviewRequest,
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table name"),
    user_id: str = Depends(get_current_user_id),
):
    """Preview table data with pagination"""
    try:
        return DatabaseToolService.table_preview(user_id, id, request)
    except Exception as e:
        _raise_connection_error(e)


# ============ SQL 自动补全 API ============


@router.post("/configs/{id}/autocomplete", response_model=AutoCompleteResponse)
async def auto_complete(
    request: AutoCompleteRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """SQL auto complete suggestions"""
    try:
        return DatabaseToolService.auto_complete(user_id, id, request)
    except Exception as e:
        _raise_connection_error(e)


# ============ 数据库备份恢复 API ============


@router.post("/configs/{id}/backup", response_model=BackupDatabaseResponse)
async def backup_database(
    request: BackupDatabaseRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Backup database to SQL file"""
    try:
        return DatabaseToolService.backup_database(user_id, id, request)
    except Exception as e:
        _raise_connection_error(e)


@router.post("/configs/{id}/restore", response_model=RestoreDatabaseResponse)
async def restore_database(
    request: RestoreDatabaseRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """Restore database from SQL file"""
    try:
        return DatabaseToolService.restore_database(user_id, id, request)
    except Exception as e:
        _raise_connection_error(e)


# ============ 批量删除 API ============


@router.post(
    "/databases/{id}/tables/{table}/batch-delete", response_model=BatchDeleteResult
)
async def batch_delete_rows(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: BatchDeleteRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """批量删除表中的多行数据（基于主键）"""
    try:
        return DatabaseToolService.batch_delete_rows(user_id, id, table, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


# ============ 行数据插入/更新 API ============


@router.post(
    "/databases/{id}/tables/{table}/insert-row", response_model=RowOperationResult
)
async def insert_table_row(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: InsertRowRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """向表中插入一行数据"""
    try:
        return DatabaseToolService.insert_row(user_id, id, table, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.post(
    "/databases/{id}/tables/{table}/update-row", response_model=RowOperationResult
)
async def update_table_row(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: UpdateRowRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """基于主键更新表中一行数据"""
    try:
        return DatabaseToolService.update_row(user_id, id, table, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


# ============ 表详情 API ============


@router.get("/databases/{id}/tables/{table}/detail", response_model=TableDetailResponse)
async def get_table_detail(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: str = Query(..., description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL only)"),
    user_id: str = Depends(get_current_user_id),
):
    """获取表详细结构（字段、索引、外键）"""
    try:
        return DatabaseToolService.get_table_detail(user_id, id, table, database_name, schema_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


@router.get("/databases/{id}/tables/{table}/row-count")
async def get_table_row_count(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: str = Query(..., description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL only)"),
    user_id: str = Depends(get_current_user_id),
):
    """获取表行数"""
    try:
        count = DatabaseToolService.get_table_row_count(user_id, id, table, database_name, schema_name)
        return {"table_name": table, "row_count": count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _raise_connection_error(e)


# ============ 备份文件下载 API ============


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str = PathParam(..., description="Backup ID"),
    user_id: str = Depends(get_current_user_id),
):
    """下载备份文件"""
    file_path = DatabaseToolService.get_backup_file_path(user_id, backup_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Backup not found")

    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    # 增加下载计数
    DatabaseToolService.increment_download_count(user_id, backup_id)

    return FileResponse(
        path=file_path,
        media_type="application/sql",
        filename=path.name,
    )


# ============ 备份历史管理 API ============


@router.get("/configs/{id}/backups")
async def list_backups(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
):
    """获取备份历史列表"""
    try:
        return DatabaseToolService.list_backups(
            user_id=user_id,
            config_id=id,
            database_name=database_name,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str = PathParam(..., description="Backup ID"),
    user_id: str = Depends(get_current_user_id),
):
    """删除备份"""
    success = DatabaseToolService.delete_backup(user_id, backup_id)
    if not success:
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"message": "Backup deleted successfully"}


# --------------------------------------------------------------------------
# Display Preferences
# --------------------------------------------------------------------------


@router.get("/preferences", response_model=DisplayPreferenceResponse)
async def get_display_preferences(
    user_id: str = Depends(get_current_user_id),
):
    """获取当前用户的显示偏好"""
    return DatabaseToolService.get_display_preferences(user_id)


@router.put("/preferences", response_model=DisplayPreferenceResponse)
async def save_display_preferences(
    preferences: DisplayPreference,
    user_id: str = Depends(get_current_user_id),
):
    """保存当前用户的显示偏好"""
    try:
        return DatabaseToolService.save_display_preferences(
            user_id, preferences.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
