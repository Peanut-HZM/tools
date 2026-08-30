"""AgentRuntime 核心循环测试

参考 spec §7.2
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.harness.agent_runtime import AgentRuntime
from app.services.harness.events import Event
from app.services.harness.tool_protocol import ToolContext, ToolResult, ToolCall
from app.services.harness.llm_bridge import LLMResponse


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


@pytest.mark.asyncio
async def test_runtime_simple_response():
    """无工具调用的简单回复"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    tool_registry.to_function_schemas = MagicMock(return_value=[])
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(
        text_part="Hello!", tool_calls=[]
    ))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)

    events = []
    async for event in runtime.run("Hi"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "done" in event_types
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_runtime_input_guardrail_blocks():
    """输入 guardrail 阻断时不应调用 LLM"""
    agent = _make_agent(input_guardrails=[{"name": "filter", "tool_id": "x"}])
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock()  # 不应被调用
    ctx = _make_ctx()

    with patch("app.services.harness.agent_runtime.run_input_guardrails") as mock_gr:
        mock_gr.return_value = MagicMock(
            blocked=True, guardrail_name="filter", reason="blocked", stage="input"
        )

        runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
        events = []
        async for event in runtime.run("bad input"):
            events.append(event)

        # LLM 不应被调用
        llm_bridge.generate.assert_not_awaited()

        event_types = [e.type for e in events]
        assert "guardrail_triggered" in event_types
        assert "done" in event_types


@pytest.mark.asyncio
async def test_runtime_tool_call_then_response():
    """工具调用后继续 LLM 循环"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[MagicMock(
        name="web_search", to_function_schema=MagicMock(return_value={})
    )])
    tool_registry.execute = AsyncMock(return_value=ToolResult.text("search result"))

    llm_bridge = MagicMock()
    # 第一次返回工具调用，第二次返回最终回复
    llm_bridge.generate = AsyncMock(side_effect=[
        LLMResponse(text_part="", tool_calls=[
            ToolCall(id="call_1", name="web_search", arguments={"query": "x"})
        ]),
        LLMResponse(text_part="Found it!", tool_calls=[]),
    ])
    tool_registry.to_function_schemas = MagicMock(return_value=[{}])

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    async for event in runtime.run("search"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "tool_call_start" in event_types
    assert "tool_result" in event_types
    # LLM 被调用两次
    assert llm_bridge.generate.await_count == 2


@pytest.mark.asyncio
async def test_runtime_cancelled():
    """cancel_event 被设置时应提前终止"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    tool_registry.to_function_schemas = MagicMock(return_value=[])
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="Hello!", tool_calls=[]))

    ctx = _make_ctx()
    ctx.cancel_event.is_set = MagicMock(return_value=True)

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    async for event in runtime.run("Hi"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "error" in event_types
    # LLM 不应被调用
    llm_bridge.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_max_steps_reached():
    """达到最大步数限制时应终止"""
    agent = _make_agent(max_steps_per_turn=2)
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[MagicMock(
        name="dummy", to_function_schema=MagicMock(return_value={})
    )])
    tool_registry.execute = AsyncMock(return_value=ToolResult.text("ok"))

    llm_bridge = MagicMock()
    # 每次都返回工具调用，永远不到最终回复
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(
        text_part="", tool_calls=[ToolCall(id="c1", name="dummy", arguments={})]
    ))
    tool_registry.to_function_schemas = MagicMock(return_value=[{}])

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    async for event in runtime.run("loop"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "error" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_runtime_llm_error_fallback():
    """LLM 调用失败时应返回 fallback 消息"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    tool_registry.to_function_schemas = MagicMock(return_value=[])
    llm_bridge.generate = AsyncMock(side_effect=RuntimeError("LLM down"))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    async for event in runtime.run("Hi"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "error" in event_types
    assert "done" in event_types
    # done 事件的 final_text 应该是 fallback 消息
    done_event = [e for e in events if e.type == "done"][0]
    assert "暂时不可用" in done_event.payload["final_text"] or done_event.payload["final_text"]


@pytest.mark.asyncio
async def test_runtime_trace_failure_does_not_crash():
    """Trace 失败不应导致整个循环崩溃"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    tool_registry.to_function_schemas = MagicMock(return_value=[])
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="OK", tool_calls=[]))

    ctx = _make_ctx()
    # trace 创建抛异常
    ctx.trace_recorder.start_trace = MagicMock(side_effect=RuntimeError("DB down"))

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    async for event in runtime.run("Hi"):
        events.append(event)

    # 循环应正常完成
    event_types = [e.type for e in events]
    assert "done" in event_types


