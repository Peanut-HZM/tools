# Harness Phase 1 测试指南

本文档说明 Harness Phase 1 计划的完整测试方案：自动化测试套件 + 端到端手动验证步骤。

## 1. 后端自动化测试

### 1.1 一键运行

```bash
cd D:/CodeProjects/tools/.worktrees/agent-harness-phase1/backend
python -m pytest tests/harness/ -v --tb=short 2>&1 | tail -50
```

期望输出结尾：

```
===================== 247 passed, 2445 warnings in 20.23s =====================
```

> 247 warnings 全部来自 `datetime.utcnow()` 弃用提示与 Pydantic V2 ConfigDict 弃用提示，非测试失败。

### 1.2 测试文件清单

`backend/tests/harness/` 共 19 个测试文件 + 1 个 conftest.py：

| 文件 | 覆盖模块 | 测试数 |
|------|----------|--------|
| `test_tool_protocol.py` | ToolProtocol 接口契约 / ToolResult / ToolContext / Attachment | 12 |
| `test_tool_registry.py` | ToolRegistry 注册 / 鉴权 / schema 转换 | 3 |
| `test_events.py` | Event 工厂方法 / SSE 序列化 / timestamp / 非 ASCII | 10 |
| `test_llm_bridge.py` | LLMFunctionBridge：OpenAI / Claude 格式解析 / tool result message 构建 | 7 |
| `test_models.py` | ORM 模型：Tool / Trace（含 TraceStep 关系） | 2 |
| `test_session.py` | Session 消息追加 / persist / rollback / metadata_ 别名 | 9 |
| `test_memory_policy.py` | 短期记忆策略：full / sliding_window / summary / unknown 回退 | 6 |
| `test_guardrail.py` | Guardrail 入口（input / output 两阶段） | 测试位于 test_agent_runtime |
| `test_handoff.py` | Handoff 检测 / 生成 / 描述 sanitize / 长度截断 | 7 |
| `test_trace_recorder.py` | TraceRecorder：start_trace / start_step / end_trace / total 计算 | 3 |
| `test_agent_runtime.py` | AgentRuntime ReAct 主循环（端到端 mock） | 多个 |
| `test_db_query_tool.py` | DbQueryTool 元数据 / SQL 安全校验 | 多个 |
| `test_web_search_tool.py` | WebSearchTool HTML 解析 / sanitize / markdown 转义 | 17 |
| `test_http_tool.py` | HttpTool 模板渲染 / SSRF 防护 / 响应解析 | 32 |
| `test_admin_tools_api.py` | `/api/v1/admin/tools` CRUD + 鉴权 + mass assignment 防护 | 16 |
| `test_admin_agents_api.py` | `/api/v1/admin/agents/{id}/harness` harness 字段 + 工具绑定 + 统计 | 24 |
| `test_admin_traces_api.py` | `/api/v1/admin/traces` 列表 / 过滤 / 详情 / 403 | 15 |
| `test_chat_stream_integration.py` | `/conversations/{id}/chat/stream` SSE 端到端 | 10 |
| `test_task17.py` | lifespan 初始化 + history limit + error sanitization | 6 |

**总计：247 测试，全部通过。**

### 1.3 conftest 基础设施

`backend/tests/harness/conftest.py`：

- `@pytest.fixture test_db`：每个用例一个干净的 SQLite 内存库（`sqlite://`）
- 自动导入 `app.models.harness_models`（Tool / ToolBinding / SessionCheckpoint / AgentMemory / Trace / TraceStep）以及扩展后的 Agent / Conversation / Message
- `@compiles(JSONB, "sqlite")` 和 `@compiles(UUID, "sqlite")` 降级到 `JSON` 和 `CHAR(32)`，让 SQLite 能跑 PostgreSQL 专属类型

其他 conftest fixtures（位于 `backend/tests/conftest.py` 或每个测试文件内）：

- `client`：FastAPI TestClient
- `mock_services` / `mock_runtime` / `mock_db` / `fake_user`：覆盖 chat_stream 的依赖注入
- `registry`：干净的 ToolRegistry（用于 tool_registry 测试）

### 1.4 跑单个测试文件

```bash
cd backend
python -m pytest tests/harness/test_http_tool.py -v
python -m pytest tests/harness/test_admin_agents_api.py::test_create_tool_binding_success -v
```

### 1.5 跑非 harness 测试（不破坏 harness 范围）

```bash
cd backend
python -m pytest tests/ --ignore=tests/harness -q
```

## 2. 前端自动化测试

### 2.1 跑全部 vitest

```bash
cd D:/CodeProjects/tools/.worktrees/agent-harness-phase1/frontend
npm run test
```

