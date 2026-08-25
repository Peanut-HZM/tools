# backend/app/routes/user_quota.py
"""用户侧 LLM 配额 API"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# 注：brief 写的是 app.core.security，但仓库内实际路径为 app.middleware.auth_middleware，
# 与 admin 路由所用 get_current_user 同源，返回 UserResponse。
from app.middleware.auth_middleware import get_current_user
from app.models.auth_models import UserResponse
from app.models.base import get_db
from app.schemas.llm_quota import QuotaInfoResponse
from app.services.llm_quota_service import LLMQuotaService
from app.routes.admin_llm_quota import _to_response

router = APIRouter(prefix="/api/quota", tags=["user-quota"])


@router.get("/me", response_model=QuotaInfoResponse)
def get_my_quota(
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询当前登录用户自身的 LLM 配额信息"""
    svc = LLMQuotaService(db)
    info = svc.get_user_quota(str(user.user_id))
    if info is None:
        raise HTTPException(status_code=404, detail="no_quota")
    return _to_response(info)
