"""Harness Phase 1 ORM 模型

参考 spec: docs/superpowers/specs/2026-08-28-agent-harness-design.md §5
包含 6 张新表：Tool / ToolBinding / SessionCheckpoint / AgentMemory / Trace / TraceStep

注：为避免与 app.models.tool_models.Tool（Pydantic schema）命名冲突，
本模块的 ORM Tool 在 app/models/__init__.py 中以别名 `HarnessTool` 导出。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Tool(Base):
    """工具注册表

    参考 spec §5.3
    """

    __tablename__ = "tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)  # builtin / http / mcp / plugin
    config = Column(JSONB, nullable=False, default=dict)
    parameters_schema = Column(JSONB, nullable=False, default=dict)
    returns_schema = Column(JSONB, nullable=True)
    is_available_condition = Column(JSONB, default=dict)
    rate_limit_per_minute = Column(Integer, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    bindings = relationship(
        "ToolBinding", back_populates="tool", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        """初始化时填充 Python 级默认值，使属性在 flush 前即可读。"""
        # JSON/dict 字段使用 copy 避免实例间共享同一引用
        import copy

        _defaults = {
            "config": {},
            "parameters_schema": {},
            "is_available_condition": {},
            "metadata_": {},
            "is_active": True,
        }
        for key, value in _defaults.items():
            kwargs.setdefault(key, copy.copy(value))
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Tool {self.name} type={self.type}>"


class ToolBinding(Base):
    """Agent ↔ Tool 绑定

    参考 spec §5.4
    """

    __tablename__ = "agent_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_overrides = Column(JSONB, default=dict)
    priority = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系（back_populates 对应 Agent.tool_bindings）
    tool = relationship("Tool", back_populates="bindings")
    agent = relationship("Agent", back_populates="tool_bindings")

    __table_args__ = (
        UniqueConstraint("agent_id", "tool_id", name="uq_agent_tools_agent_tool"),
        Index("ix_agent_tools_agent_id", "agent_id"),
    )


class SessionCheckpoint(Base):
    """会话 checkpoint（完整快照版）

    Phase 1：轻量（仅 messages_ref + agent_state）
    Phase 3-Plan-1D：扩展为完整快照 + DAG 分支
    参考 spec §5.7 + Phase 3-Plan-1D-design §4
    """

    __tablename__ = "session_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_index = Column(Integer, nullable=False)
    phase = Column(
        String(20), nullable=False
    )  # after_user_message / before_tool / after_tool / branch_point / merge_commit
    messages_ref = Column(UUID(as_uuid=True), nullable=True)  # Phase 1 兼容字段
    agent_state = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # === Phase 3-Plan-1D 新增字段 ===
    branch_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    parent_checkpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_checkpoints.id", ondelete="SET NULL"),
        nullable=True,
    )
    messages_snapshot = Column(JSONB, nullable=False, default=list)
    checkpoint_kind = Column(String(20), nullable=False, default="auto")
    # auto / manual / branch_point / merge_commit
    label = Column(String(100), nullable=True)
    merge_parents = Column(JSONB, nullable=True)  # 多父合并时存 [cp_id1, cp_id2]
    is_head = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_checkpoints_conv_step", "conversation_id", "step_index"),
        Index("ix_checkpoints_branch", "branch_id"),
    )

    def __init__(self, **kwargs):
        import copy

        _defaults = {
            "messages_snapshot": [],
            "agent_state": {},
            "checkpoint_kind": "auto",
            "is_head": False,
        }
        for key, value in _defaults.items():
            kwargs.setdefault(key, copy.copy(value) if isinstance(value, (dict, list)) else value)
        if "branch_id" not in kwargs:
            kwargs["branch_id"] = uuid.uuid4()
        super().__init__(**kwargs)


class Branch(Base):
    """会话分支（DAG 中的链）

    参考 Phase 3-Plan-1D-design §4.2
    """

    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    parent_branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id"),
        nullable=True,
    )
    head_checkpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_checkpoints.id"),
        nullable=True,
    )
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_branches_conv", "conversation_id"),
    )

    def __repr__(self):
        return f"<Branch(id={self.id}, name={self.name}, archived={self.is_archived})>"


class AgentMemory(Base):
    """Agent 长期记忆

    参考 spec §5.8
    """

    __tablename__ = "agent_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), nullable=True)
    scope = Column(String(20), default="agent_user")  # agent / user / agent_user
    key = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    source_conversation_id = Column(UUID(as_uuid=True), nullable=True)
    source_message_id = Column(UUID(as_uuid=True), nullable=True)
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_memories_agent_user_scope", "agent_id", "user_id", "scope"),
    )


class Trace(Base):
    """Agent turn 追踪记录（顶层）

    参考 spec §5.9
    """

    __tablename__ = "agent_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    agent_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    input_text = Column(Text, nullable=False)
    output_text = Column(Text, nullable=True)
    status = Column(
        String(20), nullable=False
    )  # success / error / timeout / guardrail_blocked / handoff
    total_steps = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    steps = relationship(
        "TraceStep",
        back_populates="trace",
        cascade="all, delete-orphan",
        order_by="TraceStep.step_index",
    )

    __table_args__ = (
        Index("ix_traces_agent_started", "agent_id", "started_at"),
        Index("ix_traces_user_started", "user_id", "started_at"),
    )


class TraceStep(Base):
    """Trace 子步骤

    参考 spec §5.9
    """

    __tablename__ = "trace_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_traces.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_index = Column(Integer, nullable=False)
    step_type = Column(
        String(20), nullable=False
    )  # llm_call / tool_call / handoff / guardrail / memory_read / memory_write
    tool_name = Column(String(100), nullable=True)
    llm_model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    trace = relationship("Trace", back_populates="steps")

    __table_args__ = (
        Index("ix_trace_steps_trace_id", "trace_id"),
    )
