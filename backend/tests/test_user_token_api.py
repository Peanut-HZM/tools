"""个人 API Token 路由测试（override JWT 依赖 + patch service）"""
import os
import sys
from datetime import datetime

import pytest
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth_middleware import get_current_user_id
from app.models.user_api_token_models import UserTokenCreatedResponse, UserTokenResponse


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user_id, None)


def test_create_token_returns_plain_once(client):
    resp_dto = UserTokenCreatedResponse(
        id="t1", name="cc", token_prefix="pat_abc12345", created_at=datetime.now(),
        token="pat_secretsecret",
    )
    with patch("app.routes.user_api_token.UserTokenService.generate_token",
               return_value=(resp_dto, "pat_secretsecret")) as m:
        r = client.post("/api/user-tokens", json={"name": "cc", "expires_days": 30})
    assert r.status_code == 200
    body = r.json()
    assert body["token"] == "pat_secretsecret"
    assert body["token_prefix"] == "pat_abc12345"
    m.assert_called_once_with("u1", "cc", 30)


def test_create_token_validates_input(client):
    assert client.post("/api/user-tokens", json={"name": ""}).status_code == 422
    assert client.post("/api/user-tokens", json={"name": "x", "expires_days": 0}).status_code == 422


def test_list_tokens(client):
    dto = UserTokenResponse(id="t1", name="cc", token_prefix="pat_abc12345",
                            created_at=datetime.now())
    with patch("app.routes.user_api_token.UserTokenService.list_tokens",
               return_value=[dto]) as m:
        r = client.get("/api/user-tokens")
    assert r.status_code == 200
    assert r.json()[0]["id"] == "t1"
    assert "token" not in r.json()[0]      # 列表永不含明文
    m.assert_called_once_with("u1")


def test_revoke_token_404_when_missing(client):
    with patch("app.routes.user_api_token.UserTokenService.revoke_token", return_value=False):
        r = client.delete("/api/user-tokens/nope")
    assert r.status_code == 404


def test_revoke_token_ok(client):
    with patch("app.routes.user_api_token.UserTokenService.revoke_token", return_value=True):
        r = client.delete("/api/user-tokens/t1")
    assert r.status_code == 200
