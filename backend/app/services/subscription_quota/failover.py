"""多账号 failover 与额度聚合（对照 magpie 的 quota / 账号切换能力）

magpie 的核心能力之一是「同一个 provider 配多个账号，配额用完自动切下一个」。
本模块在**只读查询**的边界内实现同等效果：

* **账号分组**：同一 provider_id 下的多个账号按 sort_order 排序
* **primary 选择**：优先选「还有额度」且「最早重置」的账号（magpie `smart` 策略）
* **failover**：primary 查询失败或额度耗尽时，依次尝试同组其它账号，直到成功
* **聚合视图**：按 provider 汇总，给出「总计可用 / 最紧张 / 推荐使用哪个账号」

不做的事情（明确边界，见文档）：
* 不实现本地网关（127.0.0.1:3425）——本工具是查询面板，不是代理
* 不改写任何 CLI 配置文件——不做「切换 agent 用哪个模型」
* 不做定时 warm-up——不触发真实请求去消耗/开启额度窗口
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.models import QuotaTier, SubscriptionQuota

logger = logging.getLogger(__name__)

#: 判定「额度耗尽」的阈值（剩余 <= 该值视为用完）
EXHAUSTED_PERCENT = 0.5

#: failover 策略
STRATEGIES = ("smart", "order")


def _remaining_of(quota: SubscriptionQuota) -> Optional[float]:
    """返回该账号所有窗口里**最小**的剩余百分比；余额型返回 None。

    None 表示「不适用」，调用方应视为可用。
    """
    window_tiers: list[QuotaTier] = [
        t for t in quota.tiers if t.balance_amount is None and t.name != "failed"
    ]
    if not window_tiers:
        return None
    return min(max(0.0, 100.0 - t.utilization) for t in window_tiers)


def _earliest_reset(quota: SubscriptionQuota) -> float:
    """最早的重置时间戳（毫秒）；没有则返回无穷大。"""
    from datetime import datetime

    best = float("inf")
    for tier in quota.tiers:
        if not tier.resets_at:
            continue
        try:
            ts = datetime.fromisoformat(tier.resets_at.replace("Z", "+00:00")).timestamp() * 1000
        except ValueError:
            continue
        best = min(best, ts)
    return best


def quota_available(quota: SubscriptionQuota) -> bool:
    """该账号当前是否还能用（查询成功且没有窗口耗尽）"""
    if not quota.success:
        return False
    remaining = _remaining_of(quota)
    if remaining is None:
        return True
    return remaining > EXHAUSTED_PERCENT


def rank_accounts(
    candidates: Iterable[tuple[QuotaAccount, SubscriptionQuota]],
    strategy: str = "smart",
) -> list[tuple[QuotaAccount, SubscriptionQuota]]:
    """按策略给同组账号排序。

    * ``smart``：可用优先 → 最早重置优先（magpie 的 smart）
    * ``order``：完全按 sort_order（用户配置顺序）
    """
    items = list(candidates)
    if strategy == "order":
        return sorted(items, key=lambda pair: (pair[0].sort_order, pair[0].id))

    return sorted(
        items,
        key=lambda pair: (
            not quota_available(pair[1]),  # 可用的排前面
            _earliest_reset(pair[1]),  # 最早重置的排前面
            pair[0].sort_order,
        ),
    )


def pick_primary(
    candidates: list[tuple[QuotaAccount, SubscriptionQuota]],
    strategy: str = "smart",
) -> Optional[tuple[QuotaAccount, SubscriptionQuota]]:
    """选出推荐账号（有额度且最早重置）。"""
    for pair in rank_accounts(candidates, strategy):
        if quota_available(pair[1]):
            return pair
    return None


def aggregate_by_provider(results: list[dict]) -> list[dict]:
    """把逐账号结果聚合成按 provider 的视图（magpie quota 的聚合口径）。

    每个 provider 返回：

    * ``accounts``：该 provider 下的账号数
    * ``available``：还能用的账号数
    * ``tightestRemaining``：所有账号里最紧张的剩余百分比（小数，None 表示不适用）
    * ``recommendedAccountId``：推荐使用的账号（smart 策略）
    * ``isFailoverReady``：是否处于「多账号可切换」状态
    """
    grouped: dict[str, list[dict]] = {}
    for item in results:
        provider = str(item.get("providerId") or item.get("tool") or "")
        grouped.setdefault(provider, []).append(item)

    aggregates: list[dict] = []
    for provider, items in grouped.items():
        usable = [it for it in items if it.get("success")]
        remaining_values: list[float] = []
        for item in usable:
            windows = [
                t
                for t in item.get("tiers", [])
                if t.get("balanceAmount") is None and t.get("name") != "failed"
            ]
            if not windows:
                continue
            remaining_values.append(
                min(max(0.0, 100.0 - float(t.get("utilization", 0))) for t in windows)
            )

        # 推荐账号：可用里剩余最多、且重置最早的
        recommended = None
        best_score = None
        for item in usable:
            windows = [
                t
                for t in item.get("tiers", [])
                if t.get("balanceAmount") is None
            ]
            if not windows:
                continue
            tightest = min(max(0.0, 100.0 - float(t.get("utilization", 0))) for t in windows)
            score = (-tightest, item.get("queriedAt") or 0)
            if best_score is None or score < best_score:
                best_score = score
                recommended = item.get("accountId")

        aggregates.append(
            {
                "providerId": provider,
                "label": items[0].get("label") if items else provider,
                "kind": items[0].get("kind") if items else "window",
                "accounts": len(items),
                "available": len(usable),
                "tightestRemaining": min(remaining_values) if remaining_values else None,
                "recommendedAccountId": recommended,
                "isFailoverReady": len(items) > 1,
            }
        )

    aggregates.sort(key=lambda a: (a["available"] == 0, a["providerId"]))
    return aggregates
