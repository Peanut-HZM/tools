"""Admin MCP servers API 多 transport 校验测试（P2-①c）

使用 FastAPI TestClient + SQLite 内存库（StaticPool 跨线程共享连接），
admin 鉴权走依赖覆盖。
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client():
    """TestClient + admin 鉴权覆盖 + 独立 SQLite 内存库"""
    # 导入模型注册 Base.metadata（mcp_servers + harness 表）
    from app.models.mcp_server import McpServer  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    def _override_db():
        yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "admin", "id": "u1"}
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_create_stdio_server_requires_command(client):
    """stdio 缺 command → 400"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s1", "server_url": "npx demo", "transport": "stdio"},
    )
    assert resp.status_code == 400


def test_create_stdio_server_accepted(client):
    """stdio + command → 201，command_json 落库"""
    cmd = {"command": "npx", "args": ["-y", "demo"], "env": {"K": "V"}}
    resp = client.post(
        "/api/admin/mcp/servers",
        json={
            "name": "s2",
            "server_url": "npx demo",
            "transport": "stdio",
            "command": cmd,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["transport"] == "stdio"
    assert json.loads(resp.json()["command_json"]) == cmd


def test_create_http_server_accepted(client):
    """transport=http → 201（URL 安全校验在 connect 时做）"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={
            "name": "s3",
            "server_url": "https://mcp.example.com/mcp",
            "transport": "http",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["command_json"] is None


def test_create_invalid_transport_rejected(client):
    """transport=grpc → 422（Pydantic Literal 兜底）"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s4", "server_url": "x", "transport": "grpc"},
    )
    assert resp.status_code == 422


def test_update_command_replaces(client):
    """update command 非 None → 整体替换 command_json"""
    created = client.post(
        "/api/admin/mcp/servers",
        json={
            "name": "s5",
            "server_url": "npx demo",
            "transport": "stdio",
            "command": {"command": "npx"},
        },
    ).json()
    resp = client.put(
        f"/api/admin/mcp/servers/{created['id']}",
        json={"command": {"command": "node", "args": ["srv.js"]}},
    )
    assert resp.status_code == 200
    assert json.loads(resp.json()["command_json"]) == {
        "command": "node",
        "args": ["srv.js"],
    }


def test_update_command_rejected_for_sse(client):
    """非 stdio server 更新 command → 400"""
    created = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s6", "server_url": "https://a.example.com", "transport": "sse"},
    ).json()
    resp = client.put(
        f"/api/admin/mcp/servers/{created['id']}",
        json={"command": {"command": "node"}},
    )
    assert resp.status_code == 400


def test_create_stdio_invalid_command_shape(client):
    """stdio command 缺 command 键 → 400"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={
            "name": "s7",
            "server_url": "npx demo",
            "transport": "stdio",
            "command": {"args": ["a"]},
        },
    )
    assert resp.status_code == 400
