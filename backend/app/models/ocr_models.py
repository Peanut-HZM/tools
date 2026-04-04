from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class OCRRequest(BaseModel):
    image: str = Field(..., description="Base64 编码的图片字符串或 URL")
    lang: str = Field("ch", description="识别语言")

class QRCodeRequest(BaseModel):
    image: str = Field(..., description="Base64 编码的图片字符串")

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
    processing_time: float = Field(..., description="处理耗时 (秒)")

class OCRBatchRequest(BaseModel):
    images: List[str] = Field(..., description="Base64 图片列表")
    lang: str = Field("ch", description="识别语言")

class OCRBatchResponse(BaseModel):
    results: List[OCRResponse]

# ============ OCR 历史记录模型 ============

class OCRHistoryRecord(BaseModel):
    id: str
    user_id: str
    original_image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    recognized_text: str
    language: str
    block_count: int
    processing_time_ms: float
    file_size: Optional[int] = None
    image_dimensions: Optional[Dict[str, int]] = None
    created_at: datetime

class OCRHistoryListResponse(BaseModel):
    records: List[OCRHistoryRecord]
    total: int
    page: int
    page_size: int

# ============ OCR 导出格式 ============

class ExportFormat(str, Enum):
    TXT = "txt"
    MD = "md"
    JSON = "json"
    DOCX = "docx"
    PDF = "pdf"

class ExportOCRRequest(BaseModel):
    history_id: str
    format: ExportFormat = Field(ExportFormat.TXT, description="导出格式")

class ExportOCRResponse(BaseModel):
    file_name: str
    content: str
    file_size: int

# ============ OCR 配额管理 ============

class OCRQuotaInfo(BaseModel):
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    reset_date: datetime

class OCRBatchProcessRequest(BaseModel):
    images: List[str]
    lang: str = Field("ch", description="识别语言")
    auto_save: bool = Field(True, description="是否自动保存到历史记录")

class OCRBatchProcessResponse(BaseModel):
    success_count: int
    failed_count: int
    results: List[OCRResponse]
    history_ids: List[str]
    errors: List[Dict[str, str]] = []

# ============ 表格识别模型 ============

class TableRecognitionRequest(BaseModel):
    image: str
    output_format: str = Field("markdown", description="输出格式：markdown, html, excel")

class TableRecognitionResponse(BaseModel):
    tables: List[str]
    table_count: int
    processing_time: float
    confidence: float
