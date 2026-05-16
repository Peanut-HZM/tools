# Token Usage Refresh and Codex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/tools/token-usage` load quickly from Redis/DB, show trustworthy refresh metadata, refresh stale data once in the background, improve model statistics, and keep Codex/OpenClaw as truthful capability indicators until real usage data is available.

**Architecture:** Preserve the existing fast read path: Redis query cache first, DB aggregation second, no CLI on initial query. Add `sync_meta`, `model_summary`, Redis TTL metadata, and a user-level refresh lock. The frontend renders existing data immediately, then triggers a cooled-down background refresh only when the backend says data is stale.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Redis, Python 3.10+, React 18, TypeScript, Recharts, lucide-react, Vite.

---

## File Structure

- Modify `backend/app/services/token_usage_cache.py`: return cached payload with Redis TTL, write `cache_written_at`, add user query cache invalidation hooks where needed.
- Modify `backend/app/routes/token_usage.py`: add `SyncMeta`, `RefreshLockMeta`, `ModelSummaryItem`, model summary query, sync meta query, refresh request params, and user-level refresh lock.
- Create `backend/tests/test_token_usage_freshness.py`: helper tests for stale/fresh metadata, model summary grouping, and refresh lock metadata.
- Modify `frontend/src/api/tokenUsageApi.ts`: add `sync_meta`, `model_summary`, refresh params, and keep source type limited to implemented statistical sources in phase 1.
- Modify `frontend/src/components/Tools/TokenUsage.tsx`: fix Chinese UI text, add `DataFreshnessBadge`, implement 60-second stale refresh cooldown, use `model_summary`, show Codex/OpenClaw as capability only.
- Run backend checks, frontend build, and browser verification through `dev-services.py` when runtime checks are needed.

## Task 1: 后端 freshness 测试与缓存 TTL 元信息

**Files:**
- Modify: `backend/app/services/token_usage_cache.py`
- Create: `backend/tests/test_token_usage_freshness.py`

- [ ] **Step 1: Create failing tests**

Create `backend/tests/test_token_usage_freshness.py`:

```python
from datetime import datetime, timezone
from types import SimpleNamespace

from app.routes.token_usage import _build_sync_meta_from_values, _rows_to_model_summary


def test_build_sync_meta_marks_fresh_data():
    now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_success = datetime(2026, 5, 16, 11, 45, 0, tzinfo=timezone.utc)

    meta = _build_sync_meta_from_values(
        now=now,
        last_success_at=last_success,
        cache_written_at=last_success,
        cache_ttl_seconds=2700,
        configured_ttl_seconds=3600,
        sources_status=[],
        refresh_lock={"locked": False, "owner": None, "ttl_seconds": 0},
    )

    assert meta["is_stale"] is False
    assert meta["data_age_seconds"] == 900
    assert meta["cache_ttl_seconds"] == 2700
    assert meta["stale_reason"] is None
    assert meta["refresh_lock"]["locked"] is False


def test_build_sync_meta_marks_stale_data():
    now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_success = datetime(2026, 5, 16, 10, 30, 0, tzinfo=timezone.utc)

    meta = _build_sync_meta_from_values(
        now=now,
        last_success_at=last_success,
        cache_written_at=None,
        cache_ttl_seconds=0,
        configured_ttl_seconds=3600,
        sources_status=[],
        refresh_lock={"locked": False, "owner": None, "ttl_seconds": 0},
    )

    assert meta["is_stale"] is True
    assert meta["data_age_seconds"] == 5400
    assert meta["stale_reason"] == "数据超过 60 分钟未同步"


def test_rows_to_model_summary_keeps_source_model_unique():
    rows = [
        SimpleNamespace(
            source="claude",
            model="sonnet",
            input_tokens=10,
            output_tokens=5,
            cache_creation_tokens=2,
            cache_read_tokens=3,
            total_tokens=20,
            total_cost=0.1,
        ),
        SimpleNamespace(
            source="opencode",
            model="sonnet",
            input_tokens=7,
            output_tokens=8,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            total_tokens=15,
            total_cost=0.2,
        ),
    ]

    summary = _rows_to_model_summary(rows)

    assert len(summary) == 2
    assert summary[0]["source"] == "opencode"
    assert summary[0]["model"] == "sonnet"
    assert summary[0]["display_model"] == "sonnet"
    assert summary[1]["source"] == "claude"
```

