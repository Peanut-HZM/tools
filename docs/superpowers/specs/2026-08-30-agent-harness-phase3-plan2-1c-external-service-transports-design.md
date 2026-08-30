# P2-①c 外部服务插件（stdio + streamable HTTP transport）设计文档

**日期**：2026-08-30
**Phase**：3-Plan-2-1c（对应原 P2 列表"Plugin 工具支持 → ①c 外部服务插件"）
**状态**：设计完成（自主决策模式：用户已预授权"按优先级完成任务、按流程处理、务必完成验收"）
**对应规划 ID**：Phase 3 设计文档 §11.4 P2 列表第 5 项 "Plugin 工具支持" 的 ①c 子方向

---

## 1. 背景与目标

### 1.1 背景

Phase 3 P1-Plan1A 交付了 MCP 工具支持，但 **只实现了 SSE transport**：

- `McpClient`（`backend/app/services/harness/mcp_client.py`）硬编码 `sse_client`
- `McpServer.transport` 列已预留 `"sse / stdio / http"` 三种值（`mcp_server.py:26`），但 stdio / http 传入即不可用
- Pydantic schema `McpServerCreate.transport` 是 `Literal["sse"]`
- 前端 `CreateDialog.tsx` 硬编码 `transport: 'sse'`

现实中大量 MCP server 以 **stdio 本地进程** 形态分发（`npx @modelcontextprotocol/server-*`、`uvx mcp-server-*`），且 MCP 官方已转向 **streamable HTTP** transport。不补齐这两种 transport，"外部服务插件"名不副实。

### 1.2 目标

让 admin 可以把三种形态的外部 MCP 服务接入 Agent 工具体系：

1. **stdio 本地进程**（新增）：spawn 子进程，MCP 协议走 stdin/stdout
2. **streamable HTTP**（新增）：新版 MCP HTTP transport（单端点 POST + SSE 流）
3. **SSE**（现状保持）：已上线，不改动行为

### 1.3 非目标（明确划出去）

- 不做非 MCP 协议的通用 OpenAPI 导入（现有 `HttpTool` 覆盖单端点 HTTP 工具，batch 导入是另一个 plan）
- 不做 MCP OAuth / sampling / roots / prompts / resources —— 仅 tools 能力
- 不做 stdio 进程崩溃自动重启 —— 调用报错，admin 重新 sync 即可（YAGNI）
- 不做 admin UI 编辑 transport —— 创建后 transport 不可改（与现状"编辑不传 transport"一致）
- 不做 Provider 插件 / 事件钩子 —— ①c 收口后如仍有需求另立 plan

---

## 2. 架构总览

### 2.1 transport 分发模型

```
McpServerManager.sync_server(server)
    │
    ▼
McpClient(server, transport=server.transport, command=server.command_json)
    │
    ├─ transport == "sse"   → sse_client(url, headers)                    （现状）
    ├─ transport == "http"  → streamable_http_client(url, headers)        （新增）
    └─ transport == "stdio" → stdio_client(StdioServerParameters(          （新增）
                                command, args, env))
    │
    ▼
ClientSession(read_stream, write_stream).initialize()   # 三者统一
    │
    ▼
tools_list() / tools_call()   # 与 transport 无关，零改动
```

关键点：**只有连接建立这一层随 transport 变化**，握手后的 `ClientSession`、`tools_list`、`tools_call`、`McpTool`、`ToolRegistry` 全部复用，零改动。

### 2.2 数据模型变更

`mcp_servers` 表新增 1 列（零破坏：nullable，无默认值变更，不改已有列）：

| 列 | 类型 | 说明 |
|---|---|---|
| `command_json` | `Text`, nullable | stdio 启动配置：`{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"], "env": {"KEY": "v"}}` |

- `sse` / `http` transport：继续用 `server_url`，`command_json` 为 NULL
- `stdio` transport：`server_url` 存进程描述字符串（仅展示用，如 `npx -y @modelcontextprotocol/server-everything`），真正启动参数读 `command_json`

### 2.3 McpClient 内部结构

```python
class McpClient:
    def __init__(self, server_url="", *, transport="sse", command=None,
                 headers=None, timeout=30, allow_private_hosts=False): ...

    async def connect(self):
        # 按 transport 分发到 _connect_sse / _connect_streamable_http / _connect_stdio
        # 统一：拿 (read, write) → ClientSession → initialize()（带 timeout）
```

