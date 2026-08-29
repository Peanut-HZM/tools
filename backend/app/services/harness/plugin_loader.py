"""Plugin Loader — 文件插件系统的核心

Phase 3 P2-①b 文件插件系统

职责：
1. @register_tool 装饰器：把 async def fn(arguments, context) 包成 ToolProtocol 实例
2. FunctionTool：实现 ToolProtocol，execute 时调用原函数 + _wrap_result 映射
3. PluginLoader.scan()：启动时扫描目录，importlib 加载每个 .py 触发装饰器注册
4. _wrap_result()：把插件函数返回 dict 映射到 ToolResult

不修改 ToolRegistry / ToolProtocol，仅复用 register_dynamic 接口。
"""
from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, AsyncIterator, Callable, List, Union

from app.services.harness.tool_protocol import (
    ToolContext,
    ToolEvent,
    ToolResult,
)

logger = logging.getLogger(__name__)


def register_tool(
    *,
    name: str,
    description: str,
    parameters: dict,
) -> Callable[[Callable], "FunctionTool"]:
    """装饰器：把 async def fn(arguments, context) 包成 ToolProtocol 实例。

    Usage:
        @register_tool(name="my_tool", description="...", parameters={...})
        async def my_tool(arguments: dict, context: ToolContext) -> dict:
            return {"text": "hello"}

    Returns:
        FunctionTool 实例（同时已注册到全局 ToolRegistry 的 _dynamic 命名空间）

    Raises:
        ValueError: name / description 为空
        TypeError: 被装饰函数不是 async def
    """
    if not name or not isinstance(name, str):
        raise ValueError("register_tool: name 不能为空")
    if not description or not isinstance(description, str):
        raise ValueError("register_tool: description 不能为空")
    if parameters is None:
        parameters = {}

    def decorator(fn: Callable) -> FunctionTool:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError(
                f"register_tool: 被装饰函数 {fn.__name__} 必须是 async def"
            )

        tool = FunctionTool(
            name=name,
            description=description,
            parameters=parameters,
            fn=fn,
        )

        # 注册到全局 ToolRegistry（与 MCP tools 共存于 _dynamic 命名空间）
        # 单测 / DB 不可用环境下注册失败不阻断装饰器返回 FunctionTool 实例
        from app.services.harness.tool_registry import get_tool_registry

        try:
            registry = get_tool_registry()
            registry.register_dynamic(tool)
            logger.info(f"[Plugin] 已注册插件工具: {name} (fn={fn.__name__})")
        except Exception as e:
            logger.debug(
                f"[Plugin] 跳过全局注册 name={name} fn={fn.__name__}: "
                f"{type(e).__name__}: {e}"
            )

        return tool

    return decorator


class FunctionTool:
    """由 @register_tool 装饰器构造，实现完整 ToolProtocol。

    execute() 委托给原函数，然后 _wrap_result 把返回 dict 映射到 ToolResult。
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters: dict,
        fn: Callable,
    ):
        self._name = name
        self._description = description
        self._parameters_schema = parameters or {}
        self._fn = fn

    # ---- ToolProtocol 属性 ----

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict:
        return self._parameters_schema

    @property
    def returns_schema(self):
        return None

    # ---- 生命周期 ----

    async def initialize(self) -> None:
        """插件默认无需初始化"""
        pass

    async def shutdown(self) -> None:
        """插件默认无需关闭"""
        pass

    # ---- 可用性 ----

    def is_available(self, ctx: ToolContext) -> bool:
        """插件默认对所有 agent 可用（可后续通过 binding 控制）"""
        return True

    # ---- LLM 集成 ----

    def to_function_schema(self) -> dict:
        """生成 OpenAI function calling 格式 schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    # ---- 核心执行 ----

    async def execute(self, arguments: dict, ctx: ToolContext) -> ToolResult:
        """调用原函数 + _wrap_result 映射返回"""
        try:
            raw = await self._fn(arguments, ctx)
        except Exception as e:
            logger.exception(
                f"[Plugin] 插件工具执行失败 name={self._name}: {type(e).__name__}: {e}"
            )
            return ToolResult.error(f"插件工具 {self._name} 执行失败: {e}")
        return _wrap_result(self._name, raw)

    async def execute_stream(
        self, arguments: dict, ctx: ToolContext
    ) -> AsyncIterator[ToolEvent]:
        """默认包装 execute 为单事件"""
        result = await self.execute(arguments, ctx)
        yield ToolEvent(type="result", payload=result)


