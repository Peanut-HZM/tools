"""
会话模型
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class Conversation(Base):
    """会话表"""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 注意：users 表通过 raw SQL 创建，不在 SQLAlchemy metadata 中
    # 因此移除外键约束，在应用层进行验证
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    current_stage = Column(
        String(50), default="requirement_clarification", nullable=False
    )
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, stage={self.current_stage})>"
