"""Guardrail 执行器单元测试

覆盖：
- 无 guardrails 时直接通过
- input guardrail 阻断（block 策略）
- input guardrail warn 不阻断
- output guardrail 阻断
- guardrail 工具成功时放行
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.harness.guardrail import (
    run_input_guardrails,
    run_output_guardrails,
    GuardrailResult,
)
from app.services.harness.events import Event


@pytest.mark.asyncio
async def test_no_guardrails_passes_through():
    """没有配置 guardrails 时应直接通过"""
    agent = MagicMock()
    agent.input_guardrails = []
    agent.guardrail_on_violation = "block"
    ctx = MagicMock()

    result = await run_input_guardrails(agent, "hello", ctx, tool_registry=MagicMock())
    assert result.blocked is False
    assert result.warned is False


@pytest.mark.asyncio
async def test_guardrail_blocks_violation():
    """guardrail 工具返回失败时应阻断"""
    agent = MagicMock()
    agent.input_guardrails = [{"name": "profanity_filter", "tool_id": "tool-id", "config": {}}]
    agent.guardrail_on_violation = "block"

    tool_registry = MagicMock()
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=MagicMock(
        success=False, error_message="contains profanity"
    ))
    tool_registry._resolve_tool_by_name = AsyncMock(return_value=mock_tool)

    ctx = MagicMock()
    result = await run_input_guardrails(agent, "bad word", ctx, tool_registry)
    assert result.blocked is True
    assert result.guardrail_name == "profanity_filter"
    assert result.stage == "input"


@pytest.mark.asyncio
async def test_guardrail_warn_does_not_block():
    """warn 策略应不阻断"""
    agent = MagicMock()
    agent.input_guardrails = [{"name": "filter", "tool_id": "tool-id", "config": {}}]
    agent.guardrail_on_violation = "warn"

    tool_registry = MagicMock()
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=MagicMock(
        success=False, error_message="warning message"
    ))
    tool_registry._resolve_tool_by_name = AsyncMock(return_value=mock_tool)

    ctx = MagicMock()
    result = await run_input_guardrails(agent, "content", ctx, tool_registry)
    assert result.blocked is False
    assert result.warned is True


@pytest.mark.asyncio
async def test_output_guardrail_blocks():
    """输出 guardrail 阻断测试"""
    agent = MagicMock()
    agent.output_guardrails = [{"name": "secret_leak", "tool_id": "tool-id", "config": {}}]
    agent.guardrail_on_violation = "block"

    tool_registry = MagicMock()
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=MagicMock(
        success=False, error_message="contains secret"
    ))
    tool_registry._resolve_tool_by_name = AsyncMock(return_value=mock_tool)

    ctx = MagicMock()
    result = await run_output_guardrails(agent, "output text", ctx, tool_registry)
    assert result.blocked is True
    assert result.stage == "output"


@pytest.mark.asyncio
async def test_guardrail_passes_when_succeeds():
    """guardrail 工具返回成功时应放行"""
    agent = MagicMock()
    agent.input_guardrails = [{"name": "filter", "tool_id": "tool-id", "config": {}}]
    agent.guardrail_on_violation = "block"

    tool_registry = MagicMock()
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=MagicMock(success=True, error_message=None))
    tool_registry._resolve_tool_by_name = AsyncMock(return_value=mock_tool)

    ctx = MagicMock()
    result = await run_input_guardrails(agent, "good content", ctx, tool_registry)
    assert result.blocked is False
