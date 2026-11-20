"""Neo4j 连接 CRUD + 连通性测试 API 的集成测试。

复用 Task 1 的模型与 crypto；测试 DB 用内存 SQLite + StaticPool，
鉴权通过 monkeypatch get_current_user_id 替换。
"""
import os
import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import get_db
from app.models.base import Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    # crypto 密钥必须在首次加解密前注入（crypto 模块加载后缓存）
    os.environ["NEO4J_CRYPTO_KEY"] = Fernet.generate_key().decode()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # 同一 client 会话内 user_id 必须稳定（否则 create/list 落到不同用户）
    fixture_user_id = str(uuid.uuid4())
    monkeypatch.setattr(
        "app.middleware.auth_middleware.get_current_user_id",
        lambda authorization=None: fixture_user_id,
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_and_list_excludes_password(client):
    r = client.post("/api/neo4j-tool/connections", json={
        "name": "local", "uri": "bolt://localhost:7687",
        "username": "neo4j", "password": "secret", "database": "neo4j",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "local"
    assert "password" not in body
    assert "encrypted_password" not in body

    r2 = client.get("/api/neo4j-tool/connections")
    assert r2.status_code == 200
    assert len(r2.json()) == 1
    assert "password" not in r2.json()[0]


def test_update_with_empty_password_keeps_old(client):
    r = client.post("/api/neo4j-tool/connections", json={
        "name": "a", "uri": "bolt://x:7687", "username": "u", "password": "p1",
    })
    cid = r.json()["id"]
    r2 = client.put(f"/api/neo4j-tool/connections/{cid}", json={"name": "b"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "b"


def test_cannot_see_others_connection(client, db_session, monkeypatch):
    other = str(uuid.uuid4())
    r = client.post("/api/neo4j-tool/connections", json={
        "name": "a", "uri": "bolt://x:7687", "username": "u", "password": "p",
    })
    cid = r.json()["id"]
    # 换个 user_id
    monkeypatch.setattr(
        "app.middleware.auth_middleware.get_current_user_id",
        lambda authorization=None: other,
    )
    r2 = client.get(f"/api/neo4j-tool/connections/{cid}")
    assert r2.status_code == 404


def test_test_endpoint_ok_when_driver_connects(client, monkeypatch):
    class FakeDriver:
        def verify_connectivity(self):
            return None

        def get_server_info(self):
            class Info:
                agent = "Neo4j/5.20.0"
            return Info()

        def close(self):
            return None

    monkeypatch.setattr(
        "app.routes.neo4j_tool._open_test_driver",
        lambda uri, username, password, database=None: FakeDriver(),
    )
    r = client.post("/api/neo4j-tool/connections", json={
        "name": "a", "uri": "bolt://x:7687", "username": "u", "password": "p",
    })
    cid = r.json()["id"]
    r2 = client.post(f"/api/neo4j-tool/connections/{cid}/test")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
    assert "5.20.0" in r2.json()["server_version"]
