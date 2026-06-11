---
author: Peanut
created_at: 2026-06-12
purpose: 修复 database-tool 页面长时间打开后频繁报 "server closed the connection unexpectedly" 及密码解密失败 500 错误
---

# database-tool 连接稳定性修复设计

## 1. 背景与问题

用户反馈：`http://localhost:5178/tools/database-tool` 页面长时间打开后，在展开连接、执行 SQL 或刷新表结构时，经常弹出如下报错：

```
server closed the connection unexpectedly
This probably means the server terminated abnormally
before or while processing the request.
```

## 2. 日志分析结论

通过本地日志定位到三类相关错误：

1. **`routes.log`**：`app.routes.database_tool - Search error: server closed the connection unexpectedly`
2. **`services.log`**：`Error fetching categories: server closed the connection unexpectedly` —— 应用自身 PostgreSQL 连接也丢失，说明是后端连接池管理问题，而非仅目标数据库问题。
3. **`backend_后端.log`**：大量 `Decryption failed: ` + `Failed to decrypt password` —— 部分数据库配置密码解密失败导致 500。

## 3. 根因分析

### 3.1 后端自身连接池没有健康检查

`backend/app/config/database.py` 使用 `psycopg2.pool.ThreadedConnectionPool(min=1, max=3)`。连接池在 `get_pooled_db_connection()` 中只是简单 `getconn()`，不会检测连接是否已被数据库服务端因空闲超时关闭。页面长时间未操作后，池内连接失效，下一次请求直接报 `server closed the connection unexpectedly`。

### 3.2 目标数据库连接回收周期过长

`backend/app/utils/db_connection_manager.py` 中 `pool_recycle=3600`（1 小时）。如果目标 MySQL/PostgreSQL 的空闲超时时长更短（如云数据库常见 10~30 分钟），连接会被服务端关闭，复用时触发同样报错。虽然已开启 `pool_pre_ping=True`，但 recycle 周期仍偏长。

### 3.3 密码解密失败未降级

`database_tool_service.py` 中多处直接 `raise ValueError("Failed to decrypt password")` 或让异常上抛，导致前端收到 500。部分 `db_configs` 记录的密码可能是历史数据或用不同密钥加密，字段为空/损坏时也会触发。

## 4. 修复方案

采用**方案 A：最小改动，聚焦连接保活 + 错误降级**。

### 4.1 后端自身连接池增加有效性检测

修改 `backend/app/config/database.py` 中的 `get_pooled_db_connection()`：

- 从连接池取出连接后，检查 `conn.closed`。
- 如果连接已关闭，调用 `pool.putconn(conn, close=True)` 归还真连接并关闭，然后重新获取一个新连接。
- 对 `release_db_connection` 增加异常保护，避免关闭失败影响业务流程。

### 4.2 缩短目标数据库连接回收周期

修改 `backend/app/utils/db_connection_manager.py`：

- 将 `pool_recycle` 从 `3600` 秒调整为 `300` 秒（5 分钟）。
- 保持 `pool_pre_ping=True` 不变。
- 修复部分方法中 engine key 重复拼接的问题：统一传 `config_id` 作为第一个参数，让 `DBConnectionManager.get_engine()` 内部根据 `config.get("database_name")` 生成 key，避免变成 `config_id:db_name:db_name`。

### 4.3 密码解密失败降级为业务错误

修改 `backend/app/services/database_tool_service.py` 与 `backend/app/routes/database_tool.py`：

- 在解密密码处使用 `try/except` 捕获异常。
- 解密失败时记录日志，并返回/抛出带有明确业务语义的 400 错误，如 `"数据库配置密码解密失败，请编辑该连接重新保存密码"`。
- 对于 `/databases`（列表）、`/databases/{id}/databases`（数据库列表）等接口，单条配置解密失败不应导致整个请求 500，应跳过该条或返回 `null` 密码并标记异常状态。

## 5. 具体修改文件

| 文件 | 修改内容 |
|------|----------|
| `backend/app/config/database.py` | `get_pooled_db_connection()` 增加连接有效性检查与重取逻辑 |
| `backend/app/utils/db_connection_manager.py` | `pool_recycle` 改为 300 秒；修复 engine key 重复问题 |
| `backend/app/services/database_tool_service.py` | 解密失败降级处理，避免抛 500 |
| `backend/app/routes/database_tool.py` | 对配置相关接口增加异常捕获，返回友好错误信息 |

## 6. 验证方式

1. 重启后端：`python dev-services.py restart backend`
2. 浏览器打开 `http://localhost:5178/tools/database-tool` 并登录。
3. 展开多个数据库连接，确认无 500/连接关闭报错。
4. 保持页面静置 30 分钟以上，再次执行刷新/搜索/SQL，确认不再出现 `server closed the connection unexpectedly`。
5. 查看后端日志 `logs/backend_后端.log`，确认无新增 `Decryption failed` 导致的 500。

## 7. 非目标范围

- 不重构整体连接池架构（不改用 SQLAlchemy 管理应用自身 DB）。
- 不修改前端交互逻辑。
- 不处理 OpenClaw / ccusage / token-usage 等其他模块的无关报错。
