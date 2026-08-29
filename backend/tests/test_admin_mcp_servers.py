"""Admin MCP Servers API 测试

Phase 3-Plan-1A Task 4: Admin API（CRUD + test + sync）
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import INET
from unittest.mock import patch, AsyncMock

# 确保 backend 目录在 sys.path 中
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# SQLite 无 PG 特有类型，注册降级编译器（Base.metadata.create_all 会建所有表）
@compiles(PG_UUID, "sqlite")
def _compile_uuid_for_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_for_sqlite(element, compiler, **kw):
    return "VARCHAR(45)"


from app.models.base import Base
from app.models.mcp_server import McpServer  # noqa: E402
from app.main import app  # noqa: E402
from app.models import get_db  # noqa: E402
from app.api.dependencies import get_current_user  # noqa: E402


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB

    使用 StaticPool 确保所有连接共享同一个内存 DB（TestClient 在不同线程运行）。
    check_same_thread=False 允许跨线程使用 SQLite 连接。
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    """TestClient，覆写 get_db 依赖"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_user():
    return {"id": "test-user", "role": "admin", "username": "admin"}


# ----------------------------------------------------------------------
# CRUD 测试
# ----------------------------------------------------------------------


def test_create_mcp_server(client, db_session, admin_user):
    """测试创建 MCP server"""
    with patch.object(app, "dependency_overrides", {**app.dependency_overrides, get_current_user: lambda: admin_user}):
        # 直接覆写 get_current_user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        try:
            response = client.post(
                "/api/admin/mcp/servers",
                json={
                    "name": "test_server",
                    "server_url": "http://localhost:3000",
                    "transport": "sse",
                    "timeout_seconds": 30,
                },
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_server"
    assert data["transport"] == "sse"
    assert data["is_active"] is True
    assert data["tools_count"] == 0


def test_list_mcp_servers(client, db_session, admin_user):
    """测试列出 MCP servers"""
    server = McpServer(
        name="test_server",
        server_url="http://localhost:3000",
        transport="sse",
    )
    db_session.add(server)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        response = client.get("/api/admin/mcp/servers")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test_server"


# ----------------------------------------------------------------------
# test 端点
# ----------------------------------------------------------------------


def test_test_mcp_server(client, db_session, admin_user):
    """测试测试连接端点"""
    server = McpServer(
        name="test_server",
        server_url="http://localhost:3000",
        transport="sse",
    )
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)

    mock_manager = AsyncMock()
    mock_manager.sync_server = AsyncMock(
        return_value={
            "success": True,
            "tools_count": 2,
            "error": None,
            "tools": [{"name": "tool1"}, {"name": "tool2"}],
        }
    )

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        with patch("app.api.routes.admin_mcp_servers.get_mcp_server_manager", return_value=mock_manager):
            response = client.post(f"/api/admin/mcp/servers/{server.id}/test")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["tools"]) == 2


# ----------------------------------------------------------------------
# 权限校验
# ----------------------------------------------------------------------


def test_non_admin_forbidden(client, db_session):
    """测试非 admin 用户被拒绝"""
    normal_user = {"id": "test-user", "role": "user", "username": "user"}

    app.dependency_overrides[get_current_user] = lambda: normal_user
    try:
        response = client.get("/api/admin/mcp/servers")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403


# ----------------------------------------------------------------------
# update / delete / sync 端点（补充）
# ----------------------------------------------------------------------


def test_update_mcp_server(client, db_session, admin_user):
    """测试更新 MCP server"""
    server = McpServer(
        name="original_name",
        server_url="http://localhost:3000",
        transport="sse",
    )
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        response = client.put(
            f"/api/admin/mcp/servers/{server.id}",
            json={"name": "updated_name", "is_active": False},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated_name"
    assert data["is_active"] is False


def test_delete_mcp_server(client, db_session, admin_user):
    """测试删除 MCP server"""
    server = McpServer(
        name="to_delete",
        server_url="http://localhost:3000",
        transport="sse",
    )
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)

    mock_manager = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        with patch("app.api.routes.admin_mcp_servers.get_mcp_server_manager", return_value=mock_manager):
            response = client.delete(f"/api/admin/mcp/servers/{server.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 204

    # 确认已删除
    remaining = db_session.query(McpServer).filter(McpServer.id == server.id).first()
    assert remaining is None


def test_sync_mcp_server(client, db_session, admin_user):
    """测试同步工具到 ToolRegistry 端点"""
    server = McpServer(
        name="sync_test",
        server_url="http://localhost:3000",
        transport="sse",
    )
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)

    mock_manager = AsyncMock()
    mock_manager.sync_server = AsyncMock(
        return_value={
            "success": True,
            "tools_count": 3,
            "error": None,
        }
    )

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        with patch("app.api.routes.admin_mcp_servers.get_mcp_server_manager", return_value=mock_manager):
            response = client.post(f"/api/admin/mcp/servers/{server.id}/sync")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["tools_count"] == 3
