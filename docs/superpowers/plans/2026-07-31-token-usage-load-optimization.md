---
author: Peanut
created_at: 2026-07-31
purpose: Token Usage 页面加载性能优化实施计划 -- 数据库直读 + Redis 缓存预热 + 异步同步
---

# Token Usage 页面加载性能优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 token-usage 页面首屏只读 Redis/DB（ms 级），同步走后台异步任务，5 分钟定时刷新并预热缓存。

**Architecture:** 读路径 summary/details 优先 Redis，未命中走 DB GROUP BY 聚合并回写；写路径（手动 /sync + 后台 5 分钟循环）跑 CLI 子进程抓取并 upsert DB，完成后 invalidate + warm Redis。CLI 抓取不持有 DB 连接，与读路径彻底解耦。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / Redis (oss2 不涉及) / React 18 + TypeScript + Vite / pytest

## Global Constraints

- **禁止 mock 业务代码**：业务路径不得有 mock/兜底默认值；仅单元测试目录内允许 mock（CLAUDE.md 最高优先级规则）。
- **后端改完必须本地编译验证**：`python -m py_compile app/routes/token_usage.py`（在 `backend/` 目录下），通过后用 `python dev_services.py restart backend` 重启，禁止本地裸跑 uvicorn。
- **前端改完优先热加载**：修改 `.tsx` 走 Vite HMR；只有改 `vite.config.ts`/`.env`/`package.json` 才用 `python dev_services.py restart frontend`。
- **浏览器强制验证**：所有改动完成后必须用浏览器打开 `http://localhost:5178/tools/token-usage`，确认 Console 无报错、首屏 < 1s。
- **中文输出**：所有自然语言、代码注释、commit message 用中文；变量名/函数名用英文。
- **配置项精确值**：`CACHE_REDIS_TOKEN_USAGE_TTL = 300`、`TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS = 300`（其余 `TOKEN_USAGE_BACKGROUND_SYNC_*` 不动）。
- **Git 提交规范**：`类型：描述`，类型含 feat/fix/refactor/docs/test/chore；末尾附 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

## File Structure

| 文件 | 职责 | 改动类型 |
|------|------|---------|
| `backend/app/config/config.py` | 全局配置 | 修改 2 个默认值 |
| `backend/app/routes/token_usage.py` | 路由层：提取 `_build_summary_payload`、新增 `warm_query_cache`、改 `/sync` | 修改 |
| `backend/app/services/token_usage_background_sync.py` | 后台同步循环：完成后调 warm | 修改 |
| `backend/frontend` 不涉及 | - | - |
| `frontend/src/components/Tools/TokenUsage.tsx` | `handleSync` 改调 `/sync` + 不阻塞 | 修改 |
| `frontend/src/api/tokenUsageApi.ts` | 复用已有 `syncTokenUsage()`（已指向 `/sync`） | 不改 |
| `backend/tests/test_token_usage_warm_cache.py` | warm_query_cache 单元测试 | 新建 |
| `backend/tests/test_token_usage_sync_async.py` | /sync 异步返回测试 | 新建 |
| `backend/tests/test_token_usage_background_sync.py` | 扩展：验证 warm 被调用 | 修改 |

**模块依赖说明（避免循环导入）**：
- `token_usage.py`（路由）已导入 `token_usage_background_sync.register_pending_sync_user`。
- 因此 `warm_query_cache` 定义在路由层 `token_usage.py`；`background_sync.py` 通过**函数内延迟导入**调用它，避免循环依赖。

---

### Task 1: 提取 `_build_summary_payload` 公共函数 + 调整配置项

**Files:**
- Modify: `backend/app/routes/token_usage.py:734-902`（`/summary` 路由）
- Modify: `backend/app/config/config.py:112,116`
- Test: `backend/tests/test_token_usage_split_integration.py`（现有，回归用）

**Interfaces:**
- Produces: `_build_summary_payload(db, user_id: str, req: SimpleNamespace) -> Optional[dict]` —— 返回可直接 `SummaryResponse(**payload)` 的 dict，或 `None`（用户无数据时）。后续 Task 2 的 `warm_query_cache` 依赖此函数。

- [ ] **Step 1: 调整配置项默认值**

打开 `backend/app/config/config.py`，定位第 112 行和第 116 行：

```python
    CACHE_REDIS_TOKEN_USAGE_TTL: int = 3600  # 1 小时
```
改为：
```python
    CACHE_REDIS_TOKEN_USAGE_TTL: int = 300  # 5 分钟，与后台同步间隔一致
```

```python
    TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS: int = 1800
```
改为：
```python
    TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS: int = 300  # 5 分钟一轮
```

