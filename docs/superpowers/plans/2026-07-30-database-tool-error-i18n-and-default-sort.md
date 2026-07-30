# 数据库工具：错误中文提示 & 默认排序 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为数据库工具页面添加连接错误中文提示和表数据默认排序功能。

**Architecture:** 后端新增 `db_error_mapper.py` 工具，对原始异常字符串做大小写不敏感的关键字匹配，提取 `error_code`；`ConnectionTestResult` 模型新增 `error_code` 字段；前端 i18n 维护错误码→中文映射表，各组件优先用 `error_code` 查找本地化文案。前端新增 `defaultSortResolver.ts` 纯函数，从表 schema 中推算默认排序字段，`TableDataViewer` 在 schema 加载后调用它预填 ORDER BY 输入框。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / Pydantic / React 18 / TypeScript / Vitest / i18n (自研)

## Global Constraints

- 所有对话、文档、注释、日志、提交信息使用中文
- 后端代码必须包含日志记录
- 前端 i18n：中文 key 在 `zh-CN.ts`，英文 key 在 `en-US.ts`，新增 key 两端同步
- 新增工具函数须有单元测试，覆盖主要分支
- 不改动已正常的业务逻辑（`query_table_data` SQL 拼接、`SQLExecutor`、`ResultViewer` 等）
- 字段名匹配大小写不敏感；输出使用数据库中原始列名
- `ConnectionTestResult.error_code` 为可选字段，向后兼容旧客户端

---

## Task 1: 后端错误分类映射器（TDD）

**Files:**
- Create: `backend/app/utils/db_error_mapper.py`
- Create: `backend/tests/test_db_error_mapper.py`

**Interfaces:**
- Produces: `map_connection_error(raw_error: str) -> tuple[str, str]` — 返回 `(error_code, zh_message)` 二元组
- error_code 取值范围：`CONNECTION_TIMEOUT | CONNECTION_REFUSED | HOST_NOT_FOUND | ACCESS_DENIED | DATABASE_NOT_FOUND | SSL_ERROR | TOO_MANY_CONNECTIONS | NETWORK_ERROR | UNKNOWN_ERROR`

- [ ] **Step 1: 编写失败测试**

创建 `backend/tests/test_db_error_mapper.py`：

```python
"""数据库连接错误中文映射单元测试"""
import pytest
from app.utils.db_error_mapper import map_connection_error


class TestMapConnectionError:
    """map_connection_error 各错误码的匹配测试"""

    def test_timeout_timed_out(self):
        code, msg = map_connection_error(
            "(pymysql.err.OperationalError) (2003, \"Can't connect to MySQL server on '10.0.0.1' (timed out)\")"
        )
        assert code == "CONNECTION_TIMEOUT"
        assert "超时" in msg

    def test_timeout_generic(self):
        code, _ = map_connection_error("connect_timeout expired")
        assert code == "CONNECTION_TIMEOUT"

    def test_connection_refused(self):
        code, msg = map_connection_error(
            "Connection refused (0x0000274D/10061)"
        )
        assert code == "CONNECTION_REFUSED"
        assert "拒绝" in msg

    def test_cant_connect(self):
        code, _ = map_connection_error(
            "Can't connect to MySQL server on 'localhost'"
        )
        assert code == "CONNECTION_REFUSED"

    def test_host_not_found(self):
        code, msg = map_connection_error(
            "Name or service not known"
        )
        assert code == "HOST_NOT_FOUND"
        assert "主机" in msg or "地址" in msg

    def test_host_not_found_getaddrinfo(self):
        code, _ = map_connection_error(
            "getaddrinfo failed: Temporary failure in name resolution"
        )
        assert code == "HOST_NOT_FOUND"

    def test_host_not_found_macos(self):
        code, _ = map_connection_error(
            "nodename nor servname provided, or not known"
        )
        assert code == "HOST_NOT_FOUND"

    def test_access_denied_mysql(self):
        code, msg = map_connection_error(
            "Access denied for user 'root'@'localhost' (using password: YES)"
        )
        assert code == "ACCESS_DENIED"
        assert "拒绝" in msg or "密码" in msg

    def test_access_denied_pg(self):
        code, _ = map_connection_error(
            'FATAL:  password authentication failed for user "postgres"'
        )
        assert code == "ACCESS_DENIED"

    def test_database_not_found(self):
        code, msg = map_connection_error(
            "Unknown database 'nonexistent_db'"
        )
        assert code == "DATABASE_NOT_FOUND"
        assert "不存在" in msg

    def test_database_not_found_pg(self):
        code, _ = map_connection_error(
            'database "nonexistent" does not exist'
        )
        assert code == "DATABASE_NOT_FOUND"

    def test_ssl_error(self):
        code, msg = map_connection_error(
            "SSL connection error: certificate verify failed"
        )
        assert code == "SSL_ERROR"
        assert "SSL" in msg or "证书" in msg

    def test_too_many_connections(self):
        code, _ = map_connection_error(
            "Too many connections (max_connections=100)"
        )
        assert code == "TOO_MANY_CONNECTIONS"

    def test_network_error_broken_pipe(self):
        code, msg = map_connection_error(
            "Broken pipe - server closed the connection unexpectedly"
        )
        # 注意："server closed" 应优先匹配 NETWORK_ERROR
        assert code == "NETWORK_ERROR"
        assert "网络" in msg or "连接" in msg

    def test_network_error_connection_lost(self):
        code, _ = map_connection_error(
            "Lost connection to MySQL server during query"
        )
        assert code == "NETWORK_ERROR"

    def test_network_error_connection_reset(self):
        code, _ = map_connection_error(
            "Connection reset by peer"
        )
        assert code == "NETWORK_ERROR"

    def test_unknown_error_fallback(self):
        code, msg = map_connection_error(
            "Some completely unknown error happened"
        )
        assert code == "UNKNOWN_ERROR"
        # UNKNOWN_ERROR 的 msg 使用原始错误字符串
        assert "Some completely unknown error happened" in msg

    def test_case_insensitive(self):
        """大小写不敏感"""
        code, _ = map_connection_error("CONNECTION REFUSED")
        assert code == "CONNECTION_REFUSED"

    def test_priority_timeout_before_network(self):
        """timeout 优先于 network_error（避免 'timeout' 被 network_error 的泛匹配吞掉）"""
        code, _ = map_connection_error(
            "Operation timed out after 30000 ms"
        )
        assert code == "CONNECTION_TIMEOUT"
```

