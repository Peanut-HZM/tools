"""APScheduler 守护：每天 00:05 自动同步 ccusage 数据。"""
import asyncio
import logging
import os
import uuid

from sqlalchemy import func

from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord
from app.services.token_usage_sync_service import sync_token_usage

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
    """00:05 自动任务：滚动同步最近 3 天 ccusage 数据。

    只同步当天会漏掉"跨天后才落盘的昨日用量"（CLI 会话在午夜后仍在写
    前一日日期的 JSONL/SQLite 记录），因此每次回补最近 3 天，靠 upsert
    幂等覆盖，既补齐缺漏又不产生重复。
    """
    if _sync_lock.locked():
        logger.warning("[ccusage-daily] 同步进行中，跳过本次触发")
        return

    async with _sync_lock:
        try:
            count = await asyncio.to_thread(_sync_recent_days, 3)
            logger.info(f"[ccusage-daily] 自动同步最近 3 天完成: {count} 条")
        except Exception as e:
            logger.error(f"[ccusage-daily] 自动同步失败: {e}", exc_info=True)


def _resolve_scheduler_user_id(db) -> str:
    """解析 scheduler 同步用的 user_id。"""
    env_user = os.environ.get("SCHEDULER_USER_ID")
    if env_user:
        return env_user

    # 只在合法 UUID 用户中选记录数最多者，排除历史污染的列名字符串账号
    top_user = (
        db.query(TokenUsageRecord.user_id, func.count().label("c"))
        .filter(TokenUsageRecord.user_id.op("~")("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"))
        .group_by(TokenUsageRecord.user_id)
        .order_by(func.count().desc())
        .first()
    )
    if top_user and _is_uuid(top_user[0]):
        return top_user[0]

    return "system"


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _sync_recent_days(days: int = 3) -> dict:
    """滚动同步最近 N 天全部数据源（ccusage 各 agent + zcode，run in thread）。

    走 v1 全源路径 sync_token_usage：内部已包含 ccusage v2 各 agent 抓取
    与 zcode 本地 SQLite 读取，并完成设备注册。
    """
    db = SessionLocal()
    try:
        user_id = _resolve_scheduler_user_id(db)
    finally:
        db.close()
    if user_id == "system":
        logger.warning("[ccusage-daily] 未找到合法用户，跳过同步")
        return {"sources_synced": [], "total_records": 0, "errors": []}
    return sync_token_usage(user_id=user_id, days=days)