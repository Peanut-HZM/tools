---
author: peanut
created_at: 2026-06-25
purpose: 修复显示设置保存卡住问题，统一后端数据库连接使用连接池
---

# 后端连接池统一设计文档

## 问题描述

数据库工具页面的"显示设置"对话框点击保存后，界面一直卡在"保存中..."状态。

### 根因分析

**核心问题：数据库连接池耗尽**

当前后端存在两种数据库连接获取方式：

1. **连接池方式**：`get_pooled_db_connection()` / `release_db_connection()`
   - 用于 `tools_service.py`、`database_tool_service.py`
   - 连接池大小已调整为 5/20（psycopg2）和 10/10（SQLAlchemy）

2. **直连方式**：`get_db_connection()` / `conn.close()`
   - 大量用于 `auth_service.py`、`http_client_service.py` 等
   - 每次调用都创建新连接，关闭后不会归还到 psycopg2 连接池

当首页、数据库工具页、显示设置等多个请求并发时，PostgreSQL 服务端的总连接数被耗尽，导致依赖连接池的接口（如 `save_display_preferences`）等待超时。

### 日志证据

```python
sqlalchemy.exc.TimeoutError: QueuePool limit of size 2 overflow 1 reached, 
connection timed out, timeout 10.00
```

### 保存卡住流程

```
1. 用户点击"保存" → 前端 setSaving(true) 显示"保存中..."
2. 前端调用 PUT /api/database-tool/preferences
3. 后端 save_display_preferences() 需要从连接池获取连接
4. 连接池耗尽 → 请求等待 10 秒后超时
5. 前端没有超时机制，await onSave(...) 一直挂起
6. finally 中的 setSaving(false) 永远不会执行
7. 界面一直显示"保存中..."
```

---

## 优化方案

### 方案 A：前端增加超时和错误处理

修改 `DisplaySettingsDialog.tsx` 的 `handleSave` 增加 Promise.race 超时。

| 优点 | 缺点 |
|------|------|
| ✅ 立即解决"一直卡着" | ❌ 保存仍可能失败 |
| ✅ 改动小 | ❌ 不解决后端根因 |

### 方案 B：统一后端使用连接池（推荐）

将 `auth_service.py`、`http_client_service.py` 等服务中的 `get_db_connection()` 替换为 `get_pooled_db_connection()` 和 `release_db_connection()`。

| 优点 | 缺点 |
|------|------|
| ✅ 彻底解决连接池耗尽问题 | ❌ 改动范围较大 |
| ✅ 所有接口受益 | ❌ 需要充分测试 |
| ✅ 连接复用，减少数据库压力 |  |

### 方案 C：增加 PostgreSQL 服务端最大连接数

修改 PostgreSQL 配置文件 `max_connections`。

| 优点 | 缺点 |
|------|------|
| ✅ 简单快速 | ❌ 不治本 |
| ✅ 不需要改代码 | ❌ 资源浪费 |
|  | ❌ 部署环境不一定允许 |

---

## 推荐方案：B

### 实施策略

#### 阶段 1：改造 `auth_service.py`

该文件是直连方式最多的服务，优先改造。

**改造模式：**

```python
# 改造前
conn = get_db_connection()
try:
    # ...
finally:
    conn.close()

# 改造后
conn = get_pooled_db_connection()
try:
    # ...
finally:
    release_db_connection(conn)
```

需要修改的方法：
- `_log_audit`
- `_get_user_by_username`
- `_get_user_by_id`
- `_create_user`
- `_update_user`
- `_change_password`
- `update_user_role`
- `delete_user`
- 其他数据库操作方法

#### 阶段 2：改造 `http_client_service.py`

#### 阶段 3：检查其他使用 `get_db_connection()` 的文件

通过全局搜索找出所有使用 `get_db_connection()` 的位置：

```bash
grep -rn "get_db_connection()" backend/app/services/
grep -rn "get_db_connection()" backend/app/routes/
```

逐个评估是否需要改为连接池。

#### 阶段 4：验证和测试

- 重启后端服务
- 测试登录、保存显示设置、首页加载
- 查看后端日志确认无连接池超时错误

---

## 风险与注意事项

### 1. 连接释放必须配对

每个 `get_pooled_db_connection()` 必须有对应的 `release_db_connection()`，否则连接池会泄漏。

### 2. 异常处理

确保在异常时也能正确释放连接：

```python
conn = get_pooled_db_connection()
try:
    with conn.cursor() as cur:
        cur.execute(...)
        conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    release_db_connection(conn)
```

### 3. 事务边界

连接池中的连接可能被复用，必须确保每个请求完成后提交或回滚事务。

### 4. 不要改造所有位置

某些特殊场景（如一次性脚本、测试代码）可能不适合连接池，需要逐案评估。

---

## 验证标准

- ✅ 显示设置保存响应时间 < 1s
- ✅ 前端不再出现"保存中..."卡住
- ✅ 后端日志无 `QueuePool limit` 错误
- ✅ 登录、注册、登出功能正常
- ✅ 首页和数据库工具页加载正常
- ✅ 浏览器 Console 无错误

---

## 相关文件

- `backend/app/config/database.py` - 连接池实现
- `backend/app/services/auth_service.py` - 需要改造的主要文件
- `backend/app/services/http_client_service.py` - 需要改造的文件
- `backend/app/services/database_tool_service.py` - 已使用连接池
- `backend/app/services/tools_service.py` - 已使用连接池
- `frontend/src/components/Tools/DatabaseTool/components/DisplaySettingsDialog.tsx` - 保存前端组件

---

## 回滚方案

如果出现连接池泄漏或其他问题，可以：
1. 回退相关服务的修改
2. 临时增加 PostgreSQL `max_connections`
3. 重启后端服务

---

## 决策记录

- **选择方案：** B（统一后端使用连接池）
- **决策时间：** 2026-06-25
- **决策理由：** 方案 B 从根因解决问题，避免连接池耗尽导致所有接口受影响
- **预期收益：** 彻底解决保存卡住问题，提升所有数据库操作接口的稳定性
