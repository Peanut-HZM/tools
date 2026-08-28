"""admin/agents harness 扩展 API 测试

Task 14: admin/agents 扩展 - harness 字段 + 工具绑定 + 统计
- POST /api/v1/admin/agents/{agent_id}/harness        更新 harness 字段
- GET  /api/v1/admin/agents/{agent_id}/harness        获取 harness 字段
- GET  /api/v1/admin/agents/{agent_id}/tools          列出工具绑定
- POST /api/v1/admin/agents/{agent_id}/tools          添加工具绑定（唯一性校验）
- DELETE /api/v1/admin/agents/{agent_id}/tools/{bid}  删除工具绑定
- GET  /api/v1/admin/agents/{agent_id}/harness-stats  单 agent 统计
"""
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent_row(**overrides):
    """构造一个模拟 Agent ORM 对象，含全部 harness 字段"""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.name = overrides.get("name", "Test Agent")
    row.description = overrides.get("description", "Test description")
    row.system_prompt = overrides.get("system_prompt", "Test prompt")
    row.icon = overrides.get("icon", "fa-robot")
    row.icon_color = overrides.get("icon_color", "bg-blue-500")
    row.category = overrides.get("category", "AI工具")
    row.is_active = overrides.get("is_active", True)
    row.is_default = overrides.get("is_default", False)
    row.created_at = overrides.get("created_at", datetime.utcnow())
    row.updated_at = overrides.get("updated_at", datetime.utcnow())
    # Harness 字段
    row.slug = overrides.get("slug", "test-agent")
    row.welcome_message = overrides.get("welcome_message", "Hello!")
    row.default_model_id = overrides.get("default_model_id", None)
    row.fallback_model_ids = overrides.get("fallback_model_ids", [])
    row.generation_params = overrides.get("generation_params", {})
    row.memory_short_term_policy = overrides.get("memory_short_term_policy", "sliding_window")
    row.memory_short_term_window = overrides.get("memory_short_term_window", 20)
    row.memory_long_term_enabled = overrides.get("memory_long_term_enabled", False)
    row.memory_long_term_config = overrides.get("memory_long_term_config", {})
    row.max_steps_per_turn = overrides.get("max_steps_per_turn", 20)
    row.tool_timeout_seconds = overrides.get("tool_timeout_seconds", 60)
    row.error_strategy = overrides.get("error_strategy", "fallback_message")
    row.max_retries = overrides.get("max_retries", 2)
    row.can_handoff_to = overrides.get("can_handoff_to", [])
    row.handoff_instruction = overrides.get("handoff_instruction", None)
    row.input_guardrails = overrides.get("input_guardrails", [])
    row.output_guardrails = overrides.get("output_guardrails", [])
    row.guardrail_on_violation = overrides.get("guardrail_on_violation", "block")
    row.visibility = overrides.get("visibility", "public")
    row.owner_id = overrides.get("owner_id", None)
    return row


def _make_binding_row(**overrides):
    """构造一个模拟 ToolBinding ORM 对象"""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.agent_id = overrides.get("agent_id", uuid.uuid4())
    row.tool_id = overrides.get("tool_id", uuid.uuid4())
    row.parameter_overrides = overrides.get("parameter_overrides", {})
    row.priority = overrides.get("priority", 0)
    row.is_enabled = overrides.get("is_enabled", True)
    row.created_at = overrides.get("created_at", datetime.utcnow())
    row.updated_at = overrides.get("updated_at", datetime.utcnow())
    # Mock tool 关系对象（注意：name 是 MagicMock 的特殊参数，需以 setattr 设置）
    tool_mock = overrides.get("tool", None)
    if tool_mock is None:
        tool_mock = MagicMock()
        tool_mock.id = row.tool_id
        tool_mock.name = "web_search"
        tool_mock.display_name = "Web Search"
    row.tool = tool_mock
    return row


def _mock_db_session():
    """创建一个 mock DB session，query() 返回可链式调用的 mock"""
    mock_db = MagicMock()
    mock_q = MagicMock()
    mock_db.query.return_value = mock_q
    # 链式调用: filter() / order_by() / offset() / limit() / group_by() 均返回自身
    mock_q.filter.return_value = mock_q
    mock_q.order_by.return_value = mock_q
    mock_q.offset.return_value = mock_q
    mock_q.limit.return_value = mock_q
    mock_q.group_by.return_value = mock_q
    # 终端方法默认值（各测试可覆盖）
    mock_q.first.return_value = None
    mock_q.count.return_value = 0
    mock_q.all.return_value = []
    mock_q.scalar.return_value = 0
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
# POST /api/v1/admin/agents/{agent_id}/harness
# ===========================================================================

