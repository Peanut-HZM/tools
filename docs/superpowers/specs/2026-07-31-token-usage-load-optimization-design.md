---
author: Peanut
created_at: 2026-07-31
purpose: Token Usage 页面加载性能优化设计文档 —— 数据库直读 + Redis 缓存 + 定时后台同步
---

# Token Usage 页面加载性能优化设计

## 背景与问题

`http://localhost:5178/tools/token-usage` 页面首次加载慢，根源是：

1. **首屏请求可能触发 CLI 子进程**：当前页面进入后，前端轮询和手动刷新可能走 `refresh` 接口，该接口会同步跑 ccusage / claude CLI 子进程（几秒到几十秒），阻塞用户等待。
2. **同步与读路径未彻底解耦**：虽然已有 Redis 缓存和后台同步循环，但缓存预热缺失，导致首次进页面或同步完成后立即访问时，仍需等待 DB 聚合查询完成。

## 目标

- **首屏数据直接来自数据库/Redis 缓存**，不经 CLI 子进程，ms 级响应。
- **定时任务负责刷新最新数据**，前端不阻塞，异步完成。
- **保持现有 Redis 缓存层**，增强同步后缓存预热，避免冷查询。

## 现状梳理

### 后端路由

| 端点 | 文件位置 | 职责 |
|------|---------|------|
| `GET /api/token-usage/summary` | `backend/app/routes/token_usage.py:734` | 返回汇总统计，先查 Redis，未命中走 DB GROUP BY |
| `POST /api/token-usage/details` | `backend/app/routes/token_usage.py:906` | 返回明细分页，先查 Redis，未命中走 DB 分页 |
| `POST /api/token-usage/refresh` | `backend/app/routes/token_usage.py:367` | 同步 + 刷缓存，阻塞调用方 |
| `POST /api/token-usage/sync` | `backend/app/routes/token_usage.py:1297` | 后台线程同步（当前实现为 `threading.Thread`） |
| `POST /api/token-usage/refresh-ccusage` | `backend/app/routes/token_usage.py:1228` | 手动触发 ccusage v2 同步 |

### 缓存层

- Redis 缓存服务：`backend/app/services/token_usage_cache.py`
- 缓存键：`token_usage:query:{source}:{type}:{days}:{group_by}:{user_id}:{device_id}:{tool_id}:{model}:{sort_by}:{sort_order}`
- TTL：来自 `settings.CACHE_REDIS_TOKEN_USAGE_TTL`（当前约 300s）
- 失效：同步完成后 `invalidate_user_query_cache(user_id)` 清除该用户所有查询缓存

### 同步层

- 同步服务：`backend/app/services/token_usage_sync_service.py:261` `sync_token_usage()`
- 后台循环：`backend/app/services/token_usage_background_sync.py:158` `_background_sync_loop()`
- 当前问题：同步完成后只 invalidate 缓存，不主动预热；首次进页面冷查询仍需 DB 聚合

### 前端

- 组件：`frontend/src/components/Tools/TokenUsage.tsx`
- 数据获取：`useTokenUsageSummary` + `useTokenUsageDetails` hooks
- 轮询：`useTokenUsagePolling` 默认 30 秒静默刷新 summary
- 手动同步：`handleSync` 当前 await `/refresh-ccusage` 完成后才刷新页面

## 设计方案

### 1. 架构总览

```
┌──────────────────────────────────────────────────┐
│  前端 (TokenUsage.tsx)                            │
│  进入页面                                          │
│    ├─ GET /summary ──→ 优先从 Redis 读取（ms 级）    │
│    ├─ POST /details ──→ 优先从 Redis 读取（ms 级）   │
│    └─ useTokenUsagePolling(30s) → 定期刷新 summary  │
│                                                   │
│  点击"同步数据"                                      │
│    └─ POST /sync ──→ 后端 fork 后台线程             │
│       → CLI 抓取 → DB 写入 → Redis invalidate + warm │
│       → 下次 summary/details 自动命中新缓存          │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  后端 (FastAPI)                                   │
│                                                   │
│  GET /summary ──→ Redis 命中?                     │
│       ├─ 命中 → 直接返回 (cached=true)             │
│       └─ 未命中 → DB SQL GROUP BY → 写 Redis → 返回 │
│                                                   │
│  POST /sync ──→ asyncio.to_thread(run_sync)       │
│       └─ sync_token_usage() → invalidate + warm    │
│                                                   │
│  _background_sync_loop (5min)                     │
│       └─ run_background_sync_once → per-user sync  │
│       └─ sync_token_usage() → invalidate + warm    │
└──────────────────────────────────────────────────┘
```

