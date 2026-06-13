"""
Author: Peanut
Created: 2026-06-13
Purpose: 线程安全的进程内 TTL 缓存，用于高频读接口的缓存加速
"""

import threading
import time
from typing import Any, Optional


class SimpleTTLCache:
    """线程安全的进程内 TTL 缓存。"""

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None 并自动清除。"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            expire_at, value = entry
            if time.monotonic() > expire_at:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值，指定 TTL（秒），默认使用构造时的 default_ttl。"""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._cache[key] = (time.monotonic() + effective_ttl, value)

    def invalidate(self, key: str) -> None:
        """手动清除指定缓存。"""
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """按前缀批量清除缓存。"""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]

    def cleanup_expired(self) -> int:
        """清理所有过期条目，返回清理数量。"""
        now = time.monotonic()
        with self._lock:
            keys_to_remove = [
                k for k, (expire_at, _) in self._cache.items()
                if now > expire_at
            ]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()
