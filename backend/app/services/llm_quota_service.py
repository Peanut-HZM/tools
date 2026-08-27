# backend/app/services/llm_quota_service.py
"""LLM 通用配额服务

三选一模式（count / token / time）；并发安全（PG FOR UPDATE 行锁）；
通过 reservation_id 支持预占/回滚/校正。
"""
from __future__ import annotations

import logging
import threading
import uuid as _uuid_mod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import InvalidQuotaMode, QuotaExceeded
from app.models.llm_quota_models import LLMUsageLog, LLMUserQuota

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 工具函数（通用配额语义，支持 daily/monthly/token 三维限额）
# ------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_naive_or_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except (ValueError, TypeError):
            logger.warning("[llm_quota] _to_naive_or_aware 无法解析字符串: %r", dt)
            return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _is_same_day(dt1: datetime, dt2: datetime) -> bool:
    return _to_naive_or_aware(dt1).date() == _to_naive_or_aware(dt2).date()


def _is_same_month(dt1: datetime, dt2: datetime) -> bool:
    d1, d2 = _to_naive_or_aware(dt1), _to_naive_or_aware(dt2)
    return d1.year == d2.year and d1.month == d2.month


# ------------------------------------------------------------------
# 返回结构
# ------------------------------------------------------------------

@dataclass
class QuotaInfo:
    user_id: str
    username: Optional[str]
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
    is_valid: bool  # now 在 [valid_from, valid_until] 内
    granted_by: Optional[str]
    notes: Optional[str]


def _to_info(q: LLMUserQuota, username: Optional[str] = None) -> QuotaInfo:
    now = _now_utc()
    vf = _to_naive_or_aware(q.valid_from)
    vu = _to_naive_or_aware(q.valid_until)
    nw = _to_naive_or_aware(now)
    is_valid = True
    if vf is not None and nw < vf:
        is_valid = False
    if vu is not None and nw > vu:
        is_valid = False
    daily_used = q.daily_used or 0
    monthly_used = q.monthly_used or 0
    token_used = q.token_used or 0
    return QuotaInfo(
        user_id=q.user_id,
        username=username,
        quota_mode=q.quota_mode,
        daily_limit=q.daily_limit,
        daily_used=daily_used,
        daily_remaining=max(0, (q.daily_limit or 0) - daily_used),
        monthly_limit=q.monthly_limit,
        monthly_used=monthly_used,
        monthly_remaining=max(0, (q.monthly_limit or 0) - monthly_used),
        token_period=q.token_period,
        token_limit=q.token_limit,
        token_used=token_used,
        token_remaining=max(0, (q.token_limit or 0) - token_used),
        valid_from=q.valid_from,
        valid_until=q.valid_until,
        is_valid=is_valid,
        granted_by=q.granted_by,
        notes=q.notes,
    )


# ------------------------------------------------------------------
# 服务类
# ------------------------------------------------------------------

