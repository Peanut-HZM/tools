"""
大模型 model（spec §16.3）

从 v1 起承担原 llm_configs 表中「具体模型」维度的数据。
每个 LLMModel 必须归属于一个 LLMProvider（provider_id 外键）。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class LLMModel(Base):
    """大模型表"""

    __tablename__ = "llm_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 可读名称，通常沿用旧 llm_configs.name
    name = Column(String(100), nullable=False)
    # 模型标识，例如 "gpt-4o"、"claude-3-5-sonnet-20241022"
    model_name = Column(String(100), nullable=False)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("llm_providers.id"),
        nullable=False,
        index=True,
    )
    # JSON 字符串形式的请求参数（temperature / max_tokens / timeout 等）
    # 注意：旧 llm_configs.request_params 为 JSON 类型，迁移时需 json.dumps
    request_params = Column(Text, nullable=True)
    # text / vision / image_gen / voice / embedding / ocr
    category = Column(String(20), nullable=False, default="text", index=True)
    # 全局默认模型（下拉框首选）
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    # 所属分类下的默认模型
    is_default_for_category = Column(Boolean, nullable=False, default=False)
    # 兜底链迭代顺序，越小越优先；同 priority 内按 id 稳定排序
    priority = Column(Integer, default=100, nullable=False, index=False)
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

    # 关联供应商，joined 加载避免 N+1
    provider = relationship("LLMProvider", lazy="joined")

    def __repr__(self):
        return (
            f"<LLMModel(id={self.id}, name={self.name}, "
            f"model={self.model_name})>"
        )
