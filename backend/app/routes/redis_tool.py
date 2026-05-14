from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Body, Query
from typing import List, Optional
from app.middleware.auth_middleware import get_current_user_id
from app.models.redis_tool_models import (
    RedisConfigResponse, CreateRedisRequest, UpdateRedisRequest,
    TestConnectionRequest, ConnectionTestResult,
    RedisKeyInfo, RedisKeyContent, KeyOperationRequest, KeyDeleteRequest,
    KeyTTLRequest, KeysScanRequest, KeysScanResponse, KeyExportRequest,
    KeyExportResponse, KeyImportRequest, KeyImportResponse, LuaScriptRequest,
    LuaScriptResponse, ScriptTemplate, CreateScriptTemplateRequest,
    UpdateScriptTemplateRequest, CLICommandRequest, CLICommandResponse,
    KeyPersistRequest,
    BatchTTLRequest, BatchRenameRequest,
    StreamOperationRequest,
    BitmapOperationRequest,
    HyperLogLogOperationRequest,
    GeoOperationRequest,
    RedisConfigUpdateRequest,
    FlushRequest,
    MigrateRequest
)
from app.services.redis_tool_service import RedisToolService

router = APIRouter(prefix="/redis-tool", tags=["redis-tool"])

@router.get("/configs", response_model=List[RedisConfigResponse])
async def get_configs(user_id: str = Depends(get_current_user_id)):
    """Get all redis configurations"""
    return RedisToolService.get_all_configs(user_id)

