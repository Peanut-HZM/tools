"""
采集引擎测试 - mock SSH 与 psutil，验证状态流转与失败隔离
"""
import os
import sys
import asyncio
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.monitor import collector
from app.services.monitor.collector import MonitorCollector, local_metrics
from app.services.monitor.ssh_client import SSHCommandError

LOCAL_SERVER = {"id": "srv-local", "user_id": "u1", "server_type": "local", "name": "本机",
                "host": "", "port": 22, "username": "", "password": None,
                "private_key": None, "passphrase": None, "group_name": None,
                "status": "enabled", "last_error": None, "last_seen_at": None}

SSH_SERVER = {"id": "srv-1", "user_id": "u1", "server_type": "ssh", "name": "web1",
              "host": "10.0.0.1", "port": 22, "username": "root", "password": "pw",
              "private_key": None, "passphrase": None, "group_name": None,
              "status": "enabled", "last_error": None, "last_seen_at": None}


def make_metrics():
    return {"cpu_percent": 10.0, "cpu_per_core": [5.0], "load_avg": [0.1, 0.2, 0.3],
            "mem_total": 8000000000, "mem_used": 1000000000, "mem_percent": 12.5,
            "swap_total": 0, "swap_used": 0, "swap_percent": 0.0,
            "disk_total": 100000000000, "disk_used": 40000000000, "disk_percent": 40.0,
            "net_recv_rate": 100.0, "net_sent_rate": 200.0,
            "disk_read_rate": 10.0, "disk_write_rate": 20.0,
            "process_count": 50, "uptime_seconds": 1000}


def test_local_metrics_shape():
    m = local_metrics()
    for key in ("cpu_percent", "cpu_per_core", "load_avg", "mem_total", "mem_used",
                "mem_percent", "swap_total", "swap_used", "swap_percent",
                "disk_total", "disk_used", "disk_percent",
                "net_recv_rate", "net_sent_rate", "disk_read_rate", "disk_write_rate",
                "process_count", "uptime_seconds"):
        assert key in m, f"缺少字段 {key}"


def test_collect_server_remote_success(monkeypatch):
    m = make_metrics()
    monkeypatch.setattr(collector, "run_command", AsyncMock(return_value="raw"))
    monkeypatch.setattr(collector, "parse_script_output", lambda raw: m)
    monkeypatch.setattr(collector, "insert_metric", lambda *a, **k: None)
    status_updates = []
    monkeypatch.setattr(collector, "update_status",
                        lambda sid, status, err, ts: status_updates.append((sid, status, err)))
    monkeypatch.setattr(collector, "alert_evaluate", lambda *a, **k: None)

    result = asyncio.run(collector.MonitorCollector().collect_server(SSH_SERVER))
    assert result == m
    assert status_updates == [("srv-1", "online", None)]


def test_collect_server_remote_failure_marks_offline(monkeypatch):
    async def fail(*a, **k):
        raise SSHCommandError("连接失败")
    monkeypatch.setattr(collector, "run_command", fail)
    monkeypatch.setattr(collector, "insert_metric", lambda *a, **k: None)
    status_updates = []
    monkeypatch.setattr(collector, "update_status",
                        lambda sid, status, err, ts: status_updates.append((sid, status, err)))
    result = asyncio.run(collector.MonitorCollector().collect_server(SSH_SERVER))
    assert result is None
    assert status_updates[-1][1] == "offline"
    assert "连接失败" in (status_updates[-1][2] or "")


def test_collect_all_isolates_failures(monkeypatch):
    """一台失败不影响其他服务器"""
    monkeypatch.setattr(collector.MonitorCollector, "collect_server",
                        AsyncMock(side_effect=[None, make_metrics()]))
    done = asyncio.run(collector.MonitorCollector().collect_all([SSH_SERVER, LOCAL_SERVER]))
    assert done == 1  # 成功 1 台


def test_collect_server_local(monkeypatch):
    m = make_metrics()
    monkeypatch.setattr(collector, "local_metrics", lambda: m)
    monkeypatch.setattr(collector, "insert_metric", lambda *a, **k: None)
    status_updates = []
    monkeypatch.setattr(collector, "update_status",
                        lambda sid, status, err, ts: status_updates.append((sid, status, err)))
    monkeypatch.setattr(collector, "alert_evaluate", lambda *a, **k: None)
    result = asyncio.run(collector.MonitorCollector().collect_server(LOCAL_SERVER))
    assert result == m
