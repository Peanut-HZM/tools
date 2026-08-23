"""
Task 4.1 — QuotaService 并发预留 + 重置日期逻辑 单元测试

使用 SQLite 内存 DB，每个用例一个干净 session。
覆盖范围：
  ✓ check_and_reserve 成功 / 日限 / 月限 / 无配额 / 有效期未开始 / 有效期已过
  ✓ daily / monthly 自动重置（按 reset_date 比较 today）
  ✓ release 回滚 / commit 持久化
  ✓ 100 并发请求不超限（threading.Lock 模拟 FOR UPDATE 语义）
  ✓ grant / revoke / reset_counters / list_users / get_user_quota
  ✓ 永久有效（valid_from / valid_until 均 None）
"""

import sys
import uuid
import threading
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_generation_models import ImageGenQuota

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.image_gen_quota_service import ImageGenQuotaService, QuotaInfo
from app.core.exceptions import QuotaExceeded


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_uid() -> str:
    """生成测试用 user_id 字符串"""
    return str(uuid.uuid4())


def _create_quota(
    session,
    user_id: str,
    daily_limit: int = 10,
    monthly_limit: int = 100,
    daily_used: int = 0,
    monthly_used: int = 0,
    daily_reset_date: datetime = None,
    monthly_reset_date: datetime = None,
    valid_from: datetime = None,
    valid_until: datetime = None,
    granted_by: str = None,
    notes: str = None,
) -> ImageGenQuota:
    """在测试 DB 中直接插入配额记录"""
    now = datetime.now(timezone.utc)
    q = ImageGenQuota(
        user_id=user_id,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
        daily_used=daily_used,
        monthly_used=monthly_used,
        daily_reset_date=daily_reset_date or now,
        monthly_reset_date=monthly_reset_date or now,
        valid_from=valid_from,
        valid_until=valid_until,
        granted_by=granted_by,
        notes=notes,
    )
    session.add(q)
    session.commit()
    session.refresh(q)
    return q


# ============================================================
# check_and_reserve 成功 / 超限
# ============================================================

