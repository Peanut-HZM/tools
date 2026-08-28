# Agent Harness 架构设计

> 完整的、标准的 Agent Harness 架构，用于统一系统所有的 Agent 相关能力，并完整移除 Dify 工作流依赖。

| 项 | 值 |
|---|---|
| **状态** | 设计评审中 |
| **作者** | Claude（与用户协作设计） |
| **创建日期** | 2026-08-28 |
| **参考框架** | Claude Agent SDK、OpenAI Agents SDK、LangGraph、CrewAI、Mastra、Vercel AI SDK、MCP、Langfuse |
| **主参考** | Anthropic Claude Agent SDK |

---

## 目录

1. [概述](#1-概述)
2. [参考框架与对标](#2-参考框架与对标)
3. [设计哲学](#3-设计哲学)
4. [整体架构](#4-整体架构)
5. [数据模型](#5-数据模型)
6. [ToolProtocol 详细设计](#6-toolprotocol-详细设计)
7. [AgentRuntime 详细设计](#7-agentruntime-详细设计)
8. [API 设计](#8-api-设计)
9. [前端架构](#9-前端架构)
10. [迁移策略](#10-迁移策略)
11. [Phase 划分](#11-phase-划分)
12. [关键设计决策汇总](#12-关键设计决策汇总)

---

## 1. 概述

### 1.1 背景与动机

当前系统中 Agent 相关能力分散在多条独立脉络：

1. **LLM 对话层**（`agent_service.py` + `OrderedLLMGateway`）
   - 已脱离 Dify，走 LLMProvider + LLMModel + 分类兜底链
   - 产品经理 Agent 的对话底座

2. **图像生成层**（`services/image_gen/`）
   - `dify_client.py` + `dify_config_service.py` + `dify_backend.py`：走 Dify 工作流
   - `selfdev_backend.py`：自研路径
   - `agent_orchestrator.py`：按 operation 分发
   - DB 表 `image_gen_dify_config`（加密存储 API key、工作流 ID）

3. **Agent 管理层**（`api/routes/agents.py`）
   - Agent CRUD：名称、描述、system prompt、图标、分类、启用/禁用、默认
   - 本质是 **system prompt 模板** + 对话路由，不涉及工具调用或工作流

**问题**：
- Dify 是外部依赖，引入额外成本和限制
- Agent 概念被割裂（LLM 对话 / 图像生成 / Agent 管理各自为政）
- 没有统一的扩展机制（新增能力需要改多处代码）
- Agent 只是"配置"，不是"一等公民"

### 1.2 目标

设计一套**完整的、标准的 Harness 架构**，统一所有的 Agent 能力，达成：

- **完整性**：以 2026 年最主流的 Agent Harness 架构为标杆，覆盖所有核心要素
- **学习价值**：概念对应业界标准术语，便于学习和参考
- **实用性**：可作为实际产品使用，健壮可靠
- **可扩展**：清晰的扩展点，未来能支撑 MCP、Plugin、工作流等高级能力
- **彻底性**：完整移除 Dify 工作流依赖，所有能力自研

### 1.3 范围

**Agent 平台级别**的完整方案：
- Agent 一等公民（可配置实体：prompt + tools + memory + behavior）
- 可插拔工具协议（内置 / HTTP / MCP / Plugin 四类）
- 统一的 ReAct 运行时
- Handoff（Agent 间委派）
- Guardrails（输入/输出校验）
- 三层 Memory（短期/长期/程序性）
- Observability（Trace / Span）
- 流式事件协议（SSE + 结构化事件）
- Checkpoint（会话可恢复）
- 管理员 Agent 组装 UI
- 用户 Agent 工作台 UI

### 1.4 术语表

| 术语 | 定义 |
|------|------|
| **Agent** | 一等公民，包含 prompt、tools、model、memory、behavior 等完整配置的可执行实体 |
| **Tool** | Agent 可调用的能力单元，实现 ToolProtocol 接口 |
| **ToolProtocol** | 工具协议接口，所有工具（builtin/http/mcp/plugin）都实现此接口 |
| **Session** | 运行时会话上下文，包含消息历史和临时状态 |
| **Conversation** | 存储概念的会话，对应 DB 一行 |
| **ReAct** | Reasoning + Acting 循环，LLM 思考并调用工具的标准范式 |
| **Handoff** | Agent 之间的任务委派 |
| **Guardrail** | 输入/输出校验器，防止 LLM 跑偏或输出违规内容 |
| **Trace** | 一次 agent turn 的执行追踪记录 |
| **Checkpoint** | 会话状态的快照，用于恢复和回滚 |
| **Event** | Agent 执行过程中的结构化事件（text/tool_call/done 等） |
| **BuiltinTool** | 代码实现的内置工具 |
| **HttpTool** | 管理员配置的 HTTP 调用工具 |
| **McpTool** | MCP 协议工具（Phase 3） |
| **PluginTool** | 自定义插件工具（Phase 3） |

---

## 2. 参考框架与对标

### 2.1 对标框架

| 框架 | 借鉴的核心思想 |
|------|--------------|
| **Anthropic Claude Agent SDK** | Agent / Tool / Session 一等公民；消息流范式；简洁性（**主参考**） |
| **OpenAI Agents SDK** | Handoff 机制（Agent 间委派）；Guardrails；结构化输出 |
| **LangGraph** | StateGraph 概念；Checkpoint 会话持久化 |
| **CrewAI** | 多 Agent 协作模式；角色扮演；任务编排 |
| **Mastra (TS)** | Tool + Workflow + Memory 一体化 |
| **Vercel AI SDK** | 流式事件协议（text/tool_call/tool_result 的 SSE 范式） |
| **MCP（Model Context Protocol）** | 标准化工具协议；Resources/Prompts/Tools 三分法 |
| **Langfuse / Arize Phoenix** | Observability 范式；Trace / Span / Event 三层追踪 |

### 2.2 完整性要素（业界共识）

2026 年主流 Agent Harness 共有的核心要素：

1. **Agent 一等公民**：Agent 是产品概念，不只是配置
2. **Tool 协议**：可插拔的工具抽象
3. **Message / Event 流**：messages 数组 + 流式事件
4. **Memory 分层**：短期（context）/ 长期（向量）/ 程序性（skills）
5. **Handoff / Delegation**：Agent 之间可以委派任务
6. **Guardrails**：输入输出校验
7. **Tracing / Observability**：调试、审计、日志
8. **Streaming**：SSE / WebSocket 流式输出
9. **Persistent Sessions**：会话持久化
10. **Structured Output**：LLM 返回结构化数据
11. **Multi-modal**：文本 + 图片 + 文件 + 工具调用结果

### 2.3 主参考：Claude Agent SDK

选择 Claude Agent SDK 作为主参考的理由：

- 设计上最简洁、最清晰，最适合作为学习范本
- 概念模型最干净（Agent / Tool / Session / Message），没有过度抽象
- 跟本设计的"三层架构"完美契合
- 工业级质量（Anthropic 官方出品，大规模生产验证）

其他框架作为补充：
- OpenAI 补充 Handoff 和 Guardrails
- LangGraph 补充 Checkpoint
- MCP 补充工具协议标准化
- Vercel AI SDK 补充事件流协议
- Langfuse 补充 Observability

---

## 3. 设计哲学

贯穿整个设计的 5 条原则：

1. **业界标准术语**：每个核心概念对应业界标准术语（Agent / Tool / Session / Event / Memory / Guardrail / Trace），不发明新词，便于学习和对照。

2. **三层分离**：配置层（Agent Layer）/ 运行时（Runtime Layer）/ 工具协议（ToolProtocol Layer）严格分离，每层职责单一，便于理解和独立演进。

3. **扩展点有范本**：每个扩展点都有"协议 + 至少一个示例实现"，不只是抽象接口。例如 ToolProtocol 有 BuiltinTool 和 HttpTool 两个具体实现。

4. **关键决策可追溯**：每个重要设计决策都写明"参考了谁、为什么这么选"，便于后续维护和教学。

5. **代码即架构**：目录结构 = 架构图，读代码就是读设计。

---

## 4. 整体架构

### 4.1 三层分层

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1 — Agent Layer（配置层 / 管理员视角）              │
│                                                          │
│   Agent Entity  ─── 完整的"能力包"实体                      │
│     • identity: name, slug, description, icon, category  │
│     • prompt: system_prompt, welcome_message             │
│     • tools: [ToolBinding]  （挂载哪些工具、参数约束）       │
│     • model: ModelConfig    （默认模型 + 兜底链）           │
│     • memory: MemoryPolicy  （上下文策略）                  │
│     • behavior: Behavior    （步数上限、错误策略）          │
│     • handoff: HandoffConfig（可委派目标 + 指令）          │
│     • guardrails: GuardrailConfig（输入/输出校验）         │
│     • scope: is_active, is_default, visibility, owner    │
│                                                          │
│   ToolBinding  ─── Agent 和 Tool 之间的绑定关系             │
│     • tool_id, agent_id                                  │
│     • parameter_overrides (覆盖默认参数)                   │
│     • enabled, priority                                  │
│                                                          │
│   存储：PostgreSQL（agents / agent_tools / 相关表）         │
│   管理：后台 AgentManagement UI（CRUD + 工具挂载 + 预览）    │
└──────────────────────────────────────────────────────────┘
                            │ 实例化
                            ▼
┌──────────────────────────────────────────────────────────┐
│  Layer 2 — Runtime Layer（运行时 / 用户视角）               │
│                                                          │
│   AgentRuntime  ─── 单 Agent 的执行引擎（单例服务）          │
│     • run(session, user_message) → AsyncIterator[Event]  │
│     • 内部固定实现 ReAct 循环（不暴露为"策略"）              │
│     • 应用 Agent.behavior 约束（步数、错误兜底）            │
│     • 通过 Agent.memory 决定上下文窗口                     │
│     • 通过 Agent.model 选择模型（走现有 OrderedLLMGateway） │
│                                                          │
│   Session  ─── 一次对话的上下文容器                         │
│     • session_id, agent_id, user_id                      │
│     • messages[] (历史)                                  │
│     • scratch_state (运行时临时状态)                       │
│     • 持久化到 conversations / messages 表                 │
│                                                          │
│   Event  ─── 结构化事件流                                  │
│     • turn_start / text_delta / tool_call_start          │
│     • tool_result / image_generated / handoff            │
│     • guardrail_triggered / error / done                 │
│     • 通过 SSE 推给前端                                   │
│                                                          │
│   存储：conversations 表 + messages 表 + session_checkpoints│
│   入口：/api/v1/conversations/{id}/chat/stream (改造)     │
└──────────────────────────────────────────────────────────┘
                            │ 调用工具
                            ▼
┌──────────────────────────────────────────────────────────┐
│  Layer 3 — ToolProtocol Layer（工具协议 / 开发者视角）      │
│                                                          │
│   ToolProtocol（抽象接口）                                 │
│     • name / description / parameters_schema             │
│     • execute(args, ctx) → ToolResult                    │
│     • is_available(ctx) → bool                           │
│     • initialize() / shutdown() (生命周期)                │
│     • to_function_schema() (LLM 集成)                    │
│                                                          │
│   四种实现：                                              │
│     ① BuiltinTool  ── 代码级工具                          │
│        text_gen, image_gen, web_search, db_query, ...   │
│                                                          │
│     ② HttpTool  ── 管理员在后台配置的 HTTP 调用             │
│        URL, method, headers, body template, schema      │
│                                                          │
│     ③ McpTool  ── MCP Server 客户端（Phase 3）            │
│                                                          │
│     ④ PluginTool  ── 自定义 Plugin（Phase 3）             │
│                                                          │
│   ToolRegistry  ─── 工具注册表                             │
│     • 内置工具：代码硬注册                                 │
│     • HTTP 工具：DB 存储（tools 表）                      │
│     • 未来 MCP/Plugin：扩展注册表，不改接口                │
└──────────────────────────────────────────────────────────┘
```

### 4.2 关键数据流

```
用户在前端发消息
    │
    ▼
POST /api/v1/conversations/{id}/chat/stream
    │
    ▼
chat_stream router:
    1. 从 DB 加载 Agent（按 conversation.agent_id）
    2. 加载或创建 Session（messages + state）
    3. 构造 ToolContext（依赖注入）
    4. 实例化 AgentRuntime(agent, tool_registry, llm_bridge, session, ctx)
    5. 启动 SSE 流，逐事件推送
    │
    ▼
AgentRuntime.run(session, user_message):
    1. 输入 Guardrail
    2. 记录用户消息 + checkpoint
    3. 创建 Trace
    4. ReAct 循环（≤ max_steps_per_turn）:
       a. 应用 memory policy 构造 messages
       b. 注入长期记忆（可选）
       c. 加载当前 agent 的可用工具
       d. 调用 LLM
       e. 解析响应：
          - 无 tool_calls → 最终回复（过输出 guardrail），退出
          - 有 handoff 意图 → 切换 agent，继续循环
          - 有 tool_calls → 逐个执行，回到 (a)
    5. 持久化 session
    6. 完成 Trace
```

### 4.3 与现有系统的集成点

| 现有组件 | 处置 |
|---------|------|
| `agent_service.py`（LLM 服务） | **保留**，AgentRuntime 内部复用其中的 `OrderedLLMGateway` 调用 |
| `chat_stream.py`（SSE 路由） | **改造**：从"直接跑 LLM"变成"启动 AgentRuntime.run()" |
| `agents.py`（Agent CRUD） | **扩展**：增加工具绑定、模型配置、行为配置等字段 |
| `MessageService`（对话历史） | **保留**，作为 Session.messages 的持久化后端 |
| `LLMQuotaService`（配额） | **接入** AgentRuntime，每个 tool call / LLM call 扣配额 |
| `services/image_gen/*`（图像生成） | **Phase 2 重构**：作为 BuiltinTool("image_gen") 接入 |
| `dify_client.py` 等 Dify 全家桶 | **Phase 2 删除** |

---

## 5. 数据模型

### 5.1 Schema 关系总览

```
┌────────────┐     ┌───────────────┐     ┌────────────┐
│  agents    │────<│ agent_tools   │>────│  tools     │
│ (Agent)    │     │ (ToolBinding) │     │ (Tool)     │
└────────────┘     └───────────────┘     └────────────┘
       │                                          │
       │ 1:N                                      │ 被调用
       ▼                                          ▼
┌────────────┐     ┌───────────────┐     ┌────────────┐
│conversations│────<│  messages     │     │agent_traces│────< trace_steps
│ (Session)  │     │ (Message)     │     │  (Trace)   │
└────────────┘     └───────────────┘     └────────────┘
       │
       │ 来源
       ▼
┌────────────┐     ┌───────────────┐
│agent_      │     │session_       │
│memories    │     │checkpoints    │
│(LongMemory)│     │(Checkpoint)   │
└────────────┘     └───────────────┘
```

核心关系：
- Agent 1:N Conversation（一个 Agent 可以被多个用户/多次会话使用）
- Agent M:N Tool（通过 agent_tools 绑定，带绑定配置）
- Conversation 1:N Message（一次会话多条消息）
- Conversation 1:N Trace（一次会话可能产生多个 trace，对应多次 turn）
- Trace 1:N TraceStep（一个 trace 包含多个执行步骤）
- Agent 1:N AgentMemory（一个 agent 累积多条长期记忆）
- Conversation 1:N SessionCheckpoint（会话的多个 checkpoint）

### 5.2 Agent 表（Agent Layer 核心）

表名：`agents`

参考：Claude Agent SDK 的 Agent 概念 + OpenAI Agents SDK 的 Handoff/Guardrails

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| **Identity** | | | | |
| id | UUID | ✓ | uuid4 | 主键 |
| name | VARCHAR(100) | ✓ | | Agent 名称 |
| slug | VARCHAR(50) | ✓ | | URL 友好的唯一标识（如 `code-assistant`） |
| description | TEXT | | | Agent 描述 |
| icon | VARCHAR(50) | | | 图标类名 |
| icon_color | VARCHAR(100) | | | 图标颜色样式 |
| category | VARCHAR(50) | | | 分类标签 |
| **Prompt** | | | | |
| system_prompt | TEXT | ✓ | | 系统提示词 |
| welcome_message | TEXT | | | 首次进入会话时的欢迎消息 |
| **Model Config** | | | | |
| default_model_id | UUID FK → llm_models | | | 默认模型（空则走分类兜底链） |
| fallback_model_ids | JSONB | | `[]` | 兜底模型 ID 列表（按顺序尝试） |
| generation_params | JSONB | | `{}` | 生成参数（temperature、max_tokens 等） |
| **Memory Policy** | | | | |
| memory_short_term_policy | VARCHAR(20) | ✓ | `'sliding_window'` | `sliding_window` / `summary` / `full` |
| memory_short_term_window | INTEGER | | `20` | 滑动窗口大小（消息条数） |
| memory_long_term_enabled | BOOLEAN | ✓ | `false` | 是否启用长期记忆 |
| memory_long_term_config | JSONB | | `{}` | 长期记忆配置 |
| **Behavior** | | | | |
| max_steps_per_turn | INTEGER | ✓ | `20` | 单次 turn 最大执行步数 |
| tool_timeout_seconds | INTEGER | ✓ | `60` | 工具调用超时 |
| error_strategy | VARCHAR(20) | ✓ | `'fallback_message'` | `stop` / `retry` / `fallback_message` |
| max_retries | INTEGER | | `2` | retry 策略时的重试次数 |
| **Handoff** | | | | |
| can_handoff_to | JSONB | | `[]` | **可委派的目标 agent slug 列表** |
| handoff_instruction | TEXT | | | 委派指令（告诉 LLM 何时应该委派） |
| **Guardrails** | | | | |
| input_guardrails | JSONB | | `[]` | 输入校验器列表：`[{name, tool_id, config}]` |
| output_guardrails | JSONB | | `[]` | 输出校验器列表 |
| guardrail_on_violation | VARCHAR(20) | ✓ | `'block'` | `block` / `warn` / `retry` |
| **Scope** | | | | |
| is_active | BOOLEAN | ✓ | `true` | 是否启用 |
| is_default | BOOLEAN | ✓ | `false` | 是否为系统默认 Agent |
| visibility | VARCHAR(20) | ✓ | `'public'` | `public` / `private` / `shared` |
| owner_id | UUID FK → users | | | 私有 Agent 的所有者 |
| created_at | TIMESTAMP | ✓ | now | |
| updated_at | TIMESTAMP | ✓ | now | |

**唯一约束**：`UNIQUE(slug)`

**slug 命名规则**：
- ASCII 字母数字和 `-` 开头
- 非 ASCII 字符（中文等）用拼音/transliteration 转写
- 截断到 50 字符
- 冲突加 `-N` 后缀（如 `code-assistant-1`）

### 5.3 Tool 表（ToolProtocol 注册表）

表名：`tools`

参考：MCP 的 Tool/Resource/Prompt 思想（第一版只实现 Tool，但 schema 留好扩展位）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| **Identity** | | | | |
| id | UUID | ✓ | uuid4 | 主键 |
| name | VARCHAR(100) | ✓ | | 工具唯一标识（代码名，如 `image_gen`） |
| display_name | VARCHAR(100) | ✓ | | 展示名 |
| description | TEXT | ✓ | | 给 LLM 看的工具描述 |
| **Type & Config** | | | | |
| type | VARCHAR(20) | ✓ | | `builtin` / `http` / `mcp` / `plugin` |
| config | JSONB | ✓ | | 按 type 解析的配置 |
| **Schema** | | | | |
| parameters_schema | JSONB | ✓ | | JSON Schema（参数） |
| returns_schema | JSONB | | | 返回值 schema（可选） |
| **Availability** | | | | |
| is_available_condition | JSONB | | `{}` | 可用性条件 |
| rate_limit_per_minute | INTEGER | | | 限流 |
| **Meta** | | | | |
| metadata | JSONB | | `{}` | 扩展字段（MCP resource / prompt 等） |
| is_active | BOOLEAN | ✓ | `true` | |
| created_at / updated_at | TIMESTAMP | ✓ | now | |

**唯一约束**：`UNIQUE(name)`

**`config` 字段结构（按 type 解析）**：

```jsonc
// type = "builtin"
{
  "module": "app.services.harness.tools.image_gen",
  "class": "ImageGenTool",
  "init_args": {"oss_prefix": "image-gen/..."}
}

// type = "http"
{
  "url": "https://api.example.com/v1/action",
  "method": "POST",
  "headers": {"Authorization": "Bearer {{secrets.api_key}}"},
  "body_template": {"query": "{{args.query}}"},
  "response_parser": {
    "result_path": "$.data.result",
    "error_path": "$.error.message"
  },
  "auth": {"type": "api_key", "secret_key": "EXAMPLE_API_KEY"}
}

// type = "mcp" (Phase 3)
{
  "server_url": "http://localhost:3000",
  "transport": "sse"
}

// type = "plugin" (Phase 3)
{
  "plugin_id": "my_plugin",
  "entry_point": "MyTool"
}
```

### 5.4 ToolBinding 表（Agent ↔ Tool 绑定）

表名：`agent_tools`

参考：OpenAI Assistants 的 tool_resources 思想

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | 主键 |
| agent_id | UUID FK → agents | ✓ | | ON DELETE CASCADE |
| tool_id | UUID FK → tools | ✓ | | |
| parameter_overrides | JSONB | | `{}` | 覆盖工具的默认参数 |
| priority | INTEGER | ✓ | `0` | 工具排序 |
| is_enabled | BOOLEAN | ✓ | `true` | 是否启用 |
| created_at / updated_at | TIMESTAMP | ✓ | now | |

**唯一约束**：`UNIQUE(agent_id, tool_id)`

### 5.5 Conversation 表（Session 持久化）

表名：`conversations`（**已存在，扩展字段**）

参考：LangGraph Checkpoint

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | 主键 |
| user_id | UUID FK → users | ✓ | | |
| agent_id | UUID FK → agents | ✓ | | **新增**：本次会话的 Agent |
| title | VARCHAR(200) | | | |
| status | VARCHAR(20) | ✓ | `'active'` | `active` / `archived` / `completed` |
| last_message_at | TIMESTAMP | | | |
| metadata | JSONB | | `{}` | 会话级元数据 |
| created_at / updated_at | TIMESTAMP | ✓ | now | |

**新增索引**：`INDEX(user_id, agent_id, status)`

### 5.6 Message 表

表名：`messages`（**已存在，扩展字段**）

参考：Claude Agent SDK 的消息模型

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | |
| conversation_id | UUID FK → conversations | ✓ | | ON DELETE CASCADE |
| role | VARCHAR(20) | ✓ | | `system` / `user` / `assistant` / `tool` |
| content | TEXT | | | 文本内容 |
| tool_calls | JSONB | | | assistant 消息的工具调用列表 |
| tool_call_id | VARCHAR(100) | | | tool 消息关联的调用 ID |
| tool_name | VARCHAR(100) | | | tool 消息对应的工具名 |
| attachments | JSONB | | `[]` | 多模态附件 |
| metadata | JSONB | | `{}` | |
| created_at | TIMESTAMP | ✓ | now | |

**`tool_calls` 字段结构**：
```json
[
  {
    "id": "call_abc123",
    "name": "image_gen",
    "arguments": {"prompt": "...", "size": "1024x1024"}
  }
]
```

### 5.7 SessionCheckpoint 表

表名：`session_checkpoints`（**新增**）

参考：LangGraph Checkpoint

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | |
| conversation_id | UUID FK → conversations | ✓ | | ON DELETE CASCADE |
| step_index | INTEGER | ✓ | | 第几步 |
| phase | VARCHAR(20) | ✓ | | `after_user_message` / `before_tool` / `after_tool` |
| messages_ref | UUID | | | 最后一条 message id（轻量引用） |
| agent_state | JSONB | | `{}` | Agent 运行时状态 |
| created_at | TIMESTAMP | ✓ | now | |

**索引**：`INDEX(conversation_id, step_index)`

### 5.8 AgentMemory 表（长期记忆）

表名：`agent_memories`（**新增**）

参考：Mem0、MemGPT、Zep 等长期记忆方案

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | |
| agent_id | UUID FK → agents | ✓ | | ON DELETE CASCADE |
| user_id | UUID FK → users | | | 维度 |
| scope | VARCHAR(20) | ✓ | `'agent_user'` | `agent` / `user` / `agent_user` |
| key | VARCHAR(100) | ✓ | | 记忆标识 |
| content | TEXT | ✓ | | 记忆内容 |
| source_conversation_id | UUID FK | | | 来源会话 |
| source_message_id | UUID FK | | | 来源消息 |
| importance | FLOAT | ✓ | `0.5` | 重要性评分 |
| access_count | INTEGER | ✓ | `0` | 访问次数 |
| last_accessed_at | TIMESTAMP | | | |
| embedding | VECTOR(1536) | | | 向量（Phase 3，pgvector） |
| created_at / updated_at | TIMESTAMP | ✓ | now | |

**索引**：`INDEX(agent_id, user_id, scope)`

### 5.9 Trace 表（Observability）

表名：`agent_traces` + `trace_steps`（**新增**）

参考：Langfuse Trace / Span 模型 + OpenTelemetry

**agent_traces**（顶层 trace）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | |
| conversation_id | UUID FK | ✓ | | |
| agent_id | UUID FK | ✓ | | |
| user_id | UUID FK | ✓ | | |
| input_text | TEXT | ✓ | | 用户输入（截断） |
| output_text | TEXT | | | Agent 最终输出 |
| status | VARCHAR(20) | ✓ | | `success` / `error` / `timeout` / `guardrail_blocked` / `handoff` |
| total_steps | INTEGER | ✓ | `0` | |
| total_tokens | INTEGER | ✓ | `0` | |
| total_duration_ms | INTEGER | ✓ | `0` | |
| error_message | TEXT | | | |
| metadata | JSONB | | `{}` | |
| started_at | TIMESTAMP | ✓ | now | |
| completed_at | TIMESTAMP | | | |

**trace_steps**（子步骤）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| id | UUID | ✓ | uuid4 | |
| trace_id | UUID FK → agent_traces | ✓ | | ON DELETE CASCADE |
| step_index | INTEGER | ✓ | | |
| step_type | VARCHAR(20) | ✓ | | `llm_call` / `tool_call` / `handoff` / `guardrail` / `memory_read` / `memory_write` |
| tool_name | VARCHAR(100) | | | |
| llm_model | VARCHAR(100) | | | |
| tokens_used | INTEGER | | `0` | |
| duration_ms | INTEGER | ✓ | `0` | |
| input_summary | TEXT | | | 截断 |
| output_summary | TEXT | | | 截断 |
| metadata | JSONB | | `{}` | |
| created_at | TIMESTAMP | ✓ | now | |

**索引**：`INDEX(agent_id, started_at)`、`INDEX(user_id, started_at)`

### 5.10 关键设计决策

1. **JSONB 广泛使用**：`config`、`parameter_overrides`、`guardrails`、`metadata` 等字段用 JSONB，保持 schema 灵活性。

2. **slug 字段**：Agent 有 URL 友好的 slug，方便前端路由和分享。

3. **Handoff 是"声明式"的**：Agent 只声明"可以委派给谁（slug 列表）"和"委派条件"。

4. **Guardrail 复用 Tool 机制**：GuardrailFunction 是特殊的 Tool，通过 agent 表的 guardrails 字段引用 tool_id。

5. **长期记忆分 scope**：`agent`（共享）/ `user`（用户偏好）/ `agent_user`（特定交互记忆）。

6. **Trace 分两层**：`agent_traces`（顶层）+ `trace_steps`（子步骤）。

7. **Checkpoint 第一版轻量**：只记录 messages_ref + agent_state。

8. **向量嵌入预留**：`agent_memories.embedding` 字段预留 pgvector。

---

## 6. ToolProtocol 详细设计

### 6.1 ToolProtocol 接口

参考：Claude Agent SDK Tool + MCP Tool + LangChain BaseTool + OpenAI Agents SDK Tool

```python
class ToolProtocol(Protocol):
    """标准工具协议接口
    
    所有工具（builtin / http / mcp / plugin）都实现此接口。
    Runtime 通过此接口调用工具，不关心实现细节。
    """
    
    # ============================================================
    # 元数据（Identity）
    # ============================================================
    name: str                      # 工具唯一标识
    display_name: str              # 展示名
    description: str               # 给 LLM 看的描述
    parameters_schema: dict        # JSON Schema（参数）
    returns_schema: Optional[dict] # 返回值 schema（可选）
    
    # ============================================================
    # 生命周期
    # ============================================================
    async def initialize(self) -> None:
        """应用启动时调用一次（建立连接、预热等）"""
        ...
    
    async def shutdown(self) -> None:
        """应用关闭时调用（释放资源）"""
        ...
    
    # ============================================================
    # 核心执行
    # ============================================================
    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        """执行工具
        
        Args:
            args: LLM 生成的参数（已验证）
            ctx: 执行上下文
        
        Returns:
            ToolResult
        
        Raises:
            ToolExecutionError
        """
        ...
    
    async def execute_stream(self, args: dict, ctx: ToolContext) -> AsyncIterator[ToolEvent]:
        """流式执行（耗时工具发中间进度事件）
        
        默认实现：调用 execute() 后包装为单个 result 事件。
        """
        ...
    
    # ============================================================
    # 可用性
    # ============================================================
    def is_available(self, ctx: ToolContext) -> bool:
        """在当前上下文下是否可用"""
        ...
    
    # ============================================================
    # LLM 集成
    # ============================================================
    def to_function_schema(self) -> dict:
        """转换为 LLM function calling 的 schema"""
        ...
```

### 6.2 相关数据结构

**ToolResult**：
```python
@dataclass
class ToolResult:
    success: bool
    content: Any
    content_type: str = "text"    # "text" | "image" | "file" | "json" | "error"
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    attachments: List[Attachment] = field(default_factory=list)
    
    @classmethod
    def text(cls, text: str, **kw) -> "ToolResult": ...
    @classmethod
    def json(cls, data: Any, **kw) -> "ToolResult": ...
    @classmethod
    def image(cls, url: str, alt: str = "", **kw) -> "ToolResult": ...
    @classmethod
    def error(cls, message: str, **kw) -> "ToolResult": ...
    
    def to_llm_text(self) -> str: ...
```

**ToolContext**：
```python
@dataclass
class ToolContext:
    user_id: str
    conversation_id: str
    agent_id: str
    session: Session
    db: SQLAlchemySession
    oss_service: Optional[OssService]
    llm_gateway: Optional[OrderedLLMGateway]
    event_emitter: EventEmitter
    quota_service: Optional[LLMQuotaService]
    trace_recorder: TraceRecorder
    cancel_event: asyncio.Event
    tool_state: dict
```

**ToolCall**：
```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
```

**ToolEvent**：
```python
@dataclass
class ToolEvent:
    type: str          # "progress" | "result" | "error" | "log"
    payload: Any
    timestamp: float = field(default_factory=time.time)
```

### 6.3 四种工具实现

#### 实现 ① BuiltinTool（代码级内置工具）

```python
class BuiltinTool:
    """内置工具基类
    
    子类实现 execute() 即可。
    """
    
    def is_available(self, ctx: ToolContext) -> bool:
        return True
    
    async def execute_stream(self, args, ctx):
        result = await self.execute(args, ctx)
        yield ToolEvent(type="result", payload=result)
```

**示例：WebSearchTool**
```python
class WebSearchTool(BuiltinTool):
    name = "web_search"
    display_name = "网络搜索"
    description = "在网络上搜索信息"
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }
    
    async def execute(self, args, ctx):
        results = await search_api.search(args["query"], limit=args.get("max_results", 5))
        return ToolResult.text("\n".join(f"- {r.title}: {r.snippet}" for r in results))
```

#### 实现 ② HttpTool（管理员配置的 HTTP 调用）

**模板变量**：
- `{{args.xxx}}`：工具参数
- `{{ctx.user_id}}` / `{{ctx.conversation_id}}` / `{{ctx.agent_id}}`：上下文
- `{{secrets.XXX}}`：从 secrets 管理读取的密钥
- `{{timestamp}}`：当前时间戳

**安全考虑**：
- URL 白名单（避免 SSRF）
- 模板变量沙箱（避免注入）
- 鉴权密钥走 secrets 管理
- 响应大小限制

#### 实现 ③ McpTool（Phase 3）

连接外部 MCP Server，支持 stdio / SSE / Streamable HTTP 三种传输，自动发现工具。

#### 实现 ④ PluginTool（Phase 3）

Python 插件接口，运行时加载，可选沙箱隔离。

### 6.4 ToolRegistry

```python
class ToolRegistry:
    """工具注册表（应用级单例）
    
    职责：
    1. 管理所有工具实例
    2. 按 agent 的 tool_bindings 选择工具
    3. 生成 LLM function schema
    4. 分发工具调用
    5. 管理工具生命周期
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._builtin: dict[str, BuiltinTool] = {}
        self._http_cache: dict[str, HttpTool] = {}
    
    def register_builtin(self, tool: BuiltinTool) -> None: ...
    
    async def get_tools_for_agent(
        self, agent_id: str, ctx: ToolContext
    ) -> List[ToolProtocol]:
        """获取 agent 在当前上下文下可用的工具列表"""
        ...
    
    def to_function_schemas(self, tools: List[ToolProtocol]) -> List[dict]: ...
    
    async def execute(self, call: ToolCall, ctx: ToolContext) -> ToolResult: ...
    
    async def execute_stream(self, call: ToolCall, ctx: ToolContext): ...
    
    async def initialize_all(self) -> None: ...
    async def shutdown_all(self) -> None: ...
    async def refresh_http_tools(self) -> None: ...
```

### 6.5 LLMFunctionBridge

```python
class LLMFunctionBridge:
    """工具与 LLM 的桥接
    
    屏蔽 OpenAI / Claude 等 provider 的工具调用格式差异。
    """
    
    def __init__(self, gateway: OrderedLLMGateway): ...
    
    def build_request(self, messages: List[dict], tools: List[ToolProtocol]) -> dict: ...
    
    def parse_tool_calls(self, provider_response: dict) -> List[ToolCall]: ...
    
    def build_tool_result_messages(
        self, calls_and_results: List[Tuple[ToolCall, ToolResult]]
    ) -> List[dict]: ...
```

### 6.6 第一版内置工具清单

| 工具名 | 类型 | 说明 | Phase |
|-------|------|------|------|
| `image_gen` | BuiltinTool | 图像生成（替代 Dify） | Phase 2 |
| `web_search` | BuiltinTool | 网络搜索 | Phase 1 |
| `db_query` | BuiltinTool | 数据库只读查询 | Phase 1 |
| `memory_read` | BuiltinTool | 读取长期记忆 | Phase 2 |
| `memory_write` | BuiltinTool | 写入长期记忆 | Phase 2 |
| `handoff` | **Runtime 内部** | Agent 委派（不暴露给 LLM 显式调用） | Phase 1 |
| `guardrail_check` | **Runtime 内部** | Guardrail 检查（自动触发） | Phase 1 |

**Phase 3 扩展候选**：
- `file_read` / `file_write`
- `code_execute`（沙箱）
- `email_send` / `notification_send`
- MCP 工具（任意 MCP server 暴露的工具自动接入）
- Plugin 工具

### 6.7 关键设计决策

1. **ToolProtocol 是 Python `Protocol`**：结构化子类型，不要求继承基类。
2. **execute_stream 默认 = 包装 execute 为单事件**：简单工具不必关心流式。
3. **ToolResult 多模态**：content_type 支持 text/image/file/json/error。
4. **ToolContext 是依赖注入载体**：工具通过 ctx 访问运行时依赖。
5. **ToolRegistry 单例**：应用级共享，DB 工具变更时刷新缓存。
6. **LLMFunctionBridge 屏蔽 provider 差异**。
7. **handoff / guardrail 不作为显式工具暴露给 LLM**：由 Runtime 内部触发。
8. **HttpTool 安全四道防线**：URL 白名单、模板沙箱、密钥 secrets 管理、响应大小限制。

---

## 7. AgentRuntime 详细设计

### 7.1 职责边界

**是什么**：
- 一次 turn 的执行引擎
- 把 Agent 配置"激活"为实际的对话行为
- 驱动 ReAct 循环
- 编排所有横切关注（memory、guardrail、handoff、checkpoint、trace）

**不是什么**：
- 不是工具执行器（ToolRegistry）
- 不是 LLM 调用器（OrderedLLMGateway）
- 不是消息持久化器（MessageService）
- 不是流式推送器（SSE 层）

**设计原则**：Runtime 是**编排者**，不是**执行者**。

### 7.2 核心循环（ReAct）

参考：Claude Agent SDK 的 ReAct 实现 + OpenAI Agents SDK 的 Runner loop

```python
async def run(self, user_message: str) -> AsyncIterator[Event]:
    """主循环"""
    
    # ========== 1. 输入 Guardrail ==========
    try:
        gr_result = await self._run_input_guardrails(user_message)
        if gr_result.blocked:
            yield Event.guardrail_triggered(gr_result)
            yield Event.done(self._fallback_message("input_blocked"))
            return
    except Exception as e:
        # Guardrail 异常降级处理，不阻塞主流程
        self.ctx.trace_recorder.log_warning(f"input guardrail failed: {e}")
    
    # ========== 2. 记录用户消息 ==========
    self.session.append_user_message(user_message)
    await self._write_checkpoint(phase="after_user_message")
    
    # ========== 3. 创建 Trace ==========
    trace = self.ctx.trace_recorder.start_trace(...)
    
    final_text = None
    
    try:
        # ========== 4. ReAct 主循环 ==========
        for step_index in range(self._current_agent.max_steps_per_turn):
            self._step_count = step_index + 1
            
            if self.ctx.cancel_event.is_set():
                yield Event.error("cancelled", recoverable=False)
                break
            
            # 4a. 构造 messages（应用短期记忆策略）
            messages = self._apply_memory_policy(self.session.messages)
            
            # 4b. 注入长期记忆上下文
            if self._current_agent.memory_long_term_enabled:
                mem_ctx = await self._retrieve_long_term_memory(messages)
                if mem_ctx:
                    messages = self._inject_memory_context(messages, mem_ctx)
                    yield Event.custom("memory_retrieved", {"facts": mem_ctx})
            
            # 4c. 加载可用工具
            tools = await self.tool_registry.get_tools_for_agent(
                self._current_agent.id, self.ctx
            )
            schemas = self.llm_bridge.to_function_schemas(tools)
            
            # 4d. 调用 LLM
            trace_step = self.ctx.trace_recorder.start_step(trace.id, step_type="llm_call")
            try:
                llm_response = await self.llm_bridge.gateway.generate(
                    messages=messages,
                    tools=schemas,
                    model=self._current_agent.default_model_id,
                    fallback_models=self._current_agent.fallback_model_ids,
                    generation_params=self._current_agent.generation_params,
                    stream=True,
                )
            except Exception as e:
                self.ctx.trace_recorder.end_step(trace_step, error=str(e))
                yield Event.error(f"LLM 调用失败: {e}")
                if self._current_agent.error_strategy == "retry":
                    continue
                yield Event.done(self._fallback_message("llm_error"))
                return
            self.ctx.trace_recorder.end_step(trace_step, tokens=llm_response.usage)
            
            # 4e. 解析响应
            if llm_response.text_part:
                yield Event.text_delta(llm_response.text_part)
            if llm_response.thinking_part:
                yield Event.thinking_delta(llm_response.thinking_part)
            
            # 检查 handoff
            handoff_target = self._detect_handoff(llm_response)
            if handoff_target:
                yield from await self._execute_handoff(handoff_target)
                continue
            
            # 检查 tool_calls
            tool_calls = self.llm_bridge.parse_tool_calls(llm_response)
            
            if not tool_calls:
                # ---- 最终回复 ----
                final_text = llm_response.text_part or ""
                
                try:
                    gr_result = await self._run_output_guardrails(final_text)
                    if gr_result.blocked:
                        yield Event.guardrail_triggered(gr_result)
                        final_text = self._fallback_message("output_blocked")
                except Exception as e:
                    self.ctx.trace_recorder.log_warning(f"output guardrail failed: {e}")
                
                yield Event.text_complete(final_text)
                yield Event.done(final_text)
                self.session.append_assistant_message(llm_response)
                break
            else:
                # ---- 工具调用 ----
                self.session.append_assistant_message(llm_response)
                
                for call in tool_calls:
                    yield Event.tool_call_start(call)
                    await self._write_checkpoint(phase="before_tool")
                    
                    tool_result = None
                    async for event in self.tool_registry.execute_stream(call, self.ctx):
                        if event.type == "progress":
                            yield Event.tool_call_progress(call.id, event.payload)
                        elif event.type == "result":
                            tool_result = event.payload
                    
                    if tool_result is None:
                        tool_result = await self.tool_registry.execute(call, self.ctx)
                    
                    yield Event.tool_result(call, tool_result)
                    self.session.append_tool_message(call, tool_result)
                    
                    if tool_result.content_type == "image":
                        yield Event.image_generated(
                            [a.url for a in tool_result.attachments],
                            metadata=tool_result.metadata,
                        )
                    
                    if self._current_agent.memory_long_term_enabled:
                        await self._maybe_write_long_term_memory(call, tool_result)
                    
                    await self._write_checkpoint(phase="after_tool")
        
        else:
            yield Event.error(
                f"达到最大步数限制 ({self._current_agent.max_steps_per_turn})",
                recoverable=True,
            )
            yield Event.done(self._fallback_message("max_steps"))
    
    except asyncio.CancelledError:
        yield Event.error("cancelled", recoverable=False)
        raise
    except Exception as e:
        logger.error("AgentRuntime 未预期异常", exc_info=True)
        self.ctx.trace_recorder.log_error(str(e))
        yield Event.error(f"内部错误: {e}")
        yield Event.done(self._fallback_message("internal_error"))
    finally:
        await self.session.persist()
        self.ctx.trace_recorder.end_trace(trace, output_text=final_text, total_steps=self._step_count)
```

### 7.3 Session 管理

```python
class Session:
    """运行时会话上下文"""
    
    def __init__(self, conversation: Conversation, agent: Agent):
        self.conversation = conversation
        self.agent = agent
        self.messages: List[Message] = []
        self.scratch_state: dict = {}
        self.metadata: dict = conversation.metadata or {}
    
    async def load(self):
        self.messages = await self._load_messages(self.conversation.id)
    
    def append_user_message(self, content: str) -> Message: ...
    def append_assistant_message(self, response: LLMResponse) -> Message: ...
    def append_tool_message(self, call: ToolCall, result: ToolResult) -> Message: ...
    
    async def persist(self):
        await self._save_new_messages(self.messages)
    
    async def write_checkpoint(self, step_index: int, phase: str):
        cp = Checkpoint(
            conversation_id=self.conversation.id,
            step_index=step_index,
            phase=phase,
            messages_ref=self.messages[-1].id if self.messages else None,
            agent_state=self.scratch_state.copy(),
        )
        await save_checkpoint(cp)
```

### 7.4 Event 流协议

参考：Vercel AI SDK + Claude Agent SDK + OpenAI Realtime API

**完整事件类型清单**：

| 事件类型 | 触发时机 | 负载 |
|---------|---------|------|
| `turn_start` | turn 开始 | `{conversation_id, agent}` |
| `text_delta` | LLM 流式输出文本片段 | `{text}` |
| `text_complete` | LLM 文本完成 | `{text}` |
| `thinking_delta` | LLM 思考过程（CoT） | `{text}` |
| `tool_call_start` | 工具调用开始 | `{id, name, arguments}` |
| `tool_call_progress` | 工具执行中间进度 | `{id, progress}` |
| `tool_result` | 工具执行完成 | `{id, name, success, content_type, content, attachments, error}` |
| `image_generated` | 图像生成完成 | `{urls, metadata}` |
| `handoff` | Agent 委派 | `{from_agent, to_agent, reason}` |
| `guardrail_triggered` | Guardrail 触发 | `{guardrail_name, reason, stage}` |
| `memory_retrieved` | 长期记忆检索 | `{facts}` |
| `error` | 错误 | `{message, recoverable}` |
| `done` | 完成 | `{final_text, usage?}` |
| `custom` | 工具自定义事件 | `{name, ...}` |

**SSE 协议**：
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no

event: turn_start
data: {"conversation_id": "uuid", "agent": {"id": "uuid", "name": "Code Assistant"}}

event: text_delta
data: {"text": "我来", "timestamp": 1724123456.789}

event: tool_call_start
data: {"id": "call_abc", "name": "image_gen", "arguments": {...}}

event: tool_result
data: {"id": "call_abc", "name": "image_gen", "success": true, ...}

event: done
data: {"final_text": "...", "usage": {"prompt_tokens": 120, "completion_tokens": 340}}
```

**前端渲染契约**：
- **必须处理**：`text_delta` / `tool_call_start` / `tool_result` / `done` / `error`
- **可选处理**：`thinking_delta`（可折叠）、`handoff`（可特殊提示）、`custom`
- **断线重连**：前端用 `Last-Event-ID` 头支持断线续传

### 7.5 Handoff 机制

参考：OpenAI Agents SDK 的 Handoff

**设计**：
- 触发方式：Runtime 内部为每个可委派目标生成 `handoff_to_<slug>` 工具
- LLM 调用这些工具即触发委派
- Runtime 切换 `self._current_agent` 为目标 agent
- 发 `Event.handoff` 通知前端
- Session 保持不变

```python
def _get_handoff_tools(self) -> List[dict]:
    """为每个可委派目标生成一个 handoff 工具"""
    tools = []
    for target_slug in self._current_agent.can_handoff_to:
        target = load_agent_by_slug(target_slug)
        tools.append({
            "name": f"handoff_to_{target.slug.replace('-', '_')}",
            "description": f"将任务委派给 {target.name}：{target.description}",
            "parameters": {...}
        })
    return tools

def _detect_handoff(self, llm_response) -> Optional[Agent]:
    """检测 LLM 是否调用了 handoff 工具"""
    for call in self.llm_bridge.parse_tool_calls(llm_response):
        if call.name.startswith("handoff_to_"):
            target_slug = call.name[len("handoff_to_"):].replace("_", "-")
            return self._load_agent_by_slug(target_slug)
    return None
```

**关键约束**：
- 只能在 `can_handoff_to` 列表里的 agent 中委派
- handoff 深度限制（默认 max 3 次，避免无限循环）
- handoff 历史可审计（记录在 session.metadata.handoffs）

### 7.6 Guardrail 集成

参考：OpenAI Agents SDK Guardrails + NeMo Guardrails

**集成点**：
```
用户消息 → [输入 Guardrail] → 通过 → Runtime 处理 → [输出 Guardrail] → 返回
                 ↓ 阻断                              ↓ 阻断
              返回拒绝消息                          返回兜底消息
```

**`guardrail_on_violation` 策略**：
- `block`：阻断，返回拒绝消息
- `warn`：记录日志 + 通知前端（发 `guardrail_triggered` 事件），但不阻断
- `retry`：重试（例如让 LLM 重新生成）

### 7.7 Memory 集成

**短期记忆策略**：
- `full`：保留所有消息
- `sliding_window`：保留最近 N 条（system 消息永远保留）
- `summary`：保留最近 N 条 + 更早消息的 LLM 摘要
  - 摘要存在 `session.scratch_state["memory_summary"]`
  - 首次生成或每累积 M 条新消息后异步刷新
  - 摘要 prompt：把更早的消息总结为关键点

**长期记忆**：
- **读取**：每次 turn 开始，基于最近一条用户消息检索相关长期记忆，注入到 system prompt
  - Phase 1：关键词匹配（SQL LIKE）
  - Phase 3：向量检索（pgvector）
- **写入**：Phase 1 基于规则触发：
  - 用户消息包含"记住"/"remember"/"请记下"等关键词
  - 特定工具（如 `memory_write`）被调用
  - Phase 3：LLM 自动判断是否写入

### 7.8 Checkpoint 机制

参考：LangGraph Checkpoint

**Phase 1 轻量版**：
- 时机：`after_user_message` / `before_tool` / `after_tool`
- 内容：messages_ref（最后一条消息 ID）+ scratch_state 快照
- Phase 3：加分支、回滚、时间旅行

### 7.9 错误处理和降级

**Agent.behavior.error_strategy**：
- `stop`：遇到错误立即停止，返回错误消息
- `retry`：重试 max_retries 次（指数退避）
- `fallback_message`：返回兜底消息

**兜底消息模板**：
```python
def _fallback_message(self, reason: str) -> str:
    messages = {
        "input_blocked": "抱歉，您的输入未通过安全校验。",
        "output_blocked": "抱歉，AI 输出未通过校验。",
        "llm_error": "抱歉，AI 服务暂时不可用，请稍后重试。",
        "max_steps": "抱歉，任务过于复杂，我未能完成。请简化问题再试。",
        "internal_error": "抱歉，发生了内部错误，请联系管理员。",
    }
    return messages.get(reason, "抱歉，发生了未知错误。")
```

### 7.10 取消机制

通过 `ctx.cancel_event`（asyncio.Event）传递取消信号：
- 前端发取消请求 → 设置 cancel_event
- Runtime 在每个 step 开始检查
- 工具执行时定期检查
- 取消时 yield `Event.error("cancelled")` 并退出

### 7.11 Trace 集成

Runtime 通过 `ctx.trace_recorder` 自动记录 trace：
```
一次 turn → 一条 agent_traces 记录
  ├─ LLM 调用 → trace_step (step_type='llm_call')
  ├─ 工具调用 → trace_step (step_type='tool_call')
  ├─ handoff → trace_step (step_type='handoff')
  ├─ guardrail → trace_step (step_type='guardrail')
  ├─ memory_read → trace_step (step_type='memory_read')
  └─ memory_write → trace_step (step_type='memory_write')
```

### 7.12 关键设计决策

1. **Runtime 是编排者不是执行者**
2. **ReAct 循环固定**（不暴露为"策略"）：YAGNI
3. **Handoff 通过"显式工具"触发**
4. **Guardrail 集成在循环入口和出口**，异常降级处理
5. **Memory 短期策略三选一**：full / sliding_window / summary
6. **Checkpoint Phase 1 轻量**
7. **Event 流是 SSE + 结构化事件**
8. **取消信号通过 asyncio.Event 传递**
9. **错误处理三策略**：stop / retry / fallback_message，默认 fallback_message
10. **Trace 自动记录**

---

## 8. API 设计

### 8.1 总览

```
管理员 API（需 admin 权限）
├── /api/v1/admin/agents/*              # Agent CRUD + 扩展操作
│   ├── /{id}/tools                     # Agent 的工具绑定
│   ├── /{id}/guardrails                # Agent 的 guardrails 配置
│   ├── /{id}/test                      # 测试运行
│   └── /{id}/stats                     # 使用统计
├── /api/v1/admin/tools/*               # Tool CRUD
│   └── /builtin                        # 内置工具清单
└── /api/v1/admin/traces/*              # Trace 查询

用户 API（需 user 权限）
├── /api/v1/agents/*                    # 用户可见的 agent 列表/详情
└── /api/v1/conversations/*             # 会话 + 对话
    ├── /{id}/chat/stream               # 流式对话 ⭐
    ├── /{id}/chat/cancel               # 取消当前 turn
    └── /{id}/handoff                   # 手动切换 agent
```

### 8.2 Agent 管理 API（管理员）

```http
GET    /api/v1/admin/agents              # 列表（分页、搜索、过滤）
POST   /api/v1/admin/agents              # 创建
GET    /api/v1/admin/agents/{id}         # 详情
PUT    /api/v1/admin/agents/{id}         # 完整更新
PATCH  /api/v1/admin/agents/{id}         # 部分更新
DELETE /api/v1/admin/agents/{id}         # 删除
POST   /api/v1/admin/agents/{id}/default # 设为默认
POST   /api/v1/admin/agents/{id}/activate
POST   /api/v1/admin/agents/{id}/deactivate
POST   /api/v1/admin/agents/{id}/duplicate
POST   /api/v1/admin/agents/{id}/test    # 测试运行（SSE 流）
GET    /api/v1/admin/agents/{id}/stats
GET    /api/v1/admin/agents/stats        # 全局统计
```

### 8.3 Agent 工具绑定 API

```http
GET    /api/v1/admin/agents/{id}/tools              # 列表
POST   /api/v1/admin/agents/{id}/tools              # 添加绑定
PUT    /api/v1/admin/agents/{id}/tools/{binding_id} # 更新
DELETE /api/v1/admin/agents/{id}/tools/{binding_id} # 删除
```

### 8.4 Tool 管理 API（管理员）

```http
GET    /api/v1/admin/tools                 # 工具列表
POST   /api/v1/admin/tools                 # 注册
GET    /api/v1/admin/tools/{id}            # 详情
PUT    /api/v1/admin/tools/{id}            # 更新
DELETE /api/v1/admin/tools/{id}            # 删除
POST   /api/v1/admin/tools/{id}/test       # 测试
GET    /api/v1/admin/tools/builtin         # 内置工具清单
```

### 8.5 用户侧 Agent API

```http
GET    /api/v1/agents                      # 当前用户可用的 agent 列表
GET    /api/v1/agents/default              # 获取默认 agent
GET    /api/v1/agents/{id}                 # agent 详情
GET    /api/v1/agents/{id}/tools           # agent 可用的工具列表
```

### 8.6 对话 API（核心）

**会话管理**：
```http
POST   /api/v1/conversations              # 创建会话
GET    /api/v1/conversations              # 我的会话列表
GET    /api/v1/conversations/{id}         # 详情
PATCH  /api/v1/conversations/{id}         # 更新
DELETE /api/v1/conversations/{id}         # 删除
GET    /api/v1/conversations/{id}/messages # 消息历史
```

**流式对话**：
```http
POST /api/v1/conversations/{id}/chat/stream
```

**请求**：
```json
{
  "content": "用户消息",
  "attachments": [{"type": "image", "url": "..."}],
  "client_request_id": "uuid"
}
```

**响应**（SSE 流）：见 7.4 节

**取消**：
```http
POST /api/v1/conversations/{id}/chat/cancel
```

**手动切换 Agent**：
```http
POST /api/v1/conversations/{id}/handoff

{
  "target_agent_id": "uuid",
  "reason": "用户主动切换"
}
```

### 8.7 Trace / Observability API（管理员）

```http
GET /api/v1/admin/traces
    ?agent_id=uuid&user_id=uuid
    &status=success|error|guardrail_blocked
    &start_time=...&end_time=...
    &page=1&per_page=50

GET /api/v1/admin/traces/{id}            # 详情（含子步骤）
GET /api/v1/admin/agents/{id}/traces     # agent 的 trace 列表
GET /api/v1/admin/users/{id}/traces      # 用户的 trace 列表
```

### 8.8 与现有 API 的兼容

| 现有端点 | 处置 |
|---------|------|
| `POST /api/v1/conversations/{id}/chat/stream` | **改造**：内部切换到 AgentRuntime，请求/响应格式保持兼容 |
| `GET /api/v1/agents` | **扩展**：新增字段 |
| `/api/v1/admin/agents/*` | **扩展**：新增端点 |
| `/api/v1/admin/conversations/*` | **保留** |
| 新增 `/api/v1/admin/tools/*` | 新增 |
| 新增 `/api/v1/admin/traces/*` | 新增 |

**向后兼容承诺**：现有的 chat/stream 端点请求/响应格式不变，新增事件类型前端忽略未知即可。

### 8.9 错误码规范

```
# 客户端错误 4xxxxx
400001  invalid_request          请求参数错误
400002  agent_not_found          Agent 不存在
400003  agent_disabled           Agent 已禁用
400004  conversation_not_found   会话不存在
400005  tool_not_found           工具不存在
400006  tool_not_available       工具当前不可用
400007  invalid_handoff          非法的委派目标
400008  guardrail_blocked        被 guardrail 阻断
400009  quota_exceeded           配额超限
400010  max_steps_reached        达到最大步数
400011  cancelled                已取消
400012  duplicate_slug           slug 重复
400013  invalid_schema           JSON Schema 校验失败

# 服务端错误 5xxxxx
500001  llm_unavailable          LLM 不可用
500002  tool_execution_failed    工具执行失败
500003  internal_error           内部错误
500004  upstream_timeout         上游超时
```

**响应格式**：
```json
{
  "error": {
    "code": "agent_disabled",
    "message": "该 Agent 已被管理员禁用",
    "details": {"agent_id": "uuid"}
  }
}
```

### 8.10 关键设计决策

1. **RESTful + SSE 流式**
2. **流式响应格式统一**
3. **幂等性通过 client_request_id**
4. **Agent 的 slug 字段**：URL 友好
5. **Handoff 同时支持 LLM 自动触发和用户手动触发**
6. **Trace 只读**
7. **向后兼容**
8. **错误码分客户端/服务端两类**

---

## 9. 前端架构

### 9.1 目录结构

沿用 React 18 + TypeScript + Vite + Tailwind CSS + Zustand。

```
frontend/src/
├── components/
│   ├── Admin/
│   │   ├── AgentManagement/          # ⭐ 新：Agent 组装 UI
│   │   │   ├── AgentList.tsx
│   │   │   ├── AgentEditor/
│   │   │   │   ├── BasicTab.tsx
│   │   │   │   ├── PromptTab.tsx
│   │   │   │   ├── ModelTab.tsx
│   │   │   │   ├── ToolsTab.tsx
│   │   │   │   ├── MemoryTab.tsx
│   │   │   │   ├── BehaviorTab.tsx
│   │   │   │   ├── GuardrailsTab.tsx
│   │   │   │   ├── HandoffTab.tsx
│   │   │   │   └── TestTab.tsx
│   │   │   └── AgentStats.tsx
│   │   ├── ToolManagement/           # ⭐ 新
│   │   └── TraceView/                # ⭐ 新
│   │
│   ├── Agent/
│   │   ├── AgentWorkspace.tsx        # ⭐ 新：Agent 工作台（独立页面）
│   │   └── AgentSwitcher.tsx
│   │
│   └── Chat/
│       ├── ChatView.tsx
│       ├── MessageList.tsx
│       ├── MessageItem.tsx
│       ├── ToolCallRenderer.tsx      # ⭐ 新
│       ├── ToolRenderers/            # ⭐ 新
│       │   ├── ImageGenRenderer.tsx
│       │   ├── WebSearchRenderer.tsx
│       │   ├── DbQueryRenderer.tsx
│       │   └── DefaultRenderer.tsx
│       ├── ThinkingBlock.tsx         # ⭐ 新（折叠 CoT）
│       ├── HandoffNotice.tsx         # ⭐ 新
│       ├── GuardrailNotice.tsx       # ⭐ 新
│       ├── EventStream.tsx           # ⭐ 新
│       └── InputBox.tsx              # 改造
│
├── services/
│   ├── agentApi.ts
│   ├── toolApi.ts
│   ├── conversationApi.ts
│   ├── traceApi.ts
│   └── eventStreamClient.ts          # ⭐ 新
│
├── stores/
│   ├── useAgentStore.ts
│   ├── useConversationStore.ts
│   ├── useEventStreamStore.ts        # ⭐ 新
│   └── useToolRegistry.ts            # ⭐ 新
│
└── types/
    ├── agent.ts
    ├── tool.ts
    ├── event.ts
    └── trace.ts
```

### 9.2 核心类型定义

```typescript
// types/agent.ts
export interface Agent {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  icon_color: string;
  category: string;
  system_prompt: string;
  welcome_message?: string;
  default_model_id?: string;
  fallback_model_ids: string[];
  generation_params: Record<string, any>;
  memory_short_term_policy: "full" | "sliding_window" | "summary";
  memory_short_term_window: number;
  memory_long_term_enabled: boolean;
  max_steps_per_turn: number;
  tool_timeout_seconds: number;
  error_strategy: "stop" | "retry" | "fallback_message";
  can_handoff_to: string[];
  handoff_instruction?: string;
  visibility: "public" | "private" | "shared";
  is_active: boolean;
  is_default: boolean;
  capabilities: string[];
}

// types/event.ts
export type AgentEvent =
  | { type: "turn_start"; payload: { conversation_id: string; agent: Agent } }
  | { type: "text_delta"; payload: { text: string }; timestamp: number }
  | { type: "text_complete"; payload: { text: string } }
  | { type: "thinking_delta"; payload: { text: string } }
  | { type: "tool_call_start"; payload: { id: string; name: string; arguments: any } }
  | { type: "tool_call_progress"; payload: { id: string; progress: any } }
  | { type: "tool_result"; payload: {
      id: string; name: string; success: boolean;
      content_type: string; content: any;
      attachments: Attachment[]; error?: string
    } }
  | { type: "image_generated"; payload: { urls: string[]; metadata: any } }
  | { type: "handoff"; payload: { from_agent: Agent; to_agent: Agent; reason: string } }
  | { type: "guardrail_triggered"; payload: { guardrail_name: string; reason: string; stage: string } }
  | { type: "error"; payload: { message: string; recoverable: boolean } }
  | { type: "done"; payload: { final_text: string; usage?: any } }
  | { type: "custom"; payload: { name: string; [key: string]: any } };
```

### 9.3 事件流客户端

```typescript
// services/eventStreamClient.ts
export class EventStreamClient {
  private abortController: AbortController | null = null;
  private lastEventId: string | null = null;
  
  constructor(
    private onEvent: (event: AgentEvent) => void,
    private onError?: (error: Error) => void,
    private onDone?: () => void,
  ) {}
  
  async connect(url: string, body: any) {
    this.abortController = new AbortController();
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.lastEventId ? {"Last-Event-ID": this.lastEventId} : {}),
      },
      body: JSON.stringify(body),
      signal: this.abortController.signal,
    });
    
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, {stream: true});
      const events = this.parseSSE(buffer);
      buffer = events.remaining;
      
      for (const event of events.parsed) {
        this.lastEventId = event.id ?? this.lastEventId;
        this.onEvent(event.data as AgentEvent);
        
        if (event.data.type === "done") {
          this.onDone?.();
          return;
        }
      }
    }
  }
  
  cancel() {
    this.abortController?.abort();
  }
  
  private parseSSE(buffer: string): { parsed: SSEEvent[]; remaining: string } {
    // 标准 SSE 解析：按 \n\n 分隔事件
    ...
  }
}
```

### 9.4 对话 UI 改造

**工具渲染器注册表**：
```tsx
const toolRenderers: Record<string, React.ComponentType<ToolCallProps>> = {
  image_gen: ImageGenRenderer,
  web_search: WebSearchRenderer,
  db_query: DbQueryRenderer,
};

function ToolCallRenderer({ call, result }: ToolCallProps) {
  const Renderer = toolRenderers[call.name] ?? DefaultRenderer;
  return (
    <div className="my-2 border rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-3 py-2 text-sm flex items-center gap-2">
        <ToolIcon name={call.name} />
        <span className="font-medium">{call.display_name}</span>
        {result ? (
          result.success ? <span className="text-green-600">✓</span>
                         : <span className="text-red-600">✗ {result.error}</span>
        ) : (
          <Spinner className="ml-auto" />
        )}
      </div>
      <Renderer call={call} result={result} />
    </div>
  );
}
```

### 9.5 Agent 工作台 UI

独立路由 `/agents/:slug`，强化 agent 身份感：
- 顶部强显示当前 agent（头像、名字、描述）
- 侧边显示 agent 的工具集、记忆、handoff 历史
- 更像"与一个独立的 AI 助手对话"

### 9.6 关键设计决策

1. **工具渲染器注册表模式**：新增工具只需加渲染器 + 注册
2. **事件流统一入口**：EventStreamClient 类与 React 解耦
3. **Agent 编辑器分 tab**：避免单页过长
4. **TestTab 复用 ChatView 组件**
5. **Handoff 在 UI 上是显式提示**
6. **ThinkingBlock 默认折叠**
7. **断线重连用 Last-Event-ID**
8. **多模态输入支持**

---

## 10. 迁移策略

### 10.1 Dify 移除路径

**当前 Dify 的痕迹**：
- `dify_client.py` / `dify_config_service.py` / `dify_backend.py`
- `agent_orchestrator.py`
- DB 表 `image_gen_dify_config`
- `config.py` 的 `DIFY_*` 配置
- 前端 `DifyConfigPanel.tsx`
- 多个测试和文档

**分阶段移除**：

```
Phase 1（harness 骨架阶段）
├── 标记 deprecated（DeprecationWarning）
├── 不删除，保留运行
└── 新代码不引用 Dify

Phase 2（自研图像生成 + 切换）
├── 实现自研 image_gen BuiltinTool
├── 切换流量到 harness 路径
├── 验证稳定 1-2 周
├── 删除 Dify 全家桶
└── 清理配置和文档

Phase 3（清理）
└── 清理 git 历史（可选）
```

**回滚方案**：
- Phase 1：删除 harness 新增代码
- Phase 2：在删除 Dify 代码前，**保留 deprecated 版本 1-2 周**；配置开关 `IMAGE_GEN_BACKEND=harness|dify`

### 10.2 Agent 数据迁移

**扩展字段**（Alembic migration）：
- 所有新字段 nullable 或有默认值
- 现有数据自动填默认值
- slug 自动生成（从 name 转 kebab-case，冲突加后缀）

**零破坏性**：迁移后现有 agent 行为不变

### 10.3 图像生成自研化

**自研 image_gen BuiltinTool**：

替代 Dify 的 4 种操作，通过**多模型策略**实现：
- 优先用 Agent 配置的默认模型
- 支持按 operation 选择不同模型
- 兜底链：主模型失败 → 备用模型

**ImageModelProvider 接口**：
```python
class ImageModelProvider(Protocol):
    async def text2img(self, prompt, size, n, **kw) -> List[bytes]: ...
    async def img2img(self, prompt, reference, strength, size, **kw) -> List[bytes]: ...
    async def inpaint(self, prompt, image, mask, size, **kw) -> List[bytes]: ...
    async def edit(self, image, edit_type, **kw) -> List[bytes]: ...
```

**Phase 1 实现**：至少 2 种 provider（DALL-E 3、通义万象）

### 10.4 对话数据迁移

**conversations 表**：
- 添加 agent_id 列（nullable）
- 先创建系统默认 agent
- 历史会话填默认 agent
- 设为 NOT NULL

**messages 表**：
- 添加 tool_calls / tool_call_id / tool_name / attachments 字段（全部 nullable）
- 历史数据无需填充

### 10.5 前端迁移

**增量改造策略**：
- 老的 AgentManagement.tsx 拆分为新结构
- Chat UI 增量添加新组件
- 新老 UI 并行 1-2 周

### 10.6 API 兼容性

**兼容不动路径**：
- 老端点只扩展响应
- 新端点用新路径
- 不需要 `/api/v2/`

### 10.7 关键设计决策

1. **Dify 分阶段移除**：每阶段都可回滚
2. **自研图生多模型策略**：不绑定单一模型
3. **Agent 数据迁移零破坏**
4. **slug 自动生成**
5. **前端增量改造**
6. **API 兼容不动路径**
7. **回滚方案优先**

---

## 11. Phase 划分

### 11.1 Phase 总览

```
Phase 1 ──────── Phase 2 ──────── Phase 3
harness MVP      去 Dify + 自研    扩展能力
(4-6 周)         图生 (3-4 周)     (持续)

并行线：
Line A: harness 骨架
Line B: 自研图生
Line C: Agent 管理平台
汇合点：Phase 1 末
```

### 11.2 Phase 1：harness MVP（4-6 周）

**目标**：harness 骨架 + LLM 对话接入 + Agent 管理平台升级。**Dify 代码保留但标记 deprecated**。

**交付物（后端）**：
- ToolProtocol 接口 + BuiltinTool / HttpTool 实现
- ToolRegistry 注册表
- LLMFunctionBridge
- AgentRuntime（ReAct 循环）
- Session 管理 + Checkpoint（轻量）
- Event 流协议 + SSE 推送
- Handoff 机制
- Guardrails 集成
- Trace 记录（基础版）
- Memory 短期策略
- DB schema migration
- 新增表：tools、agent_tools、session_checkpoints、agent_traces、trace_steps
- API：admin/tools、admin/traces、扩展 admin/agents
- 改造 chat/stream 内部切换到 AgentRuntime
- 2 个 BuiltinTool：web_search、db_query

**交付物（前端）**：
- EventStreamClient
- 工具渲染器注册表 + DefaultRenderer
- Agent 编辑器多 tab UI
- Tool 管理 UI
- Trace 查看 UI
- AgentSwitcher / HandoffNotice / GuardrailNotice

**交付物（文档）**：
- 工具开发指南
- 工具配置指南
- Agent 组装最佳实践

**验证标准**：
- 现有对话功能不回归
- 新的 Agent 管理平台可装配 agent
- Agent 可调用 web_search / db_query 工具
- Handoff 在两个 agent 间正常工作
- Guardrail 能阻断违规输入/输出
- Trace 在后台可查看
- SSE 流式输出稳定

### 11.3 Phase 2：去 Dify + 自研图生（3-4 周）

**目标**：实现自研 image_gen BuiltinTool，切换流量，**删除 Dify 全家桶**。

**交付物**：
- ImageModelProvider 接口 + 至少 2 种实现
- image_gen BuiltinTool（支持 4 种 operation）
- Prompt 润色（LLM 调用）
- 模型兜底链
- Memory long-term 接入
- 切换 chat/stream 的图生流量到 harness
- 验证稳定 1-2 周
- 删除 Dify 全家桶

**验证标准**：
- 4 种图生操作全部可用
- 图生质量 ≥ Dify 版本
- 响应时间 ≤ Dify 版本
- 完全无 Dify 代码残留

### 11.4 Phase 3：扩展能力（持续）

**P1（高优先级）**：
- MCP 工具支持
- Memory long-term 向量检索（pgvector）
- Checkpoint 时间旅行
- Langfuse / OpenTelemetry 集成

**P2（中优先级）**：
- Plugin 工具支持
- Memory procedural（Agent 技能系统）
- 多模态工具（file_read、file_write、code_execute 沙箱）
- Agent 市场 / 分享

**P3（低优先级）**：
- Agent 评估框架
- 高级 Guardrail
- 多 Agent 协作可视化
- Agent 性能分析仪表盘

### 11.5 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| harness 抽象设计错误 | 高 | Phase 1 严格控制范围；每 Phase 末做架构回顾 |
| 自研图生质量不如 Dify | 中 | 灰度发布，保留 Dify 1-2 周 |
| 数据迁移出错 | 高 | 先在测试环境跑 migration；保留回滚脚本 |
| 前端改造破坏 UX | 中 | 新老 UI 并行 1-2 周 |
| ToolProtocol 不够灵活 | 中 | 协议预留 metadata 字段 |
| Trace 数据量过大 | 低 | 设置 TTL（默认 30 天） |

---

## 12. 关键设计决策汇总

| 决策点 | 选择 | 理由 |
|-------|------|------|
| 整体范围 | Agent 平台（C） | 用户明确选择最彻底方案 |
| 工具扩展性 | 可插拔协议（C） | 内置/HTTP/MCP/Plugin 四类 |
| 实施节奏 | 并行推进（C） | 两线同时走，最终汇合 |
| 架构 | Agent 三层架构（C） | Agent 为一等公民 |
| 主参考框架 | Claude Agent SDK | 简洁、清晰、工业级 |
| ReAct 循环 | 固定为默认 | YAGNI，90% 场景够用 |
| Handoff | 显式工具触发 | 对 LLM 自然，Runtime 严格控制 |
| Handoff 目标 | slug 列表 | slug 稳定、URL 友好 |
| Guardrail 实现 | 复用 Tool 机制 | 不单独建表 |
| Memory 分层 | 三层 | short-term + long-term + procedural(Phase 3) |
| Trace | 两层 | traces + steps |
| Checkpoint | Phase 1 轻量 | messages_ref + state |
| 错误处理 | 三策略 | stop/retry/fallback_message，默认 fallback |
| 取消机制 | asyncio.Event | 工具定期检查 |
| 事件流 | SSE + 结构化事件 | 业界标准 |
| 前端工具渲染 | 注册表模式 | 新增工具只需加渲染器 |
| 前端 Agent 入口 | 独立工作台 | 强化 agent 身份感 |
| Dify 移除 | 分阶段 | Phase 1 deprecated，Phase 2 删除 |
| 自研图生 | 多模型策略 | 不绑定单一模型 |
| 数据迁移 | 零破坏 | 新字段 nullable 或有默认值 |
| API 兼容 | 不动路径 | 老端点扩展，新端点新路径 |

---

## 附录 A：术语对照表

| 中文 | 英文 | 参考框架 |
|------|------|---------|
| Agent | Agent | 所有框架 |
| 工具 | Tool | 所有框架 |
| 工具协议 | ToolProtocol | MCP |
| 会话 | Session | Claude Agent SDK |
| 对话 | Conversation | OpenAI Assistants |
| 消息 | Message | 所有框架 |
| 事件 | Event | Vercel AI SDK |
| 委派 | Handoff | OpenAI Agents SDK |
| 护栏 | Guardrail | OpenAI Agents SDK |
| 追踪 | Trace | Langfuse / OpenTelemetry |
| 检查点 | Checkpoint | LangGraph |
| 记忆 | Memory | Mem0 / MemGPT |
| 短期记忆 | Short-term Memory | 业界通用 |
| 长期记忆 | Long-term Memory | 业界通用 |
| 程序性记忆 | Procedural Memory | MemGPT |
| 编排器 | Runtime | 通用 |
| 注册表 | Registry | 通用 |
| 内置工具 | BuiltinTool | 本项目 |
| HTTP 工具 | HttpTool | 本项目 |
| MCP 工具 | McpTool | MCP |
| 插件工具 | PluginTool | 通用 |

---

## 附录 B：文件清单（Phase 1 新增）

**后端**：
```
backend/app/services/harness/
├── __init__.py
├── tool_protocol.py          # ToolProtocol 接口
├── tool_result.py            # ToolResult / ToolContext / ToolCall
├── tool_registry.py          # ToolRegistry
├── llm_bridge.py             # LLMFunctionBridge
├── agent_runtime.py          # AgentRuntime
├── session.py                # Session
├── events.py                 # Event 类型
├── trace_recorder.py         # Trace 记录
├── memory_policy.py          # Memory 策略
├── guardrail.py              # Guardrail 执行
├── handoff.py                # Handoff 机制
└── tools/
    ├── __init__.py
    ├── base.py               # BuiltinTool 基类
    ├── web_search.py         # WebSearchTool
    └── db_query.py           # DbQueryTool

backend/app/models/
├── agent.py                  # 扩展
├── tool.py                   # 新增
├── tool_binding.py           # 新增
├── session_checkpoint.py     # 新增
├── agent_memory.py           # 新增
├── trace.py                  # 新增
└── conversation.py           # 扩展

backend/app/api/routes/
├── admin_tools.py            # 新增
├── admin_traces.py           # 新增
└── agents.py                 # 扩展

backend/migrations/versions/
└── xxxx_expand_for_harness.py
```

**前端**：
```
frontend/src/
├── components/
│   ├── Admin/AgentManagement/  (新)
│   ├── Admin/ToolManagement/   (新)
│   ├── Admin/TraceView/        (新)
│   ├── Agent/AgentWorkspace.tsx (新)
│   └── Chat/...                (改造)
├── services/eventStreamClient.ts (新)
├── stores/useEventStreamStore.ts (新)
├── stores/useToolRegistry.ts     (新)
└── types/{agent,tool,event,trace}.ts (新)
```

---

**文档结束**

> 下一步：用户 review 此 spec，确认无误后，进入 `writing-plans` 阶段，把此 spec 拆分为 Phase 1 的实施计划。
