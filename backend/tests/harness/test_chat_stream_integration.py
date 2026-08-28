"""chat_stream.py 集成测试

Task 16: chat/stream 切换到 AgentRuntime

外部 SSE 形状不变（前端兼容）：
  - user_message: 用户消息 dict（data 字段）
  - chunk: content 增量（content 字段）
  - done: agent 消息 dict（data 字段，含 token 统计）
  - error: message 字段
"""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_current_user
from app.main import app
from app.services.harness.events import Event
from app.services.harness.tool_protocol import ToolCall, ToolResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_sse(response_text: str) -> list:
    """解析 SSE 流为 [{type: ..., ...}, ...] 列表

    SSE 格式为 data: {json}\\n\\n。
    """
    events = []
    for chunk in response_text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        for line in chunk.split("\n"):
            if line.startswith("data: "):
                ev = json.loads(line[6:])
                events.append(ev)
    return events


def _make_conversation_mock():
    m = MagicMock()
    m.id = uuid.uuid4()
    m.user_id = "u1"
    # Session.__init__ 会 dict(conversation.metadata_ or {})
    # MagicMock → dict() 会抛 TypeError；用空 dict 规避
    m.metadata_ = {}
    m.metadata = {}
    return m


def _make_user_message_mock():
    m = MagicMock()
    m.id = uuid.uuid4()
    m.conversation_id = uuid.uuid4()
    m.sender_type = "user"
    m.content = "Hello"
    m.message_type = "text"
    m.sent_at = MagicMock()
    m.sent_at.isoformat.return_value = "2026-08-29T00:00:00+00:00"
    return m


def _make_agent_message_mock():
    m = MagicMock()
    m.id = uuid.uuid4()
    m.conversation_id = uuid.uuid4()
    m.sender_type = "agent"
    m.content = "Hello world"
    m.message_type = "text"
    m.sent_at = MagicMock()
    m.sent_at.isoformat.return_value = "2026-08-29T00:00:00+00:00"
    return m


def _make_create_message_side_effect():
    """构造 create_message 的 side_effect 函数。

    动态根据调用参数返回 mock Message：
    - content / sender_type 从调用参数透传
    - 其他字段使用固定值

    这样在 route 内部 `agent_message.content = ...` 后读取，
    能得到与 ORM 一致的语义（create_message 时传入的 content 即最终 content）。
    """
    call_counter = {"n": 0}

    def side_effect(conversation_id: str, sender_type: str, content: str, **kwargs):
        call_counter["n"] += 1
        m = MagicMock()
        m.id = uuid.uuid4()
        m.conversation_id = conversation_id
        m.sender_type = sender_type
        m.content = content  # 关键：content 与传入参数一致
        m.message_type = "text"
        m.sent_at = MagicMock()
        m.sent_at.isoformat.return_value = "2026-08-29T00:00:00+00:00"
        return m

    return side_effect


def _make_agent_mock():
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.name = "TestAgent"
    agent.slug = "test-agent"
    agent.max_steps_per_turn = 10
    agent.input_guardrails = []
    agent.output_guardrails = []
    agent.memory_short_term_policy = "sliding_window"
    agent.memory_short_term_window = 20
    agent.default_model_id = None
    agent.fallback_model_ids = []
    agent.generation_params = {}
    agent.can_handoff_to = []
    return agent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_user():
    return {"id": "u1", "username": "test", "role": "user"}


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db, fake_user):
    """FastAPI TestClient + dependency overrides。

    使用 app.dependency_overrides 注入 mock DB + mock user，
    绕过真实 JWT 校验与 DB 连接。
    """
    def _override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_services():
    """Mock chat_stream 内部的服务层：ConversationService / MessageService / LLMQuotaService / AgentManagementService。

    返回一个字典，便于测试按名取值。
    """
    with patch("app.api.routes.chat_stream.ConversationService") as mock_conv_cls, \
         patch("app.api.routes.chat_stream.MessageService") as mock_msg_cls, \
         patch("app.api.routes.chat_stream.LLMQuotaService") as mock_quota_cls, \
         patch("app.api.routes.chat_stream.AgentManagementService") as mock_agent_cls:
        mock_conv = MagicMock()
        mock_msg = MagicMock()
        mock_quota = MagicMock()
        mock_quota.check_and_reserve = MagicMock(return_value="res-1")
        mock_quota.record_usage = MagicMock()
        mock_quota.rollback = MagicMock()
        mock_agent_svc = MagicMock()
        mock_agent_svc.get_agent = MagicMock(return_value=_make_agent_mock())
        mock_agent_svc.get_default_agent = MagicMock(return_value=_make_agent_mock())
        mock_conv_cls.return_value = mock_conv
        mock_msg_cls.return_value = mock_msg
        mock_quota_cls.return_value = mock_quota
        mock_agent_cls.return_value = mock_agent_svc
        yield {
            "conv_cls": mock_conv_cls,
            "conv": mock_conv,
            "msg_cls": mock_msg_cls,
            "msg": mock_msg,
            "quota_cls": mock_quota_cls,
            "quota": mock_quota,
            "agent_cls": mock_agent_cls,
            "agent_svc": mock_agent_svc,
        }


