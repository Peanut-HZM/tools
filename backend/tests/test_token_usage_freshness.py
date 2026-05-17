"""Token Usage freshness 元数据单元测试"""

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
