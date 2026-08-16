# Token 统计数据 Redis 缓存实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Token 消耗统计页面添加 Redis 缓存层，将页面加载时间从数秒降至 <100ms，支持每小时自动刷新和手动刷新。

**Architecture:** 后端通过 Redis 缓存 CLI 执行结果，前端通过现有 API 获取缓存数据。定时任务在后台每小时预刷新常用查询，确保用户访问时数据已是最新。

**Tech Stack:** FastAPI, Redis (redis-py), Python asyncio, React 18

---

### 当前状态

- 后端文件 `backend/app/routes/token_usage.py` 直接调用 CLI 获取数据
- 已有内存缓存（`usage_fetcher.py` 中 5 分钟 TTL）
- 项目已安装 `redis>=5.0.0` 依赖
- 已有 Redis 工具服务（`app/services/redis_tool_service.py`）和限流器（`app/core/rate_limiter.py`）
- 前端 `frontend/src/components/Tools/TokenUsage.tsx` 已有刷新按钮

### 配置信息

Redis 配置（已提供）：
- Host: <redis-host>
- Port: 6379
- Database: 0
- 密码: <redis-password>

---

### Phase 1: Redis 配置和缓存服务

### Task 1: 配置 Redis 连接参数

**Files:**
- Modify: `backend/app/config/config.py`
- Modify: `backend/.env`

在 `config.py` 中添加 Redis 缓存配置：

```python
class Settings(BaseSettings):
    # ... 现有配置保持不变 ...
    
    # Redis Cache for Token Usage
    CACHE_REDIS_HOST: str = "<redis-host>"
    CACHE_REDIS_PORT: int = 6379
    CACHE_REDIS_DB: int = 0
    CACHE_REDIS_PASSWORD: str = ""
    CACHE_REDIS_TOKEN_USAGE_TTL: int = 3600  # 1 小时
```

在 `.env` 中添加：
```env
CACHE_REDIS_HOST=<redis-host>
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_REDIS_PASSWORD=<redis-password>
CACHE_REDIS_TOKEN_USAGE_TTL=3600
```

Run: `cd backend && python -c "from app.config.config import settings; print(settings.CACHE_REDIS_HOST)"`
Expected: 输出 `<redis-host>`

Commit:
```bash
git add backend/app/config/config.py backend/.env
git commit -m "feat: 添加 Redis 缓存配置参数"
```

### Task 2: 创建 Redis 缓存服务

**Files:**
- Create: `backend/app/services/token_usage_cache.py`
- Test: 手动测试

创建缓存服务文件：

```python
"""Token 统计数据 Redis 缓存服务"""

import json
import logging
from typing import Optional
import redis
from app.config.config import settings

logger = logging.getLogger(__name__)


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端连接"""
    try:
        client = redis.Redis(
            host=settings.CACHE_REDIS_HOST,
            port=settings.CACHE_REDIS_PORT,
            db=settings.CACHE_REDIS_DB,
            password=settings.CACHE_REDIS_PASSWORD if settings.CACHE_REDIS_PASSWORD else None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis 连接失败，将使用直连模式: {e}")
        return None


def _build_cache_key(source: str, report_type: str, days: int, 
                     since: str = None, until: str = None,
                     breakdown: bool = False, by: str = None) -> str:
    """构建缓存 Key"""
    parts = [
        "token_usage",
        source,
        report_type,
        str(days),
        since or "",
        until or "",
        "1" if breakdown else "0",
        by or "",
    ]
    return ":".join(parts)


def get_cached_data(source: str, report_type: str, days: int,
                    since: str = None, until: str = None,
                    breakdown: bool = False, by: str = None) -> Optional[dict]:
    """从 Redis 获取缓存数据"""
    client = get_redis_client()
    if not client:
        return None
    
    key = _build_cache_key(source, report_type, days, since, until, breakdown, by)
    try:
        data = client.get(key)
        if data:
            logger.info(f"缓存命中: {key}")
            return json.loads(data)
        logger.info(f"缓存未命中: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis 读取失败: {e}")
        return None


def set_cached_data(source: str, report_type: str, days: int, data: dict,
                    since: str = None, until: str = None,
                    breakdown: bool = False, by: str = None) -> bool:
    """将数据写入 Redis 缓存"""
    client = get_redis_client()
    if not client:
        return False
    
    key = _build_cache_key(source, report_type, days, since, until, breakdown, by)
    try:
        client.setex(key, settings.CACHE_REDIS_TOKEN_USAGE_TTL, json.dumps(data))
        logger.info(f"缓存已写入: {key}, TTL={settings.CACHE_REDIS_TOKEN_USAGE_TTL}s")
        return True
    except Exception as e:
        logger.warning(f"Redis 写入失败: {e}")
        return False


def invalidate_cache() -> bool:
    """清除所有 Token Usage 缓存"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        keys = client.keys("token_usage:*")
        if keys:
            client.delete(*keys)
            logger.info(f"已清除 {len(keys)} 个缓存 Key")
        return True
    except Exception as e:
        logger.warning(f"Redis 缓存清除失败: {e}")
        return False


def invalidate_single_cache(source: str, report_type: str, days: int,
                           since: str = None, until: str = None,
                           breakdown: bool = False, by: str = None) -> bool:
    """清除单个缓存 Key"""
    client = get_redis_client()
    if not client:
        return False
    
    key = _build_cache_key(source, report_type, days, since, until, breakdown, by)
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis 单 Key 清除失败: {e}")
        return False
```