@pytest.fixture
def mock_runtime():
    """Mock AgentRuntime class。

    返回 (mock_cls, mock_instance)。测试用 mock_instance.run 注入自定义 Event 序列。
    """
    with patch("app.api.routes.chat_stream.AgentRuntime") as mock_cls:
        instance = MagicMock()
        instance.run = MagicMock()
        mock_cls.return_value = instance
        yield mock_cls, instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_chat_stream_returns_sse(client, mock_services, mock_runtime):
    """SSE 响应头正确 + 流式事件序列（user_message + chunk + done）"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    mock_services["msg"].create_message = MagicMock(side_effect=_make_create_message_side_effect())

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.text_delta("Hi")
        yield Event.text_delta(" there")
        yield Event.done("Hi there", usage={
            "prompt_tokens": 8,
            "completion_tokens": 4,
            "total_tokens": 12,
            "model": "gpt-4",
        })

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hello"},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert "user_message" in types
    assert "chunk" in types
    assert "done" in types


def test_chat_stream_text_delta_to_chunk(client, mock_services, mock_runtime):
    """text_delta 事件 → SSE chunk 事件（保留 content 字段）"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    user_msg = _make_user_message_mock()
    mock_services["msg"].create_message = MagicMock(return_value=user_msg)

    _, instance = mock_runtime

    async def fake_run(user_message):
        for chunk_text in ["He", "llo", " world"]:
            yield Event.text_delta(chunk_text)
        yield Event.done("Hello world")

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    chunks = [e for e in events if e["type"] == "chunk"]
    assert len(chunks) == 3
    contents = [c["content"] for c in chunks]
    assert contents == ["He", "llo", " world"]


def test_chat_stream_done_to_final_message(client, mock_services, mock_runtime):
    """done 事件 → SSE done（含 agent message dict）+ DB 写入 + quota record"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    mock_services["msg"].create_message = MagicMock(side_effect=_make_create_message_side_effect())

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.text_delta("Done text")
        yield Event.done("Done text", usage={
            "prompt_tokens": 20,
            "completion_tokens": 5,
            "total_tokens": 25,
            "model": "claude-3",
        })

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
    done = done_events[0]

    # 外部 SSE 形状兼容：data 字段包含完整 agent message dict
    assert "data" in done
    assert done["data"]["content"] == "Done text"
    assert done["data"]["sender_type"] == "agent"
    assert done["data"]["prompt_tokens"] == 20
    assert done["data"]["completion_tokens"] == 5
    assert done["data"]["total_tokens"] == 25
    assert done["data"]["llm_model_name"] == "claude-3"

    # DB 写入：create_message 被调用两次（user + agent）
    assert mock_services["msg"].create_message.call_count == 2

    # 第二次调用（agent message）参数正确
    second_call = mock_services["msg"].create_message.call_args_list[1]
    assert second_call.kwargs["sender_type"] == "agent"
    assert second_call.kwargs["content"] == "Done text"

    # quota record_usage 被调用
    mock_services["quota"].record_usage.assert_called_once()
    call_kwargs = mock_services["quota"].record_usage.call_args.kwargs
    assert call_kwargs["actual_tokens"] == 25
    assert call_kwargs["reservation_id"] == "res-1"
    assert call_kwargs["model_used"] == "claude-3"


def test_chat_stream_error_rolls_back_quota(client, mock_services, mock_runtime):
    """runtime 抛 Event.error → SSE error 事件 + quota rollback（不调用 record_usage）"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    user_msg = _make_user_message_mock()
    mock_services["msg"].create_message = MagicMock(return_value=user_msg)

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.text_delta("partial")
        yield Event.error("LLM 调用失败", recoverable=False)
        # runtime 在 error 后通常 yield done（带 fallback 文本）
        yield Event.done("fallback message")

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["message"] == "LLM 调用失败"

    # 错误状态下 done SSE 不应出现（跳过 fallback）
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 0

    # quota rollback 被调用；record_usage 不应被调用
    mock_services["quota"].rollback.assert_called_once_with("res-1")
    mock_services["quota"].record_usage.assert_not_called()


