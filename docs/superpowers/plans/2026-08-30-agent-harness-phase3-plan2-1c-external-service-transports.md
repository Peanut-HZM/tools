# P2-①c 外部服务插件（stdio + streamable HTTP transport）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MCP 外部服务补齐 stdio（本地进程）与 streamable HTTP 两种 transport，SSE 保持不变，使 admin 可接入三种形态的外部服务。

**Architecture:** 只重构连接层——`McpClient.connect()` 按 `transport` 分发到 `sse_client` / `streamable_http_client` / `stdio_client`，握手后的 `ClientSession`、`tools_list`、`tools_call`、`McpTool`、`ToolRegistry` 全部复用零改动。DB 加 1 个 nullable 列 `command_json` 存 stdio 启动配置。

**Tech Stack:** Python 3.10 / FastAPI / SQLAlchemy + Alembic / mcp SDK 2.1.1（`stdio_client`、`streamable_http_client`） / React 18 + TypeScript

## Global Constraints

- 所有代码注释使用中文（AGENTS.md §1.2）
- 后端关键节点必须有日志（AGENTS.md §3.1）
- 零破坏：新列 nullable、新 schema 字段可选、API 不删不改已有字段语义；已有 SSE server 行为完全不变
- stdio 安全模型：仅 admin API 可配（已有 `require_admin`）；env 默认最小集（`get_default_environment()`），显式 env 追加其上；日志不打印 env 值
- `http` transport 复用现有 `validate_url` SSRF 防护（含云元数据永久拒绝）；`stdio` 跳过 URL 校验
- update 接口不允许修改 `transport`（与现状一致）
- 验证命令：`cd backend && .venv/Scripts/python -m pytest tests/harness -x -q`；`cd backend && .venv/Scripts/python -m ruff check app tests`；前端 `cd frontend && npm run build`
- 每个 Task 结束单独 commit（TDD：先测试后实现）

---

### Task 1: DB 模型 + Alembic migration（command_json 列）

**Files:**
- Modify: `backend/app/models/mcp_server.py`
- Create: `backend/alembic/versions/20260830a_add_command_json_to_mcp_servers.py`
- Test: `backend/tests/harness/test_models.py`（追加用例）

**Interfaces:**
- Consumes: `McpServer` ORM（现有）
- Produces: `McpServer.command_json: str | None`（Text 列，JSON 字符串 `{"command": str, "args": [str], "env": {str: str}}`）；migration revision `20260830a`，`down_revision = "20260829c"`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/harness/test_models.py` 末尾追加：

```python
def test_mcp_server_command_json_column():
    """P2-①c: mcp_servers 表应有 command_json 列（stdio 启动配置）"""
    from app.models.mcp_server import McpServer

    server = McpServer(name="t", server_url="npx -y demo", transport="stdio")
    assert server.command_json is None  # 新列 nullable，默认 None
    server.command_json = '{"command": "npx", "args": ["-y", "demo"]}'
    assert '"command"' in server.command_json
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_models.py::test_mcp_server_command_json_column -v`
Expected: FAIL（AttributeError: command_json）

- [ ] **Step 3: 模型加列**

`backend/app/models/mcp_server.py` 在 `timeout_seconds` 列后加：

```python
    # P2-①c: stdio transport 启动配置（JSON 字符串）：
    # {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"], "env": {"K": "V"}}
    # sse / http transport 时为 NULL
    command_json = Column(Text, nullable=True)
```

- [ ] **Step 4: 创建 migration**

新建 `backend/alembic/versions/20260830a_add_command_json_to_mcp_servers.py`：

```python
"""P2-①c 外部服务插件 — mcp_servers 增加 command_json 列

stdio transport 启动配置（JSON 字符串）。迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260830a"
down_revision = "20260829c"  # 接 checkpoint 时间旅行迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE mcp_servers
        ADD COLUMN IF NOT EXISTS command_json TEXT
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE mcp_servers
        DROP COLUMN IF EXISTS command_json
        """
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_models.py -v`
Expected: PASS（含新用例）

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/mcp_server.py backend/alembic/versions/20260830a_add_command_json_to_mcp_servers.py backend/tests/harness/test_models.py
git commit -m "feat(harness): add command_json column to mcp_servers for stdio transport"
```

