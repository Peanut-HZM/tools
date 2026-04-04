from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Body
from typing import List, Dict, Any
import io
import uuid
from app.models.converter_models import (
    ConvertResponse, ConverterHistoryListResponse, ConverterHistoryRecord,
    ConverterQuotaInfo, ConverterBatchResponse, EditContentResponse, EditContentRequest
)
from app.services.converter_service import converter_service
from app.middleware.auth_middleware import get_current_user_id, get_current_user

router = APIRouter(prefix="/converter", tags=["文档转换器"])


@router.post("/convert", response_model=ConvertResponse)
async def convert_document(
    file: UploadFile = File(...),
    save_history: bool = Query(True, description="是否保存历史记录"),
    user_id: str = Depends(get_current_user_id)
):
    """
    将文档（PDF、Word、Excel 等）转换为 Markdown
    """
    if not file:
        raise HTTPException(status_code=400, detail="请上传文件")

    try:
        result = await converter_service.convert_file(
            file=file,
            user_id=user_id,
            save_history=save_history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=ConverterHistoryListResponse)
async def get_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户文档转换历史记录"""
    try:
        records, total = converter_service.get_history(user_id, page, page_size)
        return ConverterHistoryListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota", response_model=ConverterQuotaInfo)
async def get_quota(user_id: str = Depends(get_current_user_id)):
    """获取用户配额信息"""
    try:
        return converter_service._check_quota(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-convert", response_model=Dict[str, Any])
async def batch_convert(
    files: List[UploadFile] = File(...),
    auto_save: bool = Query(True, description="是否自动保存历史记录"),
    user_id: str = Depends(get_current_user_id)
):
    """批量转换文档"""
    try:
        result = await converter_service.batch_convert(
            user_id=user_id,
            files=files,
            auto_save=auto_save
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit", response_model=EditContentResponse)
async def edit_content(
    request: EditContentRequest,
    user_id: str = Depends(get_current_user_id)
):
    """在线编辑并保存 Markdown 内容"""
    try:
        file_name, file_url, file_size = converter_service.save_content(
            user_id=user_id,
            content=request.content,
            file_name=request.file_name
        )
        return EditContentResponse(
            file_name=file_name,
            file_url=file_url,
            file_size=file_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{history_id}")
async def delete_history(
    history_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """删除转换历史记录"""
    try:
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        from sqlalchemy import text

        db = Session(next(get_db()))

        # 软删除
        result = db.execute(text("""
            UPDATE converter_history
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
