from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ASRRequest(BaseModel):
    language: str = Field("zh", description="音频语言")

class ASRResponse(BaseModel):
    text: str = Field(..., description="识别出的文本")
    duration: float = Field(..., description="音频时长")
    processing_time: float = Field(..., description="处理耗时")

# ============ ASR 历史记录模型 ============

class ASRHistoryRecord(BaseModel):
    id: str
    user_id: str
    original_audio_url: Optional[str] = None
    recognized_text: str
    language: str
    duration_seconds: float
    processing_time_ms: float
    file_size: Optional[int] = None
    audio_format: Optional[str] = None
    created_at: datetime

class ASRHistoryListResponse(BaseModel):
    records: List[ASRHistoryRecord]
    total: int
    page: int
    page_size: int

# ============ ASR 导出格式 ============

class ASRExportFormat(str, Enum):
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"
    JSON = "json"
    LRC = "lrc"

class ExportASRRequest(BaseModel):
    history_id: str
    format: ASRExportFormat = Field(ASRExportFormat.TXT, description="导出格式")

class ExportASRResponse(BaseModel):
    file_name: str
    content: str
    file_size: int

# ============ ASR 配额管理 ============

class ASRQuotaInfo(BaseModel):
    user_id: str
    daily_limit_minutes: int
    daily_used_minutes: float
    daily_remaining_minutes: float
    monthly_limit_minutes: int
    monthly_used_minutes: float
    monthly_remaining_minutes: float
    reset_date: datetime

class ASRBatchProcessRequest(BaseModel):
    audio_files: List[str]  # 文件路径或 URL 列表
    language: str = Field("zh", description="音频语言")
    auto_save: bool = Field(True, description="是否自动保存到历史记录")

class ASRBatchProcessResponse(BaseModel):
    success_count: int
    failed_count: int
    results: List[ASRResponse]
    history_ids: List[str]
    errors: List[Dict[str, str]] = []

# ============ 说话人分离模型 ============

class SpeakerDiarizationRequest(BaseModel):
    audio_file: str
    num_speakers: Optional[int] = Field(None, description="说话人数量，为空则自动检测")

class SpeakerSegment(BaseModel):
    speaker: str
    start_time: float
    end_time: float
    text: str

class SpeakerDiarizationResponse(BaseModel):
    speakers: List[str]
    segments: List[SpeakerSegment]
    processing_time: float
