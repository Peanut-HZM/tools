"""
Agent模型
用于存储AI Agent配置

Harness Phase 1: 扩展 20+ 新字段（均为 nullable / 有默认值，零破坏）。
详见 spec §5.2。
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class Agent(Base):
    """Agent配置表"""

    __tablename__ = "agents"

    # === 原有字段（保持不变） ===
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # Agent名称
    description = Column(Text, nullable=False)  # Agent描述
    system_prompt = Column(Text, nullable=False)  # 系统提示词
    icon = Column(String(50), default="fa-robot")  # 图标
    icon_color = Column(String(100), default="bg-blue-500")  # 图标颜色
    category = Column(String(50), default="AI工具")  # 分类
    is_active = Column(Boolean, default=True)  # 是否启用
    is_default = Column(Boolean, default=False)  # 是否为默认Agent
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # === Harness Phase 1 新增字段（全部 nullable / 有默认值） ===
    slug = Column(String(50), nullable=True, unique=True)  # URL 友好标识
    welcome_message = Column(Text, nullable=True)  # 首条欢迎消息
    default_model_id = Column(UUID(as_uuid=True), nullable=True)  # 默认 LLM 模型
    fallback_model_ids = Column(JSONB, default=list)  # 备选模型 ID 列表
    generation_params = Column(JSONB, default=dict)  # 生成参数（temperature 等）

    # 短期记忆策略
    memory_short_term_policy = Column(String(20), default="sliding_window")
    memory_short_term_window = Column(Integer, default=20)

    # 长期记忆
    memory_long_term_enabled = Column(Boolean, default=False)
    memory_long_term_config = Column(JSONB, default=dict)

    # P2-②: 程序性记忆（技能系统）开关
    memory_procedural_enabled = Column(Boolean, default=False)

    # 运行约束
    max_steps_per_turn = Column(Integer, default=20)
    tool_timeout_seconds = Column(Integer, default=60)
    error_strategy = Column(String(20), default="fallback_message")
    max_retries = Column(Integer, default=2)

    # Handoff
    can_handoff_to = Column(JSONB, default=list)  # 存 slug 列表
    handoff_instruction = Column(Text, nullable=True)

    # Guardrails
    input_guardrails = Column(JSONB, default=list)
    output_guardrails = Column(JSONB, default=list)
    guardrail_on_violation = Column(String(20), default="block")

    # 可见性 / 归属
    visibility = Column(String(20), default="public")
    owner_id = Column(UUID(as_uuid=True), nullable=True)

    # === 关系 ===
    tool_bindings = relationship(
        "ToolBinding", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, category={self.category})>"
