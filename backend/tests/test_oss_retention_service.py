"""OssRetentionService 单元测试。

使用 SQLite 内存数据库 + mock OssService，覆盖：
- by_date 模式按 created_at 清理
- by_unused 模式按 last_accessed_at 清理
- disabled 配置跳过清理
- OSS 删除失败时不中断整体流程
- 已删除记录不被重复处理
- keep_forever 模式跳过清理
- 未知模式跳过清理
- 配置 CRUD 及默认值创建
- run_cleanup 返回摘要字典结构正确
- 无 result_oss_key 的记录仍可标记删除
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 让测试能导入 backend/app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base
from app.models.image_generation_models import (
    ImageGenHistory,
    ImageGenRetentionConfig,
)
from app.services.oss_retention_service import OssRetentionService
from app.utils.image_gen_constants import (
    RETENTION_MODE_KEEP_FOREVER,
    RETENTION_MODE_DELETE_AFTER_N_DAYS,
    RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def db_session():
    """创建内存 SQLite 数据库会话，每个测试结束后销毁表。"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class MockOssService:
    """模拟 OssService，记录 delete_file 调用并支持注入失败。"""

    def __init__(self, should_fail_for_keys=None):
        self.deleted_keys = []
        self._should_fail_for_keys = set(should_fail_for_keys or [])

    def delete_file(self, key):
        self.deleted_keys.append(key)
        if key in self._should_fail_for_keys:
            raise RuntimeError(f"模拟 OSS 删除失败: {key}")
        return True


def _make_history(
    db_session,
    created_at=None,
    last_accessed_at=None,
    result_oss_key="image-gen/result/test.png",
    is_deleted=False,
):
    """插入一条 ImageGenHistory 测试记录。"""
    record = ImageGenHistory(
        id=str(uuid.uuid4()),
        user_id="test-user",
        operation="text2img",
        result_oss_key=result_oss_key,
        status="success",
        created_at=created_at or datetime.utcnow(),
        last_accessed_at=last_accessed_at,
        is_deleted=is_deleted,
    )
    db_session.add(record)
    db_session.commit()
    return record


# ============================================================
# 测试用例
# ============================================================


def _ensure_config(db_session, mode=None, n_days=30, enabled=True):
    """确保 DB 中存在配置行并设置指定参数；返回该配置对象。"""
    svc = OssRetentionService(db_session, MockOssService())
    cfg = svc.get_config()  # 不存在则自动创建默认
    if mode is not None:
        cfg.mode = mode
    cfg.n_days = n_days
    cfg.enabled = enabled
    db_session.commit()
    return cfg


class TestRunCleanupByDate:
    """by_date 模式测试（按 created_at）。"""

    def test_deletes_old_records(self, db_session):
        """超过保留期限的记录应被标记为 is_deleted=True。"""
        # 一条 60 天前的旧记录
        _make_history(
            db_session,
            created_at=datetime.utcnow() - timedelta(days=60),
        )
        # 将配置更新为 by_date 模式，保留 30 天
        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        assert result["deleted_count"] == 1
        assert result["failed_count"] == 0
        assert result["skipped"] is False
        # DB 记录被标记为已删除
        remaining = (
            db_session.query(ImageGenHistory)
            .filter(ImageGenHistory.is_deleted == True)  # noqa: E712
            .count()
        )
        assert remaining == 1

    def test_keeps_recent_records(self, db_session):
        """保留期限内的记录不应被处理。"""
        _make_history(
            db_session,
            created_at=datetime.utcnow() - timedelta(days=5),
        )
        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        assert result["deleted_count"] == 0
        # DB 记录保持 is_deleted=False
        active = (
            db_session.query(ImageGenHistory)
            .filter(ImageGenHistory.is_deleted == False)  # noqa: E712
            .count()
        )
        assert active == 1