- [ ] **Step 2: 提取 `_build_summary_payload` 函数**

在 `backend/app/routes/token_usage.py` 的 `/summary` 路由**之前**（约第 730 行，`SummaryResponse` 类定义之后），新增函数：

```python
def _build_summary_payload(db, user_id: str, req) -> Optional[dict]:
    """构建 /summary 的完整 payload（DB 聚合 + 维度 + 图表 + meta）。

    供 /summary 路由和 warm_query_cache 共用，保证口径一致。
    用户无数据时返回 None，由调用方决定返回空响应或跳过预热。
    """
    from app.utils.device_name_resolver import load_alias_map

    alias_map = load_alias_map(db, user_id)

    has_data = (
        db.query(TokenUsageRecord)
        .filter(TokenUsageRecord.user_id == user_id)
        .first()
        is not None
    )
    if not has_data:
        return None

    since_date = datetime.now() - timedelta(days=req.days)

    agg_result = (
        db.query(
            func.sum(TokenUsageRecord.input_tokens).label("total_input"),
            func.sum(TokenUsageRecord.output_tokens).label("total_output"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("total_cc"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("total_cr"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
            func.count(func.distinct(TokenUsageRecord.record_date)).label("days_count"),
        )
        .filter(*_build_record_filters(user_id, req, since_date, alias_map, db=db))
        .first()
    )

    total_input = int(agg_result.total_input or 0)
    total_output = int(agg_result.total_output or 0)
    total_cc = int(agg_result.total_cc or 0)
    total_cr = int(agg_result.total_cr or 0)
    total_tokens = total_input + total_output + total_cc + total_cr
    total_cost = float(agg_result.total_cost or 0)
    days_count = int(agg_result.days_count or 0)

    summary = SummaryUsageSummary(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_cache_creation_tokens=total_cc,
        total_cache_read_tokens=total_cr,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        days_count=days_count,
        avg_daily_cost=round(total_cost / max(days_count, 1), 4),
    )

    dimension_rows, filter_options = _query_dimension_data(
        db, user_id, req, since_date, alias_map
    )
    model_rows = _execute_model_summary_query(db, user_id, req, since_date, alias_map)
    model_summary = _rows_to_model_summary(model_rows)
    device_names = _load_device_names(db, user_id)
    devices = [{"id": did, "name": name} for did, name in device_names.items()]

    chart_records = (
        db.query(
            TokenUsageRecord.record_date,
            TokenUsageRecord.input_tokens,
            TokenUsageRecord.output_tokens,
            TokenUsageRecord.cache_creation_tokens,
            TokenUsageRecord.cache_read_tokens,
            TokenUsageRecord.total_tokens,
            TokenUsageRecord.total_cost,
        )
        .filter(*_build_record_filters(user_id, req, since_date, alias_map, db=db))
        .all()
    )
    chart_series = build_chart_series(chart_records, req.group_by)

    sync_meta = _get_sync_meta(db, user_id, req, None)

    return SummaryResponse(
        summary=summary,
        dimension_summaries=_to_dimension_summaries(dimension_rows),
        model_summary=model_summary,
        filter_options=_to_filter_options(filter_options),
        sync_meta=_to_sync_meta(sync_meta),
        chart_series=[ChartSeriesItem(**s) for s in chart_series],
        devices=devices,
    ).model_dump(exclude={"cached"})
```

- [ ] **Step 3: 改造 `/summary` 路由调用公共函数**

将 `backend/app/routes/token_usage.py` 中 `/summary` 路由（约 774-902 行）的 DB 聚合部分替换为调用 `_build_summary_payload`。改造后路由体应为：

```python
@router.get("/summary", response_model=SummaryResponse)
async def get_token_usage_summary(
    source: str = "all",
    type: str = "daily",
    days: int = 30,
    group_by: str = "none",
    device_id: Optional[str] = None,
    tool_id: Optional[str] = None,
    model: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    from app.services.token_usage_cache import get_query_cached_payload, set_query_cached_data

    cache_payload = get_query_cached_payload(
        source=source,
        report_type=type,
        days=days,
        group_by=group_by,
        user_id=user_id,
        device_id=device_id or "",
        tool_id=tool_id or "",
        model=model or "",
        sort_by="date",
        sort_order="desc",
    )

    if cache_payload:
        logger.info(f"summary 缓存命中: user={user_id}, source={source}, days={days}")
        cached_response = dict(cache_payload)
        cached_response.pop("_cache_ttl_seconds", None)
        return SummaryResponse(**cached_response, cached=True)

    db = SessionLocal()
    try:
        req = SimpleNamespace(
            source=source,
            type=type,
            days=days,
            group_by=group_by,
            device_id=device_id,
            tool_id=tool_id,
            model=model,
            sort_by="date",
            sort_order="desc",
        )

        payload = _build_summary_payload(db, user_id, req)
        if payload is None:
            return SummaryResponse(
                summary=SummaryUsageSummary(
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_cache_creation_tokens=0,
                    total_cache_read_tokens=0,
                    total_tokens=0,
                    total_cost=0.0,
                    days_count=0,
                    avg_daily_cost=0.0,
                )
            )

        set_query_cached_data(
            source=source,
            report_type=type,
            days=days,
            group_by=group_by,
            user_id=user_id,
            device_id=device_id or "",
            tool_id=tool_id or "",
            model=model or "",
            sort_by="date",
            sort_order="desc",
            data=payload,
        )

        return SummaryResponse(**payload, cached=False)
    finally:
        db.close()
```

