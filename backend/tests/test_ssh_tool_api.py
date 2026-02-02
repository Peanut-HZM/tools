import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.services.ssh_tool_service import SSHToolService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    register_response = client.post("/api/auth/register", json={
        "username": "ssh_test_user",
        "email": "ssh_test_user@example.com",
        "password": "testpassword123"
    })
    if register_response.status_code == 200:
        token = register_response.json().get("token")
    else:
        login_response = client.post("/api/auth/login", json={
            "username": "ssh_test_user",
            "password": "testpassword123"
        })
        token = login_response.json().get("token")
    return {"Authorization": f"Bearer {token}"}


def test_ssh_test_connection_success(client, auth_headers, monkeypatch):
    def fake_test_connection(payload):
        return True
    monkeypatch.setattr(SSHToolService, "test_connection", staticmethod(fake_test_connection))

    response = client.post("/api/ssh-tool/test-connection", json={
        "host": "127.0.0.1",
        "port": 22,
        "username": "root",
        "password": "pass"
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True


def test_ssh_test_connection_failure(client, auth_headers, monkeypatch):
    def fake_test_connection(payload):
        raise Exception("Connection failed")
    monkeypatch.setattr(SSHToolService, "test_connection", staticmethod(fake_test_connection))

    response = client.post("/api/ssh-tool/test-connection", json={
        "host": "127.0.0.1",
        "port": 22,
        "username": "root",
        "password": "pass"
    }, headers=auth_headers)

    assert response.status_code == 400
