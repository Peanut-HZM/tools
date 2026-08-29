"""OpenTelemetry 初始化（仅在启用时加载 OTel SDK）"""
import logging
import os
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TRACER = None  # 模块级缓存
_TRACE_SPANS: Dict[uuid.UUID, Any] = {}  # trace_id -> OTel span


def init_otel() -> bool:
    """
    读取环境变量配置，初始化 OTel SDK。
    返回 True 表示启用成功，False 表示未启用/配置缺失。

    环境变量：
      HTRACE_ENABLED                  — "1" 启用
      OTEL_EXPORTER_OTLP_ENDPOINT     — OTLP HTTP endpoint（必填）
      OTEL_SERVICE_NAME               — 服务名（默认 agent-harness）
      OTEL_EXPORTER_OTLP_HEADERS      — 认证头 key1=val1,key2=val2
    """
    global _TRACER

    if os.environ.get("HTRACE_ENABLED") != "1":
        return False

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.warning("HTRACE_ENABLED=1 但缺少 OTEL_EXPORTER_OTLP_ENDPOINT，跳过 OTel")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider = TracerProvider()
        exporter_kwargs: Dict[str, Any] = {"endpoint": endpoint}

        headers = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS")
        if headers:
            exporter_kwargs["headers"] = _parse_headers(headers)

        provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(**exporter_kwargs),
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        ))
        trace.set_tracer_provider(provider)

        service_name = os.environ.get("OTEL_SERVICE_NAME", "agent-harness")
        _TRACER = trace.get_tracer(service_name)
        logger.info("OTel 初始化成功: service=%s endpoint=%s", service_name, endpoint)
        return True
    except ImportError:
        logger.error(
            "HTRACE_ENABLED=1 但 opentelemetry-* 未安装，"
            "请 pip install opentelemetry-sdk opentelemetry-exporter-otlp"
        )
        return False
    except Exception as e:
        logger.error("OTel 初始化失败: %s", e, exc_info=True)
        return False


def _parse_headers(raw: str) -> Dict[str, str]:
    """解析 key1=val1,key2=val2 格式的 headers"""
    result: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def _get_tracer():
    """供 TraceRecorder 使用的模块级访问器"""
    return _TRACER


def _register_trace_span(trace_id: uuid.UUID, span: Any) -> None:
    _TRACE_SPANS[trace_id] = span


def _find_trace_otel_span(trace_id: uuid.UUID):
    return _TRACE_SPANS.get(trace_id)


def _unregister_trace_span(trace_id: uuid.UUID) -> None:
    _TRACE_SPANS.pop(trace_id, None)


def shutdown_otel() -> None:
    """FastAPI lifespan shutdown，flush pending spans"""
    global _TRACER
    if _TRACER is None:
        return
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=5000)
        logger.info("OTel shutdown 完成")
    except Exception as e:
        logger.warning("OTel shutdown 失败: %s", e)
    finally:
        _TRACER = None
        _TRACE_SPANS.clear()
