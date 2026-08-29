"""Agent Trace 查询 API

Phase 3 Plan 1C / Task 3: 前端查询 traces 的 REST API

端点：
- GET /api/v1/harness/agents/{agent_id}/traces            列表（conversation_id / status 过滤 + 分页）
- GET /api/v1/harness/agents/{agent_id}/traces/{trace_id} 详情（含 steps 子查询）

安全要求：
- 所有查询强制 filter user_id（租户隔离），其他用户的 trace 不可见
- agent_id 为路径参数，强制 filter
- 不需要 admin 角色；调用者只能查自己的 traces
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.harness_models import Trace, TraceStep

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/harness/agents/{agent_id}/traces",
    tags=["harness-traces"],
)


# --- Schemas ---

class TraceStepResponse(BaseModel):
    id: uuid.UUID
    step_index: int
    step_type: str
    created_at: Optional[str]
    duration_ms: Optional[int]
    tokens_used: int
    tool_name: Optional[str]
    llm_model: Optional[str]
    input_summary: Optional[str]
    output_summary: Optional[str]
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class TraceResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    agent_id: uuid.UUID
    user_id: uuid.UUID
    input_text: str
    output_text: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_duration_ms: int
    total_steps: int
    total_tokens: int
    error_message: Optional[str]
    steps: list[TraceStepResponse] = []

    class Config:
        from_attributes = True


class TraceListResponse(BaseModel):
    items: list[TraceResponse]
    total: int
    page: int
    page_size: int


# --- Helpers ---

def _format_trace(trace: Trace, include_steps: bool = False) -> dict:
    """把 ORM Trace 转成 response dict"""
    data = {
        "id": trace.id,
        "conversation_id": trace.conversation_id,
        "agent_id": trace.agent_id,
        "user_id": trace.user_id,
        "input_text": trace.input_text,
        "output_text": trace.output_text,
        "status": trace.status,
        "started_at": trace.started_at.isoformat() if trace.started_at else None,
        "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
        "total_duration_ms": trace.total_duration_ms or 0,
        "total_steps": trace.total_steps or 0,
        "total_tokens": trace.total_tokens or 0,
        "error_message": trace.error_message,
        "steps": [],
    }
    if include_steps and hasattr(trace, "steps"):
        data["steps"] = [
            {
                "id": s.id,
                "step_index": s.step_index,
                "step_type": s.step_type,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "duration_ms": s.duration_ms or 0,
                "tokens_used": s.tokens_used or 0,
                "tool_name": s.tool_name,
                "llm_model": s.llm_model,
                "input_summary": s.input_summary,
                "output_summary": s.output_summary,
                "metadata": s.metadata_ if hasattr(s, "metadata_") else None,
            }
            for s in trace.steps
        ]
    return data


# --- Endpoints ---

@router.get("")
def list_traces(
    agent_id: uuid.UUID,
    conversation_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户对指定 Agent 的 traces（分页 + conversation/status 过滤）"""
    user_id = uuid.UUID(str(current_user["id"]))
    base_q = db.query(Trace).filter(
        Trace.agent_id == agent_id,
        Trace.user_id == user_id,
    )
    if conversation_id:
        base_q = base_q.filter(Trace.conversation_id == conversation_id)
    if status:
        base_q = base_q.filter(Trace.status == status)

    total = base_q.count()
    items = (
        base_q.order_by(desc(Trace.started_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    logger.info(
        f"list_traces agent_id={agent_id} user_id={user_id} "
        f"conversation_id={conversation_id} status={status} "
        f"page={page} page_size={page_size} total={total}"
    )
    return {
        "items": [_format_trace(t, include_steps=False) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{trace_id}")
def get_trace(
    agent_id: uuid.UUID,
    trace_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单条 trace + 所有 steps（租户隔离）"""
    user_id = uuid.UUID(str(current_user["id"]))
    trace = (
        db.query(Trace)
        .filter(
            Trace.id == trace_id,
            Trace.agent_id == agent_id,
            Trace.user_id == user_id,
        )
        .first()
    )
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    # 触发 ORM relationship 加载 steps（如果未 lazy load）
    steps = (
        db.query(TraceStep)
        .filter(TraceStep.trace_id == trace_id)
        .order_by(TraceStep.step_index.asc())
        .all()
    )
    # 将 steps 挂到 trace.steps 以复用 _format_trace
    trace.steps = steps  # type: ignore[attr-defined]

    logger.info(f"get_trace trace_id={trace_id} steps={len(steps)}")
    return _format_trace(trace, include_steps=True)
