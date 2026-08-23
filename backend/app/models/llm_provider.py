"""
大模型供应商 model（spec §16.3）

从 v1 起承担原 llm_configs 表中「供应商 / API Key」维度的数据。
一个 LLMProvider 代表一组共享同一把 API Key（+ 同一 base_url）的模型配置。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


class LLMProvider(Base):
    """大模型供应商表"""

    __tablename__ = "llm_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 可读名称，例如 "OpenAI-peanut-1234" 或 "Migrated: openai-1234"
    name = Column(String(100), nullable=False)
    # openai / anthropic / azure_openai / baidu / aliyun / doubao_seedream / qwen_image / other
    provider_type = Column(String(50), nullable=False)
    base_url = Column(String(500), nullable=False)
    # 加密后的 API Key（AES-256-GCM），与原 llm_configs.api_key_encrypted 同格式
    api_key_encrypted = Column(Text, nullable=False)
    # API Key 最后 4 位，仅用于人工识别
    api_key_suffix = Column(String(4), nullable=True)
    # 明文 API Key 的 SHA-256 摘要，用于幂等检索 / 去重
    # AES-GCM 每次加密 IV 随机，密文不幂等，因此需要单独存 hash
    api_key_hash = Column(
        LargeBinary(32),
        nullable=True,
        index=True,
        unique=True,
        comment="SHA256 of plaintext api_key, for idempotent lookup",
    )
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    def __repr__(self):
        return (
            f"<LLMProvider(id={self.id}, name={self.name}, "
            f"type={self.provider_type})>"
        )