- [ ] **Step 4: 本地编译验证**

Run（在 `backend/` 目录下）:
```bash
python -m py_compile app/routes/token_usage.py app/config/config.py
```
Expected: 无输出（编译通过）

- [ ] **Step 5: 运行现有集成测试做回归**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_split_integration.py tests/test_token_usage_split_cache.py -v
```
Expected: 全部 PASS（确认重构未破坏现有行为）

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/config/config.py
git commit -m "refactor: 提取 _build_summary_payload 公共函数并调整缓存 TTL 与同步间隔

- CACHE_REDIS_TOKEN_USAGE_TTL 3600 -> 300（与同步间隔一致）
- TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS 1800 -> 300
- /summary 路由复用 _build_summary_payload，为后续缓存预热复用

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 新增 `warm_query_cache` 函数 + 单元测试

**Files:**
- Modify: `backend/app/routes/token_usage.py`（新增 `warm_query_cache`，紧跟 `_build_summary_payload` 之后）
- Test: `backend/tests/test_token_usage_warm_cache.py`（新建）

**Interfaces:**
- Consumes: Task 1 的 `_build_summary_payload`、`token_usage_cache.set_query_cached_data`
- Produces: `warm_query_cache(user_id: str) -> bool` —— 预热 daily/30天/all/无筛选 的 summary 缓存；用户无数据返回 False，预热成功返回 True，Redis 不可用静默返回 False。Task 3、Task 4 依赖此函数。

- [ ] **Step 1: 编写失败测试**

新建 `backend/tests/test_token_usage_warm_cache.py`：

```python
"""warm_query_cache 单元测试：同步完成后预热常用 summary 缓存。"""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.routes import token_usage


def test_warm_returns_false_when_user_has_no_data():
    """用户无数据时不预热，返回 False。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None

    with patch("app.routes.token_usage.SessionLocal", return_value=fake_db):
        with patch("app.routes.token_usage.set_query_cached_data") as mock_set:
            result = token_usage.warm_query_cache("user-empty")

    assert result is False
    mock_set.assert_not_called()


def test_warm_writes_cache_when_user_has_data():
    """用户有数据时调用 set_query_cached_data 写入预热缓存。"""
    fake_db = MagicMock()
    # has_data 检查：first() 返回非 None
    fake_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    fake_payload = {"summary": {"total_tokens": 100}, "devices": []}

    with patch("app.routes.token_usage.SessionLocal", return_value=fake_db):
        with patch(
            "app.routes.token_usage._build_summary_payload",
            return_value=fake_payload,
        ) as mock_build:
            with patch("app.routes.token_usage.set_query_cached_data") as mock_set:
                result = token_usage.warm_query_cache("user-1")

    assert result is True
    mock_build.assert_called_once()
    # 验证预热的是 daily/30天/all/none 这个常用组合
    mock_set.assert_called_once()
    call_kwargs = mock_set.call_args.kwargs
    assert call_kwargs["report_type"] == "daily"
    assert call_kwargs["days"] == 30
    assert call_kwargs["source"] == "all"
    assert call_kwargs["group_by"] == "none"
    assert call_kwargs["user_id"] == "user-1"
    assert call_kwargs["data"] == fake_payload


def test_warm_returns_false_when_redis_unavailable():
    """Redis 不可用时 set_query_cached_data 返回 False，warm 整体返回 False 但不抛异常。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    with patch("app.routes.token_usage.SessionLocal", return_value=fake_db):
        with patch(
            "app.routes.token_usage._build_summary_payload",
            return_value={"summary": {}},
        ):
            with patch(
                "app.routes.token_usage.set_query_cached_data",
                return_value=False,
            ):
                result = token_usage.warm_query_cache("user-1")

    assert result is False


