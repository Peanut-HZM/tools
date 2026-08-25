# backend/app/schemas/llm_quota.py
"""LLM 通用配额 Pydantic schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class GrantQuotaRequest(BaseModel):
    quota_mode: str = Field(..., description="count/token/time")
    # count 模式
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    # token 模式
    token_period: Optional[str] = None
    token_limit: Optional[int] = None
    # 公共
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class QuotaInfoResponse(BaseModel):
    user_id: str
    username: Optional[str] = None
    quota_mode: str
    daily_limit: Optional[int]
    daily_used: int
    daily_remaining: int
    monthly_limit: Optional[int]
    monthly_used: int
    monthly_remaining: int
    token_period: Optional[str]
    token_limit: Optional[int]
    token_used: int
    token_remaining: int
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    is_valid: bool
    granted_by: Optional[str]
    notes: Optional[str]


class QuotaListResponse(BaseModel):
    items: list[QuotaInfoResponse]
    skip: int
    limit: int
    count: int


class QuotaStatsResponse(BaseModel):
    total_users: int
    by_mode: dict[str, int]
    today_total_requests: int
    month_total_requests: int