Run: `cd backend && python -m py_compile app/services/token_usage_cache.py`
Expected: 无输出（语法正确）

Commit:
```bash
git add backend/app/services/token_usage_cache.py
git commit -m "feat: 创建 Token Usage Redis 缓存服务"
```

---

### Phase 2: 修改 API 路由整合缓存

### Task 3: 修改 token_usage.py 路由添加缓存逻辑

**Files:**
- Modify: `backend/app/routes/token_usage.py`

导入缓存服务并修改 `get_token_usage` 函数：

```python
# 在文件顶部添加导入
from app.services.token_usage_cache import get_cached_data, set_cached_data, invalidate_cache

# 在响应模型添加缓存元数据
class UsageResponse(BaseModel):
    items: list[UsageItem]
    summary: UsageSummary
    cached: bool = False  # 新增：标识是否来自缓存
    cache_time: Optional[str] = None  # 新增：缓存时间
```

修改 `get_token_usage` 函数：

```python
@router.post("", response_model=UsageResponse)
async def get_token_usage(req: UsageRequest):
    """获取 Token 消耗统计数据（优先从缓存读取）"""
    # 参数验证保持不变...
    
    # 1. 尝试从缓存读取
    cached = get_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        since=req.since,
        until=req.until,
        breakdown=req.breakdown,
        by=req.by,
    )
    
    if cached:
        logger.info("返回缓存数据")
        return UsageResponse(
            items=cached["items"],
            summary=cached["summary"],
            cached=True,
            cache_time=cached.get("cache_time"),
        )
    
    # 2. 缓存未命中，执行 CLI 调用
    if req.source == "claude":
        since = req.since
        until = req.until
        if not since and req.days:
            since_date = datetime.now() - timedelta(days=req.days)
            since = since_date.strftime("%Y%m%d")
        # ccusage monthly/weekly 不支持 --since，统一取 daily 后由后端聚合
        raw = UsageFetcher.fetch_claude(
            report_type="daily",
            since=since,
            until=until,
            breakdown=req.breakdown,
        )
    else:
        raw = UsageFetcher.fetch_opencode(
            days=req.days,
            by=req.by,
        )

    if "error" in raw:
        tool_name = "ccusage" if req.source == "claude" else "opencode-usage"
        raise HTTPException(
            500,
            detail=f"{tool_name} 数据获取失败: {raw['error']}",
        )

    items = normalize_entries(raw, req.type)
    items = apply_aggregation(items, req.type)
    summary = compute_summary(items)
    
    # 3. 写入缓存
    cache_data = {
        "items": [item.dict() for item in items],
        "summary": summary.dict(),
        "cache_time": datetime.now().isoformat(),
    }
    set_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        data=cache_data,
        since=req.since,
        until=req.until,
        breakdown=req.breakdown,
        by=req.by,
    )
    
    return UsageResponse(
        items=items,
        summary=summary,
        cached=False,
        cache_time=cache_data["cache_time"],
    )
```

Run: `cd backend && python -m py_compile app/routes/token_usage.py`
Expected: 无输出

测试: `curl -s -X POST http://localhost:19092/api/token-usage -H "Content-Type: application/json" -d '{"source":"claude","type":"daily","days":7}' | python -m json.tool | grep -E '(cached|cache_time)'`

