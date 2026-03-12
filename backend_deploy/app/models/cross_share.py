"""
CrossShare 跨设备共享数据模型
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class Device(Base):
    """设备表"""

    __tablename__ = "cross_share_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), nullable=False, index=True)
    device_name = Column(String(200), nullable=False)
    device_type = Column(String(50))  # desktop/mobile/tablet
    device_token = Column(String(500), unique=True)  # 设备唯一标识
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<Device(id={self.id}, name={self.device_name}, user_id={self.user_id})>"


class CrossMessage(Base):
    """跨设备消息表"""

    __tablename__ = "cross_share_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), nullable=False, index=True)
    from_device_id = Column(UUID(as_uuid=True), ForeignKey("cross_share_devices.id"), nullable=True)
    content = Column(Text, nullable=True)  # 文本内容
    message_type = Column(String(50), nullable=False, default="text")  # text/file/link/clipboard/image
    file_id = Column(UUID(as_uuid=True), ForeignKey("cross_share_files.id"), nullable=True)
    is_encrypted = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<CrossMessage(id={self.id}, type={self.message_type}, user_id={self.user_id})>"


class CrossFile(Base):
    """跨设备文件表"""

    __tablename__ = "cross_share_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), nullable=False, index=True)
    upload_device_id = Column(UUID(as_uuid=True), ForeignKey("cross_share_devices.id"), nullable=True)
    oss_bucket = Column(String(200), nullable=False)
    oss_key = Column(String(500), nullable=False)
    oss_url = Column(String(1000), nullable=True)
    file_name = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)  # image/document/video/audio/archive/other
    file_hash = Column(String(100), nullable=True, index=True)  # 用于去重
    download_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<CrossFile(id={self.id}, name={self.file_name}, user_id={self.user_id})>"


class CrossShareConfig(Base):
    """用户配置表"""

    __tablename__ = "cross_share_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    max_file_size = Column(BigInteger, default=104857600)  # 100MB
    storage_quota = Column(BigInteger, default=5368709120)  # 5GB
    file_expire_days = Column(Integer, default=30)
    enable_encryption = Column(Boolean, default=False)
    enable_clipboard = Column(Boolean, default=True)
    allowed_file_types = Column(Text, nullable=True)  # JSON 格式存储
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<CrossShareConfig(id={self.id}, user_id={self.user_id})>"
