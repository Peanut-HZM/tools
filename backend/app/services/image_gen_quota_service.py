"""
Task 4.1 — QuotaService（并发预留 + 重置日期逻辑）

提供图像生成功能的配额管理：
  - check_and_reserve: SELECT FOR UPDATE 锁行 → 校验有效期 → 校验余额 → 递增 counter
  - commit / release: 事务提交 / 回滚
  - 管理员方法: grant / revoke / reset_counters / list_users / get_user_quota
  - 自动重置: daily_reset_date / monthly_reset_date 与 today 比较，跨日/跨月归零
"""

import logging
import threading
import uuid as _uuid_mod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import QuotaExceeded
from app.models.image_generation_models import ImageGenQuota

logger = logging.getLogger(__name__)


@dataclass
class QuotaInfo:
    """配额信息返回结构"""
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    is_valid: bool  # valid_from <= now <= valid_until (nulls = no bound)
    granted_by: Optional[str]
    notes: Optional[str]


def _now_utc() -> datetime:
    """当前 UTC 时间（带 timezone）"""
    return datetime.now(timezone.utc)


def _to_naive_or_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    用于比较：把 datetime 统一到可比较状态。
    SQLite 存的 datetime 可能无 timezone 信息，PostgreSQL 的有。
    这里统一去掉 timezone 做 date 比较，避免 TypeError。
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """比较两个 datetime 是否为同一天（忽略时区）"""
    d1 = _to_naive_or_aware(dt1)
    d2 = _to_naive_or_aware(dt2)
    return d1.date() == d2.date()


def _is_same_month(dt1: datetime, dt2: datetime) -> bool:
    """比较两个 datetime 是否为同一年月（忽略时区）"""
    d1 = _to_naive_or_aware(dt1)
    d2 = _to_naive_or_aware(dt2)
    return d1.year == d2.year and d1.month == d2.month


def _quota_to_info(q: ImageGenQuota) -> QuotaInfo:
    """把 ORM 对象转为 QuotaInfo dataclass"""
    now = _now_utc()
    # 计算 is_valid
    valid_from_naive = _to_naive_or_aware(q.valid_from)
    valid_until_naive = _to_naive_or_aware(q.valid_until)
    now_naive = _to_naive_or_aware(now)

    is_valid = True
    if valid_from_naive is not None and now_naive < valid_from_naive:
        is_valid = False
    if valid_until_naive is not None and now_naive > valid_until_naive:
        is_valid = False

    return QuotaInfo(
        user_id=q.user_id,
        daily_limit=q.daily_limit,
        daily_used=q.daily_used,
        daily_remaining=max(0, q.daily_limit - q.daily_used),
        monthly_limit=q.monthly_limit,
        monthly_used=q.monthly_used,
        monthly_remaining=max(0, q.monthly_limit - q.monthly_used),
        valid_from=q.valid_from,
        valid_until=q.valid_until,
        is_valid=is_valid,
        granted_by=q.granted_by,
        notes=q.notes,
    )


