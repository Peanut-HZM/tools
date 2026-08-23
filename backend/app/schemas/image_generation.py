"""图像生成工具 - Pydantic 请求/响应模型"""
import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.image_gen_constants import (
    MAX_N_IMAGES,
    OPERATION_TEXT2IMG,
    VALID_EDIT_TYPES,
    VALID_MODEL_PREFERENCES,
    VALID_OPERATIONS,
    VALID_SIZES,
    RETENTION_MODE_KEEP_FOREVER,
    RETENTION_MODE_DELETE_AFTER_N_DAYS,
    RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS,
)

# 允许的保留策略模式（来自常量文件，避免硬编码）
VALID_RETENTION_MODES = {
    RETENTION_MODE_KEEP_FOREVER,
    RETENTION_MODE_DELETE_AFTER_N_DAYS,
    RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS,
}

# cron 表达式单个字段的合法字符（数字、* / , -）
_CRON_FIELD_PATTERN = re.compile(r"^[\d*/,\-]+$")


def _validate_size(v: str) -> str:
    """校验尺寸在白名单内"""
    if v not in VALID_SIZES:
        raise ValueError(f"无效的尺寸: {v}，允许值: {sorted(VALID_SIZES)}")
    return v


def _validate_model_preference(v: str) -> str:
    """校验模型偏好在白名单内"""
    if v not in VALID_MODEL_PREFERENCES:
        raise ValueError(f"无效的模型偏好: {v}，允许值: {sorted(VALID_MODEL_PREFERENCES)}")
    return v


# ==================== 用户侧请求 ====================

class Text2ImgRequest(BaseModel):
    """文生图请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    n: int = Field(default=1, ge=1, le=MAX_N_IMAGES)
    style: Optional[str] = None
    model_preference: str = Field(default="auto")

    _check_size = field_validator("size")(_validate_size)
    _check_model_preference = field_validator("model_preference")(_validate_model_preference)


class Img2ImgRequest(BaseModel):
    """图生图请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    strength: float = Field(default=0.6, ge=0.0, le=1.0)
    model_preference: str = Field(default="auto")

    _check_size = field_validator("size")(_validate_size)
    _check_model_preference = field_validator("model_preference")(_validate_model_preference)


class InpaintRequest(BaseModel):
    """局部重绘请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    model_preference: str = Field(default="auto")

    _check_size = field_validator("size")(_validate_size)
    _check_model_preference = field_validator("model_preference")(_validate_model_preference)


class UploadEditRequest(BaseModel):
    """上传图片编辑请求"""
    edit_type: str
    prompt: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("edit_type")
    @classmethod
    def _check_edit_type(cls, v: str) -> str:
        """校验编辑类型在白名单内"""
        if v not in VALID_EDIT_TYPES:
            raise ValueError(f"无效的编辑类型: {v}，允许值: {sorted(VALID_EDIT_TYPES)}")
        return v


class PolishPromptRequest(BaseModel):
    """提示词润色请求"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    target_operation: str = OPERATION_TEXT2IMG

    @field_validator("target_operation")
    @classmethod
    def _check_target_operation(cls, v: str) -> str:
        """校验目标操作类型在白名单内"""
        if v not in VALID_OPERATIONS:
            raise ValueError(f"无效的操作类型: {v}，允许值: {sorted(VALID_OPERATIONS)}")
        return v


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
    daily_limit: int = Field(..., ge=1, le=10000)
    monthly_limit: int = Field(..., ge=1, le=100000)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_valid_period(self) -> "GrantQuotaRequest":
        """校验有效期顺序：同时设置时 valid_until 必须晚于 valid_from"""
        if self.valid_from is not None and self.valid_until is not None:
            if self.valid_until <= self.valid_from:
                raise ValueError("valid_until 必须晚于 valid_from")
        return self


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
    default_timeout: Optional[float] = Field(default=None, gt=0, le=600)


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
    failure_threshold: Optional[int] = Field(default=None, ge=1)
    degrade_duration_seconds: Optional[int] = Field(default=None, ge=1, le=86400)


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
    n_days: Optional[int] = Field(default=None, ge=1, le=3650)
    cleanup_cron: Optional[str] = None

    @field_validator("mode")
    @classmethod
    def _check_mode(cls, v: Optional[str]) -> Optional[str]:
        """校验保留策略模式在白名单内"""
        if v is not None and v not in VALID_RETENTION_MODES:
            raise ValueError(f"无效的保留策略模式: {v}，允许值: {sorted(VALID_RETENTION_MODES)}")
        return v

    @field_validator("cleanup_cron")
    @classmethod
    def _check_cleanup_cron(cls, v: Optional[str]) -> Optional[str]:
        """轻量校验 cron 格式：5 个空白分隔字段，每字段仅含数字和 * / , -"""
        if v is None:
            return v
        fields = v.split()
        if len(fields) != 5:
            raise ValueError("cron 表达式必须恰好包含 5 个字段")
        for f in fields:
            if not _CRON_FIELD_PATTERN.match(f):
                raise ValueError(f"cron 字段包含非法字符: {f}")
        return v
