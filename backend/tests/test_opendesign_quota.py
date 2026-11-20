"""OpenDesign 额度查询单测（全部不联网）

覆盖 2026-11-20 这次「OpenDesign 无法显示」的根因修复：

1. 推理 Key（`sk-amr-ew__…`）不能当控制面 Key 用 —— 必须识别并给出明确提示
2. 控制面 Key（`vela_ctrl_…`）才可查询
3. 推理 host（`amr-link.`）要推导成控制面 host（`amr-api.`）
4. `billing/snapshot` 的额度字段是字符串形式的 credits
5. Cloudflare Error 1010（UA 拦截）不能误报成「Key 失效」
6. 控制面 Key 可从本机 cc-switch 库只读发现
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from app.services.subscription_quota import opendesign_key, providers_full
from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.models import CredentialStatus
from app.services.subscription_quota.providers_full import parse_opendesign_tiers

CONTROL_KEY = "vela_ctrl_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
RUNTIME_KEY = "sk-amr-ew__BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


# ---------------------------------------------------------------- Key 形态判定


def test_is_control_key():
    assert opendesign_key.is_control_key(CONTROL_KEY) is True
    assert opendesign_key.is_control_key(RUNTIME_KEY) is False
    assert opendesign_key.is_control_key("") is False
    assert opendesign_key.is_control_key(None) is False


def test_looks_like_runtime_key():
    assert opendesign_key.looks_like_runtime_key(RUNTIME_KEY) is True
    assert opendesign_key.looks_like_runtime_key(CONTROL_KEY) is False
    assert opendesign_key.looks_like_runtime_key(None) is False


# ---------------------------------------------------------------- host 推导


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # 推理 host → 控制面 host（这是最常见的输入形态）
        ("https://amr-link.open-design.ai/v1", "https://amr-api.open-design.ai"),
        ("https://amr-link.open-design.ai", "https://amr-api.open-design.ai"),
        # 已经是控制面 → 原样保留
        ("https://amr-api.open-design.ai", "https://amr-api.open-design.ai"),
        # 空值 / 非 open-design 域名 → 回落官方默认
        ("", "https://amr-api.open-design.ai"),
        ("https://api.example.com", "https://amr-api.open-design.ai"),
        # 伪造后缀不能被认成官方域名
        ("https://open-design.ai.example.com", "https://amr-api.open-design.ai"),
    ],
)
def test_opendesign_api_base(raw, expected):
    assert providers_full._opendesign_api_base(raw) == expected


# ---------------------------------------------------------------- 快照解析


def test_parse_opendesign_tiers_string_credits():
    """实测响应里 limitCredits / remainingCredits 都是字符串"""
    body = {
        "designPlanWindows": [
            {
                "kind": "5h",
                "windowStart": "2026-11-19T20:43:45.967Z",
                "resetsAt": "2026-11-20T01:43:45.967Z",
                "remainingCredits": "48598",
                "limitCredits": "50000",
            },
            {
                "kind": "7d",
                "windowStart": "2026-11-17T11:43:45.967Z",
                "resetsAt": "2026-11-24T11:43:45.967Z",
                "remainingCredits": "102356",
                "limitCredits": "150000",
            },
        ]
    }
    tiers = parse_opendesign_tiers(body)
    assert len(tiers) == 2

    five_hour = next(t for t in tiers if t.name == "five_hour")
    assert five_hour.utilization == pytest.approx((50000 - 48598) / 50000 * 100)
    assert five_hour.resets_at == "2026-11-20T01:43:45.967Z"

    weekly = next(t for t in tiers if t.name == "weekly_limit")
    assert weekly.utilization == pytest.approx((150000 - 102356) / 150000 * 100)


def test_parse_opendesign_tiers_skips_unknown_kind():
    body = {"designPlanWindows": [{"kind": "30d", "limitCredits": "1", "remainingCredits": "0"}]}
    assert parse_opendesign_tiers(body) == []


def test_parse_opendesign_tiers_skips_zero_limit():
    """limitCredits=0 是脏数据，必须跳过（否则除零）"""
    body = {"designPlanWindows": [{"kind": "5h", "limitCredits": "0", "remainingCredits": "0"}]}
    assert parse_opendesign_tiers(body) == []


def test_parse_opendesign_tiers_missing_remaining_treated_as_full():
    body = {"designPlanWindows": [{"kind": "5h", "limitCredits": "50000"}]}
    tiers = parse_opendesign_tiers(body)
    assert len(tiers) == 1
    assert tiers[0].utilization == pytest.approx(0.0)


def test_parse_opendesign_tiers_missing_windows():
    assert parse_opendesign_tiers({}) == []
    assert parse_opendesign_tiers({"designPlanWindows": None}) == []


# ---------------------------------------------------------------- 查询链路


@pytest.fixture
def fake_http(monkeypatch):
    """替换 _request_json，按 URL 返回预设响应"""

    calls: list[str] = []
    responses: dict[str, tuple] = {}

    async def _fake(method, url, headers, **kwargs):
        calls.append(url)
        for fragment, payload in responses.items():
            if fragment in url:
                return payload
        return 404, None, "not found"

    monkeypatch.setattr(providers_full, "_request_json", _fake)
    return {"calls": calls, "responses": responses}


@pytest.mark.asyncio
async def test_query_with_runtime_key_gives_actionable_message(monkeypatch, fake_http):
    """存的是推理 Key → 明确说「账单接口不接受推理 Key」，不拿它去撞接口"""
    monkeypatch.setattr(opendesign_key, "pick_control_key", lambda: None)

    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="opendesign",
        api_key=RUNTIME_KEY,
        extra={"control_key": RUNTIME_KEY, "base_url": "https://amr-link.open-design.ai/v1"},
    )
    quota = await providers_full.query_opendesign(account)

    assert quota.success is False
    assert quota.credential_status == CredentialStatus.EXPIRED
    assert "推理" in quota.credential_message
    assert "controlKey" in quota.credential_message
    # 关键：不该发起任何网络请求
    assert fake_http["calls"] == []


@pytest.mark.asyncio
async def test_query_without_any_key_says_not_configured(monkeypatch, fake_http):
    monkeypatch.setattr(opendesign_key, "pick_control_key", lambda: None)

    account = QuotaAccount(id="a1", user_id="u1", provider_id="opendesign")
    quota = await providers_full.query_opendesign(account)

    assert quota.success is False
    assert quota.credential_status == CredentialStatus.NOT_FOUND
    assert fake_http["calls"] == []


@pytest.mark.asyncio
async def test_query_with_control_key_succeeds(fake_http):
    """控制面 Key + 实测响应结构 → 两个窗口都能解析出来"""
    fake_http["responses"].update(
        {
            "/workspaces/current": (200, {"workspaceId": "ws-123"}, None),
            "/billing/snapshot": (
                200,
                {
                    "plan": {"tier": "go"},
                    "designPlanWindows": [
                        {
                            "kind": "5h",
                            "limitCredits": "50000",
                            "remainingCredits": "48598",
                            "resetsAt": "2026-11-20T01:43:45.967Z",
                        },
                        {
                            "kind": "7d",
                            "limitCredits": "150000",
                            "remainingCredits": "102356",
                            "resetsAt": "2026-11-24T11:43:45.967Z",
                        },
                    ],
                },
                None,
            ),
        }
    )

    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="opendesign",
        api_key="irrelevant",
        extra={"control_key": CONTROL_KEY},
    )
    quota = await providers_full.query_opendesign(account)

    assert quota.success is True
    assert quota.credential_status == CredentialStatus.VALID
    assert len(quota.tiers) == 2
    assert quota.plan_name == "go"
    # 必须打控制面 host，不是推理 host
    assert all(url.startswith("https://amr-api.open-design.ai") for url in fake_http["calls"])
    assert any(url.endswith("/workspaces/ws-123/billing/snapshot") for url in fake_http["calls"])


@pytest.mark.asyncio
async def test_query_falls_back_to_discovered_control_key(monkeypatch, fake_http):
    """账号里只有推理 Key，但本机 cc-switch 有控制面 Key → 自动用它"""
    monkeypatch.setattr(opendesign_key, "pick_control_key", lambda: CONTROL_KEY)
    fake_http["responses"].update(
        {
            "/workspaces/current": (200, {"workspaceId": "ws-9"}, None),
            "/billing/snapshot": (
                200,
                {"designPlanWindows": [{"kind": "5h", "limitCredits": "100", "remainingCredits": "50"}]},
                None,
            ),
        }
    )

    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="opendesign",
        api_key=RUNTIME_KEY,
        extra={"control_key": RUNTIME_KEY},
    )
    quota = await providers_full.query_opendesign(account)
    assert quota.success is True
    assert len(quota.tiers) == 1


@pytest.mark.asyncio
async def test_cloudflare_1010_not_reported_as_expired_key(fake_http):
    """Cloudflare UA 拦截（403 + error-1010）不能误报成 Key 失效"""
    fake_http["responses"]["/workspaces/current"] = (
        403,
        None,
        '{"title":"Error 1010: Access denied","type":".../error-1010/"}',
    )

    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="opendesign",
        api_key=CONTROL_KEY,
        extra={"control_key": CONTROL_KEY},
    )
    quota = await providers_full.query_opendesign(account)

    assert quota.success is False
    # 关键：不是 EXPIRED（否则会让用户白换 Key），而是 VALID + 明确说明是 UA 拦截
    assert quota.credential_status == CredentialStatus.VALID
    assert "Cloudflare" in quota.error or "Cloudflare" in (quota.credential_message or "")
    assert "1010" in quota.error or "1010" in (quota.credential_message or "")


@pytest.mark.asyncio
async def test_real_401_is_reported_as_expired(fake_http):
    fake_http["responses"]["/workspaces/current"] = (401, None, "unauthorized")
    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="opendesign",
        api_key=CONTROL_KEY,
        extra={"control_key": CONTROL_KEY},
    )
    quota = await providers_full.query_opendesign(account)
    assert quota.success is False
    assert quota.credential_status == CredentialStatus.EXPIRED


# ---------------------------------------------------------------- cc-switch 发现


def _make_ccswitch_db(path, providers):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE providers (id TEXT, name TEXT, settings_config TEXT, meta TEXT)")
    conn.executemany(
        "INSERT INTO providers VALUES (?, ?, ?, ?)",
        [
            (p["id"], p["name"], json.dumps(p.get("settings_config") or {}), json.dumps(p.get("meta") or {}))
            for p in providers
        ],
    )
    conn.commit()
    conn.close()


def test_discover_control_keys_from_ccswitch(tmp_path):
    db = tmp_path / "cc-switch.db"
    _make_ccswitch_db(
        db,
        [
            {
                "id": "1",
                "name": "OpenDesign",
                "meta": {"usage_script": {"apiKey": CONTROL_KEY, "codingPlanProvider": "opendesign"}},
            },
            {
                # 推理 Key 必须被过滤掉
                "id": "2",
                "name": "OpenDesign",
                "meta": {"usage_script": {"apiKey": RUNTIME_KEY}},
            },
            {
                # 与 OpenDesign 无关的条目
                "id": "3",
                "name": "Kimi Code",
                "meta": {"usage_script": {"apiKey": "sk-kimi-xxxxxxxxxxxxxxxxxxxx"}},
            },
        ],
    )
    keys = opendesign_key.discover_control_keys(db)
    assert keys == [CONTROL_KEY]


def test_discover_control_keys_matches_by_settings_url(tmp_path):
    """名字里没写 opendesign，但配置里有 open-design.ai 域名也要认出来"""
    db = tmp_path / "cc-switch.db"
    _make_ccswitch_db(
        db,
        [
            {
                "id": "1",
                "name": "我的中转",
                "settings_config": {"options": {"baseURL": "https://amr-link.open-design.ai/v1"}},
                "meta": {"usage_script": {"apiKey": CONTROL_KEY}},
            }
        ],
    )
    assert opendesign_key.discover_control_keys(db) == [CONTROL_KEY]


def test_discover_control_keys_missing_db(tmp_path):
    assert opendesign_key.discover_control_keys(tmp_path / "nope.db") == []


def test_discover_control_keys_broken_db(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("not a sqlite file", encoding="utf-8")
    assert opendesign_key.discover_control_keys(bad) == []


def test_resolve_control_key_prefers_explicit(monkeypatch):
    monkeypatch.setattr(opendesign_key, "pick_control_key", lambda: "vela_ctrl_discovered")
    key, source = opendesign_key.resolve_control_key(CONTROL_KEY, RUNTIME_KEY)
    assert key == CONTROL_KEY
    assert source == "explicit"


def test_resolve_control_key_skips_runtime_key(monkeypatch):
    """候选里全是推理 Key → 去 cc-switch 找，绝不用推理 Key"""
    monkeypatch.setattr(opendesign_key, "pick_control_key", lambda: "vela_ctrl_from_ccswitch")
    key, source = opendesign_key.resolve_control_key(RUNTIME_KEY, "")
    assert key == "vela_ctrl_from_ccswitch"
    assert source == "cc-switch"


def test_resolve_control_key_none_found(monkeypatch):
    monkeypatch.setattr(opendesign_key, "pick_control_key", lambda: None)
    key, source = opendesign_key.resolve_control_key(RUNTIME_KEY, None)
    assert key is None
    assert source == ""
