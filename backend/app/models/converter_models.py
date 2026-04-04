from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ConvertRequest(BaseModel):
    """文档转换请求"""
    pass


class ConvertResponse(BaseModel):
    """文档转换响应"""
    content: str = Field(..., description="转换后的 Markdown 内容")
    file_name: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="原始文件大小")
    output_size: int = Field(..., description="输出 Markdown 大小")


class ConverterHistoryRecord(BaseModel):
    """文档转换历史记录"""
    id: str
    user_id: str
    original_file_name: str
    original_file_url: Optional[str] = None
    markdown_file_url: Optional[str] = None
    file_size: int
    output_size: int
    content_type: str
    word_count: int
    processing_time_ms: float
    created_at: datetime


class ConverterHistoryListResponse(BaseModel):
    """文档转换历史记录列表响应"""
    records: List[ConverterHistoryRecord]
    total: int
    page: int
    page_size: int


class ConverterQuotaInfo(BaseModel):
    """文档转换配额信息"""
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    reset_date: datetime


class ConverterBatchRequest(BaseModel):
    """批量转换请求"""
    auto_save: bool = Field(True, description="是否自动保存历史记录")


class ConverterBatchResponse(BaseModel):
    """批量转换响应"""
    success_count: int
    failed_count: int
    results: List[ConvertResponse]
    history_ids: List[str]
    errors: List[Dict[str, str]] = []


class EditContentRequest(BaseModel):
    """在线编辑内容请求"""
    content: str = Field(..., description="要保存的内容")
    file_name: Optional[str] = Field(None, description="文件名")


class EditContentResponse(BaseModel):
    """在线编辑内容响应"""
    file_name: str
    file_url: str
    file_size: int
