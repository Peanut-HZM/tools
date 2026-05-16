# Token Usage Dimensions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build device, tool, and model dimensional statistics for `/tools/token-usage`, with backend filtering/sorting, compatible schema changes, and richer frontend controls.

**Architecture:** Keep `token_usage_records` as the fact table, add nullable display/normalization fields, and compute all dimensional summaries from the database using shared filters. Extend the existing `/api/token-usage/query` response so the frontend can render trend data, dimension cards, filter options, and detail rows from one request.

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / Alembic / pytest, TypeScript / React 18 / Vite / Recharts.

---

## Scope Notes

The design spec is `docs/superpowers/specs/2026-05-16-token-usage-dimensions-design.md`.

This plan intentionally does not implement Codex collection. Codex is represented only by stable `tool_id/tool_name/source` mapping support, and it must not appear in totals until real records exist.

Current working tree may already contain uncommitted Token Usage fixes. Do not revert them. Read the files before editing and work with the current state.

## File Map

- Modify: `backend/app/models/token_usage_models.py`
  - Add nullable tool/device/model display fields and the query index.
- Create: `backend/alembic/versions/20260516_token_usage_dimensions.py`
  - Add nullable columns and index; provide downgrade.
- Modify: `backend/app/services/token_usage_sync_service.py`
  - Populate tool and display fields during sync/upsert.
- Modify: `backend/app/routes/token_usage.py`
  - Extend query request/response types, add dimension/filter helpers, support `group_by=tool`, filters, and sorting.
- Modify: `backend/app/services/token_usage_cache.py`
  - Add new query parameters to cache key helpers.
- Create: `backend/tests/test_token_usage_dimensions.py`
  - Cover mapping, fallback, dimension summaries, filter options, and sorting.
- Modify: `frontend/src/api/tokenUsageApi.ts`
  - Add request/response types for tool/model filters, sorting, dimensions, and filter options.
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`
  - Add filters, dimension cards, click-to-filter, backend sorting, and new detail columns.
- Test existing: `backend/tests/test_token_usage_freshness.py`
  - Ensure previous freshness/model-summary behavior stays green.

---

### Task 1: Add Backend Dimension Mapping Tests

**Files:**
- Create: `backend/tests/test_token_usage_dimensions.py`
- Modify: `backend/app/routes/token_usage.py`

- [ ] **Step 1: Create failing tests for tool mapping, display fallback, and dimension shares**

Create `backend/tests/test_token_usage_dimensions.py` with:

```python
"""Token Usage 多维统计单元测试。"""

from datetime import date, datetime
from types import SimpleNamespace

from app.routes.token_usage import (
    _build_dimension_summary,
    _display_model_name,
    _map_source_to_tool,
    _normalize_record_dimensions,
    _sort_usage_items,
)


def test_map_source_to_tool_known_sources():
    assert _map_source_to_tool("claude") == {
        "tool_id": "claude-code",
        "tool_name": "Claude Code",
    }
    assert _map_source_to_tool("opencode") == {
        "tool_id": "opencode",
        "tool_name": "OpenCode",
    }


def test_map_source_to_tool_unknown_source_uses_raw_value():
    assert _map_source_to_tool("my-tool") == {
        "tool_id": "my-tool",
        "tool_name": "my-tool",
    }


def test_normalize_record_dimensions_falls_back_from_source_and_device_registry():
    row = SimpleNamespace(
        source="claude",
        tool_id=None,
        tool_name=None,
        device_id="device-1",
        device_name=None,
        model="_total",
        model_display_name=None,
    )
    device_names = {"device-1": "Workstation"}

    normalized = _normalize_record_dimensions(row, device_names)

    assert normalized["tool_id"] == "claude-code"
    assert normalized["tool_name"] == "Claude Code"
    assert normalized["device_name"] == "Workstation"
    assert normalized["model_display_name"] == "Claude Code total"


def test_display_model_name_uses_tool_name_for_total_rows():
    assert _display_model_name("_total", "OpenCode") == "OpenCode total"
    assert _display_model_name("qwen3.6-plus", "Claude Code") == "qwen3.6-plus"


def test_build_dimension_summary_computes_token_and_cost_share():
    rows = [
        SimpleNamespace(
            key="claude-code",
            label="Claude Code",
            source="claude",
            tool_id="claude-code",
            device_id=None,
            model=None,
            input_tokens=10,
            output_tokens=5,
            cache_creation_tokens=2,
            cache_read_tokens=3,
            total_tokens=20,
            total_cost=2.0,
            records_count=2,
            last_used_at=datetime(2026, 5, 16, 12, 0, 0),
        ),
        SimpleNamespace(
            key="opencode",
            label="OpenCode",
            source="opencode",
            tool_id="opencode",
            device_id=None,
            model=None,
            input_tokens=30,
            output_tokens=10,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            total_tokens=40,
            total_cost=1.0,
            records_count=1,
            last_used_at=datetime(2026, 5, 16, 13, 0, 0),
        ),
    ]

    summary = _build_dimension_summary(
        rows,
        dimension="tool",
        total_tokens=60,
        total_cost=3.0,
    )

    assert summary[0]["key"] == "claude-code"
    assert summary[0]["token_share"] == 33.3333
    assert summary[0]["cost_share"] == 66.6667
    assert summary[1]["key"] == "opencode"
    assert summary[1]["token_share"] == 66.6667
    assert summary[1]["cost_share"] == 33.3333