---

### Task 2: McpClient 三 transport 分发（核心）

**Files:**
- Modify: `backend/app/services/harness/mcp_client.py`
- Create: `backend/tests/harness/test_mcp_client_transports.py`

**Interfaces:**
- Consumes: mcp SDK `sse_client`（现有）、`streamable_http_client`、`stdio_client`、`StdioServerParameters`、`get_default_environment`（均来自 `mcp.client.*`）
- Produces: `McpClient(server_url="", *, transport: str = "sse", command: dict | str | None = None, headers=None, timeout=30, allow_private_hosts=False)`；新属性 `transport`；`connect()` 按 transport 分发；`disconnect()` 统一退出 `_transport_ctx`；非法 command 抛 `McpConnectionError`。**注意**：位置参数 `server_url` 与全部现有参数保持兼容（现有测试 `McpClient(server_url=..., allow_private_hosts=True)` 不改）

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/harness/test_mcp_client_transports.py`：

```python
"""McpClient 多 transport 单元测试（P2-①c）

mock 各 transport context manager，验证 connect() 分发正确、
stdio 参数构建正确、SSRF 校验只对 url 型 transport 生效。
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.harness.mcp_client import McpClient, McpConnectionError


@pytest.mark.asyncio
async def test_sse_uses_sse_client():
    """transport=sse（默认）→ 走 sse_client"""
    client = McpClient("http://localhost:3000", allow_private_hosts=True)
    with patch("app.services.harness.mcp_client.sse_client") as mock_sse:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_sse.return_value = cm
        with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.connect()
    mock_sse.assert_called_once()
    assert client.transport == "sse"


@pytest.mark.asyncio
async def test_http_uses_streamable_client():
    """transport=http → 走 streamable_http_client；3 元组适配为 (read, write)"""
    client = McpClient(
        "http://localhost:3000", transport="http", allow_private_hosts=True
    )
    with patch(
        "app.services.harness.mcp_client.streamable_http_client"
    ) as mock_http:
        cm = MagicMock()
        # streamable http 产出 3 元组 (read, write, get_session_id)
        cm.__aenter__ = AsyncMock(
            return_value=(MagicMock(), MagicMock(), MagicMock())
        )
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = cm
        with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.connect()
    mock_http.assert_called_once()
    assert client.transport == "http"


@pytest.mark.asyncio
async def test_stdio_uses_stdio_client():
    """transport=stdio → 走 stdio_client，StdioServerParameters 参数正确"""
    client = McpClient(
        "npx -y @modelcontextprotocol/server-everything",
        transport="stdio",
        command={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"], "env": {"FOO": "bar"}},
    )
    with patch("app.services.harness.mcp_client.stdio_client") as mock_stdio:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_stdio.return_value = cm
        with patch("app.services.harness.mcp_client.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.connect()
    mock_stdio.assert_called_once()
    params = mock_stdio.call_args[0][0]
    assert params.command == "npx"
    assert params.args == ["-y", "@modelcontextprotocol/server-everything"]
    # 显式 env 应叠加在 SDK 默认最小环境之上
    assert params.env["FOO"] == "bar"
    assert "PATH" in params.env


def test_stdio_skips_url_validation():
    """stdio 不做 SSRF URL 校验（server_url 仅展示用）"""
    # 若误走 validate_url 会抛 McpConnectionError；不抛即通过
    McpClient("任何展示字符串", transport="stdio", command={"command": "npx"})


def test_http_validates_url():
    """http transport 走 SSRF 校验：内网默认拒绝"""
    with pytest.raises(McpConnectionError):
        McpClient("http://192.168.1.1:3000", transport="http")


def test_stdio_command_required():
    """stdio 缺 command 配置 → McpConnectionError"""
    with pytest.raises(McpConnectionError):
        McpClient("demo", transport="stdio", command=None)
    with pytest.raises(McpConnectionError):
        McpClient("demo", transport="stdio", command={"args": ["a"]})


def test_stdio_accepts_command_json_string():
    """command 也可传 JSON 字符串（与 DB 存储格式对齐）"""
    client = McpClient(
        "demo",
        transport="stdio",
        command=json.dumps({"command": "python", "args": ["-m", "demo"]}),
    )
    assert client._server_params.command == "python"


def test_unsupported_transport_rejected():
    """非法 transport → McpConnectionError"""
    with pytest.raises(McpConnectionError):
        McpClient("http://localhost:3000", transport="grpc", allow_private_hosts=True)


@pytest.mark.asyncio
async def test_disconnect_exits_transport_ctx():
    """disconnect 应统一退出 _transport_ctx"""
    client = McpClient("http://localhost:3000", allow_private_hosts=True)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    cm.__aexit__ = AsyncMock(return_value=False)
    client._transport_ctx = cm
    client._session = AsyncMock()
    await client.disconnect()
    cm.__aexit__.assert_called_once()
    assert client._transport_ctx is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_mcp_client_transports.py -v`
Expected: FAIL（`McpClient.__init__` 无 `transport`/`command` 参数 → TypeError）

- [ ] **Step 3: 实现 transport 分发**

修改 `backend/app/services/harness/mcp_client.py`：

3.1 顶部 import 区（SDK import 块）改为：

```python
try:
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client, StdioServerParameters, get_default_environment
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession
except ImportError:
    raise ImportError(
        "mcp package not installed. Run: pip install mcp>=1.0.0"
    )
```

3.2 `__init__` 整体替换为：

```python
    def __init__(
        self,
        server_url: str = "",
        *,
        transport: str = "sse",
        command: dict | str | None = None,
        headers: dict | None = None,
        timeout: int = 30,
        allow_private_hosts: bool = False,
    ):
        """
        Args:
            server_url: SSE / streamable HTTP 端点；stdio 时仅作展示摘要
            transport: "sse" / "http" / "stdio"（P2-①c）
            command: stdio 启动配置 dict 或 JSON 字符串：
                {"command": "npx", "args": [...], "env": {...}}
            headers: 可选的 HTTP headers（如 Authorization），仅 url 型 transport
            timeout: 操作超时秒数
            allow_private_hosts: True 则允许内网地址（仅开发/测试用）
        """
        if transport not in ("sse", "http", "stdio"):
            raise McpConnectionError(f"Unsupported transport: {transport}")

        if transport == "stdio":
            # stdio 无 URL 语义，跳过 SSRF 校验；本地代码执行风险由 admin 门禁覆盖
            self._server_params = self._build_stdio_params(command)
        else:
            # SSRF 防护：在连接前验证 URL（sse / http 共用）
            validate_url(server_url, allow_private_hosts=allow_private_hosts)

        self.server_url = server_url
        self.transport = transport
        self.headers = headers or {}
        self.timeout = timeout
        self.allow_private_hosts = allow_private_hosts  # 保留供调用方检查
        self._session: ClientSession | None = None
        self._transport_ctx = None  # 统一持有当前 transport 的 async context manager

    @staticmethod
    def _build_stdio_params(command: dict | str | None) -> StdioServerParameters:
        """构建 stdio 启动参数。

        env 策略（安全）：默认使用 SDK 最小环境（get_default_environment()，
        只含 PATH/HOME 等基础变量），显式配置的 env 追加其上——
        不透传后端进程完整环境，防止 secrets 泄露给子进程。
        """
        if isinstance(command, str):
            try:
                command = json.loads(command)
            except json.JSONDecodeError as e:
                raise McpConnectionError(f"Invalid command JSON: {e}") from e
        if not isinstance(command, dict) or not str(command.get("command") or "").strip():
            raise McpConnectionError(
                'stdio transport requires command config: {"command": "...", "args": [...], "env": {...}}'
            )
        env = None
        if command.get("env"):
            env = get_default_environment()
            env.update(command["env"])
        return StdioServerParameters(
            command=command["command"],
            args=list(command.get("args") or []),
            env=env,
        )
```

3.3 连接方法区整体替换（`_connect_sse` 保留名称、新增两个私有方法；`connect` 分发；`disconnect` 用 `_transport_ctx`）：

```python
    async def _connect_sse(self):
        """内部方法：建立 SSE 连接，返回 (read_stream, write_stream)"""
        self._transport_ctx = sse_client(self.server_url, headers=self.headers)
        read_stream, write_stream = await self._transport_ctx.__aenter__()
        return read_stream, write_stream

    async def _connect_streamable_http(self):
        """内部方法：建立 streamable HTTP 连接，返回 (read_stream, write_stream)

        streamable_http_client 产出 (read, write, get_session_id) 三元组，
        ClientSession 只需前两项。
        """
        self._transport_ctx = streamable_http_client(
            self.server_url, headers=self.headers
        )
        streams = await self._transport_ctx.__aenter__()
        return streams[0], streams[1]

    async def _connect_stdio(self):
        """内部方法：spawn stdio 子进程并接入，返回 (read_stream, write_stream)"""
        self._transport_ctx = stdio_client(self._server_params)
        read_stream, write_stream = await self._transport_ctx.__aenter__()
        return read_stream, write_stream

    async def connect(self) -> None:
        """建立连接并完成 MCP 握手（按 transport 分发）"""
        safe_url = sanitize_url(self.server_url)
        connectors = {
            "sse": self._connect_sse,
            "http": self._connect_streamable_http,
            "stdio": self._connect_stdio,
        }
        try:
            read_stream, write_stream = await connectors[self.transport]()

            # 创建 ClientSession 并初始化
            self._session = ClientSession(read_stream, write_stream)
            await asyncio.wait_for(
                self._session.initialize(),
                timeout=self.timeout,
            )

            logger.info(
                f"MCP client connected to {safe_url} (transport={self.transport})"
            )
        except asyncio.TimeoutError:
            await self.disconnect()
            raise McpConnectionError(f"Connection timeout after {self.timeout}s")
        except McpConnectionError:
            raise
        except Exception as e:
            await self.disconnect()
            logger.error(
                "MCP connection failed to %s (transport=%s): %s",
                safe_url,
                self.transport,
                type(e).__name__,
            )
            raise McpConnectionError(f"Connection failed: {type(e).__name__}") from e
```

3.4 `disconnect()` 中 `self._sse_context` 相关段替换为：

```python
        if self._transport_ctx:
            try:
                await self._transport_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing transport context: %s", type(e).__name__)
            self._transport_ctx = None
```

注意：文件头部需补 `import json`（stdlib 区）。保留模块内 `sanitize_url`、`validate_url` 及全部 SSRF 代码不动。

- [ ] **Step 4: 运行新测试 + 旧 SSE 回归**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_mcp_client_transports.py tests/harness/test_mcp_client.py tests/harness/test_mcp_client_security.py -v`
Expected: 全部 PASS（SSE 行为零变化；若旧测试直接引用 `_sse_context` 属性则同步改为 `_transport_ctx`）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/mcp_client.py backend/tests/harness/test_mcp_client_transports.py
git commit -m "feat(harness): McpClient supports stdio + streamable HTTP transports"
```

---

### Task 3: stdio 真子进程端到端集成测试

**Files:**
- Create: `backend/tests/harness/test_mcp_stdio_integration.py`

**Interfaces:**
- Consumes: Task 2 的 `McpClient`；mcp SDK 服务端 `mcp.server.fastmcp.FastMCP`
- Produces: 真实 stdio 链路的回归保障（connect → tools_list → tools_call）

- [ ] **Step 1: 写集成测试**

新建 `backend/tests/harness/test_mcp_stdio_integration.py`：

```python
"""stdio transport 端到端集成测试（P2-①c）

