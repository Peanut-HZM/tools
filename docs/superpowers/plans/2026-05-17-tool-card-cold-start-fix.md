# 工具卡片冷启动延迟修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除服务启动后首次点击工具卡片的响应延迟，通过连接池 + 前端 fire-and-forget 实现。

**Architecture:** 在 `database.py` 中引入 `psycopg2.pool.ThreadedConnectionPool`，改造 `tools_service.py` 中所有数据库操作使用连接池获取/释放连接，并在 `main.py` 的 lifespan 启动阶段预初始化连接池。前端 `App.tsx` 的 `handleToolClick` 去掉 `await`，改为 fire-and-forget。

**Tech Stack:** psycopg2 pool, FastAPI, React, TypeScript

---

## 文件结构

| 文件 | 角色 |
|------|------|
| `backend/app/config/database.py` | 新增连接池基础设施函数 |
| `backend/app/services/tools_service.py` | 所有 `get_db_connection()` 调用替换为 `get_pooled_db_connection()` / `release_db_connection()` |
| `backend/app/main.py` | lifespan 中预初始化连接池 |
| `frontend/src/App.tsx` | `handleToolClick` 改为 fire-and-forget |

**范围决定**：全项目有 20+ 文件、100+ 处 `get_db_connection()` 调用。本次只改造 `tools_service.py`（工具卡片点击直接调用的接口）和基础设施，其他服务后续迭代。

---

### Task 1: 连接池基础设施

**Files:**
- Modify: `backend/app/config/database.py`

- [ ] **Step 1: 添加连接池函数到 database.py**

在 `database.py` 末尾（`test_connection()` 函数之后）添加连接池支持：

```python
# ============================================================
# 连接池支持
# ============================================================

_pool: Optional["psycopg2.pool.ThreadedConnectionPool"] = None


def get_connection_pool(min_conn: int = 2, max_conn: int = 10):
    """获取或创建连接池（单例懒加载）"""
    global _pool
    if _pool is None:
        config = get_db_config()
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            cursor_factory=RealDictCursor,
        )
    return _pool


def get_pooled_db_connection():
    """从连接池获取连接"""
    pool = get_connection_pool()
    return pool.getconn()


def release_db_connection(conn):
    """释放连接回池"""
    pool = get_connection_pool()
    pool.putconn(conn)
```

同时在文件顶部 `import` 区域添加 `psycopg2.pool` 和 `Optional`：

```python
from typing import Optional
import psycopg2.pool
```

- [ ] **Step 2: 验证语法正确**

Run: `python -m py_compile backend/app/config/database.py`
Expected: 无报错输出

- [ ] **Step 3: 提交**

```bash
git add backend/app/config/database.py
git commit -m "feat: 添加 PostgreSQL 连接池支持"
```

---

### Task 2: tools_service.py 改用连接池

**Files:**
- Modify: `backend/app/services/tools_service.py`

**原则**：每个方法中，将 `conn = get_db_connection()` 替换为 `conn = get_pooled_db_connection()`，将 `finally` 块中的 `conn.close()` 替换为 `release_db_connection(conn)`。

**需要修改的方法**（共 23 处 `get_db_connection()` 调用）：
- `_init_db()` — 行 28
- `get_all_tools()` — 行 159
- `get_tools_by_category()` — 行 206
- `search_tools()` — 行 231
- `update_tool_status()` — 行 256
- `record_visit()` — 行 276
- `update_tool()` — 行 312, 348（两处）
- `get_tools_paginated()` — 行 384
- `upload_tool_icon()` — 行 461, 498（两处）
- `delete_tool_icon()` — 行 518
- `get_tools_for_platform()` — 行 539
- `get_all_categories()` — 行 568
- `create_category()` — 行 585
- `update_category()` — 行 621
- `delete_category()` — 行 655
- `get_tool_stats()` — 行 676

- [ ] **Step 1: 替换 import**

文件顶部添加：

```python
from app.config.database import get_db_connection, get_pooled_db_connection, release_db_connection
```

- [ ] **Step 2: 替换所有 get_db_connection → get_pooled_db_connection**

使用 AST 替换或全局替换，将所有 `get_db_connection()` 替换为 `get_pooled_db_connection()`。

- [ ] **Step 3: 替换所有 conn.close() → release_db_connection(conn)**

在 `finally` 块中，将所有 `conn.close()` 替换为 `release_db_connection(conn)`。

