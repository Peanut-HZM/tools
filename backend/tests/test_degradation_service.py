"""
Task 9.1 — DegradationService 单元测试

使用 SQLite 内存 DB，每个用例一个干净 session。
覆盖范围：
  ✓ 初始状态未降级
  ✓ 低于阈值不触发降级
  ✓ 达到阈值触发降级
  ✓ 时间到期自动解除（monkeypatch datetime）
  ✓ record_success 重置计数但不解除降级
  ✓ 手动 reset 解除降级
  ✓ get_status 返回正确结构
  ✓ update_config 持久化到 DB
  ✓ 多线程并发 record_failure 串行化（无 race）
  ✓ DB 无配置时自动创建默认值
  ✓ enabled=False 时降级机制完全失效
"""

import sys
import threading
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_generation_models import ImageGenDegradationConfig

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.degradation_service import DegradationService


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB（允许跨线程使用，便于并发测试）"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def svc(db_session):
    """构造 DegradationService 实例"""
    return DegradationService(db_session)


def _insert_config(
    session,
    enabled: bool = True,
    failure_threshold: int = 3,
    degrade_duration_seconds: int = 300,
) -> ImageGenDegradationConfig:
    """直接插入一条降级配置（便于定制阈值/时长）"""
    cfg = ImageGenDegradationConfig(
        enabled=enabled,
        failure_threshold=failure_threshold,
        degrade_duration_seconds=degrade_duration_seconds,
        updated_by="test",
    )
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg


# ============================================================
# 初始状态
# ============================================================

def test_initial_state_not_degraded(svc):
    """新实例 → is_degraded = False，failure_count = 0"""
    assert svc.is_degraded() is False
    status = svc.get_status()
    assert status["degraded"] is False
    assert status["failure_count"] == 0


# ============================================================
# record_failure 阈值触发
# ============================================================

def test_record_failure_below_threshold(svc, db_session):
    """failure_threshold=3，调用 record_failure 2 次 → 仍 not degraded"""
    _insert_config(db_session, failure_threshold=3, degrade_duration_seconds=60)
    # 重新构造 service（配置已写入）
    svc2 = DegradationService(db_session)

    svc2.record_failure()
    svc2.record_failure()

    assert svc2.is_degraded() is False
    assert svc2.get_status()["failure_count"] == 2


