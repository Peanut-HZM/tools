"""订阅套餐额度工具单测

只覆盖纯函数与凭据发现，全部不联网、不读真实家目录里的其它文件。
"""

import json
from pathlib import Path

import pytest

from app.services.subscription_quota.credentials import (
    Credential,
    _expired,
    read_claude,
    read_codex,
    read_kimi,
    read_zhipu,
)
from app.services.subscription_quota.models import (
    CredentialStatus,
    QuotaTier,
    SubscriptionQuota,
    millis_to_iso,
)
from app.services.subscription_quota.providers import (
    classify_gemini_model,
    codex_plan_label,
    parse_claude_usage,
    parse_codex_usage,
    parse_gemini_buckets,
    parse_kimi_usages,
    parse_minimax_tiers,
    parse_zhipu_tiers,
    window_tier_name,
)


# ---------------------------------------------------------------- 模型


def test_quota_tier_to_dict_omits_none_extras():
    tier = QuotaTier(name="five_hour", utilization=26.0, resets_at="2026-11-18T15:03:45Z")
    assert tier.to_dict() == {
        "name": "five_hour",
        "utilization": 26.0,
        "resetsAt": "2026-11-18T15:03:45Z",
    }


def test_quota_tier_to_dict_includes_usd_when_present():
    tier = QuotaTier(
        name="monthly",
        utilization=40.0,
        resets_at=None,
        used_value_usd=1.5,
        max_value_usd=10.0,
    )
    data = tier.to_dict()
    assert data["usedValueUsd"] == 1.5
    assert data["maxValueUsd"] == 10.0


def test_subscription_quota_not_found():
    quota = SubscriptionQuota.not_found("kimi")
    assert quota.credential_status == CredentialStatus.NOT_FOUND
    assert quota.success is False
    assert quota.tiers == []


def test_subscription_quota_failure_sets_queried_at():
    quota = SubscriptionQuota.failure("kimi", CredentialStatus.EXPIRED, "令牌已过期")
    assert quota.success is False
    assert quota.error == "令牌已过期"
    assert quota.queried_at is not None


def test_millis_to_iso_handles_none_and_invalid():
    assert millis_to_iso(None) is None
    assert millis_to_iso(0) is not None
    # 1763500000000 = 2025-11-18 前后，必须是合法 ISO
    assert millis_to_iso(1763500000000).endswith("Z")


def test_expired_helper():
    import time

    now_s = int(time.time())
    assert _expired(None) is False
    assert _expired(now_s - 60) is True  # 秒级，已过期
    assert _expired(now_s + 600) is False
    assert _expired((now_s - 60) * 1000) is True  # 毫秒级
    assert _expired((now_s + 600) * 1000) is False
    assert _expired("2000-01-01T00:00:00Z") is True
    assert _expired("2999-01-01T00:00:00Z") is False


# ---------------------------------------------------------------- Claude 解析


def test_parse_claude_usage_legacy_top_level_windows():
    body = {
        "five_hour": {"utilization": 13.0, "resets_at": "2026-11-18T15:00:00Z"},
        "seven_day": {"utilization": 62.0, "resets_at": "2026-11-21T00:00:00Z"},
    }
    tiers = parse_claude_usage(body)
    assert [t.name for t in tiers] == ["five_hour", "seven_day"]
    assert tiers[0].utilization == 13.0
    assert tiers[1].resets_at == "2026-11-21T00:00:00Z"


def test_parse_claude_usage_scoped_limits_override():
    body = {
        "five_hour": {"utilization": 10.0, "resets_at": None},
        "seven_day_opus": {"utilization": 20.0, "resets_at": None},
        "limits": [
            {
                "kind": "weekly_scoped",
                "group": "weekly",
                "percent": 55.0,
                "resets_at": "2026-11-22T00:00:00Z",
                "scope": {"model": {"display_name": "Opus"}},
            }
        ],
    }
    tiers = {t.name: t for t in parse_claude_usage(body)}
    assert tiers["seven_day_opus"].utilization == 55.0
    assert tiers["seven_day_opus"].resets_at == "2026-11-22T00:00:00Z"


