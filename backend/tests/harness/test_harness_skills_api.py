"""技能 REST API 测试（P2-②）"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

AID = str(uuid.uuid4())
UID = str(uuid.uuid4())


@pytest.fixture
def client():
    """TestClient + 普通用户鉴权覆盖 + 独立 SQLite 内存库"""
    from app.models.agent import Agent  # noqa: F401
    from app.models.agent_procedural_memory import AgentProceduralMemory  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Agent(id=uuid.UUID(AID), name="a", description="", system_prompt=""))
    session.commit()

    def _override_db():
        yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": UID}
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_create_list_delete_skill(client):
    # 创建
    r = client.post(
        f"/api/v1/harness/agents/{AID}/skills",
        json={"name": "deploy", "trigger": "部署前", "content": "1. 测试"},
    )
    assert r.status_code == 201, r.text
    # 列表
    r = client.get(f"/api/v1/harness/agents/{AID}/skills")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["records"][0]["name"] == "deploy"
    # 删除
    r = client.delete(f"/api/v1/harness/agents/{AID}/skills/deploy")
    assert r.status_code == 204
    r = client.get(f"/api/v1/harness/agents/{AID}/skills")
    assert r.json()["count"] == 0


def test_create_skill_validation(client):
    r = client.post(
        f"/api/v1/harness/agents/{AID}/skills",
        json={"name": "", "trigger": "t", "content": "c"},
    )
    assert r.status_code == 422


def test_delete_missing_skill_404(client):
    r = client.delete(f"/api/v1/harness/agents/{AID}/skills/nope")
    assert r.status_code == 404
