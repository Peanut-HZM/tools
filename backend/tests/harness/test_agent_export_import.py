"""Agent 导出/导入 bundle API 测试（P2-④）"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ADMIN_ID = str(uuid.uuid4())
TOOL_NAME = "web_search"


@pytest.fixture
def env():
    from app.models.agent import Agent  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


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


def _mk_agent_with_binding(session, name="orig"):
    from app.models.agent import Agent
    from app.models.harness_models import Tool, ToolBinding

    a = Agent(name=name, description="d", system_prompt="SP")
    a.visibility = "private"
    a.owner_id = uuid.uuid4()
    a.memory_procedural_enabled = True
    session.add(a)
    session.commit()
    session.refresh(a)

    tool = Tool(name=TOOL_NAME, display_name="Web Search", description="t", type="builtin")
    session.add(tool)
    session.commit()
    session.refresh(tool)
    session.add(ToolBinding(agent_id=a.id, tool_id=tool.id, parameter_overrides={"k": "v"}, priority=2))
    session.commit()
    return a


def test_export_bundle_shape(admin_client, env):
    agent = _mk_agent_with_binding(env)
    r = admin_client.post(f"/api/v1/admin/agents/{agent.id}/export")
    assert r.status_code == 200, r.text
    bundle = r.json()
    assert bundle["format_version"] == 1
    assert "exported_at" in bundle
    a = bundle["agent"]
    # 核心字段在
    assert a["name"] == "orig"
    assert a["system_prompt"] == "SP"
    assert a["memory_procedural_enabled"] is True
    # 剥离字段不在
    for stripped in ("id", "owner_id", "visibility", "is_default", "created_at", "updated_at"):
        assert stripped not in a
    # bindings 带工具名
    assert bundle["tool_bindings"][0]["tool_name"] == TOOL_NAME
    assert bundle["tool_bindings"][0]["parameter_overrides"] == {"k": "v"}


def test_import_roundtrip(admin_client, env):
    agent = _mk_agent_with_binding(env, "exp1")
    bundle = admin_client.post(f"/api/v1/admin/agents/{agent.id}/export").json()

    r = admin_client.post("/api/v1/admin/agents/import", json=bundle)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["warnings"] == []

    from app.models.agent import Agent
    from app.models.harness_models import ToolBinding

    imported = env.query(Agent).filter(Agent.id == uuid.UUID(body["agent"]["id"])).first()
    # 与源 agent 同库同名 → 冲突后缀是预期行为
    assert imported.name.startswith("exp1")
    assert imported.visibility == "private"
    assert str(imported.owner_id) == ADMIN_ID
    assert imported.is_default is False
    assert imported.system_prompt == "SP"
    bindings = env.query(ToolBinding).filter(ToolBinding.agent_id == imported.id).all()
    assert len(bindings) == 1
    assert bindings[0].parameter_overrides == {"k": "v"}


def test_import_name_conflict_suffixed(admin_client, env):
    agent = _mk_agent_with_binding(env, "dup")
    bundle = admin_client.post(f"/api/v1/admin/agents/{agent.id}/export").json()
    r = admin_client.post("/api/v1/admin/agents/import", json=bundle)
    assert r.status_code == 201
    # 同名原 agent 仍在，导入件改名
    assert r.json()["agent"]["name"] != "dup"
    assert r.json()["agent"]["name"].startswith("dup")


def test_import_unknown_tool_warns(admin_client, env):
    agent = _mk_agent_with_binding(env, "warned")
    bundle = admin_client.post(f"/api/v1/admin/agents/{agent.id}/export").json()
    # 清空工具表，使 tool_name 匹配失败
    from app.models.harness_models import Tool

    env.query(Tool).delete()
    env.commit()

    r = admin_client.post("/api/v1/admin/agents/import", json=bundle)
    assert r.status_code == 201
    assert len(r.json()["warnings"]) == 1


def test_import_bad_version_400(admin_client):
    r = admin_client.post("/api/v1/admin/agents/import", json={"format_version": 99})
    assert r.status_code == 400


def test_export_requires_admin(env):
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from fastapi.testclient import TestClient

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": str(uuid.uuid4())}
    client = TestClient(app)
    try:
        agent = _mk_agent_with_binding(env, "noauth")
        r = client.post(f"/api/v1/admin/agents/{agent.id}/export")
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()
