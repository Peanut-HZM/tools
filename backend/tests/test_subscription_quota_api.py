"""订阅额度 API 契约测试（v2）

* 打真实 app（含真实路由注册）
* 覆盖鉴权、供应商目录、账号 CRUD、响应不含明文 Key
* 网络层与数据库层都打桩，测试本身不联网
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.subscription_quota import accounts as accounts_mod
from app.services.subscription_quota import providers_full as providers_mod
from app.services.subscription_quota import service as service_mod
from app.services.subscription_quota.models import CredentialStatus, QuotaTier, SubscriptionQuota

client = TestClient(app)

DEMO_KEY = "sk-demo-secret-key-should-never-leak"


# ---------------------------------------------------------------- 鉴权


def test_providers_requires_auth():
    assert client.get("/api/subscription-quota/providers").status_code == 401


def test_accounts_requires_auth():
    assert client.get("/api/subscription-quota/accounts").status_code == 401


def test_query_requires_auth():
    assert client.post("/api/subscription-quota/query", json={}).status_code == 401


def test_routes_registered():
    paths = app.openapi()["paths"]
    for path in (
        "/api/subscription-quota/providers",
        "/api/subscription-quota/accounts",
        "/api/subscription-quota/accounts/{account_id}",
        "/api/subscription-quota/accounts/{account_id}/test",
        "/api/subscription-quota/query",
        "/api/subscription-quota/subscriptions",
    ):
        assert path in paths, f"缺少路由 {path}"


# ---------------------------------------------------------------- fixture


@pytest.fixture
def fake_user(monkeypatch):
    """绕过真实 JWT"""
    from app.routes import subscription_quota as route_module

    monkeypatch.setattr(route_module, "_require_user", lambda authorization: "test-user")
    return "test-user"


@pytest.fixture
def memory_store(monkeypatch):
    """用内存字典替代表存储"""
    store: dict[str, accounts_mod.QuotaAccount] = {}

    def _create(user_id, provider_id, *, label="", api_key=None, extra=None):
        import uuid

        account = accounts_mod.QuotaAccount(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider_id=provider_id,
            label=label,
            api_key=api_key,
            extra=dict(extra or {}),
            enabled=True,
        )
        store[account.id] = account
        return account

    monkeypatch.setattr(accounts_mod, "create_account", _create)
    monkeypatch.setattr(
        accounts_mod, "list_accounts", lambda user_id, only_enabled=False: list(store.values())
    )
    monkeypatch.setattr(accounts_mod, "get_account", lambda user_id, aid: store.get(aid))

    # service 模块用 from-import 引用了 list_accounts，需单独替换
    monkeypatch.setattr(
        service_mod, "list_accounts", lambda user_id, only_enabled=False: list(store.values())
    )
    # 本地虚拟账号（Kimi Code 登录等）在测试里关闭，避免依赖真实凭据
    monkeypatch.setattr(service_mod, "discover_local_accounts", lambda: [])

    def _update(user_id, aid, **kwargs):
        account = store.get(aid)
        if account is None:
            return None
        if kwargs.get("label") is not None:
            account.label = kwargs["label"]
        if kwargs.get("api_key") is not None:
            account.api_key = kwargs["api_key"]
        if kwargs.get("extra") is not None:
            account.extra = kwargs["extra"]
        if kwargs.get("enabled") is not None:
            account.enabled = kwargs["enabled"]
        return account

    def _delete(user_id, aid):
        return store.pop(aid, None) is not None

    monkeypatch.setattr(accounts_mod, "update_account", _update)
    monkeypatch.setattr(accounts_mod, "delete_account", _delete)

    # 路由模块里是 from-import，需要同步替换
    from app.routes import subscription_quota as route_module

    for name, fn in (
        ("create_account", _create),
        ("list_accounts", lambda user_id, only_enabled=False: list(store.values())),
        ("get_account", lambda user_id, aid: store.get(aid)),
        ("update_account", _update),
        ("delete_account", _delete),
    ):
        monkeypatch.setattr(route_module, name, fn)

    return store


@pytest.fixture
def fake_provider(monkeypatch):
    """把 kimi 查询换成固定结果"""

    async def _fake(account):
        return SubscriptionQuota(
            tool=account.provider_id,
            credential_status=CredentialStatus.VALID,
            success=True,
            tiers=[
                QuotaTier(name="five_hour", utilization=26.0, resets_at="2026-11-18T15:03:45Z"),
                QuotaTier(name="weekly_limit", utilization=47.0, resets_at="2026-11-21T03:03:45Z"),
            ],
            plan_name="Allegretto",
            queried_at=1_700_000_000_000,
        )

    monkeypatch.setitem(providers_mod.QUERY_FUNCS, "kimi", _fake)
    # service 里是 import 的函数表
    service_mod.QUERY_FUNCS["kimi"] = _fake
    monkeypatch.setattr(
        service_mod, "query_subscriptions", _no_subscriptions
    )
    return _fake


async def _no_subscriptions(*, force_refresh=False):
    return []


# ---------------------------------------------------------------- 目录


def test_providers_returns_full_catalog(fake_user):
    response = client.get("/api/subscription-quota/providers", headers={"Authorization": "Bearer x"})
    assert response.status_code == 200
    body = response.json()

    ids = {p["id"] for p in body["providers"]}
    # cc-switch 的全量供应商都在
    for expected in (
        "kimi", "zhipu", "zhipu_team", "minimax", "zenmux", "opencode_go",
        "command_code", "opendesign", "volcengine",
        "deepseek", "stepfun", "siliconflow", "openrouter", "novita",
        "ollama_cloud", "zhipu_payg",
        "claude", "codex", "gemini",
    ):
        assert expected in ids, f"目录缺少 {expected}"

    kimi = next(p for p in body["providers"] if p["id"] == "kimi")
    assert kimi["kind"] == "window"
    assert kimi["needs"] == ["api_key"]
    assert kimi["addable"] is True

    claude = next(p for p in body["providers"] if p["id"] == "claude")
    assert claude["kind"] == "subscription"
    assert claude["addable"] is False


# ---------------------------------------------------------------- 账号 CRUD


def test_create_account_and_list_masked(fake_user, memory_store):
    response = client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "kimi", "label": "工作号", "api_key": DEMO_KEY, "extra": {"region": "cn"}},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    body = response.json()

    # 硬约束：响应里绝不能出现明文 Key
    assert DEMO_KEY not in response.text
    assert body["account"]["maskedKey"].startswith("sk-d")
    assert body["account"]["hasKey"] is True
    assert body["account"]["label"] == "工作号"

    listing = client.get(
        "/api/subscription-quota/accounts", headers={"Authorization": "Bearer x"}
    )
    assert listing.status_code == 200
    assert len(listing.json()["accounts"]) == 1
    assert DEMO_KEY not in listing.text


def test_create_subscription_provider_rejected(fake_user, memory_store):
    response = client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "claude", "label": "x"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 400
    assert "本机 CLI 登录凭据" in response.json()["detail"]


def test_create_unknown_provider_rejected(fake_user, memory_store):
    response = client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "not-real"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 400


def test_update_account(fake_user, memory_store):
    created = client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "kimi", "api_key": DEMO_KEY},
        headers={"Authorization": "Bearer x"},
    ).json()["account"]

    response = client.put(
        f"/api/subscription-quota/accounts/{created['id']}",
        json={"label": "改名了", "enabled": False},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    assert response.json()["account"]["label"] == "改名了"
    assert response.json()["account"]["enabled"] is False


def test_delete_account(fake_user, memory_store):
    created = client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "kimi", "api_key": DEMO_KEY},
        headers={"Authorization": "Bearer x"},
    ).json()["account"]

    assert (
        client.delete(
            f"/api/subscription-quota/accounts/{created['id']}",
            headers={"Authorization": "Bearer x"},
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"/api/subscription-quota/accounts/{created['id']}",
            headers={"Authorization": "Bearer x"},
        ).status_code
        == 404
    )


def test_update_missing_account_404(fake_user, memory_store):
    response = client.put(
        "/api/subscription-quota/accounts/missing",
        json={"label": "x"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------- 查询


def test_query_returns_configured_accounts_only(fake_user, memory_store, fake_provider):
    client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "kimi", "label": "工作号", "api_key": DEMO_KEY},
        headers={"Authorization": "Bearer x"},
    )
    service_mod.clear_cache()

    response = client.post(
        "/api/subscription-quota/query",
        json={"include_subscriptions": False, "force_refresh": True},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["configured"] is True
    assert len(body["accounts"]) == 1
    quota = body["accounts"][0]
    assert quota["providerId"] == "kimi"
    assert quota["label"] == "工作号"
    assert quota["kind"] == "window"
    assert quota["success"] is True
    assert [t["name"] for t in quota["tiers"]] == ["five_hour", "weekly_limit"]
    assert quota["tiers"][0]["utilization"] == 26.0

    # 任何 token / Key 都不能出现在响应里
    assert DEMO_KEY not in response.text
    assert "secret" not in response.text.lower()


def test_query_with_no_accounts_reports_not_configured(fake_user, memory_store, monkeypatch):
    monkeypatch.setattr(service_mod, "query_subscriptions", _no_subscriptions)
    response = client.post(
        "/api/subscription-quota/query",
        json={"include_subscriptions": False},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["accounts"] == []


def test_query_failure_keeps_error_not_fake_data(fake_user, memory_store, monkeypatch):
    async def _failing(account):
        return SubscriptionQuota.failure(
            account.provider_id, CredentialStatus.EXPIRED, "认证失败（HTTP 401）"
        )

    monkeypatch.setitem(providers_mod.QUERY_FUNCS, "kimi", _failing)
    service_mod.QUERY_FUNCS["kimi"] = _failing
    monkeypatch.setattr(service_mod, "query_subscriptions", _no_subscriptions)

    client.post(
        "/api/subscription-quota/accounts",
        json={"provider_id": "kimi", "api_key": DEMO_KEY},
        headers={"Authorization": "Bearer x"},
    )
    service_mod.clear_cache()

    body = client.post(
        "/api/subscription-quota/query",
        json={"include_subscriptions": False, "force_refresh": True},
        headers={"Authorization": "Bearer x"},
    ).json()

    quota = body["accounts"][0]
    assert quota["success"] is False
    assert quota["tiers"] == []
    assert "401" in quota["error"]
