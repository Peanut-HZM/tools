"""
CrossShare API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header, File, UploadFile
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import io
import logging

logger = logging.getLogger(__name__)

from app.models.base import get_db
from app.services.cross_share_service import CrossShareService
from app.config.config import settings
from app.schemas.cross_share import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageListResponse,
    ClipboardSyncRequest,
    FileCreate,
    FileUpdate,
    FileResponse,
    FileListResponse,
    FileStats,
    UploadTokenRequest,
    UploadTokenResponse,
    DownloadUrlResponse,
    ConfigResponse,
    ConfigUpdate,
    MessageType,
    FileType,
)
from app.services.auth_service import get_auth_service

router = APIRouter(prefix="/api/cross-share", tags=["cross-share"])


def get_current_user_id(
    authorization: Optional[str] = Header(None, description="Bearer token"),
) -> str:
    """
    从 JWT token 中获取当前用户 ID

    Args:
        authorization: Authorization header (Bearer <token>)

    Returns:
        用户 ID

    Raises:
        HTTPException: 如果 token 缺失或无效
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        auth_service = get_auth_service()
        token_data = auth_service.verify_token_data(token)
        return token_data.user_id
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def get_cross_share_service(db: Session = Depends(get_db)) -> CrossShareService:
    """获取 CrossShare 服务实例"""
    return CrossShareService(db)


def get_device_id_from_header(
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
) -> Optional[str]:
    """从 header 获取设备 ID"""
    return x_device_id


def get_oss_upload_url(oss_key: str) -> str:
    """获取 OSS 上传 URL（根据当前 provider 动态生成）"""
    from app.services.oss_service import oss_service
    return f"{oss_service._storage.provider.base_url}/{oss_key}"


def get_oss_download_url(oss_key: str, expires: int = 3600) -> str:
    """获取 OSS 下载 URL（带签名）

    优先返回直接访问 Minio 的签名 URL（性能最佳）。
    当存储服务不可用时，降级返回一个指向本后端代理的 URL，
    确保前端仍有机会通过代理获取文件，避免空指针错误。
    """
    from app.services.oss_service import oss_service

    if not oss_service.is_available():
        # 服务不可用时返回一个指向后端的内容代理 URL。
        # 该 URL 会在前端尝试访问时，由本后端负责从 OSS 读取并代理返回。
        # 注意：如果 OSS 持续不可用，该代理 URL 也会返回错误，但至少不会崩溃。
        logger.warning("OSS service not available, falling back to backend proxy URL")
        # 使用配置的公共 Minio URL 兜底（仅当 _storage 可用时才能生成有效 URL）
        try:
            storage = oss_service._storage
            if storage is not None and storage.provider is not None:
                return f"{storage.provider.base_url}/{oss_key}"
        except Exception:
            pass
        # storage 不可用时，返回一个明确的错误占位 URL
        # 前端应检查该 URL 是否指向本地代理，并给出友好提示
        return f"/api/cross-share/files/by-key/{oss_key}/proxy"

    # 生成签名 URL（公网 endpoint client 直接生成 https，无需事后改 scheme）
    download_url = oss_service.sign_url('GET', oss_key, expires)
    return download_url


# ============ 设备管理 ============

@router.get("/devices")  # 移除 response_model，直接返回字典
async def get_devices(
    current_user: str = Depends(get_current_user_id),
):
    """获取设备列表"""
    from app.config.database import get_db_connection

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, device_name, device_type, device_token,
                       user_agent, ip_address, is_active, last_seen_at, created_at, updated_at
                FROM cross_share_devices
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (current_user,))
            rows = cur.fetchall()

            devices = []
            for row in rows:
                devices.append({
                    "id": str(row["id"]) if row["id"] else None,
                    "user_id": row["user_id"],
                    "device_name": row["device_name"],
                    "device_type": row["device_type"],
                    "device_token": row["device_token"],
                    "user_agent": row["user_agent"],
                    "ip_address": row["ip_address"],
                    "is_active": bool(row["is_active"]) if row["is_active"] is not None else True,
                    "last_seen_at": str(row["last_seen_at"]) if row["last_seen_at"] else None,
                    "created_at": str(row["created_at"]) if row["created_at"] else None,
                    "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
                })

            return {
                "devices": devices,
                "total": len(devices),
            }
    finally:
        if conn:
            conn.close()


