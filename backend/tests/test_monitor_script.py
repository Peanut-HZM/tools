"""
采集脚本解析测试 - 覆盖正常/异常/字段缺失场景
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.monitor.script import parse_script_output, BASH_SCRIPT


def _wrap(data: dict) -> str:
    import json
    return f"MONITOR_DATA_BEGIN{json.dumps(data)}MONITOR_DATA_END"


def test_parse_valid_output():
    raw = _wrap({
        "cpu_percent": 12.5, "cpu_per_core": [10.0, 15.0],
        "load_avg": [0.5, 0.4, 0.3],
        "mem_total": 8000000000, "mem_used": 4000000000, "mem_percent": 50.0,
        "swap_total": 2000000000, "swap_used": 0, "swap_percent": 0.0,
        "disk_total": 100000000000, "disk_used": 40000000000, "disk_percent": 40.0,
        "net_recv_rate": 1024.0, "net_sent_rate": 2048.0,
        "disk_read_rate": 512.0, "disk_write_rate": 256.0,
        "process_count": 128, "uptime_seconds": 3600,
    })
    result = parse_script_output(raw)
    assert result is not None
    assert result["cpu_percent"] == 12.5
    assert result["load_avg"] == [0.5, 0.4, 0.3]
    assert result["process_count"] == 128


def test_parse_with_noise_around_markers():
    """脚本错误输出混入时只取标记中间内容"""
    data = _wrap({
        "cpu_percent": 5.0, "cpu_per_core": [4.0, 6.0],
        "load_avg": [0.1, 0.1, 0.1],
        "mem_total": 8000000000, "mem_used": 2000000000, "mem_percent": 10.0,
        "swap_total": 2000000000, "swap_used": 0, "swap_percent": 0.0,
        "disk_total": 100000000000, "disk_used": 10000000000, "disk_percent": 10.0,
        "net_recv_rate": 100.0, "net_sent_rate": 200.0,
        "disk_read_rate": 50.0, "disk_write_rate": 25.0,
        "process_count": 100, "uptime_seconds": 1800,
    })
    raw = f"some warning line\n{data}\ntrailing error"
    result = parse_script_output(raw)
    assert result["cpu_percent"] == 5.0


def test_parse_missing_marker_returns_none():
    assert parse_script_output("no markers here") is None


def test_parse_invalid_json_returns_none():
    raw = "MONITOR_DATA_BEGIN{not json MONITOR_DATA_END"
    assert parse_script_output(raw) is None


def test_parse_missing_required_key_returns_none():
    raw = _wrap({"cpu_percent": 5.0})  # 缺 mem_percent 等
    assert parse_script_output(raw) is None


def test_parse_clamps_percent_values():
    raw = _wrap({
        "cpu_percent": 150.0, "cpu_per_core": [-5.0],
        "load_avg": [1, 2, 3], "mem_total": 1, "mem_used": 1, "mem_percent": 99,
        "swap_total": 0, "swap_used": 0, "swap_percent": 0,
        "disk_total": 1, "disk_used": 0, "disk_percent": 200,
        "net_recv_rate": 1, "net_sent_rate": 1, "disk_read_rate": 1, "disk_write_rate": 1,
        "process_count": 1, "uptime_seconds": 1,
    })
    result = parse_script_output(raw)
    assert result["cpu_percent"] == 100.0
    assert result["cpu_per_core"] == [0.0]
    assert result["disk_percent"] == 100.0


def test_script_contains_markers_and_pure_bash():
    assert "MONITOR_DATA_BEGIN" in BASH_SCRIPT
    assert "MONITOR_DATA_END" in BASH_SCRIPT
    # 不依赖非标准工具
    for tool in ("vmstat", "iostat", "python", "top", "sar"):
        assert tool not in BASH_SCRIPT
