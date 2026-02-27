"""
PRD文档模型
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class PRDDocument(Base):
    """PRD文档表"""

    __tablename__ = "prd_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), default="draft")  # 'draft', 'confirmed', 'archived'
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # 同一会话的版本号唯一
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<PRDDocument(id={self.id}, version={self.version_number}, status={self.status})>"