- [ ] **Step 2: Run tests to verify missing helpers**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py -v
```

Expected: FAIL because route helpers are not implemented.

- [ ] **Step 3: Add TTL-aware cache read helper**

In `backend/app/services/token_usage_cache.py`, add:

```python
from datetime import datetime
```

Add helper after `get_query_cached_data`:

```python
def get_query_cached_payload(
    source: str,
    report_type: str,
    days: int,
    group_by: str,
    user_id: str,
    device_id: str = None,
) -> Optional[dict]:
    """读取查询缓存，同时返回 Redis 剩余 TTL。"""
    client = get_redis_client()
    if not client:
        return None

    key = _build_query_cache_key(source, report_type, days, group_by, user_id, device_id)
    try:
        data = client.get(key)
        if not data:
            logger.info(f"查询缓存未命中: {key}")
            return None
        ttl = client.ttl(key)
        payload = json.loads(data)
        payload["_cache_ttl_seconds"] = max(int(ttl), 0)
        logger.info(f"查询缓存命中: {key}, TTL={ttl}s")
        return payload
    except Exception as e:
        logger.warning(f"Redis 查询缓存读取失败: {e}")
        return None
```

Update `set_query_cached_data` to write a cache timestamp:

```python
    key = _build_query_cache_key(source, report_type, days, group_by, user_id, device_id)
    try:
        payload = dict(data or {})
        payload.setdefault("cache_written_at", datetime.now().isoformat())
        client.setex(
            key,
            settings.CACHE_REDIS_TOKEN_USAGE_TTL,
            json.dumps(payload, ensure_ascii=False),
        )
```

- [ ] **Step 4: Commit cache/test scaffold**

```bash
git add backend/app/services/token_usage_cache.py backend/tests/test_token_usage_freshness.py
git commit -m "test: cover token usage freshness metadata"
```

## Task 2: 后端 sync_meta、model_summary 与缓存一致性

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `backend/tests/test_token_usage_freshness.py`

- [ ] **Step 1: Add response models**

In `backend/app/routes/token_usage.py`, import settings and cache helper:

```python
from app.config.config import settings
from app.services.token_usage_cache import get_query_cached_payload
```

Add models after `DeviceInfo`:

```python
class RefreshLockMeta(BaseModel):
    locked: bool = False
    owner: Optional[str] = None
    ttl_seconds: int = 0


class ModelSummaryItem(BaseModel):
    source: str
    model: str
    display_model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float


class SyncMeta(BaseModel):
    last_synced_at: Optional[str] = None
    last_success_at: Optional[str] = None
    cache_written_at: Optional[str] = None
    cache_ttl_seconds: int = 0
    cache_expires_at: Optional[str] = None
    data_age_seconds: Optional[int] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    refresh_lock: RefreshLockMeta = Field(default_factory=RefreshLockMeta)
    sources_status: list[dict] = Field(default_factory=list)
```

Extend `DbUsageResponse`:

```python
    model_summary: list[ModelSummaryItem] = Field(default_factory=list)
    sync_meta: SyncMeta = Field(default_factory=SyncMeta)
