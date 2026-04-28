"""
HTTP Client 路由 - API 接口调用工具
"""

import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Query, Request, Depends

from app.models.http_client_models import (
    Collection,
    CollectionCreate,
    CollectionUpdate,
    HttpRequest,
    HttpRequestCreate,
    HttpRequestUpdate,
    Environment,
    EnvironmentCreate,
    EnvironmentUpdate,
    SendRequestRequest,
    SendRequestResponse,
    RequestHistory,
    ImportResult,
    CurlImportRequest,
    SyncStatusResponse,
)
from app.services.http_client_service import http_client_service, is_safe_url
from app.middleware.auth_middleware import optional_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/http-client", tags=["http-client"])


# ============= Collection Endpoints =============

@router.get("/collections", response_model=List[Collection])
def get_collections(workspace_id: str = Query(default="default")):
    """获取所有请求集合"""
    collections = http_client_service.get_all_collections(workspace_id)
    return collections


@router.get("/collections/{collection_id}", response_model=Collection)
def get_collection(collection_id: str):
    """获取集合详情"""
    collection = http_client_service.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="集合不存在")
    return collection


@router.post("/collections", response_model=Collection)
def create_collection(request: CollectionCreate):
    """创建请求集合"""
    collection = http_client_service.create_collection(request)
    if not collection:
        raise HTTPException(status_code=500, detail="创建集合失败")
    return collection


@router.put("/collections/{collection_id}", response_model=Collection)
def update_collection(collection_id: str, request: CollectionUpdate):
    """更新请求集合"""
    collection = http_client_service.update_collection(collection_id, request)
    if not collection:
        raise HTTPException(status_code=404, detail="集合不存在")
    return collection


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: str):
    """删除请求集合"""
    success = http_client_service.delete_collection(collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="集合不存在")
    return {"success": True}


# ============= Request Endpoints =============

@router.get("/requests", response_model=List[HttpRequest])
def get_requests(collection_id: str = Query(..., description="集合 ID")):
    """获取集合下的所有请求"""
    requests = http_client_service.get_requests_by_collection(collection_id)
    return requests


@router.get("/requests/{request_id}", response_model=HttpRequest)
def get_request(request_id: str):
    """获取请求详情"""
    request = http_client_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="请求不存在")
    return request


@router.post("/requests", response_model=HttpRequest)
def create_request(request: HttpRequestCreate):
    """创建 HTTP 请求"""
    created = http_client_service.create_request(request)
    if not created:
        raise HTTPException(status_code=500, detail="创建请求失败")
    return created


@router.put("/requests/{request_id}", response_model=HttpRequest)
def update_request(request_id: str, request: HttpRequestUpdate):
    """更新 HTTP 请求"""
    updated = http_client_service.update_request(request_id, request)
    if not updated:
        raise HTTPException(status_code=404, detail="请求不存在")
    return updated


@router.delete("/requests/{request_id}")
def delete_request(request_id: str):
    """删除 HTTP 请求"""
    success = http_client_service.delete_request(request_id)
    if not success:
        raise HTTPException(status_code=404, detail="请求不存在")
    return {"success": True}


# ============= Environment Endpoints =============

@router.get("/environments", response_model=List[Environment])
def get_environments(workspace_id: str = Query(default="default")):
    """获取所有环境变量"""
    environments = http_client_service.get_all_environments(workspace_id)
    return environments


@router.get("/environments/active", response_model=Optional[Environment])
def get_active_environment(workspace_id: str = Query(default="default")):
    """获取当前激活的环境变量"""
    env = http_client_service.get_active_environment(workspace_id)
    return env


@router.post("/environments", response_model=Environment)
def create_environment(request: EnvironmentCreate):
    """创建环境变量"""
    environment = http_client_service.create_environment(request)
    if not environment:
        raise HTTPException(status_code=500, detail="创建环境失败")
    return environment


