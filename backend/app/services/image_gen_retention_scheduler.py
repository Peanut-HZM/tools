"""APScheduler 守护：每天按计划自动清理过期的图像生成 OSS 文件。"""
import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.base import SessionLocal
from app.services.oss_retention_service import OssRetentionService
from app.utils.image_gen_constants import DEFAULT_CLEANUP_CRON

logger = logging.getLogger(__name__)

_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"

_scheduler = None


def _parse_cron_expression(expr: str) -> CronTrigger:
    """解析 cron 表达式为 CronTrigger；解析失败时回退到默认每天 02:00。"""
    try:
        return CronTrigger.from_crontab(expr)
    except Exception as e:
        logger.warning(
            f"[image-gen-retention-scheduler] cron 表达式解析失败 '{expr}'，"
            f"回退到默认 02:00: {e}"
        )
        return CronTrigger(hour=2, minute=0)


def init_retention_scheduler():
    """初始化并启动 image-gen 保留策略定时任务。桌面模式直接返回 None。"""
    global _scheduler

    if _DESKTOP_MODE:
        logger.info("[image-gen-retention-scheduler] 桌面模式，跳过 scheduler 启动")
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    # 从 DB 读取 cron 表达式（无配置时使用默认值）
    cron_expr = DEFAULT_CLEANUP_CRON
    try:
        db = SessionLocal()
        try:
            from app.models.image_generation_models import ImageGenRetentionConfig

            config = db.query(ImageGenRetentionConfig).first()
            if config and config.cleanup_cron:
                cron_expr = config.cleanup_cron
        finally:
            db.close()
    except Exception as e:
        logger.warning(
            f"[image-gen-retention-scheduler] 读取 DB cron 配置失败，使用默认值: {e}"
        )

    trigger = _parse_cron_expression(cron_expr)

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _cleanup_job,
        trigger,
        id="image_gen_retention_cleanup",
        name="Daily image-gen retention cleanup",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        f"[image-gen-retention-scheduler] 启动成功，cron='{cron_expr}'"
    )
    return _scheduler


def shutdown_retention_scheduler():
    """关闭 scheduler。"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[image-gen-retention-scheduler] 已关闭")


async def _cleanup_job():
    """定时清理任务：创建 DB 会话与 OssService，执行 run_cleanup。"""
    db = SessionLocal()
    try:
        from app.services.oss_service import OssService

        oss_svc = OssService()
        retention_svc = OssRetentionService(db, oss_svc)
        result = await asyncio.to_thread(retention_svc.run_cleanup)
        logger.info(f"[image-gen-retention] 定时清理完成: {result}")
    except Exception as e:
        logger.error(
            f"[image-gen-retention] 定时清理失败: {e}", exc_info=True
        )
    finally:
        db.close()