def test_chat_stream_404_conversation_not_found(client, mock_services, mock_runtime):
    """conversation 不存在 → 404"""
    mock_services["conv"].get_conversation = MagicMock(return_value=None)

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 404
    body = resp.json()
    assert "会话不存在" in body.get("detail", "")


def test_chat_stream_404_conversation_not_owned(client, mock_services, mock_runtime):
    """conversation 不属于当前用户 → 404

    ConversationService.get_conversation 同时过滤 id + user_id，
    因此不匹配的 conversation 被视为 not_found（返回 None）。
    """
    mock_services["conv"].get_conversation = MagicMock(return_value=None)

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 404


def test_chat_stream_ignores_internal_events(client, mock_services, mock_runtime):
    """runtime 内部事件（thinking / tool_call / handoff / guardrail）不暴露给前端

    Phase 1 兼容策略：只暴露 text_delta + done + error，其他事件静默吞掉。
    """
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    mock_services["msg"].create_message = MagicMock(side_effect=_make_create_message_side_effect())

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.thinking_delta("思考过程...")
        yield Event.text_delta("Hello")
        yield Event.tool_call_start(
            ToolCall(id="c1", name="web_search", arguments={"q": "x"})
        )
        yield Event.tool_result(
            ToolCall(id="c1", name="web_search", arguments={}),
            ToolResult.text("search result"),
        )
        yield Event.guardrail_triggered("filter", "reason", "input")
        yield Event.handoff(
            {"id": "a1", "name": "A"}, {"id": "a2", "name": "B"}, "reason"
        )
        yield Event.done("Hello")

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]

    # 内部事件不应出现在 SSE 中
    assert "thinking_delta" not in types
    assert "tool_call_start" not in types
    assert "tool_result" not in types
    assert "guardrail_triggered" not in types
    assert "handoff" not in types
    # 仅 user_message + chunk + done 应出现
    assert "user_message" in types
    assert "chunk" in types
    assert "done" in types


def test_chat_stream_handles_runtime_exception(client, mock_services, mock_runtime):
    """runtime.run 抛异常 → SSE error 事件 + quota rollback"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    user_msg = _make_user_message_mock()
    mock_services["msg"].create_message = MagicMock(return_value=user_msg)

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.text_delta("partial")
        raise RuntimeError("unexpected crash")

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "unexpected crash" in error_events[0]["message"]

    mock_services["quota"].rollback.assert_called_once_with("res-1")


def test_chat_stream_user_message_event_emitted_first(
    client, mock_services, mock_runtime
):
    """user_message SSE 事件必须是第一个发出的"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    mock_services["msg"].create_message = MagicMock(side_effect=_make_create_message_side_effect())

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.text_delta("Hi")
        yield Event.done("Hi")

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hello"},
    )

    events = _parse_sse(resp.text)
    assert events[0]["type"] == "user_message"
    assert "data" in events[0]
    assert events[0]["data"]["sender_type"] == "user"
    assert events[0]["data"]["content"] == "Hello"


def test_chat_stream_no_quota_rollback_on_success(
    client, mock_services, mock_runtime
):
    """成功时不应调用 rollback（应调用 record_usage）"""
    mock_services["conv"].get_conversation = MagicMock(return_value=_make_conversation_mock())
    mock_services["msg"].create_message = MagicMock(side_effect=_make_create_message_side_effect())

    _, instance = mock_runtime

    async def fake_run(user_message):
        yield Event.text_delta("ok")
        yield Event.done("ok", usage={
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "model": "gpt-4",
        })

    instance.run = fake_run

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat/stream",
        json={"content": "Hi"},
    )

    assert resp.status_code == 200
    mock_services["quota"].rollback.assert_not_called()
    mock_services["quota"].record_usage.assert_called_once()