class ImageGenQuotaService:
    """
    图像生成配额服务。

    核心流程：
      1. check_and_reserve → SELECT FOR UPDATE 锁行 → 校验 → 递增
      2. 生成成功 → commit()
      3. 生成失败 → release()（回滚释放预留）
    """

    def __init__(self, db: Session, _test_lock: Optional[threading.Lock] = None):
        """
        初始化。
        _test_lock: 测试用，传入 threading.Lock 模拟 SQLite 上的 FOR UPDATE 语义。
                    生产环境使用 PostgreSQL 的 SELECT FOR UPDATE 行锁。
        """
        self.db = db
        self._test_lock = _test_lock

    # ------------------------------------------------------------------
    # 用户侧（每次生成前后调用）
    # ------------------------------------------------------------------

    def check_and_reserve(self, user_id: str, operation: str, n: int = 1) -> None:
        """
        校验配额并预留。成功时 daily_used/monthly_used 已 +n。
        失败抛 QuotaExceeded(reason)。

        - PostgreSQL 环境：SELECT FOR UPDATE 锁行，并发安全
        - SQLite 测试环境：通过 _test_lock 参数传入 threading.Lock 模拟
        - 自动处理 daily/monthly 重置（按 reset_date 比较 today）
        """
        # 根据数据库类型选择并发控制策略
        if self._test_lock is not None:
            # 测试模式：用 threading.Lock 模拟 FOR UPDATE
            with self._test_lock:
                self._do_reserve(user_id, operation, n)
        else:
            # 生产模式：PostgreSQL 用 with_for_update() 行锁
            self._do_reserve(user_id, operation, n, for_update=True)

    def _do_reserve(self, user_id: str, operation: str, n: int, for_update: bool = False) -> None:
        """实际预留逻辑（内部方法）"""
        now = _now_utc()

        # 清除 identity map 缓存，确保读到最新已提交数据（SQLite 多线程测试必需；
        # 生产 PostgreSQL 下 with_for_update 也会重新读取，不会有性能问题）
        self.db.expire_all()

        # 查询配额行（生产环境 SELECT FOR UPDATE）
        q = self.db.query(ImageGenQuota).filter(ImageGenQuota.user_id == user_id)
        if for_update:
            q = q.with_for_update()
        quota = q.first()

        # 1. 校验配额是否存在
        if quota is None:
            raise QuotaExceeded("no_quota")

        # 2. 校验有效期
        valid_from_naive = _to_naive_or_aware(quota.valid_from)
        valid_until_naive = _to_naive_or_aware(quota.valid_until)
        now_naive = _to_naive_or_aware(now)

        if valid_from_naive is not None and now_naive < valid_from_naive:
            raise QuotaExceeded("validity_not_started")
        if valid_until_naive is not None and now_naive > valid_until_naive:
            raise QuotaExceeded("validity_expired")

        # 3. 自动重置 daily（reset_date 不是今天则归零）
        if not _is_same_day(quota.daily_reset_date, now):
            quota.daily_used = 0
            quota.daily_reset_date = now

        # 4. 自动重置 monthly（reset_date 不是本月则归零）
        if not _is_same_month(quota.monthly_reset_date, now):
            quota.monthly_used = 0
            quota.monthly_reset_date = now

        # 5. 校验余额
        if quota.daily_used + n > quota.daily_limit:
            raise QuotaExceeded("daily_limit_exceeded")
        if quota.monthly_used + n > quota.monthly_limit:
            raise QuotaExceeded("monthly_limit_exceeded")

        # 6. 递增计数器
        quota.daily_used += n
        quota.monthly_used += n

        logger.info(
            "配额预留成功: user=%s op=%s n=%d daily=%d/%d monthly=%d/%d",
            user_id, operation, n,
            quota.daily_used, quota.daily_limit,
            quota.monthly_used, quota.monthly_limit,
        )

    def commit(self) -> None:
        """预留成功后的事务提交"""
        self.db.commit()

    def release(self) -> None:
        """生成失败/取消时的事务回滚（释放预留）"""
        self.db.rollback()

    def get_user_quota(self, user_id: str) -> Optional[QuotaInfo]:
        """查看当前用户的配额信息（含 remaining、is_valid）"""
        quota = self.db.query(ImageGenQuota).filter(ImageGenQuota.user_id == user_id).first()
        if quota is None:
            return None
        return _quota_to_info(quota)

    # ------------------------------------------------------------------
    # 管理员侧
    # ------------------------------------------------------------------

    def grant(
        self,
        user_id: str,
        daily_limit: int,
        monthly_limit: int,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        granted_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> QuotaInfo:
        """
        创建/覆盖配额。
        若 user_id 已有记录则更新字段（保留已用量，仅重置管理员设置的参数）。
        """
        quota = self.db.query(ImageGenQuota).filter(ImageGenQuota.user_id == user_id).first()

        if quota is None:
            # 新建
            now = _now_utc()
            quota = ImageGenQuota(
                user_id=user_id,
                daily_limit=daily_limit,
                monthly_limit=monthly_limit,
                daily_used=0,
                monthly_used=0,
                daily_reset_date=now,
                monthly_reset_date=now,
                valid_from=valid_from,
                valid_until=valid_until,
                granted_by=granted_by,
                notes=notes,
            )
            self.db.add(quota)
        else:
            # 覆盖已有记录
            quota.daily_limit = daily_limit
            quota.monthly_limit = monthly_limit
            quota.valid_from = valid_from
            quota.valid_until = valid_until
            quota.granted_by = granted_by
            quota.notes = notes

        self.db.commit()
        self.db.refresh(quota)

        logger.info("配额 grant: user=%s daily=%d monthly=%d", user_id, daily_limit, monthly_limit)
        return _quota_to_info(quota)

    def revoke(self, user_id: str) -> None:
        """撤销配额（delete row）"""
        quota = self.db.query(ImageGenQuota).filter(ImageGenQuota.user_id == user_id).first()
        if quota is not None:
            self.db.delete(quota)
            self.db.commit()
            logger.info("配额 revoke: user=%s", user_id)

    def reset_counters(self, user_id: str) -> None:
        """把 daily_used/monthly_used 归零"""
        quota = self.db.query(ImageGenQuota).filter(ImageGenQuota.user_id == user_id).first()
        if quota is not None:
            quota.daily_used = 0
            quota.monthly_used = 0
            self.db.commit()
            logger.info("配额 reset_counters: user=%s", user_id)

    def list_users(
        self, skip: int = 0, limit: int = 50, search: Optional[str] = None
    ) -> List[QuotaInfo]:
        """
        列出有配额的用户。

        - skip/limit：标准分页
        - search：模糊匹配 user_id（None 时返回全部）
        """
        q = self.db.query(ImageGenQuota)
        if search:
            pattern = f"%{search}%"
            q = q.filter(ImageGenQuota.user_id.like(pattern))
        quotas = q.order_by(ImageGenQuota.user_id).offset(skip).limit(limit).all()
        return [_quota_to_info(q) for q in quotas]

    def count_users(self, search: Optional[str] = None) -> int:
        """统计有配额的用户数量（与 list_users 同语义 search）"""
        q = self.db.query(ImageGenQuota)
        if search:
            pattern = f"%{search}%"
            q = q.filter(ImageGenQuota.user_id.like(pattern))
        return q.count()
