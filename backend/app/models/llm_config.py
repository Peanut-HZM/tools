"""
LLM配置模型
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class LLMConfig(Base):
    """大模型配置表"""

    __tablename__ = "llm_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    provider_type = Column(
        String(50), nullable=False
    )  # 'openai', 'anthropic', 'azure_openai', 'baidu', 'aliyun', 'other'
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)  # 加密的API Key
    model_name = Column(String(100), nullable=False)
    request_params = Column(JSON, nullable=True)  # {temperature, max_tokens, timeout}
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<LLMConfig(id={self.id}, name={self.name}, provider={self.provider_type})>"
