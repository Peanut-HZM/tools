"""DbQueryTool 行为测试（Task 5）

覆盖：元数据 / 拒绝写操作 / 接受 SELECT 查询
"""
from unittest.mock import MagicMock

import pytest

from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.db_query import DbQueryTool


def test_db_query_metadata():
    tool = DbQueryTool()
    assert tool.name == "db_query"
    assert "sql" in tool.parameters_schema["properties"]


@pytest.mark.asyncio
async def test_db_query_rejects_write():
    """DbQueryTool 应拒绝写操作"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"sql": "DELETE FROM users"}, ctx)
    assert result.success is False
    assert "只读" in result.error_message or "read-only" in result.error_message.lower()


@pytest.mark.asyncio
async def test_db_query_rejects_drop():
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)

    result = await tool.execute({"sql": "DROP TABLE users"}, ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_db_query_executes_select(test_db):
    """DbQueryTool 应执行 SELECT 查询"""
    tool = DbQueryTool()
    ctx = MagicMock(spec=ToolContext)
    ctx.db = test_db

    result = await tool.execute({"sql": "SELECT 1 AS n", "limit": 10}, ctx)
    assert result.success is True
    assert "1" in str(result.content) or result.content == [{"n": 1}]