def test_sort_usage_items_orders_complete_result_set():
    items = [
        SimpleNamespace(date="2026-05-15", total_tokens=10, total_cost=5.0),
        SimpleNamespace(date="2026-05-16", total_tokens=30, total_cost=1.0),
        SimpleNamespace(date="2026-05-14", total_tokens=20, total_cost=3.0),
    ]

    sorted_items = _sort_usage_items(items, sort_by="total_tokens", sort_order="desc")

    assert [item.total_tokens for item in sorted_items] == [30, 20, 10]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py -v
```

Expected: FAIL with import errors for `_build_dimension_summary`, `_map_source_to_tool`, `_normalize_record_dimensions`, and `_sort_usage_items`.

- [ ] **Step 3: Add minimal helper implementations**

In `backend/app/routes/token_usage.py`, add these helpers near the existing freshness/model helper section:

```python
def _map_source_to_tool(source: str) -> dict:
    source_value = source or "unknown"
    mapping = {
        "claude": {"tool_id": "claude-code", "tool_name": "Claude Code"},
        "opencode": {"tool_id": "opencode", "tool_name": "OpenCode"},
        "codex": {"tool_id": "codex", "tool_name": "Codex"},
    }
    return mapping.get(
        source_value,
        {"tool_id": source_value, "tool_name": source_value},
    )


def _display_model_name(model: str, tool_name: str = "Unknown Tool") -> str:
    if model == "_total":
        return f"{tool_name} total"
    if not model:
        return "未知模型"
    return model


def _normalize_record_dimensions(row, device_names: dict[str, str]) -> dict:
    tool = _map_source_to_tool(getattr(row, "source", None))
    tool_id = getattr(row, "tool_id", None) or tool["tool_id"]
    tool_name = getattr(row, "tool_name", None) or tool["tool_name"]
    device_id = getattr(row, "device_id", None) or "unknown"
    device_name = (
        getattr(row, "device_name", None)
        or device_names.get(device_id)
        or device_id
    )
    model = getattr(row, "model", None) or "unknown"
    model_display_name = getattr(row, "model_display_name", None) or _display_model_name(
        model,
        tool_name,
    )
    return {
        "source": getattr(row, "source", None) or "unknown",
        "tool_id": tool_id,
        "tool_name": tool_name,
        "device_id": device_id,
        "device_name": device_name,
        "model": model,
        "model_display_name": model_display_name,
    }


