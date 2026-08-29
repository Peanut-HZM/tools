"""ToolProtocol 及相关数据结构测试（spec §6.1 / §6.2）"""
import json

import pytest

from app.services.harness.tool_protocol import (
    Attachment,
    ToolCall,
    ToolContext,
    ToolEvent,
    ToolProtocol,
    ToolResult,
)


def test_tool_result_text():
    result = ToolResult.text("hello")
    assert result.success is True
    assert result.content_type == "text"
    assert result.to_llm_text() == "hello"


def test_tool_result_json():
    result = ToolResult.json({"a": 1})
    assert result.content_type == "json"
    assert json.loads(result.to_llm_text()) == {"a": 1}


def test_tool_result_image():
    result = ToolResult.image("https://example.com/x.png", alt="图")
    assert result.content_type == "image"
    assert len(result.attachments) == 1
    assert result.attachments[0].type == "image"
    assert "https://example.com/x.png" in result.to_llm_text()


def test_tool_result_error():
    result = ToolResult.error("失败了")
    assert result.success is False
    assert result.content_type == "error"
    assert result.error_message == "失败了"
    assert "失败了" in result.to_llm_text()


def test_tool_result_defaults():
    result = ToolResult(success=True, content="x")
    assert result.content_type == "text"
    assert result.metadata == {}
    assert result.attachments == []


def test_attachment_optional_fields():
    att = Attachment(type="file", url="https://example.com/a.pdf")
    assert att.mime_type is None
    assert att.name is None
    assert att.size is None


def test_tool_call_to_dict():
    call = ToolCall(id="c1", name="web_search", arguments={"q": "x"})
    assert call.to_dict() == {"id": "c1", "name": "web_search", "arguments": {"q": "x"}}


def test_tool_event_has_timestamp():
    event = ToolEvent(type="progress", payload={"pct": 50})
    assert event.timestamp > 0
    assert event.payload["pct"] == 50


def test_tool_context_holds_dependencies():
    ctx = ToolContext(
        user_id="u1",
        conversation_id="c1",
        agent_id="a1",
        session=object(),
        db=object(),
    )
    assert ctx.user_id == "u1"
    assert ctx.conversation_id == "c1"
    assert ctx.agent_id == "a1"
    assert ctx.oss_service is None
    assert ctx.tool_state == {}


def test_tool_context_tool_state_isolated():
    ctx1 = ToolContext(user_id="u", conversation_id="c", agent_id="a", session=None, db=None)
    ctx2 = ToolContext(user_id="u", conversation_id="c", agent_id="a", session=None, db=None)
    ctx1.tool_state["k"] = 1
    assert ctx2.tool_state == {}


class _DummyTool:
    """结构上满足 ToolProtocol 的实现"""

    name = "dummy"
    display_name = "Dummy"
    description = "测试工具"
    parameters_schema: dict = {"type": "object", "properties": {}}
    returns_schema = None

    async def initialize(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult.text("ok")

    async def execute_stream(self, args: dict, ctx: ToolContext):
        yield ToolEvent(type="result", payload="ok")

    def is_available(self, ctx: ToolContext) -> bool:
        return True

    def to_function_schema(self) -> dict:
        return {"name": self.name, "parameters": self.parameters_schema}


class _NotATool:
    name = "nope"


def test_dummy_tool_satisfies_protocol():
    assert isinstance(_DummyTool(), ToolProtocol)


def test_non_tool_does_not_satisfy_protocol():
    assert not isinstance(_NotATool(), ToolProtocol)


@pytest.mark.asyncio
async def test_dummy_tool_execute():
    tool = _DummyTool()
    ctx = ToolContext(user_id="u", conversation_id="c", agent_id="a", session=None, db=None)
    result = await tool.execute({}, ctx)
    assert result.success is True
    assert result.to_llm_text() == "ok"
