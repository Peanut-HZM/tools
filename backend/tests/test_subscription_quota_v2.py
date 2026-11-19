"""订阅额度 v2 单测

覆盖：注册表完整性、各 provider 解析纯函数、账号加密/掩码。
全部不联网、不读真实凭据。
"""

import json

import pytest

from app.core.security import decrypt_api_key, encrypt_api_key
from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.models import CredentialStatus, QuotaTier, SubscriptionQuota
from app.services.subscription_quota.providers_full import (
    balance_tier,
    parse_command_code_quota,
    parse_deepseek_balance,
    parse_kimi_usages,
    parse_minimax_tiers,
    parse_opencode_go_tiers,
    parse_opendesign_tiers,
    parse_volcengine_tiers,
    parse_zenmux_tiers,
    parse_zhipu_tiers,
)
from app.services.subscription_quota.registry import (
    ALL_PROVIDER_IDS,
    MANUAL_PROVIDER_IDS,
    PROVIDER_SPECS,
    SUBSCRIPTION_IDS,
    get_spec,
)


# ---------------------------------------------------------------- 注册表


def test_registry_has_all_cc_switch_providers():
    """cc-switch 支持的套餐/余额供应商必须全部登记"""
    expected_window = {
        "kimi",
        "zhipu",
        "zhipu_team",
        "minimax",
        "zenmux",
        "opencode_go",
        "command_code",
        "opendesign",
        "volcengine",
    }
    expected_balance = {
        "deepseek",
        "stepfun",
        "siliconflow",
        "openrouter",
        "novita",
        "ollama_cloud",
        "zhipu_payg",
    }
    expected_subscription = {"claude", "codex", "gemini"}

    ids = {spec.id for spec in PROVIDER_SPECS}
    assert expected_window <= ids
    assert expected_balance <= ids
    assert expected_subscription <= ids


def test_registry_specs_are_consistent():
    for spec in PROVIDER_SPECS:
        assert spec.id
        assert spec.name
        # 合并 agent-hub 后新增 manual（手动额度）
        assert spec.kind in ("window", "balance", "subscription", "manual")
        if spec.kind == "subscription":
            assert spec.needs == ()
            assert spec.local_source
        elif spec.kind == "manual":
            # 手动额度不需要任何网络凭据
            assert spec.needs == ()
        else:
            assert len(spec.needs) > 0, f"{spec.id} 需要至少一个凭据字段"


def test_all_provider_ids_unique():
    assert len(ALL_PROVIDER_IDS) == len(set(ALL_PROVIDER_IDS))


def test_subscription_ids_and_manual_ids_partition():
    assert set(SUBSCRIPTION_IDS).isdisjoint(set(MANUAL_PROVIDER_IDS))
    assert set(SUBSCRIPTION_IDS) | set(MANUAL_PROVIDER_IDS) == set(ALL_PROVIDER_IDS)


def test_get_spec():
    spec = get_spec("kimi")
    assert spec is not None
    assert spec.kind == "window"
    assert spec.needs == ("api_key",)

    assert get_spec("nope") is None


def test_opendesign_needs_control_key():
    spec = get_spec("opendesign")
    assert spec is not None
    assert "control_key" in spec.needs


def test_volcengine_needs_ak_sk():
    spec = get_spec("volcengine")
    assert spec is not None
    assert set(spec.needs) == {"access_key", "secret_key"}


# ---------------------------------------------------------------- 手动额度（合并 agent-hub）


def test_manual_provider_needs_nothing():
    spec = get_spec("manual")
    assert spec is not None
    assert spec.kind == "manual"
    assert spec.needs == ()
    assert spec.enabled_by_default is False
    assert "manual" in MANUAL_PROVIDER_IDS


def test_account_is_manual_flag():
    by_provider = QuotaAccount(id="a1", user_id="u1", provider_id="manual")
    assert by_provider.is_manual is True
    by_extra = QuotaAccount(
        id="a2", user_id="u1", provider_id="newapi", extra={"kind": "manual"}
    )
    assert by_extra.is_manual is True
    normal = QuotaAccount(id="a3", user_id="u1", provider_id="kimi", api_key="sk-x")
    assert normal.is_manual is False


