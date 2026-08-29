# Agent Harness Phase 3 — Plan 1C: Langfuse / OpenTelemetry 集成设计

**日期**：2026-08-29
**状态**：已批准（待实现）
**参考**：`docs/superpowers/specs/2026-08-28-agent-harness-design.md` §7.11、§5.7

## 1. 目标

为 Agent Harness 添加 OpenTelemetry（OTel）导出能力 + 前端 Trace 查看器：

- **OTel 统一导出层**：通过 OTLP 协议把 trace 推送到 Langfuse / Jaeger / Grafana 等任意 OTel 后端
- **前端 Trace Viewer**：在对话页面展示 trace 列表 + step 详情表格（基于本地 DB 查询）
- **双写架构**：本地 PostgreSQL 写入保持现有行为，OTel 导出作为并行旁路

## 2. 核心决策

| 维度 | 决策 | 理由 |
|------|------|------|
| 核心目标 | OTel 导出 + 前端 viewer | 兼顾外部 observability 和本地查看 |
| 数据流 | 双写（DB + OTel） | 解耦：前端 viewer 低延迟查 DB，外部后端独立消费 OTLP |
| 配置粒度 | 全局环境变量 | 简单、运维驱动；per-agent 配置留给未来 |
| OTel 集成方式 | 官方 SDK 内联导出 | 厂商中立、时间精度好、Langfuse 原生支持 OTel 摄入 |
| 前端 Viewer 范围 | 列表 + step 表格 | 中等复杂度，足够日常调试 |
| 数据库迁移 | 无 | 复用 Phase 2 已存在的 `agent_traces` + `trace_steps` 表 |

## 3. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentRuntime (existing)                    │
│                           │                                     │
│                    ctx.trace_recorder                           │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            ▼
              ┌─────────────────────────────┐
              │   TraceRecorder (modified)  │
              │  ┌─────────┐  ┌──────────┐  │
              │  │ DB Write│  │ OTel Span│  │
              │  │ (existing)│  │ (new)    │  │
              │  └────┬────┘  └────┬─────┘  │
              └───────┼────────────┼─────────┘
                      ▼            ▼
            ┌──────────────┐  ┌────────────────┐
            │ PostgreSQL   │  │ OTel Collector │
            │ agent_traces │  │ / Langfuse     │
            │ trace_steps  │  │ / Jaeger       │
            └──────┬───────┘  └────────────────┘
                   ▼
            ┌──────────────┐
            │ REST API     │
            │ /api/v1/     │
            │ harness/     │
            │ traces       │
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │ Frontend     │
            │ Trace Viewer │
            │ (列表+step表)│
            └──────────────┘
```

### 数据流

1. `AgentRuntime` 调用 `TraceRecorder.start_trace / start_step / end_step / end_trace`（现有接口不变）
2. `TraceRecorder` **内联**：
   - 写 PostgreSQL（保持现有行为）
   - 创建 OTel Span（新增，仅当 OTel 启用时）
3. OTel SDK 的 `BatchSpanProcessor` 异步批量推送到配置的 OTLP endpoint
4. 前端通过 REST API 查询 PostgreSQL 中的 trace 数据（低延迟、无需外部依赖）
5. 外部 OTel 后端（Langfuse 等）独立消费 OTLP 数据

### 关键设计原则

- **OTel 可选**：未配置时行为与现有完全一致（零开销）
- **双写对称**：DB 和 OTel 看到相同的 trace/step 结构
- **前端独立**：前端 viewer 只查 DB，不依赖外部 OTel 后端可用性
- **生命周期安全**：FastAPI lifespan 管理 OTel SDK 的初始化 + shutdown
- **失败隔离**：OTel 调用全部 try/except，失败只 log warning，不影响 DB 写入

## 4. 后端组件设计

### 4.1 新模块：`app/services/harness/otel_init.py`

```python
"""OpenTelemetry 初始化（仅在启用时加载 OTel SDK）"""

_TRACER = None  # 模块级缓存

