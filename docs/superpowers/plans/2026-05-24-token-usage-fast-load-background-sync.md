# Token Usage Fast Load Background Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `/tools/token-usage` 首次进入慢和接口报错问题，让页面先快读 Redis/DB 已有数据，再由后端后台定时同步数据。

**Architecture:** 前端首屏只调用 `health`、`devices`、`query`，删除基于 `sync_meta.is_stale` 的自动 `/refresh`。后端新增 Token Usage 后台同步服务，通过 FastAPI lifespan 启停，定时发现待同步用户、获取用户级锁、调用现有 `sync_token_usage` 并失效查询缓存。`/query` 只读缓存/数据库，不执行 CLI，只把当前用户登记进待同步集合并记录耗时。

**Tech Stack:** FastAPI lifespan、asyncio 后台任务、SQLAlchemy、Redis 缓存、React 18、TypeScript、Vitest/pytest、现有 `dev-services.py` 服务脚本。

---

## File Structure

- Create: `backend/app/services/token_usage_background_sync.py`
  - 负责待同步用户集合、后台定时同步循环、用户发现、用户级锁、任务启停。
- Modify: `backend/app/config/config.py`
  - 新增后台同步配置项。
- Modify: `backend/app/main.py`
  - 删除旧的 `_delayed_token_usage_cache_refresh` 启动路径，改为 lifespan 中启动/停止新后台同步服务。
- Modify: `backend/app/routes/token_usage.py`
  - `/query` 登记当前用户到待同步集合，记录 request_id 和耗时 warning，保证不触发 CLI。
  - 缓存命中和空数据响应继续返回完整结构。
- Create: `backend/tests/test_token_usage_background_sync.py`
  - 覆盖待同步用户、锁、同步失败不退出、无历史用户首次访问后可进入同步集合。
- Modify: `backend/tests/test_token_usage_freshness.py`
  - 补充缓存旧 payload、空数据、无同步日志的结构完整性测试。
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`
  - 删除首屏自动 `/refresh` effect。
  - 增加低频 `/query` 轮询。
  - 拆分主查询错误、设备错误、健康检查错误、后台状态和手动刷新错误。
- Modify: `frontend/src/api/tokenUsageApi.ts`
  - 如需，增强错误解析，确保错误信息可读且不吞掉后端 `detail`。

---

### Task 1: 后端后台同步服务测试

**Files:**
- Create: `backend/tests/test_token_usage_background_sync.py`
- Read: `backend/app/services/token_usage_cache.py`
- Read: `backend/app/services/token_usage_sync_service.py`

- [ ] **Step 1: 写待同步用户集合测试**

Create `backend/tests/test_token_usage_background_sync.py` with:

```python
import asyncio
from types import SimpleNamespace

import pytest

from app.services import token_usage_background_sync as bg


def test_pending_user_registry_deduplicates_user_ids():
    bg.clear_pending_sync_users()

    bg.register_pending_sync_user("user-1")
    bg.register_pending_sync_user("user-1")
    bg.register_pending_sync_user("user-2")

    assert bg.get_pending_sync_users() == {"user-1", "user-2"}


