"""ToolRegistry 动态注册 + 启动时 MCP 同步测试

覆盖：
- ``_dynamic`` 字典存在并独立于 ``_builtin``
- ``register_dynamic`` / ``unregister_dynamic`` 基本行为
- 重复 register 警告并覆盖
- 注销未注册名称为 no-op
- 注销动态工具不影响同名 builtin（隔离）
- ``_resolve_tool_by_name`` 查询顺序：_builtin → _dynamic → DB(http)
- startup 同步逻辑（mock DB / manager）
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tool_protocol import ToolContext, ToolEvent, ToolResult
from app.services.harness.tools.mcp_tool import McpTool


# ================================================================
# Fixtures
# ================================================================


class FakeDynamicTool:
    """用于动态注册测试的假工具对象。

    实现 ToolProtocol 的最小接口。
    """

    def __init__(self, name: str = "mcp:test:tool1", description: str = ""):
        self.name = name
        self.description = description

    async def execute(self, args, ctx):
        return ToolResult.text("ok")

    async def execute_stream(self, args, ctx):
        yield ToolEvent(type="result", payload=ToolResult.text("ok"))

    def to_function_schema(self):
        return {"name": self.name, "description": self.description}

    def is_available(self, ctx):
        return True

    async def initialize(self):
        pass

    async def shutdown(self):
        pass


@pytest.fixture
def fresh_registry():
    """返回干净状态（无 builtin 注册）的 registry。"""
    mock_db = MagicMock()
    return ToolRegistry(mock_db)


@pytest.fixture
def ctx():
    return ToolContext(user_id="u1", conversation_id="c1", agent_id="a1", db=None)


# ================================================================
# _dynamic 字典存在性
# ================================================================


def test_dynamic_dict_exists(fresh_registry):
    """__init__ 后应存在 _dynamic 字典（独立于 _builtin）"""
    assert hasattr(fresh_registry, "_dynamic")
    assert isinstance(fresh_registry._dynamic, dict)
    assert fresh_registry._dynamic == {}


def test_dynamic_dict_is_separate_from_builtin(fresh_registry):
    """_dynamic 与 _builtin 必须是独立字典（不共享引用）"""
    assert fresh_registry._dynamic is not fresh_registry._builtin


# ================================================================
# register_dynamic / unregister_dynamic 基础行为
# ================================================================


def test_register_dynamic_adds_to_dynamic_dict(fresh_registry):
    """register_dynamic 应将工具加入 _dynamic"""
    tool = FakeDynamicTool(name="mcp:test:tool1")
    fresh_registry.register_dynamic(tool)

    assert "mcp:test:tool1" in fresh_registry._dynamic
    assert fresh_registry._dynamic["mcp:test:tool1"] is tool


def test_register_dynamic_keeps_builtin_separate(fresh_registry):
    """register_dynamic 不应写入 _builtin"""
    tool = FakeDynamicTool(name="mcp:test:tool1")
    fresh_registry.register_dynamic(tool)

    assert "mcp:test:tool1" not in fresh_registry._builtin


def test_unregister_dynamic_removes_from_dynamic_dict(fresh_registry):
    """unregister_dynamic 应从 _dynamic 移除"""
    tool = FakeDynamicTool(name="mcp:test:tool1")
    fresh_registry.register_dynamic(tool)
    assert "mcp:test:tool1" in fresh_registry._dynamic

    fresh_registry.unregister_dynamic("mcp:test:tool1")
    assert "mcp:test:tool1" not in fresh_registry._dynamic


def test_unregister_dynamic_nonexistent_is_noop(fresh_registry):
    """注销未注册的名称不应抛异常"""
    # 不应抛 KeyError 等
    fresh_registry.unregister_dynamic("never_registered")
    assert fresh_registry._dynamic == {}


def test_unregister_dynamic_does_not_touch_builtin(fresh_registry):
    """注销动态工具不应影响同名 builtin"""
    # 1. 注册一个 builtin
    builtin_tool = FakeDynamicTool(name="shared_name")
    fresh_registry._builtin["shared_name"] = builtin_tool

    # 2. 注销该名称（即使 builtin 中存在，也不动 builtin）
    fresh_registry.unregister_dynamic("shared_name")

    assert "shared_name" in fresh_registry._builtin
    assert fresh_registry._builtin["shared_name"] is builtin_tool


# ================================================================
# register_dynamic 覆盖行为
# ================================================================


def test_register_dynamic_overwrites_existing_with_warning(fresh_registry, caplog):
    """同名重复注册应记录 warning 并覆盖旧实例"""
    import logging

    tool_v1 = FakeDynamicTool(name="mcp:test:tool1")
    tool_v2 = FakeDynamicTool(name="mcp:test:tool1")

    fresh_registry.register_dynamic(tool_v1)
    with caplog.at_level(logging.WARNING, logger="app.services.harness.tool_registry"):
        fresh_registry.register_dynamic(tool_v2)

    assert fresh_registry._dynamic["mcp:test:tool1"] is tool_v2
    # 验证 warning 被记录
    assert any("已注册" in r.message or "覆盖" in r.message for r in caplog.records)


def test_register_dynamic_accepts_mcp_tool_instance(fresh_registry):
    """McpTool 实例（Task 4 真实类型）应可注册"""
    mock_client = MagicMock()
    tool = McpTool(
        server_id=MagicMock(),
        server_name="test_server",
        tool_name="search",
        description="search tool",
        input_schema={},
        client=mock_client,
        timeout=30,
    )
    fresh_registry.register_dynamic(tool)

    assert "mcp:test_server:search" in fresh_registry._dynamic


# ================================================================
# _resolve_tool_by_name 查询顺序
# ================================================================


@pytest.mark.asyncio
async def test_resolve_by_name_prefers_builtin_over_dynamic(fresh_registry):
    """_resolve_tool_by_name 应优先返回 builtin（即使同名 dynamic 已注册）"""
    builtin = FakeDynamicTool(name="shared_tool")
    dynamic = FakeDynamicTool(name="shared_tool")
    fresh_registry._builtin["shared_tool"] = builtin
    fresh_registry._dynamic["shared_tool"] = dynamic

    resolved = await fresh_registry._resolve_tool_by_name("shared_tool")
    assert resolved is builtin


@pytest.mark.asyncio
async def test_resolve_by_name_falls_back_to_dynamic(fresh_registry):
    """builtin 中没有时，应返回 dynamic 中的工具"""
    dynamic = FakeDynamicTool(name="mcp:test:tool1")
    fresh_registry.register_dynamic(dynamic)

    resolved = await fresh_registry._resolve_tool_by_name("mcp:test:tool1")
    assert resolved is dynamic


@pytest.mark.asyncio
async def test_resolve_by_name_falls_back_to_db_http_tool(fresh_registry):
    """builtin / dynamic 都没有时，应查 DB（HTTP 工具）"""
    from app.services.harness.exceptions import ToolNotFoundError
    from app.services.harness.tools.http_tool import HttpTool

    # DB 返回 http 工具记录
    mock_db_tool = MagicMock()
    mock_db_tool.type = "http"
    mock_db_tool.is_active = True
    mock_db_tool.id = "db-tool-1"

    fresh_registry.db.query.return_value.filter.return_value.first.return_value = mock_db_tool

    resolved = await fresh_registry._resolve_tool_by_name("http_tool_name")
    assert isinstance(resolved, HttpTool)


@pytest.mark.asyncio
async def test_resolve_by_name_raises_when_not_found(fresh_registry):
    """三处都没有时应抛 ToolNotFoundError"""
    from app.services.harness.exceptions import ToolNotFoundError

    fresh_registry.db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(ToolNotFoundError):
        await fresh_registry._resolve_tool_by_name("nonexistent_tool")


# ================================================================
# execute() 路径验证（动态工具经鉴权 + 分发）
# ================================================================


@pytest.mark.asyncio
async def test_execute_dynamic_tool_when_authorized(fresh_registry, ctx):
    """动态工具经 _resolve_tool_by_name 正确解析后应可执行"""
    from app.services.harness.tool_protocol import ToolCall

    dynamic = FakeDynamicTool(name="mcp:test:tool1")
    fresh_registry.register_dynamic(dynamic)

    # mock execute 行为
    dynamic.execute = AsyncMock(return_value=ToolResult.text("mcp result"))

    call = ToolCall(id="c1", name="mcp:test:tool1", arguments={})

    # mock get_tools_for_agent 返回包含此动态工具
    with patch.object(
        fresh_registry, "get_tools_for_agent", AsyncMock(return_value=[dynamic])
    ):
        result = await fresh_registry.execute(call, ctx)

    assert result.success is True
    assert result.content == "mcp result"
    dynamic.execute.assert_awaited_once()


# ================================================================
# 启动时 MCP 同步逻辑（main.py）
# ================================================================


class TestStartupMcpSync:
    """测试 main.py 的 sync_mcp_servers 启动逻辑"""

    @pytest.mark.asyncio
    async def test_sync_mcp_servers_calls_active_servers(self):
        """sync_mcp_servers 应遍历所有 is_active=True 的 McpServer"""
        # 动态导入避免循环依赖
        from app.main import sync_mcp_servers

        # 构造 mock McpServer
        server1 = MagicMock()
        server1.id = "srv-1"
        server1.name = "server1"
        server1.is_active = True

        server2 = MagicMock()
        server2.id = "srv-2"
        server2.name = "server2"
        server2.is_active = True

        # mock DB session
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.all.return_value = [server1, server2]

        # mock manager
        mock_manager = MagicMock()
        mock_manager.sync_server = AsyncMock(
            return_value={"success": True, "tools_count": 3, "error": None}
        )

        # SessionLocal 是在 sync_mcp_servers 内部延迟导入，patch 源模块即可
        with patch("app.models.base.SessionLocal", return_value=mock_db), patch(
            "app.services.harness.mcp_server_manager.get_mcp_server_manager",
            return_value=mock_manager,
        ):
            await sync_mcp_servers()

        # 两个 server 都应被同步
        assert mock_manager.sync_server.await_count == 2

    @pytest.mark.asyncio
    async def test_sync_mcp_servers_continues_on_failure(self):
        """单个 server 同步失败不应阻塞后续 server"""
        from app.main import sync_mcp_servers

        server1 = MagicMock()
        server1.id = "srv-1"
        server1.name = "broken"
        server1.is_active = True

        server2 = MagicMock()
        server2.id = "srv-2"
        server2.name = "healthy"
        server2.is_active = True

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [server1, server2]

        mock_manager = MagicMock()
        # 第一个抛异常（模拟 connection refused）
        mock_manager.sync_server = AsyncMock(
            side_effect=[
                Exception("connection refused"),
                {"success": True, "tools_count": 1, "error": None},
            ]
        )

        with patch("app.models.base.SessionLocal", return_value=mock_db), patch(
            "app.services.harness.mcp_server_manager.get_mcp_server_manager",
            return_value=mock_manager,
        ):
            # 不应抛异常（失败被捕获）
            await sync_mcp_servers()

        # 两个 server 都应被尝试
        assert mock_manager.sync_server.await_count == 2

    @pytest.mark.asyncio
    async def test_sync_mcp_servers_skips_inactive(self):
        """is_active=False 的 server 不应被同步（query 过滤后不再返回）"""
        from app.main import sync_mcp_servers

        # 模拟 SQL 过滤：仅 active=True 返回
        active_server = MagicMock()
        active_server.id = "active-1"
        active_server.name = "active"
        active_server.is_active = True

        mock_db = MagicMock()
        # filter(is_active == True) 后 all() 只返回 active 的
        mock_db.query.return_value.filter.return_value.all.return_value = [active_server]

        mock_manager = MagicMock()
        mock_manager.sync_server = AsyncMock(
            return_value={"success": True, "tools_count": 2, "error": None}
        )

        with patch("app.models.base.SessionLocal", return_value=mock_db), patch(
            "app.services.harness.mcp_server_manager.get_mcp_server_manager",
            return_value=mock_manager,
        ), patch("app.models.mcp_server.McpServer") as mock_model:
            await sync_mcp_servers()

        # query 应使用 McpServer.is_active 作为过滤条件
        mock_db.query.assert_called_once_with(mock_model)
        mock_manager.sync_server.assert_awaited_once_with(active_server)