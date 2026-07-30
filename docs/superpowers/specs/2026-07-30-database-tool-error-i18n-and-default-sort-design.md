---
author: Peanut
created_at: 2026-07-30
purpose: 数据库连接错误中文提示 + 表数据默认排序
---

# 数据库工具：错误中文提示 & 默认排序设计

## 1. 背景与目标

`http://localhost:5178/tools/database-tool` 页面存在两个体验问题：

1. **连接错误直接暴露原始异常字符串**（如 `(pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'xxx' (timed out)")`），对非专业用户不友好，需要翻译为中文描述。
2. **打开表数据时没有默认排序**，结果顺序不可预期；而绝大多数业务表都带有时间字段或主键，用户通常希望按最新记录优先查看。

目标：

- 所有连接相关场景的错误信息，均提供清晰中文提示
- 打开表时自动按时间字段/主键逆序排列，用户显式声明排序则以用户为准

## 2. 功能一：数据库连接错误中文映射

### 2.1 错误分类体系

| error_code | 中文描述 | 匹配的关键字（大小写不敏感） |
|---|---|---|
| `CONNECTION_TIMEOUT` | 连接超时，请检查主机地址和端口是否正确，或网络是否可达 | `timed out`, `timeout`, `connect_timeout` |
| `CONNECTION_REFUSED` | 连接被拒绝，目标服务器可能未启动或端口未监听 | `connection refused`, `actively refused`, `can't connect` |
| `HOST_NOT_FOUND` | 无法解析主机地址，请检查主机名是否正确 | `name or service not known`, `getaddrinfo failed`, `nodename nor servname provided`, `unknown host` |
| `ACCESS_DENIED` | 访问被拒绝，用户名或密码可能错误，或该用户无权连接此数据库 | `access denied`, `authentication failed`, `invalid credentials`, `login failed`, `password authentication failed`, `using password` |
| `DATABASE_NOT_FOUND` | 指定的数据库不存在 | `unknown database`, `database .* does not exist` |
| `SSL_ERROR` | SSL/TLS 连接失败，请检查 SSL 配置或证书路径 | `ssl`, `certificate`, `tls` |
| `TOO_MANY_CONNECTIONS` | 连接数过多，服务器已达最大连接数限制 | `too many connections`, `max_connections`, `connection limit` |
| `NETWORK_ERROR` | 网络异常，连接中断或服务器关闭了连接 | `connection lost`, `broken pipe`, `connection reset`, `server closed`, `lost connection`, `econnreset`, `econnrefused` |
| `UNKNOWN_ERROR` | 连接失败（兜底，仍附带原始错误信息） | 以上均不匹配时 |

匹配优先级按表格从上到下（越具体的越先匹配）。

### 2.2 后端实现

**新增 `backend/app/utils/db_error_mapper.py`：**

```python
def map_connection_error(raw_error: str) -> tuple[str, str]:
    """
    将原始异常字符串映射为 (error_code, zh_message)。
    大小写不敏感关键字匹配。
    """
```

- 返回 `(error_code, zh_message)` 二元组
- `UNKNOWN_ERROR` 时 `zh_message` 使用原始错误字符串

**修改 `backend/app/models/database_tool_models.py`：**

```python
class ConnectionTestResult(BaseModel):
    success: bool
    message: str                         # 保留原始错误信息（调试用）
    error_code: Optional[str] = None     # 新增：错误码
    elapsed_ms: Optional[float] = None
```

**修改 `backend/app/services/database_tool_service.py`：**

在 `test_connection` / `test_connection_by_id` 的 `except Exception as e` 分支中：

```python
error_code, zh_msg = map_connection_error(str(e))
return ConnectionTestResult(
    success=False,
    message=zh_msg,           # 中文消息作为 message
    error_code=error_code,    # 错误码供前端精确匹配
    elapsed_ms=elapsed,
)
```

**其他连接相关场景**：在路由层的 `except` 块（如 SQL 执行、表数据查询等）中复用 mapper，将 `error_code` 附加到 `HTTPException.detail` 中返回。格式统一为 `{"error_code": "...", "message": "..."}` 对象，便于前端统一处理。

### 2.3 前端实现

**i18n 新增 `database.errors` 命名空间：**

```typescript
// zh-CN.ts
database: {
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
  }
}
```

**`DatabaseConfigPanel.tsx` 连接测试失败时：**

```
原来：toast.error(`${t.database.status.failed}: ${result.message}`)
改为：toast.error(`${t.database.status.failed}: ${t.database.errors[result.error_code] || result.message}`)
```

**其他场景（SQL 执行、表数据加载）同理**：若后端返回了 `error_code`，优先显示中文描述；否则 fallback 到原始消息。

