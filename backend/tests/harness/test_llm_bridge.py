"""LLMFunctionBridge 测试（spec §6.5）

- build_request: 把 ToolProtocol 列表转为 LLM function schema
- parse_tool_calls: 同时支持 OpenAI 和 Claude 响应格式
- build_tool_result_messages: 把 ToolResult 包装为 tool role message
- LLMResponse: 归一化的响应结构（text_part / thinking_part / tool_calls / usage）
"""
from unittest.mock import MagicMock

import pytest

from app.services.harness.llm_bridge import LLMFunctionBridge, LLMResponse
from app.services.harness.tool_protocol import ToolCall, ToolResult
from app.services.harness.tools.web_search import WebSearchTool


def test_build_request_includes_tool_schemas():
    """build_request 应包含工具 schema"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)
    tools = [WebSearchTool()]

    request = bridge.build_request(
        messages=[{"role": "user", "content": "search python"}],
        tools=tools,
    )

    assert "tools" in request
    assert len(request["tools"]) == 1
    assert request["tools"][0]["name"] == "web_search"


def test_parse_tool_calls_openai_format():
    """parse_tool_calls 应解析 OpenAI 格式"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)

    response = {
        "content": "",
        "tool_calls": [
            {
                "id": "call_abc",
                "type": "function",
                "function": {
                    "name": "web_search",
                    "arguments": '{"query": "python"}',
                },
            }
        ],
    }

    calls = bridge.parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0].id == "call_abc"
    assert calls[0].name == "web_search"
    assert calls[0].arguments == {"query": "python"}


def test_parse_tool_calls_claude_format():
    """parse_tool_calls 应解析 Claude content block 格式"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)

    response = {
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_xyz",
                "name": "web_search",
                "input": {"query": "rust"},
            }
        ]
    }

    calls = bridge.parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0].id == "toolu_xyz"
    assert calls[0].name == "web_search"
    assert calls[0].arguments == {"query": "rust"}


def test_parse_tool_calls_no_calls():
    """无工具调用时返回空列表"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)

    response = {"content": "hello", "tool_calls": None}
    calls = bridge.parse_tool_calls(response)
    assert calls == []


def test_build_tool_result_messages():
    """build_tool_result_messages 应生成 tool role 消息"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)

    call = ToolCall(id="call_1", name="web_search", arguments={"query": "x"})
    result = ToolResult.text("result text")

    messages = bridge.build_tool_result_messages([(call, result)])
    assert len(messages) >= 1
    roles = [m["role"] for m in messages]
    assert "tool" in roles


def test_adapt_response_string():
    """_adapt_response 应能处理字符串返回值"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)

    resp = bridge._adapt_response("hello world")
    assert isinstance(resp, LLMResponse)
    assert resp.text_part == "hello world"


def test_adapt_response_dict():
    """_adapt_response 应能处理 dict 返回值"""
    gateway = MagicMock()
    bridge = LLMFunctionBridge(gateway)

    resp = bridge._adapt_response({
        "content": "text content",
        "tool_calls": [{
            "id": "c1",
            "type": "function",
            "function": {"name": "test", "arguments": "{}"}
        }],
        "usage": {"total_tokens": 100},
    })
    assert isinstance(resp, LLMResponse)
    assert resp.text_part == "text content"
    assert len(resp.tool_calls) == 1
    assert resp.usage == {"total_tokens": 100}
    assert resp.has_tool_calls is True


def test_llm_response_no_tool_calls():
    """LLMResponse.has_tool_calls 在无工具调用时为 False"""
    resp = LLMResponse(text_part="hello", tool_calls=[])
    assert resp.has_tool_calls is False