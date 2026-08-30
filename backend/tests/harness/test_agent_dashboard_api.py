"""Agent 性能仪表盘 API 测试（P3-⑫）"""
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ADMIN_ID = str(uuid.uuid4())
AID = str(uuid.uuid4())


@pytest.fixture
def env():
    from app.models.agent import Agent  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    from app.models.agent import Agent as A

    session.add(A(id=uuid.UUID(AID), name="dash", description="", system_prompt=""))
    session.commit()
    return session


@pytest.fixture
def admin_client(env):
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "admin", "id": ADMIN_ID}
    yield TestClient(app)
    app.dependency_overrides.clear()


def _mk_trace(session, status="success", tokens=100, duration_ms=500, created_at=None):
    from app.models.harness_models import Trace

    t = Trace(
        conversation_id=uuid.uuid4(),
        agent_id=uuid.UUID(AID),
        user_id=uuid.uuid4(),
        input_text="in",
        status=status,
        total_tokens=tokens,
        total_duration_ms=duration_ms,
    )
    if created_at is not None:
        t.started_at = created_at
    session.add(t)
    session.commit()
    return t


def test_dashboard_empty_data(admin_client):
    """空数据：success_rate/avg 为 null，trend 补零 14 天"""
    r = admin_client.get(f"/api/v1/admin/agents/{AID}/dashboard")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success_rate"] is None
    assert body["avg_duration_ms"] is None
    assert len(body["daily_trend"]) == 14
    assert all(d["trace_count"] == 0 for d in body["daily_trend"])
    assert body["status_breakdown"] == {}


def test_dashboard_aggregation(admin_client, env):
    now = datetime.utcnow()
    _mk_trace(env, "success", tokens=100, duration_ms=400, created_at=now)
    _mk_trace(env, "success", tokens=300, duration_ms=800, created_at=now)
    _mk_trace(env, "error", tokens=50, duration_ms=100, created_at=now - timedelta(days=1))

    r = admin_client.get(f"/api/v1/admin/agents/{AID}/dashboard")
    body = r.json()
    assert body["status_breakdown"]["success"] == 2
    assert body["status_breakdown"]["error"] == 1
    assert abs(body["success_rate"] - 2 / 3) < 1e-6
    assert abs(body["avg_duration_ms"] - (400 + 800 + 100) / 3) < 1e-6
    # 趋势：今天 2 条，昨天 1 条
    by_date = {d["date"]: d for d in body["daily_trend"]}
    assert by_date[now.strftime("%Y-%m-%d")]["trace_count"] == 2
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    assert by_date[yesterday]["trace_count"] == 1


def test_dashboard_agent_not_found(admin_client):
    r = admin_client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/dashboard")
    assert r.status_code == 404


def test_dashboard_requires_admin(env):
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": str(uuid.uuid4())}
    client = TestClient(app)
    try:
        r = client.get(f"/api/v1/admin/agents/{AID}/dashboard")
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()