@pytest.mark.asyncio
async def test_runtime_session_persist_failure_does_not_crash():
    """Session persist 失败不应导致异常外泄"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")
    session.persist = MagicMock(side_effect=RuntimeError("DB commit failed"))

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    tool_registry.to_function_schemas = MagicMock(return_value=[])
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(text_part="OK", tool_calls=[]))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    # 不应抛出异常
    async for event in runtime.run("Hi"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "done" in event_types


@pytest.mark.asyncio
async def test_runtime_text_delta_and_complete():
    """应发出 text_delta 和 text_complete 事件"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    tool_registry.to_function_schemas = MagicMock(return_value=[])
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(
        text_part="Hello world!", tool_calls=[]
    ))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    async for event in runtime.run("Hi"):
        events.append(event)

    event_types = [e.type for e in events]
    assert "text_delta" in event_types
    assert "text_complete" in event_types

    text_delta_events = [e for e in events if e.type == "text_delta"]
    assert any("Hello world!" in e.payload.get("text", "") for e in text_delta_events)


@pytest.mark.asyncio
async def test_runtime_output_guardrail_persists_fallback():
    """输出 guardrail 阻断时，持久化的应是 fallback 文本而非原始 LLM 输出"""
    agent = _make_agent()
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(
        text_part="原始违规内容", tool_calls=[]
    ))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []

    with patch("app.services.harness.agent_runtime.run_output_guardrails") as mock_gr:
        mock_gr.return_value = MagicMock(
            blocked=True, guardrail_name="filter", reason="blocked", stage="output"
        )
        async for event in runtime.run("Hi"):
            events.append(event)

    # 持久化的 assistant 消息的 text_part 应是 fallback 文本
    session.append_assistant_message.assert_called_once()
    persisted_resp = session.append_assistant_message.call_args[0][0]
    assert persisted_resp.text_part == "抱歉，AI 输出未通过校验。"
    assert persisted_resp.text_part != "原始违规内容"


@pytest.mark.asyncio
async def test_runtime_handoff_persists_trigger_response():
    """Handoff 触发时，应持久化触发 handoff 的 LLM 响应"""
    from app.services.harness.tool_protocol import ToolCall

    agent = _make_agent()
    target_agent = _make_agent(id="agent-2", name="Target Agent", slug="target-agent")
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    llm_bridge = MagicMock()
    llm_bridge.generate = AsyncMock(return_value=LLMResponse(
        text_part="", tool_calls=[
            ToolCall(id="h1", name="handoff_to_target-agent", arguments={})
        ]
    ))

    ctx = _make_ctx()

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []

    # handoff 检测命中 → 下一轮 LLM 返回最终回复后终止
    call_count = 0
    async def gen_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(text_part="", tool_calls=[
                ToolCall(id="h1", name="handoff_to_target-agent", arguments={})
            ])
        else:
            return LLMResponse(text_part="Done", tool_calls=[])

    llm_bridge.generate = AsyncMock(side_effect=gen_side_effect)

    with patch("app.services.harness.agent_runtime.detect_handoff") as mock_detect:
        mock_detect.side_effect = [target_agent, None]
        async for event in runtime.run("transfer me"):
            events.append(event)

    # 第一次 LLM 响应（触发 handoff）应被持久化
    assert session.append_assistant_message.call_count >= 1
    first_call_args = session.append_assistant_message.call_args_list[0][0][0]
    assert first_call_args.tool_calls  # 包含 tool_calls，说明是触发 handoff 的那条


@pytest.mark.asyncio
async def test_runtime_handoff_records_trace_step():
    """P3-⑪: handoff 发生时应记录 step_type=handoff 的 TraceStep（含 from/to metadata）"""
    from app.services.harness.tool_protocol import ToolCall

    agent = _make_agent()
    target_agent = _make_agent(id="agent-2", name="Target Agent", slug="target-agent")
    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id="conv-1")

    tool_registry = MagicMock()
    tool_registry.get_tools_for_agent = AsyncMock(return_value=[])
    tool_registry.to_function_schemas = MagicMock(return_value=[])

    ctx = _make_ctx()
    trace_mock = MagicMock(id="trace-1")
    ctx.trace_recorder.start_trace = MagicMock(return_value=trace_mock)
    step_mock = MagicMock()
    ctx.trace_recorder.start_step = MagicMock(return_value=step_mock)

    llm_bridge = MagicMock()
    call_count = 0

    async def gen_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(text_part="", tool_calls=[
                ToolCall(id="h1", name="handoff_to_target-agent", arguments={})
            ])
        return LLMResponse(text_part="Done", tool_calls=[])

    llm_bridge.generate = AsyncMock(side_effect=gen_side_effect)

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    events = []
    with patch("app.services.harness.agent_runtime.detect_handoff") as mock_detect:
        mock_detect.side_effect = [target_agent, None]
        async for event in runtime.run("transfer me"):
            events.append(event)

    # handoff step 被记录（扫描全部 end_step 调用，找到 handoff 那次）
    ctx.trace_recorder.start_step.assert_any_call("trace-1", "handoff")
    handoff_meta = None
    for call in ctx.trace_recorder.end_step.call_args_list:
        meta = call.kwargs.get("metadata") or {}
        if "from_agent" in meta:
            handoff_meta = meta
            break
    assert handoff_meta is not None, "handoff step 未记录 metadata"
    assert handoff_meta["to_agent"]["name"] == "Target Agent"
