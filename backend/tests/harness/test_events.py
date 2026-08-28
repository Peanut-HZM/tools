"""Event 类型 + SSE 序列化测试（spec §7.4）"""
import json

from app.services.harness.events import Event


def test_text_delta_event():
    event = Event.text_delta("hello")
    assert event.type == "text_delta"
    assert event.payload["text"] == "hello"
    assert event.timestamp > 0


def test_tool_call_start_event():
    from app.services.harness.tool_protocol import ToolCall

    call = ToolCall(id="call_abc", name="web_search", arguments={"query": "foo"})
    event = Event.tool_call_start(call)
    assert event.type == "tool_call_start"
    assert event.payload["id"] == "call_abc"
    assert event.payload["name"] == "web_search"


def test_event_to_sse():
    event = Event.text_delta("hi")
    sse = event.to_sse()
    assert sse.startswith("event: text_delta\ndata: ")
    # 应该以 \n\n 结尾
    assert sse.endswith("\n\n")
    # 中间是有效 JSON
    data_line = sse.split("\n")[1].replace("data: ", "")
    parsed = json.loads(data_line)
    assert parsed["text"] == "hi"


def test_done_event():
    event = Event.done("final text", usage={"prompt_tokens": 10, "completion_tokens": 20})
    assert event.type == "done"
    assert event.payload["final_text"] == "final text"
    assert event.payload["usage"]["prompt_tokens"] == 10


def test_all_event_types_have_factory():
    """确保 spec 定义的所有事件类型都有对应的工厂方法"""
    factories = [
        "turn_start", "text_delta", "text_complete", "thinking_delta",
        "tool_call_start", "tool_call_progress", "tool_result",
        "image_generated", "handoff", "guardrail_triggered",
        "memory_retrieved", "error", "done", "custom",
    ]
    for name in factories:
        assert hasattr(Event, name), f"Event 缺少 {name} 工厂方法"


def test_tool_result_event_serializes_attachments():
    from app.services.harness.tool_protocol import ToolCall, ToolResult

    call = ToolCall(id="call_1", name="draw", arguments={})
    result = ToolResult.image("https://example.com/a.png", alt="猫")
    event = Event.tool_result(call, result)
    assert event.type == "tool_result"
    assert event.payload["success"] is True
    assert event.payload["content_type"] == "image"
    assert event.payload["attachments"][0]["url"] == "https://example.com/a.png"
    # 可 JSON 序列化
    json.loads(event.to_sse().split("\n")[1].replace("data: ", ""))


def test_sse_contains_timestamp_and_non_ascii():
    event = Event.text_delta("你好")
    sse = event.to_sse()
    parsed = json.loads(sse.split("\n")[1].replace("data: ", ""))
    assert parsed["text"] == "你好"
    assert parsed["timestamp"] > 0


def test_custom_event():
    event = Event.custom("my_event", foo="bar")
    assert event.type == "custom"
    assert event.payload["name"] == "my_event"
    assert event.payload["foo"] == "bar"


def test_error_event_defaults_not_recoverable():
    event = Event.error("boom")
    assert event.type == "error"
    assert event.payload["message"] == "boom"
    assert event.payload["recoverable"] is False


def test_done_event_without_usage():
    event = Event.done("ok")
    assert "usage" not in event.payload
