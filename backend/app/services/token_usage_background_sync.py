"""Token Usage 后台定时同步服务。"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import suppress

from app.config.config import settings
from app.models.base import SessionLocal
from app.models.token_usage_models import (
    DeviceRegistry,
    TokenUsageRecord,
    TokenUsageSyncLog,
)
from app.services.token_usage_cache import (
    acquire_refresh_lock,
    invalidate_user_query_cache,
    release_refresh_lock,
    warm_query_cache,
)
from app.services.token_usage_sync_service import sync_token_usage
from app.utils.device_id import get_device_id

logger = logging.getLogger(__name__)

_pending_sync_users: set[str] = set()
_background_task: asyncio.Task | None = None


def register_pending_sync_user(user_id: str | None) -> None:
    """登记需要后台同步的用户，不执行 CLI，避免阻塞首屏查询。"""
    if not user_id or user_id == "system":
        return
    _pending_sync_users.add(user_id)


def get_pending_sync_users() -> set[str]:
    """返回待同步用户集合副本，供测试和日志使用。"""
    return set(_pending_sync_users)


def clear_pending_sync_users() -> None:
    """清空待同步用户集合，供测试使用。"""
    _pending_sync_users.clear()


def _normalize_user_ids(user_ids: set[str]) -> set[str]:
    """过滤无效用户，避免后台任务同步系统或空用户。"""
    return {user_id for user_id in user_ids if user_id and user_id != "system"}


def _discover_token_usage_user_ids(max_users: int) -> list[str]:
    """发现本轮需要同步的用户。"""
    current_device_id = get_device_id()
    db = SessionLocal()
    try:
        user_ids = set(_pending_sync_users)

        device_rows = (
            db.query(DeviceRegistry.user_id)
            .filter(DeviceRegistry.device_id == current_device_id)
            .distinct()
            .all()
        )
        user_ids.update(row[0] for row in device_rows)

        record_rows = (
            db.query(TokenUsageRecord.user_id)
            .filter(TokenUsageRecord.user_id.isnot(None))
            .distinct()
            .all()
        )
        user_ids.update(row[0] for row in record_rows)

        log_rows = (
            db.query(TokenUsageSyncLog.user_id)
            .filter(TokenUsageSyncLog.user_id.isnot(None))
            .distinct()
            .all()
        )
        user_ids.update(row[0] for row in log_rows)

        return sorted(_normalize_user_ids(user_ids))[:max_users]
    except Exception as exc:
        logger.warning(
            "获取 Token Usage 后台同步用户失败: %s",
            exc,
            exc_info=True,
        )
        return sorted(_normalize_user_ids(set(_pending_sync_users)))[:max_users]
    finally:
        db.close()


def run_background_sync_once(days: int, max_users: int) -> dict[str, list[str]]:
    """执行一轮后台同步，单元测试可直接调用。"""
    started_at = time.perf_counter()
    user_ids = _discover_token_usage_user_ids(max_users=max_users)
    result = {"synced_users": [], "skipped_users": [], "failed_users": []}

    if not user_ids:
        logger.info("Token Usage 后台同步跳过: 没有待同步用户")
        return result

    logger.info("Token Usage 后台同步开始: users=%s, days=%s", len(user_ids), days)

    for user_id in user_ids:
        user_started = time.perf_counter()
        owner = str(uuid.uuid4())
        lock = acquire_refresh_lock(user_id, owner)
        if not lock.get("acquired"):
            logger.info(
                "Token Usage 后台同步跳过用户 %s: 已有刷新任务, ttl=%s",
                user_id,
                lock.get("ttl_seconds"),
            )
            result["skipped_users"].append(user_id)
            continue

        try:
            sync_result = sync_token_usage(user_id=user_id, days=days)
            invalidate_user_query_cache(user_id)
            warm_query_cache(user_id)
            result["synced_users"].append(user_id)
            user_elapsed_ms = int((time.perf_counter() - user_started) * 1000)
            logger.info(
                "Token Usage 后台同步完成: user=%s, records=%s, errors=%s, elapsed_ms=%s",
                user_id,
                sync_result.get("total_records"),
                len(sync_result.get("errors") or []),
                user_elapsed_ms,
            )
        except Exception as exc:
            result["failed_users"].append(user_id)
            user_elapsed_ms = int((time.perf_counter() - user_started) * 1000)
            logger.warning(
                "Token Usage 后台同步失败: user=%s, error=%s, elapsed_ms=%s",
                user_id,
                exc,
                user_elapsed_ms,
                exc_info=True,
            )
        finally:
            release_refresh_lock(user_id, owner)

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Token Usage 后台同步本轮结束: synced=%s, skipped=%s, failed=%s, elapsed_ms=%s",
        len(result["synced_users"]),
        len(result["skipped_users"]),
        len(result["failed_users"]),
        elapsed_ms,
    )
    return result


async def _background_sync_loop() -> None:
    """后台定时同步循环。"""
    logger.info(
        "Token Usage 后台同步任务启动: enabled=%s, interval=%s, days=%s, "
        "initial_delay=%s, max_users=%s",
        settings.TOKEN_USAGE_BACKGROUND_SYNC_ENABLED,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_DAYS,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN,
    )

    await asyncio.sleep(settings.TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS)

    while True:
        try:
            await asyncio.to_thread(
                run_background_sync_once,
                settings.TOKEN_USAGE_BACKGROUND_SYNC_DAYS,
                settings.TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Token Usage 后台同步循环异常: %s", exc, exc_info=True)

        await asyncio.sleep(settings.TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS)


def start_background_sync_task() -> asyncio.Task | None:
    """启动后台同步任务。"""
    global _background_task

    if not settings.TOKEN_USAGE_BACKGROUND_SYNC_ENABLED:
        logger.info("Token Usage 后台同步任务已禁用")
        return None

    if _background_task and not _background_task.done():
        logger.info("Token Usage 后台同步任务已存在，跳过重复启动")
        return _background_task

    _background_task = asyncio.create_task(_background_sync_loop())
    return _background_task


async def stop_background_sync_task() -> None:
    """停止后台同步任务。"""
    global _background_task

    task = _background_task
    if not task:
        return

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    logger.info("Token Usage 后台同步任务已停止")
    _background_task = None
