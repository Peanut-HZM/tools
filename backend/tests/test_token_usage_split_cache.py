"""测试 /summary 和 /details 的缓存键策略、TTL、失效。"""
import pytest
import re
from unittest.mock import patch

from app.services.token_usage_cache import (
    get_query_cached_data,
    get_query_cached_payload,
    set_query_cached_data,
    invalidate_user_query_cache,
)


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                self.ttls.pop(k, None)
                count += 1
        return count

    def keys(self, pattern):
        regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        return [k for k in self.store if re.match(regex, k)]

    def ttl(self, key):
        return self.ttls.get(key, -1)


@pytest.fixture
def fake_redis():
    return FakeRedis()


class TestCacheKeyStrategy:
    def test_summary_key_omits_pagination_params(self, fake_redis):
        with patch("app.services.token_usage_cache.get_redis_client", return_value=fake_redis):
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
                data={"summary_data": {"foo": 1}},
            )
            result = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
            )
        assert result is not None
        assert "summary_data" in result
        assert result["summary_data"]["foo"] == 1

    def test_details_key_includes_pagination(self, fake_redis):
        with patch("app.services.token_usage_cache.get_redis_client", return_value=fake_redis):
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="details:date:desc:10:0", sort_order="desc",
                data={"details_data": {"items": [1, 2, 3], "total": 3}},
            )
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="details:date:desc:50:0", sort_order="desc",
                data={"details_data": {"items": [4, 5, 6, 7], "total": 4}},
            )
            r1 = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="details:date:desc:10:0", sort_order="desc",
            )
            r2 = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="details:date:desc:50:0", sort_order="desc",
            )
        assert r1["details_data"]["total"] == 3
        assert r2["details_data"]["total"] == 4

    def test_cache_invalidation_only_affects_user(self, fake_redis):
        with patch("app.services.token_usage_cache.get_redis_client", return_value=fake_redis):
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
                data={"x": 1},
            )
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u2", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
                data={"x": 2},
            )
            invalidate_user_query_cache("u1")
            r1 = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
            )
            r2 = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u2", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
            )
        assert r1 is None
        assert r2 is not None


class TestCacheDegradation:
    def test_request_returns_none_when_redis_down(self):
        with patch("app.services.token_usage_cache.get_redis_client", return_value=None):
            result = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
            )
        assert result is None

    def test_set_returns_false_when_redis_down(self):
        with patch("app.services.token_usage_cache.get_redis_client", return_value=None):
            result = set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
                data={"summary_data": {}},
            )
        assert result is False


class TestPayloadWrapper:
    def test_payload_function_reads_wrapped_data(self, fake_redis):
        with patch("app.services.token_usage_cache.get_redis_client", return_value=fake_redis):
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
                data={"summary_data": {"summary": {"total_tokens": 100}}},
            )
            result = get_query_cached_payload(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="__summary__", sort_order="desc",
            )
        assert result is not None
        assert "summary_data" in result
        assert result["summary_data"]["summary"]["total_tokens"] == 100
