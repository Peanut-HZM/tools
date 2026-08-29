"""
会话模型

Harness Phase 1: 新增 agent_id（绑定到 Agent）与 metadata 扩展字段。
详见 spec §5.5。
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
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

    # === Harness Phase 1 新增字段 ===
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_ = Column("metadata", JSONB, default=dict)

    # === Checkpoint 时间旅行（Phase 3-Plan-1D）新增字段 ===
    head_checkpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_checkpoints.id", ondelete="SET NULL"),
        nullable=True,
    )
    main_branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, stage={self.current_stage})>"
