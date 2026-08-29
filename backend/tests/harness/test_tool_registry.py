"""ToolRegistry 单元测试

覆盖:
- register_builtin: 注册 + 重复检测
- get_tools_for_agent: 内置工具返回 + binding 加载 + is_available 过滤
- execute: 正常分发 + 未知工具错误 + 异常捕获
- execute_stream: 正常流式分发 + 未知工具错误
- to_function_schemas: 批量生成
- initialize_all / shutdown_all: 生命周期
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tools.web_search import WebSearchTool
from app.services.harness.tools.db_query import DbQueryTool
from app.services.harness.tool_protocol import ToolContext, ToolCall, ToolResult, ToolEvent


@pytest.fixture
def registry(test_db):
    reg = ToolRegistry(db=test_db)
    # 注册内置工具
    reg.register_builtin(WebSearchTool())
    reg.register_builtin(DbQueryTool())
    return reg


@pytest.fixture
def ctx():
    """构造一个最小可用的 ToolContext"""
    return ToolContext(
        user_id="u1",
        conversation_id="c1",
        agent_id="a1",
        db=None,
    )


# ================================================================
# 注册
# ================================================================


def test_register_builtin(registry):
    """register_builtin 应注册内置工具"""
    assert "web_search" in registry._builtin
    assert "db_query" in registry._builtin


def test_register_duplicate_raises(registry):
    """重复注册应抛 ValueError"""
    with pytest.raises(ValueError, match="重复注册"):
        registry.register_builtin(WebSearchTool())


# ================================================================
# 查询
# ================================================================


@pytest.mark.asyncio
async def test_get_tools_for_agent_returns_builtins(registry, ctx):
    """get_tools_for_agent 应返回所有可用的内置工具（无 binding 时）"""
    with patch.object(registry, "_load_bindings", return_value=[]):
        tools = await registry.get_tools_for_agent("agent-id", ctx)
    names = [t.name for t in tools]
    assert "web_search" in names
    assert "db_query" in names


@pytest.mark.asyncio
async def test_get_tools_for_agent_filters_unavailable(registry, ctx):
    """is_available 返回 False 的工具不应出现在结果中"""
    # 让 web_search 的 is_available 返回 False
    registry._builtin["web_search"].is_available = lambda c: False

    with patch.object(registry, "_load_bindings", return_value=[]):
        tools = await registry.get_tools_for_agent("agent-id", ctx)
    names = [t.name for t in tools]
    assert "web_search" not in names
    assert "db_query" in names


# ================================================================
# 执行
# ================================================================


@pytest.mark.asyncio
async def test_execute_builtin_tool(registry, ctx):
    """execute 应分发到正确的内置工具"""
    call = ToolCall(id="call_1", name="web_search", arguments={"query": "python"})

    # mock 工具的 execute，避免真正发起网络请求
    mock_execute = AsyncMock(return_value=ToolResult.text("search result"))
    registry._builtin["web_search"].execute = mock_execute

    with patch.object(registry, "_load_bindings", return_value=[]):
        result = await registry.execute(call, ctx)
    assert result.success is True
    assert result.content == "search result"
    mock_execute.assert_awaited_once_with(call.arguments, ctx)


@pytest.mark.asyncio
async def test_execute_unknown_tool_returns_error(registry, ctx):
    """执行未知工具应返回错误结果"""
    call = ToolCall(id="call_2", name="nonexistent", arguments={})

    result = await registry.execute(call, ctx)
    assert result.success is False
    assert "not found" in result.error_message.lower() or "未找到" in result.error_message


@pytest.mark.asyncio
async def test_execute_tool_exception_returns_error(registry, ctx):
    """工具执行抛异常时，execute 应捕获并返回错误结果"""
    call = ToolCall(id="call_3", name="web_search", arguments={"query": "test"})

    mock_execute = AsyncMock(side_effect=RuntimeError("boom"))
    registry._builtin["web_search"].execute = mock_execute

    with patch.object(registry, "_load_bindings", return_value=[]):
        result = await registry.execute(call, ctx)
    assert result.success is False
    assert "boom" in result.error_message


@pytest.mark.asyncio
async def test_execute_unauthorized_tool_returns_error(registry, ctx):
    """agent 没有该工具的绑定/可用性时，execute 应返回鉴权失败结果"""
    call = ToolCall(id="call_4", name="web_search", arguments={"query": "test"})

    # 让 web_search 对当前 ctx 不可用 → get_tools_for_agent 不会包含它
    registry._builtin["web_search"].is_available = lambda c: False

    mock_execute = AsyncMock(return_value=ToolResult.text("should not be called"))
    registry._builtin["web_search"].execute = mock_execute

    with patch.object(registry, "_load_bindings", return_value=[]):
        result = await registry.execute(call, ctx)

    assert result.success is False
    assert "未被授权" in result.error_message or "未授权" in result.error_message
    mock_execute.assert_not_awaited()


# ================================================================
# 流式执行
# ================================================================


@pytest.mark.asyncio
async def test_execute_stream_builtin(registry, ctx):
    """execute_stream 应分发到工具的 execute_stream"""
    call = ToolCall(id="call_s1", name="db_query", arguments={"sql": "SELECT 1"})

    expected_event = ToolEvent(type="result", payload=ToolResult.json({"rows": []}))

    async def mock_stream(args, c):
        yield expected_event

    registry._builtin["db_query"].execute_stream = mock_stream

    events = []
    with patch.object(registry, "_load_bindings", return_value=[]):
        async for event in registry.execute_stream(call, ctx):
            events.append(event)

    assert len(events) == 1
    assert events[0].type == "result"


@pytest.mark.asyncio
async def test_execute_stream_unknown_tool(registry, ctx):
    """流式执行未知工具应产出 error 事件"""
    call = ToolCall(id="call_s2", name="nonexistent", arguments={})

    events = []
    async for event in registry.execute_stream(call, ctx):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == "error"


@pytest.mark.asyncio
async def test_execute_stream_unauthorized_tool_returns_error(registry, ctx):
    """agent 没有该工具的绑定/可用性时，execute_stream 应产出鉴权失败 error 事件"""
    call = ToolCall(id="call_s3", name="db_query", arguments={"sql": "SELECT 1"})

    # 让 db_query 对当前 ctx 不可用
    registry._builtin["db_query"].is_available = lambda c: False

    async def mock_stream(args, c):
        yield ToolEvent(type="result", payload=ToolResult.json({"rows": []}))

    registry._builtin["db_query"].execute_stream = mock_stream

    events = []
    with patch.object(registry, "_load_bindings", return_value=[]):
        async for event in registry.execute_stream(call, ctx):
            events.append(event)

    assert len(events) == 1
    assert events[0].type == "error"
    assert "未被授权" in events[0].payload.get("message", "") or "未授权" in events[0].payload.get("message", "")


# ================================================================
# Schema 生成
# ================================================================


def test_to_function_schemas(registry):
    """to_function_schemas 应批量生成 LLM 可用的 schema 列表"""
    tools = [WebSearchTool(), DbQueryTool()]
    schemas = registry.to_function_schemas(tools)
    assert len(schemas) == 2
    assert schemas[0]["name"] == "web_search"
    assert schemas[1]["name"] == "db_query"
    # 每个 schema 都应包含 description 和 parameters
    for schema in schemas:
        assert "description" in schema
        assert "parameters" in schema


# ================================================================
# 生命周期
# ================================================================


@pytest.mark.asyncio
async def test_initialize_all(registry):
    """initialize_all 应调用每个内置工具的 initialize"""
    for tool in registry._builtin.values():
        tool.initialize = AsyncMock()

    await registry.initialize_all()

    for tool in registry._builtin.values():
        tool.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_all(registry):
    """shutdown_all 应调用每个内置工具的 shutdown"""
    for tool in registry._builtin.values():
        tool.shutdown = AsyncMock()

    await registry.shutdown_all()

    for tool in registry._builtin.values():
        tool.shutdown.assert_awaited_once()


# ============================================================
# 动态工具注册（Phase 3-Plan-1A: MCP tools）
# ============================================================


class TestDynamicRegistration:
    """register_dynamic / unregister_dynamic 测试

    动态工具独立存储于 ``_dynamic``，与 ``_builtin`` 隔离。
    """

    def test_register_dynamic_adds_tool(self, registry, test_db):
        """register_dynamic 应将工具加入 _dynamic 字典"""
        from app.services.harness.tool_protocol import ToolResult

        class FakeMcpTool:
            name = "mcp_test_tool"
            description = "MCP test tool"
            is_dynamic = True

            async def execute(self, args, ctx):
                return ToolResult.success("ok")

            async def execute_stream(self, args, ctx):
                yield ToolEvent(type="text", payload={"text": "ok"})

            def to_function_schema(self):
                return {"name": self.name, "description": self.description}

            def is_available(self, ctx):
                return True

        tool = FakeMcpTool()
        registry.register_dynamic(tool)

        assert "mcp_test_tool" in registry._dynamic
        assert registry._dynamic["mcp_test_tool"] is tool
        assert "mcp_test_tool" not in registry._builtin

    def test_unregister_dynamic_removes_tool(self, registry):
        """unregister_dynamic 应移除 _dynamic 中的工具"""
        from app.services.harness.tool_protocol import ToolResult

        class FakeMcpTool:
            name = "mcp_remove_me"
            description = ""

            async def execute(self, args, ctx):
                return ToolResult.success("ok")

            async def execute_stream(self, args, ctx):
                yield ToolEvent(type="text", payload={"text": "ok"})

            def to_function_schema(self):
                return {}

            def is_available(self, ctx):
                return True

        tool = FakeMcpTool()
        registry.register_dynamic(tool)
        assert "mcp_remove_me" in registry._dynamic

        registry.unregister_dynamic("mcp_remove_me")
        assert "mcp_remove_me" not in registry._dynamic


class TestGetToolRegistry:
    """get_tool_registry 单例函数测试"""

    def setup_method(self):
        import app.services.harness.tool_registry as tr_module

        tr_module._registry = None

    def teardown_method(self):
        import app.services.harness.tool_registry as tr_module

        tr_module._registry = None

    def test_get_tool_registry_singleton(self, test_db):
        """get_tool_registry 应返回同一单例"""
        from app.services.harness.tool_registry import (
            get_tool_registry,
            _registry,
        )

        # mock get_db to return test_db session (side_effect 生成新迭代器)
        with patch("app.models.get_db", side_effect=lambda: iter([test_db])):

            r1 = get_tool_registry()
            r2 = get_tool_registry()

            assert r1 is r2
            assert isinstance(r1, ToolRegistry)

    def test_reset_tool_registry_clears_singleton(self, test_db):
        """reset_tool_registry 应清除单例"""
        from app.services.harness.tool_registry import (
            get_tool_registry,
            reset_tool_registry,
        )

        with patch("app.models.get_db", side_effect=lambda: iter([test_db])):

            r1 = get_tool_registry()
            reset_tool_registry()
            r2 = get_tool_registry()
            assert r1 is not r2
