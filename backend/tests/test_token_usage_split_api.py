"""测试 /summary 和 /details 接口的入参/出参、错误码、缓存命中。"""
import pytest
from unittest.mock import patch
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.token_usage_models import TokenUsageRecord


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-123"}


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_records(db_session, user_id: str = "user-1", count: int = 5):
    base = date.today()
    for i in range(count):
        db_session.add(
            TokenUsageRecord(
                user_id=user_id,
                device_id=f"device-{i}",
                source="claude",
                tool_id="claude-code",
                tool_name="Claude Code",
                model="claude-3-5-sonnet",
                model_display_name="Claude 3.5 Sonnet",
                record_date=base - timedelta(days=i),
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                cache_creation_tokens=10,
                cache_read_tokens=20,
                total_tokens=180 * (i + 1),
                total_cost=0.01 * (i + 1),
            )
        )
    db_session.commit()


class TestSummaryEndpoint:
    def test_returns_summary_for_default_filters(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30, "group_by": "none", "source": "all"},
                    headers=auth_headers,
                )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "dimension_summaries" in data
        assert "chart_series" in data
        assert "sync_meta" in data

    def test_summary_excludes_items_field(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        assert "items" not in response.json()

    def test_summary_includes_total_cache_tokens(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        s = response.json()["summary"]
        assert "total_cache_creation_tokens" in s
        assert "total_cache_read_tokens" in s

    def test_summary_401_when_unauthenticated(self, client):
        response = client.get("/api/token-usage/summary")
        assert response.status_code == 401


class TestDetailsEndpoint:
    def test_returns_paginated_items(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "limit": 3, "offset": 0},
                    headers=auth_headers,
                )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
        assert data["limit"] == 3
        assert data["offset"] == 0
        assert data["has_more"] is True

    def test_details_pagination_offset_limit(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "limit": 3, "offset": 3},
                    headers=auth_headers,
                )
        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is False

    def test_details_limit_capped_at_200(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                response = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "limit": 500},
                    headers=auth_headers,
                )
        assert response.status_code == 422

    def test_details_401_when_unauthenticated(self, client):
        response = client.post("/api/token-usage/details", json={})
        assert response.status_code == 401


class TestDbQueryDeprecationHeader:
    def test_db_endpoint_adds_deprecation_header(self, client, auth_headers, db_session):
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                response = client.post(
                    "/api/token-usage/db-query",
                    json={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        assert response.headers.get("deprecation") == "true"
        assert "Sunset" in response.headers
        assert "Link" in response.headers
        assert "summary" in response.headers["Link"]
