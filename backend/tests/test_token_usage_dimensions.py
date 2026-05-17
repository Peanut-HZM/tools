"""Token Usage 多维统计单元测试。"""

from datetime import datetime
from types import SimpleNamespace

from app.routes.token_usage import (
    _build_dimension_data,
    _build_dimension_summary,
    _display_model_name,
    _map_source_to_tool,
    _normalize_record_dimensions,
    _sort_usage_items,
)
from app.services.token_usage_sync_service import _build_dimension_fields


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


def test_build_dimension_data_returns_tool_model_and_filter_options():
    records = [
        SimpleNamespace(
            source="claude",
            tool_id=None,
            tool_name=None,
            device_id="device-1",
            device_name=None,
            model="sonnet-4",
            model_display_name=None,
            input_tokens=10,
            output_tokens=5,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            total_tokens=15,
            total_cost=0.3,
            updated_at=datetime(2026, 5, 16, 12, 0, 0),
            created_at=datetime(2026, 5, 16, 11, 0, 0),
        ),
        SimpleNamespace(
            source="opencode",
            tool_id="opencode",
            tool_name="OpenCode",
            device_id="device-2",
            device_name="Notebook",
            model="qwen3.6-plus",
            model_display_name="qwen3.6-plus",
            input_tokens=20,
            output_tokens=10,
            cache_creation_tokens=2,
            cache_read_tokens=3,
            total_tokens=35,
            total_cost=0.7,
            updated_at=datetime(2026, 5, 16, 13, 0, 0),
            created_at=datetime(2026, 5, 16, 12, 0, 0),
        ),
    ]

    dimension_rows, filter_options = _build_dimension_data(
        records,
        {"device-1": "Workstation"},
    )

    assert {item["key"] for item in dimension_rows["tools"]} == {
        "claude-code",
        "opencode",
    }
    assert {item["model"] for item in dimension_rows["models"]} == {
        "sonnet-4",
        "qwen3.6-plus",
    }
    assert filter_options["tools"][0]["records_count"] == 1
    assert {item["device_name"] for item in filter_options["devices"]} == {
        "Workstation",
        "Notebook",
    }
    assert {item["model"] for item in filter_options["models"]} == {
        "sonnet-4",
        "qwen3.6-plus",
    }