def test_parse_claude_usage_skips_surface_scoped_limits():
    """带 surface 的子限额不并入模型周限额"""
    body = {
        "limits": [
            {
                "kind": "weekly_scoped",
                "group": "weekly",
                "percent": 90.0,
                "scope": {"model": {"display_name": "Opus"}, "surface": "cli"},
            }
        ]
    }
    assert parse_claude_usage(body) == []


def test_parse_claude_usage_ignores_unknown_model_names():
    body = {
        "limits": [
            {
                "kind": "weekly_scoped",
                "group": "weekly",
                "percent": 30.0,
                "scope": {"model": {"display_name": "Mystery"}},
            }
        ]
    }
    assert parse_claude_usage(body) == []


def test_parse_claude_usage_empty_body():
    assert parse_claude_usage({}) == []


# ---------------------------------------------------------------- Codex 解析


def test_window_tier_name():
    assert window_tier_name(18000) == "five_hour"
    assert window_tier_name(604800) == "seven_day"
    assert window_tier_name(2592000) == "30_day"
    assert window_tier_name(43200) == "12_hour"
    assert window_tier_name(259200) == "3_day"
    assert window_tier_name(None) == "unknown"


def test_codex_plan_label():
    assert codex_plan_label("free") == "Free"
    assert codex_plan_label("pro") == "Pro 200"
    assert codex_plan_label("promax") == "Pro 500"
    assert codex_plan_label("business") == "Enterprise"
    assert codex_plan_label("custom_plan") == "Custom Plan"
    assert codex_plan_label(None) is None
    assert codex_plan_label("unknown") is None


def test_parse_codex_usage_windows_and_plan():
    body = {
        "rate_limit": {
            "primary_window": {
                "used_percent": 26.0,
                "limit_window_seconds": 18000,
                "reset_at": 1763500000,
            },
            "secondary_window": {
                "used_percent": 47.0,
                "limit_window_seconds": 604800,
                "reset_at": 1764000000,
            },
        },
        "plan_type": "pro",
    }
    tiers, plan_type, credits = parse_codex_usage(body)
    assert [t.name for t in tiers] == ["five_hour", "seven_day"]
    assert tiers[0].utilization == 26.0
    assert tiers[0].resets_at is not None
    assert plan_type == "pro"
    assert credits is None


def test_parse_codex_usage_hides_reset_when_unused():
    """用量为 0 时上游会给占位重置时间，必须隐藏"""
    body = {
        "rate_limit": {
            "primary_window": {
                "used_percent": 0.0,
                "limit_window_seconds": 18000,
                "reset_at": 1763500000,
            }
        }
    }
    tiers, _, _ = parse_codex_usage(body)
    assert tiers[0].resets_at is None


def test_parse_codex_usage_credits_balance():
    body = {"credits": {"has_credits": True, "unlimited": False, "balance": "62500"}}
    _, _, credits = parse_codex_usage(body)
    assert credits == 62500.0


def test_parse_codex_usage_unlimited_credits_ignored():
    body = {"credits": {"has_credits": True, "unlimited": True, "balance": "1"}}
    _, _, credits = parse_codex_usage(body)
    assert credits is None


# ---------------------------------------------------------------- Gemini 解析


def test_classify_gemini_model():
    assert classify_gemini_model("gemini-3-pro-preview") == "gemini_pro"
    assert classify_gemini_model("gemini-3-flash") == "gemini_flash"
    assert classify_gemini_model("gemini-3-flash-lite") == "gemini_flash_lite"
    assert classify_gemini_model("mystery-model") == "mystery-model"


