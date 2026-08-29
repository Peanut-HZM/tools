"""TraceRecorder 测试（spec §7.11）

- start_trace: 创建 Trace 顶层记录
- start_step / end_step: 记录子步骤（llm_call / tool_call 等）
- end_trace: 计算 total_steps / total_tokens / total_duration_ms，设置 status
"""
from unittest.mock import MagicMock

import pytest

from app.services.harness.trace_recorder import TraceRecorder


def test_start_trace_creates_trace_record(test_db):
    """start_trace 应创建 Trace 记录"""
    recorder = TraceRecorder(test_db)

    trace = recorder.start_trace(
        conversation_id="00000000-0000-0000-0000-000000000001",
        agent_id="00000000-0000-0000-0000-000000000002",
        user_id="00000000-0000-0000-0000-000000000003",
        input_text="hello",
    )

    assert trace.id is not None
    assert trace.status in ("running", "success")
    assert trace.input_text == "hello"


def test_start_step_adds_trace_step(test_db):
    """start_step 应创建 TraceStep"""
    recorder = TraceRecorder(test_db)
    trace = recorder.start_trace(
        conversation_id="00000000-0000-0000-0000-000000000001",
        agent_id="00000000-0000-0000-0000-000000000002",
        user_id="00000000-0000-0000-0000-000000000003",
        input_text="hello",
    )

    step = recorder.start_step(trace.id, step_type="llm_call")
    assert step.step_type == "llm_call"

    recorder.end_step(step, tokens=100, duration_ms=200)
    assert step.tokens_used == 100
    assert step.duration_ms == 200


def test_end_trace_computes_totals(test_db):
    """end_trace 应计算总步数、总 token、总耗时"""
    recorder = TraceRecorder(test_db)
    trace = recorder.start_trace(
        conversation_id="00000000-0000-0000-0000-000000000001",
        agent_id="00000000-0000-0000-0000-000000000002",
        user_id="00000000-0000-0000-0000-000000000003",
        input_text="hello",
    )

    s1 = recorder.start_step(trace.id, "llm_call")
    recorder.end_step(s1, tokens=50, duration_ms=100)

    s2 = recorder.start_step(trace.id, "tool_call")
    recorder.end_step(s2, duration_ms=300)

    recorder.end_trace(trace, output_text="world", total_steps=2)

    assert trace.total_tokens == 50
    assert trace.total_duration_ms >= 400
    assert trace.output_text == "world"
    assert trace.status == "success"
