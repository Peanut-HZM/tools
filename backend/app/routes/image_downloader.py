from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any
from urllib.parse import urlparse
import io
import os
import uuid
import zipfile

from app.models.image_downloader_models import (
    ImageExtractRequest, ImageExtractResponse, ImageInfo,
    DownloadedImage, BatchDownloadResponse,
    ImageHistoryRecord, ImageHistoryListResponse,
    ImageQuotaInfo, ImageExportFormat
)
from app.services.image_downloader_service import image_downloader_service
from app.services.oss_service import oss_service
from app.middleware.auth_middleware import get_current_user_id

router = APIRouter(prefix="/image-downloader", tags=["图片下载器"])


@router.get("/proxy")
async def proxy_image(url: str):
    """
    公开代理端点：透传远端图片，不需要认证。
    用于前端预览和下载原图，避免 JWT 认证无法通过 window.open / a[download] 传递。
    """
    import requests as req

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="仅支持 http/https URL")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL 不合法")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    referer = image_downloader_service._get_referer(url)
    if referer:
        headers["Referer"] = referer

    try:
        response = req.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
    except req.RequestException as e:
        raise HTTPException(status_code=502, detail=f"获取图片失败：{str(e)}")

    content_type = response.headers.get("content-type", "image/jpeg")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片资源")

    return StreamingResponse(
        response.iter_content(chunk_size=8192),
        media_type=content_type,
    )


@router.post("/extract-images", response_model=ImageExtractResponse)
async def extract_images(request: ImageExtractRequest):
    """
    从指定网页提取所有图片 URL
    """
    try:
        images = image_downloader_service.extract_images(str(request.url))
        return ImageExtractResponse(
            images=images,
            count=len(images)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取图片失败：{str(e)}")


@router.get("/download", response_model=DownloadedImage)
async def download_image(
    url: str,
    save_history: bool = Query(True, description="是否保存历史记录"),
    user_id: str = Depends(get_current_user_id)
):
    """
    下载图片并上传到 OSS，返回 OSS URL
    """
    try:
        result = image_downloader_service.download_image(
            url=url,
            user_id=user_id,
            save_history=save_history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败：{str(e)}")


@router.post("/batch-download", response_model=Dict[str, Any])
async def batch_download(
    urls: List[str],
    save_history: bool = Query(True, description="是否保存历史记录"),
    user_id: str = Depends(get_current_user_id)
):
    """
    批量下载图片
    """
    try:
        result = image_downloader_service.batch_download(
            user_id=user_id,
            image_urls=urls,
            save_history=save_history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量下载失败：{str(e)}")


@router.get("/history", response_model=ImageHistoryListResponse)
async def get_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户图片下载历史记录"""
    try:
        records, total = image_downloader_service.get_history(user_id, page, page_size)
        return ImageHistoryListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota", response_model=ImageQuotaInfo)
async def get_quota(user_id: str = Depends(get_current_user_id)):
    """获取用户配额信息"""
    try:
        return image_downloader_service._check_quota(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_images(
    history_ids: List[str],
    format: ImageExportFormat = Query(ImageExportFormat.ZIP, description="导出格式"),
    user_id: str = Depends(get_current_user_id)
):
    """导出已下载的图片"""
    try:
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        from sqlalchemy import text

        db = Session(next(get_db()))

        # 获取历史记录
        placeholders = ','.join([f':id{i}' for i in range(len(history_ids))])
        params = {f'id{i}': hid for i, hid in enumerate(history_ids)}
        params['user_id'] = user_id

        result = db.execute(text(f"""
            SELECT oss_url, filename FROM image_history
            WHERE id IN ({placeholders}) AND user_id = :user_id
              AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
        """), params).fetchall()

        if not result:
            raise HTTPException(status_code=404, detail="未找到要导出的图片")

        if format == ImageExportFormat.ZIP:
            # 创建 ZIP 文件
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for row in result:
                    try:
                        # 从 OSS 下载文件
                        file_data = oss_service.download_file(row.oss_url)
                        zf.writestr(row.filename, file_data)
                    except Exception as e:
                        logger.warning(f"Failed to add {row.filename} to ZIP: {e}")

            zip_buffer.seek(0)

            return StreamingResponse(
                zip_buffer,
                media_type="application/x-zip-compressed",
                headers={"Content-Disposition": "attachment; filename=images.zip"}
            )

        elif format == ImageExportFormat.JSON:
            import json
            data = {
                "images": [
                    {"oss_url": row.oss_url, "filename": row.filename}
                    for row in result
                ]
            }
            return {
                "content": json.dumps(data, ensure_ascii=False, indent=2),
                "file_name": "images.json",
                "file_size": len(json.dumps(data).encode('utf-8'))
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{history_id}")
async def delete_history(
    history_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """删除图片下载历史记录"""
    try:
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        from sqlalchemy import text

        db = Session(next(get_db()))

        # 软删除
        result = db.execute(text("""
            UPDATE image_history
            SET is_deleted = TRUE
            WHERE id = :history_id AND user_id = :user_id
        """), {'history_id': history_id, 'user_id': user_id})

        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="历史记录不存在")

        return {"message": "历史记录已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
