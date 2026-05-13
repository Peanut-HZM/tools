"""Token 统计数据 Redis 缓存服务"""

import json
import logging
from typing import Optional
import redis
from app.config.config import settings

logger = logging.getLogger(__name__)

# 全局 Redis 客户端连接
_redis_client: Optional[redis.Redis] = None


def init_redis() -> Optional[redis.Redis]:
    """初始化 Redis 客户端连接"""
    global _redis_client
    try:
        _redis_client = redis.Redis(
            host=settings.CACHE_REDIS_HOST,
            port=settings.CACHE_REDIS_PORT,
            db=settings.CACHE_REDIS_DB,
            password=settings.CACHE_REDIS_PASSWORD
            if settings.CACHE_REDIS_PASSWORD
            else None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _redis_client.ping()
        logger.info("Redis 连接初始化成功")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis 连接失败，将使用直连模式: {e}")
        _redis_client = None
        return None


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端连接"""
    if _redis_client is None:
        return init_redis()
    try:
        _redis_client.ping()
        return _redis_client
    except Exception:
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
    ]
    return ":".join(parts)


def get_query_cached_data(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
) -> Optional[dict]:
    """从 Redis 获取用户维度的查询缓存"""
    client = get_redis_client()
    if not client:
        return None

    key = _build_query_cache_key(source, report_type, days, group_by, user_id, device_id)
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


def set_query_cached_data(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
    data: dict = None,
) -> bool:
    """将用户维度的查询数据写入 Redis 缓存"""
    client = get_redis_client()
    if not client:
        return False

    key = _build_query_cache_key(source, report_type, days, group_by, user_id, device_id)
    try:
        client.setex(
            key,
            settings.CACHE_REDIS_TOKEN_USAGE_TTL,
            json.dumps(data, ensure_ascii=False),
        )
        logger.info(f"查询缓存已写入: {key}, TTL={settings.CACHE_REDIS_TOKEN_USAGE_TTL}s")
        return True
    except Exception as e:
        logger.warning(f"Redis 查询缓存写入失败: {e}")
        return False
