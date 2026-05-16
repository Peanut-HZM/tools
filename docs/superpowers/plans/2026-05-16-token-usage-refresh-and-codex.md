# Token Usage Refresh and Codex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/tools/token-usage` load fast from cache/DB, show trustworthy data freshness metadata, refresh stale data in the background, improve model statistics, and prepare a truthful Codex/OpenClaw capability path.

**Architecture:** Keep the existing Redis -> DB query path as the fast read path. Add explicit freshness metadata from Redis TTL and `token_usage_sync_log`, then let the frontend trigger a non-blocking refresh only when stale. Model statistics become a first-class `model_summary` response instead of being inferred from daily rows.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Redis, Python 3.10+, React 18, TypeScript, Recharts, lucide-react, Vite.

---

## File Structure

- Modify `backend/app/services/token_usage_cache.py`: return cached payload with Redis TTL and write `cache_written_at`.
- Modify `backend/app/routes/token_usage.py`: add `SyncMeta` and `ModelSummaryItem`, compute sync freshness, return model summary, accept refresh parameters.
- Modify `backend/app/services/token_usage_sync_service.py`: normalize model names more consistently and prepare source validation without adding fake Codex data.
- Create `backend/tests/test_token_usage_freshness.py`: unit tests for freshness metadata and model aggregation helpers.
- Modify `frontend/src/api/tokenUsageApi.ts`: add `sync_meta`, `model_summary`, `codex/openclaw` source types, and refresh parameters.
- Modify `frontend/src/components/Tools/TokenUsage.tsx`: fix visible Chinese text, add `DataFreshnessBadge`, implement stale background refresh, use `model_summary`.
- Run validation commands from project roots.

## Task 1: 后端缓存元信息

**Files:**
- Modify: `backend/app/services/token_usage_cache.py`
- Test: `backend/tests/test_token_usage_freshness.py`

- [ ] **Step 1: Add tests for cache metadata shape**

Create `backend/tests/test_token_usage_freshness.py` with:

```python
from datetime import datetime, timezone

from app.routes.token_usage import _build_sync_meta_from_values


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
    )

    assert meta["is_stale"] is False
    assert meta["data_age_seconds"] == 900
    assert meta["cache_ttl_seconds"] == 2700
    assert meta["stale_reason"] is None


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
    )

    assert meta["is_stale"] is True
    assert meta["data_age_seconds"] == 5400
    assert meta["stale_reason"] == "数据超过 60 分钟未同步"
```

- [ ] **Step 2: Run tests to verify helper is missing**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py -v
```

Expected: FAIL because `_build_sync_meta_from_values` is not implemented.

- [ ] **Step 3: Add TTL-aware cache reads and writes**

In `backend/app/services/token_usage_cache.py`, add this helper:

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

Update `set_query_cached_data` before `json.dumps`:

```python
    payload = dict(data or {})
    payload.setdefault("cache_written_at", __import__("datetime").datetime.now().isoformat())
```

Then serialize `payload` instead of `data`.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py -v
```

Expected: still FAIL until Task 2 adds route helpers.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/token_usage_cache.py backend/tests/test_token_usage_freshness.py
git commit -m "test: add token usage freshness metadata coverage"
```

## Task 2: 后端查询响应增加 freshness 和 model_summary

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `backend/tests/test_token_usage_freshness.py`

- [ ] **Step 1: Add model summary test**

Append to `backend/tests/test_token_usage_freshness.py`:

```python
from datetime import date
from types import SimpleNamespace

from app.routes.token_usage import _rows_to_model_summary


def test_rows_to_model_summary_uses_source_and_model():
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

    assert summary[0]["source"] == "opencode"
    assert summary[0]["model"] == "sonnet"
    assert summary[0]["total_cost"] == 0.2
    assert summary[1]["source"] == "claude"
    assert summary[1]["total_tokens"] == 20
```

- [ ] **Step 2: Implement response models and helpers**

In `backend/app/routes/token_usage.py`, import `settings`:

```python
from app.config.config import settings
```

Add models after `DeviceInfo`:

```python
class ModelSummaryItem(BaseModel):
    source: str
    model: str
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
    sources_status: list[dict] = Field(default_factory=list)
```

Extend `DbUsageResponse`:

```python
    model_summary: list[ModelSummaryItem] = Field(default_factory=list)
    sync_meta: SyncMeta = Field(default_factory=SyncMeta)
