"""ZCode 套餐额度（zcode-plan/billing/balance）

ZCode 的套餐额度来自 `https://zcode.z.ai/api/v1/zcode-plan/billing/balance`，
返回 `data.plans[]` 与 `data.balances[]`，每个 balance 带
`total_units` / `used_units` / `remaining_units` / `expires_at`。

⚠️ 该接口对「客户端 JWT」返回 400 parameter error（需要额外的客户端参数，
未公开文档），所以本适配器：

1. 优先用用户粘贴的 ZCode **API Key / access token** 直接请求 billing/balance；
2. 若该接口不可用，则回落到同一账号的智谱官方额度接口
   `open.bigmodel.cn/api/monitor/usage/quota/limit`（ZCode 套餐就是智谱账号的
   Coding Plan，两者额度同源），并如实标注来源。

无论走哪条路径，`utilization` 都是**已用百分比**，绝不伪造数据。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.models import (
    CredentialStatus,
    QuotaTier,
    SubscriptionQuota,
    millis_to_iso,
    now_millis,
)
from app.services.subscription_quota.providers_full import (
    ProviderTransientError,
    _api_failure,
    _auth_failure,
    _num,
    _request_json,
)

logger = logging.getLogger(__name__)

ZCODE_PLAN_BALANCE_URL = "https://zcode.z.ai/api/v1/zcode-plan/billing/balance"
BIGMODEL_QUOTA_URL = "https://open.bigmodel.cn/api/monitor/usage/quota/limit"


def _token(account: QuotaAccount) -> str:
    return str(account.extra.get("zcode_token") or account.api_key or "").strip()


def parse_zcode_balances(data: dict) -> list[QuotaTier]:
    """解析 ``data.balances[]`` → 档位

    ``total_units`` 与 ``used_units`` 都是 token 数，折成百分比；
    余额为 0 或缺失时用 ``remaining_units`` 反推。
    """
    tiers: list[QuotaTier] = []
    balances = data.get("balances")
    if not isinstance(balances, list):
        return tiers

    for item in balances:
        if not isinstance(item, dict):
            continue
        show_name = str(item.get("show_name") or "").strip() or "额度"
        total = _num(item.get("total_units"))
        used = _num(item.get("used_units"))
        remaining = _num(item.get("remaining_units"))

        if total is None or total <= 0:
            continue
        if used is None:
            used = max(0.0, total - (remaining if remaining is not None else total))

        tier = QuotaTier(
            name=f"model:{show_name}",
            utilization=max(0.0, min(100.0, used / total * 100.0)),
            resets_at=millis_to_iso(int(ts)) if (ts := _num(item.get("expires_at"))) else None,
        )
        # 附带原始单位数，前端可在悬停里显示「已用 / 总量」
        tier.balance_amount = remaining  # 复用字段承载剩余 token 数
        tier.balance_unit = "tokens"
        tiers.append(tier)

    return tiers


def parse_bigmodel_limits(data: dict) -> list[QuotaTier]:
    """解析智谱 ``data.limits[]``（CREDIT_LIMIT / TOKENS_LIMIT）

    ``unit 3`` → 5 小时窗口；``unit 6`` → 每周窗口。
    ``percentage`` 已是**已用**百分比；缺失时用 ``usage`` / ``currentValue`` 计算。
    """
    tiers: list[QuotaTier] = []
    limits = data.get("limits")
    if not isinstance(limits, list):
        return tiers

    for item in limits:
        if not isinstance(item, dict):
            continue
        limit_type = str(item.get("type") or "").upper()
        if limit_type not in ("TOKENS_LIMIT", "CREDIT_LIMIT"):
            continue

        unit = _num(item.get("unit"))
        name = "five_hour" if unit == 3.0 else ("weekly_limit" if unit == 6.0 else None)
        if name is None:
            continue

        pct = _num(item.get("percentage"))
        if pct is None:
            total = _num(item.get("usage"))
            used = _num(item.get("currentValue"))
            pct = (used / total * 100.0) if (total and used is not None) else 0.0

        reset = _num(item.get("nextResetTime"))
        tiers.append(
            QuotaTier(
                name=name,
                utilization=max(0.0, min(100.0, pct)),
                resets_at=millis_to_iso(int(reset)) if reset else None,
            )
        )

    order = {"five_hour": 0, "weekly_limit": 1}
    tiers.sort(key=lambda t: order.get(t.name, 99))
    return tiers


async def query_zcode(account: QuotaAccount) -> SubscriptionQuota:
    """ZCode 套餐额度：优先 zcode-plan/billing/balance，回落智谱官方额度接口。"""
    token = _token(account)
    if not token:
        return SubscriptionQuota.failure(
            "zcode", CredentialStatus.NOT_FOUND, "缺少 ZCode 凭据（access token / API Key）"
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ZCode/3.18.2",
    }

    plan_status: Optional[int] = None
    plan_error: Optional[str] = None
    try:
        plan_status, plan_body, plan_error = await _request_json(
            "GET",
            f"{ZCODE_PLAN_BALANCE_URL}?app_version=3.18.2",
            headers,
        )
    except ProviderTransientError as exc:
        plan_error = str(exc)

    if plan_status == 200 and isinstance(plan_body, dict):
        data = plan_body.get("data")
        if isinstance(data, dict):
            tiers = parse_zcode_balances(data)
            if tiers:
                plan_name = None
                plans = data.get("plans")
                if isinstance(plans, list) and plans and isinstance(plans[0], dict):
                    plan_name = str(plans[0].get("name") or "").strip() or None
                return SubscriptionQuota(
                    tool="zcode",
                    credential_status=CredentialStatus.VALID,
                    success=True,
                    tiers=tiers,
                    plan_name=plan_name,
                    credential_message="来源：ZCode billing/balance",
                    queried_at=now_millis(),
                )

    if plan_status in (401, 403):
        return _auth_failure("zcode", plan_status)

    # 回落：ZCode 套餐就是智谱账号的 Coding Plan，额度同源
    try:
        status2, body2, err2 = await _request_json(
            "GET",
            BIGMODEL_QUOTA_URL,
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "ToolboxSubscriptionQuota/2.0",
            },
        )
    except ProviderTransientError as exc:
        return _api_failure("zcode", f"网络错误: {exc}")

    if status2 in (401, 403):
        return _auth_failure("zcode", status2)
    if err2 is not None:
        return _api_failure("zcode", f"接口错误: {err2}")
    if not isinstance(body2, dict):
        return _api_failure("zcode", "响应结构异常")

    if body2.get("code") not in (None, 200) or body2.get("success") is False:
        return _api_failure(
            "zcode", f"智谱额度接口返回错误：{body2.get('msg') or '未知错误'}"
        )

    data2 = body2.get("data")
    if not isinstance(data2, dict):
        return _api_failure("zcode", "响应缺少 data 字段")

    tiers = parse_bigmodel_limits(data2)
    if not tiers:
        hint = f"（billing/balance 返回 {plan_status or 'n/a'}：{plan_error or '无可用额度'}）"
        return _api_failure("zcode", f"未取得可识别的套餐额度 {hint}")

    level = data2.get("level")
    return SubscriptionQuota(
        tool="zcode",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=level if isinstance(level, str) and level else None,
        credential_message="来源：智谱 GLM 额度接口（ZCode 套餐同源）",
        queried_at=now_millis(),
    )