## 3. 功能二：表数据默认排序

### 3.1 匹配规则

前端在 schema 加载完成后，按以下优先级自动计算默认排序字段：

| 优先级 | 匹配条件 | 默认排序 |
|---|---|---|
| 1 | 存在 `create_time` 列（匹配变体见下） | `{匹配到的字段名} DESC` |
| 2 | 存在 `update_time` 列（匹配变体见下） | `{匹配到的字段名} DESC` |
| 3 | 存在主键，且主键列名含 `id`（大小写不敏感） | `{主键字段名} DESC` |
| 4 | 以上均不满足 | 不预填，保持数据库默认排序 |

**字段名匹配变体**（大小写不敏感）：

- 创建时间：`create_time`、`created_at`、`createTime`、`createdAt`
- 更新时间：`update_time`、`updated_at`、`updateTime`、`updatedAt`

匹配时将 schema.columns 中所有列名统一转小写后与上述列表比对，取第一个命中的列名。输出时使用数据库中的**原始列名**（而非小写化后的名字）。

### 3.2 前端实现

**新增 `frontend/src/utils/defaultSortResolver.ts`：**

```typescript
import { TableSchema } from '../types/databaseTool';

/**
 * 根据表结构推算默认排序字段。
 * 返回如 "create_time DESC" 的字符串，无合适字段时返回空字符串。
 */
export function resolveDefaultSort(schema: TableSchema): string {
  // ...
}
```

纯函数、无副作用、便于单测。

**`TableDataViewer.tsx` 修改：**

1. 在 `fetchSchema()` 成功后，调用 `resolveDefaultSort(schema)` 计算默认排序
2. 将结果 `setOrderByClause(...)` 预填到 ORDER BY 输入框
3. 调整时序：**先 await fetchSchema() → 再设置默认 ORDER BY → 再 fetchData(1)**，确保首次查询就带上默认排序

**数据流时序：**

```
表切换 → await fetchSchema()
       → resolveDefaultSort(schema)
       → setOrderByClause("create_time DESC")
       → fetchData(1)  // 此时 orderByClause 已是预填值
```

**用户交互：**

- 用户可以直接修改 ORDER BY 输入框内容（覆盖默认）
- 用户可以清空输入框（变回无排序）
- 切换表时自动重新计算默认排序

### 3.3 不改动的部分

- 后端 `query_table_data` 完全不变 — 它已按前端传入的 `order_by` 原样拼接 SQL
- `SQLExecutor`（SQL 控制台）不涉及 — 用户手写完整 SQL
- 后端 `get_table_schema` 接口不变 — 前端已有足够信息计算排序
- `ResultViewer` 组件不变 — 只负责展示

## 4. 改动范围总结

### 新增文件

| 文件 | 说明 |
|---|---|
| `backend/app/utils/db_error_mapper.py` | 错误分类映射工具 |
| `frontend/src/utils/defaultSortResolver.ts` | 默认排序计算工具 |

### 修改文件

| 文件 | 改动点 |
|---|---|
| `backend/app/models/database_tool_models.py` | `ConnectionTestResult` 新增 `error_code` 字段 |
| `backend/app/services/database_tool_service.py` | `test_connection` / `test_connection_by_id` 的 except 分支调用 mapper |
| `backend/app/routes/database_tool.py` | 连接相关路由 except 块中复用 mapper |
| `frontend/src/i18n/locales/zh-CN.ts` | `database.errors` 新增 9 个错误码中文描述 |
| `frontend/src/components/Tools/DatabaseTool/DatabaseConfigPanel.tsx` | 连接测试失败时优先用 `error_code` 对应中文 |
| `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx` | schema 加载后预填 ORDER BY，调整 fetch 时序 |

## 5. 测试验证计划

### 5.1 连接错误中文提示

- 故意配置错误的主机名 → 看到 "无法解析主机地址"
- 故意配置错误的端口 → 看到 "连接被拒绝" 或 "连接超时"
- 故意配置错误的密码 → 看到 "访问被拒绝"
- 故意配置不存在的数据库名 → 看到 "指定的数据库不存在"
- SQL 执行中连接断开 → 也能看到对应中文提示

### 5.2 默认排序

- 打开含 `create_time` 列的表 → ORDER BY 框预填 `create_time DESC`
- 打开含 `created_at` 但无 `create_time` 的表 → 预填 `created_at DESC`
- 打开只有 `update_time` 的表 → 预填 `update_time DESC`
- 打开无时间列但有主键 `id` 的表 → 预填 `id DESC`
- 打开无时间列且无主键的表 → ORDER BY 框为空
- 手动修改 ORDER BY → 以用户输入为准
- 切换表 → 自动重新计算默认排序