核心原则：
- **读路径**：永远不经 CLI，缓存未命中时只打 DB（聚合 SQL），命中时只读 Redis
- **写路径**：同步（CLI 子进程）完全与前端页面访问解耦，异步完成
- **缓存预热**：同步完成后主动回写 Redis，避免下次读走 DB

### 2. 缓存与数据流

#### 读路径（summary / details）

```
前端请求 → Redis 缓存命中？
  ├─ 命中 → 直接返回 JSON（含 cached=true），耗时 < 10ms
  └─ 未命中 → DB SQL GROUP BY 聚合 → 结果写 Redis（TTL=300s）
              → 返回 JSON（含 cached=false），耗时 < 500ms
```

**缓存键结构**（沿用现有 `_build_query_cache_key`）：

```
token_usage:query:{source}:{type}:{days}:{group_by}:{user_id}:{device_id}:{tool_id}:{model}:{sort_by}:{sort_order}
```

**缓存 TTL**：`settings.CACHE_REDIS_TOKEN_USAGE_TTL` 设为 **300 秒**（5 分钟），与后台同步间隔一致。

**缓存失效策略**：
- 后台同步完成 → `invalidate_user_query_cache(user_id)` + `warm_query_cache(user_id)`
- 手动同步完成 → 同上
- 设备重命名/合并/别名变更 → 同上
- **不再**在读取路径做同步检查或被动刷新——读就是纯读

#### 写路径（同步）

```
触发来源:
  ├─ _background_sync_loop (5 分钟间隔，asyncio 循环)
  └─ POST /sync (用户手动点击，asyncio.to_thread → 立即返回 202)

同步流程:
  1. acquire_refresh_lock(user_id) → 成功继续 / 失败跳过
  2. CLI 子进程抓取（ccusage daily + per-agent modelsUsed，不持有 DB 连接）
  3. SessionLocal() → per-record upsert → commit → close
  4. invalidate_user_query_cache(user_id)
  5. warm_query_cache(user_id) ← 新增：主动回写常用查询缓存
  6. release_refresh_lock(user_id)
```

> 关键优化：步骤 2「CLI 抓取」不持有 DB 连接。同步期间 DB 连接池对其他查询请求完全可用，不影响首屏加载。

### 3. 具体改动

#### 后端改动（3 处）

| # | 文件 | 改动 | 原因 |
|---|------|------|------|
| 1 | `backend/app/services/token_usage_cache.py` | 新增 `warm_query_cache(user_id: str)` 函数：同步完成后主动跑一次 DB 聚合 + 回写 Redis | 避免同步后首屏冷查询又走一次 DB |
| 2 | `backend/app/routes/token_usage.py` `/sync` | 改为 `async def`，用 `asyncio.to_thread` 提交后台线程后立即返回 202 | 当前接口阻塞等待同步完成，改为立即返回 |
| 3 | `backend/app/services/token_usage_background_sync.py` | 同步完成后调用 `warm_query_cache(user_id)` | 后台同步后预换热数据 |

**warm_query_cache 函数设计**：

```python
def warm_query_cache(user_id: str) -> None:
    """
    同步完成后预热常用查询缓存，避免首屏冷查询。

    预热策略：只预热最常用的 1 个组合（daily / 30 天 / source=all / 无筛选），
    避免预热过多组合造成资源浪费。用户实际访问其他组合时仍走正常"未命中→DB→回写"路径。
    """
    from app.models.base import SessionLocal
    from app.models.token_usage_models import TokenUsageRecord

    db = SessionLocal()
    try:
        # 仅当该用户有数据时才预热，避免空查询
        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            return

        # 调用与 /summary 相同的 DB 聚合逻辑构建 payload，再写 Redis
        # 具体实现时，把 /summary 中"DB 聚合 → 构建 payload"提取为公共函数
        # build_summary_payload(db, user_id, ...)，本函数与 /summary 共用，保证口径一致
        payload = _build_summary_payload(db, user_id)
        if payload:
            set_query_cached_data(
                source="all",
                report_type="daily",
                days=30,
                group_by="none",
                user_id=user_id,
                data=payload,
            )
    finally:
        db.close()
```

> 实现要点：把 `/summary` 中"DB 聚合 → 构建 payload"的逻辑提取为公共函数 `_build_summary_payload()`，供路由和预热函数共用，确保两者输出完全一致。

#### 配置调整

| 配置项 | 当前推测值 | 新值 | 原因 |
|--------|-----------|------|------|
| `CACHE_REDIS_TOKEN_USAGE_TTL` | ~300s | **300s** | 与同步间隔一致，无浪费 |
| `TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS` | 需确认 | **300s** | 5 分钟同步一次 |

#### 前端改动（1 处）