用 sys.executable 启动真实 FastMCP 子进程，走完整 stdin/stdout 链路。
不 mock 任何 mcp 内部组件。
"""
import sys
import textwrap
from pathlib import Path

import pytest

from app.services.harness.mcp_client import McpClient, McpConnectionError

# 临时 MCP server 脚本：提供一个 echo 工具
_SERVER_SCRIPT = textwrap.dedent(
    """
    import sys
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("echo-server")

    @mcp.tool()
    def echo(text: str) -> str:
        \"\"\"Echo the input text back\"\"\"
        return f"echo: {text}"

    if __name__ == "__main__":
        mcp.run()  # 默认 stdio transport
    """
)


@pytest.fixture
async def echo_client(tmp_path):
    """启动真实 stdio echo server 并完成握手的 client"""
    script = tmp_path / "echo_server.py"
    script.write_text(_SERVER_SCRIPT, encoding="utf-8")
    client = McpClient(
        f"python {script}",
        transport="stdio",
        command={"command": sys.executable, "args": [str(script)]},
        timeout=60,
    )
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_stdio_end_to_end_tools_list(echo_client):
    """真实子进程：connect → tools_list 返回 echo 工具"""
    tools = await echo_client.tools_list()
    names = [t["name"] for t in tools]
    assert "echo" in names


@pytest.mark.asyncio
async def test_stdio_end_to_end_tools_call(echo_client):
    """真实子进程：tools_call 拿到真实返回值"""
    result = await echo_client.tools_call("echo", {"text": "hello"})
    assert result["isError"] is False
    assert any("echo: hello" in c.get("text", "") for c in result["content"])


@pytest.mark.asyncio
async def test_stdio_command_not_found():
    """command 指向不存在的可执行文件 → McpConnectionError"""
    client = McpClient(
        "no-such-binary-xyz",
        transport="stdio",
        command={"command": "no-such-binary-xyz-12345"},
        timeout=30,
    )
    with pytest.raises(McpConnectionError):
        await client.connect()
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_mcp_stdio_integration.py -v`
Expected: PASS（若 FastMCP.run 在 Windows 下需要 asyncio event loop 策略调整，按报错在 fixture 中补 `asyncio.run` 兼容；断言语义不变）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/harness/test_mcp_stdio_integration.py
git commit -m "test(harness): stdio transport end-to-end integration with real subprocess"
```

---

### Task 4: Schema + Admin API per-transport 校验

**Files:**
- Modify: `backend/app/schemas/mcp_server.py`
- Modify: `backend/app/api/routes/admin_mcp_servers.py`
- Create: `backend/tests/harness/test_admin_mcp_transports.py`

**Interfaces:**
- Consumes: Task 1 的 `McpServer.command_json`
- Produces: `McpServerCreate.transport: Literal["sse","http","stdio"]` + `command: dict | None`；`McpServerUpdate.command: dict | None`；`McpServerResponse.command_json: str | None`；路由层校验函数 `_validate_transport_config(transport, command)`（stdio 且无有效 command → HTTP 400）。语义约定：`sse`/`http` 时忽略 `command`；`stdio` 时 `headers` 照旧存储但连接时忽略；update 中 `command` 非 None 即整体替换（不支持清空，transport 切换走删除重建）

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/harness/test_admin_mcp_transports.py`：

```python
"""Admin MCP servers API 多 transport 校验测试（P2-①c）

