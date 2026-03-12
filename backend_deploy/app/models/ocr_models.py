from pydantic import BaseModel, Field
from typing import List, Optional

class OCRRequest(BaseModel):
    image: str = Field(..., description="Base64编码的图片字符串或URL")
    lang: str = Field("ch", description="识别语言")
    
class QRCodeRequest(BaseModel):
    image: str = Field(..., description="Base64编码的图片字符串")

class QRCodeResponse(BaseModel):
    text: str = Field(..., description="二维码内容")
    type: str = Field(..., description="码类型")
    processing_time: float

class TextBlock(BaseModel):
    text: str
    confidence: float
    box: List[List[int]]

class OCRResponse(BaseModel):
    text: str = Field(..., description="合并后的完整文本")
    blocks: List[TextBlock] = Field(..., description="识别出的文本块详情")
    processing_time: float = Field(..., description="处理耗时(秒)")

class OCRBatchRequest(BaseModel):
    images: List[str] = Field(..., description="Base64图片列表")
    lang: str = Field("ch", description="识别语言")

class OCRBatchResponse(BaseModel):
    results: List[OCRResponse]
