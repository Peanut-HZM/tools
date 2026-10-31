"""
存储位置与配置迁移接口

- GET  /api/storage/status                      存储状态（服务器是否可用）
- POST /api/storage/{tool}/configs/{id}/migrate  迁移单条配置
- POST /api/storage/{tool}/configs/migrate-all   批量迁移
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth_middleware import get_current_user_id
from app.storage.locator import StorageLocation, server_available
from app.storage.migration import migrate_all, migrate_config
from app.storage.paths import get_local_db_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/storage", tags=["storage"])


class StorageStatusResponse(BaseModel):
    server_available: bool
    server_reason: str
    local_path: str


class MigrateRequest(BaseModel):
    target: str = Field(..., description="目标存储位置：local / server")


class MigrateResponse(BaseModel):
    success: bool
    storage_location: str
    message: str


class MigrateAllResponse(BaseModel):
    success: bool
    migrated: int
    failed: int
    errors: list = Field(default_factory=list)


@router.get("/status", response_model=StorageStatusResponse)
async def get_status():
    """获取存储状态：远程服务器是否可用 + 本地库路径"""
    available, reason = server_available()
    return StorageStatusResponse(
        server_available=available,
        server_reason=reason,
        local_path=str(get_local_db_path()),
    )


@router.post("/{tool}/configs/{config_id}/migrate", response_model=MigrateResponse)
async def migrate_one(
    tool: str,
    config_id: str,
    request: MigrateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """迁移单条配置到目标存储位置"""
    try:
        target = StorageLocation.from_value(request.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        return migrate_config(user_id, tool, config_id, target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("迁移配置 %s 失败：%s", config_id, exc)
        raise HTTPException(status_code=500, detail=f"迁移失败：{exc}")


@router.post("/{tool}/configs/migrate-all", response_model=MigrateAllResponse)
async def migrate_everything(
    tool: str,
    request: MigrateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """批量迁移该用户的全部配置到目标存储位置"""
    try:
        target = StorageLocation.from_value(request.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        return migrate_all(user_id, tool, target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("批量迁移失败：%s", exc)
        raise HTTPException(status_code=500, detail=f"批量迁移失败：{exc}")
