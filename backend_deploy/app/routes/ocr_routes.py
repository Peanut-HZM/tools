from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from app.models.ocr_models import OCRRequest, OCRResponse, QRCodeRequest, QRCodeResponse
from app.services.ocr_service import ocr_service
from app.middleware.auth_middleware import get_current_user

router = APIRouter(tags=["OCR"])

@router.post("/tools/ocr/predict", response_model=OCRResponse)
async def predict_ocr(
    request: OCRRequest = Body(...),
    current_user = Depends(get_current_user)
):
    """
    OCR 文字识别接口 (支持 Base64 图片)
    """
    try:
        result = ocr_service.predict(request.image, request.lang)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.post("/tools/ocr/pdf", response_model=OCRResponse)
async def predict_pdf_ocr(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    OCR PDF 识别接口 (支持 PDF 文件上传)
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    try:
        content = await file.read()
        result = ocr_service.predict_pdf(content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.post("/tools/ocr/qrcode", response_model=QRCodeResponse)
async def scan_qrcode(
    request: QRCodeRequest = Body(...),
    current_user = Depends(get_current_user)
):
    """
    二维码识别接口
    """
    try:
        result = ocr_service.scan_qrcode(request.image)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
