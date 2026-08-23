"""图像生成工具 - SQLAlchemy 模型"""
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON, func,
)

from app.models.base import Base


def gen_uuid() -> str:
    """生成 UUID 字符串主键"""
    return str(uuid.uuid4())


class ImageGenQuota(Base):
    """配额表"""
    __tablename__ = "image_gen_quota"

    user_id = Column(String(64), primary_key=True)
    daily_limit = Column(Integer, nullable=False)
    monthly_limit = Column(Integer, nullable=False)
    daily_used = Column(Integer, nullable=False, default=0)
    monthly_used = Column(Integer, nullable=False, default=0)
    daily_reset_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    monthly_reset_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    granted_by = Column(String(64), nullable=True)
    notes = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ImageGenHistory(Base):
    """历史表"""
    __tablename__ = "image_gen_history"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    operation = Column(String(32), nullable=False)
    prompt = Column(Text, nullable=True)
    params = Column(JSON, nullable=True)
    reference_oss_key = Column(String(512), nullable=True)
    mask_oss_key = Column(String(512), nullable=True)
    result_oss_key = Column(String(512), nullable=False)
    result_width = Column(Integer, nullable=True)
    result_height = Column(Integer, nullable=True)
    model_used = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False)
    backend = Column(String(16), default="dify", nullable=False, index=True)
    """生成后端：'dify' | 'selfdev'"""
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    conversation_id = Column(String(64), nullable=True, index=True)  # 关联多轮对话 ID
    last_accessed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class ImageGenDifyConfig(Base):
    """Dify 配置表（key-value，value 加密）"""
    __tablename__ = "image_gen_dify_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), nullable=False, unique=True)
    value_encrypted = Column(String(4096), nullable=False)  # 加密后的字符串
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ImageGenDegradationConfig(Base):
    """降级配置表"""
    __tablename__ = "image_gen_degradation_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, nullable=False, default=True)
    failure_threshold = Column(Integer, nullable=False, default=3)
    degrade_duration_seconds = Column(Integer, nullable=False, default=300)
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ImageGenRetentionConfig(Base):
    """OSS 保留策略配置表"""
    __tablename__ = "image_gen_retention_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(String(64), nullable=False, default="keep_forever")
    n_days = Column(Integer, nullable=False, default=30)
    cleanup_cron = Column(String(32), nullable=False, default="0 3 * * *")
    enabled = Column(Boolean, nullable=False, default=True)
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
