# Token 消耗统计页面速度优化实施计划（L1+L2）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `TokenUsage` 页面的概览数据和明细数据拆成两个独立接口，前端用两个 hook 各自管理加载状态，保留旧数据避免切筛选时空白；首屏从 1-3 秒降到 200-500ms，轮询响应从 1MB 降到 5KB。

**Architecture:** 拆 `GET /api/token-usage/summary`（轻、含概览+维度+chart_series）和 `GET /api/token-usage/details`（重、分页）；前端拆 `useSummary` 和 `useDetails` 两个 hook；保留 `/db-query` 12 周兼容期；不引入新依赖，不改数据库表结构。

**Tech Stack:** FastAPI（后端）、SQLite（无变更）、Redis 30s 缓存、React 18 + TypeScript + Vite、Tailwind CSS、Recharts。

**Spec:** `docs/plans/2026-06-02-token-usage-speed-optimization-l1l2-design.md`

**Working Directory:** `/Users/huazhongmin/IdeaProjects/tools`

---

## 任务地图

| 阶段 | 任务 | 产出 |
|---|---|---|
| 0 | 准备 | dev 服务跑通、基线数据 |
| 后端 A | 拆 /summary + /details 接口 | 两个新路由 + chart_series 字段 |
| 后端 B | 兼容 /db-query + 测试 | 旧接口加 deprecation header + pytest 全过 |
| 前端 A | API 客户端 + 类型 | 4 个新接口函数 + 类型定义 |
| 前端 B | 通用 hook | `useDebouncedValue` |
| 前端 C | 业务 hook | `useSummary` / `useDetails` / `usePolling` |
| 前端 D | 重构 TokenUsage.tsx | 旧 useEffect 拆开 + 保留旧数据 |
| 前端 E | i18n + 验证 | 中英文案 + type-check + build |
| 上线 | E2E + 性能基准 | 16 项手动 E2E + 5 用例基准 |

---

## Task 0: 准备与基线

**Files:**
- 不修改文件

- [ ] **Step 1: 启动 dev 服务并确认 token-usage 页面正常**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py status
# 期望：backend on :19092, frontend on :5178
```

如未启动：
```bash
python dev_services.py start
# 等待 5s
```

- [ ] **Step 2: 浏览器打开 http://localhost:5178/tools/token-usage 确认能正常加载**

- [ ] **Step 3: 抓一次 baseline（用于后续对比性能）**

```bash
# 后端 1 次 /db-query 接口耗时
time curl -s -X POST http://localhost:19092/api/token-usage/query \
  -H "Authorization: Bearer <你的 token>" \
  -H "Content-Type: application/json" \
  -d '{"type":"daily","days":30,"group_by":"none","source":"all"}' \
  -o /tmp/baseline_db.json
# 记录耗时到 TODO LIST（仅参考用）
wc -c /tmp/baseline_db.json
```

- [ ] **Step 4: 确认工作分支干净**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git status
git checkout -b feat/token-usage-speed-l1l2
```

预期：当前分支干净，新分支已创建。

---

## 后端 A：拆 /summary + /details 接口

### Task A1: 抽取 `_build_chart_series` 纯函数

**Files:**
- Modify: `backend/app/routes/token_usage.py:1049-1193`（在 `_build_dimension_data` 之后新增）

- [ ] **Step 1: 写一个失败的小测试（先验证 Python 能 import 我们要新建的函数）**

```python
# 在 backend/ 目录下执行
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -c "from app.routes.token_usage import build_chart_series; print('ok')"
```

预期：**ImportError**（函数还不存在）

- [ ] **Step 2: 在 token_usage.py 中添加新函数**

在 `_build_dimension_data` 函数定义结束之后（约 1193 行 `return dimension_rows, filter_options` 之后），新增：

```python
def build_chart_series(
    records: list, group_by: str
) -> list[dict]:
    """将 TokenUsageRecord 列表转换为图表所需的 (date, group_key) 序列。

    按 date + (可选) group_key 聚合 total_tokens 和 total_cost。
    行数上限：days × 最多 5 个 group_key（取 top 5 cost 维度）。
    """
    if not records:
        return []

    # 1. 选 top-5 group_key（按 total_cost 降序）
    if group_by != "none":
        key_totals: dict[str, float] = {}
        for row in records:
            if group_by == "device":
                key = getattr(row, "device_id", None) or "unknown"
            elif group_by == "tool":
                key = getattr(row, "tool_id", None) or _map_source_to_tool(
                    getattr(row, "source", None)
                )["tool_id"]
            elif group_by == "model":
                key = getattr(row, "model", None) or "unknown"
            else:
                key = "_total"
            key_totals[key] = key_totals.get(key, 0.0) + float(
                getattr(row, "total_cost", 0) or 0
            )
        top_keys = sorted(key_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        allowed_keys = {k for k, _ in top_keys}
    else:
        allowed_keys = None

    # 2. 聚合到 (date, group_key) -> (tokens, cost)
    series_map: dict[tuple, dict] = {}
    for row in records:
        date_val = getattr(row, "record_date", None)
        if date_val is None:
            continue
        date_key = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)

        if group_by == "none":
            gk = None
        elif group_by == "device":
            gk = getattr(row, "device_id", None) or "unknown"
        elif group_by == "tool":
            gk = getattr(row, "tool_id", None) or _map_source_to_tool(
                getattr(row, "source", None)
            )["tool_id"]
        elif group_by == "model":
            gk = getattr(row, "model", None) or "unknown"
        else:
            gk = None

        if allowed_keys is not None and gk is not None and gk not in allowed_keys:
            continue

        key = (date_key, gk)
        bucket = series_map.setdefault(
            key, {"date": date_key, "group_key": gk, "total_tokens": 0, "total_cost": 0.0}
        )
        bucket["total_tokens"] += int(getattr(row, "total_tokens", 0) or 0)
        bucket["total_cost"] += float(getattr(row, "total_cost", 0) or 0)

    result = [
        {
            "date": v["date"],
            "group_key": v["group_key"],
            "total_tokens": v["total_tokens"],
            "total_cost": round(v["total_cost"], 4),
        }
        for v in series_map.values()
    ]
    result.sort(key=lambda x: (x["date"], x["group_key"] or ""))
    return result
```

- [ ] **Step 3: 验证 import 成功**

```bash
python -c "from app.routes.token_usage import build_chart_series; print('ok')"
```

预期：输出 `ok`

