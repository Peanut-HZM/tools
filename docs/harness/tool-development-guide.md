# 工具开发指南

本文档说明 Harness Phase 1 工具（BuiltinTool / HttpTool）的开发流程、接口约定、安全约束和测试方法。所有代码引用均来自当前实现。

## 1. 工具类型与选型

Harness Phase 1 支持两种工具实现方式：

| 类型 | 触发方式 | 数据驱动 | 何时使用 |
|------|----------|----------|----------|
| **BuiltinTool** | 继承基类、写 Python 代码 | 否（代码驱动） | 需要复杂逻辑、访问 DB/OSS 等内部资源 |
| **HttpTool** | 通过 `POST /api/v1/admin/tools` 在 DB 配置 | 是（配置驱动） | 简单 HTTP 调用、第三方 API 包装 |

**未来阶段**：MCP / Plugin（Phase 1 暂未实现）。

### 1.1 选型决策树

```
是否需要访问 DB / OSS / LLM Gateway / Session?
  ├─ 是 → BuiltinTool（代码驱动，可调用 ctx.db / ctx.oss_service 等）
  └─ 否 → 是否需要复杂业务逻辑（重试 / 缓存 / 协议转换）?
              ├─ 是 → BuiltinTool
              └─ 否 → HttpTool（配置即用，零代码）
```

参考实现：`backend/app/services/harness/tools/builtin/db_query.py`（BuiltinTool 访问 DB）和 `backend/app/services/harness/tools/builtin/http_tool.py`（HttpTool 仅做 HTTP 调用）。

## 2. ToolProtocol 接口契约

所有工具必须实现 `ToolProtocol`（`backend/app/services/harness/tool_protocol.py:140`）：

```python
@runtime_checkable
class ToolProtocol(Protocol):
    name: str
    display_name: str
    description: str
    parameters_schema: dict        # OpenAI function calling 格式
    returns_schema: Optional[dict]

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult: ...
    def execute_stream(self, args: dict, ctx: ToolContext) -> AsyncIterator[ToolEvent]: ...
    def is_available(self, ctx: ToolContext) -> bool: ...
    def to_function_schema(self) -> dict: ...
```

### 2.1 ToolResult 数据结构（`tool_protocol.py:31`）

```python
@dataclass
class ToolResult:
    success: bool
    content: Any                       # 主内容（text/JSON 数据/图片说明）
    content_type: str                  # text / json / image / file / error
    error_message: Optional[str]
    metadata: Dict[str, Any]
    attachments: List[Attachment]

    @classmethod
    def text(cls, text: str, **kw) -> "ToolResult": ...
    @classmethod
    def json(cls, data: Any, **kw) -> "ToolResult": ...
    @classmethod
    def image(cls, url: str, alt: str = "", **kw) -> "ToolResult": ...
    @classmethod
    def error(cls, message: str, **kw) -> "ToolResult": ...

    def to_llm_text(self) -> str: ...   # 给 LLM 看的纯文本形式
```

**使用建议**：

- 普通文本 → `ToolResult.text("...")`
- 结构化数据 → `ToolResult.json({...})`
- 图片 → `ToolResult.image(url="https://...", alt="...")`
- 失败 → `ToolResult.error("...")` （不要抛异常，ToolRegistry 会捕获并转为 error 结果）
- metadata 放额外上下文（如 `{"sql": "...", "duration_ms": 123}`），不进 LLM 但进入 trace

### 2.2 ToolContext 提供的运行时依赖（`tool_protocol.py:104`）

```python
ctx.user_id           # 当前用户 UUID
ctx.conversation_id   # 当前会话 UUID
ctx.agent_id          # 当前 agent UUID
ctx.session           # Session 对象（用于追加消息等）
ctx.db                # SQLAlchemy session（DB 读写）
ctx.oss_service       # OSS 上传 / 下载
ctx.llm_gateway       # LLM 调用（高级用法：嵌套 LLM）
ctx.event_emitter     # 事件发射器（推进度等）
ctx.quota_service     # quota 校验
ctx.trace_recorder    # TraceRecorder（自定义 trace step）
ctx.cancel_event      # asyncio.Event（协作式取消）
ctx.tool_state        # Dict（工具自身持久化状态）
```

**注意**：

- `ctx.db` 不保证非 None；BuiltinTool 应做 `if ctx.db is None: return ToolResult.error(...)` 防御（参考 `db_query.py:359`）
- `ctx.session` 在 ToolProtocol 中以 `Optional` 形式存在，避免循环导入