def test_warm_returns_false_when_build_payload_returns_none():
    """_build_summary_payload 返回 None（has_data 但聚合为空）时不写缓存。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    with patch("app.routes.token_usage.SessionLocal", return_value=fake_db):
        with patch(
            "app.routes.token_usage._build_summary_payload",
            return_value=None,
        ):
            with patch("app.routes.token_usage.set_query_cached_data") as mock_set:
                result = token_usage.warm_query_cache("user-1")

    assert result is False
    mock_set.assert_not_called()
```

- [ ] **Step 2: 运行测试确认失败**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_warm_cache.py -v
```
Expected: FAIL，`AttributeError: module 'app.routes.token_usage' has no attribute 'warm_query_cache'`

- [ ] **Step 3: 实现 `warm_query_cache`**

在 `backend/app/routes/token_usage.py` 中，紧跟 `_build_summary_payload` 函数之后新增：

```python
def warm_query_cache(user_id: str) -> bool:
    """同步完成后预热常用 summary 查询缓存，避免首屏冷查询。

    只预热 daily / 30 天 / source=all / 无筛选 这个最常用组合；
    其他组合仍走正常"未命中 -> DB -> 回写"路径。
    用户无数据、Redis 不可用、构建失败时静默返回 False，不影响同步主流程。
    """
    db = SessionLocal()
    try:
        # 仅当该用户有数据时才预热，避免空查询浪费
        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            logger.info(f"warm_query_cache 跳过: user={user_id} 无数据")
            return False

        req = SimpleNamespace(
            source="all",
            type="daily",
            days=30,
            group_by="none",
            device_id=None,
            tool_id=None,
            model=None,
            sort_by="date",
            sort_order="desc",
        )

        payload = _build_summary_payload(db, user_id, req)
        if payload is None:
            logger.info(f"warm_query_cache 跳过: user={user_id} payload 为空")
            return False

        written = set_query_cached_data(
            source="all",
            report_type="daily",
            days=30,
            group_by="none",
            user_id=user_id,
            device_id="",
            tool_id="",
            model="",
            sort_by="date",
            sort_order="desc",
            data=payload,
        )
        if written:
            logger.info(f"warm_query_cache 预热成功: user={user_id}")
        return bool(written)
    except Exception as e:
        # 预热失败不影响同步主流程，仅记日志
        logger.warning(f"warm_query_cache 预热失败: user={user_id}, error={e}")
        return False
    finally:
        db.close()
```

> 注意：`set_query_cached_data` 需在文件顶部 import。当前 token_usage.py 顶部是 `from app.services.token_usage_cache import (get_cached_data, set_cached_data, ...)`，需补上 `set_query_cached_data`（若 Task 1 改造 /summary 时已用函数内导入，这里改为顶部导入更一致；二选一保持一致即可）。

- [ ] **Step 4: 运行测试确认通过**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_warm_cache.py -v
```
Expected: 4 个测试全部 PASS

- [ ] **Step 5: 本地编译验证**

Run（在 `backend/` 目录下）:
```bash
python -m py_compile app/routes/token_usage.py
```
Expected: 无输出

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/token_usage.py backend/tests/test_token_usage_warm_cache.py
git commit -m "feat: 新增 warm_query_cache 同步后预热常用 summary 缓存

避免同步完成后首屏冷查询走 DB 聚合，预热 daily/30天/all 组合。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `/sync` 接口改为 async + asyncio.to_thread + 完成后 warm

**Files:**
- Modify: `backend/app/routes/token_usage.py:1297-1334`（`/sync` 路由及其内部 `_run_sync`）
- Test: `backend/tests/test_token_usage_sync_async.py`（新建）

**Interfaces:**
- Consumes: Task 2 的 `warm_query_cache`、`sync_token_usage`、`invalidate_user_query_cache`、`get_sync_lock`
- Produces: `POST /sync` 立即返回 `{"success": True, "message": "后台同步已开始", "background": True, "started": True}`，同步在 `asyncio.to_thread` 中跑，完成后调 `warm_query_cache`。

- [ ] **Step 1: 编写失败测试**

新建 `backend/tests/test_token_usage_sync_async.py`：

```python
"""/sync 接口异步返回测试：立即返回 202 风格响应，同步在后台跑。"""
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


def _make_app():
    """构造最小 FastAPI 应用，仅挂载 token_usage 路由，避免启动后台任务。"""
    from fastapi import FastAPI
    from app.routes import token_usage
    app = FastAPI()
    app.include_router(token_usage.router, prefix="/api")
    return app, token_usage


def _auth_header():
    # get_current_user_id 会解析 Bearer token；用 patch 绕过真实校验
    return {"Authorization": "Bearer fake.token"}


def test_sync_returns_immediately_and_starts_background(monkeypatch):
    app, token_usage = _make_app()
    client = TestClient(app)

    # 绕过认证
    monkeypatch.setattr(
        token_usage, "get_current_user_id", lambda authorization: "user-1"
    )
    # 锁未占用
    fake_lock = MagicMock()
    fake_lock.locked.return_value = False
    monkeypatch.setattr(token_usage, "get_sync_lock", lambda: fake_lock)

    sync_called = {"count": 0}
    warm_called = {"count": 0}

    def fake_sync(user_id, days):
        sync_called["count"] += 1
        return {"total_records": 5, "errors": []}

    def fake_warm(user_id):
        warm_called["count"] += 1
        return True

    monkeypatch.setattr(token_usage, "sync_token_usage", fake_sync)
    monkeypatch.setattr(token_usage, "invalidate_user_query_cache", lambda user_id: None)
    # warm_query_cache 在后台线程内通过模块内引用调用，patch 模块属性即可
    monkeypatch.setattr(token_usage, "warm_query_cache", fake_warm)

    with patch("app.routes.token_usage.asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        response = client.post("/api/token-usage/sync", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["background"] is True
    assert body["started"] is True
    # 同步与预热都被调用（to_thread 被 patch 成同步执行）
    assert sync_called["count"] == 1
    assert warm_called["count"] == 1


def test_sync_returns_not_started_when_lock_held(monkeypatch):
    app, token_usage = _make_app()
    client = TestClient(app)

    monkeypatch.setattr(
        token_usage, "get_current_user_id", lambda authorization: "user-1"
    )
    fake_lock = MagicMock()
    fake_lock.locked.return_value = True  # 锁已占用
    monkeypatch.setattr(token_usage, "get_sync_lock", lambda: fake_lock)

    sync_called = {"count": 0}
    monkeypatch.setattr(
        token_usage, "sync_token_usage",
        lambda user_id, days: sync_called.__setitem__("count", sync_called["count"] + 1),
    )

    response = client.post("/api/token-usage/sync", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["started"] is False
    assert sync_called["count"] == 0  # 锁占用时不执行同步
```

- [ ] **Step 2: 运行测试确认失败**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_sync_async.py -v
```
Expected: FAIL（当前 /sync 用 threading.Thread，未调 warm_query_cache，第一个测试的 warm_called 断言失败）

- [ ] **Step 3: 改造 `/sync` 路由**

将 `backend/app/routes/token_usage.py` 中 `/sync` 路由（约 1297-1334 行）整体替换为：

```python
@router.post("/sync")
async def sync_token_usage_endpoint(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """手动触发 Token Usage 同步到数据库（后台执行，立即返回，不阻塞前端）。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    lock = get_sync_lock()
    if lock.locked():
        return {
            "success": True,
            "message": "同步进行中",
            "background": True,
            "started": False,
        }

    async def _run_sync_async():
        """在后台线程中执行同步 + 缓存预热，不阻塞 HTTP 响应。"""
        try:
            invalidate_user_query_cache(user_id)
            sync_token_usage(user_id=user_id, days=90)
            invalidate_user_query_cache(user_id)
            # 同步完成后预热常用缓存，避免下次首屏冷查询
            warm_query_cache(user_id)
        except Exception as e:
            logger.error(f"后台同步失败: user={user_id}, error={e}", exc_info=True)

    # 提交到后台线程，立即返回；不 await 其完成
    asyncio.create_task(asyncio.to_thread(_run_sync_async))

    return {
        "success": True,
        "message": "后台同步已开始",
        "background": True,
        "started": True,
    }