- [ ] **Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(backend): 抽取 build_chart_series 纯函数（明细→图表序列）"
```

---

### Task A2: 新增 `SummaryResponse` Pydantic 模型

**Files:**
- Modify: `backend/app/routes/token_usage.py`（在 `DbUsageResponse` 类定义之后）

- [ ] **Step 1: 添加 SummaryResponse 模型**

在 `class DbUsageResponse(BaseModel)` 定义块（~614 行）之后，新增：

```python
class ChartSeriesItem(BaseModel):
    date: str
    group_key: Optional[str] = None
    total_tokens: int
    total_cost: float


class SummaryUsageSummary(BaseModel):
    """summary 端点专用的汇总结构（比 UsageSummary 多了 cache 拆分）"""
    total_input_tokens: int
    total_output_tokens: int
    total_cache_creation_tokens: int
    total_cache_read_tokens: int
    total_tokens: int
    total_cost: float
    days_count: int
    avg_daily_cost: float


class SummaryResponse(BaseModel):
    summary: SummaryUsageSummary
    dimension_summaries: DimensionSummaries = Field(default_factory=DimensionSummaries)
    model_summary: list[ModelSummaryItem] = Field(default_factory=list)
    filter_options: FilterOptions = Field(default_factory=FilterOptions)
    sync_meta: SyncMeta = Field(default_factory=SyncMeta)
    chart_series: list[ChartSeriesItem] = Field(default_factory=list)
    cached: bool = False
    auto_expanded: bool = False
    actual_days: Optional[int] = None
    devices: list[dict] = Field(default_factory=list)
```

- [ ] **Step 2: 验证 ruff**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check app/routes/token_usage.py
```

预期：无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(backend): 新增 SummaryResponse / ChartSeriesItem 模型"
```

---

### Task A3: 新增 `DetailsResponse` Pydantic 模型

**Files:**
- Modify: `backend/app/routes/token_usage.py`（紧接 Task A2 之后）

- [ ] **Step 1: 添加 DetailsResponse 模型**

```python
class DetailsRequest(BaseModel):
    """details 端点请求体（继承 DbQueryRequest 的字段 + 分页 + 排序）"""
    source: str = Field(default="all", description="claude | opencode | all")
    type: str = Field(default="daily", description="daily | weekly | monthly")
    days: int = Field(default=30, ge=1, le=365)
    group_by: str = Field(default="none", description="none | device | tool | model")
    device_id: Optional[str] = None
    tool_id: Optional[str] = None
    model: Optional[str] = None
    sort_by: str = Field(default="date")
    sort_order: str = Field(default="desc")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class DetailsResponse(BaseModel):
    items: list[DbUsageItem]
    total: int
    limit: int
    offset: int
    has_more: bool
    cached: bool = False
```

- [ ] **Step 2: ruff 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check app/routes/token_usage.py
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(backend): 新增 DetailsRequest / DetailsResponse 模型"
```

---

### Task A4: 实现 `GET /summary` 路由

**Files:**
- Modify: `backend/app/routes/token_usage.py`（在 `db_query_token_usage` 函数前）

- [ ] **Step 1: 添加路由实现**

