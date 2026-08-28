"""admin/traces API — 追踪观测查询

参考 spec: docs/superpowers/specs/2026-08-28-agent-harness-design.md §5.9

端点：
- GET /api/v1/admin/traces                            列表（agent_id / user_id / status / 时间范围 过滤 + 分页）
- GET /api/v1/admin/traces/agent/{agent_id}/recent    单 agent 最近 traces（强制 filter agent_id）
- GET /api/v1/admin/traces/{trace_id}                 详情（含 steps 子查询）

安全要求（来自 Task 14 fix round 1 教训）：
- 所有按 agent 过滤的端点必须 filter agent_id（不能全表扫描）
- 路由顺序：/agent/{agent_id}/recent 必须在 /{trace_id} 之前注册
  （FastAPI 路径匹配优先级，否则 recent 会被当成 trace_id）
"""
import logging
import uuid as _uuid_mod
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_db, get_current_user
from app.models.harness_models import Trace, TraceStep
from app.schemas.harness_schemas import (
    TraceDetailView,
    TraceListView,
    TraceStepView,
    TraceSummaryView,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/traces", tags=["admin-traces"])


def require_admin(current_user: dict = Depends(get_current_user)):
    """管理员权限校验"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# status 合法值（与 ORM Trace.status 注释一致）
TraceStatusLiteral = Literal[
    "success", "error", "timeout", "guardrail_blocked", "handoff"
]


def _parse_iso_datetime(raw: str, field: str) -> datetime:
    """解析 ISO 8601 时间字符串，失败返回 422"""
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422, detail=f"{field} 不是合法的 ISO 8601 时间字符串"
        )


def _trace_to_summary(trace: Trace) -> TraceSummaryView:
    """Trace -> TraceSummaryView（显式 UUID 转换）"""
    return TraceSummaryView(
        id=str(trace.id),
        conversation_id=str(trace.conversation_id),
        agent_id=str(trace.agent_id),
        user_id=str(trace.user_id),
        status=trace.status,
        total_steps=trace.total_steps or 0,
        total_tokens=trace.total_tokens or 0,
        total_duration_ms=trace.total_duration_ms or 0,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
    )


def _step_to_view(step: TraceStep) -> TraceStepView:
    """TraceStep -> TraceStepView"""
    return TraceStepView(
        id=str(step.id),
        step_index=step.step_index,
        step_type=step.step_type,
        tool_name=step.tool_name,
        llm_model=step.llm_model,
        tokens_used=step.tokens_used or 0,
        duration_ms=step.duration_ms or 0,
        input_summary=step.input_summary,
        output_summary=step.output_summary,
        error_message=step.error_message,
    )


@router.get("", response_model=TraceListView)
def list_traces(
    agent_id: Optional[str] = Query(None, description="按 agent 过滤"),
    user_id: Optional[str] = Query(None, description="按用户过滤"),
    status: Optional[TraceStatusLiteral] = Query(None, description="按状态过滤"),
    start_time: Optional[str] = Query(None, description="起始时间 (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO 8601)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: DBSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Trace 列表（多维过滤 + 分页）

    安全：所有可选过滤参数都会生成 WHERE 子句，绝不返回全表。
    """
    q = db.query(Trace)

    if agent_id is not None:
        try:
            agent_uuid = _uuid_mod.UUID(agent_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="agent_id 不是合法的 UUID")
        q = q.filter(Trace.agent_id == agent_uuid)

    if user_id is not None:
        try:
            user_uuid = _uuid_mod.UUID(user_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="user_id 不是合法的 UUID")
        q = q.filter(Trace.user_id == user_uuid)

    if status is not None:
        q = q.filter(Trace.status == status)

    if start_time is not None:
        start_dt = _parse_iso_datetime(start_time, "start_time")
        q = q.filter(Trace.started_at >= start_dt)

    if end_time is not None:
        end_dt = _parse_iso_datetime(end_time, "end_time")
        q = q.filter(Trace.started_at <= end_dt)

    total = q.count()
    items = (
        q.order_by(Trace.started_at.desc()).offset(skip).limit(limit).all()
    )
    logger.info(
        f"list_traces agent_id={agent_id} user_id={user_id} status={status} "
        f"start={start_time} end={end_time} skip={skip} limit={limit} total={total}"
    )
    return TraceListView(
        items=[_trace_to_summary(t) for t in items],
        total=total,
    )


# 注意路由顺序：/agent/{agent_id}/recent 必须在 /{trace_id} 之前注册
@router.get("/agent/{agent_id}/recent", response_model=TraceListView)
def get_recent_agent_traces(
    agent_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: DBSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """单 agent 最近 traces（强制 filter agent_id）

    安全：路径参数 agent_id 必须转换为 UUID 并 filter，绝不能返回全表 traces。
    """
    try:
        agent_uuid = _uuid_mod.UUID(agent_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="agent_id 不是合法的 UUID")

    q = db.query(Trace).filter(Trace.agent_id == agent_uuid)
    total = q.count()
    items = q.order_by(Trace.started_at.desc()).limit(limit).all()
    logger.info(
        f"get_recent_agent_traces agent_id={agent_id} limit={limit} total={total}"
    )
    return TraceListView(
        items=[_trace_to_summary(t) for t in items],
        total=total,
    )


@router.get("/{trace_id}", response_model=TraceDetailView)
def get_trace(
    trace_id: str,
    db: DBSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Trace 详情（含 steps 子查询）"""
    try:
        trace_uuid = _uuid_mod.UUID(trace_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="trace_id 不是合法的 UUID")

    trace = db.query(Trace).filter(Trace.id == trace_uuid).first()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    steps = (
        db.query(TraceStep)
        .filter(TraceStep.trace_id == trace_uuid)
        .order_by(TraceStep.step_index.asc())
        .all()
    )
    logger.info(f"get_trace trace_id={trace_id} steps={len(steps)}")

    return TraceDetailView(
        id=str(trace.id),
        conversation_id=str(trace.conversation_id),
        agent_id=str(trace.agent_id),
        user_id=str(trace.user_id),
        status=trace.status,
        total_steps=trace.total_steps or 0,
        total_tokens=trace.total_tokens or 0,
        total_duration_ms=trace.total_duration_ms or 0,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        input_text=trace.input_text,
        output_text=trace.output_text,
        error_message=trace.error_message,
        steps=[_step_to_view(s) for s in steps],
    )