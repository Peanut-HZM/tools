"""SimpleTTLCache 单元测试"""

import time
import threading
from app.services.simple_cache import SimpleTTLCache


def test_set_and_get():
    cache = SimpleTTLCache(default_ttl=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_get_missing_key_returns_none():
    cache = SimpleTTLCache()
    assert cache.get("nonexistent") is None


def test_ttl_expiration():
    cache = SimpleTTLCache(default_ttl=1)
    cache.set("key1", "value1", ttl=1)
    assert cache.get("key1") == "value1"
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_custom_ttl_overrides_default():
    cache = SimpleTTLCache(default_ttl=60)
    cache.set("key1", "value1", ttl=1)
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_invalidate():
    cache = SimpleTTLCache()
    cache.set("key1", "value1")
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_invalidate_nonexistent_key_no_error():
    cache = SimpleTTLCache()
    cache.invalidate("nonexistent")  # 不应抛异常


def test_invalidate_prefix():
    cache = SimpleTTLCache()
    cache.set("tools:pc:all", ["tool1"])
    cache.set("tools:mobile:all", ["tool2"])
    cache.set("categories", ["cat1"])
    cache.invalidate_prefix("tools:")
    assert cache.get("tools:pc:all") is None
    assert cache.get("tools:mobile:all") is None
    assert cache.get("categories") == ["cat1"]


def test_cleanup_expired():
    cache = SimpleTTLCache()
    cache.set("key1", "v1", ttl=1)
    cache.set("key2", "v2", ttl=1)
    cache.set("key3", "v3", ttl=3600)
    time.sleep(1.1)
    cleaned = cache.cleanup_expired()
    assert cleaned == 2
    assert cache.get("key3") == "v3"


def test_len():
    cache = SimpleTTLCache()
    cache.set("a", 1)
    cache.set("b", 2)
    assert len(cache) == 2


def test_clear():
    cache = SimpleTTLCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0


def test_thread_safety():
    cache = SimpleTTLCache(default_ttl=60)
    errors = []

    def writer():
        try:
            for i in range(100):
                cache.set(f"key_{i}", i)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for i in range(100):
                cache.get(f"key_{i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(5)]
    threads += [threading.Thread(target=reader) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors) == 0
