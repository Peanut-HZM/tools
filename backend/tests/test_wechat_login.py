"""微信一键登录单测 — mock jscode2session（不出网）。

四路径：未配置 secret / 微信 errcode / 新用户自动注册（username 唯一化）/ 已有 openid 直接登录。
隔离：临时 SQLite + monkeypatch REAL_HOME；user_id 一律 zztest-<uuid> 规范。
"""
import json
import sys
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

ZZTEST_USER = {"id": f"zztest-{uuid.uuid4()}", "username": "zztest-wx"}


class _FakeWxResp:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models.base as base_mod
    from app.models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path}/wx_test.db",
                           connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(base_mod, "SessionLocal", TestingSession)
    from sqlalchemy import text
    with engine.connect() as conn:
        # auth_service 用 PG 裸 SQL（user_id/role 列）——测试表模拟其真实结构
        conn.execute(text(
            "CREATE TABLE users (user_id TEXT PRIMARY KEY, username TEXT UNIQUE, "
            "email TEXT UNIQUE, password_hash TEXT, role TEXT, openid TEXT, created_at TIMESTAMP)"))

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    monkeypatch.setattr("app.config.config.REAL_HOME", str(fake_home))

    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: ZZTEST_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


def _set_settings(monkeypatch, tmp_path, secret: str):
    """settings WX 配置；auth_service 的 pooled 连接替换为隔离 SQLite（绝不打真实 PG）。"""
    monkeypatch.setattr("app.config.config.settings.WX_APP_ID", "wxf7d4c07d66b6d237")
    monkeypatch.setattr("app.config.config.settings.WX_APP_SECRET", secret)

    import sqlite3 as _sqlite3
    import app.services.auth_service as auth_svc

    sqlite_conn = _sqlite3.connect(f"{tmp_path}/auth_test.db", check_same_thread=False)
    sqlite_conn.row_factory = _sqlite3.Row

    with sqlite_conn:
        # auth_service 用 PG 裸 SQL（user_id/role 列）——测试表模拟其真实结构
        sqlite_conn.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, username TEXT UNIQUE, "
            "email TEXT UNIQUE, password_hash TEXT, role TEXT, openid TEXT, created_at TIMESTAMP)")

    class _FakeCursor:
        """psycopg2 风格 cursor 适配：%s 占位符转 ?、Row 转 dict（RealDictCursor 语义）。"""

        def __init__(self, conn):
            self._conn = conn

        def __enter__(self):
            return self

        def __exit__(self, *args):  # noqa: ANN002,ANN003
            return False

        def execute(self, query, vars=None):  # noqa: A002
            q = query
            params = None
            if vars is not None:
                vars_list = list(vars) if isinstance(vars, (tuple, list)) else [vars]
                for _ in range(q.count("%s")):
                    q = q.replace("%s", "?", 1)
                params = tuple(vars_list)
            self._cur = self._conn.execute(q, params) if params else self._conn.execute(q)
            return self

        def fetchone(self):
            row = self._cur.fetchone()
            return dict(row) if row else None

        def fetchall(self):
            return [dict(r) for r in self._cur.fetchall() or []]

    class _FakePooledConn:
        """包一层 sqlite3 连接，模拟 psycopg2 pooled 连接的 cursor/commit/rollback/close。"""

        def cursor(self):
            return _FakeCursor(sqlite_conn)

        def commit(self):
            sqlite_conn.commit()

        def rollback(self):
            sqlite_conn.rollback()

        def close(self):
            pass

    monkeypatch.setattr(auth_svc, "get_pooled_db_connection", lambda: _FakePooledConn())
    monkeypatch.setattr(auth_svc, "release_db_connection", lambda conn: None)


def test_wechat_login_unconfigured_secret(client, tmp_path, monkeypatch):
    """未配置 WX_APP_SECRET → 503 + 明确错误（AppSecret 需用户提供）"""
    _set_settings(monkeypatch, tmp_path, secret="")
    resp = client.post("/api/auth/wechat-login", json={"code": "test-code"})
    assert resp.status_code == 503
    assert "未配置" in resp.json()["detail"]


def test_wechat_login_wx_errcode(client, tmp_path, monkeypatch):
    """微信 errcode（如 code 过期/无效）→ 401 透传 errmsg"""
    _set_settings(monkeypatch, tmp_path, secret="s")
    from app.services.agent_hub import usage_queries  # noqa: F401 确保 requests 可用
    import app.services.auth_service as auth_svc
    monkeypatch.setattr(
        auth_svc.requests, "get",
        lambda *a, **kw: _FakeWxResp({"errcode": 40029, "errmsg": "invalid code"}))
    resp = client.post("/api/auth/wechat-login", json={"code": "bad-code"})
    assert resp.status_code == 401
    assert "40029" in resp.json()["detail"]


def test_wechat_login_new_user_auto_register(client, tmp_path, monkeypatch):
    """新 openid → 自动注册（username=wx_+sha1 前 12 位）→ 签发 JWT"""
    _set_settings(monkeypatch, tmp_path, secret="s")
    import app.services.auth_service as auth_svc
    monkeypatch.setattr(
        auth_svc.requests, "get",
        lambda *a, **kw: _FakeWxResp({"openid": "oX-abcdef123456", "session_key": "sk"}))
    resp = client.post("/api/auth/wechat-login", json={"code": "good-code"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"].startswith("wx_")
    assert len(body["token"]) > 50

    # 同一 openid 第二次登录 → 同一用户（不重复注册）
    resp2 = client.post("/api/auth/wechat-login", json={"code": "good-code-2"})
    assert resp2.json()["user_id"] == body["user_id"]


def test_wechat_login_missing_code(client):
    """缺 code → 400"""
    resp = client.post("/api/auth/wechat-login", json={})
    assert resp.status_code == 400
