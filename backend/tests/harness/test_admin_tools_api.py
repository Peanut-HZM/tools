"""admin/tools API 测试

Task 13: 工具管理端点
- GET /api/v1/admin/tools          列表（type / search 过滤 + 分页）
- POST /api/v1/admin/tools         注册（name 唯一性校验）
- GET  /api/v1/admin/tools/builtin 内置工具清单
- GET  /api/v1/admin/tools/{id}    详情
- PUT  /api/v1/admin/tools/{id}    更新
- DELETE /api/v1/admin/tools/{id}  删除
"""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dep_overrides():
    """每个用例结束后清理依赖覆盖"""
    yield
    app.dependency_overrides.clear()


def _make_tool_row(**overrides):
    """构造一个模拟 ORM Tool 对象，带默认字段"""
    row = MagicMock()
    row.id = overrides.get("id", str(uuid.uuid4()))
    row.name = overrides.get("name", "test_tool")
    row.display_name = overrides.get("display_name", "Test Tool")
    row.description = overrides.get("description", "A test tool")
    row.type = overrides.get("type", "http")
    row.config = overrides.get("config", {})
    row.parameters_schema = overrides.get("parameters_schema", {})
    row.returns_schema = overrides.get("returns_schema", None)
    row.is_available_condition = overrides.get("is_available_condition", {})
    row.rate_limit_per_minute = overrides.get("rate_limit_per_minute", None)
    row.metadata_ = overrides.get("metadata_", {})
    row.is_active = overrides.get("is_active", True)
    row.created_at = overrides.get("created_at", datetime.utcnow())
    row.updated_at = overrides.get("updated_at", datetime.utcnow())
    return row


def _mock_db_session():
    """创建一个 MagicMock 作为 mock DB session"""
    return MagicMock()


def _override_get_db(mock_db):
    """注册 dependency_overrides，使 get_db 返回 mock_db"""

    def _fake_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _fake_get_db


def test_list_tools_empty(client):
    """GET /api/v1/admin/tools 应返回列表"""
    mock_db = _mock_db_session()
    # 无过滤时：q = db.query(Tool)，直接调 q.count() / q.order_by(...)
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] == 0
    assert data["items"] == []


def test_list_tools_with_items(client):
    """GET /api/v1/admin/tools 有数据时返回 items 列表"""
    mock_db = _mock_db_session()
    row = _make_tool_row(name="weather", display_name="Weather")
    mock_db.query.return_value.count.return_value = 1
    mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [row]
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "weather"


def test_list_tools_filter_by_type(client):
    """GET /api/v1/admin/tools?type=http 应传 type 过滤"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/tools?type=http")
    assert resp.status_code == 200
    mock_db.query.assert_called()


def test_create_http_tool(client):
    """POST /api/v1/admin/tools 应创建 HTTP 工具"""
    payload = {
        "name": "weather_test",
        "display_name": "Weather",
        "description": "Test weather tool",
        "type": "http",
        "config": {
            "url": "https://api.example.com/weather",
            "method": "GET",
            "response_parser": {},
        },
        "parameters_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }

    mock_db = _mock_db_session()
    # Name uniqueness check — return None (no conflict)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # db.add() side_effect: 模拟 flush 后填充服务端默认值
    def add_then_refresh(obj):
        obj.id = str(uuid.uuid4())
        obj.created_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        obj.is_active = True

    mock_db.add = MagicMock(side_effect=add_then_refresh)
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    _override_get_db(mock_db)

    resp = client.post("/api/v1/admin/tools", json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "weather_test"
    assert data["type"] == "http"
    assert data["display_name"] == "Weather"


def test_create_tool_duplicate_name_returns_400(client):
    """POST /api/v1/admin/tools 重复 name 应返回 400"""
    payload = {
        "name": "existing_tool",
        "display_name": "Existing",
        "description": "Already exists",
        "type": "http",
        "config": {},
        "parameters_schema": {},
    }

    mock_db = _mock_db_session()
    # Simulate name conflict
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    _override_get_db(mock_db)

    resp = client.post("/api/v1/admin/tools", json=payload)
    assert resp.status_code == 400


def test_create_tool_invalid_type_returns_422(client):
    """POST /api/v1/admin/tools 非法 type 应返回 422"""
    payload = {
        "name": "bad_type",
        "display_name": "Bad",
        "description": "Invalid type",
        "type": "invalid_type",
        "config": {},
        "parameters_schema": {},
    }

    resp = client.post("/api/v1/admin/tools", json=payload)
    assert resp.status_code == 422


def test_get_tool_not_found(client):
    """GET /api/v1/admin/tools/{id} 不存在应返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/tools/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_tool_found(client):
    """GET /api/v1/admin/tools/{id} 存在时返回工具详情"""
    tool_id = str(uuid.uuid4())
    mock_db = _mock_db_session()
    row = _make_tool_row(id=tool_id, name="my_tool")
    mock_db.query.return_value.filter.return_value.first.return_value = row
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/tools/{tool_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "my_tool"
    assert data["id"] == tool_id


def test_update_tool_not_found(client):
    """PUT /api/v1/admin/tools/{id} 不存在应返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.put(
        "/api/v1/admin/tools/00000000-0000-0000-0000-000000000000",
        json={"display_name": "New Name"},
    )
    assert resp.status_code == 404


def test_update_tool_success(client):
    """PUT /api/v1/admin/tools/{id} 成功更新"""
    tool_id = str(uuid.uuid4())
    mock_db = _mock_db_session()
    row = _make_tool_row(id=tool_id, name="orig", display_name="Orig")
    mock_db.query.return_value.filter.return_value.first.return_value = row
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    _override_get_db(mock_db)

    resp = client.put(
        f"/api/v1/admin/tools/{tool_id}",
        json={"display_name": "Updated"},
    )
    assert resp.status_code == 200
    assert row.display_name == "Updated"
    mock_db.commit.assert_called_once()


def test_delete_tool_not_found(client):
    """DELETE /api/v1/admin/tools/{id} 不存在应返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.delete("/api/v1/admin/tools/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_delete_tool_success(client):
    """DELETE /api/v1/admin/tools/{id} 成功删除返回 204"""
    mock_db = _mock_db_session()
    row = _make_tool_row()
    mock_db.query.return_value.filter.return_value.first.return_value = row
    mock_db.commit = MagicMock()
    _override_get_db(mock_db)

    resp = client.delete(f"/api/v1/admin/tools/{uuid.uuid4()}")
    assert resp.status_code == 204
    mock_db.delete.assert_called_once_with(row)
    mock_db.commit.assert_called_once()


def test_list_builtin_tools(client):
    """GET /api/v1/admin/tools/builtin 应返回内置工具列表"""
    with patch("app.api.routes.admin_tools._get_builtin_tools") as mock_builtins:
        from app.services.harness.tools.web_search import WebSearchTool
        from app.services.harness.tools.db_query import DbQueryTool

        mock_builtins.return_value = [WebSearchTool(), DbQueryTool()]

        resp = client.get("/api/v1/admin/tools/builtin")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        names = [t["name"] for t in data["items"]]
        assert "web_search" in names
        assert "db_query" in names