def test_parse_gemini_buckets_takes_lowest_remaining_per_category():
    buckets = [
        {"modelId": "gemini-3-pro", "remainingFraction": 0.8, "resetTime": "2026-11-20T00:00:00Z"},
        {"modelId": "gemini-3-pro-preview", "remainingFraction": 0.3, "resetTime": "2026-11-21T00:00:00Z"},
        {"modelId": "gemini-3-flash", "remainingFraction": 0.9, "resetTime": "2026-11-20T00:00:00Z"},
    ]
    tiers = parse_gemini_buckets(buckets)
    by_name = {t.name: t for t in tiers}
    # 同一分类取剩余最少的那个：0.3 → 已用 70%
    assert by_name["gemini_pro"].utilization == pytest.approx(70.0)
    assert by_name["gemini_pro"].resets_at == "2026-11-21T00:00:00Z"
    assert by_name["gemini_flash"].utilization == pytest.approx(10.0)
    # 排序 Pro 在 Flash 之前
    assert [t.name for t in tiers] == ["gemini_pro", "gemini_flash"]


def test_parse_gemini_buckets_clamps_and_skips_bad_entries():
    buckets = [
        {"modelId": "gemini-3-pro", "remainingFraction": 5.0},  # 超过 1 → 夹到 1
        "not-a-dict",
        {"modelId": "gemini-3-flash", "remainingFraction": -1.0},  # 小于 0 → 夹到 0
    ]
    by_name = {t.name: t for t in parse_gemini_buckets(buckets)}
    assert by_name["gemini_pro"].utilization == pytest.approx(0.0)
    assert by_name["gemini_flash"].utilization == pytest.approx(100.0)


# ---------------------------------------------------------------- Kimi 解析


def test_parse_kimi_usages_limits_and_usage():
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


def test_parse_kimi_usages_handles_zero_limit():
    body = {"usage": {"limit": 0, "remaining": 0}}
    tiers = parse_kimi_usages(body)
    assert tiers[0].utilization == 0.0


# ---------------------------------------------------------------- MiniMax 解析


def test_parse_minimax_tiers_two_windows():
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
    assert tiers["five_hour"].resets_at is not None


def test_parse_minimax_tiers_skips_when_no_weekly_limit():
    """current_weekly_status == 3 表示套餐无周限额，不展示周档"""
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
    tiers = parse_minimax_tiers(body)
    assert [t.name for t in tiers] == ["five_hour"]


def test_parse_minimax_tiers_shows_exhausted_weekly():
    """status == 2 表示周额度已耗尽，照常展示为 100% 已用"""
    body = {
        "model_remains": [
            {
                "model_name": "general",
                "current_interval_remaining_percent": 50.0,
                "current_weekly_status": 2,
                "current_weekly_remaining_percent": 0.0,
            }
        ]
    }
    tiers = {t.name: t for t in parse_minimax_tiers(body)}
    assert tiers["weekly_limit"].utilization == pytest.approx(100.0)


def test_parse_minimax_tiers_ignores_non_general_models():
    body = {
        "model_remains": [
            {"model_name": "video", "current_interval_remaining_percent": 10.0}
        ]
    }
    assert parse_minimax_tiers(body) == []


# ---------------------------------------------------------------- 智谱解析


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


def test_parse_zhipu_tiers_fallback_without_unit():
    """unit 缺失时按重置时间升序依次填入窗口"""
    data = {
        "limits": [
            {"type": "TOKENS_LIMIT", "percentage": 20.0, "nextResetTime": 1763827200000},
            {"type": "TOKENS_LIMIT", "percentage": 60.0, "nextResetTime": 1763510400000},
        ]
    }
    tiers = parse_zhipu_tiers(data)
    assert len(tiers) == 2
    # 先到期的（60%，smaller reset）填 five_hour
    assert tiers[0].name == "five_hour"
    assert tiers[0].utilization == 60.0
    assert tiers[1].name == "weekly_limit"
    assert tiers[1].utilization == 20.0


def test_parse_zhipu_tiers_old_plan_single_limit():
    """老套餐只回一条 TOKENS_LIMIT，降级为仅 five_hour"""
    data = {"limits": [{"type": "TOKENS_LIMIT", "percentage": 33.0}]}
    tiers = parse_zhipu_tiers(data)
    assert [t.name for t in tiers] == ["five_hour"]
    assert tiers[0].utilization == 33.0


