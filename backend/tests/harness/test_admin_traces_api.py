"""admin/traces API 测试

Task 15: 追踪查询端点（observability）
- GET /api/v1/admin/traces                            列表（agent_id / user_id / status / 时间范围 过滤 + 分页）
- GET /api/v1/admin/traces/{trace_id}                 详情（含 steps 子查询）
- GET /api/v1/admin/traces/agent/{agent_id}/recent    单 agent 最近 traces（强制 filter agent_id）

安全要求（来自 Task 14 fix round 1 教训）：
- 所有按 agent 过滤的端点必须 filter agent_id（不能全表扫描）
- list_traces 支持 agent_id 过滤；query 应 Trace.agent_id == agent_id
- recent 端点必须 filter agent_id
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace_row(**overrides):
    """构造一个模拟 Trace ORM 对象"""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.conversation_id = overrides.get("conversation_id", uuid.uuid4())
    row.agent_id = overrides.get("agent_id", uuid.uuid4())
    row.user_id = overrides.get("user_id", uuid.uuid4())
    row.input_text = overrides.get("input_text", "用户问题")
    row.output_text = overrides.get("output_text", "AI 回答")
    row.status = overrides.get("status", "success")
    row.total_steps = overrides.get("total_steps", 3)
    row.total_tokens = overrides.get("total_tokens", 1500)
    row.total_duration_ms = overrides.get("total_duration_ms", 1200)
    row.error_message = overrides.get("error_message", None)
    row.metadata_ = overrides.get("metadata_", {})
    row.started_at = overrides.get("started_at", datetime.utcnow())
    row.completed_at = overrides.get("completed_at", datetime.utcnow())
    return row


def _make_step_row(**overrides):
    """构造一个模拟 TraceStep ORM 对象"""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.trace_id = overrides.get("trace_id", uuid.uuid4())
    row.step_index = overrides.get("step_index", 1)
    row.step_type = overrides.get("step_type", "llm_call")
    row.tool_name = overrides.get("tool_name", None)
    row.llm_model = overrides.get("llm_model", "gpt-4")
    row.tokens_used = overrides.get("tokens_used", 500)
    row.duration_ms = overrides.get("duration_ms", 600)
    row.input_summary = overrides.get("input_summary", "user input summary")
    row.output_summary = overrides.get("output_summary", "model output summary")
    row.error_message = overrides.get("error_message", None)
    return row


def _mock_db_session():
    """构造可链式调用的 mock DB session"""
    mock_db = MagicMock()
    mock_q = MagicMock()
    mock_db.query.return_value = mock_q
    # 链式调用
    mock_q.filter.return_value = mock_q
    mock_q.order_by.return_value = mock_q
    mock_q.offset.return_value = mock_q
    mock_q.limit.return_value = mock_q
    # 终端方法默认值
    mock_q.first.return_value = None
    mock_q.count.return_value = 0
    mock_q.all.return_value = []
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
    # 默认模拟管理员登录
    app.dependency_overrides[get_current_user] = lambda: {"role": "admin", "id": "test-admin"}
    yield
    app.dependency_overrides.clear()


# ===========================================================================
# GET /api/v1/admin/traces（list）
# ===========================================================================

def test_list_traces_empty(client):
    """GET /admin/traces 应返回空列表"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_traces_with_items(client):
    """GET /admin/traces 有数据时返回 items 列表"""
    mock_db = _mock_db_session()
    trace = _make_trace_row()
    mock_db.query.return_value.count.return_value = 1
    mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [trace]
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "success"


def test_list_traces_filter_by_agent_id(client):
    """GET /admin/traces?agent_id=xxx 应使用 agent_id 过滤"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    agent_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/admin/traces?agent_id={agent_id}")
    assert resp.status_code == 200
    # filter 应被调用以应用 agent_id 过滤
    mock_db.query.return_value.filter.assert_called()


def test_list_traces_filter_by_user_id(client):
    """GET /admin/traces?user_id=xxx 应使用 user_id 过滤"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    user_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/admin/traces?user_id={user_id}")
    assert resp.status_code == 200
    mock_db.query.return_value.filter.assert_called()


