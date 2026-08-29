"""McpClient — MCP SSE 客户端

Phase 3-Plan-1A: MCP 工具支持核心骨架

实现 MCP 协议的 SSE transport，提供：
- connect(): 建立 SSE 长连接 + MCP 握手
- tools_list(): 调用 MCP tools/list
- tools_call(): 调用 MCP tools/call
- disconnect(): 关闭连接

参考: https://modelcontextprotocol.io/specification
"""
import asyncio
import logging
from typing import Any

try:
    from mcp.client.sse import sse_client
    from mcp import ClientSession
except ImportError:
    raise ImportError(
        "mcp package not installed. Run: pip install mcp>=1.0.0"
    )

logger = logging.getLogger(__name__)


class McpConnectionError(Exception):
    """MCP 连接失败"""
    pass


class McpClient:
    """MCP SSE 客户端

    用法:
        client = McpClient("http://localhost:3000", timeout=30)
        await client.connect()
        tools = await client.tools_list()
        result = await client.tools_call("tool_name", {"arg": "value"})
        await client.disconnect()
    """

    def __init__(self, server_url: str, headers: dict | None = None, timeout: int = 30):
        self.server_url = server_url
        self.headers = headers or {}
        self.timeout = timeout
        self._session: ClientSession | None = None
        self._sse_context = None  # 保持 SSE context manager 引用

    async def _connect_sse(self):
        """内部方法：建立 SSE 连接，返回 (read_stream, write_stream)

        实际调用 sse_client async context manager 的 __aenter__。
        """
        self._sse_context = sse_client(self.server_url, headers=self.headers)
        read_stream, write_stream = await self._sse_context.__aenter__()
        return read_stream, write_stream

    async def connect(self) -> None:
        """建立 SSE 连接并完成 MCP 握手"""
        try:
            read_stream, write_stream = await self._connect_sse()

            # 创建 ClientSession 并初始化
            self._session = ClientSession(read_stream, write_stream)
            await asyncio.wait_for(
                self._session.initialize(),
                timeout=self.timeout,
            )

            logger.info(f"MCP client connected to {self.server_url}")
        except asyncio.TimeoutError:
            await self.disconnect()
            raise McpConnectionError(f"Connection timeout after {self.timeout}s")
        except McpConnectionError:
            raise
        except Exception as e:
            await self.disconnect()
            logger.exception(f"MCP connection failed: {e}")
            raise McpConnectionError(f"Connection failed: {e}") from e

    async def tools_list(self) -> list[dict]:
        """调用 MCP tools/list 获取工具列表

        Returns:
            [{"name": "...", "description": "...", "inputSchema": {...}}, ...]
        """
        if not self._session:
            raise McpConnectionError("Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.list_tools(),
                timeout=self.timeout,
            )
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": getattr(tool, "inputSchema", {}),
                }
                for tool in result.tools
            ]
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.exception(f"tools_list failed: {e}")
            raise

    async def tools_call(self, name: str, arguments: dict) -> dict:
        """调用 MCP tools/call 执行工具

        Args:
            name: 工具名
            arguments: 工具参数

        Returns:
            {"content": [...], "isError": bool}
        """
        if not self._session:
            raise McpConnectionError("Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments),
                timeout=self.timeout,
            )
            return {
                "content": [
                    {
                        "type": getattr(c, "type", "text"),
                        "text": getattr(c, "text", str(c)),
                    }
                    for c in result.content
                ],
                "isError": result.isError,
            }
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.exception(f"tools_call failed: {e}")
            raise

    async def disconnect(self) -> None:
        """关闭连接"""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing MCP session: {e}")
            self._session = None

        if self._sse_context:
            try:
                await self._sse_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing SSE context: {e}")
            self._sse_context = None

        logger.info(f"MCP client disconnected from {self.server_url}")
