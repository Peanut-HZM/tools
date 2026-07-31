"""Token 统计数据 Redis 缓存服务"""

import json
import logging
import threading
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Optional
import redis
from app.config.config import settings

logger = logging.getLogger(__name__)

# 全局 Redis 客户端连接（使用连接池，线程安全）
_redis_client: Optional[redis.Redis] = None
_redis_lock = threading.Lock()
_last_failed_init_at: float = 0.0
_FAILED_INIT_COOLDOWN = 30.0  # 失败后 30 秒内不重试，避免每次请求都尝试连接


def init_redis() -> Optional[redis.Redis]:
    """初始化 Redis 客户端连接（线程安全，含失败冷却）"""
    global _redis_client, _last_failed_init_at

    with _redis_lock:
        # 已有可用客户端 → 直接返回
        if _redis_client is not None:
            return _redis_client

        # 最近失败过且未过冷却期 → 直接返回 None，避免阻塞
        if _last_failed_init_at and (time.time() - _last_failed_init_at) < _FAILED_INIT_COOLDOWN:
            return None

        try:
            client = redis.Redis(
                host=settings.CACHE_REDIS_HOST,
                port=settings.CACHE_REDIS_PORT,
                db=settings.CACHE_REDIS_DB,
                password=settings.CACHE_REDIS_PASSWORD
                if settings.CACHE_REDIS_PASSWORD
                else None,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            client.ping()
            _redis_client = client
            _last_failed_init_at = 0.0
            logger.info("Redis 连接初始化成功")
            return _redis_client
        except Exception as e:
            _redis_client = None
            _last_failed_init_at = time.time()
            logger.warning(f"Redis 连接失败，将使用直连模式: {e}")
            return None


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端连接。失败时返回 None 由调用方走降级路径。"""
    if _redis_client is not None:
        return _redis_client
    return init_redis()


def _build_cache_key(
    source: str,
    report_type: str,
    days: int,
    since: str = None,
    until: str = None,
    breakdown: bool = False,
    by: str = None,
) -> str:
    """构建缓存 Key"""
    parts = [
        "token_usage",
        source,
        report_type,
        str(days),
        since or "",
        until or "",
        "1" if breakdown else "0",
        by or "",
    ]
    return ":".join(parts)


def get_cached_data(
    source: str,
    report_type: str,
    days: int,
    since: str = None,
    until: str = None,
    breakdown: bool = False,
    by: str = None,
) -> Optional[dict]:
    """从 Redis 获取缓存数据"""
    client = get_redis_client()
    if not client:
        return None

    key = _build_cache_key(source, report_type, days, since, until, breakdown, by)
    try:
        data = client.get(key)
        if data:
            logger.info(f"缓存命中: {key}")
            return json.loads(data)
        logger.info(f"缓存未命中: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis 读取失败: {e}")
        return None


def set_cached_data(
    source: str,
    report_type: str,
    days: int,
    data: dict,
    since: str = None,
    until: str = None,
    breakdown: bool = False,
    by: str = None,
) -> bool:
    """将数据写入 Redis 缓存"""
    client = get_redis_client()
    if not client:
        return False

    key = _build_cache_key(source, report_type, days, since, until, breakdown, by)
    try:
        client.setex(
            key,
            settings.CACHE_REDIS_TOKEN_USAGE_TTL,
            json.dumps(data, ensure_ascii=False),
        )
        logger.info(f"缓存已写入: {key}, TTL={settings.CACHE_REDIS_TOKEN_USAGE_TTL}s")
        return True
    except Exception as e:
        logger.warning(f"Redis 写入失败: {e}")
        return False


def invalidate_cache() -> bool:
    """清除所有 Token Usage 缓存"""
    client = get_redis_client()
    if not client:
        return False

    try:
        keys = client.keys("token_usage:*")
        if keys:
            client.delete(*keys)
            logger.info(f"已清除 {len(keys)} 个缓存 Key")
        return True
    except Exception as e:
        logger.warning(f"Redis 缓存清除失败: {e}")
        return False


def invalidate_user_query_cache(user_id: str) -> bool:
    """清除指定用户的 Token Usage 查询缓存（用户维度，影响该用户所有设备）。

    当用户执行刷新或同步操作时调用，确保后续查询能获取最新数据。
    注意：由于 summary/details 查询的缓存键中 device_id 为空（汇总所有设备的数据），
    同步操作必须使用此方法（而非设备级清除）以确保聚合缓存也被清除。
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        patterns = [
            f"token_usage:query:*:{user_id}:*",
            f"token_usage:query:*:{user_id}",
        ]
        deleted = 0
        for pattern in patterns:
            keys = client.keys(pattern)
            if keys:
                deleted += client.delete(*keys)
        logger.info(f"已清除用户 {user_id} 的 Token Usage 查询缓存 {deleted} 个")
        return True
    except Exception as e:
        logger.warning(f"清除用户 Token Usage 查询缓存失败: {e}")
        return False


def invalidate_device_query_cache(user_id: str, device_id: str) -> bool:
    """仅清除指定 user + device 的设备维度查询缓存（不影响同用户下的其他设备）。

    缓存 key 结构: token_usage:query:{source}:{report_type}:{days}:{group_by}:
                  {user_id}:{device_id}:{tool_id}:{model}:{sort_by}:{sort_order}

    此方法精确匹配 device_id 位置，因此只清除该设备的缓存键，保留其他设备的缓存。
    空 device_id 的 user 级汇总缓存不会被清除（避免影响其他设备）。
    """
    client = get_redis_client()
    if not client:
        return False
    if not user_id:
        return False
    if not device_id:
        return invalidate_user_query_cache(user_id)

    try:
        pattern = f"token_usage:query:*:*:*:*:{user_id}:{device_id}:*"
        keys = client.keys(pattern)
        if not keys:
            return True
        count = client.delete(*keys)
        logger.info(
            f"已清除设备 {device_id[:8]}... 的 {count} 个查询缓存键 (user={user_id})"
        )
        return True
    except Exception as e:
        logger.warning(f"清除设备 {device_id[:8]}... 查询缓存失败: {e}")
        return False


def invalidate_single_cache(
    source: str,
    report_type: str,
    days: int,
    since: str = None,
    until: str = None,
    breakdown: bool = False,
    by: str = None,
) -> bool:
    """清除单个缓存 Key"""
    client = get_redis_client()
    if not client:
        return False

    key = _build_cache_key(source, report_type, days, since, until, breakdown, by)
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis 单 Key 清除失败: {e}")
        return False


# ========== 用户/设备维度查询缓存 ==========


def _build_query_cache_key(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
    tool_id: str = "",
    model: str = "",
    sort_by: str = "date",
    sort_order: str = "desc",
) -> str:
    """构建用户维度的查询缓存 Key"""
    parts = [
        "token_usage:query",
        source,
        report_type,
        str(days),
        group_by,
        user_id,
        device_id or "",
        tool_id or "all-tools",
        model or "all-models",
        sort_by or "date",
        sort_order or "desc",
    ]
    return ":".join(parts)


def get_query_cached_data(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
    tool_id: str = "",
    model: str = "",
    sort_by: str = "date",
    sort_order: str = "desc",
) -> Optional[dict]:
    """从 Redis 获取用户维度的查询缓存"""
    client = get_redis_client()
    if not client:
        return None

    key = _build_query_cache_key(
        source, report_type, days, group_by, user_id, device_id,
        tool_id, model, sort_by, sort_order
    )
    try:
        data = client.get(key)
        if data:
            logger.info(f"查询缓存命中: {key}")
            return json.loads(data)
        logger.info(f"查询缓存未命中: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis 查询缓存读取失败: {e}")
        return None


def get_query_cached_payload(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
    tool_id: str = "",
    model: str = "",
    sort_by: str = "date",
    sort_order: str = "desc",
) -> Optional[dict]:
    """读取查询缓存，同时返回 Redis 剩余 TTL。"""
    client = get_redis_client()
    if not client:
        return None

    key = _build_query_cache_key(
        source, report_type, days, group_by, user_id, device_id,
        tool_id, model, sort_by, sort_order
    )
    try:
        data = client.get(key)
        if not data:
            logger.info(f"查询缓存未命中: {key}")
            return None
        ttl = client.ttl(key)
        payload = json.loads(data)
        payload["_cache_ttl_seconds"] = max(int(ttl), 0)
        logger.info(f"查询缓存命中: {key}, TTL={ttl}s")
        return payload
    except Exception as e:
        logger.warning(f"Redis 查询缓存读取失败: {e}")
        return None


def set_query_cached_data(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
    tool_id: str = "",
    model: str = "",
    sort_by: str = "date",
    sort_order: str = "desc",
    data: dict = None,
) -> bool:
    """将用户维度的查询数据写入 Redis 缓存，附带写入时间戳"""
    client = get_redis_client()
    if not client:
        return False

    key = _build_query_cache_key(
        source, report_type, days, group_by, user_id, device_id,
        tool_id, model, sort_by, sort_order
    )
    try:
        payload = dict(data or {})
        payload.setdefault("cache_written_at", datetime.now().isoformat())
        client.setex(
            key,
            settings.CACHE_REDIS_TOKEN_USAGE_TTL,
            json.dumps(payload, ensure_ascii=False),
        )
        logger.info(
            f"查询缓存已写入: {key}, TTL={settings.CACHE_REDIS_TOKEN_USAGE_TTL}s"
        )
        return True
    except Exception as e:
        logger.warning(f"Redis 查询缓存写入失败: {e}")
        return False


def acquire_refresh_lock(user_id: str, owner: str, ttl_seconds: int = 120) -> dict:
    """获取用户级 Token Usage 刷新锁。"""
    client = get_redis_client()
    if not client:
        return {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": 0}

    key = f"token_usage:refresh_lock:{user_id}"
    try:
        acquired = client.set(key, owner, nx=True, ex=ttl_seconds)
        if acquired:
            return {
                "acquired": True,
                "locked": False,
                "owner": owner,
                "ttl_seconds": ttl_seconds,
            }
        return {
            "acquired": False,
            "locked": True,
            "owner": client.get(key),
            "ttl_seconds": max(int(client.ttl(key)), 0),
        }
    except Exception as e:
        logger.warning(f"Token Usage 刷新锁获取失败，将继续刷新: {e}")
        return {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": 0}


def release_refresh_lock(user_id: str, owner: str) -> None:
    """释放用户级 Token Usage 刷新锁。"""
    client = get_redis_client()
    if not client:
        return
    key = f"token_usage:refresh_lock:{user_id}"
    try:
        if client.get(key) == owner:
            client.delete(key)
    except Exception as e:
        logger.warning(f"Token Usage 刷新锁释放失败: {e}")


def warm_query_cache(user_id: str) -> bool:
    """同步完成后预热常用 summary 查询缓存，避免首屏冷查询。

    只预热 daily / 30 天 / source=all / 无筛选 这一最常用组合；
    其他组合仍走正常"未命中 -> DB -> 回写"路径。
    用户无数据、Redis 不可用、构建失败、异常时静默返回 False，不影响同步主流程。

    注意：此函数构造完整 payload（与 /summary 路由缓存写入结构一致）。
    使用 app.models.token_usage_models.TokenUsageRecord 与 DB ORM；
    复用 _build_summary_payload 同口径的聚合 SQL（函数内延迟导入避免循环依赖）。
    """
    from app.models.base import SessionLocal
    from app.models.token_usage_models import TokenUsageRecord
    from app.routes.token_usage import _build_summary_payload

    db = SessionLocal()
    try:
        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            logger.info(f"warm_query_cache 跳过: user={user_id} 无数据")
            return False

        # 构造与 /summary 默认参数一致的 req（10 字段全部包含）
        req = SimpleNamespace(
            source="all",
            type="daily",
            days=30,
            start_date=None,
            group_by="none",
            device_id=None,
            tool_id=None,
            model=None,
            sort_by="date",
            sort_order="desc",
        )

        payload = _build_summary_payload(db, user_id, req)
        if payload is None:
            logger.info(f"warm_query_cache 跳过: user={user_id} payload 为空")
            return False

        written = set_query_cached_data(
            source="all",
            report_type="daily",
            days=30,
            group_by="none",
            user_id=user_id,
            device_id="",
            tool_id="",
            model="",
            sort_by="date",
            sort_order="desc",
            data=payload,
        )
        if written:
            logger.info(f"warm_query_cache 预热成功: user={user_id}")
        return bool(written)
    except Exception as e:
        logger.warning(f"warm_query_cache 预热失败: user={user_id}, error={e}")
        return False
    finally:
        db.close()