使用 FastAPI TestClient + SQLite 内存库，admin 鉴权走依赖覆盖。
"""
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(test_db, monkeypatch):
    """TestClient + admin 鉴权覆盖 + registry 重置"""
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def _override_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "admin", "id": "u1"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_stdio_server_requires_command(client):
    """stdio 缺 command → 400"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s1", "server_url": "npx demo", "transport": "stdio"},
    )
    assert resp.status_code == 400


def test_create_stdio_server_accepted(client):
    """stdio + command → 201，command_json 落库"""
    cmd = {"command": "npx", "args": ["-y", "demo"], "env": {"K": "V"}}
    resp = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s2", "server_url": "npx demo", "transport": "stdio", "command": cmd},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["transport"] == "stdio"
    assert json.loads(resp.json()["command_json"]) == cmd


def test_create_http_server_accepted(client):
    """transport=http → 201（URL 安全校验在 connect 时做）"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s3", "server_url": "https://mcp.example.com/mcp", "transport": "http"},
    )
    assert resp.status_code == 201
    assert resp.json()["command_json"] is None


def test_create_invalid_transport_rejected(client):
    """transport=grpc → 422（Pydantic Literal 兜底）"""
    resp = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s4", "server_url": "x", "transport": "grpc"},
    )
    assert resp.status_code == 422


def test_update_command_replaces(client):
    """update command 非 None → 整体替换 command_json"""
    created = client.post(
        "/api/admin/mcp/servers",
        json={"name": "s5", "server_url": "npx demo", "transport": "stdio",
              "command": {"command": "npx"}},
    ).json()
    resp = client.put(
        f"/api/admin/mcp/servers/{created['id']}",
        json={"command": {"command": "node", "args": ["srv.js"]}},
    )
    assert resp.status_code == 200
    assert json.loads(resp.json()["command_json"]) == {"command": "node", "args": ["srv.js"]}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_admin_mcp_transports.py -v`
Expected: FAIL（transport=stdio 被 422 拒绝 / command_json 字段不存在）

- [ ] **Step 3: 修改 schema**

`backend/app/schemas/mcp_server.py`：

```python
class McpServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    server_url: str = Field(..., min_length=1, max_length=500)
    # P2-①c: 扩展 stdio / streamable http（原有 sse 保持不变）
    transport: Literal["sse", "http", "stdio"] = "sse"
    headers: Optional[dict[str, str]] = None
    # stdio 启动配置：{"command": str, "args": [str], "env": {str, str}}；sse/http 时忽略
    command: Optional[dict] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class McpServerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    server_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    headers: Optional[dict[str, str]] = None
    command: Optional[dict] = None  # 非 None 时整体替换 command_json
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    is_active: Optional[bool] = None
```

`McpServerResponse` 加：

```python
    command_json: Optional[str] = None
```

- [ ] **Step 4: 修改路由校验**

`backend/app/api/routes/admin_mcp_servers.py` 加共享校验函数（`require_admin` 之后）：

```python
def _validate_transport_config(transport: str, command: dict | None) -> None:
    """P2-①c: 按 transport 校验配置完整性。

    - sse / http：server_url 必填由 schema 保证；URL 安全校验在 connect 时做
    - stdio：command 必须为非空 dict 且含非空 command 键
    """
    if transport == "stdio":
        if not isinstance(command, dict) or not str(command.get("command") or "").strip():
            raise HTTPException(
                status_code=400,
                detail='stdio transport 需要 command 配置: {"command": "...", "args": [...], "env": {...}}',
            )
```

create_server 中构造 `McpServer` 前调用并落库：

```python
    _validate_transport_config(data.transport, data.command)

    server = McpServer(
        name=data.name,
        server_url=data.server_url,
        transport=data.transport,
        headers_json=json.dumps(data.headers) if data.headers else None,
        command_json=json.dumps(data.command, ensure_ascii=False)
        if data.transport == "stdio" and data.command
        else None,
        timeout_seconds=data.timeout_seconds,
    )
```

update_server 中 `if data.command is not None:` 分支：

```python
    if data.command is not None:
        # transport 不可改，仅当现存 server 是 stdio 时才允许替换 command
        if server.transport != "stdio":
            raise HTTPException(status_code=400, detail="仅 stdio 类型的 server 支持 command 配置")
        _validate_transport_config(server.transport, data.command)
        server.command_json = json.dumps(data.command, ensure_ascii=False)
```

两处变更点各补一行 INFO 日志（create/update 已有日志行内追加 transport 信息即可）。

- [ ] **Step 5: 运行新测试 + admin API 回归**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_admin_mcp_transports.py tests/harness/test_mcp_server_manager.py tests/harness/test_mcp_integration.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/mcp_server.py backend/app/api/routes/admin_mcp_servers.py backend/tests/harness/test_admin_mcp_transports.py
git commit -m "feat(harness): admin MCP API accepts stdio/http transports with per-transport validation"
```

---

### Task 5: McpServerManager 按 transport 构造 client

**Files:**
- Modify: `backend/app/services/harness/mcp_server_manager.py`
- Modify: `backend/tests/harness/test_mcp_server_manager.py`（追加用例）

**Interfaces:**
- Consumes: Task 2 `McpClient(transport=..., command=...)`；Task 1 `server.command_json`
- Produces: `sync_server` 对三种 transport 均可建立连接并注册工具（`McpTool` 命名空间 `mcp:{server_name}:{tool_name}` 不变）

- [ ] **Step 1: 写失败测试**

`backend/tests/harness/test_mcp_server_manager.py` 末尾追加：

```python
@pytest.mark.asyncio
async def test_get_or_create_client_per_transport(test_db):
    """P2-①c: manager 按 server.transport 构造对应 client"""
    from app.services.harness.mcp_server_manager import McpServerManager
    from app.services.harness.mcp_client import McpClient
    from app.models.mcp_server import McpServer
    import json as _json

    server = McpServer(
        name="stdio-srv",
        server_url="npx demo",
        transport="stdio",
        command_json=_json.dumps({"command": "npx", "args": ["demo"]}),
    )
    test_db.add(server)
    test_db.commit()
    test_db.refresh(server)

    manager = McpServerManager(tool_registry=object())
    client = manager._get_or_create_client(server)
    assert isinstance(client, McpClient)
    assert client.transport == "stdio"
    assert client._server_params.command == "npx"
    # 缓存命中：第二次拿同一实例
    assert manager._get_or_create_client(server) is client
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_mcp_server_manager.py -v`
Expected: FAIL（`McpClient` 不接受 transport 参数之外的用法报错 / transport 未透传）

- [ ] **Step 3: 实现**

`mcp_server_manager.py` 的 `_get_or_create_client` 中 client 构造段替换为：

```python
        command = None
        if server.command_json:
            try:
                command = json.loads(server.command_json)
            except json.JSONDecodeError:
                raise McpConnectionError(
                    f"Invalid command_json for server {server.name}"
                )

        allow_private = _is_allow_private_hosts_enabled()
        client = McpClient(
            server_url=server.server_url,
            transport=server.transport,
            command=command,
            headers=headers,
            timeout=server.timeout_seconds,
            allow_private_hosts=allow_private,
        )
```

并在 sync_server 的 `McpConnectionError` 分支确认 `last_error` 落库路径不变（无代码改动，仅确认）。

- [ ] **Step 4: 运行 manager 全部测试**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_mcp_server_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/mcp_server_manager.py backend/tests/harness/test_mcp_server_manager.py
git commit -m "feat(harness): McpServerManager builds transport-specific clients"
```

---

### Task 6: 前端 transport 选择器

**Files:**
- Modify: `frontend/src/api/mcpServersApi.ts`
- Modify: `frontend/src/components/Admin/McpServers/CreateDialog.tsx`
- Modify: `frontend/src/api/__tests__/mcpServersApi.test.ts`（如存在类型级用例则追加）

**Interfaces:**
- Consumes: Task 4 的 API 契约（`transport: "sse"|"http"|"stdio"`、`command`、`command_json`）
- Produces: `McpTransport` 联合类型；CreateDialog 按 transport 联动渲染 URL 输入 / command JSON 输入

- [ ] **Step 1: 更新 API 类型**

`mcpServersApi.ts`：

```typescript
export type McpTransport = 'sse' | 'http' | 'stdio';

export interface McpServer {
  // ...现有字段保持...
  transport: McpTransport;
  command_json?: string | null;
}

export interface McpServerCreate {
  // ...
  transport: McpTransport;
  command?: Record<string, unknown>;
}

export interface McpServerUpdate {
  // ...
  command?: Record<string, unknown>;
}
```

- [ ] **Step 2: CreateDialog 联动**

CreateDialog.tsx 关键改动（保持现有样式类与表单结构）：

1. 新增 state：`const [transport, setTransport] = useState<McpTransport>(server?.transport ?? 'sse');` 与 `const [commandText, setCommandText] = useState(() => { try { return server?.command_json ? JSON.stringify(JSON.parse(server.command_json), null, 2) : ''; } catch { return server?.command_json || ''; } });`
2. URL 输入区上方加 transport `<select>`（三个选项，中文标签：SSE（服务端事件流）/ Streamable HTTP / stdio（本地进程））；编辑模式禁用该 select（transport 不可改）
3. `transport !== 'stdio'` 时显示 Server URL 输入；`transport === 'stdio'` 时显示 command JSON textarea（placeholder `{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"]}`）
4. 校验逻辑：
   - 非 stdio：沿用现有 `!serverUrl.trim()` 必填校验
   - stdio：`commandText` 必须能 `JSON.parse` 为 object 且 `command` 键为非空字符串，否则 `setError('command 必须是含非空 "command" 键的 JSON object')`
5. 提交 payload：
   - 创建：`transport` + 按 transport 附 `server_url` 或 `command`
   - 编辑：不传 transport；`server.transport === 'stdio'` 时附 `command: parsedCommand`

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TS 错误

Run: `cd frontend && npx tsc --noEmit`（如项目有该脚本则以 `npm run type-check` 为准）
Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/mcpServersApi.ts frontend/src/components/Admin/McpServers/CreateDialog.tsx
git commit -m "feat(frontend): MCP server dialog supports stdio/http transports"
```

---

### Task 7: 全量回归 + 验收收尾

**Files:**
- Modify: `docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1c-external-service-transports-design.md`（状态行改为"已实现"）

- [ ] **Step 1: 后端全量回归**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness -q`
Expected: 全部 PASS，无新增 failure/error

- [ ] **Step 2: 代码规范**

Run: `cd backend && .venv/Scripts/python -m ruff check app/services/harness app/schemas app/api/routes/admin_mcp_servers.py tests/harness`
Expected: 无错误

- [ ] **Step 3: 前端构建终验**

Run: `cd frontend && npm run build`
Expected: 成功

- [ ] **Step 4: spec 状态更新 + 提交**

spec 状态行改为：`**状态**：已实现（2026-08-30）`，然后：

```bash
git add docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1c-external-service-transports-design.md
git commit -m "docs(harness): mark P2-①c external service transports as implemented"
```

---

## 验收标准（对照 spec §4）

1. `pytest tests/harness` 全绿：新 transport 单测 + 真子进程 stdio e2e + admin API 校验 + SSE 零回归
2. 前端 `npm run build` 通过；CreateDialog 可创建 stdio/http 类型 server
3. migration `20260830a` 幂等可重复执行
4. 已有 SSE server 的创建/测试/同步路径行为不变（现有测试不修改断言即通过）
