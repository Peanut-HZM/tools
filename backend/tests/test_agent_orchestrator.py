"""AgentOrchestrator 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.image_gen.agent_orchestrator import AgentOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_stops_on_no_tool_call():
    """LLM 直接返回 content，无 tool_call → 立即返回"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=MagicMock(
        content="你想画什么样的猫？",
        tool_calls=[],
    ))

    orch = AgentOrchestrator(gateway=gateway)
    answer, tool_calls = await orch.run(
        messages=[{"role": "user", "content": "画一只猫"}],
        tools=[],
    )
    assert answer == "你想画什么样的猫？"
    assert tool_calls == []


@pytest.mark.asyncio
async def test_orchestrator_handles_tool_call():
    """LLM 返回 tool_call → 执行，喂结果回去，再调一次 brain"""
    gateway = MagicMock()

    # 第一次：返回 tool_call
    first = MagicMock()
    first.content = None
    first.tool_calls = [
        {"id": "call_1", "name": "generate_image", "arguments": {"operation": "text2img", "prompt": "a cat"}}
    ]

    # 第二次：返回最终回答
    second = MagicMock()
    second.content = "图已生成"
    second.tool_calls = []

    gateway.generate = AsyncMock(side_effect=[first, second])

    orch = AgentOrchestrator(gateway=gateway)
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"image_urls": ["https://oss/1.png"]})

    answer, tool_results = await orch.run(
        messages=[{"role": "user", "content": "画一只猫"}],
        tools=[],
        executor=executor,
    )
    assert answer == "图已生成"
    assert len(tool_results) == 1
    assert tool_results[0]["image_urls"] == ["https://oss/1.png"]


@pytest.mark.asyncio
async def test_orchestrator_max_iterations():
    """超过 max_iterations 应停止并返回当前 best-effort"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=MagicMock(
        content=None,
        tool_calls=[{"id": "call_x", "name": "generate_image", "arguments": {}}],
    ))

    orch = AgentOrchestrator(gateway=gateway, max_iterations=3)
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"image_urls": []})

    answer, tool_results = await orch.run(
        messages=[{"role": "user", "content": "x"}],
        tools=[],
        executor=executor,
    )
    # 应该已停止
    assert executor.execute.call_count <= 3


@pytest.mark.asyncio
async def test_orchestrator_appends_assistant_message_once():
    """修正 brief bug：多个 tool_call 时，assistant 消息只追加一次"""
    gateway = MagicMock()

    first = MagicMock()
    first.content = "我来调用两个工具"
    first.tool_calls = [
        {"id": "call_a", "name": "tool_a", "arguments": {}},
        {"id": "call_b", "name": "tool_b", "arguments": {}},
    ]

    second = MagicMock()
    second.content = "完成"
    second.tool_calls = []

    gateway.generate = AsyncMock(side_effect=[first, second])

    orch = AgentOrchestrator(gateway=gateway)
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"ok": True})

    answer, tool_results = await orch.run(
        messages=[{"role": "user", "content": "do it"}],
        tools=[],
        executor=executor,
    )

    assert answer == "完成"
    assert len(tool_results) == 2
    assert executor.execute.call_count == 2

    # 验证传给 gateway 的 messages：
    # 第 1 次调用：原始 user 消息（1 条）
    # 第 2 次调用：原始 + 1 条 assistant + 2 条 tool = 4 条
    # 注意：current_messages 是同一个列表被原地追加，所以要通过 side_effect 捕获每次调用时的长度
    gateway2 = MagicMock()

    first2 = MagicMock()
    first2.content = "我来调用两个工具"
    first2.tool_calls = [
        {"id": "call_a", "name": "tool_a", "arguments": {}},
        {"id": "call_b", "name": "tool_b", "arguments": {}},
    ]
    second2 = MagicMock()
    second2.content = "完成"
    second2.tool_calls = []

    captured_lengths = []

    async def capture_generate(**kwargs):
        captured_lengths.append(len(kwargs["messages"]))
        # 返回第一次或第二次的 mock
        if len(captured_lengths) == 1:
            return first2
        return second2

    gateway2.generate = AsyncMock(side_effect=capture_generate)

    orch2 = AgentOrchestrator(gateway=gateway2)
    executor2 = AsyncMock()
    executor2.execute = AsyncMock(return_value={"ok": True})

    answer, tool_results = await orch2.run(
        messages=[{"role": "user", "content": "do it"}],
        tools=[],
        executor=executor2,
    )

    assert answer == "完成"
    assert len(tool_results) == 2
    assert executor2.execute.call_count == 2
    # 第一次 1 条 user；第二次 1 user + 1 assistant + 2 tool = 4
    assert captured_lengths == [1, 4]


@pytest.mark.asyncio
async def test_orchestrator_tool_call_without_executor_raises():
    """LLM 返回 tool_call 但没 executor → ValueError"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=MagicMock(
        content=None,
        tool_calls=[{"id": "call_1", "name": "foo", "arguments": {}}],
    ))

    orch = AgentOrchestrator(gateway=gateway)
    with pytest.raises(ValueError):
        await orch.run(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )


@pytest.mark.asyncio
async def test_orchestrator_supports_dict_response():
    """兼容 dict 形态的 response（字段访问兼容）"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value={
        "content": "hello from dict",
        "tool_calls": [],
    })

    orch = AgentOrchestrator(gateway=gateway)
    answer, tool_calls = await orch.run(
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
    )
    assert answer == "hello from dict"
    assert tool_calls == []
