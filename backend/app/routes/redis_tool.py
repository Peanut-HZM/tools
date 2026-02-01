from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Body, Query
from typing import List, Optional
from app.middleware.auth_middleware import get_current_user_id
from app.models.redis_tool_models import (
    RedisConfigResponse, CreateRedisRequest, UpdateRedisRequest,
    TestConnectionRequest, ConnectionTestResult,
    RedisKeyInfo, RedisKeyContent, KeyOperationRequest, KeyDeleteRequest
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
