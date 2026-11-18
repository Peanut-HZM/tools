"""订阅额度 API 契约测试

* 打真实 app（含真实路由注册），避免「路由没挂上」这类问题漏检
* 覆盖鉴权（401）与响应结构（不含任何 token 字段）
* 用 monkeypatch 拦截网络层与凭据读取，测试本身不联网、不读真实凭据
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.subscription_quota import models as quota_models
from app.services.subscription_quota import providers as quota_providers
from app.services.subscription_quota import service as quota_service

client = TestClient(app)


def test_providers_requires_auth():
    response = client.get("/api/subscription-quota/providers")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header missing"


def test_query_requires_auth():
    response = client.post("/api/subscription-quota/query", json={})
    assert response.status_code == 401


def test_routes_registered_in_openapi():
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/subscription-quota/providers" in paths
    assert "/api/subscription-quota/query" in paths


DEMO_TOKEN = "demo-token-should-never-leak"


@pytest.fixture
def fake_auth(monkeypatch):
    """把鉴权换成固定用户，避免测试依赖真实 JWT 与数据库。"""
    from app.routes import subscription_quota as route_module

    monkeypatch.setattr(
        route_module, "_require_user", lambda authorization: "test-user"
    )
    return "test-user"


@pytest.fixture
def fake_credentials(monkeypatch):
    """所有供应商都返回同一份可控凭据。"""
    from app.services.subscription_quota import service as svc

    def _reader():
        return quota_service.Credential(
            token=DEMO_TOKEN,
            status=quota_models.CredentialStatus.VALID,
        )

    monkeypatch.setattr(
        svc,
        "detect_credentials",
        lambda: {tool: _reader() for tool in quota_service.KNOWN_TOOLS},
    )
    for tool in quota_service.KNOWN_TOOLS:
        monkeypatch.setitem(svc.CREDENTIAL_READERS, tool, _reader)


def test_providers_response_has_no_token_fields(fake_auth, fake_credentials):
    quota_service.clear_cache()
    response = client.get(
        "/api/subscription-quota/providers", headers={"Authorization": "Bearer x"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tools"] == list(quota_service.KNOWN_TOOLS)
    assert len(body["providers"]) == len(quota_service.KNOWN_TOOLS)

    serialized = response.text
    # 响应里绝不能出现 token 值本身
    assert DEMO_TOKEN not in serialized
    for provider in body["providers"]:
        assert set(provider.keys()) == {
            "tool",
            "displayName",
            "credentialStatus",
            "credentialMessage",
            "hasCredential",
            "supported",
        }
        assert "token" not in provider


def test_query_returns_structured_result_without_tokens(
    fake_auth, fake_credentials, monkeypatch
):
    """打桩网络层后，验证响应结构与「不含 token」这一硬约束"""

    async def _fake_get_json(url, headers, timeout=15.0):
        return 200, {
            "five_hour": {"utilization": 26.0, "resets_at": "2026-11-18T15:03:45Z"},
            "seven_day": {"utilization": 47.0, "resets_at": "2026-11-21T03:03:45Z"},
            "limits": [],
        }, None

    monkeypatch.setattr(quota_providers, "_get_json", _fake_get_json)
    quota_service.clear_cache()

    response = client.post(
        "/api/subscription-quota/query",
        json={"tools": ["claude"], "force_refresh": True},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "queriedAt" in body
    assert len(body["quotas"]) == 1

    quota = body["quotas"][0]
    assert quota["tool"] == "claude"
    assert quota["success"] is True
    assert quota["credentialStatus"] == "valid"
    assert [tier["name"] for tier in quota["tiers"]] == ["five_hour", "seven_day"]
    assert quota["tiers"][0]["utilization"] == 26.0
    assert quota["tiers"][0]["resetsAt"] == "2026-11-18T15:03:45Z"

    # 硬约束：任何 token 都不能出现在响应里
    assert DEMO_TOKEN not in response.text


def test_query_unknown_tool_returns_empty(fake_auth, fake_credentials):
    quota_service.clear_cache()
    response = client.post(
        "/api/subscription-quota/query",
        json={"tools": ["not-a-real-tool"], "force_refresh": True},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    assert response.json()["quotas"] == []


def test_query_handles_not_found_credentials(fake_auth, monkeypatch):
    """没有凭据时如实返回 not_found，不伪造额度"""

    from app.services.subscription_quota import service as svc

    def _reader():
        return quota_service.Credential()

    for tool in quota_service.KNOWN_TOOLS:
        monkeypatch.setitem(svc.CREDENTIAL_READERS, tool, _reader)
    quota_service.clear_cache()

    response = client.post(
        "/api/subscription-quota/query",
        json={"tools": ["kimi"], "force_refresh": True},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    quota = response.json()["quotas"][0]
    assert quota["success"] is False
    assert quota["credentialStatus"] == "not_found"
    assert quota["tiers"] == []
