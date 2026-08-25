# backend/app/routes/admin_llm_quota.py
"""管理员 LLM 配额 API"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidQuotaMode
from app.models.auth_models import UserResponse
from app.models.base import get_db
from app.models.llm_quota_models import LLMUsageLog, LLMUserQuota
from app.routes.admin import get_admin_user
from app.schemas.llm_quota import (
    GrantQuotaRequest,
    QuotaInfoResponse,
    QuotaListResponse,
    QuotaStatsResponse,
)
from app.services.llm_quota_service import LLMQuotaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/llm-quota", tags=["admin-llm-quota"])


def _to_response(info) -> QuotaInfoResponse:
    """将 service 层 QuotaInfo dataclass 转为 Pydantic response"""
    uname = info.username
    if not isinstance(uname, str):
        uname = None
    return QuotaInfoResponse(
        user_id=info.user_id,
        username=uname,
        quota_mode=info.quota_mode,
        daily_limit=info.daily_limit,
        daily_used=info.daily_used,
        daily_remaining=info.daily_remaining,
        monthly_limit=info.monthly_limit,
        monthly_used=info.monthly_used,
        monthly_remaining=info.monthly_remaining,
        token_period=info.token_period,
        token_limit=info.token_limit,
        token_used=info.token_used,
        token_remaining=info.token_remaining,
        valid_from=info.valid_from,
        valid_until=info.valid_until,
        is_valid=info.is_valid,
        granted_by=info.granted_by,
        notes=info.notes,
    )


@router.get("/users", response_model=QuotaListResponse)
def list_users(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员查询已分配配额的用户列表（分页 + 搜索）"""
    svc = LLMQuotaService(db)
    items = svc.list_users(skip=skip, limit=limit, search=search)
    count = svc.count_users(search=search)
    return QuotaListResponse(
        items=[_to_response(i) for i in items],
        skip=skip, limit=limit, count=count,
    )


@router.get("/users/{user_id}", response_model=QuotaInfoResponse)
def get_user(
    user_id: str,
    admin: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """查询单用户配额详情"""
    svc = LLMQuotaService(db)
    info = svc.get_user_quota(user_id)
    if info is None:
        raise HTTPException(status_code=404, detail="quota not found")
    return _to_response(info)


@router.post("/users/{user_id}/grant", response_model=QuotaInfoResponse)
def grant(
    user_id: str,
    body: GrantQuotaRequest,
    admin: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """为指定用户创建/覆盖配额"""
    svc = LLMQuotaService(db)
    try:
        info = svc.grant(
            user_id=user_id,
            quota_mode=body.quota_mode,
            daily_limit=body.daily_limit,
            monthly_limit=body.monthly_limit,
            token_period=body.token_period,
            token_limit=body.token_limit,
            valid_from=body.valid_from,
            valid_until=body.valid_until,
            granted_by=str(admin.user_id),
            notes=body.notes,
        )
    except InvalidQuotaMode as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(info)


@router.post("/users/{user_id}/reset", response_model=QuotaInfoResponse)
def reset(
    user_id: str,
    admin: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """重置指定用户的已用计数"""
    svc = LLMQuotaService(db)
    svc.reset_counters(user_id)
    info = svc.get_user_quota(user_id)
    if info is None:
        raise HTTPException(status_code=404, detail="quota not found")
    return _to_response(info)


@router.delete("/users/{user_id}", status_code=204)
def revoke(
    user_id: str,
    admin: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """撤销指定用户配额"""
    svc = LLMQuotaService(db)
    svc.revoke(user_id)
    return None


@router.get("/stats", response_model=QuotaStatsResponse)
def stats(
    admin: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """全局配额统计：总用户数、按模式分布、今日/本月调用量"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    today_count = (
        db.query(func.count(LLMUsageLog.id))
        .filter(LLMUsageLog.called_at >= today_start)
        .scalar() or 0
    )
    month_count = (
        db.query(func.count(LLMUsageLog.id))
        .filter(LLMUsageLog.called_at >= month_start)
        .scalar() or 0
    )

    total_users = db.query(func.count(LLMUserQuota.user_id)).scalar() or 0
    by_mode_rows = (
        db.query(LLMUserQuota.quota_mode, func.count(LLMUserQuota.user_id))
        .group_by(LLMUserQuota.quota_mode)
        .all()
    )
    by_mode = {row[0]: row[1] for row in by_mode_rows}

    return QuotaStatsResponse(
        total_users=total_users,
        by_mode=by_mode,
        today_total_requests=today_count,
        month_total_requests=month_count,
    )
