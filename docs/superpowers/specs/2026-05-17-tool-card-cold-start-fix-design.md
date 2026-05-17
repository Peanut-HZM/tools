---
author: Peanut
created_at: 2026-05-17
purpose: 解决服务启动后首次点击工具卡片响应慢的问题
---

# 工具卡片首次点击冷启动延迟修复设计

## 问题

服务启动后，第一次点击任意工具卡片，页面无反应且接口响应时间特别长。

## 根因分析

点击工具卡片时，前端同步调用 `POST /api/admin/stats/visit` 记录访问统计。该接口存在两个问题：

1. **后端无连接池**：`get_db_connection()` 每次调用都执行 `psycopg2.connect()` 创建全新 PostgreSQL 连接。服务刚启动时，TCP 握手 + 认证 + 初始化导致首次连接耗时较长。
2. **前端阻塞等待**：`App.tsx:handleToolClick` 中 `await recordToolVisit(...)` 在页面跳转前等待接口返回，用户感知为"点击没反应"。

## 方案设计

### 方案 A：前端 fire-and-forget + 后端连接池

#### 1. 后端：引入 psycopg2 连接池

在 `backend/app/config/database.py` 中引入 `psycopg2.pool.ThreadedConnectionPool`，替换当前每次新建连接的方式。

```python
# database.py 新增
import psycopg2.pool

_pool = None

def get_connection_pool(min_conn=2, max_conn=10):
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
            cursor_factory=RealDictCursor
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

在 `ToolsService.record_visit()` 中使用连接池获取和释放连接，而非直接创建/关闭。

**改动文件**：
- `backend/app/config/database.py` — 新增连接池函数
- `backend/app/services/tools_service.py` — `record_visit` 改用连接池
- `backend/app/services/tools_service.py` — `get_tool_stats` 等其他高频方法也改用连接池
- `backend/app/main.py` — lifespan 启动时预创建连接池（通过调用 `get_connection_pool()` 触发初始化）

#### 2. 前端：fire-and-forget 记录访问

`App.tsx` 的 `handleToolClick` 中，不 `await` 访问记录，直接执行路由跳转。

```typescript
// 之前
await recordToolVisit(toolId, tool.title);

// 之后
recordToolVisit(toolId, tool.title).catch(() => {});
// 立即执行 navigate，不等待返回
```

**改动文件**：
- `frontend/src/App.tsx` — `handleToolClick` 去掉 `await`

## 影响范围

| 文件 | 变更 |
|------|------|
| `backend/app/config/database.py` | 新增连接池支持 |
| `backend/app/services/tools_service.py` | 高频数据库操作改用连接池 |
| `backend/app/main.py` | lifespan 中预初始化连接池 |
| `frontend/src/App.tsx` | 工具点击改为 fire-and-forget |

## 验证

1. 重启后端服务，观察启动日志确认连接池初始化成功
2. 打开浏览器访问首页，等待工具列表加载完成
3. 点击任意工具卡片，应立刻跳转到对应页面，无明显延迟
4. 后端日志应显示访问记录已写入（异步完成）
