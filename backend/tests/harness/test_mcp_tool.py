"""McpTool 单元测试"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.mcp_tool import McpTool


@pytest.mark.asyncio
async def test_mcp_tool_properties():
    """测试 McpTool 基本属性"""
    mock_client = AsyncMock()
    tool = McpTool(
        server_id=uuid4(),
        server_name="test_server",
        tool_name="echo",
        description="Echo tool",
        input_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
        client=mock_client,
        timeout=30,
    )

    assert tool.name == "mcp:test_server:echo"
    assert tool.display_name == "echo"
    assert tool.description == "Echo tool"
    assert tool.parameters_schema == {"type": "object", "properties": {"msg": {"type": "string"}}}


@pytest.mark.asyncio
async def test_mcp_tool_execute_success():
    """测试工具执行成功"""
    mock_client = AsyncMock()
    mock_client.tools_call = AsyncMock(
        return_value={"content": [{"type": "text", "text": "hello"}], "isError": False}
    )

    tool = McpTool(
        server_id=uuid4(),
        server_name="test_server",
        tool_name="echo",
        description="Echo tool",
        input_schema={},
        client=mock_client,
        timeout=30,
    )

    ctx = MagicMock(spec=ToolContext)
    result = await tool.execute({"msg": "hi"}, ctx)

    assert result.success is True
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_mcp_tool_execute_server_error():
    """测试 server 返回 isError=true"""
    mock_client = AsyncMock()
    mock_client.tools_call = AsyncMock(
        return_value={"content": [{"type": "text", "text": "error msg"}], "isError": True}
    )

    tool = McpTool(
        server_id=uuid4(),
        server_name="test_server",
        tool_name="echo",
        description="Echo tool",
        input_schema={},
        client=mock_client,
        timeout=30,
    )

    ctx = MagicMock(spec=ToolContext)
    result = await tool.execute({}, ctx)

    assert result.success is False


@pytest.mark.asyncio
async def test_mcp_tool_execute_timeout():
    """测试工具执行超时"""
    mock_client = AsyncMock()

    async def slow_call(*args, **kwargs):
        await asyncio.sleep(2)
        return {}

    mock_client.tools_call = slow_call

    tool = McpTool(
        server_id=uuid4(),
        server_name="test_server",
        tool_name="echo",
        description="Echo tool",
        input_schema={},
        client=mock_client,
        timeout=1,
    )

    ctx = MagicMock(spec=ToolContext)
    result = await tool.execute({}, ctx)

    assert result.success is False
    assert "timeout" in result.error_message.lower()