- `_transport_ctx`：统一的 async context manager 引用（替代现 `_sse_context`），`disconnect()` 统一 `__aexit__`
- `streamable_http_client` 产出 3 元组 `(read, write, get_session_id)`，适配时丢弃第三项
- `stdio_client` 产出 2 元组，与 SSE 一致
- SSRF `validate_url()` 仅对 `sse` / `http` 生效；`stdio` 无 URL 语义，跳过（进程 spawn 的信任模型见 §4）

### 2.4 与现有代码的衔接

| 文件 | 改动 |
|---|---|
| `mcp_client.py` | 重构连接层为三分发；`validate_url` 调用条件化 |
| `mcp_server_manager.py` | `_get_or_create_client` 按 `server.transport` 传参；缓存 key 不变 |
| `models/mcp_server.py` | 加 `command_json` 列 |
| `schemas/mcp_server.py` | `transport: Literal["sse","http","stdio"]`；Create/Update 加 `command` 字段；Response 加 `command_json` |
| `admin_mcp_servers.py` | create/update 做 per-transport 校验（见 §3.2） |
| alembic migration | 1 个新 migration：`add command_json to mcp_servers` |
| `tool_registry.py` / `mcp_tool.py` / `agent_runtime.py` | **零改动** |

---

## 3. 关键设计

### 3.1 transport 语义与配置矩阵

| transport | 必填 | 可选 | 启动方式 |
|---|---|---|---|
| `sse` | `server_url` | `headers`, `timeout` | 现状不变 |
| `http` | `server_url` | `headers`, `timeout` | streamable HTTP（同 URL 校验） |
| `stdio` | `command`（JSON） | `env`(在 command 内), `timeout` | spawn 子进程 |

### 3.2 API 校验规则（create / update 共用）

- `transport` 取值必须 ∈ {sse, http, stdio}（Pydantic Literal 兜底 + 路由层显式 400）
- `sse` / `http`：`server_url` 必填且通过 `validate_url`（在 connect 时校验，与现状一致）
- `stdio`：`command` 必须是合法 JSON object，`command` 键必填非空字符串；`args` 可选字符串数组；`env` 可选 string→string 映射
- `stdio` 时 `headers` 忽略；`sse`/`http` 时 `command` 忽略
- update 不允许改 `transport`（schema 层不暴露该字段，与现状一致）

### 3.3 安全模型

- **stdio = 本地代码执行**：只有 admin 能调 `/api/admin/mcp/servers`（已有 `require_admin` 门禁），信任模型与 P2-①b 文件插件一致——"能配 stdio 命令的人 = 已经是 admin"
- `env` 默认继承最小环境（MCP SDK `get_default_environment()`：PATH、HOME 等），admin 显式配置的 `env` 追加其上，不透传完整后端进程环境（避免泄露 SECRET_KEY 等）
- `http` transport 复用 `validate_url` SSRF 防护（含 `MCP_ALLOW_PRIVATE_HOSTS` 语义与云元数据永久拒绝）
- 日志不打 command 中的 env 值，仅记 command + args

### 3.4 错误处理表

| 场景 | 行为 |
|---|---|
| stdio 命令不存在/启动失败 | `sync_server` 返回 `{"success": False, "error": ...}`，`last_error` 落库，不影响其他 server |
| stdio 进程运行中崩溃 | 当次 `tools_call` 抛异常 → `McpTool.execute` 捕获 → `ToolResult.error` |
| `http` 端点不是 streamable MCP | connect 失败 → 同上，admin 侧 last_error 可见 |
| `command_json` 非法 JSON | create/update 时 400；历史脏数据在 connect 时 `McpConnectionError` |
| 已有 SSE server | 行为完全不变（回归保证） |

---

## 4. 测试策略

### 4.1 单元测试 `test_mcp_client_transports.py`（新）

| 用例 | 覆盖 |
|---|---|
| `test_sse_uses_sse_client` | transport=sse → mock `sse_client` 被调用，url/headers 透传 |
| `test_http_uses_streamable_client` | transport=http → mock `streamable_http_client` 被调用；3 元组适配 |
| `test_stdio_uses_stdio_client` | transport=stdio → mock `stdio_client` 被调用；`StdioServerParameters` 参数正确（command/args/env） |
| `test_stdio_skips_url_validation` | stdio 不触发 `validate_url` |
| `test_http_validates_url` | http 走 SSRF 校验（内网默认拒绝） |
| `test_stdio_default_env_is_minimal` | 未显式配 env 时使用 SDK 默认最小环境，不含后端 secrets |
| `test_disconnect_exits_active_transport` | 三种 transport 的 ctx 都能被正确 `__aexit__` |

### 4.2 集成测试 `test_mcp_stdio_integration.py`（新，真子进程）

用 `sys.executable` 启动一个临时 FastMCP server 脚本（写入 tmp_path），真实走 stdio：