## 3. BuiltinTool 开发

### 3.1 模板

完整模板参考 `backend/app/services/harness/tools/builtin/base.py`：

```python
from app.services.harness.tool_protocol import ToolContext, ToolResult, ToolEvent
from app.services.harness.tools.builtin.base import BuiltinTool


class MyTool(BuiltinTool):
    """一句话描述工具能力（供 LLM 决定何时调用）"""

    name = "my_tool"                       # 唯一，全局不重复
    display_name = "我的工具"              # 前端展示
    description = (
        "执行某操作，返回结果。"
        "使用场景：..."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "查询关键词"},
            "max_results": {
                "type": "integer",
                "description": "最大结果数",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["query"],
    }
    returns_schema = {                      # 可选
        "type": "object",
        "properties": {
            "results": {"type": "array", "items": {"type": "object"}},
        },
    }

    def __init__(self, config: dict = None):
        super().__init__(config)           # 必须调用父类
        # 自定义初始化（读取 config 等）
        self.api_key = (config or {}).get("api_key", "")

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        # 1. 参数校验
        query = args.get("query", "").strip()
        if not query:
            return ToolResult.error("query 不能为空")

        # 2. 业务逻辑
        try:
            data = await self._fetch_data(query)
        except Exception as e:
            logger.exception("MyTool 调用失败: %s", e)
            return ToolResult.error("工具执行失败，请稍后重试")  # 通用提示，不暴露内部异常

        # 3. 返回结果
        return ToolResult.json(
            {"results": data},
            metadata={"source": "my_api", "duration_ms": 123},
        )

    async def _fetch_data(self, query: str) -> list:
        # 实际网络请求或 DB 查询
        ...
```

### 3.2 生命周期（默认 no-op）

```python
async def initialize(self) -> None:
    """应用启动时调用，可建立长连接 / 预热缓存"""

async def shutdown(self) -> None:
    """应用关闭时调用，清理资源"""
```

基类默认实现是 no-op，子类按需重写。

### 3.3 可用性判断

```python
def is_available(self, ctx: ToolContext) -> bool:
    """根据当前上下文判断工具是否可用

    典型场景：
    - WebSearchTool 总返回 True
    - DbQueryTool 检查 ctx.db 是否可用
    - 配额耗尽时返回 False
    """
    return True
```

### 3.4 流式输出

默认实现（`base.py:66`）把 `execute()` 的结果包装为单个 `result` 事件。如需流式进度（如图像生成、长时间批处理），重写 `execute_stream`：

```python
async def execute_stream(self, args: dict, ctx: ToolContext):
    for progress in self._long_running(args):
        yield ToolEvent(type="progress", payload={"percent": progress})
    result = await self.execute(args, ctx)
    yield ToolEvent(type="result", payload=result)
```

`ToolEvent` 字段：`type: "progress" | "result" | "error" | "log"`，`payload: Any`，`timestamp: float`。

### 3.5 注册到 ToolRegistry

**当前内置工具在 `app/api/routes/admin_tools.py:63` 的 `_get_builtin_tools()` 函数中硬编码列表**：

```python
def _get_builtin_tools():
    from app.services.harness.tools.builtin.web_search import WebSearchTool
    from app.services.harness.tools.builtin.db_query import DbQueryTool
    return [WebSearchTool(), DbQueryTool()]
```

**新增 BuiltinTool 的步骤**：

1. 在 `backend/app/services/harness/tools/builtin/` 下创建 `my_tool.py`
2. 在 `app/api/routes/admin_tools.py:63` 的 `_get_builtin_tools()` 中加入新工具的 import 和实例化
3. ToolRegistry 通过 `_get_builtin_tools()` 在 `GET /api/v1/admin/tools/builtin` 端点暴露（`admin_tools.py:90+`）

> **未来优化方向**：改为通过 `setup.py` 的 entry_points 或 `tools/builtin/__init__.py` 自动注册，避免每次新增都要改 admin_tools.py。

### 3.6 完整示例：参考 DbQueryTool

`backend/app/services/harness/tools/builtin/db_query.py` 是一个生产级 BuiltinTool 示例，包含：

- 类属性元数据（`name` / `display_name` / `description` / `parameters_schema` / `returns_schema`）
- 构造函数注入配置（`allowed_schemas` / `allowed_tables` / `blocked_tables`）
- 多层安全校验（关键词 + sqlparse 解析 + 表级别访问控制 + 行数限制）
- 异常处理 + 日志脱敏（详细 traceback 写日志，LLM 只看到通用提示）

