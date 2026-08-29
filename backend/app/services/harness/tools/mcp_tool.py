"""McpTool — MCP 工具（实现 ToolProtocol）

Phase 3-Plan-1A: MCP 工具支持核心骨架

直接实现 ToolProtocol（不继承 BuiltinTool），因为它是配置驱动而非代码驱动。
"""
import asyncio
import logging
from typing import AsyncIterator
from uuid import UUID

from app.services.harness.mcp_client import McpClient
from app.services.harness.tool_protocol import (
    ToolContext,
    ToolEvent,
    ToolResult,
)

logger = logging.getLogger(__name__)


class McpTool:
    """MCP 工具

    实现 ToolProtocol，代理到远程 MCP server。
    命名空间: mcp:{server_name}:{tool_name}
    """

    def __init__(
        self,
        server_id: UUID,
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: dict,
        client: McpClient,
        timeout: int = 30,
    ):
        self.server_id = server_id
        self.server_name = server_name
        self.tool_name = tool_name
        self._name = f"mcp:{server_name}:{tool_name}"
        self._description = description
        self._input_schema = input_schema
        self._client = client
        self._timeout = timeout

    # ---- ToolProtocol 属性 ----

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict:
        return self._input_schema

    @property
    def returns_schema(self):
        return None

    # ---- 生命周期 ----

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    # ---- 可用性 ----

    def is_available(self, ctx: ToolContext) -> bool:
        return True

    # ---- LLM 集成 ----

    def to_function_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    # ---- 核心执行 ----

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        """调用 MCP 工具"""
        try:
            result = await asyncio.wait_for(
                self._client.tools_call(self.tool_name, args),
                timeout=self._timeout,
            )
            if result.get("isError"):
                error_text = str(result.get("content", "unknown error"))
                return ToolResult.error(f"MCP tool returned error: {error_text}")
            # 提取 content 中的文本
            content = result.get("content", [])
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return ToolResult.text("\n".join(text_parts) if text_parts else str(content))
        except asyncio.TimeoutError:
            logger.warning(f"MCP tool {self._name} timeout after {self._timeout}s")
            return ToolResult.error(f"MCP tool timeout after {self._timeout}s")
        except Exception as e:
            logger.exception(f"MCP tool {self._name} failed: {e}")
            return ToolResult.error(f"MCP tool execution failed: {e}")

    async def execute_stream(self, args: dict, ctx: ToolContext) -> AsyncIterator[ToolEvent]:
        """默认实现：包装 execute 为单事件"""
        result = await self.execute(args, ctx)
        yield ToolEvent(type="result", payload=result)
