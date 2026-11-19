"""magpie 同步单测 — 只读解析 + 路由导入逻辑

覆盖：
* providers.json 解析与 preset 映射（含不可映射项如实跳过）
* Key 脱敏
* magpie 未安装时如实返回空（不编造）
* `/import/magpie` 的 create / skip / dry-run 三种行为
* 默认不覆盖用户已有数据

全部不联网、不读真实凭据（用临时目录 + 假 providers.json）。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.subscription_quota import magpie_sync

client = TestClient(app)


@pytest.fixture
def magpie_dir(tmp_path, monkeypatch):
    """把 magpie 配置目录指到临时目录"""
    d = tmp_path / "magpie"
    d.mkdir()
    monkeypatch.setenv("MAGPIE_CONFIG_DIR", str(d))
    return d


def _write_providers(directory, providers):
    (directory / "providers.json").write_text(
        json.dumps({"providers": providers}, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------- providers.json


def test_load_providers_missing_file_returns_empty(magpie_dir):
    assert magpie_sync.load_providers() == []


def test_load_providers_maps_preset_to_provider_id(magpie_dir):
    _write_providers(
        magpie_dir,
        [
            {
                "id": "kimi",
                "name": "Kimi Code",
                "preset": "kimi",
                "key": "sk-kimi-1234567890abcdef",
                "chat": "https://api.kimi.com/coding/v1",
                "website": "https://kimi.example",
            },
            {
                "id": "zhipu",
                "name": "Zhipu GLM",
                "preset": "zhipu",
                "key": "6327abcdef1234567890",
                "chat": "https://open.bigmodel.cn/api/coding/paas/v4",
            },
        ],
    )

    providers = magpie_sync.load_providers()
    assert len(providers) == 2

    kimi = next(p for p in providers if p.id == "kimi")
    assert kimi.provider_id == "kimi"
    assert kimi.base_url == "https://api.kimi.com/coding/v1"
    assert kimi.website == "https://kimi.example"
    # 脱敏：不能出现完整 Key
    masked = kimi.masked_key()
    assert "1234567890abcdef" not in masked
    assert masked.startswith("sk-kim")


def test_load_providers_unmappable_preset_returns_none(magpie_dir):
    _write_providers(
        magpie_dir,
        [{"id": "weird", "name": "Unknown Vendor", "preset": "totally-unknown", "key": "xyz"}],
    )
    providers = magpie_sync.load_providers()
    assert len(providers) == 1
    assert providers[0].provider_id is None


def test_load_providers_generic_balance_fallback(magpie_dir):
    """magpie 认识但本工具只有通用余额查询器的供应商 → generic_balance"""
    _write_providers(
        magpie_dir,
        [{"id": "groq", "name": "Groq", "preset": "groq", "key": "gsk_1234567890abcdef"}],
    )
    providers = magpie_sync.load_providers()
    assert providers[0].provider_id == "generic_balance"


def test_load_providers_broken_json_returns_empty(magpie_dir):
    (magpie_dir / "providers.json").write_text("{not json", encoding="utf-8")
    assert magpie_sync.load_providers() == []


def test_load_accounts_without_binary_returns_empty(monkeypatch):
    """magpie 未安装时如实返回空，不编造账号"""
    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: None)
    assert magpie_sync.load_accounts() == []


def test_magpie_available_reflects_files(magpie_dir, monkeypatch):
    # 本机可能真装了 magpie，这里只验证「providers.json 文件」这一判据，
    # 把 CLI 探测打桩掉，测试不依赖宿主环境。
    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: None)
    assert magpie_sync.providers_json_path().exists() is False
    assert magpie_sync.magpie_available() is False
    _write_providers(magpie_dir, [])
    assert magpie_sync.magpie_available() is True


def test_magpie_available_with_binary_but_no_file(magpie_dir, monkeypatch):
    """只装了 CLI、还没配 providers.json 也算可用（accounts 仍能读）"""
    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: "/fake/magpie")
    assert magpie_sync.providers_json_path().exists() is False
    assert magpie_sync.magpie_available() is True


# ---------------------------------------------------------------- 路由导入


@pytest.fixture
def import_env(monkeypatch, magpie_dir):
    """路由导入单测：内存账号表 + 假 magpie 数据"""
    import uuid

    from app.routes import subscription_quota as route_module
    from app.services.subscription_quota import accounts as accounts_mod

    monkeypatch.setattr(route_module, "_require_user", lambda authorization: "test-user")
    monkeypatch.setattr(route_module, "clear_cache", lambda: None)

    store: dict = {}

    def _create(user_id, provider_id, *, label="", api_key=None, extra=None, **kwargs):
        account = accounts_mod.QuotaAccount(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider_id=provider_id,
            label=label,
            api_key=api_key,
            extra=dict(extra or {}),
            enabled=True,
            **{
                k: kwargs[k]
                for k in ("category", "app", "notes", "website_url", "manual_total",
                          "manual_used", "quota_unit", "window_type", "window_reset_at")
                if k in kwargs
            },
        )
        store[account.id] = account
        return account

    def _update(user_id, aid, **kwargs):
        account = store.get(aid)
        if account is None:
            return None
        for field in ("label", "api_key", "extra", "enabled", "category", "notes",
                      "website_url", "manual_total", "manual_used", "quota_unit",
                      "window_type", "window_reset_at"):
            if kwargs.get(field) is not None:
                setattr(account, field, kwargs[field])
        return account

    for module in (accounts_mod, route_module):
        monkeypatch.setattr(module, "create_account", _create)
        monkeypatch.setattr(module, "list_accounts", lambda user_id, only_enabled=False: list(store.values()))
        monkeypatch.setattr(module, "update_account", _update)

    return store


AUTH = {"Authorization": "Bearer x"}


@pytest.mark.asyncio
async def test_import_magpie_creates_mappable_providers(import_env, magpie_dir):
    _write_providers(
        magpie_dir,
        [
            {"id": "kimi", "name": "Kimi Code", "preset": "kimi", "key": "sk-kimi-1234567890abcdef"},
            {"id": "groq", "name": "Groq", "preset": "groq", "key": "gsk_1234567890abcdef"},
            {"id": "weird", "name": "Weird", "preset": "nope", "key": "zzz"},
        ],
    )

    resp = client.post(
        "/api/subscription-quota/import/magpie",
        json={"include_accounts": False},
        headers=AUTH,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["created"] == 2  # kimi + groq(generic_balance)
    assert data["skipped"] == 0
    # 不可映射的那条要出现在 skippedItems 里并带原因
    assert len(data["skippedItems"]) == 1
    assert data["skippedItems"][0]["name"] == "Weird"
    assert "没有对应的供应商类型" in data["skippedItems"][0]["reason"]

    provider_ids = {a.provider_id for a in import_env.values()}
    assert provider_ids == {"kimi", "generic_balance"}


@pytest.mark.asyncio
async def test_import_magpie_dry_run_writes_nothing(import_env, magpie_dir):
    _write_providers(
        magpie_dir,
        [{"id": "kimi", "name": "Kimi Code", "preset": "kimi", "key": "sk-kimi-1234567890abcdef"}],
    )
    resp = client.post(
        "/api/subscription-quota/import/magpie",
        json={"dry_run": True, "include_accounts": False},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["dryRun"] is True
    assert resp.json()["imported"] == 0
    assert import_env == {}


@pytest.mark.asyncio
async def test_import_magpie_never_overwrites_existing(import_env, magpie_dir):
    """已存在的账号默认整条跳过：用户的 label / 手工额度不能被 magpie 冲掉"""
    from app.services.subscription_quota.accounts import create_account

    existing = create_account(
        "test-user",
        "kimi",
        label="我自己的名字",
        api_key="sk-user-key-000000000",
        manual_total=999,
    )

    _write_providers(
        magpie_dir,
        [{"id": "kimi", "name": "Kimi Code", "preset": "kimi", "key": "sk-magpie-key-111111"}],
    )

    resp = client.post(
        "/api/subscription-quota/import/magpie",
        json={"include_accounts": False},
        headers=AUTH,
    )
    data = resp.json()
    assert data["skipped"] == 1
    assert data["created"] == 0

    kept = import_env[existing.id]
    assert kept.label == "我自己的名字"
    assert kept.api_key == "sk-user-key-000000000"
    assert kept.manual_total == 999


@pytest.mark.asyncio
async def test_import_magpie_empty_returns_message(import_env, magpie_dir, monkeypatch):
    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: None)
    resp = client.post(
        "/api/subscription-quota/import/magpie",
        json={"include_accounts": False},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 0
    assert "没有可同步" in resp.json()["message"]


@pytest.mark.asyncio
async def test_magpie_status_reports_paths(import_env, magpie_dir):
    resp = client.get("/api/subscription-quota/magpie/status", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["providersPath"].endswith("providers.json")
    assert resp.json()["providersFileExists"] is False


# ---------------------------------------------------------------- 订阅账号分支
# 本机 magpie 目前没有 OAuth 订阅账号（各 agent 用的是 API-key provider），
# `magpie accounts --json` 输出 []，所以这条分支只能靠单测覆盖。


def test_load_accounts_parses_json(monkeypatch):
    """accounts --json 的真实结构要能解析成 MagpieAccount"""
    payload = json.dumps(
        [
            {
                "agent": "claude",
                "user": "me@example.com",
                "plan": "Max",
                "active": True,
                "on": True,
                "alias": "工作号",
                "windows": [
                    {"name": "5h", "used": 42.5, "remaining": 57.5, "resetsAt": "2026-11-20T05:00:00Z"},
                    {"name": "weekly", "used": 10, "remaining": 90},
                ],
                "balance": "",
                "readAt": "2026-11-20T00:00:00Z",
            }
        ],
        ensure_ascii=False,
    )

    class FakeProc:
        returncode = 0
        stdout = payload
        stderr = ""

    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: "/fake/magpie")
    monkeypatch.setattr(
        magpie_sync.subprocess, "run", lambda *a, **kw: FakeProc()
    )

    accounts = magpie_sync.load_accounts()
    assert len(accounts) == 1
    acc = accounts[0]
    assert acc.agent == "claude"
    assert acc.user == "me@example.com"
    assert acc.plan == "Max"
    assert acc.active is True
    assert acc.alias == "工作号"
    assert len(acc.windows) == 2
    assert acc.windows[0]["name"] == "5h"
    assert acc.windows[0]["used"] == 42.5


def test_load_accounts_ignores_nonzero_exit(monkeypatch):
    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: "/fake/magpie")
    monkeypatch.setattr(magpie_sync.subprocess, "run", lambda *a, **kw: FakeProc())
    assert magpie_sync.load_accounts() == []


def test_load_accounts_ignores_broken_json(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = "{not json"
        stderr = ""

    monkeypatch.setattr(magpie_sync, "find_magpie_binary", lambda: "/fake/magpie")
    monkeypatch.setattr(magpie_sync.subprocess, "run", lambda *a, **kw: FakeProc())
    assert magpie_sync.load_accounts() == []


@pytest.mark.asyncio
async def test_import_magpie_syncs_subscription_accounts(import_env, magpie_dir, monkeypatch):
    """订阅账号分支：claude 账号建出来，label 带 alias+plan，窗口写进 extra"""
    from app.services.subscription_quota.magpie_sync import MagpieAccount

    monkeypatch.setattr(
        magpie_sync,
        "load_accounts",
        lambda timeout=45: [
            MagpieAccount(
                agent="claude",
                user="me@example.com",
                plan="Max",
                active=True,
                alias="工作号",
                windows=[{"name": "5h", "used": 42.5, "remaining": 57.5}],
            )
        ],
    )
    _write_providers(magpie_dir, [])

    resp = client.post(
        "/api/subscription-quota/import/magpie",
        json={"include_accounts": True},
        headers=AUTH,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["created"] == 1

    acc = next(a for a in import_env.values() if a.provider_id == "claude")
    assert acc.label == "工作号 · Max"
    assert acc.category == "official"
    assert acc.extra["source"] == "magpie"
    assert acc.extra["agent"] == "claude"
    assert acc.extra["user"] == "me@example.com"
    assert acc.extra["windows"][0]["name"] == "5h"
    # 订阅账号靠本机登录，不该写入任何 API Key
    assert not acc.api_key


@pytest.mark.asyncio
async def test_import_magpie_unsupported_account_agent_goes_to_skipped(
    import_env, magpie_dir, monkeypatch
):
    """copilot 之类不是本工具支持的官方订阅 → 进 skippedItems，不静默丢"""
    from app.services.subscription_quota.magpie_sync import MagpieAccount

    monkeypatch.setattr(
        magpie_sync,
        "load_accounts",
        lambda timeout=45: [MagpieAccount(agent="copilot", user="gh@example.com")],
    )
    _write_providers(magpie_dir, [])

    resp = client.post(
        "/api/subscription-quota/import/magpie",
        json={"include_accounts": True},
        headers=AUTH,
    )
    data = resp.json()
    assert data["created"] == 0
    assert len(data["skippedItems"]) == 1
    assert data["skippedItems"][0]["source"] == "magpie-account"
    assert "copilot" in data["skippedItems"][0]["reason"]