@router.post("/configs", response_model=RedisConfigResponse)
async def create_config(
    request: CreateRedisRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new redis configuration"""
    try:
        return RedisToolService.create_config(user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/configs/{id}", response_model=RedisConfigResponse)
async def update_config(
    request: UpdateRedisRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Update a redis configuration"""
    try:
        config = RedisToolService.update_config(id, user_id, request)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/configs/{id}")
async def delete_config(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a redis configuration"""
    try:
        success = RedisToolService.delete_config(id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return {"message": "Configuration deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/test", response_model=ConnectionTestResult)
async def test_connection(
    request: TestConnectionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Test redis connection"""
    return RedisToolService.test_connection(request)

@router.post("/configs/{id}/test", response_model=ConnectionTestResult)
async def test_connection_by_id(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Test redis connection by existing config ID"""
    return RedisToolService.test_connection_by_id(id, user_id)

@router.get("/configs/{id}/keys", response_model=List[RedisKeyInfo])
async def get_keys(
    id: str = PathParam(..., description="Configuration ID"),
    pattern: str = Query("*", description="Key pattern"),
    user_id: str = Depends(get_current_user_id)
):
    """Get keys from redis"""
    try:
        return RedisToolService.get_keys(id, user_id, pattern)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/keys/{key}", response_model=RedisKeyContent)
async def get_key_content(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key"),
    user_id: str = Depends(get_current_user_id)
):
    """Get key content"""
    try:
        return RedisToolService.get_key_content(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys")
async def set_key(
    request: KeyOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Set key value"""
    try:
        RedisToolService.set_key(id, user_id, request)
        return {"message": "Key set successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/configs/{id}/keys")
async def delete_keys(
    request: KeyDeleteRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete keys"""
    try:
        count = RedisToolService.delete_keys(id, user_id, request.keys)
        return {"message": f"Deleted {count} keys", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/configs/{id}/keys/ttl")
async def update_key_ttl(
    request: KeyTTLRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Update key TTL"""
    try:
        RedisToolService.update_key_ttl(id, user_id, request)
        return {"message": "Key TTL updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/persist")
async def persist_key(
    request: KeyPersistRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Remove key TTL"""
    try:
        RedisToolService.persist_key(id, user_id, request.key)
        return {"message": "Key TTL removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/scan", response_model=KeysScanResponse)
async def scan_keys(
    request: KeysScanRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Scan keys with pagination"""
    try:
        return RedisToolService.scan_keys(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{id}/keys/{key}/memory")
async def get_key_memory(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """Get key memory usage"""
    try:
        usage = RedisToolService.get_key_memory_usage(id, user_id, key)
        return {"key": key, "memory_usage": usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/export", response_model=KeyExportResponse)
async def export_keys(
    request: KeyExportRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Export keys to JSON"""
    try:
        return RedisToolService.export_keys(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/keys/import", response_model=KeyImportResponse)
async def import_keys(
    request: KeyImportRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Import keys from JSON"""
    try:
        return RedisToolService.import_keys(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/lua", response_model=LuaScriptResponse)
async def execute_lua(
    request: LuaScriptRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Execute Lua script"""
    try:
        return RedisToolService.execute_lua_script(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts", response_model=List[ScriptTemplate])
async def get_script_templates(user_id: str = Depends(get_current_user_id)):
    """Get user's script templates"""
    return RedisToolService.get_script_templates(user_id)

@router.post("/scripts", response_model=ScriptTemplate)
async def create_script_template(
    request: CreateScriptTemplateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a script template"""
    try:
        return RedisToolService.create_script_template(user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/scripts/{template_id}", response_model=ScriptTemplate)
async def update_script_template(
    request: UpdateScriptTemplateRequest,
    template_id: str = PathParam(..., description="Template ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Update a script template"""
    try:
        RedisToolService.update_script_template(template_id, user_id, request)
        return {"message": "Script template updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/scripts/{template_id}")
async def delete_script_template(
    template_id: str = PathParam(..., description="Template ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a script template"""
    try:
        RedisToolService.delete_script_template(template_id, user_id)
        return {"message": "Script template deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/{id}/cli", response_model=CLICommandResponse)
async def execute_cli_command(
    request: CLICommandRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """Execute Redis CLI command"""
    try:
        return RedisToolService.execute_cli_command(id, user_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/keys/batch-ttl")
async def batch_update_ttl(
    request: BatchTTLRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """批量更新 key TTL"""
    try:
        count = RedisToolService.batch_update_ttl(id, user_id, request.keys, request.ttl)
        return {"message": f"Updated TTL for {count} keys", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/keys/batch-rename")
async def batch_rename(
    request: BatchRenameRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """批量重命名 key"""
    try:
        count = RedisToolService.batch_rename(id, user_id, request.keys, request.pattern, request.replacement)
        return {"message": f"Renamed {count} keys", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/monitor")
async def get_monitor(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Redis 监控信息"""
    try:
        return RedisToolService.get_monitor_info(id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/monitor/slowlog")
async def get_slowlog(
    id: str = PathParam(..., description="Configuration ID"),
    count: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """获取慢查询日志"""
    try:
        entries = RedisToolService.get_slowlog(id, user_id, count)
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/keys/{key}/stream")
async def get_stream(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Stream 信息"""
    try:
        return RedisToolService.get_stream_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/keys/{key}/stream")
async def operate_stream(
    request: StreamOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 Stream 操作"""
    try:
        return RedisToolService.operate_stream(
            id, user_id, key, request.action,
            entry_id=request.entry_id,
            fields=request.fields,
            group_name=request.group_name,
            trim_count=request.trim_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/keys/{key}/bitmap")
async def get_bitmap(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Bitmap 信息"""
    try:
        return RedisToolService.get_bitmap_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/keys/{key}/bitmap")
async def operate_bitmap(
    request: BitmapOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 Bitmap 操作"""
    try:
        return RedisToolService.operate_bitmap(
            id, user_id, key, request.action,
            offset=request.offset, value=request.value,
            start=request.start, end=request.end
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/keys/{key}/hyperloglog")
async def get_hyperloglog(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 HyperLogLog 信息"""
    try:
        return RedisToolService.get_hyperloglog_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/keys/{key}/hyperloglog")
async def operate_hyperloglog(
    request: HyperLogLogOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 HyperLogLog 操作"""
    try:
        return RedisToolService.operate_hyperloglog(
            id, user_id, key, request.action,
            elements=request.elements,
            source_keys=request.source_keys
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/keys/{key}/geo")
async def get_geo(
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Geo 信息"""
    try:
        return RedisToolService.get_geo_info(id, user_id, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/keys/{key}/geo")
async def operate_geo(
    request: GeoOperationRequest,
    id: str = PathParam(..., description="Configuration ID"),
    key: str = PathParam(..., description="Key name"),
    user_id: str = Depends(get_current_user_id)
):
    """执行 Geo 操作"""
    try:
        return RedisToolService.operate_geo(
            id, user_id, key, request.action,
            member=request.member, member2=request.member2,
            longitude=request.longitude, latitude=request.latitude,
            radius=request.radius, unit=request.unit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/config")
async def get_redis_config(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """获取 Redis 配置参数"""
    try:
        return RedisToolService.get_redis_config(id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/config")
async def update_redis_config(
    request: RedisConfigUpdateRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """更新 Redis 配置参数"""
    try:
        RedisToolService.update_redis_config(id, user_id, request.key, request.value)
        return {"message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/replication")
async def get_replication(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """获取复制信息"""
    try:
        return RedisToolService.get_replication_info(id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/flush")
async def flush_db(
    request: FlushRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """清空数据库"""
    try:
        return RedisToolService.flush_db(id, user_id, request.mode, request.db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{id}/migrate")
async def migrate_data(
    request: MigrateRequest,
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id)
):
    """数据迁移"""
    try:
        result = RedisToolService.migrate_data(
            id, user_id,
            request.source_config_id, request.target_config_id,
            request.pattern, request.replace
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{id}/bigkeys")
async def get_big_keys(
    id: str = PathParam(..., description="Configuration ID"),
    count: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """扫描大 Key"""
    try:
        keys = RedisToolService.scan_big_keys(id, user_id, count)
        return {"keys": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

