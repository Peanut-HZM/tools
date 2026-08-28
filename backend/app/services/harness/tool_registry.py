"""ToolRegistry — 工具注册表（应用级单例）

参考 spec §6.4

职责：
1. 管理所有工具实例（builtin + http）
2. 按 agent 的 tool_bindings 选择工具
3. 生成 LLM function schema
4. 分发工具调用到具体实现
5. 管理工具生命周期
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from app.services.harness.tool_protocol import (
    ToolProtocol,
    ToolCall,
    ToolResult,
    ToolContext,
    ToolEvent,
)
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.http_tool import HttpTool
from app.services.harness.exceptions import ToolNotFoundError, ToolExecutionError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表

    管理内置工具与 HTTP 工具的注册、查询、执行和生命周期。
    """

    def __init__(self, db: DBSession):
        self.db = db
        self._builtin: Dict[str, BuiltinTool] = {}
        self._http_cache: Dict[str, HttpTool] = {}  # tool_id -> HttpTool

    # ============================================================
    # 注册
    # ============================================================

    def register_builtin(self, tool: BuiltinTool) -> None:
        """注册内置工具

        Raises:
            ValueError: 同名工具重复注册
        """
        if tool.name in self._builtin:
            raise ValueError(f"内置工具 {tool.name} 重复注册")
        self._builtin[tool.name] = tool
        logger.info(f"[ToolRegistry] 注册内置工具: {tool.name}")

    # ============================================================
    # 查询
    # ============================================================

    async def get_tools_for_agent(
        self, agent_id: str, ctx: ToolContext
    ) -> List[ToolProtocol]:
        """获取 agent 在当前上下文下可用的工具列表

        策略：
        1. 内置工具默认对所有 agent 可用（无需显式绑定）
        2. 显式绑定的工具（agent_tools 表）按 binding 配置
        3. 过滤 is_available(ctx) == True 的
        4. 绑定工具与内置工具重名时，绑定覆盖内置
        """
        tools: List[ToolProtocol] = []

        # 1. 内置工具（默认全部可用，按 is_available 过滤）
        for tool in self._builtin.values():
            if tool.is_available(ctx):
                tools.append(tool)

        # 2. 显式绑定的工具（DB 配置）
        bindings = self._load_bindings(agent_id)
        for binding in bindings:
            if not binding.is_enabled:
                continue
            try:
                tool = await self._resolve_tool_by_binding(binding)
                if tool.is_available(ctx):
                    # 绑定工具与内置工具重名时，绑定覆盖内置
                    tools = [t for t in tools if t.name != tool.name]
                    tools.append(tool)
            except Exception as e:
                logger.warning(f"加载工具绑定失败 binding_id={binding.id}: {e}")

        return tools

    def to_function_schemas(self, tools: List[ToolProtocol]) -> List[dict]:
        """批量生成 LLM function schemas"""
        return [t.to_function_schema() for t in tools]

    # ============================================================
    # 执行
    # ============================================================

    async def execute(self, call: ToolCall, ctx: ToolContext) -> ToolResult:
        """执行工具调用

        流程：
        1. 查找工具实例
        2. 调用 tool.execute(args, ctx)
        3. 捕获异常，返回 ToolResult.error
        """
        try:
            tool = await self._resolve_tool_by_name(call.name)
        except ToolNotFoundError as e:
            return ToolResult.error(str(e))

        try:
            result = await tool.execute(call.arguments, ctx)
            return result
        except Exception as e:
            logger.error(f"工具执行失败 tool={call.name}: {e}", exc_info=True)
            return ToolResult.error(f"工具执行失败: {e}")

    async def execute_stream(self, call: ToolCall, ctx: ToolContext):
        """流式执行工具调用

        产出 ToolEvent 序列。工具未找到时产出 error 事件。
        """
        try:
            tool = await self._resolve_tool_by_name(call.name)
        except ToolNotFoundError as e:
            yield ToolEvent(type="error", payload={"message": str(e)})
            return

        try:
            async for event in tool.execute_stream(call.arguments, ctx):
                yield event
        except Exception as e:
            logger.error(f"工具流式执行失败 tool={call.name}: {e}", exc_info=True)
            yield ToolEvent(type="error", payload={"message": str(e)})

    # ============================================================
    # 生命周期
    # ============================================================

    async def initialize_all(self) -> None:
        """应用启动时调用，初始化所有内置工具"""
        for tool in self._builtin.values():
            try:
                await tool.initialize()
            except Exception as e:
                logger.error(f"内置工具初始化失败 {tool.name}: {e}")

    async def shutdown_all(self) -> None:
        """应用关闭时调用，关闭所有工具并清空 HTTP 缓存"""
        for tool in self._builtin.values():
            try:
                await tool.shutdown()
            except Exception as e:
                logger.warning(f"内置工具关闭失败 {tool.name}: {e}")
        self._http_cache.clear()

    async def refresh_http_tools(self) -> None:
        """DB 中的 http 工具变更时刷新缓存"""
        self._http_cache.clear()

    # ============================================================
    # 内部方法
    # ============================================================

    def _load_bindings(self, agent_id: str):
        """从 DB 加载 agent 的工具绑定"""
        from app.models.harness_models import ToolBinding

        return (
            self.db.query(ToolBinding)
            .filter(ToolBinding.agent_id == agent_id)
            .order_by(ToolBinding.priority)
            .all()
        )

    async def _resolve_tool_by_binding(self, binding):
        """按 binding 解析工具实例"""
        from app.models.harness_models import Tool

        db_tool = self.db.query(Tool).filter(Tool.id == binding.tool_id).first()
        if not db_tool:
            raise ToolNotFoundError(f"tool_id={binding.tool_id}")

        if db_tool.type == "builtin":
            raise NotImplementedError("builtin via DB binding not implemented in Phase 1")
        elif db_tool.type == "http":
            if db_tool.id not in self._http_cache:
                self._http_cache[db_tool.id] = HttpTool(db_tool)
            return self._http_cache[db_tool.id]
        else:
            raise ToolNotFoundError(f"unknown tool type: {db_tool.type}")

    async def _resolve_tool_by_name(self, name: str):
        """按工具名解析实例

        查找顺序：内置工具 → DB（HTTP 工具）
        """
        # 1. 查内置
        if name in self._builtin:
            return self._builtin[name]

        # 2. 查 DB（HTTP 工具）
        from app.models.harness_models import Tool

        db_tool = (
            self.db.query(Tool)
            .filter(Tool.name == name, Tool.is_active == True)
            .first()
        )
        if db_tool and db_tool.type == "http":
            if db_tool.id not in self._http_cache:
                self._http_cache[db_tool.id] = HttpTool(db_tool)
            return self._http_cache[db_tool.id]

        raise ToolNotFoundError(name)
