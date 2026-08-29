"""短期记忆策略测试（spec §7.7）

- full: 全部消息
- sliding_window: 永远保留 system + 最近 window 条
- summary: Phase 1 退化为 sliding_window
- 未知策略降级为 full
- 空消息返回空列表
"""
from unittest.mock import MagicMock

from app.services.harness.memory_policy import apply_memory_policy


def _make_messages(n):
    """生成 n 条消息"""
    msgs = []
    for i in range(n):
        m = MagicMock()
        m.role = "user" if i % 2 == 0 else "assistant"
        m.content = f"msg {i}"
        msgs.append(m)
    return msgs


def test_full_policy_keeps_all():
    msgs = _make_messages(50)
    result = apply_memory_policy(msgs, policy="full", window=10)
    assert len(result) == 50


def test_sliding_window_keeps_recent():
    msgs = _make_messages(50)
    result = apply_memory_policy(msgs, policy="sliding_window", window=10)
    assert len(result) == 10
    # 应该保留最后 10 条
    assert result[0].content == "msg 40"
    assert result[-1].content == "msg 49"


def test_sliding_window_preserves_system_messages():
    """滑动窗口应永远保留 system 消息"""
    msgs = _make_messages(50)
    # 在开头插入 system 消息
    system_msg = MagicMock()
    system_msg.role = "system"
    system_msg.content = "system prompt"
    msgs.insert(0, system_msg)

    result = apply_memory_policy(msgs, policy="sliding_window", window=5)

    roles = [m.role for m in result]
    assert "system" in roles
    # system 应该在第一条
    assert result[0].role == "system"


def test_summary_policy_placeholder():
    """summary 策略：最近 window 条 + 摘要"""
    msgs = _make_messages(50)
    # Phase 1：summary 策略退化为 sliding_window（无 LLM 摘要）
    result = apply_memory_policy(msgs, policy="summary", window=10)
    assert len(result) <= 11  # window + 可能的摘要 system 消息


def test_unknown_policy_falls_back_to_full():
    """未知策略应降级为 full"""
    msgs = _make_messages(20)
    result = apply_memory_policy(msgs, policy="unknown_policy", window=10)
    assert len(result) == 20


def test_empty_messages_returns_empty():
    """空消息列表应返回空列表"""
    result = apply_memory_policy([], policy="sliding_window", window=10)
    assert result == []
