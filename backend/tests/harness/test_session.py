"""Session 行为测试（spec §7.3）

- Session 包装 Conversation（DB 持久化） + 内存中的消息历史
- Phase 1：Message 在 harness 层用 role=user/assistant/tool/system 标识
- 测试用 MagicMock 替换 Message 构造器，避免依赖真实 DB
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.harness.llm_bridge import LLMResponse
from app.services.harness.session import Session
from app.services.harness.tool_protocol import ToolCall, ToolResult


@pytest.fixture(autouse=True)
def patch_message():
    """Mock Message 构造器，让 Session 在测试中无需真实 DB。

    session.py 在函数内延迟导入 Message（避免循环依赖），
    因此我们 patch `app.services.harness.session.Message`。
    实现侧会把 `role` 写成 Python 属性（不在 ORM 列上），
    所以 mock 需要接受任意 kwargs 并以属性形式保存。
    """

    def make_message(**kwargs):
        m = MagicMock()
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m

    fake_cls = MagicMock(side_effect=make_message)
    with patch("app.services.harness.session.Message", fake_cls):
        yield fake_cls


def _fake_session():
    """构造一个最小可用的 Session 用于单元测试"""
    conv = MagicMock()
    conv.id = "conv-1"
    conv.metadata = {}
    agent = MagicMock()
    return Session(conv, agent)


def test_session_append_user_message():
    """Session 应能追加用户消息"""
    session = _fake_session()
    msg = session.append_user_message("hello")

    assert msg.role == "user"
    assert msg.content == "hello"
    assert len(session.messages) == 1


def test_session_append_assistant_message():
    """Session 应能追加 assistant 消息"""
    session = _fake_session()
    response = LLMResponse(text_part="hi there", tool_calls=[])
    msg = session.append_assistant_message(response)

    assert msg.role == "assistant"
    assert msg.content == "hi there"


def test_session_append_assistant_message_with_tool_calls():
    """Session 应能保存 tool_calls 到 assistant 消息"""
    session = _fake_session()
    response = LLMResponse(
        text_part="",
        tool_calls=[ToolCall(id="c1", name="web_search", arguments={"query": "x"})],
    )
    msg = session.append_assistant_message(response)

    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1


def test_session_append_tool_message():
    """Session 应能追加 tool 消息"""
    session = _fake_session()
    call = ToolCall(id="call_1", name="web_search", arguments={"query": "x"})
    result = ToolResult.text("result text")

    msg = session.append_tool_message(call, result)

    assert msg.role == "tool"
    assert msg.tool_call_id == "call_1"
    assert msg.tool_name == "web_search"
    assert msg.content == "result text"


def test_session_append_system_message():
    """Session 应能追加 system 消息"""
    session = _fake_session()
    msg = session.append_system_message("you are a helper")

    assert msg.role == "system"
    assert msg.content == "you are a helper"


def test_session_persist_flushes_dirty_messages():
    """persist 应将所有 dirty messages 写入 DB"""
    session = _fake_session()
    session.append_user_message("hello")
    session.append_user_message("world")

    db = MagicMock()
    db.new = []  # simulate fresh session

    # Use sync persist for testability
    session.persist(db)

    assert db.add.call_count == 2
    db.commit.assert_called_once()
    assert len(session._dirty_messages) == 0
