# OpenTelemetry 集成

Agent Harness 支持通过 OTLP 协议把 trace 推送到 Langfuse / Jaeger / Grafana 等外部 observability 后端。

## 启用

在 `.env` 中配置：

```bash
HTRACE_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-endpoint/v1/traces
OTEL_SERVICE_NAME=agent-harness  # 可选，默认 agent-harness
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <...>  # 可选，用于认证
```

## Langfuse 接入示例

```bash
HTRACE_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=https://langfuse.example.com/api/public/otel/v1/traces
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic cGst...:c2st...
```

## 前端 Trace Viewer

在 ProductManagerAgent 对话页面，点击「执行追踪」按钮可查看当前对话的 traces 和 step 详情。
数据来自本地 PostgreSQL（低延迟），不依赖外部 OTel 后端。

## 架构

- 双写：DB（agent_traces/trace_steps）+ OTel（OTLP endpoint）
- OTel 失败不影响 DB 写入（try/except 隔离）
- 未启用时零开销（lazy import）
