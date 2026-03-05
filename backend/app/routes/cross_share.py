"""
CrossShare API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from app.models.base import get_db
from app.services.cross_share_service import CrossShareService
from app.config.config import settings
from app.schemas.cross_share import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    ClipboardSyncRequest,
    FileCreate,
    FileResponse,
    FileListResponse,
    FileStats,
    StorageStats,
    UploadTokenRequest,
    UploadTokenResponse,
    DownloadUrlResponse,
    ConfigResponse,
    ConfigUpdate,
    MessageType,
    FileType,
)

router = APIRouter(prefix="/api/cross-share", tags=["cross-share"])


def get_current_user_id(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> str:
    """获取当前用户 ID"""
    # TODO: 从 JWT token 中解析用户 ID
    # 暂时从 header 中获取（简化处理）
    user_id = request.headers.get("X-User-Id")
    if not user_id and authorization:
        # 尝试从 authorization header 解析
        # 这里应该解析 JWT，暂时简化处理
        pass

    if not user_id:
        # 对于开发环境，使用默认用户 ID
        user_id = "default-user"

    return user_id


def get_cross_share_service(db: Session = Depends(get_db)) -> CrossShareService:
    """获取 CrossShare 服务实例"""
    return CrossShareService(db)


def get_device_id_from_header(
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
) -> Optional[str]:
    """从 header 获取设备 ID"""
    return x_device_id


def get_oss_upload_url(oss_key: str) -> str:
    """获取 OSS 上传 URL"""
    return f"https://{settings.ALIYUN_OSS_BUCKET_NAME}.{settings.ALIYUN_OSS_ENDPOINT}/{oss_key}"


def get_oss_download_url(oss_key: str, expires: int = 3600) -> str:
    """获取 OSS 下载 URL（带签名）"""
    # 简单实现：返回公共读 URL
    # 如果需要签名 URL，需要使用 oss2 的 sign_url 方法
    return f"https://{settings.ALIYUN_OSS_BUCKET_NAME}.{settings.ALIYUN_OSS_ENDPOINT}/{oss_key}"


# ============ 设备管理 ============

@router.get("/devices", response_model=DeviceListResponse)
async def get_devices(
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取设备列表"""
    devices = service.get_devices(current_user)
    return {
        "devices": devices,
        "total": len(devices),
    }


@router.post("/devices", response_model=DeviceResponse)
async def register_device(
    device: DeviceCreate,
    request: Request,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """注册/更新设备"""
    # 获取 User-Agent 和 IP
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    # 创建设备
    db_device = service.create_or_update_device(
        user_id=current_user,
        device=DeviceCreate(
            device_name=device.device_name,
            device_type=device.device_type,
            device_token=device.device_token,
            user_agent=user_agent,
            ip_address=ip_address,
        ),
    )
    return db_device


@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device: DeviceUpdate,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """更新设备"""
    updated = service.update_device(device_id, current_user, device)
    if not updated:
        raise HTTPException(status_code=404, detail="设备不存在")
    return updated


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """删除设备"""
    if not service.delete_device(device_id, current_user):
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"message": "设备已删除"}