| 用例 | 覆盖 |
|---|---|
| `test_stdio_end_to_end_tools_list` | connect → tools_list 返回脚本内定义的工具 |
| `test_stdio_end_to_end_tools_call` | tools_call 拿到真实返回值 |
| `test_stdio_command_not_found` | command 指向不存在的可执行文件 → `McpConnectionError`，错误信息含 stderr 摘要 |

### 4.3 API/Schema 测试（扩展现有 `test_mcp_server_manager.py` 或新增 `test_admin_mcp_transports.py`）

| 用例 | 覆盖 |
|---|---|
| `test_create_stdio_server_requires_command` | 缺 command → 400 |
| `test_create_http_server_accepted` | transport=http + url → 201 |
| `test_create_invalid_transport_rejected` | transport=grpc → 422 |
| `test_response_contains_command_json` | stdio server 的 response 带 `command_json` |
| `test_manager_builds_client_per_transport` | manager 按 transport 构造对应 client 且缓存命中 |

### 4.4 回归

现有 `test_mcp_client.py` / `test_mcp_client_security.py` / `test_mcp_server_manager.py` / `test_mcp_tool.py` / `test_mcp_integration.py` 全部保持通过（SSE 路径零行为变化）。

### 4.5 前端验证

- `npm run build` + `tsc` 通过
- `mcpServersApi.test.ts` 扩展 transport 类型用例
- CreateDialog：transport 切换时 URL/命令输入区联动（手测路径写入 plan 验收项）

---

## 5. 已知限制 / 不做清单

| 不做 | 理由 |
|---|---|
| stdio 进程自动重启/健康检查 | YAGNI；sync 失败已可见 |
| transport 编辑 | 与现状一致，删除重建即可 |
| MCP OAuth | 无使用场景 |
| OpenAPI batch 导入 | 另立 plan（HttpTool 已覆盖单端点） |
| WebSocket transport | MCP 官方已弃用该方向 |

---

## 6. 文件清单

后端新增：
- `backend/alembic/versions/xxxx_add_command_json_to_mcp_servers.py`
- `backend/tests/harness/test_mcp_client_transports.py`
- `backend/tests/harness/test_mcp_stdio_integration.py`

后端修改：
- `backend/app/services/harness/mcp_client.py`（连接层三分发，~80 行增量）
- `backend/app/services/harness/mcp_server_manager.py`（构造参数，~15 行）
- `backend/app/models/mcp_server.py`（+1 列）
- `backend/app/schemas/mcp_server.py`（transport Literal + command 字段，~20 行）
- `backend/app/api/routes/admin_mcp_servers.py`（per-transport 校验，~30 行）

前端修改：
- `frontend/src/api/mcpServersApi.ts`（transport 联合类型 + command_json）
- `frontend/src/components/Admin/McpServers/CreateDialog.tsx`（transport 选择器 + 联动输入）
- `frontend/src/components/Admin/McpServers/index.tsx`（stdio 行展示 command 摘要，可选）

---

## 7. 决策记录

### 7.1 为什么 scope 是"补齐 MCP transport"而不是"通用非 MCP 服务"

原列表写"HTTP/stdio services beyond MCP"。对照代码：`McpServer.transport` 列本身就规划了 `stdio / http`，Plan1A 只交付了 SSE——"beyond"指的是超出 1A 已交付范围，而非脱离 MCP 协议。通用 REST 服务导入与已有 `HttpTool` 重叠，收益存疑（YAGNI）。

### 7.2 为什么 stdio 不做 SSRF 而做最小 env

stdio 没有 URL，SSRF 模型不适用；它对应的风险是"本地代码执行"，由 admin 门禁 + 信任模型覆盖（与 ①b 文件插件同构）。env 用 SDK 默认最小集而非完整继承，防止后端 secrets（DB 密码、API key）意外泄露给子进程。

### 7.3 为什么 server_url 在 stdio 下仍必填（展示用）

避免 nullable 语义分叉带来的 schema 兼容复杂度：`server_url` 保持 `min_length=1`，stdio 时存人可读的命令摘要（前端列表直接复用现有列渲染）。

---

## 8. 参考 / 相关

- `docs/superpowers/specs/2026-08-28-agent-harness-design.md` §11.4 —— P2 列表出处
- `docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1b-file-plugin-system-design.md` —— ①c 定义出处
- `backend/app/services/harness/mcp_client.py` —— 现有 SSE 实现
- mcp SDK 2.1.1：`mcp.client.stdio.stdio_client` / `mcp.client.streamable_http.streamable_http_client`