第一次调用 Expected: `"cached": false`
第二次调用 Expected: `"cached": true`, `"cache_time": "2026-04-24T..."`

Commit:
```bash
git add backend/app/routes/token_usage.py
git commit -m "feat: Token Usage API 整合 Redis 缓存读取逻辑"
```

### Task 4: 添加手动刷新端点

**Files:**
- Modify: `backend/app/routes/token_usage.py`

```python
@router.post("/refresh")
async def refresh_token_usage():
    """手动刷新所有 Token Usage 缓存"""
    invalidate_cache()
    return {"message": "缓存已清除，下次访问将重新获取数据"}
```

测试: `curl -s -X POST http://localhost:19092/api/token-usage/refresh | python -m json.tool`
Expected: `{"message": "缓存已清除，下次访问将重新获取数据"}`

Commit:
```bash
git add backend/app/routes/token_usage.py
git commit -m "feat: 添加手动刷新缓存端点"
```

---

### Phase 3: 后台定时刷新任务

### Task 5: 在 main.py 中添加定时刷新任务

**Files:**
- Modify: `backend/app/main.py`

```python
# 在文件顶部添加导入
import asyncio
from app.routes import token_usage
from app.utils.usage_fetcher import UsageFetcher
from app.routes.token_usage import normalize_entries, apply_aggregation, compute_summary
from app.services.token_usage_cache import set_cached_data

# 在 lifespan 函数中添加定时任务
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting application...")

    manager = get_manager()
    cleanup_task = asyncio.create_task(manager.start_cleanup_task())

    # 启动 OpenClaw 连接
    try:
        from app.services.openclaw_service import openclaw_service
        await openclaw_service.start()
    except Exception as e:
        logger.warning(f"OpenClaw 连接启动失败（功能将不可用）: {e}")

    # 启动 Token Usage 缓存刷新任务
    cache_refresh_task = asyncio.create_task(refresh_token_usage_cache_periodically())

    yield

    # 关闭时
    logger.info("Shutting down application...")

    try:
        from app.services.openclaw_service import openclaw_service
        await openclaw_service.stop()
    except Exception as e:
        logger.error(f"OpenClaw 关闭异常: {e}")

    cleanup_task.cancel()
    cache_refresh_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await cache_refresh_task
    except asyncio.CancelledError:
        pass


async def refresh_token_usage_cache_periodically():
    """每小时刷新 Token Usage 缓存"""
    REFRESH_INTERVAL = 3600  # 1 小时
    
    # 预刷新的查询组合
    queries = [
        {"source": "claude", "report_type": "daily", "days": 7},
        {"source": "claude", "report_type": "daily", "days": 30},
        {"source": "claude", "report_type": "daily", "days": 90},
        {"source": "claude", "report_type": "monthly", "days": 90},
        {"source": "claude", "report_type": "monthly", "days": 180},
        {"source": "claude", "report_type": "monthly", "days": 365},
        {"source": "opencode", "report_type": "daily", "days": 30},
    ]
    
    while True:
        try:
            logger.info("开始刷新 Token Usage 缓存...")
            for q in queries:
                await _refresh_single_cache(q["source"], q["report_type"], q["days"])
            logger.info(f"Token Usage 缓存刷新完成，下次刷新在 {REFRESH_INTERVAL} 秒后")
        except Exception as e:
            logger.error(f"Token Usage 缓存刷新失败: {e}")
        
        await asyncio.sleep(REFRESH_INTERVAL)


async def _refresh_single_cache(source: str, report_type: str, days: int):
    """刷新单个查询的缓存，使用线程池执行 CLI 调用"""
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(
        None,
        lambda: _fetch_raw_data(source, report_type, days)
    )
    
    if "error" in raw:
        logger.warning(f"缓存刷新失败 {source}/{report_type}/{days}天: {raw['error']}")
        return
    
    items = normalize_entries(raw, report_type)
    items = apply_aggregation(items, report_type)
    summary = compute_summary(items)
    
    cache_data = {
        "items": [item.dict() for item in items],
        "summary": summary.dict(),
        "cache_time": datetime.now().isoformat(),
    }
    
    set_cached_data(
        source=source,
        report_type=report_type,
        days=days,
        data=cache_data,
    )
    logger.info(f"缓存已刷新: {source}/{report_type}/{days}天")


def _fetch_raw_data(source: str, report_type: str, days: int) -> dict:
    """同步获取原始数据（在线程池中执行）"""
    if source == "claude":
        since_date = datetime.now() - timedelta(days=days)
        since = since_date.strftime("%Y%m%d")
        raw = UsageFetcher.fetch_claude(
            report_type="daily",
            since=since,
            breakdown=False,
        )
    else:
        raw = UsageFetcher.fetch_opencode(days=days)
    return raw
```

