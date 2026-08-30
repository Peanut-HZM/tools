"""市场 API 测试（P2-④）"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

USER_ID = str(uuid.uuid4())
OTHER_ID = str(uuid.uuid4())


@pytest.fixture
def env():
    """独立 SQLite + 已注册 agents/tools 表"""
    from app.models.agent import Agent  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base
    from app.models.harness_models import Tool  # noqa: F401

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    return session


@pytest.fixture
def client(env):
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": USER_ID}
    yield TestClient(app)
    app.dependency_overrides.clear()


def _mk_agent(session, name, visibility="public", is_active=True, **kw):
    from app.models.agent import Agent

    a = Agent(name=name, description="", system_prompt="")
    a.visibility = visibility
    a.is_active = is_active
    a.owner_id = uuid.UUID(OTHER_ID)
    for k, v in kw.items():
        setattr(a, k, v)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_catalog_only_public_active(client, env):
    _mk_agent(env, "pub1", visibility="public")
    _mk_agent(env, "priv", visibility="private")
    _mk_agent(env, "unlisted", visibility="unlisted")
    _mk_agent(env, "inactive", visibility="public", is_active=False)

    r = client.get("/api/v1/marketplace/agents")
    assert r.status_code == 200
    body = r.json()
    names = [a["name"] for a in body["records"]]
    assert names == ["pub1"]


def test_fork_creates_private_copy(client, env):
    from app.models.agent import Agent
    from app.models.harness_models import Tool, ToolBinding

    agent = _mk_agent(env, "orig", visibility="public", system_prompt="SP")
    tool = Tool(name="web_search", display_name="Web Search", description="t", type="builtin", is_active=True)
    env.add(tool)
    env.commit()
    env.refresh(tool)
    env.add(ToolBinding(agent_id=agent.id, tool_id=tool.id, priority=1))
    env.commit()

    r = client.post(f"/api/v1/marketplace/agents/{agent.id}/fork")
    assert r.status_code == 201, r.text
    body = r.json()

    forked = env.query(Agent).filter(Agent.id == uuid.UUID(body["id"])).first()
    assert forked is not None
    assert forked.id != agent.id
    assert forked.name == "orig（副本）"
    assert forked.visibility == "private"
    assert str(forked.owner_id) == USER_ID
    assert forked.is_default is False
    assert forked.system_prompt == "SP"
    # bindings 已复制
    copied = env.query(ToolBinding).filter(ToolBinding.agent_id == forked.id).all()
    assert len(copied) == 1
    # 原 agent 的 bindings 不变
    orig_bindings = env.query(ToolBinding).filter(ToolBinding.agent_id == agent.id).all()
    assert len(orig_bindings) == 1


def test_fork_private_agent_403(client, env):
    agent = _mk_agent(env, "hidden", visibility="private")
    r = client.post(f"/api/v1/marketplace/agents/{agent.id}/fork")
    assert r.status_code == 403


def test_fork_missing_agent_404(client):
    r = client.post(f"/api/v1/marketplace/agents/{uuid.uuid4()}/fork")
    assert r.status_code == 404
