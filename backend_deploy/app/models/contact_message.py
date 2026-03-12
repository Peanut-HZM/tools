"""
Contact Message - 联系留言数据模型
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from .base import Base


class MessageStatus(enum.Enum):
    """留言状态枚举"""
    UNREAD = "unread"       # 未读
    READ = "read"           # 已读
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"   # 已完成


class ContactMessage(Base):
    """联系留言表"""

    __tablename__ = "contact_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 留言者信息
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)

    # 留言内容
    subject = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)

    # 状态管理
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.UNREAD, nullable=False, index=True)
    admin_reply = Column(Text, nullable=True)  # 管理员回复

    # 元数据
    ip_address = Column(String(100), nullable=True)  # 提交者 IP
    user_agent = Column(String(500), nullable=True)  # 用户代理

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<ContactMessage(id={self.id}, name={self.name}, email={self.email}, status={self.status.value})>"


# Pydantic 模式
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import uuid


class ContactMessageCreate(BaseModel):
    """创建留言请求"""
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    email: str = Field(..., description="邮箱")
    subject: Optional[str] = Field(None, max_length=200, description="主题")
    content: str = Field(..., min_length=1, description="留言内容")


class ContactMessageUpdate(BaseModel):
    """更新留言请求"""
    status: Optional[MessageStatus] = None
    admin_reply: Optional[str] = None


class ContactMessageResponse(BaseModel):
    """留言响应"""
    id: str
    name: str
    email: str
    subject: Optional[str]
    content: str
    status: str
    admin_reply: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class ContactMessageListResponse(BaseModel):
    """留言列表响应"""
    items: list[ContactMessageResponse]
    total: int
    page: int
    page_size: int
