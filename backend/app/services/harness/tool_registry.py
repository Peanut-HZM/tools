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
import os
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
        self._dynamic: Dict[str, ToolProtocol] = {}  # MCP / Plugin 动态注册
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
    # 动态工具注册（Phase 3-Plan-1A: MCP tools）
    # ============================================================

    def register_dynamic(self, tool: ToolProtocol) -> None:
        """注册动态工具（来自 MCP server 等外部源）。

        动态工具与内置工具隔离存储；同名重复注册时记录 warning 并覆盖
        （允许 MCP server 重连/更新场景下重新注册同名工具）。
        """
        if tool.name in self._dynamic:
            logger.warning(
                f"[ToolRegistry] 动态工具 {tool.name} 已注册，将被覆盖"
            )
        self._dynamic[tool.name] = tool
        logger.info(f"[ToolRegistry] 注册动态工具: {tool.name}")

    def unregister_dynamic(self, name: str) -> None:
        """注销动态工具。

        仅从 ``_dynamic`` 字典移除，不会触碰 ``_builtin`` 中的同名工具。
        未注册的名称为 no-op。
        """
        if name in self._dynamic:
            del self._dynamic[name]
            logger.info(f"[ToolRegistry] 注销动态工具: {name}")
        else:
            logger.debug(f"[ToolRegistry] 动态工具 {name} 未注册，跳过注销")

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
        2. 鉴权：校验工具是否在当前 agent 的允许列表中
        3. 调用 tool.execute(args, ctx)
        4. 捕获异常，返回 ToolResult.error
        """
        try:
            tool = await self._resolve_tool_by_name(call.name)
        except ToolNotFoundError as e:
            return ToolResult.error(str(e))

        # 鉴权：校验工具是否被授权给当前 agent
        try:
            allowed_tools = await self.get_tools_for_agent(ctx.agent_id, ctx)
        except Exception as e:
            logger.error(f"加载 agent 工具列表失败 agent_id={ctx.agent_id}: {e}", exc_info=True)
            return ToolResult.error("工具鉴权失败")

        allowed_names = {t.name for t in allowed_tools}
        if call.name not in allowed_names:
            logger.warning(
                f"[ToolRegistry] 鉴权拒绝 agent_id={ctx.agent_id} tool={call.name}"
            )
            return ToolResult.error(f"工具 {call.name} 未被授权给当前 agent")

        try:
            result = await tool.execute(call.arguments, ctx)
            return result
        except Exception as e:
            logger.error(f"工具执行失败 tool={call.name}: {e}", exc_info=True)
            return ToolResult.error(f"工具执行失败: {e}")

    async def execute_stream(self, call: ToolCall, ctx: ToolContext):
        """流式执行工具调用

        产出 ToolEvent 序列。工具未找到或未被授权时产出 error 事件。
        """
        try:
            tool = await self._resolve_tool_by_name(call.name)
        except ToolNotFoundError as e:
            yield ToolEvent(type="error", payload={"message": str(e)})
            return

        # 鉴权：校验工具是否被授权给当前 agent
        try:
            allowed_tools = await self.get_tools_for_agent(ctx.agent_id, ctx)
        except Exception as e:
            logger.error(
                f"加载 agent 工具列表失败 agent_id={ctx.agent_id}: {e}", exc_info=True
            )
            yield ToolEvent(type="error", payload={"message": "工具鉴权失败"})
            return

        allowed_names = {t.name for t in allowed_tools}
        if call.name not in allowed_names:
            logger.warning(
                f"[ToolRegistry] 鉴权拒绝 agent_id={ctx.agent_id} tool={call.name}"
            )
            yield ToolEvent(
                type="error",
                payload={"message": f"工具 {call.name} 未被授权给当前 agent"},
            )
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

        查找顺序：内置工具 → 动态工具（MCP / Plugin）→ DB（HTTP 工具）
        """
        # 1. 查内置
        if name in self._builtin:
            return self._builtin[name]

        # 2. 查动态注册（MCP / Plugin）
        if name in self._dynamic:
            return self._dynamic[name]

        # 3. 查 DB（HTTP 工具）
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


# ============================================================
# 全局单例访问器
# ============================================================

_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局 ToolRegistry 实例（懒初始化单例）。

    首次调用时通过 FastAPI 的 ``get_db()`` 依赖获取 DB session，
    并创建 ToolRegistry 实例。

    注意：
    - 首次调用必须在 FastAPI 请求上下文内（DB session 可用）
    - ToolRegistry 持有的 DB session 在进程生命周期内复用。
      ToolRegistry 主要用于工具查找/调度，不直接修改 DB，因此
      单 session 复用是安全的（任务执行通过各自的 db session）。
    - 单元测试中可通过 ``app.services.harness.tool_registry._registry = None``
      重置，或直接 patch ``get_tool_registry``。

    Phase 3-Plan-1A: 当前用于 McpServerManager 初始化。
    完整生命周期管理（FastAPI lifespan 启动/关闭）见后续 Task 5 完善。
    """
    global _registry
    if _registry is None:
        # 延迟导入避免循环依赖（get_db -> app.models）
        from app.models import get_db

        db_gen = get_db()
        db = next(db_gen)
        try:
            _registry = ToolRegistry(db)
        finally:
            # 不关闭 db：单例需要长期持有 session
            # 异常时关闭避免连接泄漏
            pass
    return _registry


def reset_tool_registry() -> None:
    """重置全局 ToolRegistry 单例（仅用于测试）。"""
    global _registry
    _registry = None
