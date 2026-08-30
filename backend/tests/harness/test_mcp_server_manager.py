"""McpServerManager 单元测试"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.mcp_server import McpServer
from app.services.harness.mcp_server_manager import (
    McpServerManager,
    _is_allow_private_hosts_enabled,
    get_mcp_server_manager,
)
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
    from app.services.harness.tool_registry import ToolRegistry

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


# ============================================================
# SSRF 防护测试：MCP_ALLOW_PRIVATE_HOSTS 环境变量
# ============================================================


class TestMcpServerManagerSSRF:
    """测试 _is_allow_private_hosts_enabled 环境变量读取与传递逻辑"""

    def setup_method(self):
        """每个测试用例前清理环境变量"""
        import os

        self._saved = os.environ.pop("MCP_ALLOW_PRIVATE_HOSTS", None)

    def teardown_method(self):
        """恢复环境变量"""
        import os

        if self._saved is not None:
            os.environ["MCP_ALLOW_PRIVATE_HOSTS"] = self._saved
        else:
            os.environ.pop("MCP_ALLOW_PRIVATE_HOSTS", None)

    def test_default_disabled(self):
        """默认未设置环境变量时，allow_private_hosts 为 False"""
        import os

        os.environ.pop("MCP_ALLOW_PRIVATE_HOSTS", None)
        assert _is_allow_private_hosts_enabled() is False

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on"])
    def test_env_true_enables(self, value):
        import os

        os.environ["MCP_ALLOW_PRIVATE_HOSTS"] = value
        assert _is_allow_private_hosts_enabled() is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "random"])
    def test_env_other_disables(self, value):
        import os

        os.environ["MCP_ALLOW_PRIVATE_HOSTS"] = value
        assert _is_allow_private_hosts_enabled() is False

    def test_get_or_create_client_default_strict(self):
        """默认情况下 allow_private_hosts=False（严格 SSRF 检查）"""
        from app.services.harness.mcp_server_manager import _is_allow_private_hosts_enabled
        import os

        os.environ.pop("MCP_ALLOW_PRIVATE_HOSTS", None)

        mock_registry = MagicMock()
        manager = McpServerManager(tool_registry=mock_registry)
        mock_server = MagicMock(spec=McpServer)
        mock_server.id = uuid4()
        mock_server.name = "public_server"
        mock_server.server_url = "http://93.184.216.34:3000"
        mock_server.headers_json = None
        mock_server.timeout_seconds = 30

        client = manager._get_or_create_client(mock_server)
        assert client.allow_private_hosts is False

    def test_get_or_create_client_env_enabled(self):
        """环境变量启用后 allow_private_hosts=True"""
        import os

        os.environ["MCP_ALLOW_PRIVATE_HOSTS"] = "true"

        mock_registry = MagicMock()
        manager = McpServerManager(tool_registry=mock_registry)
        mock_server = MagicMock(spec=McpServer)
        mock_server.id = uuid4()
        mock_server.name = "private_server"
        mock_server.server_url = "http://10.0.0.1:3000"
        mock_server.headers_json = None
        mock_server.timeout_seconds = 30

        client = manager._get_or_create_client(mock_server)
        assert client.allow_private_hosts is True

    def test_env_enabled_still_rejects_metadata_via_validate(self):
        """即使环境变量启用，validate_url 仍拒绝云元数据"""
        from app.services.harness.mcp_client import McpConnectionError
        import os

        os.environ["MCP_ALLOW_PRIVATE_HOSTS"] = "true"

        # 直接调用 validate_url 验证
        from app.services.harness.mcp_client import validate_url

        with pytest.raises(McpConnectionError, match="blocked|metadata|link-local"):
            validate_url("http://169.254.169.254", allow_private_hosts=True)


# ============================================================
# get_mcp_server_manager 单例 + ToolRegistry 集成
# ============================================================


class TestGetMcpServerManager:
    """测试全局单例初始化不再使用 tool_registry=None"""

    def setup_method(self):
        """每个测试前重置单例"""
        from app.services.harness.mcp_server_manager import _manager

        import app.services.harness.mcp_server_manager as mgr_module

        mgr_module._manager = None

    def teardown_method(self):
        """清理单例"""
        import app.services.harness.mcp_server_manager as mgr_module

        mgr_module._manager = None

    def test_uses_get_tool_registry_not_none(self):
        """get_mcp_server_manager 必须使用 get_tool_registry() 而非 None

        修复前：McpServerManager(tool_registry=None) — AttributeError
        修复后：McpServerManager(tool_registry=get_tool_registry())
        """
        mock_registry = MagicMock()
        with patch(
            "app.services.harness.mcp_server_manager.get_tool_registry",
            return_value=mock_registry,
        ) as mock_get:
            manager = get_mcp_server_manager()
            mock_get.assert_called_once()
            assert manager.tool_registry is mock_registry
            assert manager.tool_registry is not None

    def test_returns_same_singleton(self):
        """get_mcp_server_manager 返回同一单例"""
        mock_registry = MagicMock()
        with patch(
            "app.services.harness.mcp_server_manager.get_tool_registry",
            return_value=mock_registry,
        ):
            manager1 = get_mcp_server_manager()
            manager2 = get_mcp_server_manager()
            assert manager1 is manager2


@pytest.mark.asyncio
async def test_get_or_create_client_per_transport(test_db):
    """P2-①c: manager 按 server.transport 构造对应 client"""
    import json as _json

    from app.models.mcp_server import McpServer
    from app.services.harness.mcp_client import McpClient
    from app.services.harness.mcp_server_manager import McpServerManager

    server = McpServer(
        name="stdio-srv",
        server_url="npx demo",
        transport="stdio",
        command_json=_json.dumps({"command": "npx", "args": ["demo"]}),
    )
    test_db.add(server)
    test_db.commit()
    test_db.refresh(server)

    manager = McpServerManager(tool_registry=object())
    client = manager._get_or_create_client(server)
    assert isinstance(client, McpClient)
    assert client.transport == "stdio"
    assert client._server_params.command == "npx"
    # 缓存命中：第二次拿同一实例
    assert manager._get_or_create_client(server) is client
