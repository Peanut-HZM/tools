"""
LLM 配置 model - DEPRECATED

v1 起请使用 LLMProvider + LLMModel（见 backend/app/models/llm_provider.py 和 llm_model.py）。
保留本表仅用于回滚过渡，新业务逻辑不应再读写 llm_configs。
"""

from enum import Enum
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class LLMConfigCategory(str, Enum):
    """大模型配置分类枚举"""

    CHAT = "chat"  # 对话类型
    CODE = "code"  # 编程类型


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
    api_key_suffix = Column(String(4), nullable=True)  # API Key 最后4位，方便识别
    model_name = Column(String(100), nullable=False)
    request_params = Column(JSON, nullable=True)  # {temperature, max_tokens, timeout}
    category = Column(
        String(20), default=LLMConfigCategory.CHAT.value, nullable=False
    )  # chat: 对话类型, code: 编程类型
    notes = Column(String(500), nullable=True)  # 备注
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
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
        return f"<LLMConfig(id={self.id}, name={self.name}, provider={self.provider_type})>"
