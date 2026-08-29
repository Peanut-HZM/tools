# Agent Harness Phase 3-Plan-1A: MCP 工具支持（核心骨架）设计

**日期**: 2026-08-29
**状态**: 待实施
**依赖**: Phase 1 + Phase 2 已完成

---

## 1. 目标

为 harness 引入 MCP（Model Context Protocol）工具支持，使 Agent 能够调用外部 MCP server 提供的工具。

**本 plan 范围**：核心骨架，仅 SSE transport，跑通最小闭环。

**不在本 plan**：stdio / streamable HTTP transport、连接池、自动重连、健康检查、手动 schema 覆写、批量导入、性能监控（→ Plan-1B）。

---

## 2. 设计决策（已确认）

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Transport | SSE | 远程 MCP server 常用，接入成本低 |
| Server 管理 | Admin UI 动态管理 | 灵活、多环境可复用 |
| 工具发现 | 自动发现 | 零配置体验，符合 MCP 设计哲学 |
| 错误处理 | 超时 + 不重试 | 语义简单，由 LLM 决定下一轮 |
| 命名空间 | `mcp:{server_name}:{tool_name}` | 避免工具名冲突，便于追溯 |
| 超时 | 30s（可配置） | 平衡响应速度与外部调用复杂度 |

---

## 3. 架构

```
┌──────────────────────────────────────────────────────────┐
│ Admin UI (/admin/mcp)                                     │
│   - 服务器列表 (name, url, transport, active, tools)     │
│   - 添加 / 编辑 / 删除 / 测试连接 / 启用禁用              │
└──────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Backend: Admin API (/api/admin/mcp/servers)              │
│   - CRUD                                                  │
│   - POST /{id}/test → 测试连接 + 拉取工具列表            │
│   - POST /{id}/sync → 同步工具到 ToolRegistry            │
└──────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ McpServerManager                                          │
│   - 管理 mcp_servers 表的活跃 server                     │
│   - 按需创建 McpClient                                    │
│   - 触发工具发现 + ToolRegistry 注册                      │
└──────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ McpClient (SSE transport)                                │
│   - connect()      建立 SSE 长连接                        │
│   - tools_list()   调用 MCP tools/list                    │
│   - tools_call()   调用 MCP tools/call                    │
│   - disconnect()   关闭连接                                │
└──────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ McpTool (实现 Tool 协议)                                  │
│   - name: "mcp:{server_name}:{tool_name}"                 │
│   - description: 从 server 拉取                           │
│   - input_schema: 从 server 拉取                          │
│   - invoke(ctx, args) → ToolResult                        │
└──────────────────────────────────────────────────────────┘
```

---

## 4. 数据模型

### 4.1 `mcp_servers` 表

```python
class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    server_url: Mapped[str] = mapped_column(String(500))
    transport: Mapped[str] = mapped_column(String(20), default="sse")  # sse / stdio / http
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    headers_json: Mapped[str | None] = mapped_column(Text)  # JSON 字符串，鉴权用
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)

    # 状态缓存（由最近一次 test/sync 更新）
    last_connected_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 4.2 Alembic 迁移

新增迁移脚本创建 `mcp_servers` 表。

---

## 5. 核心组件

### 5.1 `McpClient`（SSE transport）

**文件**：`backend/app/services/harness/mcp_client.py`

```python
class McpClient:
    """MCP SSE 客户端"""

    def __init__(self, server_url: str, headers: dict | None = None, timeout: int = 30):
        self.server_url = server_url
        self.headers = headers or {}
        self.timeout = timeout
        self._session: ClientSession | None = None

    async def connect(self) -> None:
        """建立 SSE 连接并完成 MCP 握手"""
        # 实现：
        # 1. 建立 SSE 长连接到 {server_url}/sse
        # 2. 读取 server 的 messages endpoint
        # 3. 发送 initialize 请求
        # 4. 等待 initialized 响应

    async def tools_list(self) -> list[dict]:
        """调用 MCP tools/list 获取工具列表"""
        # 返回: [{"name": "...", "description": "...", "inputSchema": {...}}, ...]

    async def tools_call(self, name: str, arguments: dict) -> dict:
        """调用 MCP tools/call 执行工具"""
        # 返回: {"content": [...], "isError": bool}

    async def disconnect(self) -> None:
        """关闭连接"""