@router.post("/devices")  # 移除 response_model，直接返回字典
async def register_device(
    device: DeviceCreate,
    request: Request,
    current_user: str = Depends(get_current_user_id),
):
    """注册/更新设备"""
    from app.config.database import get_db_connection
    from datetime import datetime

    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 检查是否已存在设备
            cur.execute("""
                SELECT id FROM cross_share_devices WHERE device_token = %s
            """, (device.device_token,))
            existing = cur.fetchone()

            if existing:
                # 更新现有设备
                cur.execute("""
                    UPDATE cross_share_devices
                    SET device_name = %s,
                        device_type = %s,
                        ip_address = %s,
                        user_agent = %s,
                        last_seen_at = NOW(),
                        is_active = TRUE,
                        updated_at = NOW()
                    WHERE device_token = %s
                    RETURNING id, user_id, device_name, device_type, device_token,
                              user_agent, ip_address, is_active, last_seen_at, created_at, updated_at
                """, (
                    device.device_name,
                    device.device_type or "desktop",
                    ip_address,
                    user_agent,
                    device.device_token,
                ))
            else:
                # 创建新设备
                cur.execute("""
                    INSERT INTO cross_share_devices
                    (id, user_id, device_name, device_type, device_token, user_agent, ip_address, last_seen_at, is_active)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW(), TRUE)
                    RETURNING id, user_id, device_name, device_type, device_token,
                              user_agent, ip_address, is_active, last_seen_at, created_at, updated_at
                """, (
                    current_user,
                    device.device_name,
                    device.device_type or "desktop",
                    device.device_token,
                    user_agent,
                    ip_address,
                ))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row["id"]) if row["id"] else None,
                "user_id": row["user_id"],
                "device_name": row["device_name"],
                "device_type": row["device_type"],
                "device_token": row["device_token"],
                "user_agent": row["user_agent"],
                "ip_address": row["ip_address"],
                "is_active": bool(row["is_active"]) if row["is_active"] is not None else True,
                "last_seen_at": str(row["last_seen_at"]) if row["last_seen_at"] else None,
                "created_at": str(row["created_at"]) if row["created_at"] else None,
                "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
            }
    finally:
        if conn:
            conn.close()


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

@router.get("/messages")  # 移除 response_model，直接返回字典
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    message_type: Optional[MessageType] = None,
    current_user: str = Depends(get_current_user_id),
):
    """获取消息列表"""
    from app.config.database import get_db_connection

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if message_type:
                sql = """
                    SELECT id, user_id, from_device_id, content, message_type, file_id,
                           is_encrypted, is_read, expires_at, created_at
                    FROM cross_share_messages
                    WHERE user_id = %s
                      AND message_type = %s
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                params = (
                    current_user,
                    message_type.value if isinstance(message_type, MessageType) else message_type,
                    limit,
                    offset,
                )
            else:
                sql = """
                    SELECT id, user_id, from_device_id, content, message_type, file_id,
                           is_encrypted, is_read, expires_at, created_at
                    FROM cross_share_messages
                    WHERE user_id = %s
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                params = (current_user, limit, offset)

            cur.execute(sql, params)
            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append({
                    "id": str(row["id"]) if row["id"] else None,
                    "user_id": row["user_id"],
                    "from_device_id": str(row["from_device_id"]) if row["from_device_id"] else None,
                    "content": row["content"],
                    "message_type": row["message_type"] or "text",
                    "file_id": str(row["file_id"]) if row["file_id"] else None,
                    "is_encrypted": bool(row["is_encrypted"]) if row["is_encrypted"] is not None else False,
                    "is_read": bool(row["is_read"]) if row["is_read"] is not None else False,
                    "expires_at": str(row["expires_at"]) if row["expires_at"] else None,
                    "created_at": str(row["created_at"]) if row["created_at"] else None,
                })

            total = len(messages)
            return {
                "messages": messages,
                "total": total,
                "has_more": total == limit,
            }
    finally:
        if conn:
            conn.close()


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