```

Add helper functions near `compute_db_summary`:

```python
def _to_iso(value) -> Optional[str]:
    """将数据库时间安全转换为 ISO 字符串。"""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _build_sync_meta_from_values(
    now: datetime,
    last_success_at,
    cache_written_at,
    cache_ttl_seconds: int,
    configured_ttl_seconds: int,
    sources_status: list[dict],
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
        "sources_status": sources_status,
    }


def _rows_to_model_summary(rows) -> list[dict]:
    """将按 source/model 聚合的行转换为前端模型汇总。"""
    result = []
    for row in rows:
        result.append({
            "source": row.source or "unknown",
            "model": row.model or "unknown",
            "input_tokens": int(row.input_tokens or 0),
            "output_tokens": int(row.output_tokens or 0),
            "cache_creation_tokens": int(row.cache_creation_tokens or 0),
            "cache_read_tokens": int(row.cache_read_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
            "total_cost": round(float(row.total_cost or 0), 4),
        })
    return sorted(result, key=lambda item: item["total_cost"], reverse=True)
```

- [ ] **Step 3: Compute meta and model summary in `/query`**

Update imports from cache service:

```python
    get_query_cached_payload,
```

Replace cache read in `query_token_usage` with `get_query_cached_payload`. Before returning cached data, open DB and compute sync meta with latest sync log. For DB path, after `items = _execute_db_query(...)`, query model summary rows:

```python
model_rows = _execute_model_summary_query(db, user_id, req, since_date)
model_summary = _rows_to_model_summary(model_rows)
sync_meta = _get_sync_meta(db, user_id, req, cached_payload=None)
```

Add helpers:

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
    latest_by_source = db.query(TokenUsageSyncLog).filter(*filters).order_by(
        TokenUsageSyncLog.synced_at.desc()
    ).limit(10).all()
    seen = set()
    sources_status = []
    for row in latest_by_source:
        if row.source in seen:
            continue
        seen.add(row.source)
        sources_status.append({
            "source": row.source,
            "status": row.status,
            "records_count": row.records_count,
            "synced_at": _to_iso(row.synced_at),
            "error_message": row.error_message,
        })

    cache_written_at = None
    if cached_payload and cached_payload.get("cache_written_at"):
        try:
            cache_written_at = datetime.fromisoformat(cached_payload["cache_written_at"])
        except ValueError:
            cache_written_at = None

    return _build_sync_meta_from_values(
        now=datetime.now(),
        last_success_at=latest_success.synced_at if latest_success else None,
        cache_written_at=cache_written_at,
        cache_ttl_seconds=int((cached_payload or {}).get("_cache_ttl_seconds") or 0),
        configured_ttl_seconds=settings.CACHE_REDIS_TOKEN_USAGE_TTL,
        sources_status=sources_status,
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

- [ ] **Step 4: Run backend tests**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py -v
python -m py_compile app/routes/token_usage.py app/services/token_usage_cache.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/services/token_usage_cache.py backend/tests/test_token_usage_freshness.py
git commit -m "feat: expose token usage freshness metadata"
```

## Task 3: 刷新接口支持静默刷新参数

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `frontend/src/api/tokenUsageApi.ts`

- [ ] **Step 1: Extend refresh request model**

In `backend/app/routes/token_usage.py`, add:

```python
class RefreshUsageRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=365, description="同步最近 N 天数据")
    background: bool = Field(default=False, description="是否为前端自动触发的静默刷新")
```

Change `refresh_cache` signature:

```python
async def refresh_cache(
    req: RefreshUsageRequest = Body(default_factory=RefreshUsageRequest),
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
```

Update logging and sync:

```python
    logger.info(f"用户 {user_id} 刷新 Token Usage 数据: days={req.days}, background={req.background}")
    result = sync_token_usage(user_id=user_id, days=req.days)
```

- [ ] **Step 2: Extend frontend API**

In `frontend/src/api/tokenUsageApi.ts`, change:

```typescript
export async function refreshTokenUsage(params?: {
  days?: number;
  background?: boolean;
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
    }),
  });
  if (!response.ok) {
    throw await readError(response, '刷新失败');
  }
  return response.json();
}
```

- [ ] **Step 3: Validate syntax**

Run:

```bash
cd backend
python -m py_compile app/routes/token_usage.py
cd ../frontend
npm run build
```

Expected: backend compile passes; frontend build either passes or surfaces TypeScript errors to fix in this task.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/token_usage.py frontend/src/api/tokenUsageApi.ts
git commit -m "feat: support background token usage refresh"
```

## Task 4: 前端 API 类型与数据新鲜度组件

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Add API types**

In `frontend/src/api/tokenUsageApi.ts`, update source type:

```typescript
export type TokenUsageSource = 'claude' | 'opencode' | 'codex' | 'openclaw' | 'all';
```

Add interfaces:

```typescript
export interface ModelSummaryItem {
  source: string;
  model: string;
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

- [ ] **Step 2: Add component helpers**

In `frontend/src/components/Tools/TokenUsage.tsx`, add imports:

```typescript
  Clock,
  AlertTriangle,
```

Add helpers near `formatCurrency`:

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

Add `DataFreshnessBadge` inside the same file:

```tsx
function DataFreshnessBadge({
  syncMeta,
  cached,
  refreshing,
  onRefresh,
}: {
  syncMeta: SyncMeta | null;
  cached: boolean;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const stale = Boolean(syncMeta?.is_stale);
  const ttl = syncMeta?.cache_ttl_seconds ?? 0;
  const statusText = refreshing ? '后台更新中' : stale ? '数据已过期' : cached ? '缓存有效' : '数据库聚合';
  const statusClass = refreshing
    ? 'border-sky-500/40 text-sky-200'
    : stale
      ? 'border-amber-500/40 text-amber-200'
      : 'border-emerald-500/40 text-emerald-200';

  return (
    <div className={`rounded-md border bg-slate-900 px-3 py-2 text-xs ${statusClass}`}>
      <div className="mb-1 flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1 font-medium">
          {stale ? <AlertTriangle className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
          {statusText}
        </span>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-slate-100 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          刷新
        </button>
      </div>
      <div className="space-y-0.5 text-slate-300">
        <div>最后同步：{formatRelativeTime(syncMeta?.last_success_at)}，{formatDateTime(syncMeta?.last_success_at)}</div>
        <div>缓存有效期：{ttl > 0 ? `剩余 ${Math.ceil(ttl / 60)} 分钟` : '未命中缓存'}</div>
        {syncMeta?.stale_reason && <div className="text-amber-200">{syncMeta.stale_reason}</div>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Run build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS after importing `SyncMeta` type.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/tokenUsageApi.ts frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: add token usage freshness badge"
```

## Task 5: 前端加载策略和模型统计

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Add state**

Add imports from API:

```typescript
  type ModelSummaryItem,
  type SyncMeta,
```

Add state:

```typescript
  const [modelSummary, setModelSummary] = useState<ModelSummaryItem[]>([]);
  const [syncMeta, setSyncMeta] = useState<SyncMeta | null>(null);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
```

- [ ] **Step 2: Store response metadata**

In `fetchData`, after summary:

```typescript
      setModelSummary(result.model_summary || []);
      setSyncMeta(result.sync_meta || null);
```

In clear handler, reset:

```typescript
      setModelSummary([]);
      setSyncMeta(null);
```

- [ ] **Step 3: Add stale background refresh effect**

Add:

```typescript
  useEffect(() => {
    if (!syncMeta?.is_stale || backgroundRefreshing || refreshing) return;
    let cancelled = false;

    async function refreshStaleData() {
      setBackgroundRefreshing(true);
      try {
        await refreshTokenUsage({ days: Math.max(days, 90), background: true });
        if (!cancelled) {
          await loadDevices();
          await fetchData();
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || '后台刷新失败，已保留当前数据');
        }
      } finally {
        if (!cancelled) setBackgroundRefreshing(false);
      }
    }

    refreshStaleData();
    return () => {
      cancelled = true;
    };
  }, [backgroundRefreshing, days, fetchData, loadDevices, refreshing, syncMeta?.is_stale]);
```

- [ ] **Step 4: Replace model pie data**

Replace `modelData` with:

```typescript
  const modelData = useMemo(() => {
    const sourceName = (sourceValue: string) => {
      if (sourceValue === 'claude') return 'Claude';
      if (sourceValue === 'opencode') return 'OpenCode';
      if (sourceValue === 'codex') return 'Codex';
      if (sourceValue === 'openclaw') return 'OpenClaw';
      return sourceValue;
    };

    return modelSummary
      .map(item => ({
        name: `${sourceName(item.source)} · ${item.model || '未知模型'}`,
        value: item.total_cost,
        tokens: item.total_tokens,
      }))
      .filter(item => item.value > 0 || item.tokens > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [modelSummary]);
```

- [ ] **Step 5: Render badge in header**

In top-right action area, render:

```tsx
          <DataFreshnessBadge
            syncMeta={syncMeta}
            cached={cached}
            refreshing={refreshing || backgroundRefreshing}
            onRefresh={handleRefresh}
          />
```

Keep export and clear buttons beside or below it using responsive wrapping.

- [ ] **Step 6: Build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: refresh stale token usage data in background"
```

## Task 6: UI 文案修复和数据源能力展示

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Replace garbled Chinese strings**

Use these exact replacements in `TokenUsage.tsx`:

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
  if (source === 'codex') return 'Codex';
  if (source === 'openclaw') return 'OpenClaw';
  return '全部工具';
}

function healthLabel(ok: boolean): string {
  return ok ? '可用' : '不可用';
}
```

Visible labels:

```tsx
<span>按登录用户、设备和工具维度统计</span>
<h1 className="text-2xl font-semibold tracking-normal text-white">Token 消耗统计</h1>
```

Options:

```tsx
<option value="all">全部工具</option>
<option value="claude">Claude Code</option>
<option value="opencode">OpenCode</option>
<option value="codex">Codex</option>
<option value="openclaw">OpenClaw</option>
```

- [ ] **Step 2: Show Codex/OpenClaw as planned capability**

In health grid data, use:

```typescript
[
  ['ccusage', health.ccusage_installed, 'Claude Code'],
  ['opencode-usage', health.opencode_usage_installed, 'OpenCode'],
  ['ccusage-opencode', health.ccusage_opencode_installed, 'OpenCode 历史数据'],
  ['Codex/OpenClaw', false, '待接入真实 usage 数据'],
]
```

Render unavailable planned status as `待接入`, not as failure.

- [ ] **Step 3: Fix table and chart labels**

Use labels:

```typescript
const headers = ['日期', '分组', '输入 Token', '输出 Token', '缓存创建', '缓存读取', '总 Token', '成本 USD', '模型'];
```

Chart names:

```tsx
<Bar ... name="输入" />
<Bar ... name="输出" />
<Bar ... name="缓存" />
<Line ... name="成本" />
```

Empty text:

```tsx
暂无图表数据
暂无模型成本数据
暂无数据。可以点击“刷新”采集当前用户和设备的数据。
```

- [ ] **Step 4: Build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix: restore token usage Chinese UI labels"
```

## Task 7: 全量验证

**Files:**
- No planned code changes.

- [ ] **Step 1: Run backend checks**

Run:

```bash
cd backend
python -m py_compile app/routes/token_usage.py app/services/token_usage_cache.py app/services/token_usage_sync_service.py
ruff check app/routes/token_usage.py app/services/token_usage_cache.py app/services/token_usage_sync_service.py tests/test_token_usage_freshness.py
pytest tests/test_token_usage_freshness.py -v
```

Expected: PASS. If `ruff` is unavailable in the environment, record that and continue with compile plus pytest.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 3: Use dev services if runtime verification is needed**

Run only through the project service script:

```bash
python dev-services.py status
python dev-services.py restart
```

Open `http://localhost:5178/tools/token-usage` and verify:

- 首屏不等待 CLI 完成即可显示已有数据。
- 右上角显示最后同步时间和缓存剩余时间。
- 过期数据会显示后台更新中，完成后自动刷新。
- 手动刷新按钮可用，刷新失败时保留旧数据。
- Claude/OpenCode 统计正常，Codex/OpenClaw 不展示伪造数据。

- [ ] **Step 4: Final commit if validation required fixes**

If Step 1-3 required fixes:

```bash
git add backend frontend
git commit -m "fix: stabilize token usage freshness workflow"
```

If no fixes were required, do not create an empty commit.

## Self-Review

- Spec coverage: freshness metadata is covered in Tasks 1-2; background refresh is covered in Tasks 3 and 5; model accuracy is covered in Tasks 2 and 5; Codex/OpenClaw truthful boundary is covered in Task 6; validation is covered in Task 7.
- Placeholder scan: no `TBD`, generic TODO, or unresolved implementation steps remain.
- Type consistency: `sync_meta`, `model_summary`, `ModelSummaryItem`, `SyncMeta`, and `refreshTokenUsage({ days, background })` are introduced before use.
