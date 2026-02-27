"""
消息模型
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
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
    llm_config_id = Column(
        UUID(as_uuid=True), ForeignKey("llm_configs.id"), nullable=True
    )  # 使用的模型配置
    llm_model_name = Column(String(100), nullable=True)  # 使用的模型名称

    def __repr__(self):
        return f"<Message(id={self.id}, sender={self.sender_type}, type={self.message_type})>"
