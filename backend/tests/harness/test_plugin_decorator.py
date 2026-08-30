"""@register_tool 装饰器 + FunctionTool 单元测试

参考 docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1b-file-plugin-system-design.md §3.2, §3.4
"""
import inspect
from typing import Any

import pytest

from app.services.harness.tool_protocol import ToolContext, ToolEvent, ToolResult
from app.services.harness.plugin_loader import (
    FunctionTool,
    _wrap_result,
    register_tool,
)


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(user_id="u1", conversation_id="c1", agent_id="a1", db=None)


# ============================================================
# 装饰器签名校验（开发期 fail-fast）
# ============================================================


def test_register_tool_basic_returns_function_tool():
    """装饰器应返回 FunctionTool 实例（同时注册到全局 registry）"""

    @register_tool(
        name="my_echo",
        description="Echo tool",
        parameters={"type": "object", "properties": {"msg": {"type": "string"}}},
    )
    async def my_echo(arguments: dict, context: ToolContext) -> dict:
        return {"text": arguments.get("msg", "")}

    assert isinstance(my_echo, FunctionTool)
    assert my_echo.name == "my_echo"


def test_register_tool_missing_name_raises():
    """缺 name 必须 ValueError"""

    with pytest.raises(ValueError, match="name"):

        @register_tool(name="", description="x", parameters={})  # type: ignore[arg-type]
        async def fn(arguments: dict, context: ToolContext) -> dict:
            return {"text": ""}


def test_register_tool_missing_description_raises():
    """缺 description 必须 ValueError"""

    with pytest.raises(ValueError, match="description"):

        @register_tool(name="x", description="", parameters={})
        async def fn(arguments: dict, context: ToolContext) -> dict:
            return {"text": ""}


def test_register_tool_sync_function_rejected():
    """装饰同步函数必须 TypeError"""

    with pytest.raises(TypeError, match="async"):

        @register_tool(name="x", description="x", parameters={})
        def fn(arguments: dict, context: ToolContext) -> dict:  # type: ignore[arg-type]
            return {"text": ""}


# ============================================================
# FunctionTool 方法测试
# ============================================================


@pytest.mark.asyncio
async def test_function_tool_execute_calls_fn_and_wraps_result(ctx):
    """execute 应调用 fn 并把返回 dict 通过 _wrap_result 映射"""

    @register_tool(name="echo_wrap", description="Echo", parameters={})
    async def echo_wrap(arguments: dict, context: ToolContext) -> dict:
        return {"text": f"got:{arguments.get('msg', '')}"}

    result = await echo_wrap.execute({"msg": "hi"}, ctx)
    assert result.success is True
    assert result.content == "got:hi"
    assert result.content_type == "text"


@pytest.mark.asyncio
async def test_function_tool_execute_fn_raises_returns_error(ctx):
    """fn 抛异常时 execute 返回 ToolResult.error（不向上抛）"""

    @register_tool(name="boom", description="boom", parameters={})
    async def boom(arguments: dict, context: ToolContext) -> dict:
        raise RuntimeError("kaboom")

    result = await boom.execute({}, ctx)
    assert result.success is False
    assert "kaboom" in (result.error_message or "")


@pytest.mark.asyncio
async def test_function_tool_execute_stream_emits_single_result(ctx):
    """execute_stream 默认包装 execute 为单事件"""

    @register_tool(name="echo_stream", description="echo", parameters={})
    async def echo_stream(arguments: dict, context: ToolContext) -> dict:
        return {"text": "ok"}

    events = []
    async for ev in echo_stream.execute_stream({}, ctx):
        events.append(ev)
    assert len(events) == 1
    assert events[0].type == "result"
    assert events[0].payload.content == "ok"


def test_function_tool_to_function_schema():
    """to_function_schema 返回 OpenAI function calling 格式"""

    @register_tool(
        name="schema_tool",
        description="Has schema",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
    )
    async def schema_tool(arguments: dict, context: ToolContext) -> dict:
        return {"text": ""}

    schema = schema_tool.to_function_schema()
    assert schema["name"] == "schema_tool"
    assert schema["description"] == "Has schema"
    assert "properties" in schema["parameters"]


def test_function_tool_is_available_returns_true(ctx):
    """插件默认对所有 agent 可用"""

    @register_tool(name="avail", description="d", parameters={})
    async def avail(arguments: dict, context: ToolContext) -> dict:
        return {"text": ""}

    assert avail.is_available(ctx) is True


def test_function_tool_initialize_shutdown_noop():
    """插件 initialize / shutdown 默认 no-op"""

    @register_tool(name="noop", description="d", parameters={})
    async def noop(arguments: dict, context: ToolContext) -> dict:
        return {"text": ""}

    # 不抛异常即通过
    import asyncio

    asyncio.run(noop.initialize())
    asyncio.run(noop.shutdown())


# ============================================================
# _wrap_result 全部分支
# ============================================================


def test_wrap_result_text():
    r = _wrap_result("t", {"text": "hello"})
    assert r.success is True
    assert r.content == "hello"
    assert r.content_type == "text"


def test_wrap_result_json():
    r = _wrap_result("t", {"json": {"a": 1}})
    assert r.success is True
    assert r.content == {"a": 1}
    assert r.content_type == "json"


def test_wrap_result_image_with_alt():
    r = _wrap_result("t", {"image": "https://x/y.png", "alt": "logo"})
    assert r.success is True
    assert r.content_type == "image"
    assert r.attachments[0].url == "https://x/y.png"
    assert r.attachments[0].name == "logo"


def test_wrap_result_image_without_alt():
    r = _wrap_result("t", {"image": "https://x/y.png"})
    assert r.success is True
    assert r.content_type == "image"


def test_wrap_result_image_invalid_type_returns_error():
    """image 字段非 str 应返回 error"""
    r = _wrap_result("t", {"image": 123})
    assert r.success is False
    assert "image" in (r.error_message or "")


def test_wrap_result_error():
    r = _wrap_result("t", {"error": "boom"})
    assert r.success is False
    assert r.content_type == "error"
    assert "boom" in (r.error_message or "")


def test_wrap_result_unknown_dict_falls_back_to_json_content():
    """未知 dict → content_type=json，content=原始 dict"""
    r = _wrap_result("t", {"custom_key": "v", "nested": {"a": 1}})
    assert r.success is True
    assert r.content == {"custom_key": "v", "nested": {"a": 1}}
    assert r.content_type == "json"


def test_wrap_result_non_dict_returns_json_content():
    """非 dict (list/str/int) → content_type=json"""
    r = _wrap_result("t", [1, 2, 3])
    assert r.success is True
    assert r.content == [1, 2, 3]
    assert r.content_type == "json"


def test_wrap_result_none_returns_empty_text():
    r = _wrap_result("t", None)
    assert r.success is True
    assert r.content == ""
    assert r.content_type == "text"


def test_wrap_result_priority_error_beats_text():
    """error key 优先级高于 text"""
    r = _wrap_result("t", {"error": "x", "text": "y"})
    assert r.success is False
