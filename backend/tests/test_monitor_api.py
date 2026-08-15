# backend/tests/test_monitor_api.py
"""
监控 API 集成测试 - 服务器 CRUD、告警规则、设置（真实 PostgreSQL + 服务 monkeypatch）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.monitor.server_service import MonitorServerService
from app.services.monitor import alert_engine, remote_ops


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    register_response = client.post("/api/auth/register", json={
        "username": "monitor_test_user",
        "email": "monitor_test_user@example.com",
        "password": "testpassword123",
    })
    if register_response.status_code == 200:
        token = register_response.json().get("token")
    else:
        login_response = client.post("/api/auth/login", json={
            "username": "monitor_test_user",
            "password": "testpassword123",
        })
        token = login_response.json().get("token")
    return {"Authorization": f"Bearer {token}"}


def test_get_servers_creates_local_node(client, auth_headers):
    """首次获取服务器列表自动创建本机节点"""
    response = client.get("/api/monitor/servers", headers=auth_headers)
    assert response.status_code == 200
    servers = response.json()
    assert len(servers) >= 1
    assert any(s["server_type"] == "local" for s in servers)


def test_create_and_delete_server(client, auth_headers, monkeypatch):
    """创建监控服务器（凭据加密）→ 删除"""
    create_response = client.post("/api/monitor/servers", json={
        "name": "测试服务器", "host": "192.168.1.100", "port": 22,
        "username": "root", "password": "secret", "group_name": "生产",
    }, headers=auth_headers)
    assert create_response.status_code == 200
    server = create_response.json()
    assert server["server_type"] == "ssh"
    assert "password" not in server or server["password"] is None

    delete_response = client.delete(f"/api/monitor/servers/{server['id']}", headers=auth_headers)
    assert delete_response.status_code == 200


def test_create_server_invalid_port(client, auth_headers):
    response = client.post("/api/monitor/servers", json={
        "name": "x", "host": "h", "port": 99999, "username": "u",
    }, headers=auth_headers)
    assert response.status_code == 422


def test_test_connection_success(client, auth_headers, monkeypatch):
    monkeypatch.setattr(MonitorServerService, "test_connection",
                        staticmethod(lambda req: None))
    response = client.post("/api/monitor/servers/test", json={
        "host": "127.0.0.1", "port": 22, "username": "root", "password": "pw",
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_test_connection_failure(client, auth_headers, monkeypatch):
    from fastapi import HTTPException

    def fail(req):
        raise HTTPException(status_code=400, detail="连接失败: timeout")
    monkeypatch.setattr(MonitorServerService, "test_connection", staticmethod(fail))
    response = client.post("/api/monitor/servers/test", json={
        "host": "10.255.255.1", "port": 22, "username": "root", "password": "pw",
    }, headers=auth_headers)
    assert response.status_code == 400


def test_alert_rule_crud(client, auth_headers):
    create_response = client.post("/api/monitor/alerts", json={
        "server_id": "all", "metric": "cpu_percent", "operator": ">",
        "threshold": 90, "duration": 3,
    }, headers=auth_headers)
    assert create_response.status_code == 200
    rule = create_response.json()
    assert rule["metric"] == "cpu_percent"

    list_response = client.get("/api/monitor/alerts", headers=auth_headers)
    assert any(r["id"] == rule["id"] for r in list_response.json())

    update_response = client.put(f"/api/monitor/alerts/{rule['id']}", json={
        "threshold": 95,
    }, headers=auth_headers)
    assert update_response.status_code == 200
    assert update_response.json()["threshold"] == 95

    delete_response = client.delete(f"/api/monitor/alerts/{rule['id']}", headers=auth_headers)
    assert delete_response.status_code == 200


def test_settings_save_and_get(client, auth_headers):
    save_response = client.put("/api/monitor/settings", json={
        "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
        "collect_interval": 30,
    }, headers=auth_headers)
    assert save_response.status_code == 200

    get_response = client.get("/api/monitor/settings", headers=auth_headers)
    assert get_response.status_code == 200
    assert "test" in get_response.json()["webhook_url"]


def test_metrics_requires_auth(client):
    response = client.get("/api/monitor/servers")
    assert response.status_code == 401
