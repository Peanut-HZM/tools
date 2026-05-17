"""Token 统计数据 Redis 缓存服务"""

import json
import logging
import threading
import time
from datetime import datetime
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
    """清除指定用户的 Token Usage 查询缓存。"""
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
