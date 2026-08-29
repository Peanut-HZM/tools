"""TraceRecorder OTel 双写单元测试"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.trace_recorder import TraceRecorder


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.count.return_value = 0
    return db


@pytest.fixture
def mock_tracer():
    tracer = MagicMock()
    span = MagicMock()
    tracer.start_span.return_value = span
    return tracer, span


AGENT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
CONV_ID = uuid.uuid4()


def test_start_trace_without_otel(mock_db):
    """OTel 未启用时，start_trace 正常写 DB，不创建 span"""
    with patch("app.services.harness.trace_recorder._get_tracer", return_value=None):
        recorder = TraceRecorder(db=mock_db)
        trace = recorder.start_trace(CONV_ID, AGENT_ID, USER_ID, "hello")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        assert not hasattr(trace, "_otel_span") or trace._otel_span is None


def test_start_trace_with_otel(mock_db, mock_tracer):
    """OTel 启用时，start_trace 同时创建 span"""
    tracer, span = mock_tracer
    with patch("app.services.harness.trace_recorder._get_tracer", return_value=tracer), \
         patch("app.services.harness.trace_recorder._register_trace_span") as mock_reg:
        recorder = TraceRecorder(db=mock_db)
        trace = recorder.start_trace(CONV_ID, AGENT_ID, USER_ID, "hello")

        tracer.start_span.assert_called_once()
        call_kwargs = tracer.start_span.call_args.kwargs
        assert call_kwargs["attributes"]["agent.id"] == str(AGENT_ID)
        assert call_kwargs["attributes"]["harness.trace_id"] == str(trace.id)
        assert trace._otel_span is span
        mock_reg.assert_called_once_with(trace.id, span)


def test_start_step_with_parent_span(mock_db, mock_tracer):
    """start_step 能找到 parent span 并创建子 span"""
    tracer, parent_span = mock_tracer
    trace_id = uuid.uuid4()

    with patch("app.services.harness.trace_recorder._get_tracer", return_value=tracer), \
         patch("app.services.harness.trace_recorder._find_trace_otel_span",
               return_value=parent_span):
        recorder = TraceRecorder(db=mock_db)
        step = recorder.start_step(trace_id, "llm_call")

        # 第二次调用 start_span（第一次是 start_trace）
        child_span = tracer.start_span.call_args.args[0] if tracer.start_span.call_args.args else tracer.start_span.return_value
        assert step._otel_span is not None


def test_end_step_records_attributes(mock_db, mock_tracer):
    """end_step 把 tokens/tool_name 等记到 span 上"""
    tracer, parent_span = mock_tracer
    child_span = MagicMock()

    with patch("app.services.harness.trace_recorder._get_tracer", return_value=tracer):
        recorder = TraceRecorder(db=mock_db)
        step = recorder.start_step(uuid.uuid4(), "tool_call")
        step._otel_span = child_span  # 模拟

        recorder.end_step(step, tokens=42, tool_name="search", llm_model=None)

        child_span.set_attribute.assert_any_call("harness.tokens", 42)
        child_span.set_attribute.assert_any_call("harness.tool_name", "search")
        child_span.end.assert_called_once()


def test_end_step_records_error_status(mock_db, mock_tracer):
    """end_step 传 error 时设置 ERROR status"""
    tracer, _ = mock_tracer
    child_span = MagicMock()

    with patch("app.services.harness.trace_recorder._get_tracer", return_value=tracer):
        recorder = TraceRecorder(db=mock_db)
        step = recorder.start_step(uuid.uuid4(), "llm_call")
        step._otel_span = child_span

        recorder.end_step(step, error="timeout")

        child_span.set_status.assert_called()
        child_span.record_exception.assert_called_once()
        child_span.end.assert_called_once()


def test_otel_failure_does_not_break_db(mock_db):
    """OTel 调用抛异常时，DB 写入仍然成功"""
    broken_tracer = MagicMock()
    broken_tracer.start_span.side_effect = RuntimeError("otel broken")

    with patch("app.services.harness.trace_recorder._get_tracer", return_value=broken_tracer):
        recorder = TraceRecorder(db=mock_db)
        # 不应抛异常
        trace = recorder.start_trace(CONV_ID, AGENT_ID, USER_ID, "hello")
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        assert trace is not None


def test_end_trace_ends_span(mock_db, mock_tracer):
    """end_trace 关闭 trace-level span 并 unregister"""
    tracer, span = mock_tracer
    trace_id = uuid.uuid4()

    with patch("app.services.harness.trace_recorder._get_tracer", return_value=tracer), \
         patch("app.services.harness.trace_recorder._unregister_trace_span") as mock_unreg:
        recorder = TraceRecorder(db=mock_db)
        trace = recorder.start_trace(CONV_ID, AGENT_ID, USER_ID, "hi")
        trace.id = trace_id
        trace._otel_span = span

        recorder.end_trace(trace, output_text="done", total_steps=3)

        span.set_attribute.assert_any_call("harness.total_steps", 3)
        span.end.assert_called()
        mock_unreg.assert_called_once_with(trace_id)
