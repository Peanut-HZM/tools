"""Plugin tool 端到端 runtime 测试

参考 docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1b-file-plugin-system-design.md §4.3

覆盖：
- plugin tool 通过 PluginLoader.scan 注册到 ToolRegistry._dynamic
- ToolRegistry.get_tools_for_agent 返回的列表包含 plugin tool（默认对所有 agent 可用）
- ToolRegistry.execute 正常分发到 plugin tool 的原函数
- 未注册的工具名 / 未授权的工具 → ToolResult.error（不抛异常）
"""
import textwrap
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tool_protocol import (
    ToolCall,
    ToolContext,
)
from app.services.harness.plugin_loader import PluginLoader, register_tool


@pytest.fixture
def registry(test_db) -> ToolRegistry:
    """每个测试一个干净的 ToolRegistry（使用 test_db fixture 提供的 session）"""
    return ToolRegistry(db=test_db)


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(user_id="u1", conversation_id="c1", agent_id="a1", db=None)


@pytest.mark.asyncio
async def test_runtime_plugin_tool_full_chain(registry, ctx, tmp_path, monkeypatch):
    """端到端：PluginLoader.scan → tool 注册到 registry → execute 返回正确结果

    使用 monkeypatch 替换 get_tool_registry() 为 test fixture 的 registry，
    保证 PluginLoader.scan 内部装饰器调用 register_dynamic 时落到测试用 registry。
    """
    from app.services.harness import tool_registry as registry_module

    # 把测试 fixture 的 registry 注入 get_tool_registry 返回值
    monkeypatch.setattr(registry_module, "_registry", registry)

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "greeter.py").write_text(
        textwrap.dedent('''
        from app.services.harness.plugin_loader import register_tool

        @register_tool(
            name="greeter",
            description="Says hi",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
            },
        )
        async def greeter(arguments, context):
            return {"text": f"Hi {arguments.get('name', 'world')}!"}
        ''')
    )

    PluginLoader(registry).scan(plugins_dir)

    # 1. 工具已注册到 _dynamic 命名空间
    assert "greeter" in registry._dynamic

    # 2. agent 可用列表包含 plugin tool
    # mock _load_bindings 返回空列表，避免 SQLite 真实查表时的 UUID 转换问题
    with patch.object(registry, "_load_bindings", return_value=[]):
        tools = await registry.get_tools_for_agent(str(uuid4()), ctx)
    tool_names = {t.name for t in tools}
    assert "greeter" in tool_names

    # 3. execute 正常返回
    call = ToolCall(id="c1", name="greeter", arguments={"name": "Alice"})
    with patch.object(registry, "_load_bindings", return_value=[]):
        result = await registry.execute(call, ctx)

    assert result.success is True
    assert "Hi Alice!" in result.content


@pytest.mark.asyncio
async def test_runtime_plugin_tool_unknown_name_returns_error(registry, ctx):
    """执行未注册的 plugin tool → ToolResult.error(未授权/未找到)，不抛异常"""

    # 不注册任何 plugin
    with patch.object(registry, "_load_bindings", return_value=[]):
        tools = await registry.get_tools_for_agent(str(uuid4()), ctx)
    assert all(t.name != "nonexistent_plugin" for t in tools)

    call = ToolCall(id="c1", name="nonexistent_plugin", arguments={})
    with patch.object(registry, "_load_bindings", return_value=[]):
        result = await registry.execute(call, ctx)

    assert result.success is False


@pytest.mark.asyncio
async def test_runtime_plugin_tool_not_authorized_returns_error(registry, ctx, monkeypatch):
    """plugin tool 存在但未授权给当前 agent → ToolResult.error

    is_available 返回 False 模拟未授权场景。
    """
    from app.services.harness import tool_registry as registry_module

    monkeypatch.setattr(registry_module, "_registry", registry)

    @register_tool(name="restricted", description="r", parameters={})
    async def restricted(arguments, context):
        return {"text": ""}

    # 让 is_available 返回 False 模拟未授权
    restricted.is_available = lambda c: False  # type: ignore[assignment]

    call = ToolCall(id="c1", name="restricted", arguments={})
    with patch.object(registry, "_load_bindings", return_value=[]):
        result = await registry.execute(call, ctx)

    # 工具在 _dynamic 中，但 get_tools_for_agent 会过滤掉
    # 因此 execute 的鉴权阶段返回 error
    assert result.success is False