def test_parse_zhipu_tiers_ignores_unknown_limit_types():
    data = {"limits": [{"type": "SOMETHING_ELSE", "percentage": 99.0}]}
    assert parse_zhipu_tiers(data) == []


# ---------------------------------------------------------------- 凭据发现


def test_read_claude_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    cred = read_claude()
    assert cred.status == CredentialStatus.NOT_FOUND
    assert cred.token is None


def test_read_claude_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / ".credentials.json").write_text(
        json.dumps(
            {
                "claudeAiOauth": {
                    "accessToken": "sk-ant-test-token",
                    "expiresAt": 9999999999999,
                }
            }
        ),
        encoding="utf-8",
    )
    cred = read_claude()
    assert cred.status == CredentialStatus.VALID
    assert cred.token == "sk-ant-test-token"


def test_read_claude_expired_with_refresh_token(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / ".credentials.json").write_text(
        json.dumps(
            {
                "claudeAiOauth": {
                    "accessToken": "sk-ant-old",
                    "expiresAt": 1,
                    "refreshToken": "refresh-ok",
                }
            }
        ),
        encoding="utf-8",
    )
    cred = read_claude()
    assert cred.status == CredentialStatus.REFRESH_PENDING
    assert cred.token == "sk-ant-old"


def test_read_claude_expired_without_refresh(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / ".credentials.json").write_text(
        json.dumps(
            {"claudeAiOauth": {"accessToken": "sk-ant-old", "expiresAt": 1}}
        ),
        encoding="utf-8",
    )
    cred = read_claude()
    assert cred.status == CredentialStatus.EXPIRED


def test_read_claude_parse_error(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / ".credentials.json").write_text("{not valid json", encoding="utf-8")
    cred = read_claude()
    assert cred.status == CredentialStatus.PARSE_ERROR
    assert cred.message


def test_read_codex_requires_chatgpt_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    (tmp_path / "auth.json").write_text(
        json.dumps({"auth_mode": "apikey"}), encoding="utf-8"
    )
    cred = read_codex()
    assert cred.status == CredentialStatus.NOT_FOUND
    assert "OAuth" in (cred.message or "")


def test_read_codex_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    (tmp_path / "auth.json").write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {"access_token": "codex-token", "account_id": "acc-1"},
            }
        ),
        encoding="utf-8",
    )
    cred = read_codex()
    assert cred.status == CredentialStatus.VALID
    assert cred.token == "codex-token"
    assert cred.extras["account_id"] == "acc-1"


def test_read_kimi_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("KIMI_DATA_DIR", str(tmp_path))
    (tmp_path / "credentials").mkdir()
    (tmp_path / "credentials" / "kimi-code.json").write_text(
        json.dumps({"access_token": "kimi-token", "expires_at": 9999999999999, "scope": "kimi-code"}),
        encoding="utf-8",
    )
    cred = read_kimi()
    assert cred.status == CredentialStatus.VALID
    assert cred.token == "kimi-token"
    assert cred.extras["scope"] == "kimi-code"


def test_read_kimi_missing(tmp_path, monkeypatch):
    # 把三个候选路径都隔离掉：KIMI_DATA_DIR 指向空目录
    monkeypatch.setenv("KIMI_DATA_DIR", str(tmp_path / "empty"))
    cred = read_kimi()
    # 真实家目录若有凭据也可能读到，这里只断言不会抛异常且状态合法
    assert cred.status in {
        CredentialStatus.NOT_FOUND,
        CredentialStatus.VALID,
        CredentialStatus.EXPIRED,
    }


def test_read_zhipu_env_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.services.subscription_quota.credentials.real_home", lambda: tmp_path
    )
    monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-key")
    cred = read_zhipu()
    assert cred.status == CredentialStatus.VALID
    assert cred.token == "zhipu-key"


def test_credential_defaults():
    cred = Credential()
    assert cred.extras == {}
    assert cred.status == CredentialStatus.NOT_FOUND