> Phase 1 期间前端未新增 harness 专属测试。已有 vitest 套件（imageGenerationApi / DatabaseTool / HttpApiClient 等组件）保持原状。

## 3. 端到端手动测试

### 3.1 启动服务

```bash
cd D:/CodeProjects/tools/.worktrees/agent-harness-phase1
python dev-services.py restart
python dev-services.py status
```

- 后端：http://localhost:19092
- 前端：http://localhost:5178

### 3.2 浏览器登录

打开 http://localhost:5178，使用本地测试账号（`.env` 中配置）登录。

### 3.3 创建 Harness Agent

进入「管理后台」→「Agents」：

1. 找一个已有 agent（或新建一个），点击「编辑」
2. 切换到「Harness」标签
3. 配置以下字段（参考 `backend/app/schemas/harness_schemas.py`）：
   - `default_model_id`：选择一个 LLMModel 的 ID（必须先在 LLM Models 里创建）
   - `fallback_model_ids`：备选模型列表（可空）
   - `generation_params`：`{"temperature": 0.7, "max_tokens": 2048}`（白名单 key 校验）
   - `memory_short_term_policy`：`sliding_window`（或 `full` / `summary`）
   - `memory_short_term_window`：20（步数）
   - `max_steps_per_turn`：5
4. 保存 → 应该返回 200

**期望事件流**：

```
HTTP PATCH /api/v1/admin/agents/{id}/harness
  → DB upsert (Agent 表 harness_* 字段)
  → 返回 200 + 完整 Agent 配置
```

### 3.4 绑定 HTTP 工具

进入「管理后台」→「Tools」→「Create Tool」：

1. 选择 Type = `http`
2. 填写：
   - `name`：`weather_lookup`
   - `display_name`：`天气查询`
   - `description`：供 LLM function calling 使用
   - `parameters_schema`（OpenAI function calling 格式）：
     ```json
     {
       "type": "object",
       "properties": {
         "city": {"type": "string", "description": "城市名"}
       },
       "required": ["city"]
     }
     ```
   - `config`：
     ```json
     {
       "url": "https://api.example.com/weather?city={{args.city}}",
       "method": "GET",
       "headers": {"Authorization": "Bearer {{secrets.WEATHER_API_KEY}}"},
       "response_parser": {
         "result_path": "$.data.summary",
         "error_path": "$.error.message"
       },
       "timeout": 10
     }
     ```

**注意**：

- admin 端 `_validate_http_config` 会拒绝非 http/https 的 url（SSRF 防护前置）
- `secrets.WEATHER_API_KEY` 在执行时从环境变量读取（不在 admin UI 暴露）

3. 保存 → 201 Created

**绑定到 Agent**：

进入 Agents → 编辑 → Tool Bindings → Create Binding：

- `tool_id`：刚创建的 weather_lookup 的 ID
- `priority`：0
- `is_enabled`：true

### 3.5 对话测试

回到普通用户视角：

1. 新建一个对话
2. 选择「Harness Agent」作为对话 agent（如果当前 UI 不支持，调用 `POST /api/v1/agents/{id}/conversations`）
3. 发送消息：「北京今天天气怎么样？」

**期望事件流**（`POST /conversations/{id}/chat/stream` 返回 SSE）：

```
1. user_message 事件      （前端展示用户输入）
2. LLM 第一次调用         （携带 tools schemas）
3. text_delta / thinking  （LLM 思考中）
4. tool_call_start        （call_id=X name=weather_lookup args={"city":"北京"}）
5. tool_result            （调用 HttpTool.execute）
6. LLM 第二次调用         （带上 tool result）
7. text_delta ...         （最终回答）
8. done                   （final_text + usage）
```

### 3.6 验证预期事件流的代码路径

事件流的关键代码位置：

- **SSE 入口**：`backend/app/api/routes/chat_stream.py:39` `chat_stream()`
- **主循环**：`backend/app/services/harness/agent_runtime.py:52` `AgentRuntime.run()`
- **工具分发**：`backend/app/services/harness/tool_registry.py:103` `ToolRegistry.execute()`
- **事件工厂**：`backend/app/services/harness/events.py:24-101`（text_delta / tool_call_start / tool_result / done 等）
- **SSE 序列化**：`events.py:105` `Event.to_sse()`

**事件 type 全集**（`events.py` 工厂方法）：

