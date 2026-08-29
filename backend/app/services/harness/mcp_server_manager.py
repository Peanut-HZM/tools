"""McpServerManager — MCP Server 管理器

Phase 3-Plan-1A: MCP 工具支持核心骨架

管理 MCP server 的生命周期：
- sync_server(): 连接 server + 发现工具 + 注册到 ToolRegistry
- unsync_server(): 从 ToolRegistry 移除工具
- 缓存 McpClient 实例
"""
import json
import logging
from typing import Dict, List
from uuid import UUID

from app.models.mcp_server import McpServer
from app.services.harness.mcp_client import McpClient, McpConnectionError
from app.services.harness.tools.mcp_tool import McpTool
from app.services.harness.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class McpServerManager:
    """MCP Server 管理器"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._clients: Dict[UUID, McpClient] = {}
        self._server_tools: Dict[UUID, List[str]] = {}  # server_id -> [tool_names]

    async def sync_server(self, server: McpServer) -> dict:
        """同步 server 工具到 ToolRegistry

        Args:
            server: McpServer ORM 对象

        Returns:
            {"success": bool, "tools_count": int, "error": str | None}
        """
        try:
            client = self._get_or_create_client(server)
            await client.connect()

            # 拉取工具列表
            tools_data = await client.tools_list()

            # 先移除旧工具（如有）
            if server.id in self._server_tools:
                await self.unsync_server(server.id)

            # 为每个工具创建 McpTool 并注册
            tool_names = []
            for tool_data in tools_data:
                mcp_tool = McpTool(
                    server_id=server.id,
                    server_name=server.name,
                    tool_name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    client=client,
                    timeout=server.timeout_seconds,
                )
                self.tool_registry.register_dynamic(mcp_tool)
                tool_names.append(mcp_tool.name)

            self._server_tools[server.id] = tool_names

            logger.info(
                f"Synced {len(tool_names)} tools from MCP server {server.name}"
            )
            return {
                "success": True,
                "tools_count": len(tool_names),
                "error": None,
            }
        except McpConnectionError as e:
            logger.error(f"MCP server {server.name} connection failed: {e}")
            return {"success": False, "tools_count": 0, "error": str(e)}
        except Exception as e:
            logger.exception(f"Failed to sync MCP server {server.name}: {e}")
            return {"success": False, "tools_count": 0, "error": str(e)}

    async def unsync_server(self, server_id: UUID) -> None:
        """从 ToolRegistry 移除 server 的所有工具"""
        tool_names = self._server_tools.get(server_id, [])
        for name in tool_names:
            self.tool_registry.unregister_dynamic(name)
            logger.info(f"Unregistered MCP tool: {name}")

        # 断开连接
        if server_id in self._clients:
            await self._clients[server_id].disconnect()
            del self._clients[server_id]

        self._server_tools.pop(server_id, None)
        logger.info(f"Unsynced MCP server {server_id}")

    def _get_or_create_client(self, server: McpServer) -> McpClient:
        """获取或创建 McpClient"""
        if server.id in self._clients:
            return self._clients[server.id]

        headers = None
        if server.headers_json:
            headers = json.loads(server.headers_json)

        # allow_private_hosts=True：MCP server URL 来自管理员配置（admin UI），
        # 管理员可能配置内网 MCP 服务（如 http://10.x.x.x:3000），需要允许私有 IP。
        # SSRF 防护仍保留：scheme 校验、userinfo 校验等在 validate_url() 中生效。
        client = McpClient(
            server_url=server.server_url,
            headers=headers,
            timeout=server.timeout_seconds,
            allow_private_hosts=True,
        )
        self._clients[server.id] = client
        return client

    def get_client(self, server_id: UUID) -> McpClient | None:
        """获取缓存的 client"""
        return self._clients.get(server_id)
