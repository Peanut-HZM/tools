"""
告警引擎测试 - 规则评估、去重、恢复、Webhook 推送
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import alert_engine, webhook_notify

METRICS = {
    "cpu_percent": 95.0, "mem_percent": 20.0, "disk_percent": 30.0,
    "load_avg": [2.0, 1.5, 1.0], "net_recv_rate": 100.0, "net_sent_rate": 50.0,
}
SERVER = {"id": "srv-1", "user_id": "u1", "name": "web1", "server_type": "ssh",
          "host": "10.0.0.1", "port": 22, "username": "root", "password": None,
          "private_key": None, "passphrase": None, "group_name": None,
          "status": "enabled", "last_error": None, "last_seen_at": None}

RULE = {"id": "rule-1", "user_id": "u1", "server_id": "srv-1", "metric": "cpu_percent",
        "operator": ">", "threshold": 90, "duration": 2, "enabled": True}


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前重置告警内存状态"""
    alert_engine._firing_counts.clear()
    alert_engine._firing_active.clear()
    yield
    alert_engine._firing_counts.clear()
    alert_engine._firing_active.clear()


@pytest.fixture
def fake_db(monkeypatch):
    holder = {"conn": MagicMock()}
    monkeypatch.setattr(alert_engine, "get_pooled_db_connection", lambda: holder["conn"])
    monkeypatch.setattr(alert_engine, "release_db_connection", lambda c: None)
    return holder


class FakeCursor:
    def __init__(self, results):
        self._results = results if results is not None else []
        self.rowcount = 1
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "INSERT INTO monitor_alert_logs" in sql:
            # 模拟返回插入 id
            self._results = [{"id": 1}]
        if "RETURNING id" in sql:
            self._results = [{"id": "new-rule"}]

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake_db_with_rules(monkeypatch, fake_db):
    """get_rules 返回固定规则"""
    monkeypatch.setattr(
        alert_engine,
        "get_rules",
        lambda user_id: [dict(RULE)] if user_id == "u1" else [],
    )
    return fake_db


def test_evaluate_fires_after_duration(monkeypatch, fake_db_with_rules):
    """连续 2 次超过阈值后触发告警"""
    monkeypatch.setattr(webhook_notify, "send_webhook", lambda *a, **k: True)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, METRICS)
    assert alert_engine._firing_counts[("rule-1", "srv-1")] == 1
    assert not alert_engine._firing_active.get(("rule-1", "srv-1"))
    alert_engine.evaluate(SERVER, METRICS)
    assert alert_engine._firing_active.get(("rule-1", "srv-1")) is True


def test_evaluate_no_fire_when_below_threshold(monkeypatch, fake_db_with_rules):
    low = dict(METRICS, cpu_percent=10.0)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, low)
    assert alert_engine._firing_counts.get(("rule-1", "srv-1"), 0) == 0
    assert not alert_engine._firing_active.get(("rule-1", "srv-1"))


def test_firing_does_not_notify_twice(monkeypatch, fake_db_with_rules):
    """触发态中不再重复通知"""
    monkeypatch.setattr(webhook_notify, "send_webhook", lambda *a, **k: True)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, METRICS)
    alert_engine.evaluate(SERVER, METRICS)
    assert alert_engine._firing_active[("rule-1", "srv-1")]
    alert_engine.evaluate(SERVER, METRICS)  # 仍超阈值
    # 只通知一次：第二次触发插入 log，第三次不再插入
    assert alert_engine._firing_counts[("rule-1", "srv-1")] == 2


def test_recovery_writes_recovered_log(monkeypatch, fake_db_with_rules):
    recovered = {"written": []}
    monkeypatch.setattr(webhook_notify, "send_webhook", lambda *a, **k: True)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: recovered["written"].append(k))
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, METRICS)  # 1
    alert_engine.evaluate(SERVER, METRICS)  # 2 → fire
    assert alert_engine._firing_active[("rule-1", "srv-1")]
    low = dict(METRICS, cpu_percent=10.0)
    alert_engine.evaluate(SERVER, low)  # 恢复
    assert alert_engine._firing_active.get(("rule-1", "srv-1")) is False
    assert any(w["status"] == "recovered" for w in recovered["written"])


def test_rule_server_all_matches_any_server(monkeypatch, fake_db, fake_db_with_rules):
    """server_id='all' 的规则对所有服务器生效"""
    monkeypatch.setattr(alert_engine, "get_rules", lambda uid: [dict(RULE, server_id="all")])
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    other = dict(SERVER, id="srv-2")
    alert_engine.evaluate(other, METRICS)
    assert alert_engine._firing_counts.get(("rule-1", "srv-2"), 0) == 1


def test_send_webhook_success(monkeypatch):
    resp = MagicMock()
    resp.status_code = 200
    monkeypatch.setattr(webhook_notify.httpx, "post", lambda *a, **k: resp)
    assert webhook_notify.send_webhook("http://hook", "标题", "内容") is True


def test_send_webhook_failure(monkeypatch):
    monkeypatch.setattr(webhook_notify.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(Exception("网络错误")))
    assert webhook_notify.send_webhook("http://hook", "标题", "内容") is False