```

**实现要点**：
- 使用 `mcp` Python 包（如 `mcp.client.sse`）或手写 SSE + JSON-RPC 客户端
- 所有方法带超时（`asyncio.wait_for`）
- 连接失败抛 `McpConnectionError`

### 5.2 `McpTool`（Tool 协议实现）

**文件**：`backend/app/services/harness/tools/mcp_tool.py`

```python
class McpTool:
    """MCP 工具（实现 harness Tool 协议）"""

    def __init__(
        self,
        server_id: UUID,
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: dict,
        client: McpClient,
        timeout: int,
    ):
        self.server_id = server_id
        self.tool_name = tool_name
        self._name = f"mcp:{server_name}:{tool_name}"
        self._description = description
        self._input_schema = input_schema
        self._client = client
        self._timeout = timeout

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict:
        return self._input_schema

    async def invoke(self, ctx: ToolContext, args: dict) -> ToolResult:
        """调用 MCP 工具"""
        try:
            result = await asyncio.wait_for(
                self._client.tools_call(self.tool_name, args),
                timeout=self._timeout,
            )
            if result.get("isError"):
                return ToolResult(success=False, error=str(result.get("content")))
            return ToolResult(success=True, content=result.get("content"))
        except asyncio.TimeoutError:
            logger.warning(f"MCP tool {self._name} timeout after {self._timeout}s")
            return ToolResult(success=False, error=f"MCP tool timeout after {self._timeout}s")
        except Exception as e:
            logger.exception(f"MCP tool {self._name} failed")
            return ToolResult(success=False, error=str(e))