class LLMQuotaService:
    """LLM 通用配额服务

    调用流程：
      res_id = check_and_reserve(...)         # 预占
      try:
          result = await llm_call(...)
          record_usage(..., actual_tokens, res_id)   # 校正 + 写 log
      except:
          rollback(res_id)                     # 回滚
    """

    def __init__(self, db: Session, _test_lock: Optional[threading.Lock] = None):
        self.db = db
        self._test_lock = _test_lock
        # reservation_id -> {user_id, planned_tokens, category}
        # v1 单实例内存 dict；多实例需要换 Redis
        self._reservations: dict[str, dict] = {}

    # -------- 公共：用户侧 --------

    def check_and_reserve(
        self, user_id: str, category: str, planned_tokens: int = 0
    ) -> str:
        """校验 + 预占，返回 reservation_id"""
        if self._test_lock is not None:
            with self._test_lock:
                return self._do_check_and_reserve(user_id, category, planned_tokens)
        return self._do_check_and_reserve(user_id, category, planned_tokens, for_update=True)

    def record_usage(
        self,
        user_id: str,
        category: str,
        actual_tokens: int,
        reservation_id: str,
        model_used: Optional[str] = None,
    ) -> None:
        """写 usage_log + 按模式校正扣减"""
        res = self._reservations.pop(reservation_id, None)
        if res is None:
            logger.warning("[llm_quota] record_usage 找不到 reservation_id=%s", reservation_id)
            return

        self.db.expire_all()
        quota = (
            self.db.query(LLMUserQuota)
            .filter(LLMUserQuota.user_id == user_id)
            .with_for_update()
            .first()
        )
        if quota is None:
            logger.warning("[llm_quota] record_usage 用户无配额 row: %s", user_id)
            return

        if quota.quota_mode == "token":
            # 先减去预留，再加实际
            planned = res["planned_tokens"]
            quota.token_used = quota.token_used - planned + actual_tokens
            quota.token_used = max(0, quota.token_used)

        # 写 usage_log
        log = LLMUsageLog(
            user_id=user_id,
            category=category,
            tokens_used=actual_tokens,
            request_count=1,
            model_used=model_used,
            reservation_id=reservation_id,
        )
        self.db.add(log)
        self.db.commit()
        logger.info(
            "[llm_quota] record_usage user=%s category=%s actual=%d model=%s",
            user_id, category, actual_tokens, model_used,
        )

    def rollback(self, reservation_id: str) -> None:
        """回滚预占"""
        res = self._reservations.pop(reservation_id, None)
        if res is None:
            return

        self.db.expire_all()
        quota = (
            self.db.query(LLMUserQuota)
            .filter(LLMUserQuota.user_id == res["user_id"])
            .with_for_update()
            .first()
        )
        if quota is None:
            return

        if quota.quota_mode == "count":
            quota.daily_used = max(0, quota.daily_used - 1)
            quota.monthly_used = max(0, quota.monthly_used - 1)
        elif quota.quota_mode == "token":
            quota.token_used = max(0, quota.token_used - res["planned_tokens"])

        self.db.commit()
        logger.info("[llm_quota] rollback reservation_id=%s", reservation_id)

    def get_user_quota(self, user_id: str) -> Optional[QuotaInfo]:
        quota = (
            self.db.query(LLMUserQuota).filter(LLMUserQuota.user_id == user_id).first()
        )
        if quota is None:
            return None
        # 附带 username：用原生 SQL 查 users 表（避开 SQLAlchemy User 模型列名不一致）
        username = self._lookup_username(user_id)
        return _to_info(quota, username)

    # -------- 公共：管理员侧 --------

    def grant(
        self,
        user_id: str,
        quota_mode: str,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None,
        token_period: Optional[str] = None,
        token_limit: Optional[int] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        granted_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> QuotaInfo:
        """创建/覆盖配额。校验模式字段合法性后写入。"""
        # 模式字段校验
        if quota_mode == "count":
            if not (daily_limit and daily_limit > 0) and not (monthly_limit and monthly_limit > 0):
                raise InvalidQuotaMode("count 模式必须设置 daily_limit 或 monthly_limit > 0")
        elif quota_mode == "token":
            if not (token_limit and token_limit > 0):
                raise InvalidQuotaMode("token 模式必须设置 token_limit > 0")
            if token_period not in ("daily", "monthly", "total"):
                raise InvalidQuotaMode("token_period 必须为 daily/monthly/total")
        elif quota_mode == "time":
            # time 模式：可设置 valid_from / valid_until 之一，也可两个都为空（永久有效）
            pass
        else:
            raise InvalidQuotaMode(f"未知 quota_mode: {quota_mode}")

        self.db.expire_all()
        quota = (
            self.db.query(LLMUserQuota).filter(LLMUserQuota.user_id == user_id).first()
        )
        now = _now_utc()
        if quota is None:
            quota = LLMUserQuota(
                user_id=user_id,
                quota_mode=quota_mode,
                daily_used=0, monthly_used=0, token_used=0,
                daily_reset_date=now, monthly_reset_date=now, token_reset_date=now,
            )
            self.db.add(quota)
        # 覆盖模式字段
        quota.quota_mode = quota_mode
        if quota_mode == "count":
            quota.daily_limit = daily_limit
            quota.monthly_limit = monthly_limit
            if quota.daily_reset_date is None:
                quota.daily_reset_date = now
            if quota.monthly_reset_date is None:
                quota.monthly_reset_date = now
        elif quota_mode == "token":
            quota.token_period = token_period
            quota.token_limit = token_limit
            if quota.token_reset_date is None:
                quota.token_reset_date = now
        quota.valid_from = valid_from
        quota.valid_until = valid_until
        quota.granted_by = granted_by
        # 追加审计信息
        ts_str = now.strftime("%Y-%m-%d %H:%M:%S")
        audit = f"granted_by={granted_by or 'system'} at {ts_str}"
        quota.notes = (notes + " | " + audit) if notes else audit

        self.db.commit()
        self.db.refresh(quota)
        logger.info(
            "[llm_quota] grant user=%s mode=%s daily=%s monthly=%s token_limit=%s granted_by=%s",
            user_id, quota_mode, daily_limit, monthly_limit, token_limit, granted_by,
        )
        # 附带 username：原生 SQL 查 users 表（避免 User 模型列名不一致问题）
        return _to_info(quota, self._lookup_username(user_id))

    def revoke(self, user_id: str) -> None:
        self.db.expire_all()
        quota = (
            self.db.query(LLMUserQuota).filter(LLMUserQuota.user_id == user_id).first()
        )
        if quota is not None:
            self.db.delete(quota)
            self.db.commit()
            logger.info("[llm_quota] revoke user=%s", user_id)

    def reset_counters(self, user_id: str) -> None:
        self.db.expire_all()
        quota = (
            self.db.query(LLMUserQuota).filter(LLMUserQuota.user_id == user_id).with_for_update().first()
        )
        if quota is None:
            return
        if quota.quota_mode == "count":
            quota.daily_used = 0
            quota.monthly_used = 0
        elif quota.quota_mode == "token":
            quota.token_used = 0
        self.db.commit()
        logger.info("[llm_quota] reset_counters user=%s", user_id)

    def list_users(
        self, skip: int = 0, limit: int = 50, search: Optional[str] = None
    ) -> list[QuotaInfo]:
        # 先查配额行
        q = self.db.query(LLMUserQuota)
        if search:
            pattern = f"%{search}%"
            q = q.filter(LLMUserQuota.user_id.like(pattern))
        rows = (
            q.order_by(LLMUserQuota.user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        if not rows:
            return []
        # 批量查 username（原生 SQL，避开 SQLAlchemy User 模型列名问题）
        user_ids = [r.user_id for r in rows]
        username_map = self._lookup_usernames_batch(user_ids)
        return [_to_info(r, username_map.get(r.user_id)) for r in rows]

    def count_users(self, search: Optional[str] = None) -> int:
        q = self.db.query(LLMUserQuota)
        if search:
            pattern = f"%{search}%"
            q = q.filter(LLMUserQuota.user_id.like(pattern))
        return q.count()

    # -------- 内部：username 查询（原生 SQL 避开 User 模型列名问题） --------

    def _lookup_username(self, user_id: str) -> Optional[str]:
        """单条 username 查询；失败或 user 不存在时返回 None"""
        try:
            result = self.db.execute(
                text("SELECT username FROM users WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            return result if isinstance(result, str) else None
        except Exception as e:
            logger.warning("[llm_quota] _lookup_username 失败 user=%s: %s", user_id, e)
            return None

    def _lookup_usernames_batch(self, user_ids: list[str]) -> dict[str, str]:
        """批量查询 user_id → username；user 不存在则不出现在结果中"""
        if not user_ids:
            return {}
        try:
            rows = self.db.execute(
                text("SELECT user_id, username FROM users WHERE user_id = ANY(:ids)"),
                {"ids": user_ids},
            ).fetchall()
            return {row[0]: row[1] for row in rows if isinstance(row[1], str)}
        except Exception as e:
            logger.warning("[llm_quota] _lookup_usernames_batch 失败: %s", e)
            return {}

    # -------- 内部 --------

    def _do_check_and_reserve(
        self, user_id: str, category: str, planned_tokens: int,
        for_update: bool = False,
    ) -> str:
        self.db.expire_all()
        q = self.db.query(LLMUserQuota).filter(LLMUserQuota.user_id == user_id)
        if for_update:
            q = q.with_for_update()
        quota = q.first()
        if quota is None:
            raise QuotaExceeded("no_quota")

        # 校验有效期（所有模式都检查）
        now = _now_utc()
        vf = _to_naive_or_aware(quota.valid_from)
        vu = _to_naive_or_aware(quota.valid_until)
        now_n = _to_naive_or_aware(now)
        if vf is not None and now_n < vf:
            raise QuotaExceeded("validity_not_started")
        if vu is not None and now_n > vu:
            raise QuotaExceeded("validity_expired")

        # 按模式处理
        if quota.quota_mode == "count":
            self._reset_count_if_needed(quota, now)
            if quota.daily_used + 1 > (quota.daily_limit or 0):
                raise QuotaExceeded("daily_limit_exceeded")
            if quota.monthly_used + 1 > (quota.monthly_limit or 0):
                raise QuotaExceeded("monthly_limit_exceeded")
            quota.daily_used += 1
            quota.monthly_used += 1
        elif quota.quota_mode == "token":
            self._reset_token_if_needed(quota, now)
            if quota.token_used + planned_tokens > (quota.token_limit or 0):
                raise QuotaExceeded("token_limit_exceeded")
            quota.token_used += planned_tokens
        elif quota.quota_mode == "time":
            pass  # 已校验有效期
        else:
            logger.error("[llm_quota] 未知 quota_mode=%s user=%s", quota.quota_mode, user_id)
            raise QuotaExceeded("no_quota")

        self.db.commit()

        res_id = str(_uuid_mod.uuid4())
        self._reservations[res_id] = {
            "user_id": user_id,
            "planned_tokens": planned_tokens,
            "category": category,
            "mode": quota.quota_mode,
        }
        logger.info(
            "[llm_quota] check_and_reserve user=%s mode=%s category=%s res_id=%s",
            user_id, quota.quota_mode, category, res_id,
        )
        return res_id

    def _reset_count_if_needed(self, quota: LLMUserQuota, now: datetime) -> None:
        if quota.daily_reset_date is None:
            quota.daily_reset_date = now
        elif not _is_same_day(quota.daily_reset_date, now):
            quota.daily_used = 0
            quota.daily_reset_date = now
        if quota.monthly_reset_date is None:
            quota.monthly_reset_date = now
        elif not _is_same_month(quota.monthly_reset_date, now):
            quota.monthly_used = 0
            quota.monthly_reset_date = now

    def _reset_token_if_needed(self, quota: LLMUserQuota, now: datetime) -> None:
        period = quota.token_period
        if period == "total":
            return
        if quota.token_reset_date is None:
            quota.token_reset_date = now
            return
        if period == "daily" and not _is_same_day(quota.token_reset_date, now):
            quota.token_used = 0
            quota.token_reset_date = now
        elif period == "monthly" and not _is_same_month(quota.token_reset_date, now):
            quota.token_used = 0
            quota.token_reset_date = now