def test_list_traces_filter_by_status(client):
    """GET /admin/traces?status=success 应过滤 status"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/traces?status=success")
    assert resp.status_code == 200
    mock_db.query.return_value.filter.assert_called()


def test_list_traces_filter_by_time_range(client):
    """GET /admin/traces?start_time=...&end_time=... 应解析 ISO 时间"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    start = (datetime.utcnow() - timedelta(days=1)).isoformat()
    end = datetime.utcnow().isoformat()
    resp = client.get(f"/api/v1/admin/traces?start_time={start}&end_time={end}")
    assert resp.status_code == 200
    mock_db.query.return_value.filter.assert_called()


def test_list_traces_pagination(client):
    """GET /admin/traces?skip=10&limit=20 应支持分页"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/traces?skip=10&limit=20")
    assert resp.status_code == 200


def test_list_traces_invalid_status_returns_422(client):
    """GET /admin/traces?status=invalid 应返回 422"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/traces?status=invalid_status")
    assert resp.status_code == 422


def test_list_traces_non_admin_returns_403(client):
    """非管理员访问 /admin/traces 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get("/api/v1/admin/traces")
    assert resp.status_code == 403


# ===========================================================================
# GET /api/v1/admin/traces/agent/{agent_id}/recent
# 必须在 GET /api/v1/admin/traces/{trace_id} 之前注册（路由顺序）
# ===========================================================================

def test_recent_agent_traces_success(client):
    """GET /admin/traces/agent/{agent_id}/recent 应返回该 agent 的 traces"""
    agent_id = uuid.uuid4()
    trace = _make_trace_row(agent_id=agent_id)
    mock_db = _mock_db_session()
    # q.count() 在 filter 链上 -> 1; q.order_by().limit().all() 在新链上 -> [trace]
    # filter 链默认返回 mock_q（即自身），count() 和 order_by() 等链式调用都在其上
    mock_q = mock_db.query.return_value
    mock_q.count.return_value = 1
    mock_q.order_by.return_value.limit.return_value.all.return_value = [trace]
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/agent/{agent_id}/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["agent_id"] == str(agent_id)


def test_recent_agent_traces_empty(client):
    """GET /admin/traces/agent/{agent_id}/recent 无数据时返回空列表"""
    agent_id = uuid.uuid4()
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/agent/{agent_id}/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_recent_agent_traces_filter_agent_id(client):
    """GET /admin/traces/agent/{agent_id}/recent 必须 filter agent_id（不能全表扫描）"""
    agent_id = uuid.uuid4()
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/agent/{agent_id}/recent")
    assert resp.status_code == 200
    # 关键安全要求：filter 必须被调用以应用 agent_id 过滤
    mock_db.query.return_value.filter.assert_called()


def test_recent_agent_traces_non_admin_returns_403(client):
    """非管理员访问 /admin/traces/agent/{agent_id}/recent 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    agent_id = uuid.uuid4()
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/agent/{agent_id}/recent")
    assert resp.status_code == 403


# ===========================================================================
# GET /api/v1/admin/traces/{trace_id}
# ===========================================================================

def test_get_trace_not_found(client):
    """GET /admin/traces/{id} 不存在应返回 404"""
    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_trace_with_steps(client):
    """GET /admin/traces/{id} 存在时返回 trace + steps"""
    trace_id = uuid.uuid4()
    trace = _make_trace_row(id=trace_id)
    step1 = _make_step_row(trace_id=trace_id, step_index=1, step_type="llm_call")
    step2 = _make_step_row(trace_id=trace_id, step_index=2, step_type="tool_call", tool_name="web_search")

    mock_db = _mock_db_session()
    # 第一次 query(Trace)  -> 返回 trace
    # 第二次 query(TraceStep) -> 返回 steps 列表
    trace_q = MagicMock()
    trace_q.filter.return_value = trace_q
    trace_q.first.return_value = trace
    step_q = MagicMock()
    step_q.filter.return_value = step_q
    step_q.order_by.return_value = step_q
    step_q.all.return_value = [step1, step2]
    mock_db.query.side_effect = [trace_q, step_q]
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/{trace_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(trace_id)
    assert len(data["steps"]) == 2
    assert data["steps"][0]["step_index"] == 1
    assert data["steps"][1]["step_type"] == "tool_call"


def test_get_trace_non_admin_returns_403(client):
    """非管理员访问 /admin/traces/{id} 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/traces/{uuid.uuid4()}")
    assert resp.status_code == 403