### 3.7 BuiltinTool 测试

参考 `backend/tests/harness/test_db_query_tool.py` 和 `test_web_search_tool.py`：

- 元数据测试：`test_xxx_metadata()` 验证 name / display_name / parameters_schema
- function schema 测试：`test_xxx_function_schema()` 验证 `to_function_schema()` 返回格式
- 业务逻辑测试：每个分支一个用例
- 安全测试：恶意输入（SQL 注入、javascript URL、控制字符等）

`BuiltinTool.is_available()` 的测试模式：

```python
def test_my_tool_is_always_available():
    tool = MyTool()
    ctx = ToolContext(user_id="u1", conversation_id="c1", agent_id="a1")
    assert tool.is_available(ctx) is True
```

## 4. HttpTool 配置（无需写代码）

HttpTool 由 admin 通过 `POST /api/v1/admin/tools` 注册到 DB（`backend/app/services/harness/tools/builtin/http_tool.py` 动态构造）。

### 4.1 Config 字段

```json
{
  "url": "https://api.example.com/search?q={{args.query}}",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer {{secrets.API_TOKEN}}",
    "X-User": "{{ctx.user_id}}"
  },
  "body_template": {
    "query": "{{args.query}}",
    "limit": "{{args.limit}}",
    "timestamp": "{{timestamp}}"
  },
  "response_parser": {
    "result_path": "$.data.results",
    "error_path": "$.error.message"
  },
  "timeout": 30
}
```

### 4.2 模板变量

支持的变量（`http_tool.py:296` `_render_string()`）：

| 语法 | 含义 | 示例 |
|------|------|------|
| `{{args.xxx}}` | LLM 传入的工具参数 | `{{args.city}}` |
| `{{ctx.user_id}}` | 当前用户 ID | `{{ctx.user_id}}` |
| `{{ctx.conversation_id}}` | 当前会话 ID | `{{ctx.conversation_id}}` |
| `{{ctx.agent_id}}` | 当前 Agent ID | `{{ctx.agent_id}}` |
| `{{secrets.XXX}}` | 从环境变量读取密钥 | `{{secrets.OPENAI_API_KEY}}` |
| `{{timestamp}}` | 当前 Unix 时间戳 | `{{timestamp}}` |

**沙箱**：仅以上白名单变量可解析，其他 `{{...}}` 会被替换为空字符串。参考测试 `test_http_tool.py::test_http_tool_template_rendering_*`。

### 4.3 Response Parser

简化版 JSONPath：

- `result_path`：从响应中提取最终结果，传给 LLM
- `error_path`：错误时提取错误消息

支持语法：`$.a.b.c` 或 `$.a[0].b`。不支持通配符 / 过滤 / 递归。

参考实现：`http_tool.py:401` `_extract_by_path()` 和 `test_http_tool.py::test_extract_by_path_*`。

### 4.4 Method 与 Body

- `method`：`GET` / `POST` / `PUT` / `PATCH`，默认 `GET`
- `body_template`：dict / list / str，非空且 method 为 POST/PUT/PATCH 时作为 JSON body 发送（`http_tool.py:251` `client.stream(json=body)`）

### 4.5 完整配置示例：天气查询

参考 `docs/harness/phase1-testing.md` §3.4 的 weather_lookup 例子。

## 5. 工具安全

### 5.1 SSRF 防护（HttpTool）

`http_tool.py:38` `_BLOCKED_NETWORKS` 拒绝以下网段：

| 网段 | 用途 |
|------|------|
| `10.0.0.0/8` | IPv4 私网 |
| `172.16.0.0/12` | IPv4 私网 |
| `192.168.0.0/16` | IPv4 私网 |
| `127.0.0.0/8` | IPv4 环回 |
| `169.254.0.0/16` | 云元数据服务（AWS / 阿里云） |
| `::1/128` | IPv6 环回 |
| `fe80::/10` | IPv6 链路本地 |
| `fc00::/7` | IPv6 唯一本地（ULA） |
| `::ffff:0:0/96` | IPv4 映射 IPv6（提取嵌入 IPv4 检查） |

**双层防护**：

1. **Admin 端**：`admin_tools.py:53` `_validate_http_config()` 仅接受 `http://` 或 `https://` scheme（不接 ftp / file / gopher 等）
2. **执行端**：`http_tool.py:333` `_is_url_safe()`：
   - IP 字面量直接检查
   - hostname 通过 `socket.getaddrinfo()` 解析所有地址族（IPv4 + IPv6）
   - IPv4 映射的 IPv6（`::ffff:127.0.0.1`）会解出嵌入的 IPv4 再检查
   - TOCTOU 防护：DNS 解析一次后用已校验 IP 直连，`Host` 头保留原始 hostname 支持虚拟主机

