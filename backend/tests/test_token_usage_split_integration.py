"""端到端测试：summary 和 details 的一致性。"""
import re

import pytest
from datetime import date, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.token_usage_models import TokenUsageRecord


class FakeRedis:
    """隔离 Redis 的空实现，避免测试读到真实环境的缓存数据。"""

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


# 使用真实环境不存在的 user_id，避免与线上数据 / Redis 缓存撞键
TEST_USER_ID = "zztest_token_usage_split_u1"


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def seeded_client(tmp_path, fake_redis):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    base = date.today()
    for i in range(10):
        session.add(
            TokenUsageRecord(
                user_id=TEST_USER_ID,
                device_id="d1",
                source="claude",
                tool_id="claude-code",
                tool_name="Claude Code",
                model="claude-3-5-sonnet",
                model_display_name="Claude 3.5 Sonnet",
                record_date=base - timedelta(days=i),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=10,
                cache_read_tokens=20,
                total_tokens=180,
                total_cost=0.01,
            )
        )
    session.commit()
    client = TestClient(app)
    # 隔离 Redis：查询缓存必须从空缓存开始，否则会读到真实环境的数据
    with patch(
        "app.services.token_usage_cache.get_redis_client", return_value=fake_redis
    ):
        yield client, session


class TestEndToEndFlow:
    def test_summary_total_matches_details_total(self, seeded_client):
        client, session = seeded_client
        with patch("app.routes.token_usage.SessionLocal", return_value=session):
            with patch("app.routes.token_usage.get_current_user_id", return_value=TEST_USER_ID):
                summary_resp = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30, "group_by": "none", "source": "all"},
                    headers={"Authorization": "Bearer t"},
                )
                details_resp = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "group_by": "none", "source": "all", "limit": 200, "offset": 0},
                    headers={"Authorization": "Bearer t"},
                )
        s_total = summary_resp.json()["summary"]["total_tokens"]
        d_total = sum(item["total_tokens"] for item in details_resp.json()["items"])
        assert s_total == d_total

    def test_summary_total_tokens_equals_sum_of_daily(self, seeded_client):
        client, session = seeded_client
        with patch("app.routes.token_usage.SessionLocal", return_value=session):
            with patch("app.routes.token_usage.get_current_user_id", return_value=TEST_USER_ID):
                summary_resp = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30, "group_by": "none", "source": "all"},
                    headers={"Authorization": "Bearer t"},
                )
        s = summary_resp.json()["summary"]
        assert s["total_input_tokens"] + s["total_output_tokens"] + s["total_cache_creation_tokens"] + s["total_cache_read_tokens"] == s["total_tokens"]

    def test_details_total_equals_records_count(self, seeded_client):
        client, session = seeded_client
        with patch("app.routes.token_usage.SessionLocal", return_value=session):
            with patch("app.routes.token_usage.get_current_user_id", return_value=TEST_USER_ID):
                details_resp = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "group_by": "none", "source": "all", "limit": 200, "offset": 0},
                    headers={"Authorization": "Bearer t"},
                )
        data = details_resp.json()
        assert data["total"] == 10
        assert len(data["items"]) == 10
        assert data["has_more"] is False
