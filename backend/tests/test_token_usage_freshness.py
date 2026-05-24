"""Token Usage freshness 元数据单元测试"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.routes import token_usage as token_usage_route
from app.routes.token_usage import (
    DimensionSummaries,
    FilterOptions,
    SyncMeta,
    _build_sync_meta_from_values,
    _empty_dimension_rows,
    _empty_filter_options,
    _empty_sync_meta,
    _rows_to_model_summary,
)


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


def test_rows_to_model_summary_uses_tool_name_for_total_model():
    rows = [
        SimpleNamespace(
            source="claude",
            model="_total",
            input_tokens=10,
            output_tokens=5,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            total_tokens=15,
            total_cost=0.1,
        ),
    ]

    summary = _rows_to_model_summary(rows)

    assert summary[0]["display_model"] == "Claude Code total"


def test_empty_dimension_rows_returns_dimension_summaries():
    assert isinstance(_empty_dimension_rows(), DimensionSummaries)
    assert _empty_dimension_rows().devices == []
    assert _empty_dimension_rows().tools == []
    assert _empty_dimension_rows().models == []


def test_empty_filter_options_returns_filter_options():
    assert isinstance(_empty_filter_options(), FilterOptions)
    assert _empty_filter_options().tools == []
    assert _empty_filter_options().devices == []
    assert _empty_filter_options().models == []


def test_empty_sync_meta_returns_sync_meta():
    meta = _empty_sync_meta()

    assert isinstance(meta, SyncMeta)
    assert meta.refresh_lock.locked is False
    assert meta.sources_status == []


def test_query_registers_pending_sync_without_direct_sync(monkeypatch):
    registered_users = []

    def fail_direct_sync(*args, **kwargs):
        raise AssertionError("query 不应直接执行同步")

    monkeypatch.setattr(
        token_usage_route,
        "get_current_user_id",
        lambda authorization: "user-1",
    )
    monkeypatch.setattr(
        token_usage_route,
        "register_pending_sync_user",
        registered_users.append,
    )
    monkeypatch.setattr(token_usage_route, "sync_token_usage", fail_direct_sync)
    monkeypatch.setattr(
        token_usage_route,
        "get_query_cached_payload",
        lambda **kwargs: {
            "items": [],
            "summary": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "days_count": 0,
                "avg_daily_cost": 0,
            },
            "devices": [],
            "model_summary": [],
            "dimension_summaries": _empty_dimension_rows().model_dump(),
            "filter_options": _empty_filter_options().model_dump(),
            "sync_meta": _empty_sync_meta().model_dump(),
        },
    )

    response = asyncio.run(
        token_usage_route.query_token_usage(
            token_usage_route.DbQueryRequest(),
            authorization="Bearer test-token",
        )
    )

    assert registered_users == ["user-1"]
    assert response.cached is True
    assert response.items == []


def test_query_returns_empty_response_when_database_unavailable(monkeypatch):
    def fail_session():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        token_usage_route,
        "get_current_user_id",
        lambda authorization: "user-1",
    )
    monkeypatch.setattr(
        token_usage_route,
        "register_pending_sync_user",
        lambda user_id: None,
    )
    monkeypatch.setattr(
        token_usage_route,
        "get_query_cached_payload",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(token_usage_route, "SessionLocal", fail_session)

    response = asyncio.run(
        token_usage_route.query_token_usage(
            token_usage_route.DbQueryRequest(),
            authorization="Bearer test-token",
        )
    )

    assert response.cached is False
    assert response.items == []
    assert response.summary.total_tokens == 0
    assert response.dimension_summaries.devices == []
    assert response.filter_options.devices == []
    assert response.sync_meta.refresh_lock.locked is False