def _build_dimension_summary(
    rows,
    dimension: str,
    total_tokens: int,
    total_cost: float,
) -> list[dict]:
    result = []
    for row in rows:
        row_tokens = int(getattr(row, "total_tokens", 0) or 0)
        row_cost = float(getattr(row, "total_cost", 0) or 0)
        result.append(
            {
                "dimension": dimension,
                "key": getattr(row, "key", "") or "",
                "label": getattr(row, "label", "") or "",
                "device_id": getattr(row, "device_id", None),
                "tool_id": getattr(row, "tool_id", None),
                "source": getattr(row, "source", None),
                "model": getattr(row, "model", None),
                "input_tokens": int(getattr(row, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(row, "output_tokens", 0) or 0),
                "cache_creation_tokens": int(
                    getattr(row, "cache_creation_tokens", 0) or 0
                ),
                "cache_read_tokens": int(getattr(row, "cache_read_tokens", 0) or 0),
                "total_tokens": row_tokens,
                "total_cost": round(row_cost, 4),
                "token_share": round(
                    (row_tokens / total_tokens * 100) if total_tokens else 0,
                    4,
                ),
                "cost_share": round(
                    (row_cost / total_cost * 100) if total_cost else 0,
                    4,
                ),
                "records_count": int(getattr(row, "records_count", 0) or 0),
                "last_used_at": _to_iso(getattr(row, "last_used_at", None)),
            }
        )
    return result


def _sort_usage_items(items, sort_by: str, sort_order: str):
    allowed = {
        "date",
        "total_tokens",
        "total_cost",
        "input_tokens",
        "output_tokens",
        "cache_tokens",
    }
    selected = sort_by if sort_by in allowed else "date"
    reverse = sort_order != "asc"

    def sort_value(item):
        if selected == "cache_tokens":
            return (item.cache_creation_tokens or 0) + (item.cache_read_tokens or 0)
        return getattr(item, selected, None) or 0

    return sorted(items, key=sort_value, reverse=reverse)
```

If `_display_model_name` already exists, update it in place instead of creating a duplicate.

- [ ] **Step 4: Run tests to verify helper behavior passes**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py -v
```

Expected: PASS for all tests in this file.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_token_usage_dimensions.py backend/app/routes/token_usage.py
git commit -m "test: cover token usage dimension helpers"
```

---

### Task 2: Add Nullable Dimension Fields and Migration

**Files:**
- Modify: `backend/app/models/token_usage_models.py`
- Create: `backend/alembic/versions/20260516_token_usage_dimensions.py`
- Test: `backend/tests/test_token_usage_dimensions.py`

- [ ] **Step 1: Extend the SQLAlchemy model**

In `backend/app/models/token_usage_models.py`, add these nullable columns after `source` and `model`:

```python
    source = Column(String(32), nullable=False)  # 'claude' | 'opencode'
    source_raw = Column(String(128), nullable=True)
    tool_id = Column(String(64), nullable=True, index=True)
    tool_name = Column(String(128), nullable=True)
    model = Column(String(128), nullable=False)
    model_display_name = Column(String(128), nullable=True)
    device_name = Column(String(128), nullable=True)
```

Update `__table_args__` to include:

```python
        Index(
            "idx_token_usage_dimensions",
            "user_id",
            "record_date",
            "tool_id",
            "device_id",
            "model",
        ),
```

- [ ] **Step 2: Create the Alembic migration**

Create `backend/alembic/versions/20260516_token_usage_dimensions.py`:

```python
"""add token usage dimension columns

Revision ID: 20260516_token_usage_dimensions
Revises: 6a4a752ab3ad
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_token_usage_dimensions"
down_revision = "6a4a752ab3ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "token_usage_records",
        sa.Column("source_raw", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("tool_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("tool_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("model_display_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("device_name", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "idx_token_usage_dimensions",
        "token_usage_records",
        ["user_id", "record_date", "tool_id", "device_id", "model"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_token_usage_dimensions", table_name="token_usage_records")
    op.drop_column("token_usage_records", "device_name")
    op.drop_column("token_usage_records", "model_display_name")
    op.drop_column("token_usage_records", "tool_name")
    op.drop_column("token_usage_records", "tool_id")
    op.drop_column("token_usage_records", "source_raw")
```

- [ ] **Step 3: Compile the model and migration**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m py_compile app\models\token_usage_models.py alembic\versions\20260516_token_usage_dimensions.py
```

Expected: command exits with code 0.

- [ ] **Step 4: Run dimension helper tests**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/token_usage_models.py backend/alembic/versions/20260516_token_usage_dimensions.py
git commit -m "feat: add token usage dimension fields"
```

---

### Task 3: Populate Dimension Fields During Sync

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py`
- Test: `backend/tests/test_token_usage_dimensions.py`

- [ ] **Step 1: Add a sync payload test**

Append to `backend/tests/test_token_usage_dimensions.py`:

```python
from app.services.token_usage_sync_service import _build_dimension_fields


def test_build_dimension_fields_for_sync_payload():
    fields = _build_dimension_fields(
        source="claude",
        device_name="Workstation",
        model="_total",
    )

    assert fields == {
        "source_raw": "claude",
        "tool_id": "claude-code",
        "tool_name": "Claude Code",
        "device_name": "Workstation",
        "model_display_name": "Claude Code total",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py::test_build_dimension_fields_for_sync_payload -v
```

Expected: FAIL because `_build_dimension_fields` does not exist.

- [ ] **Step 3: Implement sync dimension helper**

In `backend/app/services/token_usage_sync_service.py`, add imports and helper:

```python
from app.routes.token_usage import _display_model_name, _map_source_to_tool
```

```python
def _build_dimension_fields(source: str, device_name: str, model: str) -> dict:
    tool = _map_source_to_tool(source)
    return {
        "source_raw": source,
        "tool_id": tool["tool_id"],
        "tool_name": tool["tool_name"],
        "device_name": device_name,
        "model_display_name": _display_model_name(model, tool["tool_name"]),
    }
```

- [ ] **Step 4: Populate fields in `_upsert_records`**

Change `_upsert_records` signature:

```python
def _upsert_records(
    db,
    user_id: str,
    device_id: str,
    source: str,
    records: list[dict],
    device_name: str,
) -> int:
```

Before create/update logic inside the loop:

```python
        dimension_fields = _build_dimension_fields(
            source=source,
            device_name=device_name,
            model=rec["model"],
        )
```

When adding `TokenUsageRecord`, include:

```python
                source_raw=dimension_fields["source_raw"],
                tool_id=dimension_fields["tool_id"],
                tool_name=dimension_fields["tool_name"],
                device_name=dimension_fields["device_name"],
                model_display_name=dimension_fields["model_display_name"],
```

When updating an existing record, after token/cost assignments also assign:

```python
                existing.source_raw = dimension_fields["source_raw"]
                existing.tool_id = dimension_fields["tool_id"]
                existing.tool_name = dimension_fields["tool_name"]
                existing.device_name = dimension_fields["device_name"]
                existing.model_display_name = dimension_fields["model_display_name"]
```

In `sync_token_usage`, compute one device display name:

```python
    device_name = get_device_display_name()
```

Use it for `DeviceRegistry.default_display_name` and pass it to `_upsert_records`:

```python
                count = _upsert_records(
                    db,
                    user_id,
                    device_id,
                    source_name,
                    parsed,
                    device_name,
                )
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py -v
```

Expected: PASS.

- [ ] **Step 6: Compile sync service**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m py_compile app\services\token_usage_sync_service.py
```

Expected: command exits with code 0.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/token_usage_sync_service.py backend/tests/test_token_usage_dimensions.py
git commit -m "feat: populate token usage dimensions on sync"
```

---

### Task 4: Extend Backend Query Contract, Filters, Sorting, and Cache Key

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `backend/app/services/token_usage_cache.py`
- Test: `backend/tests/test_token_usage_dimensions.py`
- Test existing: `backend/tests/test_token_usage_freshness.py`

- [ ] **Step 1: Add request and response models**

In `backend/app/routes/token_usage.py`, update `DbQueryRequest`:

```python
class DbQueryRequest(BaseModel):
    type: str = Field(default="daily", description="daily | weekly | monthly")
    days: int = Field(default=30, ge=1, le=365, description="最近 N 天")
    group_by: str = Field(default="none", description="none | device | tool | model")
    source: str = Field(default="all", description="claude | opencode | all")
    device_id: Optional[str] = Field(
        default=None, description="筛选特定设备，不传则查全部"
    )
    tool_id: Optional[str] = Field(default=None, description="筛选工具")
    model: Optional[str] = Field(default=None, description="筛选模型")
    sort_by: str = Field(default="date", description="date | total_tokens | total_cost")
    sort_order: str = Field(default="desc", description="asc | desc")
```

Add models near `ModelSummaryItem`:

```python
class DimensionSummaryItem(BaseModel):
    dimension: str
    key: str
    label: str
    device_id: Optional[str] = None
    tool_id: Optional[str] = None
    source: Optional[str] = None
    model: Optional[str] = None
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    token_share: float
    cost_share: float
    records_count: int
    last_used_at: Optional[str] = None


class FilterToolOption(BaseModel):
    tool_id: str
    tool_name: str
    records_count: int


class FilterDeviceOption(BaseModel):
    device_id: str
    device_name: str
    records_count: int


class FilterModelOption(BaseModel):
    tool_id: str
    source: str
    model: str
    model_display_name: str
    records_count: int


class DimensionSummaries(BaseModel):
    devices: list[DimensionSummaryItem] = Field(default_factory=list)
    tools: list[DimensionSummaryItem] = Field(default_factory=list)
    models: list[DimensionSummaryItem] = Field(default_factory=list)


class FilterOptions(BaseModel):
    tools: list[FilterToolOption] = Field(default_factory=list)
    devices: list[FilterDeviceOption] = Field(default_factory=list)
    models: list[FilterModelOption] = Field(default_factory=list)
```

Extend `DbUsageResponse`:

```python
    dimension_summaries: DimensionSummaries = Field(default_factory=DimensionSummaries)
    filter_options: FilterOptions = Field(default_factory=FilterOptions)
```

- [ ] **Step 2: Add filters to the shared record filter helper**

Update `_build_record_filters`:

```python
def _build_record_filters(user_id: str, req, since_date: Optional[datetime] = None) -> list:
    filters = [TokenUsageRecord.user_id == user_id]
    if since_date:
        filters.append(TokenUsageRecord.record_date >= since_date.date())
    if getattr(req, "source", "all") != "all":
        filters.append(TokenUsageRecord.source == req.source)
    if getattr(req, "device_id", None):
        filters.append(TokenUsageRecord.device_id == req.device_id)
    if getattr(req, "tool_id", None):
        tool_id = req.tool_id
        mapped_sources = [
            source
            for source in ("claude", "opencode", "codex")
            if _map_source_to_tool(source)["tool_id"] == tool_id
        ]
        filters.append(
            (TokenUsageRecord.tool_id == tool_id)
            | (
                TokenUsageRecord.tool_id.is_(None)
                & TokenUsageRecord.source.in_(mapped_sources or [tool_id])
            )
        )
    if getattr(req, "model", None):
        filters.append(TokenUsageRecord.model == req.model)
    return filters
```

If SQLAlchemy complains about `|`, import `or_` and `and_` from SQLAlchemy and express the same logic with `or_(...)` and `and_(...)`.

- [ ] **Step 3: Implement dimension queries**

Add helpers:

```python
def _device_name_map(db, user_id: str) -> dict[str, str]:
    rows = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()
    return {
        row.device_id: row.display_name or row.default_display_name or row.device_id
        for row in rows
    }
```

```python
def _execute_dimension_rows(db, user_id: str, req, since_date: datetime, dimension: str):
    filters = _build_record_filters(user_id, req, since_date)
    updated_at = func.max(
        func.coalesce(TokenUsageRecord.updated_at, TokenUsageRecord.created_at)
    ).label("last_used_at")

    if dimension == "device":
        return (
            db.query(
                TokenUsageRecord.device_id.label("key"),
                func.coalesce(TokenUsageRecord.device_name, TokenUsageRecord.device_id).label("label"),
                TokenUsageRecord.device_id.label("device_id"),
                func.cast(None, String).label("tool_id"),
                func.cast(None, String).label("source"),
                func.cast(None, String).label("model"),
                func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
                func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
                func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
                func.count(TokenUsageRecord.id).label("records_count"),
                updated_at,
            )
            .filter(*filters)
            .group_by(TokenUsageRecord.device_id, TokenUsageRecord.device_name)
            .all()
        )

    if dimension == "tool":
        tool_expr = func.coalesce(TokenUsageRecord.tool_id, TokenUsageRecord.source)
        label_expr = func.coalesce(TokenUsageRecord.tool_name, TokenUsageRecord.source)
        return (
            db.query(
                tool_expr.label("key"),
                label_expr.label("label"),
                func.cast(None, String).label("device_id"),
                tool_expr.label("tool_id"),
                TokenUsageRecord.source.label("source"),
                func.cast(None, String).label("model"),
                func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
                func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
                func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
                func.count(TokenUsageRecord.id).label("records_count"),
                updated_at,
            )
            .filter(*filters)
            .group_by(tool_expr, label_expr, TokenUsageRecord.source)
            .all()
        )

    tool_expr = func.coalesce(TokenUsageRecord.tool_id, TokenUsageRecord.source)
    model_label = func.coalesce(TokenUsageRecord.model_display_name, TokenUsageRecord.model)
    return (
        db.query(
            (tool_expr + ":" + TokenUsageRecord.model).label("key"),
            model_label.label("label"),
            func.cast(None, String).label("device_id"),
            tool_expr.label("tool_id"),
            TokenUsageRecord.source.label("source"),
            TokenUsageRecord.model.label("model"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
            func.count(TokenUsageRecord.id).label("records_count"),
            updated_at,
        )
        .filter(*filters)
        .group_by(tool_expr, TokenUsageRecord.source, TokenUsageRecord.model, model_label)
        .all()
    )
```

If the string concatenation expression fails on the configured database, replace the model key in Python after fetching rows by grouping on `tool_expr/source/model/model_label` and creating a `SimpleNamespace`.

- [ ] **Step 4: Implement filter options**

Add helper:

```python
def _build_filter_options(db, user_id: str, req, since_date: datetime) -> dict:
    device_names = _device_name_map(db, user_id)
    base_filters = _build_record_filters(user_id, req, since_date)

    tool_rows = _execute_dimension_rows(db, user_id, req, since_date, "tool")
    device_rows = _execute_dimension_rows(db, user_id, req, since_date, "device")
    model_rows = _execute_dimension_rows(db, user_id, req, since_date, "model")

    return {
        "tools": [
            {
                "tool_id": row.key,
                "tool_name": row.label,
                "records_count": int(row.records_count or 0),
            }
            for row in tool_rows
        ],
        "devices": [
            {
                "device_id": row.device_id,
                "device_name": device_names.get(row.device_id, row.label),
                "records_count": int(row.records_count or 0),
            }
            for row in device_rows
        ],
        "models": [
            {
                "tool_id": row.tool_id,
                "source": row.source,
                "model": row.model,
                "model_display_name": row.label,
                "records_count": int(row.records_count or 0),
            }
            for row in model_rows
        ],
    }
```

- [ ] **Step 5: Add `group_by=tool` and sorting to `_execute_db_query`**

In `_execute_db_query`, add a `tool` branch before the model branch:

```python
    elif req.group_by == "tool":
        tool_expr = func.coalesce(TokenUsageRecord.tool_id, TokenUsageRecord.source)
        results = (
            db.query(
                TokenUsageRecord.record_date.label("date"),
                tool_expr.label("group_key"),
                func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
                func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
                func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
            )
            .filter(*base_filter)
            .group_by(TokenUsageRecord.record_date, tool_expr)
            .order_by(TokenUsageRecord.record_date)
            .all()
        )
```

After constructing `items`, return sorted items:

```python
    return _sort_usage_items(items, req.sort_by, req.sort_order)
```

- [ ] **Step 6: Include dimensions in query response and cache payload**

In both cached and DB response paths, populate:

```python
dimension_rows = {
    "devices": _build_dimension_summary(
        _execute_dimension_rows(db, user_id, req, since_date, "device"),
        "device",
        summary.total_tokens,
        summary.total_cost,
    ),
    "tools": _build_dimension_summary(
        _execute_dimension_rows(db, user_id, req, since_date, "tool"),
        "tool",
        summary.total_tokens,
        summary.total_cost,
    ),
    "models": _build_dimension_summary(
        _execute_dimension_rows(db, user_id, req, since_date, "model"),
        "model",
        summary.total_tokens,
        summary.total_cost,
    ),
}
filter_options = _build_filter_options(db, user_id, req, since_date)
```

Add to `cache_payload`:

```python
            "dimension_summaries": dimension_rows,
            "filter_options": filter_options,
```

Add to `DbUsageResponse` construction:

```python
            dimension_summaries=DimensionSummaries(**dimension_rows),
            filter_options=FilterOptions(**filter_options),
```

For cached responses, read these keys from cached payload. If missing, compute them from DB before returning.

- [ ] **Step 7: Extend cache key**

In `backend/app/services/token_usage_cache.py`, extend `_build_query_cache_key`, `get_query_cached_data`, `get_query_cached_payload`, and `set_query_cached_data` with:

```python
    tool_id: str = "",
    model: str = "",
    sort_by: str = "date",
    sort_order: str = "desc",
```

Include them in the key parts:

```python
        tool_id or "all-tools",
        model or "all-models",
        sort_by or "date",
        sort_order or "desc",
```

Update all call sites in `token_usage.py` to pass:

```python
        tool_id=req.tool_id or "",
        model=req.model or "",
        sort_by=req.sort_by,
        sort_order=req.sort_order,
```

- [ ] **Step 8: Run backend tests**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py tests\test_token_usage_freshness.py -v
```

Expected: PASS.

- [ ] **Step 9: Compile backend files**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m py_compile app\routes\token_usage.py app\services\token_usage_cache.py
```

Expected: command exits with code 0.

- [ ] **Step 10: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/services/token_usage_cache.py backend/tests/test_token_usage_dimensions.py backend/tests/test_token_usage_freshness.py
git commit -m "feat: add token usage dimension query API"
```

---

### Task 5: Update Frontend API Types

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`

- [ ] **Step 1: Extend frontend types**

In `frontend/src/api/tokenUsageApi.ts`, change group type:

```ts
export type TokenUsageGroupBy = 'none' | 'device' | 'tool' | 'model';
export type TokenUsageSortBy = 'date' | 'total_tokens' | 'total_cost' | 'input_tokens' | 'output_tokens' | 'cache_tokens';
export type TokenUsageSortOrder = 'asc' | 'desc';
```

Add interfaces:

```ts
export interface DimensionSummaryItem {
  dimension: 'device' | 'tool' | 'model';
  key: string;
  label: string;
  device_id?: string | null;
  tool_id?: string | null;
  source?: string | null;
  model?: string | null;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  token_share: number;
  cost_share: number;
  records_count: number;
  last_used_at?: string | null;
}

export interface DimensionSummaries {
  devices: DimensionSummaryItem[];
  tools: DimensionSummaryItem[];
  models: DimensionSummaryItem[];
}

export interface FilterOptions {
  tools: Array<{ tool_id: string; tool_name: string; records_count: number }>;
  devices: Array<{ device_id: string; device_name: string; records_count: number }>;
  models: Array<{
    tool_id: string;
    source: string;
    model: string;
    model_display_name: string;
    records_count: number;
  }>;
}
```

Extend `DbQueryParams`:

```ts
  tool_id?: string;
  model?: string;
  sort_by?: TokenUsageSortBy;
  sort_order?: TokenUsageSortOrder;
```

Extend `DbUsageResponse`:

```ts
  dimension_summaries: DimensionSummaries;
  filter_options: FilterOptions;
```

- [ ] **Step 2: Send new request parameters**

In `getDbTokenUsage`, add to JSON body:

```ts
      tool_id: params.tool_id,
      model: params.model,
      sort_by: params.sort_by || 'date',
      sort_order: params.sort_order || 'desc',
```

- [ ] **Step 3: Build frontend**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat: add token usage dimension API types"
```

---

### Task 6: Add Frontend Filters, Dimension Cards, and Backend Sorting

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Add state for tool/model filters, sort, dimensions, and options**

Update imports from `tokenUsageApi`:

```ts
  type DimensionSummaries,
  type DimensionSummaryItem,
  type FilterOptions,
  type TokenUsageSortBy,
  type TokenUsageSortOrder,
```

Add empty constants near `emptySummary`:

```ts
const emptyDimensions: DimensionSummaries = {
  devices: [],
  tools: [],
  models: [],
};

const emptyFilterOptions: FilterOptions = {
  tools: [],
  devices: [],
  models: [],
};
```

Add component state:

```ts
  const [selectedTool, setSelectedTool] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [sortBy, setSortBy] = useState<TokenUsageSortBy>('date');
  const [sortOrder, setSortOrder] = useState<TokenUsageSortOrder>('desc');
  const [dimensionSummaries, setDimensionSummaries] = useState<DimensionSummaries>(emptyDimensions);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>(emptyFilterOptions);
```

- [ ] **Step 2: Include new parameters in data fetch**

In `fetchData`, pass:

```ts
        tool_id: selectedTool || undefined,
        model: selectedModel || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
```

After response:

```ts
      setDimensionSummaries(result.dimension_summaries || emptyDimensions);
      setFilterOptions(result.filter_options || emptyFilterOptions);
```

Add dependencies:

```ts
  }, [days, groupBy, reportType, selectedDevice, selectedModel, selectedTool, sortBy, sortOrder, source]);
```

- [ ] **Step 3: Add compact filter controls**

In the existing top control area, add selects:

```tsx
<select
  value={selectedTool}
  onChange={event => {
    setSelectedTool(event.target.value);
    setSelectedModel('');
    setCurrentPage(1);
  }}
  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
>
  <option value="">全部工具</option>
  {filterOptions.tools.map(tool => (
    <option key={tool.tool_id} value={tool.tool_id}>
      {tool.tool_name}
    </option>
  ))}
</select>

<select
  value={selectedModel}
  onChange={event => {
    const value = event.target.value;
    const selected = filterOptions.models.find(model => `${model.tool_id}:${model.model}` === value);
    setSelectedTool(selected?.tool_id || selectedTool);
    setSelectedModel(selected?.model || '');
    setCurrentPage(1);
  }}
  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
>
  <option value="">全部模型</option>
  {filterOptions.models.map(model => (
    <option key={`${model.tool_id}:${model.model}`} value={`${model.tool_id}:${model.model}`}>
      {model.model_display_name}
    </option>
  ))}
</select>

<select
  value={groupBy}
  onChange={event => {
    setGroupBy(event.target.value as TokenUsageGroupBy);
    setCurrentPage(1);
  }}
  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
>
  <option value="none">按日期</option>
  <option value="device">按设备</option>
  <option value="tool">按工具</option>
  <option value="model">按模型</option>
</select>

<select
  value={sortBy}
  onChange={event => {
    setSortBy(event.target.value as TokenUsageSortBy);
    setCurrentPage(1);
  }}
  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
>
  <option value="date">日期</option>
  <option value="total_tokens">总 Token</option>
  <option value="total_cost">成本</option>
  <option value="input_tokens">输入</option>
  <option value="output_tokens">输出</option>
  <option value="cache_tokens">缓存</option>
</select>

<button
  type="button"
  onClick={() => {
    setSortOrder(order => (order === 'desc' ? 'asc' : 'desc'));
    setCurrentPage(1);
  }}
  className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
>
  {sortOrder === 'desc' ? '倒序' : '正序'}
</button>
```

If the current file already has equivalent controls, replace the existing controls instead of duplicating them.

- [ ] **Step 4: Add reusable DimensionCard component**

Add before `export default function TokenUsage()`:

```tsx
function DimensionCard({
  title,
  items,
  selectedKey,
  onSelect,
}: {
  title: string;
  items: DimensionSummaryItem[];
  selectedKey?: string;
  onSelect: (item: DimensionSummaryItem) => void;
}) {
  const visible = items.slice(0, 6);
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-medium text-white">{title}</h2>
        <span className="text-xs text-slate-500">Top {visible.length}</span>
      </div>
      {visible.length ? (
        <div className="space-y-2">
          {visible.map(item => {
            const active = selectedKey === item.key;
            const share = item.total_cost > 0 ? item.cost_share : item.token_share;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => onSelect(item)}
                className={`w-full rounded-md border px-3 py-2 text-left transition ${
                  active ? 'border-sky-500 bg-sky-500/10' : 'border-slate-800 bg-slate-950 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate text-slate-200">{item.label}</span>
                  <span className="font-mono text-slate-400">{share.toFixed(1)}%</span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-3 text-xs text-slate-500">
                  <span>{formatToken(item.total_tokens)} Token</span>
                  <span>{formatCurrency(item.total_cost)}</span>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex h-32 items-center justify-center text-sm text-slate-500">暂无维度数据</div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Render three dimension cards**

Place above the main chart grid:

```tsx
<div className="grid gap-4 lg:grid-cols-3">
  <DimensionCard
    title="设备排行"
    items={dimensionSummaries.devices}
    selectedKey={selectedDevice}
    onSelect={item => {
      setSelectedDevice(current => (current === item.device_id ? '' : item.device_id || ''));
      setCurrentPage(1);
    }}
  />
  <DimensionCard
    title="工具排行"
    items={dimensionSummaries.tools}
    selectedKey={selectedTool}
    onSelect={item => {
      const nextTool = item.tool_id || item.key;
      setSelectedTool(current => (current === nextTool ? '' : nextTool));
      setSelectedModel('');
      setCurrentPage(1);
    }}
  />
  <DimensionCard
    title="模型排行"
    items={dimensionSummaries.models}
    selectedKey={selectedModel ? `${selectedTool}:${selectedModel}` : ''}
    onSelect={item => {
      const modelKey = item.model || '';
      const toolKey = item.tool_id || '';
      const active = selectedTool === toolKey && selectedModel === modelKey;
      setSelectedTool(active ? '' : toolKey);
      setSelectedModel(active ? '' : modelKey);
      setCurrentPage(1);
    }}
  />
</div>
```

- [ ] **Step 6: Build frontend**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: add token usage dimension filters"
```

---

### Task 7: Extend Detail Table and Chart Labels

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `frontend/src/api/tokenUsageApi.ts`
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: Add display fields to `DbUsageItem`**

In `backend/app/routes/token_usage.py`, extend `DbUsageItem`:

```python
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    model: Optional[str] = None
    model_display_name: Optional[str] = None
    share: float = 0
    last_used_at: Optional[str] = None
```

When creating `DbUsageItem` in `_execute_db_query`, populate these fields from the group context:

```python
            device_id=getattr(row, "device_id", None),
            device_name=getattr(row, "device_name", None),
            tool_id=getattr(row, "tool_id", None),
            tool_name=getattr(row, "tool_name", None),
            model=getattr(row, "model", None),
            model_display_name=getattr(row, "model_display_name", None),
            last_used_at=_to_iso(getattr(row, "last_used_at", None)),
```

After summary calculation, set share for every item before response:

```python
        for item in items:
            item.share = round(
                (item.total_cost / summary.total_cost * 100)
                if summary.total_cost
                else (
                    (item.total_tokens / summary.total_tokens * 100)
                    if summary.total_tokens
                    else 0
                ),
                4,
            )
```

- [ ] **Step 2: Extend frontend item type**

In `frontend/src/api/tokenUsageApi.ts`, add to `DbUsageItem`:

```ts
  device_id?: string | null;
  device_name?: string | null;
  tool_id?: string | null;
  tool_name?: string | null;
  model?: string | null;
  model_display_name?: string | null;
  share?: number;
  last_used_at?: string | null;
```

- [ ] **Step 3: Add columns to the detail table**

In `TokenUsage.tsx`, update table header to include:

```tsx
<th className="px-4 py-3 text-left">设备</th>
<th className="px-4 py-3 text-left">工具</th>
<th className="px-4 py-3 text-left">模型</th>
```

Add cells before token columns:

```tsx
<td className="max-w-[160px] truncate px-4 py-3 text-slate-300" title={item.device_name || item.device_id || '-'}>
  {item.device_name || item.device_id || '-'}
</td>
<td className="max-w-[160px] truncate px-4 py-3 text-slate-300" title={item.tool_name || item.tool_id || '-'}>
  {item.tool_name || item.tool_id || '-'}
</td>
<td className="max-w-[180px] truncate px-4 py-3 text-slate-300" title={item.model_display_name || item.model || item.models_used.join(', ')}>
  {item.model_display_name || item.model || item.models_used.join(', ') || '-'}
</td>
```

Add share and updated cells near the end:

```tsx
<td className="px-4 py-3 text-right font-mono text-slate-400">{Number(item.share || 0).toFixed(1)}%</td>
<td className="px-4 py-3 text-right text-xs text-slate-500">{formatDateTime(item.last_used_at)}</td>
```

Update empty-state `colSpan` to match the new column count.

- [ ] **Step 4: Build frontend and compile backend**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m py_compile app\routes\token_usage.py
cd ..\frontend
npm run build
```

Expected: both commands pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/token_usage.py frontend/src/api/tokenUsageApi.ts frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: show token usage dimensions in detail table"
```

---

### Task 8: End-to-End Verification on Local Services

**Files:**
- No source changes expected unless verification finds a bug.

- [ ] **Step 1: Start or refresh services with project script**

Run:

```bash
python dev-services.py status
```

If backend is not healthy:

```bash
$env:DEBUG='false'; python dev-services.py start backend
```

If frontend is not healthy:

```bash
python dev-services.py start frontend
```

Expected:

- Backend ready at `http://127.0.0.1:19092`
- Frontend ready at `http://localhost:5178`

- [ ] **Step 2: Verify OpenAPI includes new fields**

Run:

```bash
$schema=(Invoke-RestMethod -Uri 'http://localhost:19092/openapi.json').components.schemas.DbUsageResponse
$schema.properties.PSObject.Properties.Name -join ', '
```

Expected output includes:

```text
dimension_summaries, filter_options
```

- [ ] **Step 3: Verify query response with dimensions**

Generate a short-lived local auth token, then run:

```bash
$token = .\backend\venv\Scripts\python.exe -c "from app.routes.auth import AuthService; print(AuthService().create_token('317efe5a','debug'))"
$body = '{"source":"all","type":"daily","days":30,"group_by":"tool","sort_by":"total_tokens","sort_order":"desc"}'
$res=Invoke-RestMethod -Uri 'http://localhost:19092/api/token-usage/query' -Method Post -Headers @{Authorization="Bearer $token"} -ContentType 'application/json' -Body $body
[pscustomobject]@{
  ItemsCount = @($res.items).Count
  ToolDimensions = @($res.dimension_summaries.tools).Count
  DeviceDimensions = @($res.dimension_summaries.devices).Count
  ModelDimensions = @($res.dimension_summaries.models).Count
  ToolOptions = @($res.filter_options.tools).Count
  FirstTool = $res.dimension_summaries.tools[0].label
} | ConvertTo-Json -Depth 5
```

Expected:

- `ToolDimensions` is greater than 0 when data exists.
- `DeviceDimensions` is greater than 0 when data exists.
- `ModelDimensions` is greater than 0 when data exists.
- `ToolOptions` is greater than 0 when data exists.

- [ ] **Step 4: Run backend tests**

Run:

```bash
cd backend
$env:DEBUG='true'; .\venv\Scripts\python.exe -m pytest tests\test_token_usage_dimensions.py tests\test_token_usage_freshness.py -v
```

Expected: PASS.

- [ ] **Step 5: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS. Vite may warn about chunk size; that warning is acceptable if build exits with code 0.

- [ ] **Step 6: Manual UI smoke test**

Open `http://localhost:5178/tools/token-usage` and verify:

1. Device, tool, and model cards render.
2. Tool filter changes the cards and detail rows.
3. Model filter does not merge same-name models across tools.
4. `group_by=tool` displays tool trend data.
5. Table header sorting changes request results.
6. Refresh metadata still appears in the upper-right action area.

- [ ] **Step 7: Commit verification fixes if needed**

If verification required code changes:

```bash
git add backend frontend
git commit -m "fix: stabilize token usage dimensions"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Device/tool/model stats: covered by Tasks 4, 6, and 7.
- Table field additions: covered by Tasks 2 and 7.
- Backend logic and filters: covered by Tasks 1, 3, and 4.
- Frontend dimensions, filters, sorting: covered by Tasks 5, 6, and 7.
- Cache correctness: covered by Task 4.
- Codex compatibility without fake totals: covered by mapping rules in Tasks 1 and 4.
- Verification: covered by Task 8.

Completeness scan:

- No unresolved markers or open-ended deferred instructions are used.
- Each code-changing step includes concrete code or exact replacement guidance.

Type consistency:

- Backend names: `dimension_summaries`, `filter_options`, `tool_id`, `model`, `sort_by`, `sort_order`.
- Frontend names match backend response and request fields.
- `group_by` uses `none | device | tool | model` consistently.
