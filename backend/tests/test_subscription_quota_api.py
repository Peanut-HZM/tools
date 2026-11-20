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

    def _create(user_id, provider_id, *, label="", api_key=None, extra=None, **kwargs):
        """假实现：接受与生产同签名的新字段（category/app/manual_* 等）"""
        import uuid

        account = accounts_mod.QuotaAccount(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider_id=provider_id,
            label=label,
            api_key=api_key,
            extra=dict(extra or {}),
            enabled=True,
            **{
                key: kwargs[key]
                for key in (
                    "category",
                    "app",
                    "notes",
                    "website_url",
                    "manual_total",
                    "manual_used",
                    "quota_unit",
                    "window_type",
                    "window_reset_at",
                )
                if key in kwargs
            },
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
        # 新字段（category/app/manual_* 等）与老字段一样，按关键字直接赋值
        for field in (
            "label",
            "api_key",
            "extra",
            "enabled",
            "category",
            "app",
            "notes",
            "website_url",
            "manual_total",
            "manual_used",
            "quota_unit",
            "window_type",
            "window_reset_at",
        ):
            if kwargs.get(field) is not None:
                setattr(account, field, kwargs[field])
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


# ---------------------------------------------------------------- cc-switch 导入（非破坏性）


@pytest.fixture
def fake_ccswitch(monkeypatch):
    """把 cc-switch 候选与数据库路径打桩，避免依赖本机 cc-switch 安装"""
    from app.routes import subscription_quota as route_module
    from app.services.subscription_quota import usage_import

    # 伪造一个存在的 db 文件路径（只用于通过 exists() 检查，内容不会被读）
    fake_db = __import__("pathlib").Path("/tmp/zztest-cc-switch.db")
    monkeypatch.setattr(usage_import, "ccswitch_db_path", lambda: fake_db)
    monkeypatch.setattr(
        __import__("pathlib").Path, "exists", lambda self: True, raising=False
    )

    import sys as _sys

    sys_mod = __import__("sys")
    fake_module = type(sys_mod)("scripts.import_ccswitch_providers")

    def _load_candidates(_db):
        return [
            {
                "provider_id": "zhipu",
                "source_app": "claude",
                "source_name": "Zhipu GLM",
                "api_key": "sk-ccswitch-zhipu-key-0001",
                "region": "cn",
                "base_url": "",
                "from_control_key": False,
            },
            {
                "provider_id": "newprov",
                "source_app": "codex",
                "source_name": "New Provider",
                "api_key": "sk-ccswitch-new-key-0002",
                "region": "",
                "base_url": "https://new.example.com",
                "from_control_key": False,
            },
        ]

    fake_module.load_candidates = _load_candidates
    monkeypatch.setitem(sys_mod.modules, "scripts.import_ccswitch_providers", fake_module)
    monkeypatch.setattr(route_module, "clear_cache", lambda: None)

    # 探测会真实联网查额度 —— 测试里必须打桩，否则依赖外网且结果不稳定。
    # 默认「全部可用」，各用例可按需覆盖成不可用。
    # 注意：导入流程用的是 pick_working_candidates（返回多个账号），
    # 单账号场景才用 pick_working_candidate，两个都要打桩。
    from app.services.subscription_quota import credential_probe

    async def _pick_all_working_multi(candidates):
        seen: set[str] = set()
        out = []
        for candidate in candidates:
            key = str(candidate.get("api_key") or "")
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
        return out

    async def _pick_all_working(candidates):
        result = await _pick_all_working_multi(candidates)
        return result[0] if result else None

    monkeypatch.setattr(credential_probe, "pick_working_candidates", _pick_all_working_multi)
    monkeypatch.setattr(credential_probe, "pick_working_candidate", _pick_all_working)
    return route_module


AUTH = {"Authorization": "Bearer zztest"}


def test_ccswitch_import_does_not_overwrite_existing(fake_user, memory_store, fake_ccswitch):
    """核心回归：同一个账号不能被 cc-switch 导入覆盖

    真实缺陷：导入逻辑对同 provider 的账号无条件 update，
    把用户在页面里改过的 Key / 显示名 / 手工额度全部冲掉。

    去重口径是 (provider_id, api_key)：同一个 Key 视为同一账号 → 跳过；
    同 provider 的**不同** Key 是另一个账号 → 允许新建（多账号场景）。
    """
    # 用户已有 zhipu 账号（Key 与 cc-switch 里的那条相同），手工改过 label 与额度
    accounts_mod.create_account(
        fake_user, "zhipu", label="我自己改的名字", api_key="sk-ccswitch-zhipu-key-0001"
    )
    existing = accounts_mod.list_accounts(fake_user)[0]
    accounts_mod.update_account(
        fake_user, existing.id, manual_total=500.0, manual_used=123.0, notes="手工备注"
    )

    resp = client.post("/api/subscription-quota/import/cc-switch", json={}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()

    # 同 Key 的 zhipu 应被跳过；newprov 应被新建
    assert body["skipped"] == 1
    assert body["created"] == 1
    assert body["updated"] == 0

    after = {a.provider_id: a for a in accounts_mod.list_accounts(fake_user)}
    zhipu = after["zhipu"]
    # 关键断言：用户数据一个都不能变
    assert zhipu.label == "我自己改的名字"
    assert zhipu.api_key == "sk-ccswitch-zhipu-key-0001"
    assert zhipu.manual_total == 500.0
    assert zhipu.manual_used == 123.0
    assert zhipu.notes == "手工备注"
    # 新供应商正常导入
    assert "newprov" in after


def test_ccswitch_import_keeps_multiple_accounts_of_same_provider(
    fake_user, memory_store, fake_ccswitch, monkeypatch
):
    """回归：同供应商的多个账号必须都导入，不能只留一个

    真实缺陷：导入按 provider_id 归组并只取一个候选，
    智谱的三个订阅（团队 HZM / 团队 LYD / 个人 Peanut）只剩一个。
    """
    from app.services.subscription_quota import credential_probe

    # 让 cc-switch 里同一个 provider 出现两个不同 Key 的账号
    route_module = fake_ccswitch
    import sys as _sys

    fake_module = _sys.modules["scripts.import_ccswitch_providers"]

    def _load_candidates(_db):
        return [
            {
                "provider_id": "zhipu_team",
                "source_app": "claude",
                "source_name": "Zhipu GLM Team HZM",
                "api_key": "sk-team-hzm-0001",
                "region": "cn",
                "base_url": "",
                "from_control_key": False,
                "organization_id": "org-aaa",
                "project_id": "proj-aaa",
            },
            {
                "provider_id": "zhipu_team",
                "source_app": "claude",
                "source_name": "Zhipu GLM Team LYD",
                "api_key": "sk-team-lyd-0002",
                "region": "cn",
                "base_url": "",
                "from_control_key": False,
                "organization_id": "org-aaa",
                "project_id": "proj-aaa",
            },
        ]

    fake_module.load_candidates = _load_candidates

    async def _all(candidates):
        return list(candidates)

    monkeypatch.setattr(credential_probe, "pick_working_candidates", _all)

    resp = client.post("/api/subscription-quota/import/cc-switch", json={}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2, "同供应商的两个不同 Key 必须都建号"
    assert body["skipped"] == 0

    labels = sorted(a.label for a in accounts_mod.list_accounts(fake_user))
    assert any("HZM" in x for x in labels)
    assert any("LYD" in x for x in labels)

    # 团队组织的 org/proj 必须落库，否则团队版额度查不出来
    for account in accounts_mod.list_accounts(fake_user):
        assert account.extra.get("organization_id") == "org-aaa"
        assert account.extra.get("project_id") == "proj-aaa"


def test_ccswitch_import_overwrite_flag_only_touches_credentials(
    fake_user, memory_store, fake_ccswitch
):
    """显式 overwrite 时只更新凭据，用户手工维护的字段仍保留

    去重口径是 (provider_id, api_key)，所以要覆盖同一个账号，
    本地账号的 Key 必须与 cc-switch 里那条一致。
    """
    accounts_mod.create_account(
        fake_user, "zhipu", label="我改的名字", api_key="sk-ccswitch-zhipu-key-0001"
    )
    existing = accounts_mod.list_accounts(fake_user)[0]
    accounts_mod.update_account(
        fake_user, existing.id, manual_total=800.0, notes="别动我"
    )

    resp = client.post(
        "/api/subscription-quota/import/cc-switch",
        json={"overwrite": True},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["updated"] == 1

    zhipu = {a.provider_id: a for a in accounts_mod.list_accounts(fake_user)}["zhipu"]
    # 凭据被更新
    assert zhipu.api_key == "sk-ccswitch-zhipu-key-0001"
    # 用户手工维护的字段保持不变
    assert zhipu.label == "我改的名字"
    assert zhipu.manual_total == 800.0
    assert zhipu.notes == "别动我"


def test_ccswitch_import_dry_run_writes_nothing(fake_user, memory_store, fake_ccswitch):
    resp = client.post(
        "/api/subscription-quota/import/cc-switch", json={"dry_run": True}, headers=AUTH
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dryRun"] is True
    assert body["imported"] == 0
    assert accounts_mod.list_accounts(fake_user) == []


def test_ccswitch_import_probes_and_skips_unusable_keys(
    fake_user, memory_store, fake_ccswitch, monkeypatch
):
    """回归：候选 Key 不可用时不得导入

    真实缺陷：cc-switch 里同一供应商常有多条配置（给不同 CLI 各配一份），
    盲目取第一条会把失效 Key 导进来 —— 卡片永远显示
    「认证失败（HTTP 401）」/「当前用户不存在coding plan」。
    现在改为探测后只导入可用的那条。
    """
    from app.services.subscription_quota import credential_probe

    async def _none_works(candidates):
        # 模拟：该供应商的所有候选 Key 都失效（例如 cc-switch 里只剩过期 Key）
        return None

    async def _none_works_multi(candidates):
        return []

    monkeypatch.setattr(credential_probe, "pick_working_candidate", _none_works)
    monkeypatch.setattr(credential_probe, "pick_working_candidates", _none_works_multi)

    resp = client.post("/api/subscription-quota/import/cc-switch", json={}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()

    # 全部候选不可用 → 一条都不写入，并给出原因
    assert body["created"] == 0
    assert {s["providerId"] for s in body["probeSkipped"]} == {"zhipu", "newprov"}
    assert accounts_mod.list_accounts(fake_user) == []


def test_ccswitch_import_reports_probe_skipped_reason(
    fake_user, memory_store, fake_ccswitch, monkeypatch
):
    """所有候选都不可用时要给出明确原因，不能静默消失"""
    from app.services.subscription_quota import credential_probe

    async def _none_works(candidates):
        return None

    async def _none_works_multi(candidates):
        return []

    monkeypatch.setattr(credential_probe, "pick_working_candidate", _none_works)
    monkeypatch.setattr(credential_probe, "pick_working_candidates", _none_works_multi)

    resp = client.post("/api/subscription-quota/import/cc-switch", json={}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert body["probeSkipped"], "必须返回探测失败原因"
    reasons = {s["providerId"]: s["reason"] for s in body["probeSkipped"]}
    assert "zhipu" in reasons and "不可用" in reasons["zhipu"]


def test_edit_account_syncs_extra_api_key(fake_user, memory_store):
    """回归：编辑 Key 必须同步 extra.api_key

    真实缺陷：查询实现读的是 `extra.api_key or api_key`，只改 api_key 字段时
    extra 里的旧值优先级更高，导致「页面显示新 Key、查询仍用旧 Key」。
    """
    account = accounts_mod.create_account(
        fake_user, "zhipu", label="测试", api_key="sk-old-key-0000"
    )

    resp = client.put(
        f"/api/subscription-quota/accounts/{account.id}",
        json={"api_key": "sk-new-key-1111"},
        headers=AUTH,
    )
    assert resp.status_code == 200

    saved = accounts_mod.get_account(fake_user, account.id)
    assert saved is not None
    assert saved.api_key == "sk-new-key-1111"
    # 关键断言：extra 里的副本必须同步，否则查询会用旧 Key
    assert saved.extra.get("api_key") == "sk-new-key-1111"
