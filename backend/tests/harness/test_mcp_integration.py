"""MCP 集成测试

端到端测试：创建 server → 测试连接 → 同步 → Agent 调用工具。

注意：此测试需要一个真实的 MCP server 运行。
如无可用的 MCP server，测试会跳过。
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from app.models.mcp_server import McpServer
from app.services.harness.mcp_client import McpClient, McpConnectionError
from app.services.harness.mcp_server_manager import McpServerManager
from app.services.harness.tools.mcp_tool import McpTool
from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tool_protocol import ToolContext


@pytest.mark.skip(reason="Requires a real MCP server; run manually")
@pytest.mark.asyncio
async def test_mcp_end_to_end():
    """端到端测试（需要真实 MCP server）

    步骤：
    1. 创建 McpServer 记录
    2. McpServerManager.sync_server()
    3. 验证工具注册到 ToolRegistry
    4. 模拟 Agent 调用工具
    """
    # ... 实际实现需要启动一个 echo MCP server
    pass


@pytest.mark.asyncio
async def test_mcp_workflow_mock():
    """端到端流程测试（mock）

    模拟完整流程：创建 server → 同步 → 调用工具。
    """
    # 1. 创建 McpServer
    mock_db_server = MagicMock(spec=McpServer)
    mock_db_server.id = uuid4()
    mock_db_server.name = "mock_server"
    mock_db_server.server_url = "http://localhost:3000"
    mock_db_server.headers_json = None
    mock_db_server.timeout_seconds = 30

    # 2. 创建 ToolRegistry
    mock_registry = MagicMock(spec=ToolRegistry)
    registered_tools = {}

    def capture_register(tool):
        registered_tools[tool.name] = tool

    mock_registry.register_dynamic = capture_register

    # 3. 创建 McpServerManager
    manager = McpServerManager(tool_registry=mock_registry)

    # 4. Mock McpClient
    mock_client = AsyncMock(spec=McpClient)
    mock_client.connect = AsyncMock()
    mock_client.tools_list = AsyncMock(
        return_value=[
            {
                "name": "echo",
                "description": "Echo tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
            }
        ]
    )
    mock_client.tools_call = AsyncMock(
        return_value={
            "content": [{"type": "text", "text": "Echo: hello"}],
            "isError": False,
        }
    )

    # 5. Sync server
    with patch.object(manager, "_get_or_create_client", return_value=mock_client):
        result = await manager.sync_server(mock_db_server)

    assert result["success"] is True
    assert result["tools_count"] == 1
    assert "mcp:mock_server:echo" in registered_tools

    # 6. 调用工具
    tool = registered_tools["mcp:mock_server:echo"]
    ctx = MagicMock(spec=ToolContext)
    tool_result = await tool.execute({"message": "hello"}, ctx)

    assert tool_result.success is True
    assert "Echo: hello" in tool_result.content