def test_register_pending_sync_user_ignores_empty_and_system_users():
    bg.clear_pending_sync_users()

    bg.register_pending_sync_user("")
    bg.register_pending_sync_user(None)
    bg.register_pending_sync_user("system")
    bg.register_pending_sync_user("user-3")

    assert bg.get_pending_sync_users() == {"user-3"}
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd backend
pytest tests/test_token_usage_background_sync.py::test_pending_user_registry_deduplicates_user_ids -v
```

Expected: FAIL with import error or missing `token_usage_background_sync`.

- [ ] **Step 3: 写同步循环单轮测试**

Append to `backend/tests/test_token_usage_background_sync.py`:

```python
def test_run_background_sync_once_syncs_pending_user(monkeypatch):
    bg.clear_pending_sync_users()
    bg.register_pending_sync_user("user-1")

    events = []

    monkeypatch.setattr(bg, "_discover_token_usage_user_ids", lambda max_users: ["user-1"])
    monkeypatch.setattr(
        bg,
        "acquire_refresh_lock",
        lambda user_id, owner: {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": 120},
    )
    monkeypatch.setattr(bg, "release_refresh_lock", lambda user_id, owner: events.append(("release", user_id)))
    monkeypatch.setattr(bg, "sync_token_usage", lambda user_id, days: {"total_records": 3, "errors": []})
    monkeypatch.setattr(bg, "invalidate_user_query_cache", lambda user_id: events.append(("invalidate", user_id)))

    result = bg.run_background_sync_once(days=90, max_users=50)

    assert result["synced_users"] == ["user-1"]
    assert result["failed_users"] == []
    assert ("invalidate", "user-1") in events
    assert ("release", "user-1") in events


def test_run_background_sync_once_skips_locked_user(monkeypatch):
    bg.clear_pending_sync_users()
    bg.register_pending_sync_user("user-locked")

    monkeypatch.setattr(bg, "_discover_token_usage_user_ids", lambda max_users: ["user-locked"])
    monkeypatch.setattr(
        bg,
        "acquire_refresh_lock",
        lambda user_id, owner: {"acquired": False, "locked": True, "owner": "other", "ttl_seconds": 60},
    )

    result = bg.run_background_sync_once(days=90, max_users=50)

    assert result["synced_users"] == []
    assert result["skipped_users"] == ["user-locked"]
```

- [ ] **Step 4: 运行新增测试确认失败**

Run:

```bash
cd backend
pytest tests/test_token_usage_background_sync.py -v
```

Expected: FAIL because `run_background_sync_once` is not defined yet.

- [ ] **Step 5: Commit failing tests**

```bash
git add backend/tests/test_token_usage_background_sync.py
git commit -m "test: 覆盖 Token Usage 后台同步服务"
```

---

### Task 2: 实现后台同步服务

**Files:**
- Create: `backend/app/services/token_usage_background_sync.py`
- Modify: `backend/app/config/config.py`
- Test: `backend/tests/test_token_usage_background_sync.py`

- [ ] **Step 1: 新增配置项**

Modify `backend/app/config/config.py` inside `class Settings` after `CACHE_REDIS_TOKEN_USAGE_TTL`:

```python
    # Token Usage 后台定时同步
    TOKEN_USAGE_BACKGROUND_SYNC_ENABLED: bool = True
    TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS: int = 1800
    TOKEN_USAGE_BACKGROUND_SYNC_DAYS: int = 90
    TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS: int = 30
    TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN: int = 50
```

- [ ] **Step 2: 创建后台同步服务**

Create `backend/app/services/token_usage_background_sync.py`:

```python
"""Token Usage 后台定时同步服务。"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import suppress
from typing import Optional

from app.config.config import settings
from app.models.base import SessionLocal
from app.models.token_usage_models import DeviceRegistry, TokenUsageRecord, TokenUsageSyncLog
from app.services.token_usage_cache import (
    acquire_refresh_lock,
    invalidate_user_query_cache,
    release_refresh_lock,
)
from app.services.token_usage_sync_service import sync_token_usage
from app.utils.device_id import get_device_id

logger = logging.getLogger(__name__)

_pending_sync_users: set[str] = set()
_pending_lock = asyncio.Lock()
_background_task: Optional[asyncio.Task] = None


def register_pending_sync_user(user_id: Optional[str]) -> None:
    """登记需要后台同步的用户，不执行 CLI，不阻塞首屏查询。"""
    if not user_id or user_id == "system":
        return
    _pending_sync_users.add(user_id)


def get_pending_sync_users() -> set[str]:
    """返回待同步用户集合副本，供测试和日志使用。"""
    return set(_pending_sync_users)


def clear_pending_sync_users() -> None:
    """清空待同步用户集合，供测试使用。"""
    _pending_sync_users.clear()


def _discover_token_usage_user_ids(max_users: int) -> list[str]:
    """发现本轮需要同步的用户。"""
    current_device_id = get_device_id()
    db = SessionLocal()
    try:
        user_ids = set(_pending_sync_users)

        device_rows = (
            db.query(DeviceRegistry.user_id)
            .filter(DeviceRegistry.device_id == current_device_id)
            .distinct()
            .all()
        )
        user_ids.update(row[0] for row in device_rows if row[0] and row[0] != "system")

        record_rows = (
            db.query(TokenUsageRecord.user_id)
            .filter(TokenUsageRecord.user_id.isnot(None))
            .distinct()
            .all()
        )
        user_ids.update(row[0] for row in record_rows if row[0] and row[0] != "system")

        log_rows = (
            db.query(TokenUsageSyncLog.user_id)
            .filter(TokenUsageSyncLog.user_id.isnot(None))
            .distinct()
            .all()
        )
        user_ids.update(row[0] for row in log_rows if row[0] and row[0] != "system")

        return sorted(user_ids)[:max_users]
    except Exception as exc:
        logger.warning("获取 Token Usage 后台同步用户失败: %s", exc, exc_info=True)
        return sorted(_pending_sync_users)[:max_users]
    finally:
        db.close()


def run_background_sync_once(days: int, max_users: int) -> dict[str, list[str]]:
    """执行一轮后台同步，单元测试可直接调用。"""
    started_at = time.perf_counter()
    user_ids = _discover_token_usage_user_ids(max_users=max_users)
    result = {"synced_users": [], "skipped_users": [], "failed_users": []}

    if not user_ids:
        logger.info("Token Usage 后台同步跳过: 没有待同步用户")
        return result

    logger.info("Token Usage 后台同步开始: users=%s, days=%s", len(user_ids), days)

    for user_id in user_ids:
        owner = str(uuid.uuid4())
        lock = acquire_refresh_lock(user_id, owner)
        if not lock.get("acquired"):
            logger.info(
                "Token Usage 后台同步跳过用户 %s: 已有刷新任务, ttl=%s",
                user_id,
                lock.get("ttl_seconds"),
            )
            result["skipped_users"].append(user_id)
            continue

        try:
            sync_result = sync_token_usage(user_id=user_id, days=days)
            invalidate_user_query_cache(user_id)
            result["synced_users"].append(user_id)
            logger.info(
                "Token Usage 后台同步完成: user=%s, records=%s, errors=%s",
                user_id,
                sync_result.get("total_records"),
                len(sync_result.get("errors") or []),
            )
        except Exception as exc:
            result["failed_users"].append(user_id)
            logger.warning("Token Usage 后台同步失败: user=%s, error=%s", user_id, exc, exc_info=True)
        finally:
            release_refresh_lock(user_id, owner)

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Token Usage 后台同步本轮结束: synced=%s, skipped=%s, failed=%s, elapsed_ms=%s",
        len(result["synced_users"]),
        len(result["skipped_users"]),
        len(result["failed_users"]),
        elapsed_ms,
    )
    return result


async def _background_sync_loop() -> None:
    """后台定时同步循环。"""
    logger.info(
        "Token Usage 后台同步任务启动: enabled=%s, interval=%s, days=%s, initial_delay=%s, max_users=%s",
        settings.TOKEN_USAGE_BACKGROUND_SYNC_ENABLED,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_DAYS,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS,
        settings.TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN,
    )

    await asyncio.sleep(settings.TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS)

    while True:
        try:
            await asyncio.to_thread(
                run_background_sync_once,
                settings.TOKEN_USAGE_BACKGROUND_SYNC_DAYS,
                settings.TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Token Usage 后台同步循环异常: %s", exc, exc_info=True)

        await asyncio.sleep(settings.TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS)


def start_background_sync_task() -> Optional[asyncio.Task]:
    """启动后台同步任务。"""
    global _background_task
    if not settings.TOKEN_USAGE_BACKGROUND_SYNC_ENABLED:
        logger.info("Token Usage 后台同步任务已禁用")
        return None
    if _background_task and not _background_task.done():
        logger.info("Token Usage 后台同步任务已存在，跳过重复启动")
        return _background_task
    _background_task = asyncio.create_task(_background_sync_loop())
    return _background_task


async def stop_background_sync_task() -> None:
    """停止后台同步任务。"""
    global _background_task
    task = _background_task
    if not task:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    logger.info("Token Usage 后台同步任务已停止")
    _background_task = None
```

- [ ] **Step 3: 运行后台同步测试**

Run:

```bash
cd backend
pytest tests/test_token_usage_background_sync.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit service implementation**

```bash
git add backend/app/config/config.py backend/app/services/token_usage_background_sync.py backend/tests/test_token_usage_background_sync.py
git commit -m "feat: 添加 Token Usage 后台同步服务"
```

---

### Task 3: 接入 FastAPI lifespan 并移除旧首启刷新任务

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_token_usage_background_sync.py`

- [ ] **Step 1: 修改导入**

Modify `backend/app/main.py`: remove these imports if they become unused:

```python
from datetime import datetime, timedelta
from app.utils.usage_fetcher import UsageFetcher
from app.routes.token_usage import normalize_entries, apply_aggregation, compute_summary, merge_items
from app.services.token_usage_cache import set_cached_data, invalidate_user_query_cache
from app.services.token_usage_sync_service import sync_token_usage
```

Add:

```python
from app.services.token_usage_background_sync import (
    start_background_sync_task,
    stop_background_sync_task,
)
```

- [ ] **Step 2: 替换启动逻辑**

In `lifespan`, replace:

```python
    # 启动 Token Usage 缓存刷新任务...
    cache_refresh_task = asyncio.create_task(
        _delayed_token_usage_cache_refresh()
    )
```

with:

```python
    # 启动 Token Usage 后台定时同步任务，不阻塞首屏查询
    cache_refresh_task = start_background_sync_task()
```

- [ ] **Step 3: 替换关闭逻辑**

In shutdown section, replace:

```python
    cache_refresh_task.cancel()
    try:
        await cache_refresh_task
    except asyncio.CancelledError:
        pass
```

with:

```python
    await stop_background_sync_task()
```

Keep `cleanup_task.cancel()` and `db_pool_cleanup_task` shutdown unchanged.

- [ ] **Step 4: 删除旧缓存刷新函数**

Delete these old functions from `backend/app/main.py`:

```python
_get_token_usage_sync_user_ids
_delayed_token_usage_cache_refresh
refresh_token_usage_cache_periodically
_refresh_single_cache
_fetch_raw_data
_refresh_aggregate_cache
```

The new background sync service handles DB sync and query cache invalidation. It does not precompute old global CLI cache entries.

- [ ] **Step 5: 语法检查**

Run:

```bash
cd backend
python -m py_compile app/main.py app/services/token_usage_background_sync.py
```

Expected: command exits 0.

- [ ] **Step 6: Run tests**

Run:

```bash
cd backend
pytest tests/test_token_usage_background_sync.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit lifespan integration**

```bash
git add backend/app/main.py backend/app/services/token_usage_background_sync.py
git commit -m "feat: 接入 Token Usage 后台同步生命周期"
```

---

### Task 4: 保证 `/query` 快读、登记待同步用户并增强接口稳健性

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `backend/tests/test_token_usage_freshness.py`
- Test: `backend/tests/test_token_usage_freshness.py`

- [ ] **Step 1: 写空结构和缓存结构测试**

Append to `backend/tests/test_token_usage_freshness.py`:

```python
from app.routes.token_usage import (
    DimensionSummaries,
    FilterOptions,
    SyncMeta,
    _empty_dimension_rows,
    _empty_filter_options,
    _empty_sync_meta,
)


def test_empty_dimension_rows_match_response_model():
    rows = _empty_dimension_rows()

    parsed = DimensionSummaries(**rows)

    assert parsed.devices == []
    assert parsed.tools == []
    assert parsed.models == []


def test_empty_filter_options_match_response_model():
    options = _empty_filter_options()

    parsed = FilterOptions(**options)

    assert parsed.devices == []
    assert parsed.tools == []
    assert parsed.models == []


def test_empty_sync_meta_matches_response_model():
    meta = _empty_sync_meta()

    parsed = SyncMeta(**meta)

    assert parsed.is_stale is True
    assert parsed.refresh_lock.locked is False
    assert parsed.sources_status == []
```

- [ ] **Step 2: Run tests**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py -v
```

Expected: PASS if structures already match; FAIL if response models reject empty defaults.

- [ ] **Step 3: 修改 `/query` 登记待同步用户和耗时日志**

Modify imports in `backend/app/routes/token_usage.py`:

```python
import time
```

Add:

```python
from app.services.token_usage_background_sync import register_pending_sync_user
```

Inside `query_token_usage`, after `user_id = get_current_user_id(...)`, add:

```python
    request_id = str(uuid.uuid4())
    started_at = time.perf_counter()
    register_pending_sync_user(user_id)
    logger.info(
        "[%s] Token Usage 查询开始: user=%s, source=%s, type=%s, days=%s, group_by=%s, device=%s, tool=%s, model=%s",
        request_id,
        user_id,
        req.source,
        req.type,
        req.days,
        req.group_by,
        req.device_id or "",
        req.tool_id or "",
        req.model or "",
    )
```

Before every `return DbUsageResponse(...)` in `query_token_usage`, route through a helper:

```python
        return _finish_query_response(request_id, started_at, response)
```

Add helper above `query_token_usage`:

```python
def _finish_query_response(request_id: str, started_at: float, response: DbUsageResponse) -> DbUsageResponse:
    """记录 Token Usage 查询耗时并返回响应。"""
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    if elapsed_ms > 1000:
        logger.warning("[%s] Token Usage 查询耗时较长: %sms", request_id, elapsed_ms)
    else:
        logger.info("[%s] Token Usage 查询完成: %sms", request_id, elapsed_ms)
    return response
```

For the cached branch, build `response` first:

```python
        response = DbUsageResponse(
            items=cached_items,
            summary=UsageSummary(**cached["summary"]),
            devices=cached.get("devices", []),
            cached=True,
            model_summary=[
                ModelSummaryItem(**item)
                for item in cached.get("model_summary", [])
            ],
            dimension_summaries=DimensionSummaries(
                **cached.get("dimension_summaries", _empty_dimension_rows())
            ),
            filter_options=FilterOptions(
                **cached.get("filter_options", _empty_filter_options())
            ),
            sync_meta=SyncMeta(**cached.get("sync_meta", _empty_sync_meta())),
        )
        return _finish_query_response(request_id, started_at, response)
```

Apply the same pattern to empty and non-empty DB responses.

- [ ] **Step 4: 确认 `/query` 不调用 CLI**

Search:

```bash
cd ..
rg "_fallback_to_cli_for_query|UsageFetcher|sync_token_usage" backend/app/routes/token_usage.py
```

Expected:

- `_fallback_to_cli_for_query` may still exist only if unused.
- `query_token_usage` must not call `_fallback_to_cli_for_query`, `UsageFetcher`, or `sync_token_usage`.

If `_fallback_to_cli_for_query` is unused, delete it to remove ambiguity.

- [ ] **Step 5: 运行 Token Usage 相关后端测试**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py tests/test_token_usage_dimensions.py tests/test_token_usage_background_sync.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit query hardening**

```bash
git add backend/app/routes/token_usage.py backend/tests/test_token_usage_freshness.py
git commit -m "fix: 解耦 Token Usage 查询与后台同步"
```

---

### Task 5: 前端删除首屏自动刷新并增加低频查询轮询

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`
- Optional Modify: `frontend/src/api/tokenUsageApi.ts`

- [ ] **Step 1: 拆分非关键接口错误状态**

In `TokenUsage.tsx`, add state near existing `error`:

```typescript
  const [deviceLoadError, setDeviceLoadError] = useState<string | null>(null);
  const [healthLoadError, setHealthLoadError] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
```

Update `loadDevices`:

```typescript
  const loadDevices = useCallback(async () => {
    try {
      const result = await getUserDevices();
      setDevices(result.devices);
      setDeviceLoadError(null);
    } catch (err: any) {
      setDeviceLoadError(err.message || '设备列表加载失败');
    }
  }, []);
```

Update the initial health effect:

```typescript
  useEffect(() => {
    checkTokenUsageHealth()
      .then(result => {
        setHealth(result);
        setHealthLoadError(null);
      })
      .catch((err: any) => {
        setHealth(null);
        setHealthLoadError(err.message || '能力状态加载失败');
      });
    loadDevices();
  }, [loadDevices]);
```

- [ ] **Step 2: 删除首屏自动 `/refresh` effect**

Delete the entire effect currently starting with:

```typescript
  useEffect(() => {
    if (!syncMeta?.is_stale || backgroundRefreshing || refreshing) return;
```

Also remove `lastAutoRefreshRef` and `backgroundRefreshing` if no longer used.

Keep manual `handleRefresh` unchanged except it should set `refreshError` only for manual refresh failures.

- [ ] **Step 3: 增加低频 `/query` 轮询**

Add refs:

```typescript
  const pollFailureCountRef = useRef(0);
```

Add polling effect after the normal `fetchData` effect:

```typescript
  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const schedule = () => {
      const delay = pollFailureCountRef.current > 0 ? 120_000 : 60_000;
      timer = window.setTimeout(run, delay);
    };

    const run = async () => {
      if (cancelled) return;
      if (document.hidden || refreshing || loading) {
        schedule();
        return;
      }

      try {
        const result = await getDbTokenUsage({
          source,
          type: reportType,
          days,
          group_by: groupBy,
          device_id: selectedDevice || undefined,
          tool_id: selectedTool || undefined,
          model: selectedModel || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
        });
        if (cancelled) return;
        pollFailureCountRef.current = 0;
        setPollError(null);
        setItems(result.items || []);
        setSummary(result.summary || emptySummary);
        setCached(Boolean(result.cached));
        setAutoExpanded(Boolean(result.auto_expanded));
        setActualDays(result.actual_days || null);
        setModelSummary(result.model_summary || []);
        setDimensionSummaries(result.dimension_summaries || emptyDimensionSummaries);
        setFilterOptions(result.filter_options || emptyFilterOptions);
        setSyncMeta(result.sync_meta || null);
        if (result.devices?.length) setDevices(result.devices);
      } catch (err: any) {
        if (!cancelled) {
          pollFailureCountRef.current += 1;
          setPollError(err.message || '后台状态刷新失败');
        }
      } finally {
        if (!cancelled) schedule();
      }
    };

    schedule();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [days, groupBy, loading, refreshing, reportType, selectedDevice, selectedModel, selectedTool, sortBy, sortOrder, source]);
```

- [ ] **Step 4: 更新状态提示区域**

In the block that renders `(error || lastSyncMessage || autoExpanded)`, include non-blocking messages:

```typescript
      {(error || lastSyncMessage || autoExpanded || deviceLoadError || healthLoadError || pollError || syncMeta?.is_stale) && (
        <div className="mb-5 space-y-2">
          {error && <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
          {!error && syncMeta?.is_stale && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              数据可能滞后，后台同步会自动更新；页面会低频刷新已有统计。
            </div>
          )}
          {deviceLoadError && <div className="rounded-md border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-300">{deviceLoadError}</div>}
          {healthLoadError && <div className="rounded-md border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-300">{healthLoadError}</div>}
          {pollError && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">{pollError}</div>}
          {lastSyncMessage && <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{lastSyncMessage}</div>}
          {autoExpanded && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">当前范围无数据，已自动扩大到最近 {actualDays} 天。</div>}
        </div>
      )}
```

The existing file has mojibake text. Use the same surrounding style, but new user-facing text should be readable Chinese.

- [ ] **Step 5: Remove unused imports and state**

Run:

```bash
cd frontend
npm run build
```

Expected: if TypeScript reports unused `backgroundRefreshing`, `lastAutoRefreshRef`, or imports, remove them and rerun.

- [ ] **Step 6: Commit frontend changes**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx frontend/src/api/tokenUsageApi.ts
git commit -m "fix: Token Usage 首屏不再自动刷新"
```

---

### Task 6: 集成验证与服务验证

**Files:**
- Verify: `backend/app/main.py`
- Verify: `backend/app/routes/token_usage.py`
- Verify: `backend/app/services/token_usage_background_sync.py`
- Verify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: 后端测试**

Run:

```bash
cd backend
pytest tests/test_token_usage_freshness.py tests/test_token_usage_dimensions.py tests/test_token_usage_background_sync.py -v
```

Expected: PASS.

- [ ] **Step 2: 后端语法和规范**

Run:

```bash
cd backend
python -m py_compile app/main.py app/routes/token_usage.py app/services/token_usage_background_sync.py
ruff check app/main.py app/routes/token_usage.py app/services/token_usage_background_sync.py tests/test_token_usage_freshness.py tests/test_token_usage_background_sync.py
```

Expected: both commands exit 0.

- [ ] **Step 3: 前端构建**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: 重启后端验证后台任务**

Because background task configuration changes require backend restart, run:

```bash
python dev-services.py restart
python dev-services.py status
```

Expected:

- Backend 状态为运行中。
- `logs/backend.log` or `backend/logs/app.log` contains `Token Usage 后台同步任务启动`.

- [ ] **Step 5: 浏览器 Network 验证**

Open:

```text
http://localhost:5178/tools/token-usage
```

Expected:

- First load requests include `/api/token-usage/health`, `/api/token-usage/devices`, `/api/token-usage/query`.
- First load requests do not include `/api/token-usage/refresh`.
- Existing chart/table data renders after `/query`.
- If stale, page shows stale notice instead of auto-refreshing.

- [ ] **Step 6: 手动刷新验证**

Click the refresh button on the Token Usage page.

Expected:

- `/api/token-usage/refresh` appears only after click.
- If backend returns `locked=true`, page shows a lightweight message and keeps old data.
- If refresh fails, old chart/table stays visible.

- [ ] **Step 7: Commit verification fixes**

If verification required small fixes:

```bash
git add backend/app/main.py backend/app/routes/token_usage.py backend/app/services/token_usage_background_sync.py backend/tests/test_token_usage_background_sync.py backend/tests/test_token_usage_freshness.py frontend/src/components/Tools/TokenUsage.tsx frontend/src/api/tokenUsageApi.ts
git commit -m "fix: 完成 Token Usage 快速加载后台同步验证"
```

If no fixes were needed, skip this commit.

---

## Self-Review

- Spec coverage:
  - 首屏只读 Redis/DB：Task 4 and Task 5.
  - 后台定时同步：Task 2 and Task 3.
  - 首次访问用户进入待同步集合：Task 2 and Task 4.
  - 前端低频 `/query` 轮询看到后台更新：Task 5.
  - 接口错误分层：Task 5.
  - 后台任务生命周期：Task 3.
  - 验证首屏无 `/refresh`：Task 6.
- Placeholder scan:
  - No placeholder wording or vague implementation instructions remain.
- Type consistency:
  - `register_pending_sync_user`, `run_background_sync_once`, `start_background_sync_task`, and `stop_background_sync_task` are introduced before use.
  - Config names match the design spec and planned service code.
  - Frontend polling uses existing `getDbTokenUsage` and existing state setters.
