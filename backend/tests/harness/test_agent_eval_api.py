"""Agent 评估 API 测试（P3-⑨）"""
import uuid
from types import SimpleNamespace

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
    from app.models.agent_eval import AgentEvalRun  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(SimpleNamespace()) if False else None
    from app.models.agent import Agent as A

    session.add(A(id=uuid.UUID(AID), name="eval-agent", description="", system_prompt="SP"))
    session.commit()
    return session


@pytest.fixture
def admin_client(env, monkeypatch):
    """TestClient + admin 鉴权 + EvalService 替换为 Fake（不依赖真实 LLM）"""
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from app.models.agent_eval import AgentEvalRun

    def _override_db():
        yield env

    async def _fake_run_eval(self, agent, user_id, name, cases, judge_threshold=0.7):
        run = AgentEvalRun(
            agent_id=agent.id, user_id=user_id, name=name,
            status="completed", total_cases=len(cases),
            passed_cases=len(cases), avg_score=0.9,
        )
        env.add(run)
        env.commit()
        env.refresh(run)
        return run

    monkeypatch.setattr(
        "app.services.harness.eval_service.EvalService.run_eval", _fake_run_eval
    )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "admin", "id": ADMIN_ID}
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_and_get_eval_run(admin_client):
    r = admin_client.post(
        f"/api/v1/admin/agents/{AID}/evals",
        json={"name": "首轮评测", "cases": [{"input": "q", "expected": "e"}]},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["total_cases"] == 1

    # 列表
    r2 = admin_client.get(f"/api/v1/admin/agents/{AID}/evals")
    assert r2.status_code == 200
    assert r2.json()["count"] == 1

    # 详情（含 cases 数组，可为空——Fake 未建 case 行）
    r3 = admin_client.get(f"/api/v1/admin/agents/{AID}/evals/{body['id']}")
    assert r3.status_code == 200
    assert "cases" in r3.json()


def test_eval_validation(admin_client):
    r = admin_client.post(
        f"/api/v1/admin/agents/{AID}/evals",
        json={"name": "bad", "cases": []},
    )
    assert r.status_code == 422


def test_eval_agent_not_found(admin_client):
    r = admin_client.post(
        f"/api/v1/admin/agents/{uuid.uuid4()}/evals",
        json={"name": "x", "cases": [{"input": "q", "expected": "e"}]},
    )
    assert r.status_code == 404


def test_eval_requires_admin(env, monkeypatch):
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from fastapi.testclient import TestClient

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": str(uuid.uuid4())}
    client = TestClient(app)
    try:
        r = client.post(
            f"/api/v1/admin/agents/{AID}/evals",
            json={"name": "x", "cases": [{"input": "q", "expected": "e"}]},
        )
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_run_detail_404(admin_client):
    r = admin_client.get(f"/api/v1/admin/agents/{AID}/evals/{uuid.uuid4()}")
    assert r.status_code == 404