@pytest.mark.asyncio
async def test_manual_quota_tier_from_local_numbers():
    """手动额度不联网：直接按 manual_total / manual_used 算利用率"""
    from app.services.subscription_quota.providers_full import query_manual_quota

    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="manual",
        label="手动套餐",
        manual_total=500,
        manual_used=125,
        quota_unit="credits",
    )
    quota = await query_manual_quota(account)
    assert quota.success is True
    assert len(quota.tiers) == 1
    tier = quota.tiers[0]
    assert tier.utilization == pytest.approx(25.0)
    assert tier.balance_amount == pytest.approx(375.0)
    assert tier.balance_unit == "credits"
    assert quota.plan_name == "手动套餐"


@pytest.mark.asyncio
async def test_manual_quota_without_total_is_balance():
    """没有总额度时按余额展示已用（不编造默认总额）"""
    from app.services.subscription_quota.providers_full import query_manual_quota

    account = QuotaAccount(id="a1", user_id="u1", provider_id="manual", manual_used=88)
    quota = await query_manual_quota(account)
    assert quota.success is True
    assert quota.tiers[0].balance_amount == pytest.approx(88.0)


@pytest.mark.asyncio
async def test_manual_account_queried_without_api_key():
    """manual 账号没有 API Key 也必须能查（不能被「未配置 Key」拦下）"""
    from app.services.subscription_quota.service import _query_account

    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="manual",
        label="手动",
        manual_total=100,
        manual_used=10,
    )
    quota = await _query_account(account)
    assert quota.success is True
    assert quota.credential_status == CredentialStatus.VALID


@pytest.mark.asyncio
async def test_normal_account_without_key_still_rejected():
    """普通账号没 Key 仍然如实报「未配置」，不静默放行"""
    from app.services.subscription_quota.service import _query_account

    account = QuotaAccount(id="a1", user_id="u1", provider_id="kimi")
    quota = await _query_account(account)
    assert quota.success is False
    assert quota.credential_status == CredentialStatus.NOT_FOUND


# ---------------------------------------------------------------- 加密与掩码


def test_api_key_roundtrip_encryption():
    plain = "sk-test-1234567890abcdef"
    enc = encrypt_api_key(plain)
    assert enc.startswith("v1:")
    assert plain not in enc
    assert decrypt_api_key(enc) == plain


def test_account_masks_key():
    account = QuotaAccount(
        id="a1", user_id="u1", provider_id="kimi", api_key="sk-abcdefghijklmn"
    )
    masked = account.masked_key()
    assert masked is not None
    assert masked.startswith("sk-a")
    assert masked.endswith("klmn")
    assert "bcdefghij" not in masked


def test_account_public_dict_has_no_plain_key():
    account = QuotaAccount(
        id="a1",
        user_id="u1",
        provider_id="kimi",
        api_key="sk-supersecretvalue123",
        extra={"region": "cn", "secret_key": "hidden"},
    )
    data = account.to_public_dict()
    serialized = json.dumps(data, ensure_ascii=False)
    assert "supersecretvalue" not in serialized
    assert data["hasKey"] is True
    assert data["extra"]["region"] == "cn"
    # extra 中的敏感字段同样被掩码
    assert data["extra"]["secret_key"] == "***"


def test_account_short_key_fully_masked():
    account = QuotaAccount(id="a1", user_id="u1", provider_id="kimi", api_key="abc")
    assert account.masked_key() == "***"


# ---------------------------------------------------------------- Kimi


def test_parse_kimi_usages():
    body = {
        "limits": [
            {
                "detail": {
                    "limit": 1000,
                    "remaining": 740,
                    "resetTime": "2026-11-18T15:03:45.898038Z",
                }
            }
        ],
        "usage": {"limit": 10000, "remaining": 5300, "resetTime": "2026-11-21T03:03:45Z"},
    }
    tiers = {t.name: t for t in parse_kimi_usages(body)}
    assert tiers["five_hour"].utilization == pytest.approx(26.0)
    assert tiers["five_hour"].resets_at == "2026-11-18T15:03:45.898038Z"
    assert tiers["weekly_limit"].utilization == pytest.approx(47.0)


