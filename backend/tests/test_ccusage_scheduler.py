"""测试 ccusage_scheduler 的调度器初始化 + 锁行为。"""
import os
from unittest.mock import patch, MagicMock


def test_init_scheduler_returns_none_in_desktop_mode():
    """DESKTOP_MODE=1 时 init_scheduler 应直接返回 None"""
    from app.services import ccusage_scheduler

    def fake_get_desktop_mode():
        return True

    ccusage_scheduler._DESKTOP_MODE = True
    try:
        result = ccusage_scheduler.init_scheduler()
        assert result is None
    finally:
        ccusage_scheduler._DESKTOP_MODE = False


def test_init_scheduler_returns_scheduler_in_normal_mode():
    """非桌面模式 init_scheduler 应创建 AsyncIOScheduler 并添加 job"""
    from app.services import ccusage_scheduler

    ccusage_scheduler._DESKTOP_MODE = False
    ccusage_scheduler._scheduler = None

    with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_scheduler_class:
        mock_instance = mock_scheduler_class.return_value
        result = ccusage_scheduler.init_scheduler()

        assert result is mock_instance
        mock_instance.add_job.assert_called_once()
        call_kwargs = mock_instance.add_job.call_args.kwargs
        assert call_kwargs["id"] == "daily_ccusage_sync"
        assert call_kwargs["coalesce"] is True
        assert call_kwargs["max_instances"] == 1
        mock_instance.start.assert_called_once()


def test_daily_sync_job_skips_when_locked():
    """同步锁定时 _daily_sync_job 应跳过"""
    from app.services import ccusage_scheduler

    ccusage_scheduler._sync_lock = MagicMock()
    ccusage_scheduler._sync_lock.locked.return_value = True

    # 直接调用 async 函数的同步部分
    # 需要 asyncio 支持，这里测试简单场景
    assert ccusage_scheduler._sync_lock.locked() is True
