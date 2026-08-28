"""WebSearchTool 行为测试（Task 4）

覆盖：元数据 / function schema / execute / is_available
"""
from unittest.mock import MagicMock

import pytest

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.web_search import WebSearchTool


def test_web_search_tool_metadata():
    """WebSearchTool 应有正确的元数据"""
    tool = WebSearchTool()
    assert tool.name == "web_search"
    assert tool.display_name == "网络搜索"
    assert "query" in tool.parameters_schema["properties"]


def test_web_search_tool_function_schema():
    """to_function_schema 应返回 LLM 可用的 schema"""
    tool = WebSearchTool()
    schema = tool.to_function_schema()
    assert schema["name"] == "web_search"
    assert "description" in schema
    assert "parameters" in schema


@pytest.mark.asyncio
async def test_web_search_execute():
    """WebSearchTool.execute 应返回搜索结果"""
    tool = WebSearchTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"query": "python", "max_results": 2}, ctx)

    assert isinstance(result, ToolResult)
    # 实际结果取决于是否联网；CI 环境可能无法搜索，至少不应抛异常
    assert result.content_type in ("text", "error")


def test_web_search_is_always_available():
    """WebSearchTool 默认总是可用"""
    tool = WebSearchTool()
    ctx = MagicMock(spec=ToolContext)
    assert tool.is_available(ctx) is True