def test_parse_kimi_usages_empty():
    assert parse_kimi_usages({}) == []


# ---------------------------------------------------------------- 智谱


def test_parse_zhipu_tiers_by_unit():
    data = {
        "limits": [
            {"type": "TOKENS_LIMIT", "unit": 3, "percentage": 45.0, "nextResetTime": 1763510400000},
            {"type": "TOKENS_LIMIT", "unit": 6, "percentage": 70.0, "nextResetTime": 1763827200000},
        ]
    }
    tiers = {t.name: t for t in parse_zhipu_tiers(data)}
    assert tiers["five_hour"].utilization == 45.0
    assert tiers["weekly_limit"].utilization == 70.0


def test_parse_zhipu_tiers_fallback():
    data = {
        "limits": [
            {"type": "TOKENS_LIMIT", "percentage": 20.0, "nextResetTime": 1763827200000},
            {"type": "TOKENS_LIMIT", "percentage": 60.0, "nextResetTime": 1763510400000},
        ]
    }
    tiers = parse_zhipu_tiers(data)
    assert tiers[0].name == "five_hour"
    assert tiers[0].utilization == 60.0
    assert tiers[1].name == "weekly_limit"


def test_parse_zhipu_tiers_single_limit():
    data = {"limits": [{"type": "TOKENS_LIMIT", "percentage": 33.0}]}
    tiers = parse_zhipu_tiers(data)
    assert [t.name for t in tiers] == ["five_hour"]


# ---------------------------------------------------------------- MiniMax


def test_parse_minimax_tiers():
    body = {
        "model_remains": [
            {
                "model_name": "general",
                "current_interval_remaining_percent": 40.0,
                "end_time": 1763481600000,
                "current_weekly_status": 1,
                "current_weekly_remaining_percent": 27.0,
                "weekly_end_time": 1763827200000,
            }
        ]
    }
    tiers = {t.name: t for t in parse_minimax_tiers(body)}
    assert tiers["five_hour"].utilization == pytest.approx(60.0)
    assert tiers["weekly_limit"].utilization == pytest.approx(73.0)


def test_parse_minimax_no_weekly_limit():
    body = {
        "model_remains": [
            {
                "model_name": "general",
                "current_interval_remaining_percent": 50.0,
                "current_weekly_status": 3,
                "current_weekly_remaining_percent": 100.0,
            }
        ]
    }
    assert [t.name for t in parse_minimax_tiers(body)] == ["five_hour"]


def test_parse_minimax_ignores_video():
    body = {"model_remains": [{"model_name": "video", "current_interval_remaining_percent": 10}]}
    assert parse_minimax_tiers(body) == []


# ---------------------------------------------------------------- ZenMux


def test_parse_zenmux_tiers():
    data = {
        "quota_5_hour": {"usage_percentage": 0.3, "resets_at": "2026-11-18T15:00:00Z"},
        "quota_7_day": {"usage_percentage": 0.6, "resets_at": "2026-11-21T00:00:00Z"},
        "plan": {"tier": "pro"},
        "account_status": "active",
    }
    tiers = {t.name: t for t in parse_zenmux_tiers(data)}
    assert tiers["five_hour"].utilization == pytest.approx(30.0)
    assert tiers["weekly_limit"].utilization == pytest.approx(60.0)


# ---------------------------------------------------------------- OpenCode Go


def test_parse_opencode_go_tiers():
    body = {
        "usage": {
            "rolling": {"percent": 25, "resetsAt": "2026-11-18T15:00:00Z"},
            "weekly": {"percent": 60, "resetsAt": "2026-11-21T00:00:00Z"},
            "monthly": {"percent": 10, "resetsAt": "2026-12-01T00:00:00Z"},
        }
    }
    tiers = {t.name: t for t in parse_opencode_go_tiers(body)}
    assert tiers["five_hour"].utilization == 25
    assert tiers["weekly_limit"].utilization == 60
    assert tiers["monthly"].utilization == 10


def test_parse_opencode_go_drops_placeholder_reset_at_zero():
    body = {"usage": {"rolling": {"percent": 0, "resetsAt": "2026-11-18T15:00:00Z"}}}
    tiers = parse_opencode_go_tiers(body)
    assert tiers[0].resets_at is None