Run: `cd backend && python -m py_compile app/main.py`
Expected: 无输出

Commit:
```bash
git add backend/app/main.py
git commit -m "feat: 添加 Token Usage 缓存定时刷新任务"
```

---

### Phase 4: 前端更新

### Task 6: 更新前端 API 支持缓存元数据

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`

在 `UsageResponse` 接口中添加缓存字段：

```typescript
export interface UsageResponse {
  items: UsageItem[];
  summary: UsageSummary;
  cached?: boolean;
  cache_time?: string;
}

export async function refreshTokenUsage(): Promise<{ message: string }> {
  const response = await fetch(`${BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error('刷新缓存失败');
  }
  return response.json();
}
```

Commit:
```bash
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat: 前端 API 支持缓存元数据和手动刷新"
```

### Task 7: 更新前端组件显示缓存状态

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

在组件中添加缓存状态显示：

```typescript
// 在状态中添加
const [cacheTime, setCacheTime] = useState<string | null>(null);
const [isCached, setIsCached] = useState(false);

// 在 fetchData 中设置
const fetchData = useCallback(async () => {
  setLoading(true);
  setError(null);
  try {
    const result = await getTokenUsage({
      source,
      type: reportType,
      days,
    });
    setItems(result.items);
    setSummary(result.summary);
    setIsCached(result.cached || false);
    setCacheTime(result.cache_time || null);
    setCurrentPage(1);
  } catch (err: any) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}, [source, reportType, days]);

// 在 JSX 中修改刷新按钮并添加缓存时间显示
<div className="flex items-center justify-between mb-6">
  <h1 className="text-3xl font-bold text-slate-100">Token 消耗统计</h1>
  <div className="flex items-center gap-3">
    {cacheTime && (
      <span className="text-xs text-slate-500">
        {isCached ? '📦 缓存 ' : '🔄 实时 '}
        {new Date(cacheTime).toLocaleTimeString('zh-CN')}
      </span>
    )}
    <button
      onClick={handleRefresh}
      disabled={loading}
      className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium transition-colors"
    >
      {loading ? '刷新中...' : '刷新'}
    </button>
  </div>
</div>
```

Commit:
```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: Token Usage 页面显示缓存状态和时间"
```

---

### Phase 5: 验证和测试

### Task 8: 完整流程验证

Run:
1. `cd backend && uvicorn app.main:app --reload --port 19092`（重启后端加载新配置）
2. `cd frontend && npm run dev`（前端热重载）
3. 访问 `http://localhost:5178/tools/token-usage`
4. 观察：
   - 首次加载：数据较慢，显示"🔄 实时 XX:XX:XX"
   - 第二次加载：快速，显示"📦 缓存 XX:XX:XX"
   - 点击刷新：显示"刷新中..."，然后更新
5. 测试 Redis 不可用时的降级（可临时停止 Redis 或断网）

Commit: 无需提交

---

## 总结

以上计划分为 5 个 Phase，共 8 个 Task：
1. Phase 1: Redis 配置和缓存服务（Task 1-2）
2. Phase 2: API 路由整合缓存（Task 3-4）
3. Phase 3: 后台定时刷新任务（Task 5）
4. Phase 4: 前端更新（Task 6-7）
5. Phase 5: 验证和测试（Task 8）

每个 Task 都是 2-5 分钟的小型操作，遵循 TDD、DRY、YAGNI 原则，频繁提交。

计划已保存至 `docs/plans/2026-04-24-token-usage-redis-cache-implementation.md`。

---

计划完成并保存到 `docs/plans/2026-04-24-token-usage-redis-cache-implementation.md`。两个执行选项：

**1. 子代理驱动**（当前会话）- 我分派子代理逐个执行任务，任务之间进行代码审查，快速迭代

**2. 并行会话**（独立）- 开启新会话使用 executing-plans，批量执行带检查点

选择哪种方式？