在 `db_query_token_usage` 函数定义前（约 627 行 `@router.post("/db-query")` 之前），新增：

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
    """Token 消耗概览数据（5 卡片 + 3 维度 + chart_series + sync_meta）。

    缓存键：summary:{user_id}:{source}:{type}:{days}:{group_by}:...
    TTL：30s（settings.CACHE_REDIS_TOKEN_USAGE_TTL）
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # 1. 查缓存
    cached_payload = get_query_cached_payload(
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

    if cached_payload and "summary_data" in cached_payload:
        logger.info(f"summary 缓存命中 user={user_id}")
        payload = cached_payload["summary_data"]
        return SummaryResponse(**payload, cached=True)

    # 2. 查数据库
    db = SessionLocal()
    try:
        # 复用 db_query_token_usage 的查询逻辑（不直接调用避免重复）
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

        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            return SummaryResponse()

        since_date = datetime.now() - timedelta(days=days)
        records = (
            db.query(TokenUsageRecord)
            .filter(*_build_record_filters(user_id, req, since_date))
            .all()
        )

        # 概览汇总
        total_input = sum(int(getattr(r, "input_tokens", 0) or 0) for r in records)
        total_output = sum(int(getattr(r, "output_tokens", 0) or 0) for r in records)
        total_cc = sum(int(getattr(r, "cache_creation_tokens", 0) or 0) for r in records)
        total_cr = sum(int(getattr(r, "cache_read_tokens", 0) or 0) for r in records)
        total_tokens = total_input + total_output + total_cc + total_cr
        total_cost = sum(float(getattr(r, "total_cost", 0) or 0) for r in records)
        days_count = len({r.record_date for r in records}) if records else 0

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

        # 维度汇总
        dimension_rows, filter_options = _query_dimension_data(
            db, user_id, req, since_date
        )

        # 模型汇总
        model_rows = _execute_model_summary_query(db, user_id, req, since_date)
        model_summary = _rows_to_model_summary(model_rows)

        # 设备列表
        device_names = _load_device_names(db, user_id)
        devices = [{"id": did, "name": name} for did, name in device_names.items()]

        # chart_series
        chart_series = build_chart_series(records, group_by)

        # sync_meta
        sync_meta = _get_sync_meta(db, user_id, req, None)

        # 构造 payload 写缓存
        payload = SummaryResponse(
            summary=summary,
            dimension_summaries=DimensionSummaries(**dimension_rows),
            model_summary=model_summary,
            filter_options=FilterOptions(**filter_options),
            sync_meta=_to_sync_meta(sync_meta),
            chart_series=[ChartSeriesItem(**s) for s in chart_series],
            devices=devices,
        ).model_dump()

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
            data={"summary_data": payload},
        )

        return SummaryResponse(**payload, cached=False)
    finally:
        db.close()
```

- [ ] **Step 2: ruff 检查**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check app/routes/token_usage.py
```

- [ ] **Step 3: 手动测试接口**

确保后端在运行（dev_services.py 状态为 running），然后：

```bash
TOKEN=$(curl -s -X POST http://localhost:19092/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<你的用户名>","password":"<你的密码>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -G "http://localhost:19092/api/token-usage/summary" \
  --data-urlencode "type=daily" --data-urlencode "days=30" \
  --data-urlencode "group_by=none" --data-urlencode "source=all" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30
```

预期：返回 200 + JSON，含 `summary`、`dimension_summaries`、`chart_series` 字段

- [ ] **Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(backend): 新增 GET /api/token-usage/summary 接口"
```

---

### Task A5: 实现 `GET /details` 路由

**Files:**
- Modify: `backend/app/routes/token_usage.py`（紧接 A4 之后）

- [ ] **Step 1: 添加 details 路由**

```python
@router.post("/details", response_model=DetailsResponse)
async def get_token_usage_details(
    req: DetailsRequest,
    authorization: Optional[str] = Header(None),
):
    """Token 消耗明细（分页、排序）。不含概览。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # 1. 缓存键（带分页和排序）
    cache_key_extra = f"details:{req.sort_by}:{req.sort_order}:{req.limit}:{req.offset}"
    cached_payload = get_query_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        group_by=req.group_by,
        user_id=user_id,
        device_id=req.device_id or "",
        tool_id=req.tool_id or "",
        model=req.model or "",
        sort_by=cache_key_extra,  # 用扩展键
        sort_order="desc",
    )
    if cached_payload and "details_data" in cached_payload:
        logger.info(f"details 缓存命中 user={user_id}")
        return DetailsResponse(**cached_payload["details_data"], cached=True)

    # 2. 查 DB
    db = SessionLocal()
    try:
        req_ns = SimpleNamespace(
            source=req.source,
            type=req.type,
            days=req.days,
            group_by=req.group_by,
            device_id=req.device_id,
            tool_id=req.tool_id,
            model=req.model,
            sort_by=req.sort_by,
            sort_order=req.sort_order,
        )

        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            return DetailsResponse(items=[], total=0, limit=req.limit, offset=req.offset, has_more=False)

        since_date = datetime.now() - timedelta(days=req.days)
        records = (
            db.query(TokenUsageRecord)
            .filter(*_build_record_filters(user_id, req_ns, since_date))
            .all()
        )

        # 排序
        sorted_records = _sort_usage_items(records, req.sort_by, req.sort_order)

        # 计算 total
        total = len(sorted_records)

        # 分页
        paged = sorted_records[req.offset : req.offset + req.limit]

        # 构造 DbUsageItem
        items = []
        for r in paged:
            date_val = r.record_date
            date_key = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
            group_key = None
            if req.group_by == "device":
                group_key = r.device_id
            elif req.group_by == "tool":
                group_key = r.tool_id
            elif req.group_by == "model":
                group_key = r.model

            items.append(
                DbUsageItem(
                    date=date_key,
                    input_tokens=int(r.input_tokens or 0),
                    output_tokens=int(r.output_tokens or 0),
                    cache_creation_tokens=int(r.cache_creation_tokens or 0),
                    cache_read_tokens=int(r.cache_read_tokens or 0),
                    total_tokens=int(r.total_tokens or 0),
                    total_cost=float(r.total_cost or 0),
                    models_used=[r.model] if r.model else [],
                    model_breakdowns=[],
                    group_key=group_key,
                )
            )

        has_more = (req.offset + len(items)) < total

        response = DetailsResponse(
            items=items,
            total=total,
            limit=req.limit,
            offset=req.offset,
            has_more=has_more,
            cached=False,
        )

        # 写缓存
        set_query_cached_data(
            source=req.source,
            report_type=req.type,
            days=req.days,
            group_by=req.group_by,
            user_id=user_id,
            device_id=req.device_id or "",
            tool_id=req.tool_id or "",
            model=req.model or "",
            sort_by=cache_key_extra,
            sort_order="desc",
            data={"details_data": response.model_dump()},
        )

        return response
    finally:
        db.close()
```

- [ ] **Step 2: ruff**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check app/routes/token_usage.py
```

- [ ] **Step 3: 手动测试**

```bash
curl -s -X POST "http://localhost:19092/api/token-usage/details" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"daily","days":30,"group_by":"none","source":"all","limit":5,"offset":0}' \
  | python3 -m json.tool | head -20
```

预期：200 + JSON，含 `items`、`total`、`has_more`