def test_update_harness_success(client):
    """POST /harness 成功更新 harness 字段"""
    agent_id = str(uuid.uuid4())
    agent = _make_agent_row(id=agent_id)
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = agent
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    _override_get_db(mock_db)

    body = {
        "slug": "new-slug",
        "welcome_message": "Welcome!",
        "memory_short_term_window": 30,
        "max_steps_per_turn": 10,
        "can_handoff_to": ["other-agent"],
        "input_guardrails": [{"type": "pii_filter"}],
    }
    resp = client.post(f"/api/v1/admin/agents/{agent_id}/harness", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "new-slug"
    assert data["welcome_message"] == "Welcome!"
    assert data["memory_short_term_window"] == 30
    assert data["max_steps_per_turn"] == 10
    assert data["can_handoff_to"] == ["other-agent"]
    assert data["input_guardrails"] == [{"type": "pii_filter"}]
    mock_db.commit.assert_called_once()


def test_update_harness_agent_not_found(client):
    """POST /harness agent 不存在返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.post(
        f"/api/v1/admin/agents/{uuid.uuid4()}/harness",
        json={"slug": "test"},
    )
    assert resp.status_code == 404


def test_update_harness_whitelist_blocks_non_harness_fields(client):
    """POST /harness 白名单外字段（name, system_prompt）被忽略"""
    agent_id = str(uuid.uuid4())
    agent = _make_agent_row(id=agent_id, name="Original", system_prompt="Original prompt")
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = agent
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    _override_get_db(mock_db)

    # 同时发送白名单内 + 白名单外字段
    body = {
        "slug": "updated-slug",
        "name": "HACKED",
        "system_prompt": "HACKED PROMPT",
    }
    resp = client.post(f"/api/v1/admin/agents/{agent_id}/harness", json=body)
    assert resp.status_code == 200
    data = resp.json()
    # 白名单内：slug 已更新
    assert data["slug"] == "updated-slug"
    # 白名单外：name / system_prompt 不应被修改
    assert agent.name == "Original"
    assert agent.system_prompt == "Original prompt"


def test_update_harness_non_admin_403(client):
    """非管理员访问 POST /harness 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row()
    _override_get_db(mock_db)

    resp = client.post(
        f"/api/v1/admin/agents/{uuid.uuid4()}/harness",
        json={"slug": "test"},
    )
    assert resp.status_code == 403


# ===========================================================================
# GET /api/v1/admin/agents/{agent_id}/harness
# ===========================================================================

def test_get_harness_success(client):
    """GET /harness 成功返回 harness 扩展字段"""
    agent_id = str(uuid.uuid4())
    agent = _make_agent_row(
        id=agent_id,
        slug="my-agent",
        welcome_message="Hi there",
        memory_short_term_window=15,
        max_retries=3,
    )
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = agent
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{agent_id}/harness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "my-agent"
    assert data["welcome_message"] == "Hi there"
    assert data["memory_short_term_window"] == 15
    assert data["max_retries"] == 3
    # 基本字段也应包含
    assert data["id"] == agent_id
    assert data["name"] == "Test Agent"


def test_get_harness_agent_not_found(client):
    """GET /harness agent 不存在返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/harness")
    assert resp.status_code == 404


def test_get_harness_non_admin_403(client):
    """非管理员访问 GET /harness 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/harness")
    assert resp.status_code == 403


# ===========================================================================
# GET /api/v1/admin/agents/{agent_id}/tools
# ===========================================================================

def test_list_tool_bindings_empty(client):
    """GET /tools 无绑定返回空列表"""
    mock_db = _mock_db_session()
    # agent 存在
    mock_db.query.return_value.first.return_value = _make_agent_row()
    # 绑定列表为空（默认）
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


def test_list_tool_bindings_with_data(client):
    """GET /tools 有绑定时返回绑定列表"""
    agent_id = uuid.uuid4()
    binding = _make_binding_row(agent_id=agent_id)
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row(id=agent_id)
    mock_db.query.return_value.all.return_value = [binding]
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{agent_id}/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(binding.id)
    assert data[0]["tool_id"] == str(binding.tool_id)
    assert data[0]["tool_name"] == "web_search"


def test_list_tool_bindings_agent_not_found(client):
    """GET /tools agent 不存在返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/tools")
    assert resp.status_code == 404


def test_list_tool_bindings_non_admin_403(client):
    """非管理员访问 GET /tools 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/tools")
    assert resp.status_code == 403


# ===========================================================================
# POST /api/v1/admin/agents/{agent_id}/tools
# ===========================================================================

def test_create_tool_binding_success(client):
    """POST /tools 成功创建绑定"""
    agent_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    binding_id = uuid.uuid4()
    mock_db = _mock_db_session()
    # agent 存在
    tool_mock = MagicMock()
    mock_db.query.return_value.first.side_effect = [
        _make_agent_row(id=agent_id),  # 1. agent 查询 → 存在
        tool_mock,                      # 2. tool 查询 → 存在
        None,                           # 3. binding 唯一性检查 → 不存在
        MagicMock(),                    # 4. binding.tool 懒加载（_binding_to_view）
    ]

    # db.add() side_effect: 模拟 flush 后填充 id
    binding_tool_mock = MagicMock()
    binding_tool_mock.name = "web_search"
    binding_tool_mock.display_name = "Web Search"

    def add_then_fill(obj):
        obj.id = binding_id
        obj.created_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        obj.tool = binding_tool_mock  # 模拟 relationship 预加载

    mock_db.add = MagicMock(side_effect=add_then_fill)
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    _override_get_db(mock_db)

    body = {
        "tool_id": str(tool_id),
        "parameter_overrides": {"timeout": 30},
        "priority": 5,
        "is_enabled": True,
    }
    resp = client.post(f"/api/v1/admin/agents/{agent_id}/tools", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tool_id"] == str(tool_id)
    assert data["priority"] == 5
    mock_db.commit.assert_called_once()


def test_create_tool_binding_duplicate_returns_400(client):
    """POST /tools 重复绑定（agent_id + tool_id）返回 400"""
    agent_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    mock_db = _mock_db_session()
    # agent 存在, tool 存在, binding 已存在（唯一性冲突）
    mock_db.query.return_value.first.side_effect = [
        _make_agent_row(id=agent_id),  # 1. agent 查询 → 存在
        MagicMock(),                    # 2. tool 查询 → 存在
        MagicMock(),                    # 3. binding 唯一性检查 → 已存在（触发 400）
    ]
    _override_get_db(mock_db)

    body = {"tool_id": str(tool_id)}
    resp = client.post(f"/api/v1/admin/agents/{agent_id}/tools", json=body)
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower() or "已存在" in resp.json()["detail"]


def test_create_tool_binding_agent_not_found(client):
    """POST /tools agent 不存在返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = None
    _override_get_db(mock_db)

    body = {"tool_id": str(uuid.uuid4())}
    resp = client.post(f"/api/v1/admin/agents/{uuid.uuid4()}/tools", json=body)
    assert resp.status_code == 404


def test_create_tool_binding_tool_not_found(client):
    """POST /tools 工具不存在返回 404"""
    agent_id = uuid.uuid4()
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.side_effect = [
        _make_agent_row(id=agent_id),  # agent 存在
        None,                           # 工具不存在
    ]
    _override_get_db(mock_db)

    body = {"tool_id": str(uuid.uuid4())}
    resp = client.post(f"/api/v1/admin/agents/{agent_id}/tools", json=body)
    assert resp.status_code == 404


def test_create_tool_binding_non_admin_403(client):
    """非管理员访问 POST /tools 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row()
    _override_get_db(mock_db)

    body = {"tool_id": str(uuid.uuid4())}
    resp = client.post(f"/api/v1/admin/agents/{uuid.uuid4()}/tools", json=body)
    assert resp.status_code == 403


# ===========================================================================
# DELETE /api/v1/admin/agents/{agent_id}/tools/{binding_id}
# ===========================================================================

def test_delete_tool_binding_success(client):
    """DELETE /tools/{binding_id} 成功删除"""
    agent_id = uuid.uuid4()
    binding_id = uuid.uuid4()
    binding = _make_binding_row(id=binding_id, agent_id=agent_id)
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.side_effect = [
        _make_agent_row(id=agent_id),  # agent 存在
        binding,                        # binding 存在
    ]
    mock_db.commit = MagicMock()
    _override_get_db(mock_db)

    resp = client.delete(f"/api/v1/admin/agents/{agent_id}/tools/{binding_id}")
    assert resp.status_code == 200
    mock_db.commit.assert_called_once()
    mock_db.delete.assert_called_once_with(binding)


def test_delete_tool_binding_agent_not_found(client):
    """DELETE /tools/{binding_id} agent 不存在返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.delete(f"/api/v1/admin/agents/{uuid.uuid4()}/tools/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_delete_tool_binding_not_found(client):
    """DELETE /tools/{binding_id} binding 不存在返回 404"""
    agent_id = uuid.uuid4()
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.side_effect = [
        _make_agent_row(id=agent_id),  # agent 存在
        None,                           # binding 不存在
    ]
    _override_get_db(mock_db)

    resp = client.delete(f"/api/v1/admin/agents/{agent_id}/tools/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_delete_tool_binding_non_admin_403(client):
    """非管理员访问 DELETE /tools/{binding_id} 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row()
    _override_get_db(mock_db)

    resp = client.delete(
        f"/api/v1/admin/agents/{uuid.uuid4()}/tools/{uuid.uuid4()}"
    )
    assert resp.status_code == 403


# ===========================================================================
# GET /api/v1/admin/agents/{agent_id}/harness-stats
# ===========================================================================

def test_get_harness_stats_success(client):
    """GET /harness-stats 成功返回统计"""
    agent_id = uuid.uuid4()
    mock_db = _mock_db_session()
    mock_q = mock_db.query.return_value
    # agent 存在
    mock_q.first.return_value = _make_agent_row(id=agent_id)
    # 对话数 / 消息数: query(...).filter(...).count()
    mock_q.count.return_value = 5
    # trace 统计: query(func.sum(...)).filter(...).scalar()
    mock_q.scalar.return_value = 1000
    # 工具使用频率: query(...).group_by(...).all()
    mock_q.all.return_value = [("web_search", 3), ("db_query", 2)]
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{agent_id}/harness-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_count" in data
    assert "trace_count" in data
    assert "total_tokens" in data
    assert "total_duration_ms" in data
    assert "tool_usage" in data


def test_get_harness_stats_agent_not_found(client):
    """GET /harness-stats agent 不存在返回 404"""
    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = None
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/harness-stats")
    assert resp.status_code == 404


def test_get_harness_stats_non_admin_403(client):
    """非管理员访问 GET /harness-stats 返回 403"""
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": "u1"}

    mock_db = _mock_db_session()
    mock_db.query.return_value.first.return_value = _make_agent_row()
    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{uuid.uuid4()}/harness-stats")
    assert resp.status_code == 403


def test_harness_stats_tool_usage_filters_by_agent(client):
    """回归测试：harness-stats 的 tool_usage 必须按 agent_id 过滤，不能跨 agent 泄露

    通过 mock 捕获 route 内 tool_usage query 的 filter 调用链，
    断言包含 `Trace.agent_id == agent_id` 过滤条件，以验证跨 agent 隔离。
    """
    from app.models.harness_models import Trace

    agent_id = uuid.uuid4()

    # 构造一个 mock db，捕获所有 .filter() 的入参
    mock_db = MagicMock()
    mock_q = MagicMock()
    mock_db.query.return_value = mock_q
    for m in ("filter", "order_by", "offset", "limit", "group_by", "join"):
        getattr(mock_q, m).return_value = mock_q
    mock_q.first.return_value = _make_agent_row(id=agent_id)
    mock_q.count.return_value = 0
    mock_q.scalar.return_value = 0
    mock_q.all.return_value = [("web_search", 3), ("db_query", 2)]

    _override_get_db(mock_db)

    resp = client.get(f"/api/v1/admin/agents/{agent_id}/harness-stats")
    assert resp.status_code == 200

    # 检查所有 .filter() 调用入参，断言其中至少一个的 SQL 编译结果
    # 同时引用 Trace.agent_id 列（防止跨 agent 数据泄露）
    from sqlalchemy.dialects import postgresql
    filter_calls = mock_q.filter.call_args_list
    found = False
    for call in filter_calls:
        for arg in call.args:
            try:
                compiled = str(
                    arg.compile(
                        dialect=postgresql.dialect(),
                        compile_kwargs={"literal_binds": True},
                    )
                )
            except Exception:
                compiled = ""
            if "agent_traces" in compiled and "agent_id" in compiled:
                found = True
                break
        if found:
            break

    if not found:
        debug_info = []
        for i, call in enumerate(filter_calls):
            for j, arg in enumerate(call.args):
                try:
                    c = str(
                        arg.compile(
                            dialect=postgresql.dialect(),
                            compile_kwargs={"literal_binds": True},
                        )
                    )
                except Exception as e:
                    c = f"<compile error: {e}>"
                debug_info.append(f"filter[{i}].args[{j}]: {c}")
        raise AssertionError(
            "tool_usage 查询未包含 Trace.agent_id 过滤条件。\n"
            + "\n".join(debug_info)
        )

    # 同时确认调用了 .join(Trace, ...)，因为只有 join 后 Trace.agent_id 才能参与过滤
    assert mock_q.join.called, "tool_usage 查询应 join Trace 表，但未发现 .join 调用"
