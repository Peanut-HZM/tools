"""OTel 初始化模块单元测试"""
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def clean_env():
    """确保每个测试前后环境变量干净"""
    keys = ["HTRACE_ENABLED", "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_SERVICE_NAME", "OTEL_EXPORTER_OTLP_HEADERS"]
    saved = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ.pop(k, None)
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_init_disabled_by_default(clean_env):
    """未设置 HTRACE_ENABLED 时返回 False，不初始化"""
    from app.services.harness import otel_init
    # 重置模块状态
    otel_init._TRACER = None
    assert otel_init.init_otel() is False
    assert otel_init._get_tracer() is None


def test_init_enabled_but_missing_endpoint(clean_env):
    """HTRACE_ENABLED=1 但缺 endpoint 时返回 False"""
    os.environ["HTRACE_ENABLED"] = "1"
    from app.services.harness import otel_init
    otel_init._TRACER = None
    assert otel_init.init_otel() is False


def test_init_enabled_with_endpoint(clean_env):
    """完整配置时成功初始化（mock OTel SDK）"""
    os.environ["HTRACE_ENABLED"] = "1"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318/v1/traces"
    os.environ["OTEL_SERVICE_NAME"] = "test-service"

    mock_tracer = MagicMock()
    mock_provider = MagicMock()

    # 预加载子模块，确保 patch 能按点号路径解析到目标对象
    import opentelemetry.sdk.trace  # noqa: F401
    import opentelemetry.sdk.trace.export  # noqa: F401
    import opentelemetry.exporter.otlp.proto.http.trace_exporter  # noqa: F401

    with patch("opentelemetry.trace.set_tracer_provider") as mock_set, \
         patch("opentelemetry.trace.get_tracer", return_value=mock_tracer) as mock_get, \
         patch("opentelemetry.sdk.trace.TracerProvider", return_value=mock_provider), \
         patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"), \
         patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"):

        from app.services.harness import otel_init
        otel_init._TRACER = None
        result = otel_init.init_otel()

        assert result is True
        assert otel_init._get_tracer() is mock_tracer
        mock_set.assert_called_once_with(mock_provider)
        mock_get.assert_called_once_with("test-service")


def test_init_handles_import_error(clean_env):
    """OTel SDK 未安装时优雅降级"""
    os.environ["HTRACE_ENABLED"] = "1"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318/v1/traces"

    from app.services.harness import otel_init
    otel_init._TRACER = None

    # 临时把 opentelemetry 相关模块从 sys.modules 移除并禁止导入
    import sys
    saved = {k: sys.modules.pop(k) for k in list(sys.modules)
             if k.startswith("opentelemetry")}
    try:
        # 通过 meta_path finder 拦截 opentelemetry 导入
        import importlib.abc
        class BlockOTelFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path, target=None):
                if name.startswith("opentelemetry"):
                    raise ImportError("blocked for test")
                return None
        finder = BlockOTelFinder()
        sys.meta_path.insert(0, finder)
        try:
            result = otel_init.init_otel()
        finally:
            sys.meta_path.remove(finder)
    finally:
        sys.modules.update(saved)

    assert result is False
    assert otel_init._get_tracer() is None


def test_shutdown_idempotent(clean_env):
    """shutdown_otel() 未初始化时不抛异常"""
    from app.services.harness import otel_init
    otel_init._TRACER = None
    otel_init.shutdown_otel()  # 应无异常


def test_trace_span_mapping(clean_env):
    """_register/_find/_unregister 工作正常"""
    import uuid
    from app.services.harness import otel_init

    tid = uuid.uuid4()
    span = MagicMock()

    assert otel_init._find_trace_otel_span(tid) is None

    otel_init._register_trace_span(tid, span)
    assert otel_init._find_trace_otel_span(tid) is span

    otel_init._unregister_trace_span(tid)
    assert otel_init._find_trace_otel_span(tid) is None

    # 二次 unregister 不抛
    otel_init._unregister_trace_span(tid)
