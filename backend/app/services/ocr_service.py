import base64
import time
import numpy as np
import cv2
import logging
import httpx
from typing import List, Dict, Any
from app.models.ocr_models import OCRResponse, TextBlock, QRCodeResponse
from app.config.ocr_config import ocr_settings

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.api_url = ocr_settings.OCR_API_URL
        self.api_key = ocr_settings.API_KEY

    def _decode_image(self, image_data: str) -> np.ndarray:
        try:
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            img_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Image decoding failed: {e}")
            raise ValueError("Invalid image data")

    def predict(self, image_data: str, lang: str = "ch") -> OCRResponse:
        """
        调用远程 OCR 服务进行识别
        :param image_data: Base64 编码的图片数据
        :param lang: 语言代码
        """
        start_time = time.time()
        
        try:
            # 构造请求体 (参考 Umi-OCR 的 OcrRequest)
            # Umi-OCR 接收 { "base64": "...", "options": {...} }
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
                
            payload = {
                "base64": image_data,
                "options": {
                    "ocr.language": lang
                }
            }
            
            headers = {
                "api-key": self.api_key
            }
            
            target_url = f"{self.api_url}/api/ocr"
            logger.info(f"Calling OCR API: {target_url}")
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(target_url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    raise RuntimeError(f"OCR API error: {response.status_code} - {response.text}")
                
                result = response.json()
                
                # 解析响应 (参考 Umi-OCR 的 ApiResponse)
                # { "code": 100, "data": [...], "time": 0.5 }
                code = result.get("code")
                data = result.get("data")
                processing_time = result.get("time", 0.0)
                
                if code != 100 and code != 101:
                    raise RuntimeError(f"OCR failed with code {code}: {data}")
                
                # 解析 data -> blocks
                # data 结构假设: [{"text": "...", "box": [[x,y],...], "score": 0.9}]
                blocks = []
                full_text = []
                
                if isinstance(data, list):
                    for item in data:
                        text = item.get("text", "")
                        confidence = item.get("score", 0.0)
                        box = item.get("box", [])
                        
                        blocks.append(TextBlock(
                            text=text,
                            confidence=confidence,
                            box=box
                        ))
                        full_text.append(text)
                
                return OCRResponse(
                    text="\n".join(full_text),
                    blocks=blocks,
                    processing_time=processing_time
                )
                
        except Exception as e:
            logger.error(f"Remote OCR prediction failed: {e}")
            raise

    def predict_pdf(self, file_content: bytes) -> OCRResponse:
        """
        PDF OCR 识别 (转图片后调用远程 OCR)
        """
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise RuntimeError("pypdfium2 not installed")
            
        start_time = time.time()
        
        full_blocks = []
        full_text = []
        
        try:
            pdf = pdfium.PdfDocument(file_content)
            n_pages = len(pdf)
            
            # 使用 httpx client 复用连接
            with httpx.Client(timeout=60.0) as client:
                target_url = f"{self.api_url}/api/ocr"
                headers = {"api-key": self.api_key}
                
                for i in range(n_pages):
                    page = pdf[i]
                    # Render page to PIL image
                    pil_image = page.render(scale=2.0).to_pil()
                    
                    # Convert PIL image to Base64
                    import io
                    buffered = io.BytesIO()
                    pil_image.save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    # Call API
                    payload = {
                        "base64": img_base64,
                        "options": {"ocr.language": "ch"}
                    }
                    
                    response = client.post(target_url, json=payload, headers=headers)
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("code") in [100, 101]:
                            data = result.get("data", [])
                            if isinstance(data, list):
                                for item in data:
                                    text = item.get("text", "")
                                    confidence = item.get("score", 0.0)
                                    box = item.get("box", [])
                                    full_blocks.append(TextBlock(
                                        text=text,
                                        confidence=confidence,
                                        box=box
                                    ))
                                    full_text.append(text)
                        
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")
                    
        processing_time = time.time() - start_time
        
        return OCRResponse(
            text="\n".join(full_text),
            blocks=full_blocks,
            processing_time=processing_time
        )

    def scan_qrcode(self, image_data: str) -> QRCodeResponse:
        """
        二维码识别 (使用 OpenCV 原生识别，无需 zbar 系统库)
        """
        start_time = time.time()
        img = self._decode_image(image_data)
        
        # 使用 OpenCV 微信二维码识别引擎 (如果可用) 或原生 QRCodeDetector
        # 鉴于环境一致性，优先使用原生 QRCodeDetector
        detector = cv2.QRCodeDetector()
        
        # detectAndDecode 返回: (解码文本, 矩形框, 矫正后的二值图)
        val, points, straight_qrcode = detector.detectAndDecode(img)
        
        if not val:
            return QRCodeResponse(
                text="",
                type="None",
                processing_time=time.time() - start_time
            )
            
        return QRCodeResponse(
            text=val,
            type="QR_CODE",
            processing_time=time.time() - start_time
        )

ocr_service = OCRService()