```

> 关键点：
> 1. 路由改为 `async def`，用 `asyncio.create_task(asyncio.to_thread(...))` 提交后台执行，立即返回。
> 2. 后台流程末尾调用 `warm_query_cache(user_id)`，与设计文档一致。
> 3. `_run_sync_async` 内部异常被捕获并记日志，不影响已返回的 HTTP 响应。
> 4. 测试中 `asyncio.to_thread` 被 patch 成同步执行，所以 warm 会被调用；生产环境是真正的后台线程。

- [ ] **Step 4: 运行测试确认通过**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_sync_async.py -v
```
Expected: 2 个测试全部 PASS

- [ ] **Step 5: 本地编译验证**

Run（在 `backend/` 目录下）:
```bash
python -m py_compile app/routes/token_usage.py
```
Expected: 无输出

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/token_usage.py backend/tests/test_token_usage_sync_async.py
git commit -m "feat: /sync 接口改为 async 后台执行并预热缓存

- asyncio.create_task(to_thread(...)) 提交后台，立即返回
- 同步完成后调用 warm_query_cache 预热常用缓存
- 前端不再阻塞等待 CLI 子进程

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 后台同步循环调用 `warm_query_cache`

**Files:**
- Modify: `backend/app/services/token_usage_background_sync.py:109-145`（`run_background_sync_once` 的 per-user 同步块）
- Test: `backend/tests/test_token_usage_background_sync.py`（扩展已有测试）

