"""
Agent 长期记忆 ORM 模型

Phase 2 Plan-2 / Task 1
参考 spec §6.2: docs/superpowers/specs/2026-08-29-agent-harness-phase2-design.md

简单 key-value 存储，每个 (agent_id, user_id, key) 唯一一条。
Phase 3 才会扩展到 pgvector 向量检索。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class AgentMemoryLongTerm(Base):
    """Agent 长期记忆（key-value 存储）

    设计要点：
    - (agent_id, user_id, key) 唯一约束
    - value 为 JSONB，存任意结构化内容
    - summary 为可选纯文本摘要，便于快速检索/展示
    - created_at / updated_at 由 DB 默认值维护
    """

    __tablename__ = "agent_memory_long_term"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    # user_id 暂不加 FK：users.id 为 String(64) 与 UUID 类型不匹配
    # Phase 1 agent_memories 表同样未加 FK，保持一致
    user_id = Column(UUID(as_uuid=True), nullable=False)
    key = Column(String(200), nullable=False)
    value = Column(JSONB, nullable=False, default=dict)
    summary = Column(Text, nullable=True)
    # Phase 3 Plan-1B: 向量检索相关列
    importance = Column(Float, nullable=False, default=0.5, server_default="0.5")
    access_count = Column(Integer, nullable=False, default=0, server_default="0")
    # embedding 使用 Text 类型，应用层做 list[float] ↔ string 转换
    embedding = Column(Text, nullable=True)  # 存储为字符串 "[0.1, 0.2, ...]"
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "agent_id", "user_id", "key", name="uq_agent_memory_long_term_key"
        ),
        Index("ix_memory_agent_user", "agent_id", "user_id"),
    )

    def __repr__(self):
        return (
            f"<AgentMemoryLongTerm(agent_id={self.agent_id}, "
            f"user_id={self.user_id}, key={self.key!r})>"
        )