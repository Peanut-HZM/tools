"""Agent 程序性记忆（技能）ORM 模型

P2-② Memory procedural
技能 = Agent 沉淀的命名操作流程（怎么做事），区别于长期记忆的事实 KV。
(agent_id, user_id, name) 唯一。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class AgentProceduralMemory(Base):
    """Agent 程序性记忆（技能）"""

    __tablename__ = "agent_procedural_memory"
    __table_args__ = (
        UniqueConstraint("agent_id", "user_id", "name", name="uq_procedural_agent_user_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    # user_id 暂不加 FK：与 agent_memory_long_term 同构（users.id 为 String 类型不匹配）
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    trigger = Column(Text, nullable=False)   # 何时使用（进索引供 LLM 判断）
    content = Column(Text, nullable=False)   # 完整步骤/规则（skill_read 返回）
    importance = Column(Float, nullable=False, default=0.5, server_default="0.5")
    use_count = Column(Integer, nullable=False, default=0, server_default="0")
    is_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self):
        return f"<AgentProceduralMemory {self.name} agent={self.agent_id}>"