class TestCheckAndReserve:
    def test_check_and_reserve_success(self, db_session):
        """有配额、有效期内、余额足 → 通过，daily_used +n"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=10, monthly_limit=100)

        svc = ImageGenQuotaService(db_session)
        svc.check_and_reserve(uid, "txt2img", n=2)

        # 验证 DB 行已递增（事务内可见）
        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_used == 2
        assert row.monthly_used == 2

    def test_daily_limit_exceeded(self, db_session):
        """daily_used == daily_limit → QuotaExceeded("daily_limit_exceeded")"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=5, monthly_limit=100, daily_used=5)

        svc = ImageGenQuotaService(db_session)
        with pytest.raises(QuotaExceeded) as exc_info:
            svc.check_and_reserve(uid, "txt2img", n=1)
        assert exc_info.value.reason == "daily_limit_exceeded"

    def test_monthly_limit_exceeded(self, db_session):
        """monthly_used == monthly_limit → QuotaExceeded("monthly_limit_exceeded")"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=100, monthly_limit=10, monthly_used=10)

        svc = ImageGenQuotaService(db_session)
        with pytest.raises(QuotaExceeded) as exc_info:
            svc.check_and_reserve(uid, "txt2img", n=1)
        assert exc_info.value.reason == "monthly_limit_exceeded"

    def test_no_quota_record(self, db_session):
        """用户在 image_gen_quota 表无记录 → QuotaExceeded("no_quota")"""
        uid = _make_uid()
        svc = ImageGenQuotaService(db_session)
        with pytest.raises(QuotaExceeded) as exc_info:
            svc.check_and_reserve(uid, "txt2img", n=1)
        assert exc_info.value.reason == "no_quota"

    def test_validity_not_started(self, db_session):
        """now < valid_from → QuotaExceeded("validity_not_started")"""
        uid = _make_uid()
        future = datetime.now(timezone.utc) + timedelta(days=7)
        far_future = datetime.now(timezone.utc) + timedelta(days=30)
        _create_quota(db_session, uid, valid_from=future, valid_until=far_future)

        svc = ImageGenQuotaService(db_session)
        with pytest.raises(QuotaExceeded) as exc_info:
            svc.check_and_reserve(uid, "txt2img", n=1)
        assert exc_info.value.reason == "validity_not_started"

    def test_validity_expired(self, db_session):
        """now > valid_until → QuotaExceeded("validity_expired")"""
        uid = _make_uid()
        past = datetime.now(timezone.utc) - timedelta(days=30)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        _create_quota(db_session, uid, valid_from=past, valid_until=yesterday)

        svc = ImageGenQuotaService(db_session)
        with pytest.raises(QuotaExceeded) as exc_info:
            svc.check_and_reserve(uid, "txt2img", n=1)
        assert exc_info.value.reason == "validity_expired"

    def test_reserve_exactly_remaining(self, db_session):
        """余额刚好等于 n → 应成功"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=5, monthly_limit=100, daily_used=3)

        svc = ImageGenQuotaService(db_session)
        svc.check_and_reserve(uid, "txt2img", n=2)
        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_used == 5

    def test_reserve_exceeds_remaining(self, db_session):
        """余额 < n → 应失败"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=5, monthly_limit=100, daily_used=4)

        svc = ImageGenQuotaService(db_session)
        with pytest.raises(QuotaExceeded) as exc_info:
            svc.check_and_reserve(uid, "txt2img", n=2)
        assert exc_info.value.reason == "daily_limit_exceeded"


# ============================================================
# 自动重置逻辑
# ============================================================

class TestAutoReset:
    def test_daily_auto_reset(self, db_session):
        """daily_reset_date 是昨天，daily_used=5 → 调用后 daily_used=1（重置后 +1）"""
        uid = _make_uid()
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        _create_quota(
            db_session, uid,
            daily_limit=10, monthly_limit=100,
            daily_used=5, monthly_used=20,
            daily_reset_date=yesterday,
        )

        svc = ImageGenQuotaService(db_session)
        svc.check_and_reserve(uid, "txt2img", n=1)

        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_used == 1  # 重置为 0 再 +1
        assert row.monthly_used == 21  # 月不变（同一个月内）

    def test_monthly_auto_reset(self, db_session):
        """monthly_reset_date 是上个月，monthly_used=50 → 调用后 monthly_used=1"""
        uid = _make_uid()
        last_month = datetime.now(timezone.utc) - timedelta(days=60)
        _create_quota(
            db_session, uid,
            daily_limit=100, monthly_limit=100,
            daily_used=0, monthly_used=50,
            monthly_reset_date=last_month,
        )

        svc = ImageGenQuotaService(db_session)
        svc.check_and_reserve(uid, "txt2img", n=1)

        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.monthly_used == 1
        # 同时 daily 也可能重置（取决于 reset_date），这里只断言 monthly
        assert row.monthly_limit == 100


# ============================================================
# commit / release
# ============================================================

class TestCommitRelease:
    def test_commit_persists(self, db_session):
        """check_and_reserve + commit → 新 session 查询确认 DB 真改了"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=10, monthly_limit=100)

        svc = ImageGenQuotaService(db_session)
        svc.check_and_reserve(uid, "txt2img", n=3)
        svc.commit()

        # 用新 session 验证持久化
        engine = db_session.get_bind()
        Session2 = sessionmaker(bind=engine)
        session2 = Session2()
        try:
            row = session2.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
            assert row.daily_used == 3
            assert row.monthly_used == 3
        finally:
            session2.close()

    def test_release_rolls_back(self, db_session):
        """check_and_reserve 后调 release → daily_used 不变（事务回滚）"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=10, monthly_limit=100)

        svc = ImageGenQuotaService(db_session)
        svc.check_and_reserve(uid, "txt2img", n=3)
        # 此时 session 内 daily_used=3，但未 commit

        svc.release()  # rollback

        # 回滚后，用同一 session 重新查询应看到原始值
        # 注意：rollback 后 session 状态回到 commit 之前，SQLAlchemy 会重新加载
        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_used == 0  # 回滚到初始


# ============================================================
# 并发测试（100 请求不超限）
# ============================================================

class TestConcurrency:
    def test_concurrent_100_requests_no_overlimit(self):
        """
        100 个并发线程同时执行预留逻辑，验证不超限。

        SQLite 不支持 SELECT FOR UPDATE，按 brief 选项 (b) 用 threading.Lock
        模拟 FOR UPDATE 语义，用内存计数器模拟 DB 行。
        这验证了"锁 → 校验 → 递增"的并发安全性逻辑。
        真正 PostgreSQL 下的 SQL 行锁由 with_for_update() 在生产环境保证。
        """
        # 模拟数据库行的内存状态
        row = {"daily_used": 0, "daily_limit": 20}
        lock = threading.Lock()  # 模拟 FOR UPDATE
        success_count = 0
        fail_count = 0
        count_lock = threading.Lock()

        def worker():
            nonlocal success_count, fail_count
            # 模拟 ImageGenQuotaService.check_and_reserve 的并发逻辑
            with lock:  # 等价于 SELECT FOR UPDATE 锁行
                if row["daily_used"] + 1 > row["daily_limit"]:
                    with count_lock:
                        fail_count += 1
                else:
                    row["daily_used"] += 1
                    with count_lock:
                        success_count += 1

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # 核心断言：成功次数不超过 daily_limit=20
        assert success_count <= 20, (
            f"并发预留成功 {success_count} 次，超过 daily_limit=20"
        )
        # 计数器精确等于 limit（20 个成功 + 80 个失败 = 100）
        assert success_count == 20
        assert fail_count == 80
        assert row["daily_used"] == 20


# ============================================================
# 管理员方法
# ============================================================

class TestAdminMethods:
    def test_grant_creates_record(self, db_session):
        """管理员 grant → 创建配额记录"""
        uid = _make_uid()
        admin_id = _make_uid()
        svc = ImageGenQuotaService(db_session)
        info = svc.grant(
            user_id=uid,
            daily_limit=50,
            monthly_limit=500,
            valid_from=None,
            valid_until=None,
            granted_by=admin_id,
            notes="测试配额",
        )
        assert isinstance(info, QuotaInfo)
        assert info.user_id == uid
        assert info.daily_limit == 50
        assert info.monthly_limit == 500
        assert info.daily_remaining == 50
        assert info.monthly_remaining == 500
        assert info.notes == "测试配额"

    def test_grant_overwrites_existing(self, db_session):
        """二次 grant 覆盖已有记录"""
        uid = _make_uid()
        svc = ImageGenQuotaService(db_session)
        svc.grant(uid, 10, 100, None, None, None, None)
        svc.grant(uid, 20, 200, None, None, None, "updated")

        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_limit == 20
        assert row.monthly_limit == 200
        assert row.notes == "updated"

    def test_revoke_deletes_record(self, db_session):
        """revoke 后无记录"""
        uid = _make_uid()
        svc = ImageGenQuotaService(db_session)
        svc.grant(uid, 10, 100, None, None, None, None)
        svc.revoke(uid)

        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).first()
        assert row is None

    def test_reset_counters_zeroes_used(self, db_session):
        """reset_counters 后 daily_used=monthly_used=0"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_used=5, monthly_used=30)

        svc = ImageGenQuotaService(db_session)
        svc.reset_counters(uid)

        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_used == 0
        assert row.monthly_used == 0

    def test_list_users_pagination(self, db_session):
        """skip/limit 工作"""
        svc = ImageGenQuotaService(db_session)
        # 创建 5 个用户配额
        for i in range(5):
            svc.grant(_make_uid(), 10, 100, None, None, None, None)

        all_users = svc.list_users(skip=0, limit=50)
        assert len(all_users) == 5

        page1 = svc.list_users(skip=0, limit=2)
        assert len(page1) == 2

        page2 = svc.list_users(skip=2, limit=2)
        assert len(page2) == 2

        page3 = svc.list_users(skip=4, limit=2)
        assert len(page3) == 1

    def test_grant_with_no_validity_period(self, db_session):
        """valid_from/valid_until 都 None → 永久有效，is_valid=True"""
        uid = _make_uid()
        svc = ImageGenQuotaService(db_session)
        info = svc.grant(uid, 10, 100, None, None, None, None)

        assert info.valid_from is None
        assert info.valid_until is None
        assert info.is_valid is True

        # 永久有效的用户应能正常 check_and_reserve
        svc.check_and_reserve(uid, "txt2img", n=1)
        row = db_session.query(ImageGenQuota).filter(ImageGenQuota.user_id == uid).one()
        assert row.daily_used == 1


# ============================================================
# get_user_quota
# ============================================================

class TestGetUserQuota:
    def test_get_user_quota_returns_info(self, db_session):
        """get_user_quota 返回 QuotaInfo，含 remaining / is_valid"""
        uid = _make_uid()
        _create_quota(db_session, uid, daily_limit=10, monthly_limit=100, daily_used=3, monthly_used=20)

        svc = ImageGenQuotaService(db_session)
        info = svc.get_user_quota(uid)
        assert info is not None
        assert info.daily_limit == 10
        assert info.daily_used == 3
        assert info.daily_remaining == 7
        assert info.monthly_limit == 100
        assert info.monthly_used == 20
        assert info.monthly_remaining == 80
        assert info.is_valid is True

    def test_get_user_quota_returns_none(self, db_session):
        """无配额用户 → 返回 None"""
        uid = _make_uid()
        svc = ImageGenQuotaService(db_session)
        info = svc.get_user_quota(uid)
        assert info is None