```

- [ ] **Step 2: Add helper functions**

Add near `compute_db_summary`:

```python
def _to_iso(value) -> Optional[str]:
    """将数据库时间安全转换为 ISO 字符串。"""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _parse_cache_time(value: Optional[str]):
    """解析缓存写入时间，解析失败时返回 None。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _display_model_name(model: str) -> str:
    """生成模型展示名，同时保留原始模型名用于排查。"""
    if not model or model == "_total":
        return "未知模型"
    return model


def _build_sync_meta_from_values(
    now: datetime,
    last_success_at,
    cache_written_at,
    cache_ttl_seconds: int,
    configured_ttl_seconds: int,
    sources_status: list[dict],
    refresh_lock: dict,
) -> dict:
    """根据同步日志和缓存 TTL 计算数据新鲜度。"""
    last_dt = last_success_at
    if last_dt and getattr(last_dt, "tzinfo", None) is None and getattr(now, "tzinfo", None):
        last_dt = last_dt.replace(tzinfo=now.tzinfo)
    data_age_seconds = int((now - last_dt).total_seconds()) if last_dt else None
    stale_limit_minutes = max(int(configured_ttl_seconds / 60), 1)
    is_stale = last_dt is None or (data_age_seconds is not None and data_age_seconds > configured_ttl_seconds)

    stale_reason = None
    if last_dt is None:
        stale_reason = "尚未成功同步"
    elif is_stale:
        stale_reason = f"数据超过 {stale_limit_minutes} 分钟未同步"

    cache_expires_at = None
    if cache_written_at and cache_ttl_seconds > 0:
        written = cache_written_at
        if getattr(written, "tzinfo", None) is None and getattr(now, "tzinfo", None):
            written = written.replace(tzinfo=now.tzinfo)
        cache_expires_at = _to_iso(written + timedelta(seconds=cache_ttl_seconds))

    return {
        "last_synced_at": _to_iso(last_success_at),
        "last_success_at": _to_iso(last_success_at),
        "cache_written_at": _to_iso(cache_written_at),
        "cache_ttl_seconds": max(int(cache_ttl_seconds or 0), 0),
        "cache_expires_at": cache_expires_at,
        "data_age_seconds": data_age_seconds,
        "is_stale": is_stale,
        "stale_reason": stale_reason,
        "refresh_lock": refresh_lock,
        "sources_status": sources_status,
    }


def _rows_to_model_summary(rows) -> list[dict]:
    """将按 source/model 聚合的行转换为前端模型汇总。"""
    result = []
    for row in rows:
        model = row.model or "unknown"
        result.append({
            "source": row.source or "unknown",
            "model": model,
            "display_model": _display_model_name(model),
            "input_tokens": int(row.input_tokens or 0),
            "output_tokens": int(row.output_tokens or 0),
            "cache_creation_tokens": int(row.cache_creation_tokens or 0),
            "cache_read_tokens": int(row.cache_read_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
            "total_cost": round(float(row.total_cost or 0), 4),
        })
    return sorted(result, key=lambda item: (item["total_cost"], item["total_tokens"]), reverse=True)
```

- [ ] **Step 3: Add DB meta queries**

Add:

```python
def _get_sync_meta(db, user_id: str, req: DbQueryRequest, cached_payload: Optional[dict]) -> dict:
    """读取同步日志并合成前端可展示的数据新鲜度。"""
    filters = [TokenUsageSyncLog.user_id == user_id]
    if req.source != "all":
        filters.append(TokenUsageSyncLog.source == req.source)

    latest_success = db.query(TokenUsageSyncLog).filter(
        *filters,
        TokenUsageSyncLog.status == "success",
    ).order_by(TokenUsageSyncLog.synced_at.desc()).first()

    latest_logs = db.query(TokenUsageSyncLog).filter(*filters).order_by(
        TokenUsageSyncLog.synced_at.desc()
    ).limit(20).all()

    seen_sources = set()
    sources_status = []
    for row in latest_logs:
        if row.source in seen_sources:
            continue
        seen_sources.add(row.source)
        sources_status.append({
            "source": row.source,
            "status": row.status,
            "records_count": row.records_count,
            "synced_at": _to_iso(row.synced_at),
            "error_message": row.error_message,
        })

    return _build_sync_meta_from_values(
        now=datetime.now(),
        last_success_at=latest_success.synced_at if latest_success else None,
        cache_written_at=_parse_cache_time((cached_payload or {}).get("cache_written_at")),
        cache_ttl_seconds=int((cached_payload or {}).get("_cache_ttl_seconds") or 0),
        configured_ttl_seconds=settings.CACHE_REDIS_TOKEN_USAGE_TTL,
        sources_status=sources_status,
        refresh_lock={"locked": False, "owner": None, "ttl_seconds": 0},
    )


def _execute_model_summary_query(db, user_id: str, req: DbQueryRequest, since_date: datetime):
    """按 source/model 聚合模型统计，避免前端从日期行猜测。"""
    filters = [
        TokenUsageRecord.user_id == user_id,
        TokenUsageRecord.record_date >= since_date.date(),
    ]
    if req.source != "all":
        filters.append(TokenUsageRecord.source == req.source)
    if req.device_id:
        filters.append(TokenUsageRecord.device_id == req.device_id)

    return db.query(
        TokenUsageRecord.source.label("source"),
        TokenUsageRecord.model.label("model"),
        func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
        func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
        func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
        func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
        func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
        func.sum(TokenUsageRecord.total_cost).label("total_cost"),
    ).filter(*filters).group_by(
        TokenUsageRecord.source,
        TokenUsageRecord.model,
    ).all()
```

- [ ] **Step 4: Wire `/query`**

Use `get_query_cached_payload` instead of `get_query_cached_data`. For cached returns, open DB only to compute `sync_meta`:

```python
cached = get_query_cached_payload(...)
if cached:
    db = SessionLocal()
    try:
        sync_meta = _get_sync_meta(db, user_id, req, cached)
    finally:
        db.close()
    return DbUsageResponse(
        items=[DbUsageItem(**item) for item in cached["items"]],
        summary=UsageSummary(**cached["summary"]),
        devices=cached.get("devices", []),
        cached=True,
        model_summary=[ModelSummaryItem(**item) for item in cached.get("model_summary", [])],
        sync_meta=SyncMeta(**sync_meta),
    )
```

For DB returns, compute and cache model summary:

```python
model_summary = _rows_to_model_summary(_execute_model_summary_query(db, user_id, req, since_date))
sync_meta = _get_sync_meta(db, user_id, req, None)
cache_payload = {
    "items": [item.model_dump() for item in items],
    "summary": summary.model_dump(),
    "devices": devices,
    "model_summary": model_summary,
}
```

Return `model_summary` and `sync_meta` in every branch, including empty results.

- [ ] **Step 5: Run tests**

```bash
cd backend
pytest tests/test_token_usage_freshness.py -v
python -m py_compile app/routes/token_usage.py app/services/token_usage_cache.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/services/token_usage_cache.py backend/tests/test_token_usage_freshness.py
git commit -m "feat: expose token usage freshness metadata"
```

## Task 3: 后端用户级刷新锁与刷新参数

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `backend/app/services/token_usage_cache.py`

- [ ] **Step 1: Add refresh lock helpers**

In `backend/app/services/token_usage_cache.py`, add:

```python
def acquire_refresh_lock(user_id: str, owner: str, ttl_seconds: int = 120) -> dict:
    """获取用户级 Token Usage 刷新锁。"""
    client = get_redis_client()
    if not client:
        return {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": 0}

    key = f"token_usage:refresh_lock:{user_id}"
    try:
        acquired = client.set(key, owner, nx=True, ex=ttl_seconds)
        if acquired:
            return {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": ttl_seconds}
        return {
            "acquired": False,
            "locked": True,
            "owner": client.get(key),
            "ttl_seconds": max(int(client.ttl(key)), 0),
        }
    except Exception as e:
        logger.warning(f"Token Usage 刷新锁获取失败，将继续刷新: {e}")
        return {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": 0}


def release_refresh_lock(user_id: str, owner: str) -> None:
    """释放用户级 Token Usage 刷新锁。"""
    client = get_redis_client()
    if not client:
        return
    key = f"token_usage:refresh_lock:{user_id}"
    try:
        if client.get(key) == owner:
            client.delete(key)
    except Exception as e:
        logger.warning(f"Token Usage 刷新锁释放失败: {e}")
```

- [ ] **Step 2: Add refresh request model**

In `backend/app/routes/token_usage.py`, import `uuid` and lock helpers:

```python
import uuid
from app.services.token_usage_cache import acquire_refresh_lock, release_refresh_lock
```

Add:

```python
class RefreshUsageRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=365, description="同步最近 N 天数据")
    background: bool = Field(default=False, description="是否为前端自动触发的静默刷新")
    reason: str = Field(default="manual", description="manual | stale")
```

- [ ] **Step 3: Update `/refresh`**

Change `refresh_cache` signature:

```python
async def refresh_cache(
    req: RefreshUsageRequest = Body(default_factory=RefreshUsageRequest),
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
```

Wrap sync with lock:

```python
    owner = str(uuid.uuid4())
    lock = acquire_refresh_lock(user_id, owner)
    if not lock["acquired"]:
        logger.info(f"用户 {user_id} Token Usage 刷新被锁拦截: {lock}")
        return {
            "message": "已有刷新任务进行中",
            "sources_synced": [],
            "total_records": 0,
            "errors": [],
            "locked": True,
            "lock_ttl_seconds": lock["ttl_seconds"],
        }

    try:
        logger.info(f"用户 {user_id} 刷新 Token Usage 数据: days={req.days}, background={req.background}, reason={req.reason}")
        invalidate_user_query_cache(user_id)
        result = sync_token_usage(user_id=user_id, days=req.days)
        invalidate_user_query_cache(user_id)
        result["message"] = "同步完成，缓存已刷新"
        result["locked"] = False
        return result
    finally:
        release_refresh_lock(user_id, owner)
```

- [ ] **Step 4: Compile**

```bash
cd backend
python -m py_compile app/routes/token_usage.py app/services/token_usage_cache.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/services/token_usage_cache.py
git commit -m "feat: guard token usage refresh with user lock"
```

## Task 4: 前端 API 类型与刷新时间组件

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Update API types**

In `frontend/src/api/tokenUsageApi.ts`, keep phase-1 statistical sources limited:

```typescript
export type TokenUsageSource = 'claude' | 'opencode' | 'all';
```

Add:

```typescript
export interface ModelSummaryItem {
  source: string;
  model: string;
  display_model: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
}

export interface SyncMeta {
  last_synced_at?: string | null;
  last_success_at?: string | null;
  cache_written_at?: string | null;
  cache_ttl_seconds: number;
  cache_expires_at?: string | null;
  data_age_seconds?: number | null;
  is_stale: boolean;
  stale_reason?: string | null;
  refresh_lock: {
    locked: boolean;
    owner?: string | null;
    ttl_seconds: number;
  };
  sources_status: Array<{
    source: string;
    status: string;
    records_count: number;
    synced_at?: string | null;
    error_message?: string | null;
  }>;
}
```

Extend `DbUsageResponse`:

```typescript
  model_summary: ModelSummaryItem[];
  sync_meta: SyncMeta;
```

Update `SyncTokenUsageResponse`:

```typescript
  locked?: boolean;
  lock_ttl_seconds?: number;
```

Update refresh:

```typescript
export async function refreshTokenUsage(params?: {
  days?: number;
  background?: boolean;
  reason?: 'manual' | 'stale';
}): Promise<SyncTokenUsageResponse> {
  const response = await fetch(`${BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      days: params?.days ?? 90,
      background: params?.background ?? false,
      reason: params?.reason ?? 'manual',
    }),
  });
  if (!response.ok) {
    throw await readError(response, '刷新失败');
  }
  return response.json();
}
```

- [ ] **Step 2: Add `DataFreshnessBadge`**

In `frontend/src/components/Tools/TokenUsage.tsx`, import `Clock` and `AlertTriangle`.

Add helpers:

```typescript
function formatRelativeTime(value?: string | null): string {
  if (!value) return '尚未同步';
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return '时间未知';
  const diffSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) return '刚刚更新';
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} 分钟前`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} 小时前`;
  return `${Math.floor(diffSeconds / 86400)} 天前`;
}

function formatDateTime(value?: string | null): string {
  if (!value) return '暂无记录';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未知';
  return date.toLocaleString('zh-CN', { hour12: false });
}
```

Add component:

```tsx
function DataFreshnessBadge({
  syncMeta,
  cached,
  refreshing,
  refreshError,
  onRefresh,
}: {
  syncMeta: SyncMeta | null;
  cached: boolean;
  refreshing: boolean;
  refreshError: string | null;
  onRefresh: () => void;
}) {
  const stale = Boolean(syncMeta?.is_stale);
  const locked = Boolean(syncMeta?.refresh_lock?.locked);
  const ttl = syncMeta?.cache_ttl_seconds ?? 0;
  const statusText = refreshing
    ? '后台更新中'
    : refreshError
      ? '刷新失败'
      : locked
        ? '其他窗口正在更新'
        : stale
          ? '数据已过期'
          : cached
            ? '缓存有效'
            : '数据库聚合';
  const statusClass = refreshing || locked
    ? 'border-sky-500/40 text-sky-200'
    : refreshError || stale
      ? 'border-amber-500/40 text-amber-200'
      : 'border-emerald-500/40 text-emerald-200';

  return (
    <div className={`min-w-[300px] rounded-md border bg-slate-900 px-3 py-2 text-xs ${statusClass}`}>
      <div className="mb-1 flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1 font-medium">
          {refreshError || stale ? <AlertTriangle className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
          {statusText}
        </span>
        <button onClick={onRefresh} disabled={refreshing} className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-slate-100 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50">
          {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          刷新
        </button>
      </div>
      <div className="space-y-0.5 text-slate-300">
        <div>最后同步：{formatRelativeTime(syncMeta?.last_success_at)}，{formatDateTime(syncMeta?.last_success_at)}</div>
        <div>缓存有效期：{ttl > 0 ? `剩余 ${Math.ceil(ttl / 60)} 分钟` : '未命中缓存'}</div>
        {syncMeta?.stale_reason && <div className="text-amber-200">{syncMeta.stale_reason}</div>}
        {refreshError && <div className="text-amber-200">{refreshError}</div>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build**

```bash
cd frontend
npm run build
```

Expected: PASS after importing `SyncMeta`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/tokenUsageApi.ts frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: add token usage freshness badge"
```

## Task 5: 前端静默刷新冷却与模型统计

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Add state**

Import API types:

```typescript
  type ModelSummaryItem,
  type SyncMeta,
```

Add state:

```typescript
  const [modelSummary, setModelSummary] = useState<ModelSummaryItem[]>([]);
  const [syncMeta, setSyncMeta] = useState<SyncMeta | null>(null);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const lastAutoRefreshRef = React.useRef<Record<string, number>>({});
```

- [ ] **Step 2: Store response metadata**

In `fetchData`:

```typescript
      setModelSummary(result.model_summary || []);
      setSyncMeta(result.sync_meta || null);
```

In clear handler:

```typescript
      setModelSummary([]);
      setSyncMeta(null);
      setRefreshError(null);
```

- [ ] **Step 3: Add cooled-down background refresh**

Add:

```typescript
  const queryKey = `${source}:${reportType}:${days}:${groupBy}:${selectedDevice || 'all'}`;

  useEffect(() => {
    if (!syncMeta?.is_stale || backgroundRefreshing || refreshing) return;
    const lastAt = lastAutoRefreshRef.current[queryKey] || 0;
    if (Date.now() - lastAt < 60_000) return;

    let cancelled = false;
    lastAutoRefreshRef.current[queryKey] = Date.now();

    async function refreshStaleData() {
      setBackgroundRefreshing(true);
      setRefreshError(null);
      try {
        const result = await refreshTokenUsage({ days: Math.max(days, 90), background: true, reason: 'stale' });
        if (result.locked) {
          if (!cancelled) setRefreshError('其他窗口正在更新数据');
          return;
        }
        if (!cancelled) {
          await loadDevices();
          await fetchData();
        }
      } catch (err: any) {
        if (!cancelled) {
          setRefreshError(err.message || '后台刷新失败，已保留当前数据');
        }
      } finally {
        if (!cancelled) setBackgroundRefreshing(false);
      }
    }

    refreshStaleData();
    return () => {
      cancelled = true;
    };
  }, [backgroundRefreshing, days, fetchData, loadDevices, queryKey, refreshing, syncMeta?.is_stale]);
```

- [ ] **Step 4: Use `model_summary` for pie chart**

Replace `modelData`:

```typescript
  const modelData = useMemo(() => {
    const sourceName = (sourceValue: string) => {
      if (sourceValue === 'claude') return 'Claude';
      if (sourceValue === 'opencode') return 'OpenCode';
      return sourceValue;
    };

    return modelSummary
      .map(item => ({
        name: `${sourceName(item.source)} · ${item.display_model || item.model || '未知模型'}`,
        value: item.total_cost,
        tokens: item.total_tokens,
      }))
      .filter(item => item.value > 0 || item.tokens > 0)
      .sort((a, b) => b.value - a.value || b.tokens - a.tokens)
      .slice(0, 8);
  }, [modelSummary]);
```

- [ ] **Step 5: Render badge**

In the header action area:

```tsx
          <DataFreshnessBadge
            syncMeta={syncMeta}
            cached={cached}
            refreshing={refreshing || backgroundRefreshing}
            refreshError={refreshError}
            onRefresh={handleRefresh}
          />
```

Update `handleRefresh`:

```typescript
      const result = await refreshTokenUsage({ days: Math.max(days, 90), background: false, reason: 'manual' });
      if (result.locked) {
        setRefreshError('已有刷新任务进行中，请稍后重试');
        return;
      }
```

- [ ] **Step 6: Build and commit**

```bash
cd frontend
npm run build
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: refresh stale token usage data once"
```

Expected: build passes before commit.

## Task 6: 中文文案、布局和 Codex/OpenClaw 能力边界

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Fix helper labels**

Use:

```typescript
function formatToken(num: number): string {
  if (num >= 100_000_000) return `${(num / 100_000_000).toFixed(1)} 亿`;
  if (num >= 10_000_000) return `${(num / 10_000_000).toFixed(1)} 千万`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)} 百万`;
  if (num >= 10_000) return `${(num / 10_000).toFixed(1)} 万`;
  return num.toLocaleString('zh-CN');
}

function sourceLabel(source: TokenUsageSource): string {
  if (source === 'claude') return 'Claude Code';
  if (source === 'opencode') return 'OpenCode';
  return '全部工具';
}

function healthLabel(ok: boolean): string {
  return ok ? '可用' : '不可用';
}
```

- [ ] **Step 2: Keep source select truthful**

Source options must be:

```tsx
<option value="all">全部工具</option>
<option value="claude">Claude Code</option>
<option value="opencode">OpenCode</option>
```

Do not add Codex/OpenClaw as filter options in phase 1.

- [ ] **Step 3: Show capability status**

Use a health grid data shape like:

```typescript
[
  { name: 'ccusage', ok: health.ccusage_installed, detail: 'Claude Code' },
  { name: 'opencode-usage', ok: health.opencode_usage_installed, detail: 'OpenCode' },
  { name: 'ccusage-opencode', ok: health.ccusage_opencode_installed, detail: 'OpenCode 历史数据' },
  { name: 'Codex/OpenClaw', ok: null, detail: '待接入真实 usage 数据' },
]
```

Render `ok === null` as `待接入` with neutral color, not red.

- [ ] **Step 4: Fix visible text**

Use these visible labels:

```tsx
按登录用户、设备和工具维度统计
Token 消耗统计
刷新
导出
清理
工具
维度
时间范围
设备
分组
图表
最近 7 天
最近 14 天
最近 30 天
最近 90 天
按天
按周
按月
全部设备
按日期汇总
按设备对比
按模型分析
柱状图
折线图
暂无图表数据
暂无模型成本数据
暂无数据。可以点击“刷新”采集当前用户和设备的数据。
```

- [ ] **Step 5: Build and commit**

```bash
cd frontend
npm run build
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix: restore token usage Chinese UI labels"
```

Expected: build passes before commit.

## Task 7: 验证

**Files:**
- No planned code changes.

- [ ] **Step 1: Backend checks**

```bash
cd backend
python -m py_compile app/routes/token_usage.py app/services/token_usage_cache.py app/services/token_usage_sync_service.py
ruff check app/routes/token_usage.py app/services/token_usage_cache.py app/services/token_usage_sync_service.py tests/test_token_usage_freshness.py
pytest tests/test_token_usage_freshness.py -v
```

Expected: PASS. If `ruff` is unavailable, record it and continue with compile plus pytest.

- [ ] **Step 2: Frontend build**

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 3: Runtime verification through service script**

Use the project service script only:

```bash
python dev-services.py status
python dev-services.py restart
```

Open `http://localhost:5178/tools/token-usage` and verify:

- Redis hit returns visible data without waiting for CLI.
- Right top badge shows last sync time and cache TTL.
- Stale data triggers one background refresh; same filter does not auto-refresh again within 60 seconds.
- Two windows do not start two refresh jobs; one sees lock/other window status.
- Manual refresh handles lock and errors without clearing old charts.
- Claude/OpenCode stats remain correct.
- Codex/OpenClaw appears only as neutral capability status, not as a filter or total-stat source.
- Chinese UI text is readable and not garbled.

- [ ] **Step 4: Commit validation fixes only if needed**

```bash
git add backend frontend
git commit -m "fix: stabilize token usage freshness workflow"
```

Do not create an empty commit if no validation fixes were required.

## Self-Review

- Spec coverage: data freshness, cache priority, background refresh cooldown, user-level lock, model summary, Codex/OpenClaw phase boundary, failure states, observability, and validation are covered.
- Placeholder scan: no unresolved TBD/TODO steps remain.
- Type consistency: phase-1 `TokenUsageSource` remains `'claude' | 'opencode' | 'all'`; Codex/OpenClaw stays a capability status until real data is available.
