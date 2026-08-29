"""Runtime checkpoint 集成测试

验证 AgentRuntime 在 3 个时机（after_user_message / before_tool / after_tool）
调用 CheckpointService.write_checkpoint 写入完整快照 checkpoint。

参考：spec §7 + Phase 3-Plan-1D Task 3 brief
"""
import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.harness.agent_runtime import AgentRuntime
from app.services.harness.checkpoint_service import CheckpointService
from app.services.harness.events import Event
from app.services.harness.llm_bridge import LLMResponse
from app.services.harness.tool_protocol import ToolCall, ToolContext, ToolResult


# ----------------------------------------------------------------------
# Mock 工厂
# ----------------------------------------------------------------------


def _make_agent(**overrides):
    """构造一个测试用 agent mock"""
    agent = MagicMock()
    agent.id = "agent-1"
    agent.name = "Test Agent"
    agent.slug = "test-agent"
    agent.is_active = True
    agent.max_steps_per_turn = 10
    agent.input_guardrails = []
    agent.output_guardrails = []
    agent.memory_short_term_policy = "full"
    agent.memory_short_term_window = 20
    agent.memory_long_term_window = 20
    agent.memory_long_term_enabled = False
    agent.error_strategy = "fallback_message"
    agent.can_handoff_to = []
    agent.default_model_id = "gpt-4"
    agent.fallback_model_ids = []
    agent.generation_params = {}
    agent.guardrail_on_violation = "block"
    for k, v in overrides.items():
        setattr(agent, k, v)
    return agent


def _make_ctx():
    """构造一个测试用 ToolContext mock"""
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-1"
    ctx.conversation_id = "conv-1"
    ctx.agent_id = "agent-1"
    ctx.cancel_event = MagicMock()
    ctx.cancel_event.is_set = MagicMock(return_value=False)
    ctx.trace_recorder = MagicMock()
    ctx.trace_recorder.start_trace = MagicMock(return_value=MagicMock(id="trace-1"))
    ctx.trace_recorder.start_step = MagicMock()
    ctx.trace_recorder.end_step = MagicMock()
    ctx.trace_recorder.end_trace = MagicMock()
    ctx.db = MagicMock()
    return ctx


def _make_session(main_branch_id=None, messages=None):
    """构造一个测试用 session mock（带 conversation.main_branch_id）"""
    session = MagicMock()
    session.messages = messages if messages is not None else []
    conversation = MagicMock(id="conv-1")
    conversation.main_branch_id = main_branch_id
    session.conversation = conversation
    return session


# ----------------------------------------------------------------------
# 测试 1：after_user_message 时机
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_writes_checkpoint_after_user_message():
    """Runtime 应在用户消息后写入 checkpoint（phase=after_user_message）"""
    agent = _make_agent()
    main_branch_id = uuid.uuid4()
    session = _make_session(main_branch_id=main_branch_id)

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="Hi!", tool_calls=[]))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        async for _ in runtime.run("Hi"):
            pass

    # 验证：write_checkpoint 至少被调用一次，且 phase=after_user_message
    assert mock_write.call_count >= 1
    phases = [call.kwargs.get("phase") for call in mock_write.call_args_list]
    assert "after_user_message" in phases


@pytest.mark.asyncio
async def test_runtime_after_user_message_passes_branch_id_from_conversation():
    """Runtime 应使用 conversation.main_branch_id 作为 branch_id"""
    agent = _make_agent()
    main_branch_id = uuid.uuid4()
    session = _make_session(main_branch_id=main_branch_id)

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="OK", tool_calls=[]))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        async for _ in runtime.run("Hi"):
            pass

    # 找到 after_user_message 的调用，验证 branch_id
    after_user_calls = [
        c for c in mock_write.call_args_list
        if c.kwargs.get("phase") == "after_user_message"
    ]
    assert len(after_user_calls) == 1
    assert after_user_calls[0].kwargs["branch_id"] == main_branch_id
    assert after_user_calls[0].kwargs["conversation_id"] == session.conversation.id


# ----------------------------------------------------------------------
# 测试 2：before_tool / after_tool 时机
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_writes_checkpoint_before_and_after_tool():
    """Runtime 应在工具调用前后各写一个 checkpoint（before_tool + after_tool）"""
    agent = _make_agent()
    main_branch_id = uuid.uuid4()
    session = _make_session(main_branch_id=main_branch_id)

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[MagicMock(
        name="web_search", to_function_schema=MagicMock(return_value={})
    )])
    tool_registry.execute = AsyncMock(return_value=ToolResult.text("search result"))
    tool_registry.to_function_schemas = MagicMock(return_value=[{}])

    llm_bridge = MagicMock()
    # 第一次：工具调用；第二次：最终回复
    llm_bridge.generate = AsyncMock(side_effect=[
        LLMResponse(text_part="", tool_calls=[
            ToolCall(id="call_1", name="web_search", arguments={"query": "x"})
        ]),
        LLMResponse(text_part="Done", tool_calls=[]),
    ])

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        async for _ in runtime.run("search"):
            pass

    phases = [c.kwargs.get("phase") for c in mock_write.call_args_list]
    assert "before_tool" in phases
    assert "after_tool" in phases


