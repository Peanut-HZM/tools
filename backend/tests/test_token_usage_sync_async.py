"""/sync 接口单元测试：后台线程执行同步与缓存预热，不阻塞 HTTP 响应。"""
import threading
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import token_usage


def _make_app():
    """构造最小 FastAPI 应用，仅挂载 token_usage 路由，避免启动后台任务。"""
    app = FastAPI()
    app.include_router(token_usage.router, prefix="/api")
    return app, token_usage


def _auth_header():
    return {"Authorization": "Bearer fake.token"}


def _patch_auth(token_usage):
    """绕过认证，返回固定 user_id。"""
    return patch.object(
        token_usage,
        "get_current_user_id",
        lambda authorization: "user-1",
    )


def _patch_lock_unlocked(token_usage):
    """get_sync_lock().locked() 返回 False（锁未占用）。"""
    fake_lock = MagicMock()
    fake_lock.locked.return_value = False
    return patch.object(token_usage, "get_sync_lock", lambda: fake_lock)


def test_sync_returns_immediately_and_starts_background(monkeypatch):
    """/sync 立即返回，后台线程会调 sync + invalidate + warm。"""
    app, token_usage = _make_app()
    client = TestClient(app)

    monkeypatch.setattr(token_usage, "get_current_user_id", lambda authorization: "user-1")
    fake_lock = MagicMock()
    fake_lock.locked.return_value = False
    monkeypatch.setattr(token_usage, "get_sync_lock", lambda: fake_lock)

    # 让后台线程同步执行（不真的起 daemon），便于断言副作用
    real_start = threading.Thread.start

    def fake_start(self):
        if self._target is not None and self._target.__name__ == "_run_sync":
            self.run()
            return
        real_start(self)

    monkeypatch.setattr(threading.Thread, "start", fake_start)

    sync_calls = []
    invalidate_calls = []
    warm_calls = []

    def fake_sync(user_id, days):
        sync_calls.append((user_id, days))
        return {"total_records": 5, "errors": []}

    def fake_invalidate(user_id):
        invalidate_calls.append(user_id)

    def fake_warm(user_id):
        warm_calls.append(user_id)
        return True

    monkeypatch.setattr(token_usage, "sync_token_usage", fake_sync)
    monkeypatch.setattr(token_usage, "invalidate_user_query_cache", fake_invalidate)
    monkeypatch.setattr(token_usage, "warm_query_cache", fake_warm)

    response = client.post("/api/token-usage/sync", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["background"] is True
    assert body["started"] is True
    # 后台线程已执行：sync + invalidate + warm 各被调一次
    assert len(sync_calls) == 1
    assert sync_calls[0] == ("user-1", 90)
    assert invalidate_calls == ["user-1", "user-1"]  # sync 前 + sync 后
    assert warm_calls == ["user-1"]  # sync 完成后预热


def test_sync_returns_not_started_when_lock_held(monkeypatch):
    """锁已占用时返回 started=False，不调 sync/warm。"""
    app, token_usage = _make_app()
    client = TestClient(app)

    monkeypatch.setattr(token_usage, "get_current_user_id", lambda authorization: "user-1")
    fake_lock = MagicMock()
    fake_lock.locked.return_value = True
    monkeypatch.setattr(token_usage, "get_sync_lock", lambda: fake_lock)

    sync_calls = []
    warm_calls = []

    monkeypatch.setattr(
        token_usage,
        "sync_token_usage",
        lambda user_id, days: sync_calls.append((user_id, days)),
    )
    monkeypatch.setattr(
        token_usage,
        "warm_query_cache",
        lambda user_id: warm_calls.append(user_id),
    )

    response = client.post("/api/token-usage/sync", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["started"] is False
    assert sync_calls == []
    assert warm_calls == []