```

### 5.3 `McpServerManager`

**文件**：`backend/app/services/harness/mcp_server_manager.py`

```python
class McpServerManager:
    """MCP Server 管理器"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._clients: dict[UUID, McpClient] = {}

    async def sync_server(self, server_id: UUID) -> dict:
        """同步 server 工具到 ToolRegistry

        Returns:
            {"success": bool, "tools_count": int, "error": str | None}
        """
        # 1. 从 DB 加载 McpServer
        # 2. 创建 McpClient
        # 3. 调用 connect() + tools_list()
        # 4. 为每个工具创建 McpTool 并注册到 ToolRegistry
        # 5. 更新 server.tools_count + last_connected_at
        # 6. 返回结果

    async def unsync_server(self, server_id: UUID) -> None:
        """从 ToolRegistry 移除 server 的所有工具"""
        # 用于删除 server 或禁用时

    def get_client(self, server_id: UUID) -> McpClient | None:
        """获取缓存的 client（如有）"""
        return self._clients.get(server_id)
```

---

## 6. Admin API

### 6.1 路由

**文件**：`backend/app/api/routes/v1/admin/mcp_servers.py`

```
GET    /api/admin/mcp/servers           # 列表
POST   /api/admin/mcp/servers           # 创建
GET    /api/admin/mcp/servers/{id}      # 详情
PUT    /api/admin/mcp/servers/{id}      # 更新
DELETE /api/admin/mcp/servers/{id}      # 删除
POST   /api/admin/mcp/servers/{id}/test # 测试连接
POST   /api/admin/mcp/servers/{id}/sync # 同步工具到 ToolRegistry
```

### 6.2 Pydantic Schema

**文件**：`backend/app/schemas/mcp_server.py`

```python
class McpServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    server_url: str = Field(..., min_length=1, max_length=500)
    transport: Literal["sse"] = "sse"  # 本期仅支持 sse
    headers: dict[str, str] | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)

class McpServerUpdate(BaseModel):
    name: str | None = None
    server_url: str | None = None
    headers: dict[str, str] | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    is_active: bool | None = None

class McpServerResponse(BaseModel):
    id: UUID
    name: str
    server_url: str
    transport: str
    is_active: bool
    timeout_seconds: int
    last_connected_at: datetime | None
    last_error: str | None
    tools_count: int
    created_at: datetime
    updated_at: datetime

class McpServerTestResponse(BaseModel):
    success: bool
    tools: list[dict]  # [{name, description, input_schema}, ...]
    error: str | None = None
```

---

## 7. 前端 Admin UI

### 7.1 页面结构

**路由**：`/admin/mcp`

**文件**：
- `frontend/src/components/Admin/McpServers/index.tsx` — 列表页
- `frontend/src/components/Admin/McpServers/CreateDialog.tsx` — 添加对话框
- `frontend/src/components/Admin/McpServers/EditDialog.tsx` — 编辑对话框
- `frontend/src/components/Admin/McpServers/TestResultDialog.tsx` — 测试结果对话框

### 7.2 列表页

```
+-----------------------------------------------+
| MCP Servers                   [+ 添加 Server] |
+-----------------------------------------------+
| Name   | URL              | Tools | Status    | Actions        |
|--------|------------------|-------|-----------|----------------|
| github | http://...:3000  | 12    | ✅ Active | [测试][编辑][删]|
| fs     | http://...:3001  | 5     | ❌ Error  | [测试][编辑][删]|
+-----------------------------------------------+
```

**操作**：
- **添加 Server**：表单（name, server_url, headers JSON, timeout）
- **测试连接**：调用 `POST /{id}/test`，显示工具列表
- **编辑**：修改 name/url/headers/timeout/is_active
- **删除**：二次确认后删除

### 7.3 API Client

**文件**：`frontend/src/api/mcpServersApi.ts`

```typescript
export interface McpServer {
  id: string;
  name: string;
  server_url: string;
  transport: 'sse';
  is_active: boolean;
  timeout_seconds: number;
  last_connected_at: string | null;
  last_error: string | null;
  tools_count: number;
  created_at: string;
  updated_at: string;
}

export const mcpServersApi = {
  list: () => apiClient.get<McpServer[]>('/api/admin/mcp/servers'),
  create: (data: McpServerCreate) => apiClient.post<McpServer>('/api/admin/mcp/servers', data),
  update: (id: string, data: McpServerUpdate) => apiClient.put<McpServer>(`/api/admin/mcp/servers/${id}`, data),
  delete: (id: string) => apiClient.delete(`/api/admin/mcp/servers/${id}`),
  test: (id: string) => apiClient.post<McpServerTestResponse>(`/api/admin/mcp/servers/${id}/test`),
  sync: (id: string) => apiClient.post<{ success: boolean; tools_count: number }>(`/api/admin/mcp/servers/${id}/sync`),
};
```

### 7.4 AdminLayout 菜单

在 `AdminLayout.tsx` 添加菜单项：

```typescript
{ path: '/admin/mcp', label: 'MCP 工具', icon: <PlugIcon className="w-5 h-5" /> },
```

---

## 8. ToolRegistry 集成

### 8.1 动态注册

**文件**：`backend/app/services/harness/tool_registry.py`

新增方法：

```python
def register_dynamic(self, tool: Tool) -> None:
    """动态注册工具（MCP / Plugin 用）"""
    if tool.name in self._tools:
        logger.warning(f"Tool {tool.name} already registered, overwriting")
    self._tools[tool.name] = tool
    logger.info(f"Registered dynamic tool: {tool.name}")

def unregister_dynamic(self, name: str) -> None:
    """移除动态注册的工具"""
    if name in self._tools:
        del self._tools[name]
        logger.info(f"Unregistered dynamic tool: {name}")
```

### 8.2 启动时同步

**文件**：`backend/app/main.py`

在 startup hook 中：

```python
@app.on_event("startup")
async def sync_mcp_servers():
    """启动时同步所有活跃的 MCP server"""
    mcp_manager = get_mcp_server_manager()
    servers = db.query(McpServer).filter(McpServer.is_active == True).all()
    for server in servers:
        try:
            await mcp_manager.sync_server(server.id)
        except Exception as e:
            logger.exception(f"Failed to sync MCP server {server.name}: {e}")
```

---

## 9. 错误处理

| 场景 | 处理 |
|------|------|
| 连接失败 | `McpConnectionError`，更新 `last_error`，返回 500 |
| 工具调用超时 | 30s 后返回 `ToolResult(success=False, error="timeout")` |
| 工具不存在 | `ToolResult(success=False, error="tool not found")` |
| Server 返回 isError=true | `ToolResult(success=False, error=<content>)` |
| 同步时 server 不可用 | 更新 `last_error`，不影响其他 server |
| 工具名冲突 | `logger.warning` + 覆盖旧工具 |

**不重试**：失败后由 LLM 下一轮决定是否重试。

---

## 10. 测试策略

### 10.1 单元测试

**文件**：`backend/tests/harness/test_mcp_client.py`
- Mock SSE stream，测试 `connect` / `tools_list` / `tools_call` / `disconnect`
- 测试超时
- 测试连接失败

**文件**：`backend/tests/harness/test_mcp_tool.py`
- Mock McpClient，测试 `McpTool.invoke`
- 测试成功 / 超时 / 工具不存在 / server 返回错误

**文件**：`backend/tests/harness/test_mcp_server_manager.py`
- 测试 `sync_server` / `unsync_server`
- 测试工具注册到 ToolRegistry

### 10.2 Admin API 测试

**文件**：`backend/tests/test_admin_mcp_servers.py`
- CRUD 测试
- `/test` 和 `/sync` 测试
- 权限测试（需 admin 认证）

### 10.3 集成测试

**文件**：`backend/tests/harness/test_mcp_integration.py`
- 启动真实 MCP server（Python `mcp` 包的 echo server）
- 端到端测试：创建 server → 测试连接 → 同步 → Agent 调用工具

### 10.4 前端测试

**文件**：`frontend/src/components/Admin/McpServers/__tests__/`
- 列表渲染
- 添加 / 编辑 / 删除流程
- 测试连接结果显示

---

## 11. Plan-1A 任务拆分（预估）

1. **Task 1**: Alembic 迁移 + `McpServer` 模型
2. **Task 2**: `McpClient`（SSE transport + 单元测试）
3. **Task 3**: `McpTool` + `McpServerManager`（+ 单元测试）
4. **Task 4**: Admin API 路由 + Schema（+ API 测试）
5. **Task 5**: ToolRegistry 动态注册 + 启动时同步
6. **Task 6**: 前端 Admin UI（列表 + CRUD + 测试连接）
7. **Task 7**: 集成测试 + 端到端验证

**预估工作量**：5-7 天。

---

## 12. 成功标准

- ✅ 管理员可以通过 UI 添加 MCP server（SSE transport）
- ✅ 测试连接返回工具列表
- ✅ 同步后工具出现在 ToolRegistry，Agent 可调用
- ✅ 工具调用超时返回友好错误
- ✅ 单元测试覆盖率 ≥ 80%
- ✅ 集成测试通过（真实 MCP server）
- ✅ 前端 UI 可用，无 console 错误

---

## 13. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| MCP Python SDK 不成熟 | 高 | 手写 SSE + JSON-RPC 客户端作为 fallback |
| SSE 长连接稳定性差 | 中 | 本期不重连，失败后手动重新同步 |
| 工具 schema 与 harness 不兼容 | 中 | 宽松校验，仅要求 `name` + `description` + `inputSchema` |
| 工具名冲突 | 低 | 命名空间 `mcp:{server_name}:{tool_name}` 隔离 |
| Server 响应慢导致 Agent 卡死 | 中 | 30s 超时保护 |

---

## 14. 后续 Plan（Phase 3-Plan-1B）

- stdio + streamable HTTP transport
- 连接池 + 自动重连 + 健康检查
- 手动 schema 覆写 + 批量导入
- 性能监控面板

---

## 附录 A：参考资源

- MCP 官方文档：https://modelcontextprotocol.io/
- MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
- MCP TypeScript SDK：https://github.com/modelcontextprotocol/typescript-sdk
- MCP Servers 列表：https://github.com/modelcontextprotocol/servers

## 附录 B：测试用 MCP Server

**Echo server**（最简单）：

```bash
# Python
pip install mcp
python -m mcp.server.echo

# Node.js
npx @modelcontextprotocol/server-everything
```
