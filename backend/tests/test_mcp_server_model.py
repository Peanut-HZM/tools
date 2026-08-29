"""McpServer 模型测试

Phase 3-Plan-1A Task 1: MCP Server 配置表
"""
import os
import sys
import uuid
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB

# 确保 backend 目录在 sys.path 中
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# SQLite 无 UUID 类型，注册降级编译器
@compiles(PG_UUID, "sqlite")
def _compile_uuid_for_sqlite(element, compiler, **kw):
    return "CHAR(32)"


# SQLite 无 JSONB 类型，注册降级编译器（Base.metadata.create_all 会建所有表）
@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
    return "JSON"


from app.models.base import Base
from app.models.mcp_server import McpServer


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_mcp_server_creation(db_session):
    """测试 McpServer 基本字段"""
    server = McpServer(
        name="test_server",
        server_url="http://localhost:3000",
        transport="sse",
        is_active=True,
        timeout_seconds=30,
    )
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)

    assert server.name == "test_server"
    assert server.server_url == "http://localhost:3000"
    assert server.transport == "sse"
    assert server.is_active is True
    assert server.timeout_seconds == 30
    assert server.tools_count == 0
    assert server.last_connected_at is None
    assert server.last_error is None


def test_mcp_server_name_unique(db_session):
    """测试 name 唯一约束"""
    server1 = McpServer(name="unique_name", server_url="http://localhost:3000")
    db_session.add(server1)
    db_session.commit()

    server2 = McpServer(name="unique_name", server_url="http://localhost:3001")
    db_session.add(server2)
    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()


def test_mcp_server_default_values(db_session):
    """测试默认值：transport=sse, is_active=True, timeout_seconds=30, tools_count=0"""
    server = McpServer(name="defaults_test", server_url="http://localhost:4000")
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)

    assert server.transport == "sse"
    assert server.is_active is True
    assert server.timeout_seconds == 30
    assert server.tools_count == 0
    assert server.headers_json is None


def test_mcp_server_repr(db_session):
    """测试 __repr__"""
    server = McpServer(
        name="repr_test",
        server_url="http://localhost:5000",
        is_active=True,
    )
    assert "repr_test" in repr(server)
    assert "http://localhost:5000" in repr(server)