@pytest.mark.asyncio
async def test_runtime_before_tool_called_with_same_step_as_after_tool():
    """before_tool 与 after_tool 应使用相同的 step_index"""
    agent = _make_agent()
    main_branch_id = uuid.uuid4()
    session = _make_session(main_branch_id=main_branch_id)

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[MagicMock(
        name="dummy", to_function_schema=MagicMock(return_value={})
    )])
    tool_registry.execute = AsyncMock(return_value=ToolResult.text("ok"))
    tool_registry.to_function_schemas = MagicMock(return_value=[{}])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(side_effect=[
        LLMResponse(text_part="", tool_calls=[
            ToolCall(id="c1", name="dummy", arguments={})
        ]),
        LLMResponse(text_part="done", tool_calls=[]),
    ])

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        async for _ in runtime.run("loop"):
            pass

    before_calls = [c for c in mock_write.call_args_list if c.kwargs.get("phase") == "before_tool"]
    after_calls = [c for c in mock_write.call_args_list if c.kwargs.get("phase") == "after_tool"]

    assert len(before_calls) == 1
    assert len(after_calls) == 1
    assert before_calls[0].kwargs["step_index"] == after_calls[0].kwargs["step_index"]


# ----------------------------------------------------------------------
# 测试 3：懒加载创建 main branch
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_creates_main_branch_if_missing():
    """Runtime 在 main_branch_id 缺失时应懒加载创建主线分支"""
    agent = _make_agent()
    # main_branch_id 为 None（首次 turn）
    session = _make_session(main_branch_id=None)
    new_branch_id = uuid.uuid4()

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="OK", tool_calls=[]))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        async for _ in runtime.run("Hi"):
            pass

    # 主线分支应已被设置到 conversation.main_branch_id
    assert session.conversation.main_branch_id is not None
    # write_checkpoint 收到的 branch_id 应等于新设置的 main_branch_id
    user_calls = [
        c for c in mock_write.call_args_list
        if c.kwargs.get("phase") == "after_user_message"
    ]
    assert user_calls[0].kwargs["branch_id"] == session.conversation.main_branch_id


# ----------------------------------------------------------------------
# 测试 4：checkpoint 写入失败不应导致主循环崩溃（best-effort）
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_checkpoint_failure_does_not_crash():
    """write_checkpoint 抛异常时主循环应继续运行"""
    agent = _make_agent()
    main_branch_id = uuid.uuid4()
    session = _make_session(main_branch_id=main_branch_id)

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="OK", tool_calls=[]))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        # 模拟 checkpoint 写入抛异常
        mock_write.side_effect = RuntimeError("DB down")
        events = []
        async for event in runtime.run("Hi"):
            events.append(event)

    # 主循环应正常完成
    event_types = [e.type for e in events]
    assert "done" in event_types


# ----------------------------------------------------------------------
# 测试 5：messages 快照传递
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_passes_current_messages_to_checkpoint():
    """Runtime 应把当前 session.messages 列表传给 CheckpointService"""
    agent = _make_agent()
    main_branch_id = uuid.uuid4()

    # 真实 list + 真实 append，让 session.messages 累积内容
    real_session = MagicMock()
    real_session.messages = []
    real_session.conversation = MagicMock(id="conv-1", main_branch_id=main_branch_id)

    def fake_append_user_message(content):
        msg = MagicMock()
        real_session.messages.append(msg)
        return msg

    real_session.append_user_message = MagicMock(side_effect=fake_append_user_message)

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="OK", tool_calls=[]))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, real_session, ctx)

    with patch.object(CheckpointService, "write_checkpoint") as mock_write:
        async for _ in runtime.run("Hi"):
            pass

    user_calls = [
        c for c in mock_write.call_args_list
        if c.kwargs.get("phase") == "after_user_message"
    ]
    assert len(user_calls) == 1
    # messages 应是非空 list（包含用户消息后追加的对象）
    msgs_passed = user_calls[0].kwargs["messages"]
    assert isinstance(msgs_passed, list)
    assert len(msgs_passed) >= 1