def init_otel() -> bool:
    """
    读取环境变量配置，初始化 OTel SDK。
    返回 True 表示启用成功，False 表示未启用/配置缺失。
    """
    import os
    if os.environ.get("HTRACE_ENABLED") != "1":
        return False
    
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.warning("HTRACE_ENABLED=1 但缺少 OTEL_EXPORTER_OTLP_ENDPOINT")
        return False
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        
        provider = TracerProvider()
        exporter_kwargs = {"endpoint": endpoint}
        headers = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS")
        if headers:
            exporter_kwargs["headers"] = _parse_headers(headers)
        
        provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(**exporter_kwargs),
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        ))
        trace.set_tracer_provider(provider)
        
        global _TRACER
        _TRACER = trace.get_tracer(
            os.environ.get("OTEL_SERVICE_NAME", "agent-harness")
        )
        return True
    except ImportError:
        logger.error("HTRACE_ENABLED=1 但 opentelemetry-* 未安装")
        return False
    except Exception as e:
        logger.error("OTel 初始化失败: %s", e)
        return False


def _get_tracer():
    """供 TraceRecorder 使用的模块级访问器"""
    return _TRACER


def shutdown_otel():
    """FastAPI lifespan shutdown，flush pending spans"""
    global _TRACER
    if _TRACER:
        try:
            provider = trace.get_tracer_provider()
            if hasattr(provider, "force_flush"):
                provider.force_flush(timeout_millis=5000)
        except Exception as e:
            logger.warning("OTel shutdown 失败: %s", e)
        _TRACER = None
```

### 4.2 `TraceRecorder` 改造

```python
class TraceRecorder:
    def __init__(self, db: DBSession):
        self.db = db
        self._tracer = _get_tracer()  # 从模块级缓存获取
    
    def start_trace(self, conversation_id, agent_id, user_id, input_text) -> Trace:
        # 现有 DB 写入（不变）
        trace = Trace(...)
        self.db.add(trace)
        self.db.commit()
        
        # 新增：创建 OTel span（仅当 self._tracer 非 None）
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
    
    def start_step(self, trace_id, step_type) -> TraceStep:
        step = TraceStep(...)
        self.db.add(step)
        self.db.commit()
        
        if self._tracer:
            try:
                parent = _find_trace_otel_span(trace_id)
                if parent:
                    ctx = trace.set_span_in_context(parent)
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
    
    def end_step(self, step, tokens=0, duration_ms=None, tool_name=None,
                 llm_model=None, input_summary=None, output_summary=None,
                 error=None, metadata=None):
        # 现有 DB 更新（不变）
        step.tokens = tokens
        step.duration_ms = duration_ms
        # ... 其余字段
        self.db.commit()
        
        # 新增：记录属性 + 关闭 span
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
                    span.set_status(StatusCode.ERROR)
                    span.record_exception(Exception(error))
                span.end()
            except Exception as e:
                logger.warning("OTel end_step 失败: %s", e)
    
    def end_trace(self, trace, output_text, total_steps):
        # 现有 DB 更新
        trace.output_text = output_text
        trace.total_steps = total_steps
        trace.status = "completed"
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
```

### 4.3 关键设计点

1. **`_get_tracer()` 模块级函数**：从 `otel_init.py` 暴露的缓存获取，避免每次构造 `TraceRecorder` 都查
2. **trace → otel_span 映射**：用模块级 `WeakValueDictionary` 或普通 dict 维护 `trace_id → otel_span`，让 step 能找到 parent
3. **`_otel_span` 临时属性**：存在 ORM 实例上，commit 后仍可用；ORM 实例销毁时 span 已 end 不影响
4. **OTel 失败隔离**：所有 OTel 调用包在 `try/except` 中，失败只 log warning，不影响 DB 写入
5. **依赖可选**：`opentelemetry-*` 加到 `requirements.txt` 但只在启用时 import

## 5. 配置

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `HTRACE_ENABLED` | 否 | `"0"` | `"1"` 启用 OTel 导出 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | 启用时必填 | — | OTLP HTTP endpoint URL |
| `OTEL_SERVICE_NAME` | 否 | `"agent-harness"` | OTel 服务名（在 Langfuse/Jaeger 中显示）|
| `OTEL_EXPORTER_OTLP_HEADERS` | 否 | — | 认证头，格式 `key1=val1,key2=val2`。Langfuse 用 `Authorization=Basic <base64(pk:sk)>` |

### FastAPI 启动/关闭

```python
# app/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 数据库 + 现有 startup
    _run_memory_backfill(...)
    
    # 2. OTel 初始化（新增）
    from app.services.harness.otel_init import init_otel
    otel_ok = init_otel()
    logger.info("OpenTelemetry export: %s", "enabled" if otel_ok else "disabled")
    
    yield
    
    # 3. Shutdown（新增）
    from app.services.harness.otel_init import shutdown_otel
    shutdown_otel()  # flush pending spans
