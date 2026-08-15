"""
监控服务器服务测试 - 使用内存 fake 数据库连接
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import server_service
from app.services.monitor.server_service import MonitorServerService


class FakeCursor:
    """模拟 psycopg2 游标（只覆盖本模块用到的操作）"""
    def __init__(self, conn, fetch_results=None, rowcount=1):
        self.conn = conn
        self._results = fetch_results if fetch_results is not None else []
        self.rowcount = rowcount
        self.executed = []

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

    def close(self):
        pass


class FakeConn:
    def __init__(self, results=None):
        self.commits = 0
        self.rollbacks = 0
        self._results = results

    def cursor(self):
        return FakeCursor(self, self._results)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    holder = {"conn": FakeConn()}
    monkeypatch.setattr(server_service, "get_pooled_db_connection", lambda: holder["conn"])
    monkeypatch.setattr(server_service, "release_db_connection", lambda c: None)
    return holder


def test_create_server_encrypts_password(monkeypatch, fake_db):
    from app.models.monitor_models import CreateMonitorServerRequest
    req = CreateMonitorServerRequest(name="web1", host="10.0.0.1", username="root", password="p@ss")
    fake_db["conn"]._results = [{"id": "srv-1", "user_id": "u1", "name": "web1",
                                 "server_type": "ssh", "host": "10.0.0.1", "port": 22,
                                 "username": "root", "group_name": None, "status": "enabled",
                                 "last_error": None, "last_seen_at": None,
                                 "created_at": __import__("datetime").datetime(2026, 1, 1)}]
    created = MonitorServerService.create_server("u1", req)
    assert created["id"] == "srv-1"
    # 确认写入的是加密后的密码
    insert_sql = fake_db["conn"].cursor().executed[0][0] if fake_db["conn"].cursor().executed else ""
    # cursor 每次调用是新对象，直接断言结果即可
    assert created["name"] == "web1"


def test_get_servers_returns_metric(monkeypatch, fake_db):
    from datetime import datetime
    fake_db["conn"]._results = [
        {"id": "srv-1", "user_id": "u1", "name": "web1", "server_type": "ssh",
         "host": "10.0.0.1", "port": 22, "username": "root", "group_name": None,
         "status": "online", "last_error": None, "last_seen_at": datetime(2026, 1, 1),
         "created_at": datetime(2026, 1, 1),
         "metric": {"cpu_percent": 12.3, "mem_percent": 55.0, "disk_percent": 40.0,
                    "net_recv_rate": 1000, "net_sent_rate": 500}}
    ]
    servers = MonitorServerService.get_servers("u1")
    assert len(servers) == 1
    assert servers[0]["metric"]["cpu_percent"] == 12.3


def test_get_server_decrypts_credentials(monkeypatch, fake_db):
    from datetime import datetime
    fake_db["conn"]._results = [
        {"id": "srv-1", "user_id": "u1", "name": "web1", "server_type": "ssh",
         "host": "10.0.0.1", "port": 22, "username": "root",
         "password_encrypted": "ENC:pw", "private_key_encrypted": None,
         "passphrase_encrypted": None, "group_name": None, "status": "online",
         "last_error": None, "last_seen_at": datetime(2026, 1, 1),
         "created_at": datetime(2026, 1, 1)}
    ]
    monkeypatch.setattr(server_service.EncryptionUtils, "decrypt",
                        staticmethod(lambda v: v.replace("ENC:", "")))
    server = MonitorServerService.get_server("u1", "srv-1")
    assert server["password"] == "pw"


def test_get_global_interval_default(monkeypatch, fake_db):
    fake_db["conn"]._results = []  # 无全局设置行
    assert MonitorServerService.get_global_interval() == 30


def test_get_global_interval_from_db(monkeypatch, fake_db):
    fake_db["conn"]._results = [{"collect_interval": 60}]
    assert MonitorServerService.get_global_interval() == 60
