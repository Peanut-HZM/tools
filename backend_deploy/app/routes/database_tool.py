from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam, Body
from typing import List, Optional, Dict, Any

from app.middleware.auth_middleware import get_current_user_id
from app.models.database_tool_models import (
    DatabaseConfigResponse, CreateDatabaseRequest, UpdateDatabaseRequest,
    TestConnectionRequest, ConnectionTestResult,
    SQLExecutionRequest, SQLExecutionResult, ExecutionHistory,
    TableSchema, TableData, TableModificationRequest
)
from app.services.database_tool_service import DatabaseToolService

router = APIRouter(prefix="/database-tool", tags=["database-tool"])

# --------------------------------------------------------------------------
# Database Configs
# --------------------------------------------------------------------------

@router.get("/databases", response_model=List[DatabaseConfigResponse])
async def get_databases(
    user_id: str = Depends(get_current_user_id)
):
    """Get all database configurations for the current user"""
    return DatabaseToolService.get_all_configs(user_id)

@router.post("/databases", response_model=DatabaseConfigResponse)
async def create_database(
    request: CreateDatabaseRequest,
    user_id: str = Depends(get_current_user_id)
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
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific database configuration"""
    config = DatabaseToolService.get_config(id, user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.put("/databases/{id}", response_model=DatabaseConfigResponse)
async def update_database(
    request: UpdateDatabaseRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Update a database configuration"""
    try:
        config = DatabaseToolService.update_config(id, user_id, request)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/databases/{id}")
async def delete_database(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a database configuration"""
    try:
        success = DatabaseToolService.delete_config(id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return {"message": "Configuration deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/databases/test", response_model=ConnectionTestResult)
async def test_connection(
    request: TestConnectionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Test database connection with provided details"""
    return DatabaseToolService.test_connection(request)

@router.post("/databases/{id}/test", response_model=ConnectionTestResult)
async def test_connection_by_id(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Test database connection for an existing configuration"""
    return DatabaseToolService.test_connection_by_id(id, user_id)

@router.get("/databases/{id}/databases", response_model=List[str])
async def get_databases_list(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """List databases for a connection"""
    try:
        return DatabaseToolService.get_databases_list(user_id, id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/databases/{id}/structure", response_model=Dict[str, List[Dict[str, Any]]])
async def get_database_structure(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Get structure (tables, views) for a specific database"""
    try:
        return DatabaseToolService.get_database_structure(user_id, id, database_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/databases/{id}/tables/{table}/ddl", response_model=str)
async def get_table_ddl(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Get DDL for a table"""
    try:
        return DatabaseToolService.generate_ddl(user_id, id, table, database_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/databases/{id}/tables/modify", response_model=bool)
async def modify_table_structure(
    request: TableModificationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Modify table structure"""
    try:
        return DatabaseToolService.modify_table_structure(user_id, id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/databases/{id}/all-tables", response_model=bool)
async def delete_all_tables(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete all tables in a database"""
    try:
        return DatabaseToolService.delete_all_tables(user_id, id, database_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/databases/{id}/truncate-all-tables", response_model=bool)
async def truncate_all_tables(
    id: str = PathParam(..., description="Configuration ID"),
    request: dict = Body(..., description="Request body with database_name"),
    user_id: str = Depends(get_current_user_id)
):
    """Truncate all tables in a database"""
    try:
        database_name = request.get("database_name")
        if not database_name:
             raise HTTPException(status_code=400, detail="database_name is required")
        return DatabaseToolService.truncate_all_tables(user_id, id, database_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/databases/{id}/ddl", response_model=str)
async def get_database_ddl(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Get DDL for all tables in a database"""
    try:
        return DatabaseToolService.generate_all_tables_ddl(user_id, id, database_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/databases/{id}/search", response_model=List[Dict[str, str]])
async def search_tables(
    id: str = PathParam(..., description="Configuration ID"),
    request: dict = Body(..., description="Request body"),
    user_id: str = Depends(get_current_user_id)
):
    """Search for tables/views matching keyword"""
    try:
        keyword = request.get("keyword")
        if not keyword:
            return []
        return DatabaseToolService.search_tables(user_id, id, keyword)
    except Exception as e:
        # Don't fail search, just log and return empty
        print(f"Search error: {e}")
        return []

# --------------------------------------------------------------------------
# Database Administration (DDL)
# --------------------------------------------------------------------------

@router.post("/databases/{id}/databases", response_model=bool)
async def create_database_instance(
    request: dict = Body(..., description="Request body"),
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new database on the server"""
    try:
        name = request.get("name")
        charset = request.get("charset", "utf8mb4")
        if not name:
             raise HTTPException(status_code=400, detail="name is required")
        return DatabaseToolService.create_database_instance(user_id, id, name, charset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/databases/{id}/databases/{name}", response_model=bool)
async def drop_database_instance(
    id: str = PathParam(..., description="Configuration ID"),
    name: str = PathParam(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Drop a database on the server"""
    try:
        return DatabaseToolService.drop_database_instance(user_id, id, name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/databases/{id}/tables/{table}", response_model=bool)
async def drop_table_instance(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: str = Query(..., description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Drop a table"""
    try:
        return DatabaseToolService.drop_table_instance(user_id, id, database_name, table)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/databases/{id}/tables/{table}/truncate", response_model=bool)
async def truncate_table_instance(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: dict = Body(..., description="Request body with database_name"),
    user_id: str = Depends(get_current_user_id)
):
    """Truncate a table"""
    try:
        database_name = request.get("database_name")
        if not database_name:
             raise HTTPException(status_code=400, detail="database_name is required")
        return DatabaseToolService.truncate_table_instance(user_id, id, database_name, table)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------
# SQL Execution
# --------------------------------------------------------------------------

@router.post("/execute", response_model=SQLExecutionResult)
async def execute_sql(
    request: SQLExecutionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Execute SQL statement"""
    result = DatabaseToolService.execute_sql(user_id, request)
    return result

@router.get("/history", response_model=List[ExecutionHistory])
async def get_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id)
):
    """Get execution history"""
    return DatabaseToolService.get_history(user_id, limit, offset)

# --------------------------------------------------------------------------
# Schema Browsing
# --------------------------------------------------------------------------

@router.get("/databases/{id}/tables", response_model=List[str])
async def get_tables(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Get all tables in the database"""
    try:
        return DatabaseToolService.get_tables(user_id, id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/databases/{id}/tables/{table}/schema", response_model=TableSchema)
async def get_table_schema(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: Optional[str] = Query(None, description="Database Name"),
    user_id: str = Depends(get_current_user_id)
):
    """Get table schema structure"""
    try:
        return DatabaseToolService.get_table_schema(user_id, id, table, database_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/databases/{id}/tables/{table}/data", response_model=SQLExecutionResult)
async def query_table_data(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: dict = Body(..., description="Query parameters"),
    user_id: str = Depends(get_current_user_id)
):
    """Query table data with filtering and sorting"""
    try:
        database_name = request.get("database_name")
        where_clause = request.get("where")
        order_by_clause = request.get("order_by")
        page = request.get("page", 1)
        page_size = request.get("page_size", 20)
        
        return DatabaseToolService.query_table_data(
            user_id, id, table, 
            database_name=database_name,
            where_clause=where_clause,
            order_by_clause=order_by_clause,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
