"""Agent 评估 Run / Case ORM 模型

P3-⑨ Agent 评估框架
run = 一次评测批次；case = 单条评测用例（输入/期望/实际输出/judge 打分）。
agent_id / user_id 为逻辑关联（不加 FK，与 agent_traces 同构）。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class AgentEvalRun(Base):
    """评估批次"""

    __tablename__ = "agent_eval_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(200), nullable=False)
    # pending / running / completed / failed
    status = Column(String(20), nullable=False, default="pending")
    total_cases = Column(Integer, nullable=False, default=0)
    passed_cases = Column(Integer, nullable=False, default=0)
    avg_score = Column(Float, nullable=False, default=0.0)
    total_duration_ms = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<AgentEvalRun {self.name} status={self.status}>"


class AgentEvalCase(Base):
    """评估用例结果"""

    __tablename__ = "agent_eval_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input = Column(Text, nullable=False)
    expected = Column(Text, nullable=False)
    actual_output = Column(Text, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    judge_reasoning = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    # pending / success / error
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<AgentEvalCase run={self.run_id} score={self.score}>"