**重定向防护**：`http_tool.py:160` 手动跟随重定向（最多 10 次），每一跳都重新校验 `_is_url_safe()`，禁用 `httpx` 自动 follow。

**测试覆盖**：

- `test_http_tool.py::test_http_tool_rejects_localhost`
- `test_http_tool.py::test_http_tool_rejects_private_*`
- `test_http_tool.py::test_is_url_safe_blocks_ipv6_*`
- `test_http_tool.py::test_is_url_safe_blocks_ipv4_mapped_ipv6*`

### 5.2 响应大小限制（DoS 防护）

`http_tool.py:53` `_MAX_RESPONSE_SIZE = 1024 * 1024`（1 MB）。

`_stream_request()`：

1. 先检查 `Content-Length` 头（`http_tool.py:258`），超出立即返回 error
2. 流式下载 + 增量大小校验（`http_tool.py:271`），超出立即中止

**注意**：实际可配置为 agent 级参数（不在 Phase 1 实现）。

### 5.3 模板变量沙箱

仅白名单变量可解析（`http_tool.py:317` `_resolve_variable()`）：

```python
if key.startswith("args."): ...
if key.startswith("ctx."): ...
if key.startswith("secrets."): ...
if key == "timestamp": ...
return ""  # 其他 key 返回空字符串，不抛异常
```

这样即使 admin 误配置 `{{evil.path}}` 也不会泄露敏感数据。

### 5.4 异常信息脱敏

参考 `web_search.py:145-148` 的模式：

```python
except Exception as e:
    logger.exception("WebSearchTool 搜索失败: %s", e)  # 详细 traceback 进日志
    return ToolResult.error("搜索失败，请稍后重试")  # 通用提示给 LLM
```

**不要**直接把 `str(e)` 暴露给 LLM，因为：

- 异常消息可能含 stack frame / 内部路径 / SQL 语句 / 密钥
- LLM 可能利用这些信息构造 prompt injection 或泄漏到用户响应

### 5.5 Prompt Injection 防护（BuiltinTool 返回数据时）

当工具返回的文本会进入 LLM 上下文，需做转义：

- `web_search.py:44` `_sanitize_text()`：HTML 实体解码 → 控制字符剥离 → Markdown 转义 → 长度截断
- `web_search.py:64` `_sanitize_url()`：仅接受 http/https scheme，拒绝 javascript: / data: / vbscript: / 空 host

参考测试：

- `test_web_search_tool.py::test_parse_ddg_html_drops_javascript_url`
- `test_web_search_tool.py::test_parse_ddg_html_escapes_markdown_special_chars`
- `test_web_search_tool.py::test_parse_ddg_html_truncates_long_title`

### 5.6 DbQueryTool SQL 安全

`backend/app/services/harness/tools/builtin/db_query.py` 是 SQL 注入防护的参考实现：

1. **`_WRITE_KEYWORDS`**：正则第一道防线，阻止 INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE
2. **`_DANGEROUS_FUNCTIONS`**：阻止 `dblink_exec` / `lo_import` / `pg_read_file` / `lo_export` 等危险 PostgreSQL 函数（即使在 SELECT 里）
3. **`_INTO_PATTERN`**：阻止 `SELECT INTO` / `INSERT INTO ... SELECT` 绕过
4. **`_COPY_PATTERN`**：阻止 COPY 语句
5. **`_validate_sql_select_only`**：用 `sqlparse` 二次解析，确保类型是 `SELECT` 或 `WITH`
6. **`_check_table_access`**：表级别 allowlist / blocklist

> **重要**：DbQueryTool 仍应部署在只读 PostgreSQL 用户下，表级别控制是**额外防线**，不能替代数据库权限。

## 6. 鉴权与绑定

### 6.1 Agent 工具可用性

`ToolRegistry.get_tools_for_agent()`（`tool_registry.py:61`）：

1. 内置工具（builtin）默认对所有 agent 可用（按 `is_available(ctx)` 过滤）
2. 显式绑定的工具（`ToolBinding` 表）按 binding 配置
3. 绑定工具与内置工具重名时，绑定覆盖内置

### 6.2 工具调用鉴权

`ToolRegistry.execute()`（`tool_registry.py:103`）：