@router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: str,
    message: MessageUpdate,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """编辑消息"""
    updated = service.update_message(
        message_id=message_id,
        user_id=current_user,
        content=message.content,
        message_type=message.message_type.value if message.message_type else None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="消息不存在")
    return updated


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


@router.get("/files/stats")
async def get_storage_stats(
    current_user: str = Depends(get_current_user_id),
):
    """获取存储统计"""
    from app.config.database import get_db_connection

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 总文件数和大小
            cur.execute("""
                SELECT COUNT(*) as total_files,
                       COALESCE(SUM(file_size), 0) as total_size
                FROM cross_share_files
                WHERE user_id = %s AND is_deleted = FALSE
            """, (current_user,))
            row = cur.fetchone()
            total_files = int(row["total_files"] or 0)
            total_size = int(row["total_size"] or 0)

            # 按文件类型统计
            cur.execute("""
                SELECT file_type, COUNT(*) as count
                FROM cross_share_files
                WHERE user_id = %s AND is_deleted = FALSE
                GROUP BY file_type
            """, (current_user,))
            rows = cur.fetchall()
            files_by_type = {row["file_type"]: int(row["count"]) for row in rows}

            # 获取用户配置的存储配额
            cur.execute("""
                SELECT storage_quota FROM cross_share_configs WHERE user_id = %s
            """, (current_user,))
            config_row = cur.fetchone()
            storage_quota = int(config_row["storage_quota"]) if config_row else 5368709120  # 5GB 默认

            return {
                "total_files": total_files,
                "total_size": total_size,
                "used_quota": total_size,
                "available_quota": max(0, storage_quota - total_size),
                "usage_percentage": (total_size / storage_quota * 100) if storage_quota > 0 else 0,
                "files_by_type": files_by_type,
            }
    finally:
        if conn:
            conn.close()


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


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
    from_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
):
    """上传文件到 OSS - 使用流式上传支持大文件"""
    from app.services.oss_service import oss_service
    import io

    file_name = file.filename or "unknown"
    file_type = file.content_type or "application/octet-stream"

    # 获取用户配置，检查文件大小限制
    config = service.get_config(current_user)

    # 检查存储空间（先获取当前统计）
    stats = service.get_storage_stats(current_user, config)

    # 生成 OSS key
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    oss_key = f"cross_share/{current_user}/{timestamp}/{unique_id}_{file_name}"

    # 上传到 OSS
    if not oss_service.is_available():
        raise HTTPException(status_code=500, detail="OSS 服务未初始化")

    try:
        # 读取文件内容到内存（对于大文件，可以考虑使用临时文件）
        file_content = await file.read()
        file_size = len(file_content)

        # 上传到 OSS
        url = oss_service.upload_file(
            object_name=oss_key,
            data=io.BytesIO(file_content),
            size=file_size,
            content_type=file_type,
            uploaded_by="system",
        )
        if not url:
            raise HTTPException(status_code=500, detail="上传到 OSS 失败")

        logger.info(f"File uploaded successfully: {file_name}, size: {file_size} bytes")
    except Exception as e:
        logger.error(f"上传文件到 OSS 失败：{e}")
        raise HTTPException(status_code=500, detail=f"上传文件失败：{str(e)}")

    # 检查文件大小限制
    if file_size > config.max_file_size:
        # 上传成功后删除文件
        try:
            oss_service.delete_file(oss_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({config.max_file_size / 1024 / 1024:.0f}MB)"
        )

    # 检查存储空间
    if stats["used_quota"] + file_size > config.storage_quota:
        # 上传成功后删除文件
        try:
            oss_service.delete_file(oss_key)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="存储空间不足")

    # 确定文件类型 - 优先根据扩展名判断，其次根据 MIME type
    response_file_type = FileType.OTHER

    # 获取文件扩展名
    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''

    # 根据扩展名判断文件类型
    ext_to_type = {
        # 图片
        'jpg': FileType.IMAGE, 'jpeg': FileType.IMAGE, 'png': FileType.IMAGE,
        'gif': FileType.IMAGE, 'webp': FileType.IMAGE, 'svg': FileType.IMAGE,
        'bmp': FileType.IMAGE, 'ico': FileType.IMAGE,
        # 视频
        'mp4': FileType.VIDEO, 'webm': FileType.VIDEO, 'avi': FileType.VIDEO,
        'mov': FileType.VIDEO, 'mkv': FileType.VIDEO, 'flv': FileType.VIDEO,
        'wmv': FileType.VIDEO, 'm4v': FileType.VIDEO,
        # 音频
        'mp3': FileType.AUDIO, 'wav': FileType.AUDIO, 'aac': FileType.AUDIO,
        'ogg': FileType.AUDIO, 'flac': FileType.AUDIO, 'm4a': FileType.AUDIO,
        'wma': FileType.AUDIO,
        # 文档
        'pdf': FileType.DOCUMENT, 'doc': FileType.DOCUMENT, 'docx': FileType.DOCUMENT,
        'xls': FileType.DOCUMENT, 'xlsx': FileType.DOCUMENT, 'ppt': FileType.DOCUMENT,
        'pptx': FileType.DOCUMENT, 'odt': FileType.DOCUMENT, 'ods': FileType.DOCUMENT,
        # 文本
        'txt': FileType.TEXT, 'md': FileType.TEXT, 'markdown': FileType.TEXT,
        'json': FileType.TEXT, 'xml': FileType.TEXT, 'csv': FileType.TEXT,
        'log': FileType.TEXT,
        # 压缩包
        'zip': FileType.ARCHIVE, 'rar': FileType.ARCHIVE, '7z': FileType.ARCHIVE,
        'tar': FileType.ARCHIVE, 'gz': FileType.ARCHIVE, 'bz2': FileType.ARCHIVE,
    }

    if ext in ext_to_type:
        response_file_type = ext_to_type[ext]
    # 扩展名未匹配时，根据 MIME type 判断
    elif file_type.startswith("image"):
        response_file_type = FileType.IMAGE
    elif file_type.startswith("video"):
        response_file_type = FileType.VIDEO
    elif file_type.startswith("audio"):
        response_file_type = FileType.AUDIO
    elif file_type in ["application/pdf", "application/msword", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        response_file_type = FileType.DOCUMENT
    elif file_type in ["text/plain", "text/markdown", "application/json", "text/xml", "text/csv"]:
        response_file_type = FileType.TEXT
    elif file_type in ["application/zip", "application/x-rar", "application/x-7z-compressed", "application/x-tar"]:
        response_file_type = FileType.ARCHIVE

    # 计算文件过期时间
    expires_at = datetime.now() + timedelta(days=config.file_expire_days)

    db_file = service.create_file(
        user_id=current_user,
        file=FileCreate(
            file_name=file_name,
            file_size=file_size,
            file_type=response_file_type,
            oss_bucket=settings.ALIYUN_OSS_BUCKET_NAME,
            oss_key=oss_key,
            upload_device_id=from_device_id,
        ),
        expires_at=expires_at,
    )

    # 生成下载 URL
    download_url = get_oss_download_url(oss_key, expires=3600)

    return {
        "file_id": str(db_file.id),
        "file_name": file_name,
        "file_size": file_size,
        "file_type": response_file_type.value if isinstance(response_file_type, FileType) else response_file_type,
        "oss_key": oss_key,
        "download_url": download_url,
        "created_at": db_file.created_at.isoformat() if db_file.created_at else None,
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


@router.put("/files/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: str,
    file: FileUpdate,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """更新文件信息"""
    updated = service.update_file(
        file_id=file_id,
        user_id=current_user,
        file_name=file.file_name,
        file_type=file.file_type.value if file.file_type else None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="文件不存在")
    return updated


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


@router.get("/files/{file_id}/preview")
async def preview_file(
    file_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """预览文件 - 通过后端代理转发到 OSS，解决 CORS 问题"""
    from fastapi.responses import RedirectResponse

    file = service.get_file_by_id(file_id, current_user)
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 生成临时预览 URL（1 小时过期）
    preview_url = get_oss_download_url(file.oss_key, expires=3600)

    # 重定向到 OSS 签名 URL
    # 使用 302 重定向，浏览器会自动跟随请求，绕过 CORS 限制
    return RedirectResponse(url=preview_url, status_code=302)


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    service: CrossShareService = Depends(get_cross_share_service),
    authorization: Optional[str] = Header(None, description="Bearer token"),
    token: Optional[str] = Query(None, description="JWT token for media files"),
):
    """获取文件内容 - 通过后端代理从 OSS 获取并返回，解决 CORS 问题

    支持文本类文件（markdown、json、txt 等）和媒体文件（视频、音频）的预览

    支持两种认证方式：
    - Authorization header: 适用于文本类文件预览
    - Query parameter: 适用于 HTML5 video/audio 标签（无法设置 header）
    """
    from fastapi.responses import StreamingResponse
    from app.services.oss_service import oss_service
    from app.services.auth_service import get_auth_service
    import io
    from jose import jwt

    # 优先使用 query parameter 的 token（适用于媒体文件）
    auth_token = token or (authorization.replace("Bearer ", "") if authorization else None)

    # 验证 token 并获取用户 ID
    user_id = None
    if auth_token:
        try:
            from app.config.config import settings as app_settings
            payload = jwt.decode(auth_token, app_settings.JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("sub")
        except Exception:
            pass

    if not user_id:
        raise HTTPException(status_code=401, detail="未授权访问")

    file = service.get_file_by_id(file_id, user_id)
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    if not oss_service.is_available():
        raise HTTPException(status_code=500, detail="OSS 服务未初始化")

    try:
        # 从 OSS 获取文件内容
        obj = oss_service.get_object(file.oss_key)
        content = obj.read()

        # 根据文件扩展名设置正确的 Content-Type
        ext = file.file_name.lower().split('.')[-1] if '.' in file.file_name else ''

        # 扩展 Content-Type 映射表，支持媒体文件
        content_type_map = {
            # 文本类
            'md': 'text/markdown; charset=utf-8',
            'markdown': 'text/markdown; charset=utf-8',
            'json': 'application/json; charset=utf-8',
            'txt': 'text/plain; charset=utf-8',
            'csv': 'text/csv; charset=utf-8',
            'xml': 'application/xml; charset=utf-8',
            'log': 'text/plain; charset=utf-8',
            # 视频类
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime',
            'mkv': 'video/x-matroska',
            'flv': 'video/x-flv',
            'wmv': 'video/x-ms-wmv',
            'm4v': 'video/x-m4v',
            # 音频类
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'aac': 'audio/aac',
            'ogg': 'audio/ogg',
            'flac': 'audio/flac',
            'm4a': 'audio/mp4',
            'wma': 'audio/x-ms-wma',
        }

        content_type = content_type_map.get(ext, 'application/octet-stream')

        # 返回流式响应，添加 CORS 头
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            }
        )
    except Exception as e:
        logger.error(f"Failed to get file content from OSS: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件内容失败：{str(e)}")


@router.get("/files/by-key/{oss_key:path}/proxy")
async def proxy_file_by_key(
    oss_key: str,
    service: CrossShareService = Depends(get_cross_share_service),
    current_user: str = Depends(get_current_user_id),
):
    """文件内容代理 - 根据 oss_key 从 OSS 读取并返回

    当 OSS 签名 URL 不可用时的降级方案。
    """
    from fastapi.responses import StreamingResponse
    from app.services.oss_service import oss_service
    import io

    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="存储服务不可用，请稍后重试")

    # 根据 oss_key 找到对应的文件记录
    file = service.get_file_by_oss_key(oss_key, current_user)
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        obj = oss_service.get_object(oss_key)
        content = obj.read()

        ext = file.file_name.lower().split('.')[-1] if '.' in file.file_name else ''
        content_type_map = {
            'md': 'text/markdown; charset=utf-8', 'markdown': 'text/markdown; charset=utf-8',
            'json': 'application/json; charset=utf-8', 'txt': 'text/plain; charset=utf-8',
            'csv': 'text/csv; charset=utf-8', 'xml': 'application/xml; charset=utf-8',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'webp': 'image/webp', 'svg': 'image/svg+xml',
            'pdf': 'application/pdf', 'mp4': 'video/mp4', 'webm': 'video/webm',
            'mp3': 'audio/mpeg', 'wav': 'audio/wav',
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')

        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'inline; filename="{file.file_name}"',
            }
        )
    except Exception as e:
        logger.error(f"Failed to proxy file by key from OSS: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件内容失败：{str(e)}")


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