- [ ] **Step 2: 运行测试确认失败**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_db_error_mapper.py -v
```
预期：FAIL — `ModuleNotFoundError: No module named 'app.utils.db_error_mapper'`

- [ ] **Step 3: 编写实现**

创建 `backend/app/utils/db_error_mapper.py`：

```python
"""数据库连接错误分类映射工具

将原始异常字符串映射为 (error_code, zh_message) 二元组，
供路由层和服务层复用，统一向前端传递结构化的错误信息。
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# 错误码 → 中文描述（兜底文案）
_ERROR_CODE_ZH: dict[str, str] = {
    "CONNECTION_TIMEOUT": "连接超时，请检查主机地址和端口是否正确，或网络是否可达",
    "CONNECTION_REFUSED": "连接被拒绝，目标服务器可能未启动或端口未监听",
    "HOST_NOT_FOUND": "无法解析主机地址，请检查主机名是否正确",
    "ACCESS_DENIED": "访问被拒绝，用户名或密码可能错误，或该用户无权连接此数据库",
    "DATABASE_NOT_FOUND": "指定的数据库不存在",
    "SSL_ERROR": "SSL/TLS 连接失败，请检查 SSL 配置或证书路径",
    "TOO_MANY_CONNECTIONS": "连接数过多，服务器已达最大连接数限制",
    "NETWORK_ERROR": "网络异常，连接中断或服务器关闭了连接",
    "UNKNOWN_ERROR": "连接失败",
}

# 按优先级排列（越具体的越靠前）。
# 每个条目：(error_code, [关键字列表])
# 匹配时对 raw_error 做大小写不敏感的关键字子串匹配，任一关键字命中即视为该错误码
_RULES: list[tuple[str, list[str]]] = [
    (
        "CONNECTION_TIMEOUT",
        ["timed out", "timeout", "connect_timeout", "operation timed out"],
    ),
    (
        "CONNECTION_REFUSED",
        ["connection refused", "actively refused", "can't connect", "cannot connect"],
    ),
    (
        "HOST_NOT_FOUND",
        [
            "name or service not known",
            "getaddrinfo failed",
            "nodename nor servname provided",
            "unknown host",
            "temporary failure in name resolution",
        ],
    ),
    (
        "ACCESS_DENIED",
        [
            "access denied",
            "authentication failed",
            "invalid credentials",
            "login failed",
            "password authentication failed",
            "using password",
        ],
    ),
    (
        "DATABASE_NOT_FOUND",
        [
            "unknown database",
            # 匹配 "database "xxx" does not exist" 或 "database xxx does not exist"
            r"database .+ does not exist",
        ],
    ),
    (
        "SSL_ERROR",
        ["ssl", "certificate verify failed", "tls"],
    ),
    (
        "TOO_MANY_CONNECTIONS",
        ["too many connections", "max_connections", "connection limit"],
    ),
    (
        "NETWORK_ERROR",
        [
            "connection lost",
            "broken pipe",
            "connection reset",
            "server closed",
            "lost connection",
            "econnreset",
            "econnrefused",
        ],
    ),
]

# 预编译正则（大小写不敏感）
_COMPILED_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    (code, [re.compile(kw, re.IGNORECASE) for kw in keywords])
    for code, keywords in _RULES
]


def map_connection_error(raw_error: str) -> Tuple[str, str]:
    """将原始异常字符串映射为 (error_code, zh_message)。

    匹配规则按优先级从上到下，首个命中即返回。
    全部未命中时返回 ("UNKNOWN_ERROR", 原始错误字符串)。
    """
    lowered = raw_error.lower()
    for code, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(lowered):
                return code, _ERROR_CODE_ZH[code]

    logger.debug("未匹配到已知错误模式，返回 UNKNOWN_ERROR: %s", raw_error[:200])
    return "UNKNOWN_ERROR", raw_error
```

- [ ] **Step 4: 运行测试确认通过**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_db_error_mapper.py -v
```
预期：全部 PASS（约 18 个测试）

- [ ] **Step 5: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/utils/db_error_mapper.py backend/tests/test_db_error_mapper.py
git commit -m "feat: 新增数据库连接错误分类映射工具"
```

---

## Task 2: 模型 & 服务层集成错误码

**Files:**
- Modify: `backend/app/models/database_tool_models.py:82-86`（`ConnectionTestResult`）
- Modify: `backend/app/services/database_tool_service.py:883-906`（`test_connection`）
- Modify: `backend/app/services/database_tool_service.py:909-962`（`test_connection_by_id`）

**Interfaces:**
- Consumes: `map_connection_error(raw_error: str) -> tuple[str, str]`（来自 Task 1）
- Produces: `ConnectionTestResult` 模型新增 `error_code: Optional[str] = None` 字段
- Produces: `test_connection` / `test_connection_by_id` 在失败时填充 `error_code` 和中文 `message`

- [ ] **Step 1: 给 ConnectionTestResult 添加 error_code 字段**

修改 `backend/app/models/database_tool_models.py`，在 `ConnectionTestResult` 中添加 `error_code` 字段：

```python
class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    error_code: Optional[str] = None   # 新增：错误分类码，供前端 i18n 精确匹配
    elapsed_ms: Optional[float] = None
    version: Optional[str] = None
```

- [ ] **Step 2: 修改 test_connection 使用错误映射**

修改 `backend/app/services/database_tool_service.py` 中 `test_connection` 的 except 分支（第 902-906 行附近）：

原来：
```python
except Exception as e:
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    return ConnectionTestResult(
        success=False, message=str(e), elapsed_ms=elapsed
    )
```

改为：
```python
except Exception as e:
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    error_code, zh_msg = map_connection_error(str(e))
    return ConnectionTestResult(
        success=False,
        message=zh_msg,
        error_code=error_code,
        elapsed_ms=elapsed,
    )
```

并在文件顶部添加导入：

```python
from app.utils.db_error_mapper import map_connection_error
```

- [ ] **Step 3: 修改 test_connection_by_id 使用错误映射**

修改 `backend/app/services/database_tool_service.py` 中 `test_connection_by_id` 的 except 分支（第 958-962 行附近）：

原来：
```python
except Exception as e:
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    return ConnectionTestResult(
        success=False, message=str(e), elapsed_ms=elapsed
    )
```

改为：
```python
except Exception as e:
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    error_code, zh_msg = map_connection_error(str(e))
    return ConnectionTestResult(
        success=False,
        message=zh_msg,
        error_code=error_code,
        elapsed_ms=elapsed,
    )
```

（`map_connection_error` 已在 Step 2 导入，无需重复导入。）

- [ ] **Step 4: 验证现有测试不被破坏**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_database_tool_service.py -v
```
预期：全部 PASS（模型字段新增是向后兼容的，Optional 默认 None）

- [ ] **Step 5: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/models/database_tool_models.py backend/app/services/database_tool_service.py
git commit -m "feat: ConnectionTestResult 新增 error_code，test_connection 接入错误映射"
```

---

## Task 3: 路由层其他连接异常复用错误映射

**Files:**
- Modify: `backend/app/routes/database_tool.py`（多处 except Exception 块）

**Interfaces:**
- Consumes: `map_connection_error(raw_error: str) -> tuple[str, str]`（来自 Task 1）
- Produces: 以下路由在连接异常时返回 `HTTPException(detail={"error_code": str, "message": str})`：
  - `get_tables` (line 481-486)
  - `get_table_schema` (line 498-503)
  - `query_table_data` (line 514-529)
  - `execute_sql` (当前无 try/except，需添加)
  - 其他含 `except Exception as e: raise HTTPException(status_code=500, detail=str(e))` 的路由

> **注意**：只对涉及"与目标数据库建立连接"的路由应用映射。纯业务逻辑错误（如配置不存在 `ValueError`）保持原样。

- [ ] **Step 1: 在路由文件顶部导入 mapper**

在 `backend/app/routes/database_tool.py` 顶部添加：

```python
from app.utils.db_error_mapper import map_connection_error
```

- [ ] **Step 2: 添加统一的连接异常处理辅助函数**

在 `backend/app/routes/database_tool.py` 的 router 定义之后（第 49 行 `router = APIRouter(...)` 之后），添加辅助函数：

```python
def _raise_connection_error(e: Exception) -> None:
    """将连接相关异常转为带 error_code 的 HTTPException。

    仅用于路由层 except Exception 分支，保持 HTTP detail 结构统一。
    """
    error_code, zh_msg = map_connection_error(str(e))
    raise HTTPException(
        status_code=500,
        detail={"error_code": error_code, "message": zh_msg, "raw": str(e)},
    ) from e
```

- [ ] **Step 3: 修改 get_tables 路由**

`backend/app/routes/database_tool.py` 第 481-486 行：

原来：
```python
try:
    return DatabaseToolService.get_tables(user_id, id)
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

改为：
```python
try:
    return DatabaseToolService.get_tables(user_id, id)
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    _raise_connection_error(e)
```

- [ ] **Step 4: 修改 get_table_schema 路由**

第 498-503 行：

原来：
```python
try:
    return DatabaseToolService.get_table_schema(user_id, id, table, database_name, schema_name)
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

改为：
```python
try:
    return DatabaseToolService.get_table_schema(user_id, id, table, database_name, schema_name)
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    _raise_connection_error(e)
```

- [ ] **Step 5: 修改 query_table_data 路由**

第 514-529 行：

原来：
```python
try:
    return DatabaseToolService.query_table_data(
        user_id,
        id,
        table,
        database_name=body.database_name,
        schema_name=body.schema_name,
        where_clause=body.where,
        order_by_clause=body.order_by,
        page=body.page,
        page_size=body.page_size,
    )
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

改为：
```python
try:
    return DatabaseToolService.query_table_data(
        user_id,
        id,
        table,
        database_name=body.database_name,
        schema_name=body.schema_name,
        where_clause=body.where,
        order_by_clause=body.order_by,
        page=body.page,
        page_size=body.page_size,
    )
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    _raise_connection_error(e)
```

- [ ] **Step 6: 修改 execute_sql 路由，添加 try/except**

当前 `execute_sql` 路由（第 452-457 行）无 try/except：

原来：
```python
@router.post("/execute", response_model=SQLExecutionResult)
async def execute_sql(
    request: SQLExecutionRequest, user_id: str = Depends(get_current_user_id)
):
    """Execute SQL statement"""
    result = DatabaseToolService.execute_sql(user_id, request)
    return result
```

改为：
```python
@router.post("/execute", response_model=SQLExecutionResult)
async def execute_sql(
    request: SQLExecutionRequest, user_id: str = Depends(get_current_user_id)
):
    """Execute SQL statement"""
    try:
        return DatabaseToolService.execute_sql(user_id, request)
    except Exception as e:
        _raise_connection_error(e)
```

> **说明**：`execute_sql` 服务层返回 `SQLExecutionResult(success=False, error_message=...)` 是正常路径（HTTP 200），此 try/except 捕获的是服务层未处理的连接异常（如引擎失效、无法建立连接等）。

- [ ] **Step 7: 修改其他涉及目标数据库连接的常见路由**

以下路由的 `except Exception as e: raise HTTPException(status_code=500, detail=str(e))` 全部替换为 `_raise_connection_error(e)`：

| 路由函数 | 大致行号范围 |
|---|---|
| `get_databases_list` (list databases) | 第 206-213 行附近 |
| `get_structure` | 第 224-228 行附近 |
| `search_tables` | 第 240-242 行附近 |
| `get_table_detail` | 第 254-257 行附近 |
| `get_table_ddl` | 第 272-274 行附近 |
| `get_all_ddl` | 第 288-290 行附近 |

执行：对每个路由，将 `except Exception as e:` 分支的 `raise HTTPException(status_code=500, detail=str(e))` 替换为 `_raise_connection_error(e)`。

- [ ] **Step 8: 验证后端启动无误**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -c "from app.routes.database_tool import router; print('OK')"
```
预期：输出 `OK`

运行现有测试确认无回归：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_database_tool_service.py -v
```
预期：全部 PASS

- [ ] **Step 9: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/database_tool.py
git commit -m "feat: 路由层连接异常统一附带 error_code 中文描述"
```

---

## Task 4: 前端 i18n 错误码文案 & 组件集成

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts:334` 附近（`database.status` 之后）
- Modify: `frontend/src/i18n/locales/en-US.ts`（对应位置添加英文）
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseConfigPanel.tsx:70-86`（`handleTestConnection`）
- Modify: `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx:53-54`（`fetchData` 错误展示）

**Interfaces:**
- Consumes: 后端 `ConnectionTestResult.error_code` 字段（来自 Task 2）
- Consumes: 后端 `HTTPException.detail` 为 `{error_code, message, raw}` 对象（来自 Task 3）
- Produces: `t.database.errors[code]` 查询函数，前端各组件复用

- [ ] **Step 1: 在 zh-CN.ts 中添加 database.errors 命名空间**

在 `frontend/src/i18n/locales/zh-CN.ts` 的 `database.status` 块（第 327-334 行）之后添加：

```typescript
    errors: {
      CONNECTION_TIMEOUT: '连接超时，请检查主机地址和端口是否正确，或网络是否可达',
      CONNECTION_REFUSED: '连接被拒绝，目标服务器可能未启动或端口未监听',
      HOST_NOT_FOUND: '无法解析主机地址，请检查主机名是否正确',
      ACCESS_DENIED: '访问被拒绝，用户名或密码可能错误，或该用户无权连接此数据库',
      DATABASE_NOT_FOUND: '指定的数据库不存在',
      SSL_ERROR: 'SSL/TLS 连接失败，请检查 SSL 配置或证书路径',
      TOO_MANY_CONNECTIONS: '连接数过多，服务器已达最大连接数限制',
      NETWORK_ERROR: '网络异常，连接中断或服务器关闭了连接',
      UNKNOWN_ERROR: '连接失败',
    },
```

- [ ] **Step 2: 在 en-US.ts 中添加对应英文**

找到 `en-US.ts` 中 `database.status` 对应位置，添加：

```typescript
    errors: {
      CONNECTION_TIMEOUT: 'Connection timed out. Please check host and port, or network reachability',
      CONNECTION_REFUSED: 'Connection refused. The target server may not be running or the port is not listening',
      HOST_NOT_FOUND: 'Cannot resolve host. Please check the hostname',
      ACCESS_DENIED: 'Access denied. Username or password may be incorrect, or the user is not allowed to connect',
      DATABASE_NOT_FOUND: 'The specified database does not exist',
      SSL_ERROR: 'SSL/TLS connection failed. Please check SSL configuration or certificate path',
      TOO_MANY_CONNECTIONS: 'Too many connections. The server has reached its maximum connection limit',
      NETWORK_ERROR: 'Network error. Connection lost or server closed the connection',
      UNKNOWN_ERROR: 'Connection failed',
    },
```

- [ ] **Step 3: 修改 DatabaseConfigPanel 的连接测试失败展示**

修改 `frontend/src/components/Tools/DatabaseTool/DatabaseConfigPanel.tsx` 第 70-86 行的 `handleTestConnection`：

原来：
```typescript
const handleTestConnection = async () => {
  setTesting(true);
  try {
    const result = await api.testConnection({
      ...formData,
      ssl_cert_path: undefined // Not supported in UI yet
    });
    if (result.success) {
      toast.success(`${t.database.status.success} (${result.elapsed_ms?.toFixed(0)}ms)`);
    } else {
      toast.error(`${t.database.status.failed}: ${result.message}`);
    }
  } catch (error) {
    toast.error(t.database.status.failed);
  } finally {
    setTesting(false);
  }
};
```

改为：
```typescript
const handleTestConnection = async () => {
  setTesting(true);
  try {
    const result = await api.testConnection({
      ...formData,
      ssl_cert_path: undefined // Not supported in UI yet
    });
    if (result.success) {
      toast.success(`${t.database.status.success} (${result.elapsed_ms?.toFixed(0)}ms)`);
    } else {
      // 优先使用 error_code 对应的本地化文案，fallback 到后端返回的 message
      const errorMsg = (result.error_code && t.database.errors[result.error_code])
        || result.message;
      toast.error(`${t.database.status.failed}: ${errorMsg}`);
    }
  } catch (error) {
    toast.error(t.database.status.failed);
  } finally {
    setTesting(false);
  }
};
```

- [ ] **Step 4: 修改 TableDataViewer 的 fetchData 错误展示**

修改 `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx` 第 53-54 行：

原来：
```typescript
if (!data.success) {
  toast.error(data.error_message || "Failed to load data");
}
```

改为：
```typescript
if (!data.success) {
  // error_message 可能包含后端传来的中文文案，直接展示
  toast.error(data.error_message || t.database.executor.noResults);
}
```

同时，由于后端 `HTTPException.detail` 现在是对象（`{error_code, message, raw}`），需要更新 catch 块（第 56-57 行）：

原来：
```typescript
} catch (error: any) {
  toast.error(error.message || "Request failed");
}
```

改为：
```typescript
} catch (error: unknown) {
  // HTTPException.detail 可能是 {error_code, message, raw} 对象
  const err = error as { message?: string; response?: { detail?: { error_code?: string; message?: string } | string } };
  const detail = err?.response?.detail;
  const errorMsg = (typeof detail === 'object' && detail?.error_code && t.database.errors[detail.error_code])
    || (typeof detail === 'object' && detail?.message)
    || (typeof detail === 'string' && detail)
    || err?.message
    || t.database.status.failed;
  toast.error(errorMsg);
}
```

> **说明**：`api/databaseToolApi.ts` 的 `handleResponse` 已经把 `error.detail` 抛到了 `Error.message` 中，但 detail 是对象时 `String(detail)` 会变成 `"[object Object]"`。此处通过 `error.response.detail` 取回原始对象。需要在 Step 5 中同步调整 `handleResponse`。

- [ ] **Step 5: 调整 handleResponse 保留 detail 原始结构**

修改 `frontend/src/api/databaseToolApi.ts` 中的 `handleResponse` 函数。先定位其位置：

```bash
grep -n "handleResponse\|throw new Error" /Users/huazhongmin/IdeaProjects/tools/frontend/src/api/databaseToolApi.ts | head -10
```

找到 `handleResponse` 后，将其错误抛出逻辑从：

```typescript
throw new Error(detail);
```

改为保留 detail 原始结构（如果 detail 是对象则保留对象）：

```typescript
const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
(err as any).detail = detail;
(err as any).response = { detail };
throw err;
```

- [ ] **Step 6: 验证前端编译通过**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run build
```
预期：构建成功，无 TypeScript 错误

- [ ] **Step 7: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts frontend/src/components/Tools/DatabaseTool/DatabaseConfigPanel.tsx frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx frontend/src/api/databaseToolApi.ts
git commit -m "feat: 前端接入数据库错误码 i18n 中文提示"
```

---

## Task 5: 前端默认排序解析器（TDD）

**Files:**
- Create: `frontend/src/utils/defaultSortResolver.ts`
- Create: `frontend/src/utils/defaultSortResolver.test.ts`

**Interfaces:**
- Consumes: `TableSchema` 类型（`columns: {name: string}[]`, `primary_key?: string[]`）
- Produces: `resolveDefaultSort(schema: TableSchema) -> string` — 返回如 `"create_time DESC"` 或空字符串

- [ ] **Step 1: 编写失败测试**

创建 `frontend/src/utils/defaultSortResolver.test.ts`：

```typescript
import { describe, it, expect } from 'vitest';
import { resolveDefaultSort } from './defaultSortResolver';
import type { TableSchema } from '../types/databaseTool';

const makeSchema = (columns: string[], primaryKey?: string[]): TableSchema => ({
  table_name: 'test_table',
  columns: columns.map(name => ({ name, type: 'VARCHAR', nullable: true, comment: null, primary_key: false, auto_increment: false })),
  primary_key: primaryKey,
});

describe('resolveDefaultSort', () => {
  describe('优先级 1：创建时间字段', () => {
    it('匹配 create_time', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'create_time', 'name'])))
        .toBe('create_time DESC');
    });

    it('匹配 created_at', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'created_at', 'name'])))
        .toBe('created_at DESC');
    });

    it('匹配 createTime（驼峰）', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'createTime'])))
        .toBe('createTime DESC');
    });

    it('匹配 createdAt（驼峰）', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'createdAt'])))
        .toBe('createdAt DESC');
    });

    it('大小写不敏感：CREATE_TIME', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'CREATE_TIME'])))
        .toBe('CREATE_TIME DESC');
    });
  });

  describe('优先级 2：更新时间字段（无创建时间时）', () => {
    it('匹配 update_time', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'update_time', 'name'])))
        .toBe('update_time DESC');
    });

    it('匹配 updated_at', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'updated_at'])))
        .toBe('updated_at DESC');
    });

    it('匹配 updateTime', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'updateTime'])))
        .toBe('updateTime DESC');
    });

    it('匹配 updatedAt', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'updatedAt'])))
        .toBe('updatedAt DESC');
    });

    it('同时有 create_time 和 update_time 时优先 create_time', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'create_time', 'update_time'])))
        .toBe('create_time DESC');
    });
  });

  describe('优先级 3：主键 ID', () => {
    it('主键为 id 时返回 id DESC', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'name'], ['id'])))
        .toBe('id DESC');
    });

    it('主键为 ID（大写）时返回 ID DESC', () => {
      expect(resolveDefaultSort(makeSchema(['ID', 'name'], ['ID'])))
        .toBe('ID DESC');
    });

    it('主键为 user_id 时不匹配（不含 "id" 子串？实际含 "id"，应匹配）', () => {
      // 主键名包含 "id" 子串即匹配
      expect(resolveDefaultSort(makeSchema(['user_id', 'name'], ['user_id'])))
        .toBe('user_id DESC');
    });

    it('主键不含 id 时不匹配', () => {
      expect(resolveDefaultSort(makeSchema(['code', 'name'], ['code'])))
        .toBe('');
    });

    it('无时间列且无主键时返回空字符串', () => {
      expect(resolveDefaultSort(makeSchema(['code', 'name'])))
        .toBe('');
    });
  });

  describe('边界情况', () => {
    it('空 columns 返回空字符串', () => {
      expect(resolveDefaultSort(makeSchema([]))).toBe('');
    });

    it('primaryKey 为空数组视为无主键', () => {
      expect(resolveDefaultSort(makeSchema(['code', 'name'], []))).toBe('');
    });

    it('primaryKey 多列时，任一列名含 id 即匹配', () => {
      expect(resolveDefaultSort(makeSchema(['a', 'b'], ['a', 'b_id'])))
        .toBe('b_id DESC');
    });
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx vitest run src/utils/defaultSortResolver.test.ts
```
预期：FAIL — `Cannot find module './defaultSortResolver'`

- [ ] **Step 3: 编写实现**

创建 `frontend/src/utils/defaultSortResolver.ts`：

```typescript
import type { TableSchema } from '../types/databaseTool';

/**
 * 创建时间字段的候选名称（全部小写，用于匹配）。
 */
const CREATE_TIME_VARIANTS = ['create_time', 'created_at', 'createtime', 'createdat'];

/**
 * 更新时间字段的候选名称（全部小写，用于匹配）。
 */
const UPDATE_TIME_VARIANTS = ['update_time', 'updated_at', 'updatetime', 'updatedat'];

/**
 * 根据表结构推算默认排序字段。
 *
 * 匹配优先级：
 * 1. 创建时间字段（create_time / created_at / createTime / createdAt）
 * 2. 更新时间字段（update_time / updated_at / updateTime / updatedAt）
 * 3. 主键列名包含 "id"（大小写不敏感）
 * 4. 均不满足则返回空字符串（保持数据库默认排序）
 *
 * 所有匹配大小写不敏感，返回时使用数据库中的原始列名。
 */
export function resolveDefaultSort(schema: TableSchema): string {
  if (!schema || !schema.columns || schema.columns.length === 0) {
    return '';
  }

  // 构造小写列名 → 原始列名的映射（取第一个命中的）
  const lowerToOriginal = new Map<string, string>();
  for (const col of schema.columns) {
    const lower = col.name.toLowerCase();
    if (!lowerToOriginal.has(lower)) {
      lowerToOriginal.set(lower, col.name);
    }
  }

  // 优先级 1：创建时间字段
  for (const variant of CREATE_TIME_VARIANTS) {
    const original = lowerToOriginal.get(variant);
    if (original) {
      return `${original} DESC`;
    }
  }

  // 优先级 2：更新时间字段
  for (const variant of UPDATE_TIME_VARIANTS) {
    const original = lowerToOriginal.get(variant);
    if (original) {
      return `${original} DESC`;
    }
  }

  // 优先级 3：主键列名包含 "id"
  if (schema.primary_key && schema.primary_key.length > 0) {
    // 在多列主键中找第一个名字包含 "id" 的列
    const matchedPk = schema.primary_key.find(pkCol => pkCol.toLowerCase().includes('id'));
    if (matchedPk) {
      return `${matchedPk} DESC`;
    }
  }

  // 优先级 4：无合适字段，保持默认
  return '';
}
```

- [ ] **Step 4: 运行测试确认通过**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx vitest run src/utils/defaultSortResolver.test.ts
```
预期：全部 PASS（约 15 个测试）

- [ ] **Step 5: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/utils/defaultSortResolver.ts frontend/src/utils/defaultSortResolver.test.ts
git commit -m "feat: 新增表默认排序解析工具 resolveDefaultSort"
```

---

## Task 6: TableDataViewer 集成默认排序

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx`

**Interfaces:**
- Consumes: `resolveDefaultSort(schema: TableSchema) -> string`（来自 Task 5）
- Produces: `TableDataViewer` 在 schema 加载后自动预填 ORDER BY 输入框；调整 fetch 时序为先 schema 后 data

- [ ] **Step 1: 导入 resolveDefaultSort**

在 `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx` 顶部添加导入：

```typescript
import { resolveDefaultSort } from '../../../utils/defaultSortResolver';
```

- [ ] **Step 2: 将 fetchSchema 改为返回 schema**

当前 `fetchSchema`（第 29-36 行）只设置 state 不返回值：

原来：
```typescript
const fetchSchema = useCallback(async () => {
  try {
    const s = await api.getTableSchema(configId, tableName, databaseName, schemaName);
    setSchema(s);
  } catch (error) {
    console.error("Failed to fetch table schema", error);
  }
}, [configId, tableName, databaseName]);
```

改为：
```typescript
const fetchSchema = useCallback(async (): Promise<TableSchema | null> => {
  try {
    const s = await api.getTableSchema(configId, tableName, databaseName, schemaName);
    setSchema(s);
    return s;
  } catch (error) {
    console.error("Failed to fetch table schema", error);
    return null;
  }
}, [configId, tableName, databaseName, schemaName]);
```

- [ ] **Step 3: 调整 useEffect 时序 — 先 schema 后 data**

当前 `useEffect`（第 64-72 行）并行调用 fetchSchema 和 fetchData：

原来：
```typescript
// Reset page when table changes
useEffect(() => {
  setPage(1);
  setWhereClause('');
  setOrderByClause('');
  setResult(null);
  setSchema(null);
  fetchSchema();
  fetchData(1);
}, [configId, databaseName, tableName, schemaName]);
```

改为：
```typescript
// Reset page when table changes
useEffect(() => {
  let cancelled = false;

  const init = async () => {
    setPage(1);
    setWhereClause('');
    setOrderByClause('');
    setResult(null);
    setSchema(null);

    // 先获取 schema，计算默认排序，再发起数据查询
    const s = await fetchSchema();
    if (cancelled) return;

    const defaultSort = s ? resolveDefaultSort(s) : '';
    setOrderByClause(defaultSort);

    // 注意：fetchData 依赖 orderByClause state，但 setState 是异步的。
    // 由于 fetchData 内部通过闭包读取 orderByClause，
    // 我们需要把 defaultSort 直接传给 fetchData 而不是等 state 更新。
    // 见 Step 4 对 fetchData 的改造。
    fetchData(1, undefined, defaultSort);
  };

  init();

  return () => { cancelled = true; };
}, [configId, databaseName, tableName, schemaName]);
```

- [ ] **Step 4: 给 fetchData 添加可选的 orderBy 覆盖参数**

当前 `fetchData`（第 38-61 行）从 state 中读取 `orderByClause`：

原来：
```typescript
const fetchData = useCallback(async (pageNum: number, newPageSize?: number) => {
  setLoading(true);
  try {
    const data = await api.queryTableData(configId, tableName, {
      database_name: databaseName,
      schema_name: schemaName,
      where: whereClause,
      order_by: orderByClause,
      page: pageNum,
      page_size: newPageSize ?? pageSize
    });
    // ...
```

改为（新增第三个可选参数 `overrideOrderBy`）：
```typescript
const fetchData = useCallback(async (
  pageNum: number,
  newPageSize?: number,
  overrideOrderBy?: string,
) => {
  setLoading(true);
  try {
    const data = await api.queryTableData(configId, tableName, {
      database_name: databaseName,
      schema_name: schemaName,
      where: whereClause,
      order_by: overrideOrderBy !== undefined ? overrideOrderBy : orderByClause,
      page: pageNum,
      page_size: newPageSize ?? pageSize
    });
    // ... 其余不变
```

并在 `useCallback` 的依赖数组中无需修改（`overrideOrderBy` 是参数，不依赖 state）。

- [ ] **Step 5: 确保其他调用 fetchData 的地方签名兼容**

在组件内搜索 `fetchData(` 的所有调用点：

```bash
grep -n "fetchData(" /Users/huazhongmin/IdeaProjects/tools/frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx
```

需要检查的调用点：
- `handleExecute`（第 74 行）：`fetchData(1)` — 无需改动，`overrideOrderBy` 默认 undefined
- `handleRefresh`（第 79 行）：`fetchData(page)` — 无需改动
- `handlePageChange`（第 83 行）：`fetchData(newPage)` — 无需改动
- pageSize 变化的 `onChange`（第 192 行）：`fetchData(1, newPageSize)` — 无需改动
- `onDeleted` 回调（第 178 行）：`fetchData(page)` — 无需改动

以上所有调用都不传第三个参数，因此 `overrideOrderBy` 默认为 `undefined`，行为与原来一致。

- [ ] **Step 6: 验证前端编译通过**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run build
```
预期：构建成功，无 TypeScript 错误

- [ ] **Step 7: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx
git commit -m "feat: TableDataViewer 接入默认排序，schema 加载后预填 ORDER BY"
```

---

## Task 7: 端到端验证 & 热重启

**Files:**
- 无新增文件，此任务为验证步骤

**Interfaces:**
- 依赖 Task 1-6 全部完成

- [ ] **Step 1: 重启后端服务以应用全部改动**

运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py restart
```

确认服务状态：
```bash
python dev_services.py status
```
预期：前后端服务均处于 running 状态

- [ ] **Step 2: 浏览器验证 — 连接错误中文提示**

打开 http://localhost:5178/tools/database-tool，新建/编辑一个数据库配置：

| 测试场景 | 配置 | 预期 toast 提示 |
|---|---|---|
| 错误主机名 | host: `nonexistent.invalid.host` | "无法解析主机地址，请检查主机名是否正确" |
| 错误端口 | port: `59999`（无服务监听） | "连接被拒绝，目标服务器可能未启动或端口未监听" 或 "连接超时" |
| 错误密码 | 配置正确 host/port 但错误 password | "访问被拒绝，用户名或密码可能错误..." |
| 不存在的数据库 | database_name: `nonexistent_db_xyz` | "指定的数据库不存在" |

- [ ] **Step 3: 浏览器验证 — 默认排序**

在数据库工具左侧展开一个已有的数据库连接，双击打开不同的表：

| 测试场景 | 预期 ORDER BY 框内容 |
|---|---|
| 表含 `create_time` 列 | 预填 `create_time DESC` |
| 表含 `created_at` 但无 `create_time` | 预填 `created_at DESC` |
| 表只有 `update_time` | 预填 `update_time DESC` |
| 表无时间列但有主键 `id` | 预填 `id DESC` |
| 表无时间列且无主键 | 框为空 |

手动修改 ORDER BY 框内容 → 点 Run → 确认结果按用户输入排序。

- [ ] **Step 4: 浏览器验证 — Console 无报错**

在上述验证过程中，打开浏览器 DevTools Console：

- 无红色错误信息
- 无 `Unhandled Promise Rejection`
- 无 `Cannot read properties of undefined` 等

- [ ] **Step 5: 最终提交（如有遗漏修改）**

如果上述验证过程中发现任何需要修复的地方，修复后执行：

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git status
# 如有未提交改动
git add -A
git commit -m "fix: 数据库工具错误提示 & 默认排序修复"
```

---

## 自检清单

### 1. Spec 覆盖度

| Spec 章节 | 对应 Task |
|---|---|
| §2.1 错误分类体系（9 个 error_code） | Task 1 |
| §2.2 后端 `db_error_mapper.py` | Task 1 |
| §2.2 `ConnectionTestResult` 新增 `error_code` | Task 2 |
| §2.2 `test_connection` / `test_connection_by_id` 使用 mapper | Task 2 |
| §2.2 其他连接场景路由复用 mapper | Task 3 |
| §2.3 前端 i18n `database.errors` | Task 4 Step 1-2 |
| §2.3 `DatabaseConfigPanel` 连接测试失败展示 | Task 4 Step 3 |
| §2.3 SQL 执行 / 表数据加载场景 | Task 4 Step 4-5 |
| §3.1 匹配规则（4 级优先级 + 变体列表） | Task 5 |
| §3.2 `resolveDefaultSort` 纯函数 | Task 5 |
| §3.2 `TableDataViewer` 预填 ORDER BY | Task 6 |
| §3.2 时序：先 schema 后 data | Task 6 Step 3 |
| §3.3 不改动 `query_table_data` / `SQLExecutor` / `ResultViewer` | 全程遵守 |
| §5 测试验证计划 | Task 7 |

### 2. 占位符扫描

已逐一检查，无 TBD / TODO / "implement later" / "similar to Task N" 等占位符。所有代码步骤均含完整代码块。

### 3. 类型一致性

- `map_connection_error` 签名在 Task 1（定义）/ Task 2（导入使用）/ Task 3（通过 `_raise_connection_error` 间接使用）中一致
- `ConnectionTestResult.error_code` 在 Task 2（模型定义）/ Task 4（前端消费）中类型一致（`Optional[str]` / `string | undefined`）
- `resolveDefaultSort` 签名在 Task 5（定义 + 测试）/ Task 6（导入使用）中一致
- `fetchData` 新增的 `overrideOrderBy` 参数在 Task 6 内部所有调用点保持兼容
