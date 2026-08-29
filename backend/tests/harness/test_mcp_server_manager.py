"""McpServerManager 单元测试"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.mcp_server import McpServer
from app.services.harness.mcp_server_manager import McpServerManager
from app.services.harness.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_sync_server_success():
    """测试同步 server 工具到 ToolRegistry"""
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_registry.register_dynamic = MagicMock()

    manager = McpServerManager(tool_registry=mock_registry)

    # mock DB server
    mock_server = MagicMock(spec=McpServer)
    mock_server.id = uuid4()
    mock_server.name = "test_server"
    mock_server.server_url = "http://localhost:3000"
    mock_server.headers_json = None
    mock_server.timeout_seconds = 30

    # mock client
    mock_client = AsyncMock()
    mock_client.tools_list = AsyncMock(
        return_value=[
            {"name": "tool1", "description": "Tool 1", "inputSchema": {}},
            {"name": "tool2", "description": "Tool 2", "inputSchema": {}},
        ]
    )

    with patch.object(manager, "_get_or_create_client", return_value=mock_client):
        result = await manager.sync_server(mock_server)

    assert result["success"] is True
    assert result["tools_count"] == 2
    assert mock_registry.register_dynamic.call_count == 2


@pytest.mark.asyncio
async def test_sync_server_connection_failure():
    """测试同步时连接失败"""
    mock_registry = MagicMock(spec=ToolRegistry)
    manager = McpServerManager(tool_registry=mock_registry)

    mock_server = MagicMock(spec=McpServer)
    mock_server.id = uuid4()
    mock_server.name = "test_server"
    mock_server.server_url = "http://nonexistent:3000"
    mock_server.headers_json = None
    mock_server.timeout_seconds = 30

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(side_effect=Exception("Connection refused"))

    with patch.object(manager, "_get_or_create_client", return_value=mock_client):
        result = await manager.sync_server(mock_server)

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_unsync_server():
    """测试从 ToolRegistry 移除 server 的工具"""
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_registry.unregister_dynamic = MagicMock()

    manager = McpServerManager(tool_registry=mock_registry)
    manager._server_tools = {
        uuid4(): ["mcp:test:tool1", "mcp:test:tool2"],
    }

    server_id = list(manager._server_tools.keys())[0]
    await manager.unsync_server(server_id)

    assert mock_registry.unregister_dynamic.call_count == 2
    assert server_id not in manager._server_tools