# ---------------------------------------------------------------- Command Code


def test_parse_command_code_quota():
    credits = {
        "credits": {
            "monthlyCredits": 100,
            "purchasedCredits": 50,
            "freeCredits": 0,
            "windowLimits": {"limited": True, "fiveHour": {"used": 5, "cap": 20}},
        }
    }
    subscription = {"data": {"currentPeriodEnd": "2026-12-01T00:00:00Z"}}
    summary = {"totalCost": 50}
    quota = parse_command_code_quota(credits, subscription, summary)
    assert quota.success is True
    names = [t.name for t in quota.tiers]
    assert "five_hour" in names
    assert "monthly" in names


def test_parse_command_code_quota_missing_credits():
    quota = parse_command_code_quota({}, None, {})
    assert quota.success is False
    assert "credits" in (quota.error or "")


# ---------------------------------------------------------------- OpenDesign


def test_parse_opendesign_tiers():
    body = {
        "designPlanWindows": [
            {"kind": "5h", "limitCredits": "1000", "remainingCredits": "600", "resetsAt": "2026-11-18T15:00:00Z"},
            {"kind": "7d", "limitCredits": "5000", "remainingCredits": "1000", "resetsAt": "2026-11-21T00:00:00Z"},
        ]
    }
    tiers = {t.name: t for t in parse_opendesign_tiers(body)}
    assert tiers["five_hour"].utilization == pytest.approx(40.0)
    assert tiers["weekly_limit"].utilization == pytest.approx(80.0)


def test_parse_opendesign_skips_unknown_kind():
    body = {"designPlanWindows": [{"kind": "30d", "limitCredits": "1", "remainingCredits": "0"}]}
    assert parse_opendesign_tiers(body) == []


def test_parse_opendesign_skips_zero_limit():
    body = {"designPlanWindows": [{"kind": "5h", "limitCredits": "0", "remainingCredits": "0"}]}
    assert parse_opendesign_tiers(body) == []


# ---------------------------------------------------------------- 火山


def test_parse_volcengine_tiers():
    body = {
        "Result": {
            "FiveHour": {"Usage": 20, "Limit": 100, "ResetTime": "2026-11-18T15:00:00Z"},
            "Weekly": {"Usage": 50, "Limit": 200},
        }
    }
    tiers = {t.name: t for t in parse_volcengine_tiers(body)}
    assert tiers["five_hour"].utilization == pytest.approx(20.0)
    assert tiers["weekly_limit"].utilization == pytest.approx(25.0)


def test_parse_volcengine_empty():
    assert parse_volcengine_tiers({}) == []


# ---------------------------------------------------------------- 余额


def test_parse_deepseek_balance():
    body = {
        "balance_infos": [
            {"currency": "CNY", "total_balance": "12.34"},
            {"currency": "USD", "total_balance": "0"},
        ]
    }
    tiers = parse_deepseek_balance(body)
    # 只保留有余额的币种
    assert len(tiers) == 1
    assert tiers[0].balance_unit == "CNY"
    assert tiers[0].balance_amount == pytest.approx(12.34)


def test_balance_tier_carries_amount_and_unit():
    tier = balance_tier("balance_USD", 9.5, "USD")
    data = tier.to_dict()
    assert data["balanceAmount"] == 9.5
    assert data["balanceUnit"] == "USD"
    assert data["utilization"] == 0.0


def test_quota_tier_to_dict_omits_none_balance():
    tier = QuotaTier(name="five_hour", utilization=10.0, resets_at=None)
    data = tier.to_dict()
    assert "balanceAmount" not in data
    assert "balanceUnit" not in data


# ---------------------------------------------------------------- 失败语义


def test_failure_never_fakes_quota():
    quota = SubscriptionQuota.failure("kimi", CredentialStatus.EXPIRED, "认证失败")
    assert quota.success is False
    assert quota.tiers == []
    assert quota.error == "认证失败"


def test_not_found_has_no_tiers():
    quota = SubscriptionQuota.not_found("kimi")
    assert quota.success is False
    assert quota.tiers == []
    assert quota.credential_status == CredentialStatus.NOT_FOUND