| type | 触发时机 |
|------|----------|
| `turn_start` | 每个 turn 起始（当前由 chat_stream 注入，未直接由 AgentRuntime 发） |
| `text_delta` | LLM 流式输出 token |
| `text_complete` | LLM 完成一段文本 |
| `thinking_delta` | LLM 思考链（如 Claude） |
| `tool_call_start` | LLM 决定调用工具 |
| `tool_call_progress` | 工具执行中间进度（如图像生成） |
| `tool_result` | 工具返回结果 |
| `image_generated` | 图像类工具完成 |
| `handoff` | Agent 切换 |
| `guardrail_triggered` | Guardrail 拦截 |
| `memory_retrieved` | 长期记忆命中 |
| `error` | 错误（recoverable 标志区分） |
| `done` | 整个 turn 结束（含 final_text + usage） |
| `custom` | 自定义事件 |

> Phase 1 兼容策略：chat_stream 路由仅向前端暴露 `user_message` / `chunk` / `done` / `error` 四类外部 SSE 事件（保持原有前端兼容）；AgentRuntime 内部事件暂不直接透传，等前端 EventStreamClient 接入后再放开。

### 3.7 验证 Trace 记录

对话结束后：

1. 进入「管理后台」→「Traces」
2. 找到刚才的对话 trace，点击查看详情
3. 验证：
   - trace.status = `success`
   - trace.total_steps 至少 1（tool 调用会增加步数）
   - 每个 step 包含：step_type（`llm_call`）、tokens、llm_model
   - 工具调用会产生对应 step_type

**对应实现**：

- 路由：`backend/app/api/routes/admin_traces.py`
- 测试：`backend/tests/harness/test_admin_traces_api.py`（15 个用例）

### 3.8 验证 SSRF 防护

创建 HTTP 工具时，尝试以下 URL，应全部被 admin `_validate_http_config` 拒绝（返回 400）：

```
http://localhost:8080/admin
http://127.0.0.1/
http://10.0.0.5/internal
http://169.254.169.254/latest/meta-data/   # AWS 元数据
ftp://example.com/file
file:///etc/passwd
```

如果绕过 admin 校验直接调用（不可达，仅理论），`HttpTool._is_url_safe()` 会再次拦截（参考 `test_http_tool.py::test_http_tool_rejects_localhost` 等）。

### 3.9 验证 Guardrail

如果 admin 配置了 input guardrail（例如关键词 blocklist），尝试发送命中关键词的消息，期望：

- SSE 流立即收到 `error` + `done` 事件
- `final_text` 是兜底消息（`"抱歉，您的输入未通过安全校验。"`）
- 不会调用 LLM

**对应代码**：`backend/app/services/harness/guardrail.py` + `agent_runtime.py:57` `run_input_guardrails()`

### 3.10 验证 Handoff

如果配置了两个 agent：A 能 handoff 到 B：

1. 与 A 对话，请求 A 触发 handoff（具体触发词取决于 prompt）
2. SSE 流应出现 `handoff` 事件：`from_agent={A}, to_agent={B}, reason="handoff requested"`
3. 后续 LLM 调用使用 B 的 default_model / tools
4. session.agent 切换为 B（持久化到 DB）

**对应代码**：`backend/app/services/harness/handoff.py`

## 4. 测试覆盖矩阵

| 组件 | 单元测试 | 集成测试 | 手动 E2E |
|------|----------|----------|----------|
| ToolProtocol | `test_tool_protocol.py` | — | — |
| ToolRegistry | `test_tool_registry.py` | — | §3.5 |
| BuiltinTool (WebSearch) | `test_web_search_tool.py` | — | §3.5 |
| BuiltinTool (DbQuery) | `test_db_query_tool.py` | — | §3.5 |
| HttpTool | `test_http_tool.py` | — | §3.4, §3.5, §3.8 |
| AgentRuntime | `test_agent_runtime.py` | `test_chat_stream_integration.py` | §3.5 |
| Session | `test_session.py` | `test_chat_stream_integration.py` | §3.7 |
| TraceRecorder | `test_trace_recorder.py` | — | §3.7 |
| Guardrail | 间接（runtime） | `test_chat_stream_integration.py` | §3.9 |
| Handoff | `test_handoff.py` | — | §3.10 |
| Memory Policy | `test_memory_policy.py` | — | — |
| LLM Bridge | `test_llm_bridge.py` | `test_chat_stream_integration.py` | — |
| Events / SSE | `test_events.py` | `test_chat_stream_integration.py` | §3.5 |
| admin/tools API | `test_admin_tools_api.py` | — | §3.4 |
| admin/agents API | `test_admin_agents_api.py` | — | §3.3 |
| admin/traces API | `test_admin_traces_api.py` | — | §3.7 |
| lifespan / 启动 | `test_task17.py` | — | §3.1 |
