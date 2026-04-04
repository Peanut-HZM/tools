import os
import shutil
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from typing import List, Optional, Dict, Any
from app.models.asr_models import (
    ASRResponse, ASRRequest,
    ASRHistoryListResponse, ASRHistoryRecord,
    ExportASRRequest, ExportASRResponse,
    ASRQuotaInfo, ASRBatchProcessRequest, ASRBatchProcessResponse,
    SpeakerDiarizationRequest, SpeakerDiarizationResponse, ASRExportFormat
)
from app.services.asr_service import asr_service
from app.middleware.auth_middleware import get_current_user_id, get_current_user
import tempfile
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/asr", tags=["ASR 语音识别"])


@router.post("/predict", response_model=ASRResponse)
async def predict_asr(
    file: UploadFile = File(...),
    language: str = Query("zh", description="音频语言"),
    save_history: bool = Query(True, description="是否保存历史记录"),
    user_id: str = Depends(get_current_user_id),
    current_user = Depends(get_current_user)
):
    """
    语音识别接口
    """
    temp_file_path = None
    try:
        # 保存上传的文件到临时目录
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        # 执行识别
        result = asr_service.predict(
            temp_file_path,
            language=language,
            user_id=user_id if save_history else None,
            save_history=save_history
        )
        return result

    except RuntimeError as e:
        logger.error(f"ASR prediction failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"ASR failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@router.get("/history", response_model=ASRHistoryListResponse)
async def get_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户 ASR 历史记录"""
    try:
        records, total = asr_service.get_history(user_id, page, page_size)
        return ASRHistoryListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Get ASR history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota", response_model=ASRQuotaInfo)
async def get_quota(user_id: str = Depends(get_current_user_id)):
    """获取用户配额信息"""
    try:
        return asr_service._check_quota(user_id)
    except Exception as e:
        logger.error(f"Get ASR quota failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export", response_model=ExportASRResponse)
async def export_asr(
    request: ExportASRRequest,
    user_id: str = Depends(get_current_user_id)
):
    """导出 ASR 识别结果"""
    try:
        return asr_service.export_ocr_result(
            user_id=user_id,
            history_id=request.history_id,
            export_format=request.format
        )
    except ValueError as e:
        logger.error(f"Export ASR failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export ASR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-process", response_model=Dict[str, Any])
async def batch_process(
    files: List[UploadFile] = File(...),
    language: str = Query("zh", description="音频语言"),
    auto_save: bool = Query(True, description="是否自动保存"),
    user_id: str = Depends(get_current_user_id)
):
    """批量 ASR 识别"""
    try:
        temp_files = []
        for file in files:
            suffix = os.path.splitext(file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_files.append(temp_file.name)

        result = asr_service.batch_process(
            user_id=user_id,
            audio_files=temp_files,
            language=language,
            auto_save=auto_save
        )

        return result

    except Exception as e:
        logger.error(f"Batch ASR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        for temp_file_path in temp_files:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass


@router.post("/speaker-diarization", response_model=SpeakerDiarizationResponse)
async def speaker_diarization(
    file: UploadFile = File(...),
    num_speakers: Optional[int] = Query(None, ge=1, le=10, description="说话人数量"),
    user_id: str = Depends(get_current_user_id)
):
    """说话人分离"""
    temp_file_path = None
    try:
        # 保存上传的文件到临时目录
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        # 执行说话人分离
        result = asr_service.speaker_diarization(
            user_id=user_id,
            audio_file=temp_file_path,
            num_speakers=num_speakers
        )
        return result

    except Exception as e:
        logger.error(f"Speaker diarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