**Interfaces:**
- Consumes: Task 2 的 `warm_query_cache`（通过函数内延迟导入避免循环依赖）
- Produces: 后台每轮同步完成后，对该用户调用 warm。

- [ ] **Step 1: 扩展失败测试**

打开 `backend/tests/test_token_usage_background_sync.py`，在 `test_run_background_sync_once_syncs_pending_user` 中补充对 warm 的断言。在该测试函数末尾（`assert ("release", "user-1") in events` 之后）追加：

```python
    # 新增：验证同步完成后调用了 warm_query_cache
    monkeypatch.setattr(
        bg,
        "warm_query_cache",
        lambda user_id: events.append(("warm", user_id)),
    )
```

> 注意：`warm_query_cache` 是在 `run_background_sync_once` 内部通过延迟导入调用的，不能直接 `monkeypatch.setattr(bg, ...)`。正确做法见 Step 2 实现 + Step 3 测试调整。先把上面的追加**删掉**，改用下面的独立测试。

在文件末尾新增独立测试：

```python
def test_run_background_sync_once_calls_warm_after_sync(monkeypatch):
    """后台同步完成后应调用 warm_query_cache 预热缓存。"""
    bg.clear_pending_sync_users()
    bg.register_pending_sync_user("user-1")

    events = []

    monkeypatch.setattr(bg, "_discover_token_usage_user_ids", lambda max_users: ["user-1"])
    monkeypatch.setattr(
        bg, "acquire_refresh_lock",
        lambda user_id, owner: {"acquired": True, "locked": False, "owner": owner, "ttl_seconds": 120},
    )
    monkeypatch.setattr(
        bg, "release_refresh_lock",
        lambda user_id, owner: events.append(("release", user_id)),
    )
    monkeypatch.setattr(
        bg, "sync_token_usage",
        lambda user_id, days: {"total_records": 3, "errors": []},
    )
    monkeypatch.setattr(
        bg, "invalidate_user_query_cache",
        lambda user_id: events.append(("invalidate", user_id)),
    )
    # warm_query_cache 通过延迟导入从 app.routes.token_usage 引入，
    # patch 模块级函数即可被 run_background_sync_once 内的 import 捕获
    from app.routes import token_usage as routes_tu
    monkeypatch.setattr(
        routes_tu, "warm_query_cache",
        lambda user_id: events.append(("warm", user_id)),
    )

    result = bg.run_background_sync_once(days=90, max_users=50)

    assert result["synced_users"] == ["user-1"]
    # 顺序：invalidate -> sync -> invalidate -> warm -> release
    assert ("warm", "user-1") in events
    warm_idx = events.index(("warm", "user-1"))
    release_idx = events.index(("release", "user-1"))
    assert warm_idx < release_idx  # warm 在 release 之前
```

- [ ] **Step 2: 运行测试确认失败**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_background_sync.py::test_run_background_sync_once_calls_warm_after_sync -v
```
Expected: FAIL，`AssertionError: ('warm', 'user-1') not in events`

- [ ] **Step 3: 修改 `run_background_sync_once` 调用 warm**

打开 `backend/app/services/token_usage_background_sync.py`，定位 `run_background_sync_once` 函数中 per-user 的 try 块（约 122-133 行）。在 `invalidate_user_query_cache(user_id)`（同步成功后那次）之后、`logger.info("Token Usage 后台同步完成...")` 之前，插入 warm 调用：

```python
        try:
            sync_result = sync_token_usage(user_id=user_id, days=days)
            invalidate_user_query_cache(user_id)
            # 同步完成后预热常用缓存，避免下次首屏冷查询
            # 延迟导入避免与 token_usage 路由层循环依赖
            from app.routes.token_usage import warm_query_cache
            warm_query_cache(user_id)
            result["synced_users"].append(user_id)
            user_elapsed_ms = int((time.perf_counter() - user_started) * 1000)
            logger.info(
                "Token Usage 后台同步完成: user=%s, records=%s, errors=%s, elapsed_ms=%s",
                user_id,
                sync_result.get("total_records"),
                len(sync_result.get("errors") or []),
                user_elapsed_ms,
            )
