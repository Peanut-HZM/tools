"""
竞品分析模型
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class CompetitorAnalysis(Base):
    """竞品分析表"""

    __tablename__ = "competitor_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    competitors = Column(
        JSON, nullable=False
    )  # 竞品列表 [{name, features, pros, cons, opportunity}]
    differentiation_suggestions = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<CompetitorAnalysis(id={self.id})>"
