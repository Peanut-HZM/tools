"""图像生成工具 - Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.utils.image_gen_constants import (
    MAX_N_IMAGES,
    OPERATION_TEXT2IMG,
)


# ==================== 用户侧请求 ====================

class Text2ImgRequest(BaseModel):
    """文生图请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    n: int = Field(default=1, ge=1, le=MAX_N_IMAGES)
    style: Optional[str] = None
    model_preference: str = Field(default="auto")


class Img2ImgRequest(BaseModel):
    """图生图请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    strength: float = Field(default=0.6, ge=0.0, le=1.0)
    model_preference: str = Field(default="auto")


class InpaintRequest(BaseModel):
    """局部重绘请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    model_preference: str = Field(default="auto")


class UploadEditRequest(BaseModel):
    """上传图片编辑请求"""
    edit_type: str
    prompt: Optional[str] = Field(default=None, max_length=2000)


class PolishPromptRequest(BaseModel):
    """提示词润色请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    target_operation: str = OPERATION_TEXT2IMG


# ==================== 响应 ====================

class GenerationResult(BaseModel):
    """生成结果"""
    record_id: str
    result_url: str                    # OSS 签名 URL (1h)
    model_used: str
    duration_ms: int
    width: Optional[int] = None
    height: Optional[int] = None


class PolishPromptResult(BaseModel):
    """提示词润色结果"""
    polished_prompt: str
    original_prompt: str


class QuotaInfo(BaseModel):
    """用户配额信息"""
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_valid: bool


class HistoryRecord(BaseModel):
    """生成历史记录"""
    id: str
    operation: str
    prompt: Optional[str] = None
    result_url: str
    model_used: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str
    created_at: datetime


class HistoryListResponse(BaseModel):
    """历史记录分页响应"""
    items: List[HistoryRecord]
    total: int
    page: int
    page_size: int


# ==================== 管理侧 ====================

class GrantQuotaRequest(BaseModel):
    """管理员授予配额请求"""
    daily_limit: int = Field(..., ge=1)
    monthly_limit: int = Field(..., ge=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class QuotaRecord(BaseModel):
    """配额记录（管理侧）"""
    user_id: str
    daily_limit: int
    daily_used: int
    monthly_limit: int
    monthly_used: int
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    granted_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class DifyConfigView(BaseModel):
    """Dify 配置视图（返回给前端，不显示明文 key）"""
    api_url: str
    is_api_key_set: bool
    workflow_text2img: str
    workflow_img2img: str
    workflow_inpaint: str
    workflow_upload_edit: str
    default_timeout: float


class DifyConfigUpdate(BaseModel):
    """Dify 配置更新请求"""
    api_url: Optional[str] = None
    app_api_key: Optional[str] = None
    workflow_text2img: Optional[str] = None
    workflow_img2img: Optional[str] = None
    workflow_inpaint: Optional[str] = None
    workflow_upload_edit: Optional[str] = None
    default_timeout: Optional[float] = None


class DegradationConfigView(BaseModel):
    """降级配置视图"""
    enabled: bool
    failure_threshold: int
    degrade_duration_seconds: int
    current_status: str              # "normal" / "degraded"
    degraded_until: Optional[datetime] = None
    failure_count: int


class DegradationConfigUpdate(BaseModel):
    """降级配置更新请求"""
    enabled: Optional[bool] = None
    failure_threshold: Optional[int] = None
    degrade_duration_seconds: Optional[int] = None


class RetentionConfigView(BaseModel):
    """保留策略配置视图"""
    mode: str
    n_days: int
    cleanup_cron: str
    total_oss_keys: Optional[int] = None
    total_oss_bytes: Optional[int] = None


class RetentionConfigUpdate(BaseModel):
    """保留策略配置更新请求"""
    mode: Optional[str] = None
    n_days: Optional[int] = None
    cleanup_cron: Optional[str] = None