```

### 依赖声明

```txt
# requirements.txt（新增）
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp>=1.20.0
```

加到主依赖，但只在 `HTRACE_ENABLED=1` 时 import。未启用时不产生运行开销。

### Langfuse 接入示例

```bash
# .env
HTRACE_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=https://langfuse.example.com/api/public/otel/v1/traces
OTEL_SERVICE_NAME=agent-harness-prod
# Langfuse 需要 Basic auth（pk-xxx:sk-xxx base64 编码）
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic cGstbGFuZ2Z1c2U6c2stbGFuZ2Z1c2U=
```

## 6. REST API（前端 Trace 查询）

### 端点

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/api/v1/harness/agents/{agent_id}/traces` | 列出 traces（分页，可按 conversation_id 过滤）|
| `GET` | `/api/v1/harness/agents/{agent_id}/traces/{trace_id}` | 获取单条 trace + 所有 steps |

### Response Schemas

```python
class TraceStepResponse(BaseModel):
    id: uuid.UUID
    step_index: int
    step_type: str             # "llm_call" | "tool_use" | "guardrail" | ...
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    tokens: int
    tool_name: Optional[str]
    llm_model: Optional[str]
    input_summary: Optional[str]
    output_summary: Optional[str]
    error: Optional[str]
    metadata: Optional[dict]

class TraceResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    agent_id: uuid.UUID
    user_id: uuid.UUID
    input_text: str
    output_text: Optional[str]
    status: str                # "running" | "completed" | "failed"
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    total_steps: int
    total_tokens: int
    steps: List[TraceStepResponse]  # 仅 detail 端点返回

class TraceListResponse(BaseModel):
    items: List[TraceResponse]  # 不含 steps
    total: int
    page: int
    page_size: int
```

### 列表端点查询参数

```
GET /api/v1/harness/agents/{agent_id}/traces
  ?conversation_id=xxx      # 可选：按对话过滤
  ?status=completed         # 可选：按状态过滤
  &page=1&page_size=20      # 分页，默认 20
```

### 实现文件

- **新建**：`backend/app/api/routes/harness_traces.py`
- **注册**：`backend/app/main.py` 加 `app.include_router(harness_traces.router)`
- **查询**：直接用 SQLAlchemy 查 `agent_traces` + `trace_steps`（不需要新的 service 层）

### Auth 策略

与现有 `harness_memories.py` 一致：
- 从 JWT 提取 `user_id`
- 查询时强制 `filter(user_id=user_id, agent_id=agent_id)`（租户隔离）
- Agent 不存在或不属于该用户 → 404

## 7. 前端 Trace Viewer

### 入口位置

在 `ProductManagerAgent.tsx` 对话页面加一个 toggle panel，与「长期记忆」并列。

### UI 布局

```
┌─────────────────────────────────────────┐
│ 对话区                                   │
├─────────────────────────────────────────┤
│ [长期记忆]  [执行追踪 ▼]                 │
├─────────────────────────────────────────┤
│  (展开时)                                │
│  ┌───────────────────────────────────┐  │
│  │ Trace 列表（当前对话）             │  │
│  │ ┌─────────────────────────────┐   │  │
│  │ │ 14:23:05 ✓ 1.2s  420 tok   │   │  │
│  │ │ 14:22:30 ✓ 0.8s  210 tok   │   │  │
│  │ │ 14:21:15 ✗ 0.3s    0 tok   │   │  │
│  │ └─────────────────────────────┘   │  │
│  │                                    │  │
│  │ 选中 trace 的 Steps（表格）        │  │
│  │ # │ 类型     │ 耗时  │ Tokens │ 模型 │
│  │ 0 │ llm_call │ 820ms │   380  │ gpt-4│
│  │ 1 │ tool_use │ 310ms │    40  │  -   │
│  │ 2 │ llm_call │ 120ms │   200  │ gpt-4│
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 组件结构

**新文件**：
- `frontend/src/components/Harness/TraceViewer.tsx` — 主容器
- `frontend/src/components/Harness/__tests__/TraceViewer.test.tsx` — 单元测试
- `frontend/src/api/harnessTracesApi.ts` — API 封装（用 `authedFetch`）

**修改**：
- `frontend/src/components/Tools/ProductManagerAgent.tsx` — 在「长期记忆」按钮旁加「执行追踪」toggle

### 关键行为

1. **Conversation 自动过滤**：打开 panel 时，用当前 `conversationId`（store 中）查 traces
2. **轮询刷新**：展开时每 5 秒拉一次列表（trace 可能在运行中），折叠时停止
3. **Trace 选中**：点击列表项 → 调用 detail API 拿 steps → 表格渲染
4. **状态图标**：`running`=旋转、`completed`=✓、`failed`=✗
5. **错误高亮**：step 有 error 字段时行背景变红
6. **空状态**：无 trace 时显示"本次对话还没有执行记录"

### API 调用示例

```typescript
// harnessTracesApi.ts
import { authedFetch } from '../utils/auth';

