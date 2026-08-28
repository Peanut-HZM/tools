"""
Agent管理路由
用于管理AI Agent配置
"""
import logging
import uuid as _uuid_mod
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.harness_models import Tool, ToolBinding, Trace, TraceStep
from app.models.message import Message
from app.schemas.harness_schemas import (
    AgentHarnessStatsView,
    AgentHarnessUpdate,
    AgentHarnessView,
    ToolBindingCreate,
    ToolBindingView,
)
from app.services.agent_management_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/agents", tags=["admin-agents"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)
    icon: str = Field(default="fa-robot")
    icon_color: str = Field(default="bg-blue-500")
    category: str = Field(default="AI工具")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    icon: Optional[str] = None
    icon_color: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    icon: str
    icon_color: str
    category: str
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: Optional[str] = None


class AgentStats(BaseModel):
    total: int
    active: int
    inactive: int


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """获取Agent列表（管理员）"""
    service = AgentService(db)
    agents = service.list_agents(skip=skip, limit=limit, is_active=is_active)

    return [
        {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "icon": agent.icon,
            "icon_color": agent.icon_color,
            "category": agent.category,
            "is_active": agent.is_active,
            "is_default": agent.is_default,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        }
        for agent in agents
    ]


@router.post("", response_model=AgentResponse)
async def create_agent(
    data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """创建Agent（管理员）"""
    service = AgentService(db)
    agent = service.create_agent(
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        icon=data.icon,
        icon_color=data.icon_color,
        category=data.category,
    )

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """获取Agent详情（管理员）"""
    service = AgentService(db)
    agent = service.get_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """更新Agent（管理员）"""
    service = AgentService(db)

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    agent = service.update_agent(agent_id, **update_data)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """删除Agent（管理员）"""
    service = AgentService(db)
    success = service.delete_agent(agent_id)

    if not success:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {"message": "Agent已删除"}


@router.post("/{agent_id}/default", response_model=AgentResponse)
async def set_default_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """设置默认Agent（管理员）"""
    service = AgentService(db)
    agent = service.set_default_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/stats/overview", response_model=AgentStats)
async def get_agent_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """获取Agent统计（管理员）"""
    service = AgentService(db)
    stats = service.get_agent_stats()
    return stats


# ===========================================================================
# Task 14: admin/agents harness 扩展端点
# ===========================================================================

# Harness 字段可更新白名单（防止 mass assignment）
_HARNESS_UPDATABLE_FIELDS = frozenset({
    "slug", "welcome_message", "default_model_id", "fallback_model_ids",
    "generation_params", "memory_short_term_policy", "memory_short_term_window",
    "memory_long_term_enabled", "memory_long_term_config", "max_steps_per_turn",
    "tool_timeout_seconds", "error_strategy", "max_retries", "can_handoff_to",
    "handoff_instruction", "input_guardrails", "output_guardrails",
    "guardrail_on_violation", "visibility", "owner_id",
})


def _agent_to_harness_view(agent) -> dict:
    """将 Agent ORM 对象转为 AgentHarnessView dict"""
    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "slug": agent.slug,
        "welcome_message": agent.welcome_message,
        "default_model_id": str(agent.default_model_id) if agent.default_model_id else None,
        "fallback_model_ids": agent.fallback_model_ids or [],
        "generation_params": agent.generation_params or {},
        "memory_short_term_policy": agent.memory_short_term_policy,
        "memory_short_term_window": agent.memory_short_term_window,
        "memory_long_term_enabled": agent.memory_long_term_enabled,
        "memory_long_term_config": agent.memory_long_term_config or {},
        "max_steps_per_turn": agent.max_steps_per_turn,
        "tool_timeout_seconds": agent.tool_timeout_seconds,
        "error_strategy": agent.error_strategy,
        "max_retries": agent.max_retries,
        "can_handoff_to": agent.can_handoff_to or [],
        "handoff_instruction": agent.handoff_instruction,
        "input_guardrails": agent.input_guardrails or [],
        "output_guardrails": agent.output_guardrails or [],
        "guardrail_on_violation": agent.guardrail_on_violation,
        "visibility": agent.visibility,
        "owner_id": str(agent.owner_id) if agent.owner_id else None,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }


def _binding_to_view(binding) -> dict:
    """将 ToolBinding ORM 对象转为 ToolBindingView dict"""
    tool_name = None
    tool_display_name = None
    if binding.tool:
        tool_name = binding.tool.name
        tool_display_name = binding.tool.display_name
    return {
        "id": str(binding.id),
        "agent_id": str(binding.agent_id),
        "tool_id": str(binding.tool_id),
        "tool_name": tool_name,
        "tool_display_name": tool_display_name,
        "parameter_overrides": binding.parameter_overrides or {},
        "priority": binding.priority,
        "is_enabled": binding.is_enabled,
        "created_at": binding.created_at,
        "updated_at": binding.updated_at,
    }


