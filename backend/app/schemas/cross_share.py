"""
CrossShare Schemas
"""
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    FILE = "file"
    LINK = "link"
    CLIPBOARD = "clipboard"
    IMAGE = "image"


class FileType(str, Enum):
    """文件类型"""
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    TEXT = "text"
    OTHER = "other"


class DeviceType(str, Enum):
    """设备类型"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


# ============ 设备相关 Schemas ============

class DeviceBase(BaseModel):
    """设备基础模型"""
    device_name: str
    device_type: Optional[str] = None


class DeviceCreate(DeviceBase):
    """创建设备请求"""
    device_token: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class DeviceUpdate(BaseModel):
    """更新设备请求"""
    device_name: Optional[str] = None
    is_active: Optional[bool] = None


class DeviceResponse(DeviceBase):
    """设备响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    device_token: str
    is_active: bool
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        return str(v) if v else v


# ============ 消息相关 Schemas ============

class MessageBase(BaseModel):
    """消息基础模型"""
    content: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    is_encrypted: bool = False


class MessageCreate(MessageBase):
    """创建消息请求"""
    file_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class MessageUpdate(BaseModel):
    """更新消息请求"""
    content: Optional[str] = None
    message_type: Optional[MessageType] = None
    is_read: Optional[bool] = None


class MessageResponse(BaseModel):
    """消息响应"""
    # 不继承 MessageBase，直接定义所有字段
    id: str
    user_id: str
    from_device_id: Optional[str] = None
    content: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    file_id: Optional[str] = None
    file: Optional["FileResponse"] = None
    is_encrypted: bool = False
    is_read: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    @field_validator('id', 'from_device_id', 'file_id', mode='before')
    @classmethod
    def validate_uuid_fields(cls, v):
        return str(v) if v else v

    @field_validator('message_type', mode='before')
    @classmethod
    def validate_message_type(cls, v):
        # 如果是字符串，转换为 MessageType 枚举
        if isinstance(v, str):
            try:
                return MessageType(v)
            except ValueError:
                return MessageType.TEXT
        return v


class ClipboardSyncRequest(BaseModel):
    """剪贴板同步请求"""
    content: str
    is_encrypted: bool = False


# ============ 文件相关 Schemas ============

class FileBase(BaseModel):
    """文件基础模型"""
    file_name: str
    file_type: FileType
    oss_bucket: str
    oss_key: str


class FileCreate(FileBase):
    """创建文件请求"""
    file_size: int
    file_hash: Optional[str] = None
    upload_device_id: Optional[str] = None


class FileUpdate(BaseModel):
    """更新文件请求"""
    file_name: Optional[str] = None
    file_type: Optional[FileType] = None


class FileResponse(FileBase):
    """文件响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    oss_url: Optional[str] = None
    file_size: int
    download_count: int
    is_deleted: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        return str(v) if v else v


class UploadTokenRequest(BaseModel):
    """请求上传令牌"""
    file_name: str
    file_size: int
    file_type: str


class UploadTokenResponse(BaseModel):
    """上传令牌响应"""
    token: str
    bucket: str
    oss_key: str
    upload_url: str
    file_id: str


class DownloadUrlResponse(BaseModel):
    """下载链接响应"""
    download_url: str
    expires_at: datetime


class FileStats(BaseModel):
    """文件统计"""
    total_files: int
    total_size: int
    used_quota: int
    available_quota: int
    usage_percentage: float


class StorageStats(BaseModel):
    """存储统计"""
    total_files: int
    total_size: int
    used_quota: int
    available_quota: int
    usage_percentage: float
    files_by_type: Dict[str, int]


# ============ 配置相关 Schemas ============

class ConfigBase(BaseModel):
    """配置基础模型"""
    max_file_size: int = 104857600  # 100MB
    storage_quota: int = 5368709120  # 5GB
    file_expire_days: int = 30
    enable_encryption: bool = False
    enable_clipboard: bool = True


class ConfigCreate(ConfigBase):
    """创建配置请求"""
    user_id: str


class ConfigUpdate(BaseModel):
    """更新配置请求"""
    max_file_size: Optional[int] = Field(None, ge=1048576, le=10737418240)  # 1MB - 10GB
    storage_quota: Optional[int] = Field(None, ge=1073741824, le=1099511627776)  # 1GB - 1TB
    file_expire_days: Optional[int] = Field(None, ge=1, le=365)
    enable_encryption: Optional[bool] = None
    enable_clipboard: Optional[bool] = None
    allowed_file_types: Optional[str] = None


class ConfigResponse(ConfigBase):
    """配置响应"""
    id: int
    user_id: str
    allowed_file_types: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 组合响应 ============

class MessageWithFileResponse(MessageResponse):
    """带文件的消息响应"""
    file: Optional[FileResponse] = None


class DeviceWithMessagesResponse(DeviceResponse):
    """带消息的设备响应"""
    messages: List[MessageResponse] = []


# ============ 列表响应 ============

class DeviceListResponse(BaseModel):
    """设备列表响应"""
    devices: List[DeviceResponse]
    total: int


class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[MessageResponse]
    total: int
    has_more: bool


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[FileResponse]
    total: int
    has_more: bool


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    configs: List[ConfigResponse]
    total: int
