from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ImageExtractRequest(BaseModel):
    """图片提取请求"""
    url: HttpUrl


class ImageInfo(BaseModel):
    """图片信息"""
    url: str
    alt: str
    index: int
    width: Optional[int] = None
    height: Optional[int] = None


class ImageExtractResponse(BaseModel):
    """图片提取响应"""
    images: List[ImageInfo]
    count: int


class DownloadedImage(BaseModel):
    """已下载的图片信息"""
    url: str
    oss_url: str
    filename: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None


class BatchDownloadResponse(BaseModel):
    """批量下载响应"""
    success_count: int
    failed_count: int
    images: List[DownloadedImage]
    errors: List[Dict[str, str]] = []


class ImageHistoryRecord(BaseModel):
    """图片下载历史记录"""
    id: str
    user_id: str
    original_url: str
    oss_url: str
    filename: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    content_type: str
    created_at: datetime


class ImageHistoryListResponse(BaseModel):
    """图片历史记录列表响应"""
    records: List[ImageHistoryRecord]
    total: int
    page: int
    page_size: int


class ImageQuotaInfo(BaseModel):
    """图片下载配额信息"""
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    reset_date: datetime


class ImageExportFormat(str, Enum):
    """图片导出格式"""
    ZIP = "zip"
    JSON = "json"