1. 查找工具实例
2. **鉴权**：校验工具是否在当前 agent 的允许列表中（防止 LLM 幻觉调用未授权工具）
3. 调用 `tool.execute(args, ctx)`
4. 捕获异常，返回 `ToolResult.error`

**鉴权失败**：返回 `ToolResult.error("工具 {name} 未被授权给当前 agent")`，不抛异常。

### 6.3 工具绑定 API

- `GET /api/v1/admin/agents/{id}/tool-bindings` 列表
- `POST /api/v1/admin/agents/{id}/tool-bindings` 创建（priority / is_enabled）
- `DELETE /api/v1/admin/agents/{id}/tool-bindings/{binding_id}` 删除

参考 `backend/app/api/routes/admin_agents.py` 和 `backend/tests/harness/test_admin_agents_api.py`。

## 7. 工具开发流程总结

### 7.1 BuiltinTool 新增流程

1. 在 `backend/app/services/harness/tools/builtin/` 创建 `<name>.py`
2. 实现 BuiltinTool 子类（参见 §3.1）
3. 在 `backend/app/api/routes/admin_tools.py:63` `_get_builtin_tools()` 中加入
4. 在 `backend/tests/harness/` 下创建 `test_<name>.py`
5. 运行 `python -m pytest tests/harness/test_<name>.py -v` 验证
6. 重启后端：`python dev-services.py restart backend`
7. 手动验证：`GET /api/v1/admin/tools/builtin` 应列出新工具
8. 创建一个测试 agent，绑定新工具，发起对话验证

### 7.2 HttpTool 新增流程

1. 进入「管理后台」→「Tools」→「Create Tool」
2. 填 name / display_name / description / parameters_schema
3. 填 config（url / method / headers / body_template / response_parser / timeout）
4. 验证 schema：`POST /api/v1/admin/tools` 返回 201
5. 绑定到目标 agent（POST `/api/v1/admin/agents/{id}/tool-bindings`）
6. 发起对话测试
7. 可选：在 `backend/tests/harness/test_http_tool.py` 中增加特定模板渲染场景的单元测试

## 8. 故障排查

| 现象 | 可能原因 | 排查方法 |
|------|----------|----------|
| LLM 不调用工具 | `description` 不够清晰 / `parameters_schema` 缺 `required` | 检查 `to_function_schema()` 输出 |
| 工具返回 401/403 | agent 未绑定 / 鉴权失败 | 看 `ToolRegistry` 日志：工具 `{name}` 未被授权给当前 agent |
| HTTP 工具调用 SSRF 拒绝 | URL 命中内网 | 看 `http_tool.py` 日志：URL 不安全（SSRF 防护） |
| 模板变量未替换 | 变量拼写错误 / 不在白名单 | 用 `{{args.xxx}}` 严格匹配 `parameters_schema.properties.xxx` |
| Body 不发送 | method 是 GET | 仅 POST/PUT/PATCH 会发 body（`http_tool.py:255`） |
| 响应过大 | > 1MB | `_MAX_RESPONSE_SIZE` 限制 |
| 工具返回 error 但 LLM 不显示 | `to_llm_text()` 输出空 | 检查 `ToolResult.content_type`，error 会变成 `[error: ...]` |
| WebSearch 返回 0 结果 | DuckDuckGo HTML 改版 | 更新 `_parse_ddg_html()` 的 CSS 选择器 |

## 9. 参考资料

- `backend/app/services/harness/tool_protocol.py` — ToolProtocol + ToolResult + ToolContext 定义
- `backend/app/services/harness/tools/builtin/base.py` — BuiltinTool 基类
- `backend/app/services/harness/tools/builtin/db_query.py` — 复杂 BuiltinTool 示例（SQL 安全）
- `backend/app/services/harness/tools/builtin/web_search.py` — 简单 BuiltinTool 示例（HTML 解析 + sanitize）
- `backend/app/services/harness/tools/builtin/http_tool.py` — HttpTool 实现（SSRF + 模板沙箱 + 响应大小）
- `backend/app/services/harness/tool_registry.py` — ToolRegistry 生命周期 / 鉴权
- `backend/app/api/routes/admin_tools.py` — admin/tools API（含 SSRF 前置校验）
- `backend/tests/harness/test_http_tool.py` — HttpTool 全部测试用例（SSRF / 模板渲染 / 响应解析）
- `backend/tests/harness/test_web_search_tool.py` — WebSearchTool 全部测试用例
- `backend/tests/harness/test_db_query_tool.py` — DbQueryTool 测试
- `docs/harness/phase1-testing.md` — Phase 1 测试指南（自动化 + 手动 E2E）