def test_record_failure_at_threshold_triggers_degradation(svc, db_session):
    """failure_threshold=3，第 3 次 → is_degraded = True"""
    _insert_config(db_session, failure_threshold=3, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    for _ in range(3):
        svc2.record_failure()

    assert svc2.is_degraded() is True
    status = svc2.get_status()
    assert status["degraded"] is True
    assert status["failure_count"] == 3
    assert status["degraded_until"] is not None


# ============================================================
# 自动解除
# ============================================================

def test_degradation_auto_unblocks_after_time(svc, db_session):
    """手动设置 _degraded_until 到过去 → is_degraded 自动返回 False 且计数清零"""
    _insert_config(db_session, failure_threshold=3, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    # 直接注入一个"已过期"的降级时间点（模拟时间流逝）
    past_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    svc2._degraded_until = past_time
    svc2._failure_count = 5

    # 此时查询应自动解除
    assert svc2.is_degraded() is False
    # 内部状态应被清理
    assert svc2._failure_count == 0
    assert svc2._degraded_until is None


# ============================================================
# record_success
# ============================================================

def test_record_success_resets_failure_count(svc, db_session):
    """3 failures + success → failure_count=0，再失败 2 次 → 未达阈值"""
    _insert_config(db_session, failure_threshold=5, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    for _ in range(3):
        svc2.record_failure()
    assert svc2.get_status()["failure_count"] == 3

    svc2.record_success()
    assert svc2.get_status()["failure_count"] == 0

    # 再失败 2 次（< 阈值 5）
    for _ in range(2):
        svc2.record_failure()
    assert svc2.is_degraded() is False
    assert svc2.get_status()["failure_count"] == 2


def test_record_success_does_not_un_degrade(svc, db_session):
    """已降级 → record_success → 仍 degraded（直到时间到）"""
    _insert_config(db_session, failure_threshold=2, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    # 触发降级
    svc2.record_failure()
    svc2.record_failure()
    assert svc2.is_degraded() is True

    # 成功一次 → 计数清零，但降级不解除
    svc2.record_success()
    assert svc2.get_status()["failure_count"] == 0
    assert svc2.is_degraded() is True  # 关键：仍然降级


# ============================================================
# 手动 reset
# ============================================================

def test_manual_reset_unblocks_degradation(svc, db_session):
    """已降级 → reset() → not degraded，failure_count 清零"""
    _insert_config(db_session, failure_threshold=2, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    svc2.record_failure()
    svc2.record_failure()
    assert svc2.is_degraded() is True

    svc2.reset()
    assert svc2.is_degraded() is False
    assert svc2.get_status()["failure_count"] == 0
    assert svc2.get_status()["degraded_until"] is None


# ============================================================
# get_status
# ============================================================

def test_get_status_returns_current_state(svc, db_session):
    """返回正确的 degraded / failure_count / threshold / duration / enabled 字段"""
    cfg = _insert_config(
        db_session,
        failure_threshold=4,
        degrade_duration_seconds=120,
    )
    svc2 = DegradationService(db_session)

    svc2.record_failure()
    svc2.record_failure()

    status = svc2.get_status()
    assert status["degraded"] is False
    assert status["enabled"] is True
    assert status["failure_count"] == 2
    assert status["failure_threshold"] == 4
    assert status["degrade_duration_seconds"] == 120
    assert status["degraded_until"] is None


# ============================================================
# update_config
# ============================================================

def test_update_config_persists_to_db(svc, db_session):
    """update_config 后，新 session 读到的配置值已更新"""
    _insert_config(db_session)  # 默认 threshold=3
    svc2 = DegradationService(db_session)

    updated = svc2.update_config(
        failure_threshold=10,
        degrade_duration_seconds=600,
        updated_by="admin",
    )
    assert updated.failure_threshold == 10
    assert updated.degrade_duration_seconds == 600
    assert updated.updated_by == "admin"

    # 重新查询 DB 验证持久化
    fresh = db_session.query(ImageGenDegradationConfig).first()
    assert fresh.failure_threshold == 10
    assert fresh.degrade_duration_seconds == 600


def test_update_config_partial(svc, db_session):
    """部分更新：只传 failure_threshold，其他字段保持不变"""
    _insert_config(db_session, failure_threshold=3, degrade_duration_seconds=300)
    svc2 = DegradationService(db_session)

    svc2.update_config(failure_threshold=7)
    fresh = db_session.query(ImageGenDegradationConfig).first()
    assert fresh.failure_threshold == 7
    assert fresh.degrade_duration_seconds == 300  # 未变


# ============================================================
# 并发
# ============================================================

def test_concurrent_record_failure_serializable(svc, db_session):
    """10 线程各 record_failure 10 次 → 最终 failure_count 精确等于 100（无 race）"""
    _insert_config(db_session, failure_threshold=1000, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    n_threads = 10
    n_ops = 10
    barriers = {"count": 0, "lock": threading.Lock()}

    def worker():
        for _ in range(n_ops):
            svc2.record_failure()
        with barriers["lock"]:
            barriers["count"] += 1

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 全部完成
    assert barriers["count"] == n_threads
    # 计数精确 = n_threads * n_ops
    assert svc2.get_status()["failure_count"] == n_threads * n_ops


# ============================================================
# 默认配置
# ============================================================

def test_config_default_created_if_missing(svc, db_session):
    """DB 无配置行 → _get_config 自动创建默认值"""
    # 初始 DB 为空
    assert db_session.query(ImageGenDegradationConfig).count() == 0

    cfg = svc.get_config()
    assert cfg is not None
    assert cfg.failure_threshold == 3
    assert cfg.degrade_duration_seconds == 300
    assert cfg.enabled is True

    # 再次查询 → 只有一行
    assert db_session.query(ImageGenDegradationConfig).count() == 1
    # 幂等
    cfg2 = svc.get_config()
    assert cfg2.id == cfg.id


# ============================================================
# enabled=False 行为
# ============================================================

def test_enabled_false_disables_degradation(svc, db_session):
    """enabled=False → is_degraded 永远返回 False，record_failure 不累积计数"""
    _insert_config(db_session, enabled=False, failure_threshold=1, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    # 即使阈值=1，也不触发
    svc2.record_failure()
    svc2.record_failure()
    assert svc2.is_degraded() is False
    assert svc2.get_status()["failure_count"] == 0
    assert svc2.get_status()["enabled"] is False


def test_enabled_toggle_off_clears_degradation(svc, db_session):
    """降级中 → admin 把 enabled 设为 False → is_degraded 返回 False 并清理状态"""
    _insert_config(db_session, enabled=True, failure_threshold=1, degrade_duration_seconds=60)
    svc2 = DegradationService(db_session)

    svc2.record_failure()
    assert svc2.is_degraded() is True

    # admin 关闭
    svc2.update_config(enabled=False)
    assert svc2.is_degraded() is False
    # 内部状态应被清理
    assert svc2._failure_count == 0
    assert svc2._degraded_until is None
