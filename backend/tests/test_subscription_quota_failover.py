"""failover / 聚合单测（对照 magpie 的 smart 策略）"""

import pytest

from app.services.subscription_quota.failover import (
    EXHAUSTED_PERCENT,
    aggregate_by_provider,
    pick_primary,
    quota_available,
    rank_accounts,
)
from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.models import CredentialStatus, QuotaTier, SubscriptionQuota


def _account(aid: str, provider: str = "openrouter", order: int = 0) -> QuotaAccount:
    return QuotaAccount(
        id=aid, user_id="u", provider_id=provider, label=aid, sort_order=order
    )


def _quota(remaining: float, reset_iso: str | None = None, ok: bool = True) -> SubscriptionQuota:
    if not ok:
        return SubscriptionQuota.failure("openrouter", CredentialStatus.EXPIRED, "认证失败")
    return SubscriptionQuota(
        tool="openrouter",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[QuotaTier(name="five_hour", utilization=100.0 - remaining, resets_at=reset_iso)],
    )


def test_quota_available():
    assert quota_available(_quota(50)) is True
    assert quota_available(_quota(0)) is False
    assert quota_available(_quota(0.4)) is False
    assert quota_available(_quota(0, ok=False)) is False


def test_quota_available_balance_only_counts_as_available():
    quota = SubscriptionQuota(
        tool="deepseek",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[QuotaTier(name="balance_CNY", utilization=0.0, balance_amount=10.0)],
    )
    assert quota_available(quota) is True


def test_rank_smart_prefers_available_then_earliest_reset():
    pairs = [
        (_account("exhausted"), _quota(0)),
        (_account("later"), _quota(80, "2026-12-01T00:00:00Z")),
        (_account("sooner"), _quota(30, "2026-11-19T00:00:00Z")),
    ]
    ranked = rank_accounts(pairs, "smart")
    assert [p[0].id for p in ranked] == ["sooner", "later", "exhausted"]


def test_rank_order_follows_sort_order():
    pairs = [
        (_account("b", order=2), _quota(90, "2026-11-19T00:00:00Z")),
        (_account("a", order=0), _quota(10)),
    ]
    assert [p[0].id for p in rank_accounts(pairs, "order")] == ["a", "b"]


def test_pick_primary_skips_exhausted():
    pairs = [(_account("exhausted"), _quota(0)), (_account("ok"), _quota(40))]
    primary = pick_primary(pairs)
    assert primary is not None
    assert primary[0].id == "ok"


def test_pick_primary_none_when_all_exhausted():
    pairs = [(_account("a"), _quota(0)), (_account("b"), _quota(0))]
    assert pick_primary(pairs) is None


def test_aggregate_by_provider():
    results = [
        {
            "providerId": "openrouter",
            "accountId": "a1",
            "label": "OpenRouter 主",
            "kind": "balance",
            "success": True,
            "tiers": [
                {"name": "balance_USD", "utilization": 0, "balanceAmount": 5, "balanceUnit": "USD"}
            ],
            "queriedAt": 1,
        },
        {
            "providerId": "kimi",
            "accountId": "a2",
            "label": "Kimi 主",
            "kind": "window",
            "success": True,
            "tiers": [{"name": "five_hour", "utilization": 26, "resetsAt": None}],
            "queriedAt": 2,
        },
        {
            "providerId": "kimi",
            "accountId": "a3",
            "label": "Kimi 备",
            "kind": "window",
            "success": True,
            "tiers": [{"name": "five_hour", "utilization": 90, "resetsAt": None}],
            "queriedAt": 3,
        },
    ]
    agg = {a["providerId"]: a for a in aggregate_by_provider(results)}
    assert agg["kimi"]["accounts"] == 2
    assert agg["kimi"]["isFailoverReady"] is True
    # 剩 74 vs 剩 10 → 最紧张是 10
    assert agg["kimi"]["tightestRemaining"] == pytest.approx(10.0)
    # 推荐剩余更多的 a2
    assert agg["kimi"]["recommendedAccountId"] == "a2"
    assert agg["openrouter"]["accounts"] == 1
    assert agg["openrouter"]["isFailoverReady"] is False
    # 余额型不参与 tightestRemaining
    assert agg["openrouter"]["tightestRemaining"] is None


def test_aggregate_puts_unavailable_last():
    results = [
        {
            "providerId": "zed",
            "accountId": "x",
            "success": False,
            "tiers": [],
            "kind": "window",
            "label": "zed",
        },
        {
            "providerId": "alpha",
            "accountId": "y",
            "success": True,
            "tiers": [{"name": "five_hour", "utilization": 10, "resetsAt": None}],
            "kind": "window",
            "label": "alpha",
        },
    ]
    order = [a["providerId"] for a in aggregate_by_provider(results)]
    assert order == ["alpha", "zed"]


def test_exhausted_threshold_value():
    assert EXHAUSTED_PERCENT == 0.5