| # | 文件 | 改动 | 原因 |
|---|------|------|------|
| 1 | `frontend/src/components/Tools/TokenUsage.tsx` `handleSync` | 调用 `/sync` 后不再 await，直接 showToast "后台同步已启动"，不阻塞 UI | 当前 await 等同步完成才刷新，改为乐观通知 |

**前端同步按钮交互**：

```typescript
const handleSync = async () => {
  setSyncing(true);
  setSyncError(null);
  try {
    const result = await syncTokenUsage();  // POST /sync
    showToast(result.message || '后台同步已启动', 'success', 3000);
    // 不再 await 同步完成，30 秒后轮询自动刷新
  } catch (e: any) {
    setSyncError(e.message || '同步启动失败');
  } finally {
    setSyncing(false);
  }
};
```

> 前端轮询（30s `useTokenUsagePolling` → `summary.refresh({ silent: true })`）保持不动——它读的是 Redis 缓存，轻量不会产生额外 DB 压力。

#### 不动的部分

- summary/details 的 DB 聚合 SQL 已经用 GROUP BY，不改为全量拉取
- `_build_dimension_data` / `_query_dimension_data` 已在 Python 内存聚合维度数据，不做更细粒度的 SQL 物化视图
- 设备列表 `/devices` 已有 5 分钟 Redis 缓存，不动

### 4. 错误处理

| 场景 | 处理策略 |
|------|---------|
| **CLI 抓取失败** | `sync_token_usage` 返回 errors 列表，记 `TokenUsageSyncLog` status=failed；读路径不受影响（返回上次缓存数据） |
| **Redis 不可用** | `get_redis_client()` 返回 None → 所有缓存读走 DB，缓存写静默跳过，不影响主流程 |
| **DB 连接池耗尽** | `sync_token_usage` 阶段 2 独占 1 个连接，时间 < 100ms；读路径无独占，不会互斥 |
| **手动同步并发** | `acquire_refresh_lock` per-user 串行；重复点击返回 `locked=True` + ttl_seconds，前端 toast 提示 |
| **后台任务崩溃** | `_background_sync_loop` 有 try/except，单轮崩溃不会停掉循环，下次间隔继续 |
| **device_id 变更** | 同步完成后 `invalidate_user_query_cache` 清除所有用户级缓存，`warm_query_cache` 重建 |
| **首次进页面且无缓存** | summary/details 走 DB 聚合 SQL，< 500ms，可接受 |

**日志要求**（CLAUDE.md 强制）：
- 后台同步每轮开始/结束：记录 `user_count, elapsed_ms, synced/failed`
- 缓存命中/未命中：记录 `key, hit/miss`
- 手动同步请求：记录 `user_id, triggered_at`
- 缓存预热：记录 `user_id, warmed_queries, elapsed_ms`

### 5. 测试策略

#### 后端单元测试

- `warm_query_cache()`：mock Redis + DB，验证同步后缓存被正确预热
- `/sync` 接口：验证返回 202，后台线程已启动，不阻塞
- `sync_token_usage()`：已有单元测试，保持不动

#### 前端集成测试

- 进入页面 → 确认首屏无 loading 长等待（< 1s）
- 点击"同步数据"按钮 → 确认不阻塞，立即提示"后台同步已启动"
- 等待 30 秒 → 确认轮询自动刷新 → 新数据展示
- 检查浏览器 Console → 无错误

#### 性能验证

- 首屏 summary 接口响应时间：< 500ms（缓存未命中）/ < 10ms（缓存命中）
- 首屏 details 接口响应时间：< 500ms（缓存未命中）/ < 10ms（缓存命中）
- 同步完成到数据可见延迟：< 60 秒（同步完成 + 轮询间隔 30s）

## 实施计划

1. 修改 `token_usage_cache.py`，新增 `warm_query_cache()` 函数
2. 修改 `token_usage.py` `/sync` 接口，改为 `async def` + `asyncio.to_thread`
3. 修改 `token_usage_background_sync.py`，同步完成后调用 `warm_query_cache()`
4. 修改 `TokenUsage.tsx` `handleSync`，不再 await，直接 toast 提示
5. 修改配置 `CACHE_REDIS_TOKEN_USAGE_TTL = 300`、`TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS = 300`
6. 运行后端单元测试
7. 浏览器验证前端页面加载性能

## 验收标准

- ✅ 首屏加载时间 < 1 秒（缓存命中时 < 100ms）
- ✅ 手动点击"同步数据"不阻塞 UI，立即返回
- ✅ 同步完成后 60 秒内页面自动展示新数据
- ✅ Redis 缓存命中时接口响应 < 10ms
- ✅ 缓存未命中时接口响应 < 500ms
- ✅ 浏览器 Console 无错误
