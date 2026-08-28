"""
消息模型

Harness Phase 1: 新增 tool_calls / tool_call_id / tool_name / attachments，
支持 LLM 工具调用消息与附件。详见 spec §5.6。
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from .base import Base


class Message(Base):
    """消息表"""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type = Column(String(20), nullable=False)  # 'user' 或 'agent'
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # 'text', 'structured', 'chart'
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Token消耗统计（仅AI消息）
    prompt_tokens = Column(Integer, default=0)  # 输入token数
    completion_tokens = Column(Integer, default=0)  # 输出token数
    total_tokens = Column(Integer, default=0)  # 总token数
    # 历史原因列名保留，实际存储 LLMModel.id（v1 起已迁移到 llm_models 表）。
    # 移除原 ForeignKey("llm_configs.id") 约束：旧 llm_configs 表仅保留用于回滚过渡，
    # 新写入的 ID 指向 llm_models.id，不再受 FK 约束；项目使用 create_all 不做 schema migration，
    # 数据库层面若已存在旧 FK 约束需 DBA 手动 DROP，ORM 层面已解除。
    llm_config_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    llm_model_name = Column(String(100), nullable=True)  # 使用的模型名称

    # === Harness Phase 1 新增字段（工具调用 & 附件） ===
    tool_calls = Column(JSONB, nullable=True)  # LLM 工具调用请求列表
    tool_call_id = Column(String(100), nullable=True)  # 工具调用结果关联 ID
    tool_name = Column(String(100), nullable=True)  # 工具名称（结果消息）
    attachments = Column(JSONB, default=list)  # 附件列表

    def __repr__(self):
        return f"<Message(id={self.id}, sender={self.sender_type}, type={self.message_type})>"
