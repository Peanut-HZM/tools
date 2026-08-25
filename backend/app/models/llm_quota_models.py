# backend/app/models/llm_quota_models.py
"""LLM 通用配额 - SQLAlchemy 模型

两张表：
  - llm_user_quota：每用户 1 行，三选一模式（count/token/time）
  - llm_usage_log：每次 LLM 调用 1 行（用于审计 + 统计）
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class LLMUserQuota(Base):
    """用户配额表（三选一模式）"""
    __tablename__ = "llm_user_quota"

    user_id = Column(String(64), primary_key=True)
    quota_mode = Column(String(16), nullable=False)  # 'count' / 'token' / 'time'

    # --- count 模式字段 ---
    daily_limit = Column(Integer, nullable=True)
    daily_used = Column(Integer, nullable=False, default=0)
    daily_reset_date = Column(DateTime(timezone=True), nullable=True)
    monthly_limit = Column(Integer, nullable=True)
    monthly_used = Column(Integer, nullable=False, default=0)
    monthly_reset_date = Column(DateTime(timezone=True), nullable=True)

    # --- token 模式字段 ---
    token_period = Column(String(16), nullable=True)  # 'daily' / 'monthly' / 'total'
    token_limit = Column(Integer, nullable=True)
    token_used = Column(Integer, nullable=False, default=0)
    token_reset_date = Column(DateTime(timezone=True), nullable=True)

    # --- 公共字段 ---
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    granted_by = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LLMUsageLog(Base):
    """每次 LLM 调用流水（用于审计 + 统计）"""
    __tablename__ = "llm_usage_log"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    category = Column(String(16), nullable=False, index=True)  # 'text'/'image'/'asr'/'ocr'/'embedding'
    tokens_used = Column(Integer, nullable=False, default=0)
    request_count = Column(Integer, nullable=False, default=1)
    model_used = Column(String(128), nullable=True)
    reservation_id = Column(String(64), nullable=True, index=True)
    called_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