@router.put("/environments/{env_id}", response_model=Environment)
def update_environment(env_id: str, request: EnvironmentUpdate):
    """更新环境变量"""
    environment = http_client_service.update_environment(env_id, request)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    return environment


@router.post("/environments/{env_id}/activate", response_model=Environment)
def activate_environment(env_id: str):
    """激活环境变量"""
    environment = http_client_service.activate_environment(env_id)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    return environment


@router.delete("/environments/{env_id}")
def delete_environment(env_id: str):
    """删除环境变量"""
    success = http_client_service.delete_environment(env_id)
    if not success:
        raise HTTPException(status_code=404, detail="环境不存在")
    return {"success": True}


# ============= Send Request Endpoint =============

@router.post("/send", response_model=SendRequestResponse)
async def send_request(request: SendRequestRequest, req: Request, user_id: Optional[str] = Depends(optional_auth)):
    """发送 HTTP 请求（代理转发）"""
    try:
        user_id = user_id or "anonymous"
        result = await http_client_service.send_request(request, user_id)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Send request failed: {e}")
        raise HTTPException(status_code=500, detail=f"请求失败：{str(e)}")


# ============= History Endpoints =============

@router.get("/history", response_model=List[RequestHistory])
def get_history(
    limit: int = Query(default=50, ge=1, le=200, description="获取记录数量"),
    user_id: Optional[str] = Depends(optional_auth),
):
    """获取请求历史"""
    user_id = user_id or "anonymous"
    history = http_client_service.get_request_history(user_id, limit)
    return history


@router.delete("/history/{history_id}")
def delete_history(history_id: str):
    """删除单条历史记录"""
    # TODO: 实现单条删除逻辑
    return {"success": True}


@router.post("/history/clear")
def clear_history(user_id: Optional[str] = Depends(optional_auth)):
    """清空请求历史"""
    user_id = user_id or "anonymous"
    success = http_client_service.clear_request_history(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="清空历史失败")
    return {"success": True}


# ============= Import/Export Endpoints =============

@router.post("/import", response_model=ImportResult)
def import_requests(
    collection_data: Dict,
    workspace_id: str = Query(default="default", description="工作区 ID"),
):
    """导入 Postman Collection"""
    try:
        result = http_client_service.import_postman_collection(collection_data, workspace_id)
        return ImportResult(**result)
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return ImportResult(success=False, imported_count=0, failed_count=1, errors=[str(e)])


@router.post("/import/curl", response_model=HttpRequest)
def import_curl(request_data: CurlImportRequest):
    """从 cURL 命令导入请求"""
    try:
        parsed = http_client_service.parse_curl_command(request_data.curl_command)
        created = http_client_service.create_request(HttpRequestCreate(
            collection_id=request_data.collection_id,
            name=request_data.name,
            method=parsed['method'],
            url=parsed['url'],
            headers=parsed['headers'],
            params={},
            body_type=parsed['body_type'],
            body=parsed['body'],
            auth_type="none",
            auth_config={},
            sort_order=0,
        ))
        if not created:
            raise HTTPException(status_code=500, detail="创建请求失败")
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"cURL 解析失败：{str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"cURL import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{collection_id}")
def export_collection(
    collection_id: str,
    format: str = Query(default="postman", description="导出格式：postman/json"),
):
    """导出集合为 Postman Collection 格式"""
    try:
        result = http_client_service.export_collection(collection_id)
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "导出失败"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Sync Endpoints =============

@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status(req: Request):
    """获取同步状态"""
    # TODO: 实现同步状态查询
    return SyncStatusResponse(
        is_synced=True,
        last_sync_time=None,
        pending_changes=0,
    )


@router.post("/sync/push")
def sync_push():
    """推送本地数据到云端"""
    # TODO: 实现推送同步
    raise HTTPException(status_code=501, detail="云端同步功能暂未实现")


@router.post("/sync/pull")
def sync_pull():
    """从云端拉取数据"""
    # TODO: 实现拉取同步
    raise HTTPException(status_code=501, detail="云端同步功能暂未实现")
