"""BuiltinTool 基类

参考 spec §6.3 实现 ①
"""
from typing import AsyncIterator

from app.services.harness.tool_protocol import (
    ToolContext,
    ToolEvent,
    ToolResult,
)


class BuiltinTool:
    """内置工具基类

    提供 ToolProtocol 的默认实现。子类只需实现 execute() 和定义类属性。

    用法：
        class MyTool(BuiltinTool):
            name = "my_tool"
            display_name = "我的工具"
            description = "..."
            parameters_schema = {...}

            async def execute(self, args, ctx):
                return ToolResult.text("result")
    """

    # 子类必须定义
    name: str = ""
    display_name: str = ""
    description: str = ""
    parameters_schema: dict = {}
    returns_schema: dict = None

    def __init__(self, config: dict = None):
        self._config = config or {}

    # ---- 生命周期（默认 no-op）----

    async def initialize(self) -> None:
        """内置工具通常不需要初始化"""
        pass

    async def shutdown(self) -> None:
        """内置工具通常不需要关闭"""
        pass

    # ---- 可用性（默认总是可用）----

    def is_available(self, ctx: ToolContext) -> bool:
        return True

    # ---- LLM 集成 ----

    def to_function_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    # ---- 流式执行（默认包装 execute 为单事件）----

    async def execute_stream(self, args: dict, ctx: ToolContext) -> AsyncIterator[ToolEvent]:
        """默认实现：调用 execute() 后包装为单个 result 事件

        需要进度反馈的工具（如图像生成）应重写此方法。
        """
        result = await self.execute(args, ctx)
        yield ToolEvent(type="result", payload=result)

    # ---- 核心执行（子类必须实现）----

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")