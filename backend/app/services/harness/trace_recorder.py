"""TraceRecorder — 自动记录 Trace + TraceStep

参考 spec §7.11
"""
import logging
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.models.harness_models import Trace, TraceStep
from app.services.harness.otel_init import (
    _get_tracer, _register_trace_span, _find_trace_otel_span, _unregister_trace_span,
)

logger = logging.getLogger(__name__)


def _to_uuid(value) -> uuid.UUID:
    """把字符串/UUID 统一转为 uuid.UUID 对象。"""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


class TraceRecorder:
    """自动记录 agent 执行追踪"""

    def __init__(self, db: DBSession):
        self.db = db
        self._tracer = _get_tracer()

    def start_trace(
        self,
        conversation_id,
        agent_id,
        user_id,
        input_text: str,
    ) -> Trace:
        """开始一个 trace（一次 turn）"""
        trace = Trace(
            conversation_id=_to_uuid(conversation_id),
            agent_id=_to_uuid(agent_id),
            user_id=_to_uuid(user_id),
            input_text=(input_text or "")[:5000],  # 截断
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(trace)
        self.db.commit()

        if self._tracer:
            try:
                otel_span = self._tracer.start_span(
                    name=f"agent.turn.{agent_id}",
                    attributes={
                        "agent.id": str(agent_id),
                        "user.id": str(user_id),
                        "conversation.id": str(conversation_id),
                        "harness.trace_id": str(trace.id),
                    },
                )
                trace._otel_span = otel_span
                _register_trace_span(trace.id, otel_span)
            except Exception as e:
                logger.warning("OTel start_trace 失败: %s", e)
        return trace

    def start_step(self, trace_id, step_type: str) -> TraceStep:
        """开始一个 step"""
        # 计算 step_index：当前 trace 已有的 step 数
        existing_count = (
            self.db.query(TraceStep).filter_by(trace_id=_to_uuid(trace_id)).count()
        )

        step = TraceStep(
            trace_id=_to_uuid(trace_id),
            step_index=existing_count,
            step_type=step_type,
        )
        self.db.add(step)
        self.db.commit()

        # 临时存开始时间，end_step 时用
        step._start_time = time.time()

        if self._tracer:
            try:
                parent = _find_trace_otel_span(_to_uuid(trace_id))
                if parent:
                    from opentelemetry import trace as otel_api
                    ctx = otel_api.set_span_in_context(parent)
                    otel_span = self._tracer.start_span(
                        name=f"step.{step_type}",
                        context=ctx,
                        attributes={
                            "harness.step_type": step_type,
                            "harness.step_index": step.step_index,
                        },
                    )
                    step._otel_span = otel_span
            except Exception as e:
                logger.warning("OTel start_step 失败: %s", e)
        return step

    def end_step(
        self,
        step: TraceStep,
        tokens: int = 0,
        duration_ms=None,
        tool_name: str = None,
        llm_model: str = None,
        input_summary: str = None,
        output_summary: str = None,
        error: str = None,
        metadata: dict = None,
    ):
        """结束一个 step"""
        if duration_ms is None:
            start_time = getattr(step, "_start_time", None)
            if start_time:
                duration_ms = int((time.time() - start_time) * 1000)
            else:
                duration_ms = 0

        step.tokens_used = tokens
        step.duration_ms = duration_ms
        step.tool_name = tool_name
        step.llm_model = llm_model
        step.input_summary = input_summary[:2000] if input_summary else None
        step.output_summary = output_summary[:2000] if output_summary else None
        step.metadata_ = metadata or {}

        if error:
            step.metadata_ = {**(step.metadata_ or {}), "error": error}

        self.db.commit()

        span = getattr(step, "_otel_span", None)
        if span:
            try:
                if tokens:
                    span.set_attribute("harness.tokens", tokens)
                if tool_name:
                    span.set_attribute("harness.tool_name", tool_name)
                if llm_model:
                    span.set_attribute("harness.llm_model", llm_model)
                if error:
                    from opentelemetry.trace import StatusCode
                    span.set_status(StatusCode.ERROR)
                    span.record_exception(Exception(error))
                span.end()
            except Exception as e:
                logger.warning("OTel end_step 失败: %s", e)

    def end_trace(
        self,
        trace: Trace,
        output_text: str = None,
        total_steps: int = 0,
        status: str = "success",
        error_message: str = None,
    ):
        """结束一个 trace"""
        # 计算总 tokens / 总 duration
        steps = self.db.query(TraceStep).filter_by(trace_id=trace.id).all()
        total_tokens = sum(s.tokens_used or 0 for s in steps)
        total_duration_ms = sum(s.duration_ms or 0 for s in steps)

        trace.output_text = output_text[:5000] if output_text else None
        trace.total_steps = total_steps
        trace.total_tokens = total_tokens
        trace.total_duration_ms = total_duration_ms
        trace.status = status
        trace.error_message = error_message
        trace.completed_at = datetime.utcnow()

        self.db.commit()

        span = getattr(trace, "_otel_span", None)
        if span:
            try:
                span.set_attribute("harness.total_steps", total_steps)
                span.end()
                _unregister_trace_span(trace.id)
            except Exception as e:
                logger.warning("OTel end_trace 失败: %s", e)

    def log_warning(self, message: str):
        """记录警告"""
        logger.warning(f"[TraceRecorder] {message}")

    def log_error(self, message: str):
        """记录错误"""
        logger.error(f"[TraceRecorder] {message}")