**注意**：`_init_db()` 方法中第 146 行 `conn.commit()` 后直接关闭，需要将第 152 行的 `conn.close()` 替换为 `release_db_connection(conn)`。

`upload_tool_icon()` 方法中第 475 行有 `conn.close()` 单独调用（非 finally 块），也需要替换为 `release_db_connection(conn)`。

- [ ] **Step 4: 验证语法正确**

Run: `python -m py_compile backend/app/services/tools_service.py`
Expected: 无报错输出

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/tools_service.py
git commit -m "refactor: tools_service 改用连接池替代直接新建连接"
```

---

### Task 3: main.py 预初始化连接池

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 lifespan 中添加连接池预初始化**

在 `lifespan` 函数中，找到 `logger.info("Application startup complete")` 行（约 154 行），在其之前添加：

```python
    # 预初始化数据库连接池
    try:
        from app.config.database import get_connection_pool
        get_connection_pool()
        logger.info("数据库连接池初始化完成")
    except Exception as e:
        logger.warning(f"数据库连接池初始化失败（将按需懒加载）: {e}")
```

- [ ] **Step 2: 验证语法正确**

Run: `python -m py_compile backend/app/main.py`
Expected: 无报错输出

- [ ] **Step 3: 提交**

```bash
git add backend/app/main.py
git commit -m "feat: 启动时预初始化数据库连接池"
```

---

### Task 4: 前端 fire-and-forget

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 修改 handleToolClick 中的 recordToolVisit**

找到 `App.tsx` 第 202-211 行：

```typescript
  // 处理工具点击 - 使用路由导航
  const handleToolClick = async (toolId: string) => {
    // Record tool visit
    try {
      const tool = filteredTools.find(t => t.id === toolId);
      if (tool) {
        await recordToolVisit(toolId, tool.title);
      }
    } catch (e) {
      console.error("Failed to record tool visit", e);
    }

    // ... 后续登录拦截和路由跳转 ...
```

改为：

```typescript
  // 处理工具点击 - 使用路由导航
  const handleToolClick = (toolId: string) => {
    // Record tool visit (fire-and-forget，不阻塞页面跳转)
    const tool = filteredTools.find(t => t.id === toolId);
    if (tool) {
      recordToolVisit(toolId, tool.title).catch(() => {});
    }

    // 登录拦截
    if (tool?.require_login && !isAuthenticated) {
      if (window.confirm('该工具需要登录后才能使用，是否前往登录？')) {
        navigate('/login');
      }
      return;
    }
```

关键变化：
- `async` 关键字移除
- `await recordToolVisit(...)` 改为 `recordToolVisit(...).catch(() => {})`
- 删除 try-catch 包裹（已在 `.catch()` 中处理）

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: `App.tsx` 无编译错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/App.tsx
git commit -m "perf: 工具点击改为 fire-and-forget，不阻塞页面跳转"
```

---

### Task 5: 浏览器验证

- [ ] **Step 1: 重启后端服务**

Run: `python dev-services.py restart`
Expected: 日志中出现 "数据库连接池初始化完成" 和 "Application startup complete"

- [ ] **Step 2: 打开浏览器访问首页**

URL: `http://localhost:5178`
Expected: 工具列表正常加载

- [ ] **Step 3: 点击任意工具卡片**

Expected: 立刻跳转到对应工具页面，无明显延迟（<100ms）

- [ ] **Step 4: 检查后端日志**

Run: `tail -n 50 backend/logs/app.log`（或 Read 工具）
Expected: 能看到 "Recorded visit for tool: xxx" 日志

---

## Spec Coverage 检查

| 规格要求 | 对应 Task |
|---------|----------|
| database.py 新增连接池 | Task 1 |
| tools_service.py record_visit 改用连接池 | Task 2 |
| tools_service.py 其他高频方法改用连接池 | Task 2 |
| main.py lifespan 预初始化连接池 | Task 3 |
| frontend App.tsx 去掉 await | Task 4 |
| 重启后验证连接池初始化成功 | Task 5 |
| 点击工具卡片立刻跳转 | Task 5 |
| 后端日志显示访问记录已写入 | Task 5 |

## Placeholder 扫描

无 TBD、TODO、"add validation" 等占位内容。

## 类型一致性

所有修改沿用现有类型签名和函数接口，无新类型引入。`psycopg2.pool.ThreadedConnectionPool` 返回的连接对象与 `psycopg2.connect()` 完全兼容，`conn.cursor()`、`conn.commit()`、`conn.close()` 等行为一致。