@router.post("/{agent_id}/harness", response_model=AgentHarnessView)
async def update_agent_harness(
    agent_id: str,
    payload: AgentHarnessUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """更新 agent 的 harness 扩展字段（白名单更新）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    # 白名单更新：仅允许更新 _HARNESS_UPDATABLE_FIELDS 中的字段
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in _HARNESS_UPDATABLE_FIELDS:
            # UUID 字符串字段转为 UUID 对象（若 ORM 列为 UUID 类型）
            if key in ("default_model_id", "owner_id") and value is not None:
                try:
                    value = _uuid_mod.UUID(str(value))
                except (ValueError, AttributeError):
                    raise HTTPException(
                        status_code=400, detail=f"invalid uuid for {key}"
                    )
            setattr(agent, key, value)

    db.commit()
    db.refresh(agent)
    logger.info(f"Agent harness updated: {agent.name} (id={agent.id})")
    return _agent_to_harness_view(agent)


@router.get("/{agent_id}/harness", response_model=AgentHarnessView)
async def get_agent_harness(
    agent_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """获取 agent 的 harness 扩展字段"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")
    return _agent_to_harness_view(agent)


@router.get("/{agent_id}/tools", response_model=list[ToolBindingView])
async def list_agent_tool_bindings(
    agent_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """列出 agent 的工具绑定"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    bindings = (
        db.query(ToolBinding)
        .filter(ToolBinding.agent_id == agent_id)
        .order_by(ToolBinding.priority.desc())
        .all()
    )
    return [_binding_to_view(b) for b in bindings]


@router.post("/{agent_id}/tools", response_model=ToolBindingView, status_code=201)
async def create_agent_tool_binding(
    agent_id: str,
    payload: ToolBindingCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """为 agent 添加工具绑定（agent_id + tool_id 唯一性校验）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    # 校验工具存在
    tool = db.query(Tool).filter(Tool.id == payload.tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool不存在")

    # 唯一性校验：agent_id + tool_id 不得重复
    existing = (
        db.query(ToolBinding)
        .filter(ToolBinding.agent_id == agent_id)
        .filter(ToolBinding.tool_id == payload.tool_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"工具绑定已存在 (agent={agent_id}, tool={payload.tool_id})",
        )

    binding = ToolBinding(
        agent_id=agent_id,
        tool_id=payload.tool_id,
        parameter_overrides=payload.parameter_overrides,
        priority=payload.priority,
        is_enabled=payload.is_enabled,
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    logger.info(
        f"Tool binding created: agent={agent_id}, tool={payload.tool_id}, id={binding.id}"
    )
    return _binding_to_view(binding)


@router.delete("/{agent_id}/tools/{binding_id}")
async def delete_agent_tool_binding(
    agent_id: str,
    binding_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """删除工具绑定"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    binding = (
        db.query(ToolBinding)
        .filter(ToolBinding.id == binding_id)
        .filter(ToolBinding.agent_id == agent_id)
        .first()
    )
    if not binding:
        raise HTTPException(status_code=404, detail="工具绑定不存在")

    db.delete(binding)
    db.commit()
    logger.info(f"Tool binding deleted: {binding_id}")
    return {"message": "工具绑定已删除"}


@router.get("/{agent_id}/harness-stats", response_model=AgentHarnessStatsView)
async def get_agent_harness_stats(
    agent_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """单 agent harness 使用统计（对话数、消息数、trace 统计、工具使用频率）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    # 对话数
    conversation_count = (
        db.query(Conversation).filter(Conversation.agent_id == agent_id).count()
    )
    # 消息数（通过 conversation 关联统计）
    conv_ids = [
        r[0] for r in
        db.query(Conversation.id).filter(Conversation.agent_id == agent_id).all()
    ]
    message_count = 0
    if conv_ids:
        message_count = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conv_ids))
            .count()
        )
    # Trace 统计
    trace_count = db.query(Trace).filter(Trace.agent_id == agent_id).count()
    total_tokens = (
        db.query(sa_func.sum(Trace.total_tokens))
        .filter(Trace.agent_id == agent_id)
        .scalar()
    ) or 0
    total_duration_ms = (
        db.query(sa_func.sum(Trace.total_duration_ms))
        .filter(Trace.agent_id == agent_id)
        .scalar()
    ) or 0
    # 工具使用频率（按 tool_name 分组）
    tool_usage_rows = (
        db.query(TraceStep.tool_name, sa_func.count(TraceStep.tool_name))
        .join(Trace, Trace.id == TraceStep.trace_id)
        .filter(Trace.agent_id == agent_id)
        .filter(TraceStep.step_type == "tool_call")
        .filter(TraceStep.tool_name.isnot(None))
        .group_by(TraceStep.tool_name)
        .all()
    )
    tool_usage = [{"tool_name": r[0], "count": r[1]} for r in tool_usage_rows]

    return {
        "agent_id": agent_id,
        "conversation_count": conversation_count,
        "message_count": message_count,
        "trace_count": trace_count,
        "total_tokens": int(total_tokens),
        "total_duration_ms": int(total_duration_ms),
        "tool_usage": tool_usage,
    }
