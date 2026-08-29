"""Traces REST API 单元测试

Phase 3 Plan 1C / Task 3: 前端查询 traces 的 REST API
- GET /api/v1/harness/agents/{agent_id}/traces (分页 + conversation/status 过滤)
- GET /api/v1/harness/agents/{agent_id}/traces/{trace_id} (含 steps)

安全要求：
- 租户隔离：强制 filter user_id
"""
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers — 复用 test_admin_traces_api.py 的 dependency_overrides 模式
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
AGENT_ID = uuid.uuid4()
TRACE_ID = uuid.uuid4()
CONV_ID = uuid.uuid4()


def _mock_db_session():
    """创建模拟 DB session，query chain 默认返回空"""
    mock_db = MagicMock()
    mock_q = MagicMock()
    mock_db.query.return_value = mock_q
    mock_q.filter.return_value = mock_q
    mock_q.order_by.return_value = mock_q
    mock_q.offset.return_value = mock_q
    mock_q.limit.return_value.all.return_value = []
    mock_q.count = MagicMock(return_value=0)
    return mock_db


def _override_get_db(mock_db):
    def _fake_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = _fake_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dep_overrides():
    # 默认模拟普通用户登录
    app.dependency_overrides[get_current_user] = lambda: {
        "role": "user", "id": str(USER_ID)
    }
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_list_traces_empty(client):
    """无 trace 时返回空列表"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/harness/agents/{AGENT_ID}/traces")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_traces_with_conversation_filter(client):
    """按 conversation_id 过滤"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(
        f"/api/v1/harness/agents/{AGENT_ID}/traces"
        f"?conversation_id={CONV_ID}"
    )

    assert resp.status_code == 200
    # 验证 filter 被调用时包含 conversation_id 列引用
    # （SQLAlchemy BinaryExpression 编译为 SQL 字符串，包含列名）
    mock_q = mock_db.query.return_value
    filter_calls = mock_q.filter.call_args_list
    all_filter_args = [a for call in filter_calls for a in call.args]
    assert any(
        "conversation_id" in str(a) or str(CONV_ID) in str(a)
        for a in all_filter_args
    )


def test_get_trace_detail_not_found(client):
    """trace 不存在时返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.get(
        f"/api/v1/harness/agents/{AGENT_ID}/traces/{TRACE_ID}"
    )

    assert resp.status_code == 404


def test_list_traces_tenancy_isolation(client):
    """其他用户的 trace 不可见（通过 user_id 强制 filter）"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    client.get(f"/api/v1/harness/agents/{AGENT_ID}/traces")

    mock_q = mock_db.query.return_value
    filter_calls = mock_q.filter.call_args_list
    # 至少有一个 filter 调用包含 user_id 条件
    assert any(
        any("user_id" in str(a) for a in call.args)
        for call in filter_calls
    )
