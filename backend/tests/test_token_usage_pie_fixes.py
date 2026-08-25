"""饼图修复相关后端函数的单元测试。"""
from types import SimpleNamespace

import pytest


# —— 工具函数：_normalize_record_dimensions ——

def test_device_name_from_map_overrides_record_field():
    """修复问题 1：设备名应从 device_names map 取，不再用记录里落库的旧值。"""
    from app.routes.token_usage import _normalize_record_dimensions

    row = SimpleNamespace(
        source="claude",
        tool_id=None,
        tool_name=None,
        device_id="uuid-111",
        device_name="peanut@old-host",  # 同步时落库的旧快照
        model="claude-sonnet-4-5",
        model_display_name="claude-sonnet-4-5",
    )
    device_names = {"uuid-111": "My Renamed Laptop"}

    result = _normalize_record_dimensions(row, device_names)

    assert result["device_id"] == "uuid-111"
    assert result["device_name"] == "My Renamed Laptop"
    assert result["device_name"] != "peanut@old-host"


def test_device_name_falls_back_to_device_id_when_missing():
    """device_names map 里查不到时回退到 device_id 本身。"""
    from app.routes.token_usage import _normalize_record_dimensions

    row = SimpleNamespace(
        source="opencode", tool_id=None, tool_name=None,
        device_id="uuid-orphan", device_name=None,
        model="m1", model_display_name="m1",
    )
    result = _normalize_record_dimensions(row, {})

    assert result["device_name"] == "uuid-orphan"


# —— 工具函数：_build_dimension_data 设备按显示名合并 ——

def test_dimension_data_merges_devices_with_same_display_name():
    """修复问题 2：两个不同 device_id 但显示名相同 → 合并为一个切片。"""
    from app.routes.token_usage import _build_dimension_data

    rows = [
        SimpleNamespace(
            record_date=None, source="claude", tool_id=None, tool_name=None,
            device_id="uuid-A", device_name="My-Laptop",
            model="m1", model_display_name="m1",
            input_tokens=100, output_tokens=50,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=150, total_cost=0.01,
            updated_at=None, created_at=None,
        ),
        SimpleNamespace(
            record_date=None, source="claude", tool_id=None, tool_name=None,
            device_id="uuid-B", device_name="My-Laptop",  # 同名，不同 UUID
            model="m1", model_display_name="m1",
            input_tokens=200, output_tokens=100,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=300, total_cost=0.02,
            updated_at=None, created_at=None,
        ),
    ]
    device_names = {"uuid-A": "My-Laptop", "uuid-B": "My-Laptop"}

    dimension_rows, _ = _build_dimension_data(rows, device_names)

    device_slices = dimension_rows["devices"]
    assert len(device_slices) == 1, f"期望 1 个设备切片，实际 {len(device_slices)}"
    assert device_slices[0]["label"] == "My-Laptop"
    assert device_slices[0]["total_tokens"] == 450
    assert device_slices[0]["total_cost"] == pytest.approx(0.03)


# —— 工具函数：_build_dimension_data 模型按纯 model 分组 ——

def test_dimension_data_models_grouped_by_model_only():
    """修复问题 4：模型维度按 model 单字段分组，不再带 tool_id 前缀。"""
    from app.routes.token_usage import _build_dimension_data

    rows = [
        SimpleNamespace(
            record_date=None, source="claude", tool_id="claude-code", tool_name="Claude Code",
            device_id="uuid-A", device_name="Laptop",
            model="claude-sonnet-4-5", model_display_name="claude-sonnet-4-5",
            input_tokens=100, output_tokens=50,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=150, total_cost=0.01,
            updated_at=None, created_at=None,
        ),
        SimpleNamespace(
            record_date=None, source="opencode", tool_id="opencode", tool_name="OpenCode",
            device_id="uuid-A", device_name="Laptop",
            model="claude-sonnet-4-5", model_display_name="claude-sonnet-4-5",
            input_tokens=200, output_tokens=100,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=300, total_cost=0.02,
            updated_at=None, created_at=None,
        ),
    ]
    device_names = {"uuid-A": "Laptop"}

    dimension_rows, _ = _build_dimension_data(rows, device_names)

    model_slices = dimension_rows["models"]
    assert len(model_slices) == 1, f"期望 1 个模型切片，实际 {len(model_slices)}"
    assert model_slices[0]["key"] == "claude-sonnet-4-5"
    assert model_slices[0]["label"] == "claude-sonnet-4-5"
    assert model_slices[0]["total_tokens"] == 450
    assert model_slices[0]["tool_id"] is None
    assert model_slices[0]["source"] is None
