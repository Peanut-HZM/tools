from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class JSONFormatRequest(BaseModel):
    """JSON 格式化请求"""
    content: str = Field(..., description="JSON 内容")
    indent: int = Field(2, ge=0, le=8, description="缩进空格数")
    sort_keys: bool = Field(False, description="是否排序键")


class JSONFormatResponse(BaseModel):
    """JSON 格式化响应"""
    content: str = Field(..., description="格式化后的 JSON")
    original_size: int = Field(..., description="原始大小")
    formatted_size: int = Field(..., description="格式化后大小")


class JSONMinifyRequest(BaseModel):
    """JSON 压缩请求"""
    content: str = Field(..., description="JSON 内容")


class JSONMinifyResponse(BaseModel):
    """JSON 压缩响应"""
    content: str = Field(..., description="压缩后的 JSON")
    original_size: int = Field(..., description="原始大小")
    minified_size: int = Field(..., description="压缩后大小")
    compression_ratio: float = Field(..., description="压缩率")


class JSONValidateRequest(BaseModel):
    """JSON 校验请求"""
    content: str = Field(..., description="JSON 内容")


class JSONValidateResponse(BaseModel):
    """JSON 校验响应"""
    valid: bool = Field(..., description="是否有效")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_line: Optional[int] = Field(None, description="错误行号")
    error_column: Optional[int] = Field(None, description="错误列号")


class JSONCompareRequest(BaseModel):
    """JSON 比较请求"""
    json1: str = Field(..., description="第一个 JSON")
    json2: str = Field(..., description="第二个 JSON")


class JSONDiffItem(BaseModel):
    """JSON 差异项"""
    path: str = Field(..., description="差异路径")
    type: str = Field(..., description="差异类型：added/removed/changed")
    old_value: Optional[Any] = Field(None, description="旧值")
    new_value: Optional[Any] = Field(None, description="新值")


class JSONCompareResponse(BaseModel):
    """JSON 比较响应"""
    are_equal: bool = Field(..., description="是否相等")
    differences: List[JSONDiffItem] = Field(..., description="差异列表")
    diff_count: int = Field(..., description="差异数量")


class JSONConvertFormat(str, Enum):
    """JSON 转换格式"""
    XML = "xml"
    YAML = "yaml"
    CSV = "csv"
    TOML = "toml"


class JSONConvertRequest(BaseModel):
    """JSON 转换请求"""
    content: str = Field(..., description="JSON 内容")
    target_format: JSONConvertFormat = Field(..., description="目标格式")


class JSONConvertResponse(BaseModel):
    """JSON 转换响应"""
    content: str = Field(..., description="转换后的内容")
    format: str = Field(..., description="目标格式")


class JSONQueryRequest(BaseModel):
    """JSON 查询请求"""
    content: str = Field(..., description="JSON 内容")
    path: str = Field(..., description="JSONPath 表达式")


class JSONQueryResponse(BaseModel):
    """JSON 查询响应"""
    result: Any = Field(..., description="查询结果")
    result_type: str = Field(..., description="结果类型")


class JSONHistoryRecord(BaseModel):
    """JSON 操作历史记录"""
    id: str
    user_id: str
    operation_type: str  # format, minify, validate, compare, convert, query
    input_size: int
    output_size: Optional[int] = None
    created_at: datetime


class JSONHistoryListResponse(BaseModel):
    """JSON 历史记录列表响应"""
    records: List[JSONHistoryRecord]
    total: int
    page: int
    page_size: int


class JSONQuotaInfo(BaseModel):
    """JSON 操作配额信息"""
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    reset_date: datetime
