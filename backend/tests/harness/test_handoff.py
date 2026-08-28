"""Handoff 机制单元测试

覆盖：
- generate_handoff_tools: 每个目标生成一个工具
- generate_handoff_tools: 跳过 inactive 目标
- detect_handoff: 识别 handoff 调用
- detect_handoff: 没有 handoff 调用时返回 None
- detect_handoff: 校验 can_handoff_to 白名单
"""
import pytest
from unittest.mock import MagicMock
from app.services.harness.handoff import detect_handoff, generate_handoff_tools
from app.services.harness.tool_protocol import ToolCall


def test_generate_handoff_tools_creates_one_per_target():
    """应为每个可委派目标生成一个 handoff 工具"""
    agent = MagicMock()
    agent.can_handoff_to = ["writer", "code-assistant"]

    target_writer = MagicMock()
    target_writer.slug = "writer"
    target_writer.name = "Writer"
    target_writer.description = "Professional writer"
    target_writer.is_active = True

    target_code = MagicMock()
    target_code.slug = "code-assistant"
    target_code.name = "Code Assistant"
    target_code.description = "Code helper"
    target_code.is_active = True

    def load_by_slug(slug):
        return {"writer": target_writer, "code-assistant": target_code}.get(slug)

    tools = generate_handoff_tools(agent, load_agent_by_slug=load_by_slug)

    assert len(tools) == 2
    names = {t["name"] for t in tools}
    assert "handoff_to_writer" in names
    assert "handoff_to_code_assistant" in names


def test_generate_handoff_tools_skips_inactive_targets():
    """inactive target 应被跳过"""
    agent = MagicMock()
    agent.can_handoff_to = ["writer", "inactive"]

    target_writer = MagicMock()
    target_writer.slug = "writer"
    target_writer.is_active = True
    target_writer.name = "Writer"
    target_writer.description = "Writer desc"

    target_inactive = MagicMock()
    target_inactive.slug = "inactive"
    target_inactive.is_active = False

    def load_by_slug(slug):
        return {"writer": target_writer, "inactive": target_inactive}.get(slug)

    tools = generate_handoff_tools(agent, load_agent_by_slug=load_by_slug)

    assert len(tools) == 1
    assert tools[0]["name"] == "handoff_to_writer"


def test_detect_handoff_finds_handoff_call():
    """detect_handoff 应从 tool_calls 中识别 handoff"""
    agent = MagicMock()
    agent.can_handoff_to = ["writer"]

    target = MagicMock()
    target.slug = "writer"
    target.is_active = True

    calls = [
        ToolCall(id="call_1", name="handoff_to_writer", arguments={"reason": "writing task"})
    ]

    def load_by_slug(slug):
        return target if slug == "writer" else None

    result = detect_handoff(calls, agent, load_agent_by_slug=load_by_slug)
    assert result is not None
    assert result.slug == "writer"


def test_detect_handoff_returns_none_when_no_handoff():
    """没有 handoff 调用时返回 None"""
    agent = MagicMock()
    agent.can_handoff_to = ["writer"]

    calls = [
        ToolCall(id="call_1", name="web_search", arguments={"query": "x"})
    ]

    result = detect_handoff(calls, agent, load_agent_by_slug=lambda s: None)
    assert result is None


def test_detect_handoff_validates_can_handoff_to():
    """不在 can_handoff_to 列表的目标应被拒绝"""
    agent = MagicMock()
    agent.can_handoff_to = ["writer"]  # 不包含 "hacker"

    calls = [
        ToolCall(id="call_1", name="handoff_to_hacker", arguments={})
    ]

    # 即使 load 能找到，也不应返回
    hacker = MagicMock()
    hacker.slug = "hacker"
    hacker.is_active = True

    def load_by_slug(slug):
        return hacker if slug == "hacker" else None

    result = detect_handoff(calls, agent, load_agent_by_slug=load_by_slug)
    assert result is None
