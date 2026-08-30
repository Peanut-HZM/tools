"""Agent 市场 API

P2-④ Agent 市场 / 分享
- GET  /api/v1/marketplace/agents            public Agent 目录（登录用户可浏览）
- POST /api/v1/marketplace/agents/{id}/fork  fork public agent 到当前用户名下（private 副本）

fork = 深拷贝 agent 核心字段 + tool_bindings；不拷贝用户数据
（会话/记忆/检查点/轨迹），can_handoff_to 不拷（跨 agent slug 引用，YAGNI）。
"""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_db, get_current_user
from app.models.agent import Agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])

# fork 深拷贝的 agent 字段（与 export bundle 的 agent 子集一致）
_FORK_FIELDS = (
    "name",
    "description",
    "system_prompt",
    "icon",
    "icon_color",
    "category",
    "welcome_message",
    "handoff_instruction",
    "generation_params",
    "memory_short_term_policy",
    "memory_short_term_window",
    "max_steps_per_turn",
    "error_strategy",
    "max_retries",
    "memory_procedural_enabled",
    "sandbox_enabled",
    "memory_long_term_enabled",
    "memory_long_term_config",
)


@router.get("/agents")
async def list_marketplace_agents(
    skip: int = 0,
    limit: int = 50,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """public Agent 目录（登录用户可浏览）"""
    skip = max(0, skip)
    limit = max(1, min(limit, 200))

    agents = (
        db.query(Agent)
        .filter(Agent.visibility == "public", Agent.is_active == True)  # noqa: E712
        .order_by(Agent.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "records": [
            {
                "id": str(a.id),
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "icon_color": a.icon_color,
                "category": a.category,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in agents
        ],
        "count": len(agents),
    }


@router.post("/agents/{agent_id}/fork", status_code=201)
async def fork_agent(
    agent_id: uuid.UUID,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """fork public agent 到当前用户名下（private 副本）"""
    source = db.query(Agent).filter(Agent.id == agent_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    # 仅 public 可被 fork（private/unlisted 不进市场语义）
    if (source.visibility or "public") != "public":
        raise HTTPException(status_code=403, detail="该 Agent 不在市场开放范围")

    from app.models.harness_models import ToolBinding

    forked = Agent(name=f"{source.name}（副本）", description="", system_prompt="")
    for field in _FORK_FIELDS:
        if field == "name":
            continue
        setattr(forked, field, getattr(source, field))
    forked.visibility = "private"
    forked.owner_id = uuid.UUID(str(current_user["id"]))
    forked.is_active = True
    forked.is_default = False
    db.add(forked)
    db.flush()  # 拿到 forked.id 再复制 bindings

    # 复制工具绑定（同库内 tool_id 有效，直拷）
    source_bindings = (
        db.query(ToolBinding).filter(ToolBinding.agent_id == source.id).all()
    )
    for b in source_bindings:
        db.add(ToolBinding(
            agent_id=forked.id,
            tool_id=b.tool_id,
            parameter_overrides=dict(b.parameter_overrides or {}),
            priority=b.priority,
            is_enabled=b.is_enabled,
        ))
    db.commit()
    db.refresh(forked)

    logger.info(
        "Agent 已 fork: source=%s fork=%s user=%s", source.id, forked.id, current_user["id"]
    )
    return {
        "id": str(forked.id),
        "name": forked.name,
        "visibility": forked.visibility,
        "owner_id": str(forked.owner_id),
    }