class TestRunCleanupByUnused:
    """by_unused 模式测试（按 last_accessed_at）。"""

    def test_uses_last_accessed_at(self, db_session):
        """by_unused 模式应以 last_accessed_at 为判断基准。"""
        # last_accessed_at 40 天前 → 应被清理
        _make_history(
            db_session,
            created_at=datetime.utcnow() - timedelta(days=10),
            last_accessed_at=datetime.utcnow() - timedelta(days=40),
        )
        # last_accessed_at 5 天前 → 应保留
        _make_history(
            db_session,
            created_at=datetime.utcnow() - timedelta(days=60),
            last_accessed_at=datetime.utcnow() - timedelta(days=5),
        )
        _ensure_config(
            db_session, mode=RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS, n_days=30
        )

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        assert result["deleted_count"] == 1
        assert result["mode"] == RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS


class TestSkipConditions:
    """跳过清理的各种场景。"""

    def test_skips_when_disabled(self, db_session):
        """enabled=False 时应跳过清理。"""
        _make_history(
            db_session,
            created_at=datetime.utcnow() - timedelta(days=100),
        )
        _ensure_config(
            db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30, enabled=False
        )

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        assert result["skipped"] is True
        assert result["reason"] == "disabled"
        assert result["deleted_count"] == 0

    def test_skips_keep_forever_mode(self, db_session):
        """keep_forever 模式应跳过清理。"""
        _make_history(
            db_session,
            created_at=datetime.utcnow() - timedelta(days=100),
        )
        _ensure_config(db_session, mode=RETENTION_MODE_KEEP_FOREVER)

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        assert result["skipped"] is True
        assert result["reason"] == "keep_forever"
        assert result["deleted_count"] == 0

    def test_skips_unknown_mode(self, db_session):
        """未知模式应跳过清理并返回 unknown_mode。"""
        _ensure_config(db_session, mode="some_unknown_mode")

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        assert result["skipped"] is True
        assert result["reason"] == "unknown_mode"


class TestOssFailureHandling:
    """OSS 删除失败场景。"""

    def test_oss_delete_failure_continues(self, db_session):
        """单条 OSS 删除失败应计入 failed_count，不影响其他记录。"""
        old = datetime.utcnow() - timedelta(days=60)
        _make_history(db_session, created_at=old, result_oss_key="key/ok1.png")
        _make_history(
            db_session, created_at=old, result_oss_key="key/fail.png"
        )
        _make_history(db_session, created_at=old, result_oss_key="key/ok2.png")

        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        mock_oss = MockOssService(should_fail_for_keys={"key/fail.png"})
        svc = OssRetentionService(db_session, mock_oss)
        result = svc.run_cleanup()

        assert result["deleted_count"] == 2
        assert result["failed_count"] == 1
        # 失败的记录不应被标记为 is_deleted
        failed_record = (
            db_session.query(ImageGenHistory)
            .filter(ImageGenHistory.result_oss_key == "key/fail.png")
            .first()
        )
        assert failed_record.is_deleted is False
        # 成功的记录应被标记
        ok_record = (
            db_session.query(ImageGenHistory)
            .filter(ImageGenHistory.result_oss_key == "key/ok1.png")
            .first()
        )
        assert ok_record.is_deleted is True


class TestAlreadyDeleted:
    """已删除记录处理。"""

    def test_ignores_already_deleted_records(self, db_session):
        """is_deleted=True 的记录不应被再次处理。"""
        old = datetime.utcnow() - timedelta(days=60)
        _make_history(
            db_session, created_at=old, is_deleted=True,
            result_oss_key="key/already_gone.png",
        )
        _make_history(
            db_session, created_at=old, is_deleted=False,
            result_oss_key="key/active.png",
        )

        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        mock_oss = MockOssService()
        svc = OssRetentionService(db_session, mock_oss)
        result = svc.run_cleanup()

        # 只处理了 1 条（未删除的那条）
        assert result["deleted_count"] == 1
        assert "key/already_gone.png" not in mock_oss.deleted_keys
        assert "key/active.png" in mock_oss.deleted_keys