def _wrap_result(tool_name: str, raw: Any) -> ToolResult:
    """把 plugin 函数返回的 dict 映射到 ToolResult。

    约定（key 优先级从高到低）：
      1. {"error": "..."}                       → ToolResult.error(...)
      2. {"text": "..."}                        → ToolResult.text(...)
      3. {"image": url, "alt": "..."}           → ToolResult.image(url, alt=...)
      4. {"json": {...}}                        → ToolResult.json(...)
      5. 其它 dict / 非 dict                    → ToolResult(success=True, content=raw, content_type="json")
      6. None                                   → ToolResult(success=True, content="", content_type="text")

    Args:
        tool_name: 用于错误日志
        raw: plugin 函数返回值

    Returns:
        ToolResult 实例
    """
    if raw is None:
        return ToolResult(success=True, content="", content_type="text")

    if not isinstance(raw, dict):
        # 非 dict（如 list / str / int / 自定义对象）→ 视作 JSON content
        return ToolResult(success=True, content=raw, content_type="json")

    # dict：按约定 key 优先级匹配
    if "error" in raw:
        return ToolResult.error(str(raw["error"]))

    if "text" in raw:
        return ToolResult.text(str(raw["text"]))

    if "image" in raw:
        url = raw["image"]
        if not isinstance(url, str):
            return ToolResult.error(
                f"插件 {tool_name}: image 字段必须是 url 字符串，得到 {type(url).__name__}"
            )
        alt = raw.get("alt", "")
        return ToolResult.image(url, alt=alt if isinstance(alt, str) else "")

    if "json" in raw:
        return ToolResult.json(raw["json"])

    # 其它 dict（无约定 key）→ 视作 JSON content
    return ToolResult(success=True, content=raw, content_type="json")


class PluginLoader:
    """扫描插件目录、加载所有 .py、注册 tool 到 tool_registry。

    失败隔离：单文件抛异常时记录 ERROR log + 跳过该文件，不阻断整体加载。
    """

    def __init__(self, tool_registry) -> None:
        self.tool_registry = tool_registry
        self._loaded: List[str] = []  # 已成功加载的 plugin 文件名

    def scan(self, plugins_dir: Union[str, Path]) -> None:
        """扫描 plugins_dir 下所有 *.py，逐个 importlib 加载。

        跳过 _*.py 与 __pycache__/。
        单文件失败（SyntaxError / ImportError / 装饰器 ValueError 等）只记录 ERROR log。

        实现细节：装饰器通过 ``get_tool_registry()`` 单例拿到 registry，
        这里在 exec_module 前临时把单例替换为 self.tool_registry，
        exec_module 后还原。生产环境 main.py 把真实的 get_tool_registry() 传入；
        测试中可传 MagicMock。
        """
        plugins_path = Path(plugins_dir)

        if not plugins_path.exists() or not plugins_path.is_dir():
            logger.warning(
                f"[PluginLoader] plugins directory not found or not a dir: {plugins_path}"
            )
            return

        # 列出 *.py（不含 _*.py 和 __pycache__/）
        py_files = sorted(
            p
            for p in plugins_path.glob("*.py")
            if p.is_file() and not p.name.startswith("_")
        )

        if not py_files:
            logger.info(
                f"[PluginLoader] no plugins found in: {plugins_path}"
            )
            return

        logger.info(f"[PluginLoader] 发现 {len(py_files)} 个插件文件，开始加载")

        # 临时把全局单例替换为 self.tool_registry，让装饰器注册到传入的 registry
        from app.services.harness import tool_registry as _tr_module

        original = _tr_module._registry
        _tr_module._registry = self.tool_registry
        try:
            for py_file in py_files:
                module_name = f"_plugin_{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, str(py_file))
                if spec is None or spec.loader is None:
                    logger.error(f"[PluginLoader] 无法构造 spec: {py_file.name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except SyntaxError as e:
                    logger.error(
                        f"[PluginLoader] 语法错误 {py_file.name}: {e.msg} (line {e.lineno})"
                    )
                    continue
                except ImportError as e:
                    logger.error(
                        f"[PluginLoader] 导入错误 {py_file.name}: {e}"
                    )
                    continue
                except ValueError as e:
                    # 装饰器在校验失败时抛 ValueError
                    logger.error(
                        f"[PluginLoader] 装饰器校验失败 {py_file.name}: {e}"
                    )
                    continue
                except Exception as e:
                    # 任何其他异常（包含装饰器副作用）一并隔离
                    logger.exception(
                        f"[PluginLoader] 加载失败 {py_file.name}: "
                        f"{type(e).__name__}: {e}"
                    )
                    continue

                # 成功执行模块后，装饰器已调用 tool_registry.register_dynamic
                self._loaded.append(py_file.name)
                logger.info(f"[PluginLoader] 已加载: {py_file.name}")

            logger.info(
                f"[PluginLoader] 加载完成: 共 {len(py_files)} 个文件，"
                f"成功 {len(self._loaded)} 个"
            )
        finally:
            # 还原全局单例，避免污染后续代码
            _tr_module._registry = original