@router.post("/devices/{device_id}/ping", response_model=DeviceResponse)
async def ping_device(
    device_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """更新设备活跃时间"""
    updated = service.ping_device(device_id, current_user)
    if not updated:
        raise HTTPException(status_code=404, detail="设备不存在")
    return updated


# ============ 消息功能 ============

@router.get("/messages", response_model=MessageListResponse)
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    message_type: Optional[MessageType] = None,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取消息列表"""
    messages = service.get_messages(current_user, limit=limit, offset=offset, message_type=message_type)
    total = len(messages)
    return {
        "messages": messages,
        "total": total,
        "has_more": total == limit,
    }


@router.post("/messages", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
    from_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
):
    """发送消息"""
    db_message = service.create_message(
        user_id=current_user,
        message=message,
        from_device_id=from_device_id,
    )
    return db_message


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """删除消息"""
    if not service.delete_message(message_id, current_user):
        raise HTTPException(status_code=404, detail="消息不存在")
    return {"message": "消息已删除"}


@router.post("/messages/{message_id}/read", response_model=MessageResponse)
async def mark_message_read(
    message_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """标记消息为已读"""
    updated = service.mark_message_as_read(message_id, current_user)
    if not updated:
        raise HTTPException(status_code=404, detail="消息不存在")
    return updated


@router.get("/messages/clipboard", response_model=MessageListResponse)
async def get_clipboard_history(
    limit: int = Query(100, ge=1, le=200),
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取剪贴板历史"""
    messages = service.get_clipboard_history(current_user, limit=limit)
    return {
        "messages": messages,
        "total": len(messages),
        "has_more": False,
    }


@router.post("/messages/clipboard", response_model=MessageResponse)
async def sync_clipboard(
    request: ClipboardSyncRequest,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
    from_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
):
    """同步剪贴板"""
    message = service.create_clipboard_message(
        user_id=current_user,
        content=request.content,
        from_device_id=from_device_id,
        is_encrypted=request.is_encrypted,
    )
    return message


# ============ 文件功能 ============

@router.get("/files", response_model=FileListResponse)
async def get_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    file_type: Optional[FileType] = None,
    search: Optional[str] = None,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取文件列表"""
    files = service.get_files(current_user, limit=limit, offset=offset, file_type=file_type, search=search)
    total = len(files)
    return {
        "files": files,
        "total": total,
        "has_more": total == limit,
    }


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取文件详情"""
    file = service.get_file_by_id(file_id, current_user)
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return file


@router.post("/files/upload", response_model=UploadTokenResponse)
async def upload_file(
    request: UploadTokenRequest,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
    from_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
):
    """获取上传令牌"""
    # 获取用户配置，检查文件大小限制
    config = service.get_config(current_user)
    if request.file_size > config.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({config.max_file_size / 1024 / 1024:.0f}MB)"
        )

    # 检查存储空间
    stats = service.get_storage_stats(current_user, config)
    if stats["used_quota"] + request.file_size > config.storage_quota:
        raise HTTPException(status_code=400, detail="存储空间不足")

    # 生成 OSS key
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    oss_key = f"cross_share/{current_user}/{timestamp}/{unique_id}_{request.file_name}"

    # 获取上传 URL
    upload_url = get_oss_upload_url(oss_key)

    # 创建文件记录
    file_type = FileType.OTHER
    if request.file_type.startswith("image"):
        file_type = FileType.IMAGE
    elif request.file_type.startswith("video"):
        file_type = FileType.VIDEO
    elif request.file_type.startswith("audio"):
        file_type = FileType.AUDIO
    elif request.file_type in ["application/pdf", "application/msword"]:
        file_type = FileType.DOCUMENT
    elif request.file_type in ["text/plain", "text/markdown"]:
        file_type = FileType.TEXT
    elif request.file_type in ["application/zip", "application/x-rar"]:
        file_type = FileType.ARCHIVE

    db_file = service.create_file(
        user_id=current_user,
        file=FileCreate(
            file_name=request.file_name,
            file_size=request.file_size,
            file_type=file_type,
            oss_bucket=settings.ALIYUN_OSS_BUCKET_NAME,
            oss_key=oss_key,
            upload_device_id=from_device_id,
        ),
    )

    return {
        "token": "direct-upload",  # OSS 直传不需要额外 token
        "bucket": settings.ALIYUN_OSS_BUCKET_NAME,
        "oss_key": oss_key,
        "upload_url": upload_url,
        "file_id": str(db_file.id),
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """删除文件"""
    if not service.delete_file(file_id, current_user):
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"message": "文件已删除"}


@router.post("/files/{file_id}/download", response_model=DownloadUrlResponse)
async def get_download_url(
    file_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取下载链接"""
    file = service.get_file_by_id(file_id, current_user)
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 增加下载计数
    service.increment_download_count(file_id, current_user)

    # 生成临时下载 URL（1 小时过期）
    download_url = get_oss_download_url(file.oss_key, expires=3600)

    return {
        "download_url": download_url,
        "expires_at": datetime.now() + timedelta(hours=1),
    }


@router.get("/files/stats", response_model=StorageStats)
async def get_storage_stats(
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取存储统计"""
    config = service.get_config(current_user)
    stats = service.get_storage_stats(current_user, config)
    return stats


# ============ 配置管理 ============

@router.get("/config", response_model=ConfigResponse)
async def get_config(
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """获取用户配置"""
    config = service.get_config(current_user)
    return config


@router.put("/config", response_model=ConfigResponse)
async def update_config(
    config: ConfigUpdate,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """更新用户配置"""
    updated = service.update_config(current_user, config)
    return updated