class TestConfigCrud:
    """配置 CRUD 测试。"""

    def test_get_config_returns_db_config(self, db_session):
        """get_config 应返回 DB 中已有的配置。"""
        svc = OssRetentionService(db_session, MockOssService())
        existing = svc.get_config()
        existing.mode = RETENTION_MODE_DELETE_AFTER_N_DAYS
        existing.n_days = 60
        db_session.commit()

        config = svc.get_config()

        assert config.mode == RETENTION_MODE_DELETE_AFTER_N_DAYS
        assert config.n_days == 60

    def test_update_config_persists(self, db_session):
        """update_config 应持久化变更。"""
        svc = OssRetentionService(db_session, MockOssService())
        svc.update_config(
            mode=RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS,
            retention_days=14,
            cron_expression="0 4 * * *",
            enabled=False,
        )

        # 重新读取
        fresh = db_session.query(ImageGenRetentionConfig).first()
        assert fresh.mode == RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS
        assert fresh.n_days == 14
        assert fresh.cleanup_cron == "0 4 * * *"
        assert fresh.enabled is False

    def test_default_config_created_if_missing(self, db_session):
        """DB 无配置时应自动创建默认配置。"""
        # 清空现有配置
        db_session.query(ImageGenRetentionConfig).delete()
        db_session.commit()

        svc = OssRetentionService(db_session, MockOssService())
        config = svc.get_config()

        assert config is not None
        assert config.mode == RETENTION_MODE_KEEP_FOREVER
        assert config.n_days == 30
        assert config.cleanup_cron == "0 3 * * *"
        assert config.enabled is True


class TestSummaryShape:
    """返回摘要结构校验。"""

    def test_run_cleanup_returns_correct_summary(self, db_session):
        """run_cleanup 返回字典应包含所有必需字段。"""
        old = datetime.utcnow() - timedelta(days=60)
        _make_history(db_session, created_at=old)

        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        svc = OssRetentionService(db_session, MockOssService())
        result = svc.run_cleanup()

        # 必须包含的字段
        expected_keys = {
            "deleted_count",
            "failed_count",
            "skipped",
            "mode",
            "retention_days",
            "cutoff",
        }
        assert set(result.keys()) == expected_keys
        assert result["deleted_count"] == 1
        assert result["failed_count"] == 0
        assert result["skipped"] is False
        assert result["mode"] == RETENTION_MODE_DELETE_AFTER_N_DAYS
        assert result["retention_days"] == 30
        # cutoff 应为 ISO 格式时间字符串
        assert result["cutoff"] is not None
        datetime.fromisoformat(result["cutoff"])


class TestEdgeCases:
    """边界条件。"""

    def test_record_without_oss_key_still_marked_deleted(self, db_session):
        """result_oss_key 为空字符串的记录应直接标记删除，不触发 OSS 调用。

        注：model 中 result_oss_key 为 NOT NULL，此处用空串模拟"无有效 key"的情况，
        OssRetentionService 用 `if record.result_oss_key:` 判断，空串为 falsy。
        """
        old = datetime.utcnow() - timedelta(days=60)
        _make_history(db_session, created_at=old, result_oss_key="")

        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        mock_oss = MockOssService()
        svc = OssRetentionService(db_session, mock_oss)
        result = svc.run_cleanup()

        assert result["deleted_count"] == 1
        assert len(mock_oss.deleted_keys) == 0  # 未调用 OSS

    def test_mixed_success_and_failure_summary(self, db_session):
        """混合成功失败场景下摘要数值正确。"""
        old = datetime.utcnow() - timedelta(days=60)
        _make_history(db_session, created_at=old, result_oss_key="k1.png")
        _make_history(db_session, created_at=old, result_oss_key="k2.png")
        _make_history(db_session, created_at=old, result_oss_key="k3.png")

        _ensure_config(db_session, mode=RETENTION_MODE_DELETE_AFTER_N_DAYS, n_days=30)

        mock_oss = MockOssService(should_fail_for_keys={"k2.png"})
        svc = OssRetentionService(db_session, mock_oss)
        result = svc.run_cleanup()

        assert result["deleted_count"] == 2
        assert result["failed_count"] == 1
        assert result["skipped"] is False