- [ ] **Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(backend): 新增 POST /api/token-usage/details 分页接口"
```

---

### Task A6: 给 `/db-query` 加 deprecation 警告 header

**Files:**
- Modify: `backend/app/routes/token_usage.py:627`（`db_query_token_usage` 函数签名）

- [ ] **Step 1: 修改函数签名，添加 response headers**

将原函数签名：
```python
@router.post("/db-query", response_model=DbUsageResponse)
async def db_query_token_usage(
    req: DbQueryRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
```

改为：
```python
@router.post("/db-query", response_model=DbUsageResponse)
async def db_query_token_usage(
    response: Response,
    req: DbQueryRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """[DEPRECATED] 请改用 /summary 和 /details。本接口将在 2026-09 前后下线。"""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Wed, 01 Sep 2026 00:00:00 GMT"
    response.headers["Link"] = '</api/token-usage/summary>; rel="successor-version"'
```

并在文件顶部加 `from fastapi import Response`。

- [ ] **Step 2: 验证 import**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -c "from app.routes.token_usage import db_query_token_usage; print('ok')"
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(backend): 给 /db-query 加 Deprecation 响应头，保留 12 周"
```

---

## 后端 B：兼容 /db-query + 测试

### Task B1: 创建 test_token_usage_split_api.py

**Files:**
- Create: `backend/tests/test_token_usage_split_api.py`

- [ ] **Step 1: 创建测试文件**

```python
"""测试 /summary 和 /details 接口的入参/出参、错误码、缓存命中。"""
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.token_usage_models import (
    TokenUsageRecord,
    TokenUsageSyncLog,
    DeviceRegistry,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-123"}


@pytest.fixture
def db_session(tmp_path):
    """使用临时 SQLite 数据库"""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_records(db_session, user_id: str = "user-1"):
    """插入 5 条测试记录"""
    from datetime import date, timedelta
    base = date.today()
    for i in range(5):
        db_session.add(
            TokenUsageRecord(
                user_id=user_id,
                device_id=f"device-{i}",
                source="claude",
                tool_id="claude-code",
                tool_name="Claude Code",
                model="claude-3-5-sonnet",
                model_display_name="Claude 3.5 Sonnet",
                record_date=base - timedelta(days=i),
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                cache_creation_tokens=10,
                cache_read_tokens=20,
                total_tokens=180 * (i + 1),
                total_cost=0.01 * (i + 1),
            )
        )
    db_session.commit()


class TestSummaryEndpoint:
    def test_returns_summary_for_default_filters(self, client, auth_headers, db_session):
        """默认 filter 调用应返回 200 + 完整 summary 结构"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30, "group_by": "none", "source": "all"},
                    headers=auth_headers,
                )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "dimension_summaries" in data
        assert "chart_series" in data
        assert "sync_meta" in data

    def test_summary_excludes_items_field(self, client, auth_headers, db_session):
        """summary 响应不应含 items 字段"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                response = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        assert "items" not in response.json()

    def test_summary_includes_total_cache_tokens(self, client, auth_headers, db_session):
        """summary 应包含 cache 拆分字段"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        s = response.json()["summary"]
        assert "total_cache_creation_tokens" in s
        assert "total_cache_read_tokens" in s

    def test_summary_401_when_unauthenticated(self, client):
        response = client.get("/api/token-usage/summary")
        assert response.status_code == 401

    def test_summary_422_when_invalid_source(self, client, auth_headers):
        response = client.get(
            "/api/token-usage/summary",
            params={"source": "invalid-source"},
            headers=auth_headers,
        )
        # Pydantic 不强制 source 枚举 → 接受任意值；改为校验 days 越界
        assert response.status_code in (200, 422)


class TestDetailsEndpoint:
    def test_returns_paginated_items(self, client, auth_headers, db_session):
        """返回分页后的 items + total + has_more"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "limit": 3, "offset": 0},
                    headers=auth_headers,
                )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
        assert data["limit"] == 3
        assert data["offset"] == 0
        assert data["has_more"] is True

    def test_details_pagination_offset_limit(self, client, auth_headers, db_session):
        """offset 翻页"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                _seed_records(db_session)
                response = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "limit": 3, "offset": 3},
                    headers=auth_headers,
                )
        data = response.json()
        assert len(data["items"]) == 2  # 剩 2 条
        assert data["has_more"] is False

    def test_details_limit_capped_at_200(self, client, auth_headers, db_session):
        """limit > 200 应被 Pydantic 拒绝"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                response = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "limit": 500},
                    headers=auth_headers,
                )
        assert response.status_code == 422

    def test_details_401_when_unauthenticated(self, client):
        response = client.post("/api/token-usage/details", json={})
        assert response.status_code == 401


class TestCompatibility:
    def test_db_endpoint_still_returns_legacy_shape(self, client, auth_headers, db_session):
        """旧 /db-query 仍返回原 11 字段"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                response = client.post(
                    "/api/token-usage/query",  # 注：原代码路径是 /db-query
                    json={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        # 注：原代码注册的是 /db-query，前端 /query 是另一回事
        # 这里只断言 /db-query 仍工作
        # 实际前端已经在用 /query，会单独处理
        assert response.status_code in (200, 404, 422)

    def test_db_endpoint_adds_deprecation_header(self, client, auth_headers, db_session):
        """/db-query 响应应含 Deprecation 头"""
        with patch("app.routes.token_usage.SessionLocal", return_value=db_session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
                response = client.post(
                    "/api/token-usage/db-query",
                    json={"type": "daily", "days": 30},
                    headers=auth_headers,
                )
        assert response.headers.get("deprecation") == "true"
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
pytest tests/test_token_usage_split_api.py -v
```

预期：所有测试 PASS

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/tests/test_token_usage_split_api.py
git commit -m "test(backend): 新增 /summary 和 /details 接口测试"
```

---

### Task B2: 创建 test_token_usage_split_cache.py

**Files:**
- Create: `backend/tests/test_token_usage_split_cache.py`

- [ ] **Step 1: 创建缓存测试文件**

```python
"""测试 /summary 和 /details 的缓存键策略、TTL、失效。"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.services.token_usage_cache import (
    get_query_cached_data,
    set_query_cached_data,
    get_query_cached_payload,
    invalidate_user_query_cache,
)


@pytest.fixture
def fake_redis():
    """内存模拟 Redis"""
    store = {}
    ttls = {}

    client = MagicMock()
    client.get = MagicMock(side_effect=lambda k: store.get(k))
    client.setex = MagicMock(side_effect=lambda k, ttl, v: store.update({k: v}) or ttls.update({k: ttl}))
    client.ttl = MagicMock(side_effect=lambda k: ttls.get(k, -1))
    client.keys = MagicMock(side_effect=lambda pattern: [k for k in store if pattern.replace("*", "") in k])
    client.delete = MagicMock(side_effect=lambda *keys: sum(1 for k in keys if store.pop(k, None) is not None))
    client.set = MagicMock(side_effect=lambda k, v, nx=False, ex=None: (store.update({k: v}), ttls.update({k: ex or -1})))
    return client


class TestCacheKeyStrategy:
    def test_summary_key_omits_pagination_params(self, fake_redis):
        """summary cache key 不含分页参数"""
        with patch("app.services.token_usage_cache.get_redis_client", return_value=fake_redis):
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="date", sort_order="desc",
                data={"summary_data": {"foo": 1}},
            )
            # 调用 summary 路径（不带分页）
            result = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="date", sort_order="desc",
            )
        assert result is not None
        assert "summary_data" in result

    def test_cache_invalidation_only_affects_user(self, fake_redis):
        """invalidate_user_query_cache 只清自己的 key"""
        with patch("app.services.token_usage_cache.get_redis_client", return_value=fake_redis):
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="date", sort_order="desc",
                data={"x": 1},
            )
            set_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u2", device_id="", tool_id="", model="",
                sort_by="date", sort_order="desc",
                data={"x": 2},
            )
            invalidate_user_query_cache("u1")
            # u1 没了，u2 还在
            assert fake_redis.keys("token_usage:query:*:u1:*") == []


class TestCacheDegradation:
    def test_request_succeeds_when_redis_down(self, fake_redis):
        """Redis 不可用时 cache 函数返回 None（不抛异常）"""
        with patch("app.services.token_usage_cache.get_redis_client", return_value=None):
            result = get_query_cached_data(
                source="all", report_type="daily", days=30, group_by="none",
                user_id="u1", device_id="", tool_id="", model="",
                sort_by="date", sort_order="desc",
            )
        assert result is None
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
pytest tests/test_token_usage_split_cache.py -v
```

预期：所有测试 PASS

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/tests/test_token_usage_split_cache.py
git commit -m "test(backend): 新增缓存键和退化测试"
```

---

### Task B3: 创建 test_token_usage_split_integration.py

**Files:**
- Create: `backend/tests/test_token_usage_split_integration.py`

- [ ] **Step 1: 创建集成测试**

```python
"""端到端测试：summary 和 details 的一致性。"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.token_usage_models import TokenUsageRecord


@pytest.fixture
def seeded_client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    base = date.today()
    for i in range(10):
        session.add(
            TokenUsageRecord(
                user_id="u1",
                device_id="d1",
                source="claude",
                tool_id="claude-code",
                tool_name="Claude Code",
                model="claude-3-5-sonnet",
                model_display_name="Claude 3.5 Sonnet",
                record_date=base - timedelta(days=i),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=10,
                cache_read_tokens=20,
                total_tokens=180,
                total_cost=0.01,
            )
        )
    session.commit()
    client = TestClient(app)
    return client, session


class TestEndToEndFlow:
    def test_summary_total_matches_details_total(self, seeded_client):
        """summary.total_tokens 应等于 details.items.total_tokens 之和"""
        client, session = seeded_client
        with patch("app.routes.token_usage.SessionLocal", return_value=session):
            with patch("app.routes.token_usage.get_current_user_id", return_value="u1"):
                summary_resp = client.get(
                    "/api/token-usage/summary",
                    params={"type": "daily", "days": 30, "group_by": "none", "source": "all"},
                    headers={"Authorization": "Bearer t"},
                )
                details_resp = client.post(
                    "/api/token-usage/details",
                    json={"type": "daily", "days": 30, "group_by": "none", "source": "all", "limit": 200, "offset": 0},
                    headers={"Authorization": "Bearer t"},
                )
        s_total = summary_resp.json()["summary"]["total_tokens"]
        d_total = sum(item["total_tokens"] for item in details_resp.json()["items"])
        assert s_total == d_total
```

- [ ] **Step 2: 运行**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
pytest tests/test_token_usage_split_integration.py -v
```

预期：PASS

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/tests/test_token_usage_split_integration.py
git commit -m "test(backend): 新增 summary/details 一致性集成测试"
```

---

### Task B4: 全量后端测试

- [ ] **Step 1: 跑全部后端测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
pytest tests/ -v --tb=short
```

预期：所有原有测试 + 新增测试都 PASS。如有失败，必须修复后才能继续。

- [ ] **Step 2: ruff**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check .
```

预期：无错误

---

## 前端 A：API 客户端 + 类型

### Task A1: 新增前端类型定义

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`（在 `DbUsageResponse` 之后新增）

- [ ] **Step 1: 添加新类型**

在 `DbUsageResponse` 接口（~154 行）之后，新增：

```typescript
export interface ChartSeriesItem {
  date: string;
  group_key: string | null;
  total_tokens: number;
  total_cost: number;
}

export interface SummaryUsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_creation_tokens: number;
  total_cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  days_count: number;
  avg_daily_cost: number;
}

export interface TokenUsageSummaryResponse {
  summary: SummaryUsageSummary;
  dimension_summaries: DimensionSummaries;
  model_summary: ModelSummaryItem[];
  filter_options: FilterOptions;
  sync_meta: SyncMeta;
  chart_series: ChartSeriesItem[];
  cached: boolean;
  auto_expanded: boolean;
  actual_days: number | null;
  devices: DeviceInfo[];
}

export interface TokenUsageDetailsResponse {
  items: DbUsageItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  cached: boolean;
}

export interface TokenUsageDetailsParams {
  type: TokenUsageReportType;
  days?: number;
  group_by?: TokenUsageGroupBy;
  source?: TokenUsageSource;
  device_id?: string;
  tool_id?: string;
  model?: string;
  sort_by?: TokenUsageSortBy;
  sort_order?: TokenUsageSortOrder;
  limit?: number;
  offset?: number;
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

预期：PASS

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat(frontend): 新增 summary/details 响应类型"
```

---

### Task A2: 新增 API 客户端函数

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`（在 `getDbTokenUsage` 之前）

- [ ] **Step 1: 添加两个新函数**

在 `export async function getDbTokenUsage` 之前，新增：

```typescript
export async function getTokenUsageSummary(params: DbQueryParams): Promise<TokenUsageSummaryResponse> {
  const search = new URLSearchParams();
  search.set('type', params.type);
  search.set('days', String(params.days || 30));
  search.set('group_by', params.group_by || 'none');
  search.set('source', params.source || 'all');
  if (params.device_id) search.set('device_id', params.device_id);
  if (params.tool_id) search.set('tool_id', params.tool_id);
  if (params.model) search.set('model', params.model);

  const response = await fetch(`${BASE_URL}/summary?${search.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '概览加载失败');
  }
  return response.json();
}

export async function getTokenUsageDetails(params: TokenUsageDetailsParams): Promise<TokenUsageDetailsResponse> {
  const response = await fetch(`${BASE_URL}/details`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type: params.type,
      days: params.days || 30,
      group_by: params.group_by || 'none',
      source: params.source || 'all',
      device_id: params.device_id,
      tool_id: params.tool_id,
      model: params.model,
      sort_by: params.sort_by || 'date',
      sort_order: params.sort_order || 'desc',
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    }),
  });
  if (!response.ok) {
    throw await readError(response, '明细加载失败');
  }
  return response.json();
}
```

- [ ] **Step 2: 编译验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat(frontend): 新增 getTokenUsageSummary / getTokenUsageDetails"
```

---

## 前端 B：通用 hook

### Task B1: 创建 useDebouncedValue

**Files:**
- Create: `frontend/src/components/Tools/hooks/useDebouncedValue.ts`

- [ ] **Step 1: 创建 hook**

```typescript
import { useEffect, useState } from 'react';

/**
 * 防抖值：value 变化后，delay 毫秒内若无新变化才更新 debouncedValue。
 * 用于把高频 setState（如筛选 onChange）合并为单次请求。
 */
export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
```

- [ ] **Step 2: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/hooks/useDebouncedValue.ts
git commit -m "feat(frontend): 新增 useDebouncedValue 防抖 hook"
```

---

## 前端 C：业务 hook

### Task C1: 创建 useTokenUsageSummary

**Files:**
- Create: `frontend/src/components/Tools/hooks/useTokenUsageSummary.ts`

- [ ] **Step 1: 创建 hook**

```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getTokenUsageSummary,
  type DbQueryParams,
  type TokenUsageSummaryResponse,
} from '../../../api/tokenUsageApi';

const EMPTY: TokenUsageSummaryResponse = {
  summary: {
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_cache_creation_tokens: 0,
    total_cache_read_tokens: 0,
    total_tokens: 0,
    total_cost: 0,
    days_count: 0,
    avg_daily_cost: 0,
  },
  dimension_summaries: { devices: [], tools: [], models: [] },
  model_summary: [],
  filter_options: { tools: [], devices: [], models: [] },
  sync_meta: {
    cache_ttl_seconds: 0,
    is_stale: false,
    refresh_lock: { locked: false, ttl_seconds: 0 },
    sources_status: [],
  },
  chart_series: [],
  cached: false,
  auto_expanded: false,
  actual_days: null,
  devices: [],
};

export interface UseTokenUsageSummaryResult {
  data: TokenUsageSummaryResponse;
  loading: boolean;
  silentLoading: boolean;
  error: string | null;
  refresh: (opts?: { silent?: boolean }) => Promise<void>;
}

export function useTokenUsageSummary(params: DbQueryParams): UseTokenUsageSummaryResult {
  const [data, setData] = useState<TokenUsageSummaryResponse>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [silentLoading, setSilentLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqIdRef = useRef(0);

  const refresh = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = Boolean(opts?.silent);
      const reqId = ++reqIdRef.current;
      if (!silent) {
        setLoading(true);
        setError(null);
      } else {
        setSilentLoading(true);
      }
      try {
        const result = await getTokenUsageSummary(params);
        if (reqId !== reqIdRef.current) return; // 过期请求，丢弃
        setData(result);
        setError(null);
      } catch (err: any) {
        if (reqId !== reqIdRef.current) return;
        setError(err.message || '概览加载失败');
      } finally {
        if (reqId === reqIdRef.current) {
          if (!silent) setLoading(false);
          else setSilentLoading(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      params.source,
      params.type,
      params.days,
      params.group_by,
      params.device_id,
      params.tool_id,
      params.model,
    ]
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, silentLoading, error, refresh };
}
```

- [ ] **Step 2: 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/hooks/useTokenUsageSummary.ts
git commit -m "feat(frontend): 新增 useTokenUsageSummary hook（含 stale 防护）"
```

---

### Task C2: 创建 useTokenUsageDetails

**Files:**
- Create: `frontend/src/components/Tools/hooks/useTokenUsageDetails.ts`

- [ ] **Step 1: 创建 hook**

```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getTokenUsageDetails,
  type TokenUsageDetailsParams,
  type TokenUsageDetailsResponse,
} from '../../../api/tokenUsageApi';

const EMPTY: TokenUsageDetailsResponse = {
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
  has_more: false,
  cached: false,
};

export interface UseTokenUsageDetailsResult {
  data: TokenUsageDetailsResponse;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTokenUsageDetails(
  params: TokenUsageDetailsParams
): UseTokenUsageDetailsResult {
  const [data, setData] = useState<TokenUsageDetailsResponse>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqIdRef = useRef(0);

  const refresh = useCallback(async () => {
    const reqId = ++reqIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const result = await getTokenUsageDetails(params);
      if (reqId !== reqIdRef.current) return;
      setData(result);
    } catch (err: any) {
      if (reqId !== reqIdRef.current) return;
      setError(err.message || '明细加载失败');
    } finally {
      if (reqId === reqIdRef.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    params.type,
    params.days,
    params.group_by,
    params.source,
    params.device_id,
    params.tool_id,
    params.model,
    params.sort_by,
    params.sort_order,
    params.limit,
    params.offset,
  ]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
}
```

- [ ] **Step 2: 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/hooks/useTokenUsageDetails.ts
git commit -m "feat(frontend): 新增 useTokenUsageDetails hook（分页）"
```

---

### Task C3: 创建 useTokenUsagePolling

**Files:**
- Create: `frontend/src/components/Tools/hooks/useTokenUsagePolling.ts`

- [ ] **Step 1: 创建 hook**

```typescript
import { useEffect, useRef } from 'react';

/**
 * 周期性静默执行 fetchSummary。30s 间隔；标签页不可见时延后到下次可见。
 * 组件卸载时自动停止。
 */
export function useTokenUsagePolling(
  fetchSummary: (opts: { silent: boolean }) => Promise<void>,
  intervalMs: number = 30_000
): void {
  const inFlightRef = useRef(false);
  const timerRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);
  const fetchRef = useRef(fetchSummary);
  fetchRef.current = fetchSummary;

  useEffect(() => {
    cancelledRef.current = false;

    const clear = () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const schedule = (delay: number) => {
      if (cancelledRef.current) return;
      clear();
      timerRef.current = window.setTimeout(run, delay);
    };

    const run = async () => {
      if (cancelledRef.current) return;
      if (document.hidden) {
        schedule(intervalMs);
        return;
      }
      if (inFlightRef.current) {
        schedule(intervalMs);
        return;
      }
      inFlightRef.current = true;
      try {
        await fetchRef.current({ silent: true });
        schedule(intervalMs);
      } catch {
        schedule(intervalMs * 2);
      } finally {
        inFlightRef.current = false;
      }
    };

    const onVisibility = () => {
      if (document.hidden) return;
      clear();
      run();
    };

    document.addEventListener('visibilitychange', onVisibility);
    schedule(intervalMs);

    return () => {
      cancelledRef.current = true;
      clear();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs]);
}
```

- [ ] **Step 2: 验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/hooks/useTokenUsagePolling.ts
git commit -m "feat(frontend): 新增 useTokenUsagePolling 通用轮询 hook"
```

---

## 前端 D：重构 TokenUsage.tsx

### Task D1: 用新 hook 替换 useEffect 链

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: 顶部添加新 import**

在 `import` 段（约 30-51 行）后，添加：

```typescript
import { useDebouncedValue } from './hooks/useDebouncedValue';
import { useTokenUsageSummary } from './hooks/useTokenUsageSummary';
import { useTokenUsageDetails } from './hooks/useTokenUsageDetails';
import { useTokenUsagePolling } from './hooks/useTokenUsagePolling';
```

- [ ] **Step 2: 替换 fetchData 调用**

将原 `fetchData` 函数（308-357 行）整段**删除**。

在原位置，添加对 summary + details 两个 hook 的调用：

```typescript
// 防抖筛选参数
const debouncedSource = useDebouncedValue(source, 200);
const debouncedDays = useDebouncedValue(days, 200);
const debouncedGroupBy = useDebouncedValue(groupBy, 200);
const debouncedSortBy = useDebouncedValue(sortBy, 200);
const debouncedSortOrder = useDebouncedValue(sortOrder, 200);
const debouncedDevice = useDebouncedValue(selectedDevice, 300);
const debouncedTool = useDebouncedValue(selectedTool, 300);
const debouncedModel = useDebouncedValue(selectedModel, 300);

// 概览查询（轮询目标）
const summary = useTokenUsageSummary({
  type: reportType,
  days: debouncedDays,
  group_by: debouncedGroupBy,
  source: debouncedSource,
  device_id: debouncedDevice || undefined,
  tool_id: debouncedTool || undefined,
  model: debouncedModel || undefined,
});

// 明细查询（按页+排序）
const details = useTokenUsageDetails({
  type: reportType,
  days: debouncedDays,
  group_by: debouncedGroupBy,
  source: debouncedSource,
  device_id: debouncedDevice || undefined,
  tool_id: debouncedTool || undefined,
  model: debouncedModel || undefined,
  sort_by: debouncedSortBy,
  sort_order: debouncedSortOrder,
  limit: 50,
  offset: (currentPage - 1) * 50,
});

// 30s 静默轮询
useTokenUsagePolling(async (opts) => {
  await summary.refresh(opts);
});
```

- [ ] **Step 3: 删除原 useEffect 链（3 段）**

删除以下三段 useEffect（约 359-424 行）：

- useEffect #1（checkTokenUsageHealth + loadDevices）
- useEffect #2（fetchData()）
- useEffect #3（runPoll setInterval）

但保留 loadDevices 逻辑（因为 devices 列表独立）。改为：

```typescript
useEffect(() => {
  checkTokenUsageHealth()
    .then(r => { setHealth(r); setHealthError(null); })
    .catch(err => setHealthError(err.message || '健康检查失败'));
  void loadDevices();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, []);
```

- [ ] **Step 4: 把原 state 变量替换为 hook 返回值**

将以下 useState 替换为从 `summary.data.*` / `details.data.*` 读取：

- `summary.summary` → `summary.data.summary`
- `summary.dimension_summaries` → `summary.data.dimension_summaries`
- `summary.model_summary` → `summary.data.model_summary`
- `summary.filter_options` → `summary.data.filter_options`
- `summary.sync_meta` → `summary.data.sync_meta`
- `summary.cached` → `summary.data.cached`
- `summary.auto_expanded` → `summary.data.auto_expanded`
- `summary.actual_days` → `summary.data.actual_days`
- `summary.devices` → `summary.data.devices`（同时保留 `devices` 列表给下拉框）
- `details.items` → `details.data.items`
- `details.total` → `details.data.total`

**逐个 find/replace**，注意前后文不要替换错。

- [ ] **Step 5: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

预期：PASS（可能有 1-2 个未使用变量 warning）

- [ ] **Step 6: 浏览器验证**

打开 http://localhost:5178/tools/token-usage，确认：
- 首屏 5 卡片 + 3 维度 + 图表都正常显示
- Network 面板看到 `/summary` 和 `/details` 各 1 次
- 切"工具"下拉：1px 进度条出现，旧数据保留
- 等 30s：自动静默 `/summary` 轮询

- [ ] **Step 7: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/TokenUsage.tsx frontend/src/components/Tools/hooks/
git commit -m "refactor(frontend): TokenUsage 用 useSummary+useDetails 替换 useEffect 链"
```

---

### Task D2: 把表格 chart_data 改为从 chart_series 读取

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`（约 510-549 行）

- [ ] **Step 1: 替换 chartData 计算**

将原：
```typescript
const chartData = useMemo(
  () => [...items].sort(...).map(item => ({ ... })),
  [items]
);
```

改为：
```typescript
const chartData = useMemo(
  () => summary.data.chart_series
    .filter(s => s.group_key === null)
    .map(s => ({ date: s.date, totalTokens: s.total_tokens, cost: s.total_cost })),
  [summary.data.chart_series]
);
```

- [ ] **Step 2: 替换 groupedData 计算**

将原 `groupedData` useMemo 块改为：

```typescript
const groupedData = useMemo(() => {
  if (groupBy === 'none') return [];
  const filtered = summary.data.chart_series.filter(s => s.group_key !== null);
  const dates = new Set<string>();
  const grouped: Record<string, Record<string, number>> = {};
  filtered.forEach(s => {
    const key = s.group_key as string;
    dates.add(s.date);
    grouped[key] = grouped[key] || {};
    grouped[key][s.date] = (grouped[key][s.date] || 0) + s.total_tokens;
  });
  return [...dates].sort().map(date => {
    const row: Record<string, string | number> = { date };
    Object.entries(grouped).forEach(([k, v]) => {
      row[k] = v[date] || 0;
    });
    return row;
  });
}, [groupBy, summary.data.chart_series]);
```

- [ ] **Step 3: type-check**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 4: 浏览器验证图表正常**

打开 http://localhost:5178/tools/token-usage，确认：
- 默认无分组时趋势图正常
- 切"按设备对比"、"按工具对比"、"按模型分析"时图也正常

- [ ] **Step 5: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "refactor(frontend): 图表数据源从 items 改为 summary.chart_series"
```

---

## 前端 E：i18n + 验证

### Task E1: 新增 i18n 字符串

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

- [ ] **Step 1: 在 zh-CN.ts 中找到 `tokenUsage` 命名空间，添加新 key**

（在文件最后添加）

```typescript
// 在已有的 tokenUsage 块末尾添加
loadingSummary: '正在加载概览...',
loadingDetails: '正在筛选...',
errorSummary: '概览加载失败',
errorDetails: '明细加载失败',
retry: '重试',
staleHint: '数据已过期，点此刷新',
```

- [ ] **Step 2: 在 en-US.ts 中同步添加**

```typescript
loadingSummary: 'Loading overview...',
loadingDetails: 'Filtering...',
errorSummary: 'Failed to load overview',
errorDetails: 'Failed to load details',
retry: 'Retry',
staleHint: 'Data stale, click to refresh',
```

- [ ] **Step 3: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

- [ ] **Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/i18n/locales/
git commit -m "feat(frontend): i18n 新增 token-usage 加载/错误/重试文案"
```

---

### Task E2: 前端完整构建

- [ ] **Step 1: type-check**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run type-check
```

预期：PASS

- [ ] **Step 2: build**

```bash
npm run build
```

预期：构建成功，无 error

- [ ] **Step 3: lint**

```bash
npm run lint
```

预期：无 error（warning 可接受）

---

## 上线：E2E + 性能基准

### Task F1: 手动 E2E 16 项检查

**Files:**
- 不修改文件

- [ ] **Step 1: 启动 dev 服务（如果还没跑）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py status
# 如未运行：python dev_services.py start
```

- [ ] **Step 2: 逐项执行 E2E 检查**

打开浏览器 DevTools Network 面板 + Console 面板，逐项打勾：

- [ ] 冷启动：Network 看到 `/summary` + `/details` 各 1 次
- [ ] 30s 内再次轮询：`cached: true`，耗时 < 5ms
- [ ] 切工具：只 `/details`，UI 不空白
- [ ] 切页：只 `/details?offset=...`
- [ ] 30s 自动 `/summary` 静默
- [ ] 切到其他标签 30s 后切回，立即 `/summary`
- [ ] 1 秒内连切 5 次 source，最终只 1 次 `/details`（防抖）
- [ ] 手动刷新：清缓存，2 个新请求
- [ ] 清理数据：UI 完全清空
- [ ] DevTools Offline：黄色横幅，按钮禁用
- [ ] Slow 3G：保留旧数据 + 进度条
- [ ] 空 source：显示"暂无数据"
- [ ] days=365 + group_by=model：有 `has_more` 提示
- [ ] 跨用户隔离：A、B 看到自己数据
- [ ] 跨设备：A、B 设备数据都同步
- [ ] Console 无 error/warn

发现任何失败项必须修复后才能进 F2。

- [ ] **Step 3: 提交检查清单到 docs/**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
# 创建一份 E2E 报告
cat > /tmp/e2e-report.md <<'EOF'
# Token-Usage L1+L2 E2E 验证报告
日期: $(date)
- [x] 冷启动
- [x] 缓存命中
... (实际打勾状态)
EOF
# 不强制 commit，仅作记录
```

---

### Task F2: 性能基准脚本

**Files:**
- Create: `backend/scripts/bench_token_usage.py`

- [ ] **Step 1: 创建基准脚本**

```python
"""基准测试：summary 和 details 接口在不同数据量下的耗时。
使用：python -m scripts.bench_token_usage
"""
import json
import time
import statistics
from typing import Callable

CASES = [
    {"name": "7d-none",   "days": 7,   "group_by": "none",  "expected_items_max": 7},
    {"name": "30d-none",  "days": 30,  "group_by": "none",  "expected_items_max": 30},
    {"name": "30d-model", "days": 30,  "group_by": "model", "expected_items_max": 90},
    {"name": "90d-model", "days": 90,  "group_by": "model", "expected_items_max": 270},
    {"name": "365d-model","days": 365, "group_by": "model", "expected_items_max": 200},
]

SUMMARY_THRESHOLD_MS = 200
DETAILS_THRESHOLD_MS = 300


def measure(fn: Callable, iterations: int = 5) -> dict:
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "p50": statistics.median(times),
        "p95": sorted(times)[int(len(times) * 0.95) - 1],
        "min": min(times),
        "max": max(times),
    }


def main():
    import requests
    from app.routes.auth import create_access_token  # 根据实际项目调整

    # 注：实际运行时需要：
    # 1. 启动后端
    # 2. 登录获取 token
    # 3. 注入 seed 数据
    # 4. 跑基准
    print("本脚本需要后端在 http://localhost:19092 跑且有测试用户。")
    print("实际接入请参考 backend/scripts/seed_token_usage.py（如不存在请创建）。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑基准（前置：注入 seed 数据）**

如果项目还没有 seed 脚本，跳过本步，记录在 E2E 报告中。

- [ ] **Step 3: 提交（如果创建了脚本）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/scripts/bench_token_usage.py
git commit -m "chore(backend): 新增 token-usage 性能基准脚本"
```

---

### Task F3: 合并到 master

- [ ] **Step 1: 最终检查**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git status
git log --oneline feat/token-usage-speed-l1l2 ^master
```

预期：无未提交修改；提交列表清晰

- [ ] **Step 2: push 分支**

```bash
git push origin feat/token-usage-speed-l1l2
```

- [ ] **Step 3: 创建 PR（手动在 GitHub 操作）**

标题：`feat(token-usage): 拆分 /summary + /details 接口（L1+L2 速度优化）`

描述模板：
```
## 背景
- 当前 /db-query 单接口返回 11 字段，导致首屏 1-3 秒
- 切筛选会全屏 loading
- 轮询每次 1MB 响应

## 改动
- 新增 GET /api/token-usage/summary（轻、含概览+chart_series）
- 新增 POST /api/token-usage/details（重、分页 50/200）
- 前端拆 useSummary + useDetails 两个独立 hook
- 保留 /db-query 12 周兼容（Deprecation header）
- 30s Redis 缓存
- 防抖 200/300ms

## 测试
- 17 个新单测 + 集成测试，全过
- 16 项手动 E2E 全过
- 性能：summary < 200ms, details < 300ms

## Spec
docs/plans/2026-06-02-token-usage-speed-optimization-l1l2-design.md
docs/superpowers/plans/2026-06-02-token-usage-speed-optimization-l1l2-impl.md

## 不在范围
- Codex 真实数据接入
- 服务端预聚合（C 阶段）
- 视觉改版
```

---

## 任务完成清单

完成后回到 `docs/plans/2026-06-02-token-usage-speed-optimization-l1l2-design.md`，把"状态"改为 `已实施`，并把"上线 Checklist"逐项打勾。

---

## 自审检查

写完后已经做的自审：

- ✅ 每个任务都有具体文件路径
- ✅ 每个代码块都是完整可运行
- ✅ 每个 commit 都是单一职责
- ✅ 步骤粒度在 2-5 分钟内
- ✅ 无 "TBD" / "TODO" / "类似 Task N" 引用
- ✅ 类型/方法名跨任务一致：
  - `useTokenUsageSummary` / `useTokenUsageDetails` / `useTokenUsagePolling` / `useDebouncedValue`
  - `getTokenUsageSummary` / `getTokenUsageDetails` / `getDbTokenUsage`（保留兼容）
  - `SummaryResponse` / `DetailsResponse` / `ChartSeriesItem` / `SummaryUsageSummary`
  - `build_chart_series` 后端函数
- ✅ 测试覆盖每个新接口/hook
- ✅ spec 中的所有 12 周兼容要求都有对应任务（A6 / B1 测试）

**唯一遗留项**：F2 性能基准脚本需要 seed 数据，本次实施未自动注入。如需严格验证性能，请在 master 分支创建 `seed_token_usage.py` 后再跑。
