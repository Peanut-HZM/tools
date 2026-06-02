"""端到端测试：summary 和 details 的一致性。"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.token_usage_models import TokenUsageRecord


@pytest.fixture
def seeded_client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    base = date.today()
    for i in range(10):
        session.add(
            TokenUsageRecord(
                user_id="u1",
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
    return client, session


class TestEndToEndFlow:
    def test_summary_total_matches_details_total(self, seeded_client):
        client, session = seeded_client
        with patch("app.routes.token_usage.SessionLocal", return_value=session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="u1"):
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
            with patch("app.routes.token_usage.get_current_user_id", return_value="u1"):
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
            with patch("app.routes.token_usage.get_current_user_id", return_value="u1"):
                details_resp = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "group_by": "none", "source": "all", "limit": 200, "offset": 0},
                    headers={"Authorization": "Bearer t"},
                )
        data = details_resp.json()
        assert data["total"] == 10
        assert len(data["items"]) == 10
        assert data["has_more"] is False
