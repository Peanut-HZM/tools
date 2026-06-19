"""APScheduler 守护：每天 00:05 自动同步 ccusage 数据。"""
import asyncio
import logging
import os
from datetime import date

from sqlalchemy import func

from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord
from app.services.token_usage_sync_service import sync_token_usage_v2
from app.utils.device_id import get_device_id, get_device_display_name

logger = logging.getLogger(__name__)

_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"

_sync_lock = asyncio.Lock()
_scheduler = None


def get_sync_lock() -> asyncio.Lock:
    return _sync_lock


def init_scheduler():
    """初始化并启动 APScheduler。桌面模式直接返回 None。"""
    global _scheduler

    if _DESKTOP_MODE:
        logger.info("[ccusage-scheduler] 桌面模式，跳过 scheduler 启动")
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _daily_sync_job,
        CronTrigger(hour=0, minute=5),
        id="daily_ccusage_sync",
        name="Daily ccusage sync at 00:05",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("[ccusage-scheduler] 启动成功，每天 00:05 触发")
    return _scheduler


def shutdown_scheduler():
    """关闭 scheduler。"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[ccusage-scheduler] 已关闭")


async def _daily_sync_job():
    """00:05 自动任务：同步当天 ccusage 数据。"""
    if _sync_lock.locked():
        logger.warning("[ccusage-daily] 同步进行中，跳过本次触发")
        return

    async with _sync_lock:
        try:
            today = date.today().isoformat()
            count = await asyncio.to_thread(_sync_today, today)
            logger.info(f"[ccusage-daily] 自动同步 {today} 完成: {count} 条")
        except Exception as e:
            logger.error(f"[ccusage-daily] 自动同步失败: {e}", exc_info=True)


def _resolve_scheduler_user_id(db) -> str:
    """解析 scheduler 同步用的 user_id。"""
    env_user = os.environ.get("SCHEDULER_USER_ID")
    if env_user:
        return env_user

    top_user = db.query(TokenUsageRecord.user_id, func.count().label("c")).group_by(
        TokenUsageRecord.user_id
    ).order_by(func.count().desc()).first()
    if top_user:
        return top_user[0]

    return "system"


def _sync_today(date_str: str) -> dict:
    """同步指定日期数据（同步函数，run in thread）。"""
    db = SessionLocal()
    try:
        return sync_token_usage_v2(
            db=db,
            user_id=_resolve_scheduler_user_id(db),
            device_id=get_device_id(),
            device_name=get_device_display_name(),
            since=date_str,
            until=date_str,
        )
    finally:
        db.close()