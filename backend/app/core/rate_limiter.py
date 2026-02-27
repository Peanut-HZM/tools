"""
限流模块 - 基于 Redis 的滑动窗口限流
"""

import time
from typing import Optional
import redis
from datetime import datetime, timedelta


class RateLimiter:
    """Redis 限流器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _get_key(self, user_id: str, hour: str) -> str:
        """生成 Redis key"""
        return f"rate_limit:{user_id}:{hour}"

    def check_limit(self, user_id: str, limit: int) -> tuple[bool, int, Optional[int]]:
        """
        检查是否超过限流阈值

        Args:
            user_id: 用户ID
            limit: 每小时限制次数

        Returns:
            (是否允许, 当前次数, 剩余秒数)
        """
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        redis_key = self._get_key(user_id, hour_key)

        # 获取当前计数
        current_count = self.redis.get(redis_key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        # 检查是否超过限制
        if current_count >= limit:
            # 计算剩余时间
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )
            remaining_seconds = int((next_hour - now).total_seconds())
            return False, current_count, remaining_seconds

        return True, current_count, None

    def increment_counter(self, user_id: str) -> int:
        """
        增加计数器

        Args:
            user_id: 用户ID

        Returns:
            增加后的计数
        """
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        redis_key = self._get_key(user_id, hour_key)

        # 增加计数，设置过期时间为当前小时剩余时间
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)

        # 获取当前 TTL，如果没有设置则设置
        ttl = self.redis.ttl(redis_key)
        if ttl < 0:
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )
            ttl = int((next_hour - now).total_seconds())
            pipe.expire(redis_key, ttl)

        results = pipe.execute()
        return results[0]

    def get_remaining(self, user_id: str, limit: int) -> tuple[int, int]:
        """
        获取剩余可用次数和重置时间

        Args:
            user_id: 用户ID
            limit: 每小时限制次数

        Returns:
            (剩余次数, 重置秒数)
        """
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        redis_key = self._get_key(user_id, hour_key)

        current_count = self.redis.get(redis_key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        remaining = max(0, limit - current_count)

        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        remaining_seconds = int((next_hour - now).total_seconds())

        return remaining, remaining_seconds
