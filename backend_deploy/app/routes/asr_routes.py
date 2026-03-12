import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.models.asr_models import ASRResponse
from app.services.asr_service import asr_service
from app.middleware.auth_middleware import get_current_user
import tempfile

router = APIRouter(tags=["ASR"])

@router.post("/tools/asr/predict", response_model=ASRResponse)
async def predict_asr(
    file: UploadFile = File(...),
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
        result = asr_service.predict(temp_file_path)
        return result
        
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
