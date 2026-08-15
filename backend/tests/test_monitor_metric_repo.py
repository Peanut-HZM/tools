"""
指标存储测试 - 内存 fake 数据库验证 SQL 生成与返回映射
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import metric_repo
from app.services.monitor.metric_repo import (
    ensure_tables, insert_metric, get_latest_metric,
    query_metrics, delete_expired_metrics, RANGE_SECONDS,
)


class FakeCursor:
    def __init__(self, results, rowcount=None):
        self._results = results if results is not None else []
        self.rowcount = len(self._results) if rowcount is None else rowcount
        self.executed = []

    def close(self):
        pass

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, results=None, rowcount=None):
        self._results = results
        self._rowcount = rowcount
        self.committed = False
        self.cursors = []

    def cursor(self):
        cur = FakeCursor(self._results, self._rowcount)
        self.cursors.append(cur)
        return cur

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def fake_db(monkeypatch):
    holder = {"conn": FakeConn()}
    monkeypatch.setattr(metric_repo, "get_pooled_db_connection", lambda: holder["conn"])
    monkeypatch.setattr(metric_repo, "release_db_connection", lambda c: None)
    return holder


def test_range_seconds():
    assert RANGE_SECONDS == {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}


def test_insert_metric_uses_correct_sql(fake_db):
    m = {"cpu_percent": 10.0, "cpu_per_core": [1.0, 2.0], "load_avg": [0.1, 0.2, 0.3],
         "mem_total": 1, "mem_used": 1, "mem_percent": 1.0,
         "swap_total": 0, "swap_used": 0, "swap_percent": 0.0,
         "disk_total": 1, "disk_used": 1, "disk_percent": 1.0,
         "net_recv_rate": 1.0, "net_sent_rate": 1.0,
         "disk_read_rate": 1.0, "disk_write_rate": 1.0,
         "process_count": 10, "uptime_seconds": 100}
    insert_metric("srv-1", m)
    sql = fake_db["conn"].cursors[-1].executed[-1][0]
    assert "INSERT INTO monitor_metrics" in sql
    assert "jsonb" in sql.lower() or "json" in sql.lower()
    assert fake_db["conn"].committed


def test_get_latest_metric_returns_row(fake_db):
    fake_db["conn"] = FakeConn([{"collected_at": datetime(2026, 1, 1, 12, 0),
                                 "cpu_percent": 5.0, "mem_percent": 30.0,
                                 "net_recv_rate": 10.0}])
    result = get_latest_metric("srv-1")
    assert result["cpu_percent"] == 5.0
    assert result["collected_at"] is not None


def test_get_latest_metric_empty(fake_db):
    fake_db["conn"] = FakeConn([])
    assert get_latest_metric("srv-1") is None


def test_query_metrics_7d_uses_hourly_aggregation(fake_db):
    fake_db["conn"] = FakeConn([{"t": "2026-01-01 10:00:00", "cpu_percent": 5.0,
                                 "mem_percent": 5.0, "disk_percent": 5.0,
                                 "net_recv_rate": 1.0, "net_sent_rate": 1.0,
                                 "disk_read_rate": 1.0, "disk_write_rate": 1.0,
                                 "load1": 0.5}])
    rows = query_metrics("srv-1", "7d")
    assert len(rows) == 1
    sql = fake_db["conn"].cursors[-1].executed[-1][0]
    assert "date_trunc" in sql


def test_delete_expired_returns_count(fake_db):
    fake_db["conn"] = FakeConn([], rowcount=100)
    assert delete_expired_metrics(604800) == 100