export async function listTraces(
  agentId: string,
  conversationId?: string,
  page = 1,
  pageSize = 20,
): Promise<TraceListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (conversationId) params.set('conversation_id', conversationId);
  
  const res = await authedFetch(
    `/api/v1/harness/agents/${agentId}/traces?${params}`
  );
  if (!res.ok) throw new Error(`Failed to list traces: ${res.status}`);
  return res.json();
}

export async function getTrace(
  agentId: string,
  traceId: string,
): Promise<TraceResponse> {
  const res = await authedFetch(
    `/api/v1/harness/agents/${agentId}/traces/${traceId}`
  );
  if (!res.ok) throw new Error(`Failed to get trace: ${res.status}`);
  return res.json();
}
```

### 类型定义

```typescript
// types/harness.ts（追加）
export interface TraceStep {
  id: string;
  step_index: number;
  step_type: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  tokens: number;
  tool_name: string | null;
  llm_model: string | null;
  input_summary: string | null;
  output_summary: string | null;
  error: string | null;
}

export interface Trace {
  id: string;
  conversation_id: string;
  agent_id: string;
  user_id: string;
  input_text: string;
  output_text: string | null;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  total_steps: number;
  total_tokens: number;
  steps?: TraceStep[];
}
```

## 8. 测试策略

### 后端测试（pytest）

| 测试文件 | 覆盖 |
|---------|------|
| `test_otel_init.py` | `init_otel()` 三种分支：未启用 / 缺 endpoint / 成功初始化；`shutdown_otel()` 幂等 |
| `test_trace_recorder_otel.py` | `TraceRecorder` 双写：OTel 禁用时不创建 span；启用时 span 创建/end 正确；end_step 记录 tokens/error 等属性；OTel 异常不影响 DB 写入 |
| `test_harness_traces_api.py` | 两个端点：列表分页、conversation 过滤、详情含 steps、租户隔离（404）、trace 不存在 404 |

### 前端测试（vitest）

| 测试文件 | 覆盖 |
|---------|------|
| `TraceViewer.test.tsx` | 渲染列表、点击展开 steps、空状态、loading 状态、错误状态、conversationId 变化时重新拉取 |

### Mock 策略

- **OTel SDK**：`patch("opentelemetry.trace.get_tracer")` 返回 mock tracer，断言 `start_span`/`set_attribute`/`end` 调用
- **DB**：复用 `MagicMock()` db fixture
- **API**：前端测试用 `vi.stubGlobal("fetch", ...)` mock `authedFetch`

### 集成测试（可选，env-gated）

```python
@pytest.mark.skipif(not os.environ.get("HTRACE_INTEGRATION"), ...)
async def test_otel_end_to_end_langfuse():
    """真实 OTel endpoint 端到端验证"""
    # 启动 TraceRecorder → 写 trace → flush → 通过 OTel API 反查验证
```

## 9. 数据库迁移

**不需要新迁移**。`agent_traces` + `trace_steps` 表已在 Phase 2 创建（master design §5.7 已落地）。OTel 集成只是在 `TraceRecorder` 中附加创建 OTel span，不修改表结构。

## 10. 任务拆解预估

按 `writing-plans` skill 格式，预计 **7 个任务**：

1. `otel_init.py` 模块 + 单元测试（init 三种分支）
2. `TraceRecorder` 改造（内联 OTel span）+ 单元测试
3. `harness_traces.py` REST API + 单元测试
4. 前端 API 层 + 类型定义
5. `TraceViewer.tsx` 组件 + 单元测试
6. `ProductManagerAgent.tsx` 集成（toggle panel）
7. 端到端验证（启动、写 trace、前端展示）+ 文档
