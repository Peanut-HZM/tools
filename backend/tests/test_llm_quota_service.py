# backend/tests/test_llm_quota_service.py
"""LLMQuotaService 单元测试"""
from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import InvalidQuotaMode, QuotaExceeded
from app.models.llm_quota_models import LLMUserQuota, LLMUsageLog
from app.services.llm_quota_service import LLMQuotaService, QuotaInfo


def _make_db_with_quota(quota: LLMUserQuota | None) -> MagicMock:
    """构造 mock DB session + 一次 query().filter().first() 返回 quota"""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = quota
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = quota
    return db


def test_check_and_reserve_no_quota_raises():
    db = _make_db_with_quota(None)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    with pytest.raises(QuotaExceeded) as exc:
        svc.check_and_reserve("user-1", "text", 100)
    assert str(exc.value) == "no_quota"


def test_check_and_reserve_count_increments_daily():
    quota = LLMUserQuota(
        user_id="u1",
        quota_mode="count",
        daily_limit=10,
        daily_used=0,
        daily_reset_date=datetime.now(timezone.utc),
        monthly_limit=300,
        monthly_used=0,
        monthly_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    res_id = svc.check_and_reserve("u1", "image", 0)
    assert isinstance(res_id, str) and len(res_id) > 0
    assert quota.daily_used == 1
    assert quota.monthly_used == 1


def test_check_and_reserve_count_daily_limit_exceeded():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="count",
        daily_limit=1, daily_used=1,
        daily_reset_date=datetime.now(timezone.utc),
        monthly_limit=300, monthly_used=0,
        monthly_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    with pytest.raises(QuotaExceeded) as exc:
        svc.check_and_reserve("u1", "image", 0)
    assert str(exc.value) == "daily_limit_exceeded"


def test_check_and_reserve_token_reserves_planned():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="token",
        token_period="monthly", token_limit=10000, token_used=0,
        token_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    res_id = svc.check_and_reserve("u1", "text", 500)
    assert quota.token_used == 500
    assert svc._reservations[res_id]["planned_tokens"] == 500


def test_check_and_reserve_token_limit_exceeded():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="token",
        token_period="total", token_limit=100, token_used=99,
        token_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    with pytest.raises(QuotaExceeded) as exc:
        svc.check_and_reserve("u1", "text", 10)
    assert str(exc.value) == "token_limit_exceeded"


def test_check_and_reserve_time_validity_expired():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="time",
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2020, 12, 31, tzinfo=timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    with pytest.raises(QuotaExceeded) as exc:
        svc.check_and_reserve("u1", "text", 0)
    assert str(exc.value) == "validity_expired"


def test_record_usage_token_corrects_to_actual():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="token",
        token_period="monthly", token_limit=10000, token_used=500,  # 已预留 500
        token_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    # 手动塞 reservation
    svc._reservations["res-1"] = {"user_id": "u1", "planned_tokens": 500, "category": "text"}
    svc.record_usage("u1", "text", actual_tokens=300, reservation_id="res-1", model_used="qwen-max")
    assert quota.token_used == 300  # 校正：500 - 500 + 300
    # 验证 usage_log 被写入
    db.add.assert_called_once()
    log_obj = db.add.call_args[0][0]
    assert isinstance(log_obj, LLMUsageLog)
    assert log_obj.tokens_used == 300


def test_rollback_token_restores_planned():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="token",
        token_period="monthly", token_limit=10000, token_used=500,
        token_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    svc._reservations["res-1"] = {"user_id": "u1", "planned_tokens": 500, "category": "text"}
    svc.rollback("res-1")
    assert quota.token_used == 0


def test_rollback_count_decrements_daily():
    quota = LLMUserQuota(
        user_id="u1", quota_mode="count",
        daily_limit=10, daily_used=1,  # check_and_reserve 已 +1
        daily_reset_date=datetime.now(timezone.utc),
        monthly_limit=300, monthly_used=1,
        monthly_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(quota)
    svc = LLMQuotaService(db, _test_lock=threading.Lock())
    svc._reservations["res-1"] = {"user_id": "u1", "planned_tokens": 0, "category": "image"}
    svc.rollback("res-1")
    assert quota.daily_used == 0
    assert quota.monthly_used == 0


def test_get_user_quota_none_when_missing():
    db = _make_db_with_quota(None)
    svc = LLMQuotaService(db)
    assert svc.get_user_quota("user-1") is None


def test_grant_count_validates_have_limit():
    db = _make_db_with_quota(None)
    svc = LLMQuotaService(db)
    with pytest.raises(InvalidQuotaMode) as exc:
        svc.grant(user_id="u1", quota_mode="count", daily_limit=0, monthly_limit=0)
    assert "count 模式" in str(exc.value)


def test_grant_token_validates_have_limit():
    db = _make_db_with_quota(None)
    svc = LLMQuotaService(db)
    with pytest.raises(InvalidQuotaMode):
        svc.grant(user_id="u1", quota_mode="token", token_limit=0, token_period="monthly")


def test_grant_time_validates_validity():
    db = _make_db_with_quota(None)
    svc = LLMQuotaService(db)
    with pytest.raises(InvalidQuotaMode):
        svc.grant(user_id="u1", quota_mode="time", valid_from=None, valid_until=None)


def test_grant_count_creates_new_record():
    db = _make_db_with_quota(None)  # 首次 grant 时无现有记录
    svc = LLMQuotaService(db)
    info = svc.grant(
        user_id="u1", quota_mode="count",
        daily_limit=10, monthly_limit=300,
        granted_by="admin", notes="测试",
    )
    assert info.quota_mode == "count"
    assert info.daily_limit == 10
    assert db.add.called
    db.commit.assert_called()


def test_grant_count_overwrites_existing():
    existing = LLMUserQuota(
        user_id="u1", quota_mode="count",
        daily_limit=5, daily_used=2,
        daily_reset_date=datetime.now(timezone.utc),
        monthly_limit=100, monthly_used=10,
        monthly_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(existing)
    svc = LLMQuotaService(db)
    info = svc.grant(user_id="u1", quota_mode="count", daily_limit=20, monthly_limit=500)
    assert info.daily_limit == 20
    assert existing.daily_used == 2  # 保留已用


def test_revoke_deletes_row():
    existing = LLMUserQuota(user_id="u1", quota_mode="count", daily_limit=1, daily_used=0, daily_reset_date=datetime.now(timezone.utc), monthly_limit=1, monthly_used=0, monthly_reset_date=datetime.now(timezone.utc))
    db = _make_db_with_quota(existing)
    svc = LLMQuotaService(db)
    svc.revoke("u1")
    db.delete.assert_called_once_with(existing)


def test_reset_counters_zeroes_used():
    existing = LLMUserQuota(
        user_id="u1", quota_mode="count",
        daily_limit=10, daily_used=5,
        daily_reset_date=datetime.now(timezone.utc),
        monthly_limit=300, monthly_used=100,
        monthly_reset_date=datetime.now(timezone.utc),
    )
    db = _make_db_with_quota(existing)
    svc = LLMQuotaService(db)
    svc.reset_counters("u1")
    assert existing.daily_used == 0
    assert existing.monthly_used == 0