```

> 注意：warm_query_cache 内部已捕获所有异常并返回 False，不会因预热失败导致整个 per-user 同步失败。但它放在 try 块内，若 import 失败会被 except 捕获记为 failed_users。import 失败属于代码错误，应当暴露，所以这是可接受的。

- [ ] **Step 4: 运行测试确认通过**

Run（在 `backend/` 目录下）:
```bash
python -m pytest tests/test_token_usage_background_sync.py -v
```
Expected: 全部 PASS（含原有 3 个 + 新增 1 个）

- [ ] **Step 5: 本地编译验证**

Run（在 `backend/` 目录下）:
```bash
python -m py_compile app/services/token_usage_background_sync.py
```
Expected: 无输出

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/token_usage_background_sync.py backend/tests/test_token_usage_background_sync.py
git commit -m "feat: 后台同步循环完成后调用 warm_query_cache 预热缓存

延迟导入避免循环依赖，预热失败不影响同步主流程。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 前端 `handleSync` 改为调用 `/sync` + 不阻塞

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx:302-324`（`handleSync` 函数）
- 不改: `frontend/src/api/tokenUsageApi.ts`（已有 `syncTokenUsage()` 指向 `/sync`）

**Interfaces:**
- Consumes: 已有 `syncTokenUsage()` API（POST `/api/token-usage/sync`）、`useToast`
- Produces: 点击"同步数据"立即 toast"后台同步已开始"，不 await 同步完成；数据更新由 30 秒轮询自动拉取。

- [ ] **Step 1: 改造 `handleSync`**

打开 `frontend/src/components/Tools/TokenUsage.tsx`，定位 `handleSync`（约 302-324 行），整体替换为：

```typescript
  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const result = await syncTokenUsage();
      if (result.started) {
        showToast('后台同步已开始，约 1 分钟后数据自动更新', 'success', 3000);
      } else {
        showToast('同步进行中，请稍候', 'info', 3000);
      }
      // 不再 await 同步完成 + 立即 refresh，改为依赖 30 秒轮询自动拉取新数据
    } catch (e: any) {
      setSyncError(e.message || '同步启动失败');
    } finally {
      setSyncing(false);
    }
  };
```

> 关键改动：
> 1. 用 `syncTokenUsage()`（已有，调 `/sync`）替代原来直接 `fetch('/api/token-usage/refresh-ccusage')`。
> 2. 不再 `await Promise.all([summary.refresh(), details.refresh()])` + `loadDevices()`——这些会在同步完成后由 `useTokenUsagePolling` 的 30 秒定时自动触发。
> 3. 乐观提示用户"约 1 分钟后自动更新"，对齐后台同步耗时（ccusage 抓取数秒~十几秒）+ 轮询间隔 30s。

- [ ] **Step 2: 确认 import 已存在**

检查 `TokenUsage.tsx` 顶部 import 区，确认已有 `syncTokenUsage`。当前文件（第 29-48 行）import 列表中**没有** `syncTokenUsage`，需补上。在 `refreshTokenUsage,` 下方添加 `syncTokenUsage,`：

```typescript
import {
  clearTokenUsageData,
  createDeviceAlias,
  deleteDeviceAlias,
  getDbTokenUsage,
  getUserDevices,
  mergeDevices,
  refreshTokenUsage,
  renameDevice,
  syncTokenUsage,
  // ... 其余 type 导入
} from '../../api/tokenUsageApi';
```

同时移除不再使用的 `getAuthToken` import（第 55 行 `import { getAuthToken } from '../../api/authApi';`），因为 `handleSync` 不再直接 fetch。**先确认 `getAuthToken` 在文件其他地方没有使用**，若无其他引用再删除。

- [ ] **Step 3: 前端类型检查**

Run（在 `frontend/` 目录下）:
```bash
npx tsc --noEmit
```
Expected: 无报错。若提示 `syncTokenUsage` 未导出，回到 `tokenUsageApi.ts` 确认导出（第 329 行已有 `export async function syncTokenUsage`）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: 前端同步按钮改调 /sync 异步接口，不再阻塞等待

- 复用 syncTokenUsage() 调用后台 /sync
- 乐观提示用户数据约 1 分钟后自动更新
- 数据刷新交由 30 秒轮询自动完成

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 集成验证（重启服务 + 浏览器）

**Files:**
- 无文件改动，仅验证

**Interfaces:**
- Consumes: Task 1-5 全部完成

- [ ] **Step 1: 重启后端服务**

Run（在项目根目录 `G:\IdeaProjects\tools`）:
```bash
python dev_services.py restart backend
```
Expected: 终端输出后端启动成功，无报错

- [ ] **Step 2: 确认前端热加载生效**

