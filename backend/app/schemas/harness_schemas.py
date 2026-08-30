"""Harness Phase 1 Pydantic schemas

参考 spec §8
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenerationParams(BaseModel):
    """LLM 生成参数白名单（仅允许以下 6 个标准参数 + 范围校验）

    Task 14 fix round 2: 替代原先的 Dict[str, Any]，
    防止攻击者通过 generation_params 传入 system_prompt / tool_choice 等
    harness runtime 内置字段。
    """

    model_config = ConfigDict(extra="forbid")

    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)


class ToolCreate(BaseModel):
    """创建工具请求体"""

    name: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=100)
    description: str
    type: str = Field(..., pattern="^(builtin|http|mcp|plugin)$")
    config: Dict[str, Any] = Field(default_factory=dict)
    parameters_schema: Dict[str, Any]
    returns_schema: Optional[Dict[str, Any]] = None
    is_available_condition: Dict[str, Any] = Field(default_factory=dict)
    rate_limit_per_minute: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="metadata")


class ToolUpdate(BaseModel):
    """更新工具请求体"""

    display_name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    returns_schema: Optional[Dict[str, Any]] = None
    is_available_condition: Optional[Dict[str, Any]] = None
    rate_limit_per_minute: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    is_active: Optional[bool] = None


class ToolView(BaseModel):
    """工具视图（响应体）"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    description: str
    type: str
    config: Dict[str, Any]
    parameters_schema: Dict[str, Any]
    returns_schema: Optional[Dict[str, Any]]
    is_available_condition: Dict[str, Any]
    rate_limit_per_minute: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ToolListView(BaseModel):
    """工具列表响应体"""

    items: List[ToolView]
    total: int


# ---------------------------------------------------------------------------
# Task 14: admin/agents harness 扩展
# ---------------------------------------------------------------------------

def _validate_guardrail_entry(entry: Any) -> None:
    """P3-⑩: 校验单条 guardrail 条目形状。

    - 必须为 dict 且含 name
    - tool_id 条目放行（工具型，运行时解析）
    - type 条目校验 config 形状（keyword/regex/max_length）
    - 两者都缺 → ValueError（Pydantic 转 422）
    """
    import re as _re

    if not isinstance(entry, dict) or not str(entry.get("name") or "").strip():
        raise ValueError("guardrail 条目必须为含 name 的对象")
    if "tool_id" in entry:
        return
    rule_type = entry.get("type")
    config = entry.get("config") or {}
    if rule_type == "keyword":
        keywords = config.get("keywords")
        if not isinstance(keywords, list) or not keywords or not all(
            isinstance(k, str) and k for k in keywords
        ):
            raise ValueError("keyword 规则需要非空字符串数组 keywords")
    elif rule_type == "regex":
        pattern = config.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("regex 规则需要非空 pattern")
        try:
            _re.compile(pattern)
        except _re.error:
            raise ValueError(f"非法正则: {pattern[:50]}")
    elif rule_type == "max_length":
        max_chars = config.get("max_chars")
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
            raise ValueError("max_length 规则需要正整数 max_chars")
    else:
        raise ValueError(f"未知 guardrail 类型: {rule_type}")


class AgentHarnessUpdate(BaseModel):
    """更新 agent harness 扩展字段（全部 optional，仅更新传入字段）"""

    slug: Optional[str] = Field(None, max_length=50)
    welcome_message: Optional[str] = None
    default_model_id: Optional[str] = None
    fallback_model_ids: Optional[List[str]] = None
    generation_params: Optional[GenerationParams] = None
    memory_short_term_policy: Optional[str] = Field(None, max_length=20)
    memory_short_term_window: Optional[int] = None
    memory_long_term_enabled: Optional[bool] = None
    memory_long_term_config: Optional[Dict[str, Any]] = None
    max_steps_per_turn: Optional[int] = None
    tool_timeout_seconds: Optional[int] = None
    error_strategy: Optional[str] = Field(None, max_length=20)
    max_retries: Optional[int] = None
    can_handoff_to: Optional[List[str]] = None
    handoff_instruction: Optional[str] = None
    input_guardrails: Optional[List[Dict[str, Any]]] = None
    output_guardrails: Optional[List[Dict[str, Any]]] = None
    guardrail_on_violation: Optional[str] = Field(None, max_length=20)
    visibility: Optional[str] = Field(None, max_length=20)
    owner_id: Optional[str] = None

    @field_validator("input_guardrails", "output_guardrails")
    @classmethod
    def _check_guardrails(cls, v):
        """P3-⑩: 校验 guardrail 条目形状（内置规则/工具条目二选一）"""
        if v is None:
            return v
        for entry in v:
            _validate_guardrail_entry(entry)
        return v


class AgentHarnessView(BaseModel):
    """Agent harness 扩展字段视图"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    icon: str
    icon_color: str
    category: str
    is_active: bool
    slug: Optional[str]
    welcome_message: Optional[str]
    default_model_id: Optional[str]
    fallback_model_ids: List[Any]
    generation_params: Dict[str, Any]
    memory_short_term_policy: Optional[str]
    memory_short_term_window: Optional[int]
    memory_long_term_enabled: bool
    memory_long_term_config: Dict[str, Any]
    max_steps_per_turn: Optional[int]
    tool_timeout_seconds: Optional[int]
    error_strategy: Optional[str]
    max_retries: Optional[int]
    can_handoff_to: List[Any]
    handoff_instruction: Optional[str]
    input_guardrails: List[Any]
    output_guardrails: List[Any]
    guardrail_on_violation: Optional[str]
    visibility: Optional[str]
    owner_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class ToolBindingCreate(BaseModel):
    """创建工具绑定请求体"""

    tool_id: str
    parameter_overrides: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    is_enabled: bool = True


class ToolBindingView(BaseModel):
    """工具绑定视图"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    tool_id: str
    tool_name: Optional[str] = None
    tool_display_name: Optional[str] = None
    parameter_overrides: Dict[str, Any]
    priority: int
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]


class AgentHarnessStatsView(BaseModel):
    """单 agent harness 使用统计"""

    agent_id: str
    conversation_count: int = 0
    message_count: int = 0
    trace_count: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    tool_usage: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Task 15: admin/traces observability schemas
# ---------------------------------------------------------------------------

class TraceSummaryView(BaseModel):
    """Trace 列表条目（不含 input/output 全文与 steps）"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    agent_id: str
    user_id: str
    status: str
    total_steps: int
    total_tokens: int
    total_duration_ms: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TraceStepView(BaseModel):
    """Trace 子步骤视图"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    step_index: int
    step_type: str
    tool_name: Optional[str] = None
    llm_model: Optional[str] = None
    tokens_used: int
    duration_ms: int
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_message: Optional[str] = None


class TraceDetailView(TraceSummaryView):
    """Trace 详情（含 input/output 全文与 steps）

    继承 TraceSummaryView 共享基础字段，扩展 input/output 与步骤列表。
    """

    input_text: str
    output_text: Optional[str] = None
    error_message: Optional[str] = None
    steps: List[TraceStepView] = []


class TraceListView(BaseModel):
    """Trace 列表响应体"""

    items: List[TraceSummaryView]
    total: int