观察前端 Vite 终端，确认 `TokenUsage.tsx` 改动已热更新（无报错）。若改动未生效：
```bash
python dev_services.py restart frontend
```

- [ ] **Step 3: 浏览器打开页面验证**

用浏览器（agent-browser 或 MCP playwright）打开 `http://localhost:5178/tools/token-usage`，使用测试账号 `peanut` / `Peanut2817*#` 登录。

验证标准（全部满足）：
- [ ] 页面首屏加载 < 1 秒（肉眼观察，无长时间 loading）
- [ ] 浏览器 DevTools Network 面板：`/summary` 和 `/details` 接口响应 < 500ms（首次）/ < 50ms（缓存命中）
- [ ] 浏览器 Console 无任何报错
- [ ] 点击"同步数据"按钮 -> 立即弹出 toast"后台同步已开始"-> 按钮不长时间转圈
- [ ] 等待约 1 分钟 -> 页面数据自动更新（30 秒轮询触发，summary 接口 cached=true 或新数据）

- [ ] **Step 4: 验证后端日志**

Run（在项目根目录）:
```bash
python dev_services.py logs backend
```
或在日志中确认：
- [ ] 进入页面时出现 `summary 缓存命中` 或 `summary 缓存未命中` 日志
- [ ] 点击同步后出现 `后台同步已开始` 相关日志
- [ ] 同步完成后出现 `warm_query_cache 预热成功: user=...` 日志
- [ ] 5 分钟后出现 `Token Usage 后台同步本轮结束` 日志

- [ ] **Step 5: 若验证失败，按 CLAUDE.md 报错修复原则处理**

任何报错（端口冲突、编译错误、Bean 初始化失败、数据库连接失败等）：
1. 立即停止后续操作
2. 分析报错原因（查日志）
3. 修复问题
4. 再次验证
5. 确认无报错后才能继续

不跳过报错，不带侥幸心理。

- [ ] **Step 6: 最终 Commit（如有验证中发现的修复）**

若 Step 3-4 发现问题并修复，提交修复：
```bash
git add <修复的文件>
git commit -m "fix: 修复集成验证中发现的问题

<具体问题描述>

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

若无需修复，跳过本步。

---

## Self-Review

**1. Spec 覆盖检查**

逐条对照设计文档的 5 个核心改动：
- ✅ 后端 `warm_query_cache()` 新增 —— Task 2
- ✅ 后端 `/sync` 改 async + asyncio.to_thread 立即返回 —— Task 3
- ✅ 后台同步完成后调用 warm —— Task 4
- ✅ 前端 `handleSync` 不阻塞、乐观提示 —— Task 5
- ✅ 配置 `CACHE_REDIS_TOKEN_USAGE_TTL=300`、`TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS=300` —— Task 1

设计文档的"错误处理""测试策略""验收标准"由 Task 6 集成验证覆盖。

**2. 占位符扫描**

- 无 "TBD"/"TODO"/"implement later"
- 所有代码步骤均给出完整代码块
- 测试步骤均给出可运行的测试代码
- 无"添加适当错误处理"等模糊描述（warm_query_cache 的异常处理已明确为 try/except + 记日志 + 返回 False）

**3. 类型一致性**

- `warm_query_cache(user_id: str) -> bool` —— Task 2 定义，Task 3 / Task 4 调用，签名一致
- `_build_summary_payload(db, user_id, req) -> Optional[dict]` —— Task 1 定义，Task 2 调用，签名一致
- `syncTokenUsage()` —— 前端 Task 5 调用，`tokenUsageApi.ts:329` 已存在且返回 `SyncTokenUsageResponse`（含 `started` 字段），与 Task 5 的 `result.started` 一致

**4. 循环依赖处理**

- Task 4 明确用函数内延迟导入 `from app.routes.token_usage import warm_query_cache` 避免 `background_sync -> token_usage` 的循环依赖（`token_usage` 已导入 `background_sync.register_pending_sync_user`）
- Task 3 的 `/sync` 在 `token_usage.py` 内部，直接调用 `warm_query_cache` 无循环问题

**5. 风险点**

- Task 3 测试用 `TestClient` + `monkeypatch` patch 模块属性，需确保 `asyncio.to_thread` 被 patch 成同步执行（已在测试中用 `with patch(...)` 处理）。若 TestClient 的事件循环导致 `asyncio.create_task` 调度异常，备选方案是直接 patch `asyncio.create_task` 为同步调用——但当前设计已用 `to_thread` patch 覆盖，应可工作。
- Task 5 移除 `getAuthToken` import 前需确认无其他引用，已在 Step 2 明确提示。
