"""全量供应商标注与查询实现（对照 cc-switch 的 coding_plan.rs / balance.rs）

每个函数签名统一：``async def query(account: QuotaAccount, region: str) -> SubscriptionQuota``

约定
----
* 网络 / 超时等瞬时错误 → 抛 :class:`ProviderTransientError`
* 鉴权失败 / 非 2xx / 业务错误 → 返回 ``success=False`` 并带真实原因
* 解析不出任何档位 → ``success=False`` 并说明「响应形态不认识」，不渲染空卡片
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import httpx

from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.models import (
    CredentialStatus,
    QuotaTier,
    SubscriptionQuota,
    millis_to_iso,
    now_millis,
)

logger = logging.getLogger(__name__)

TIMEOUT = 15.0
USER_AGENT = "ToolboxSubscriptionQuota/2.0"


class ProviderTransientError(RuntimeError):
    """瞬时错误（网络 / 超时 / 读体中断）"""


# --------------------------------------------------------------------------
# HTTP 辅助
# --------------------------------------------------------------------------


async def _request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    *,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = TIMEOUT,
) -> tuple[Optional[int], Any, Optional[str]]:
    """返回 (status, parsed_json, error)。网络错误抛 ProviderTransientError。"""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.request(
                method, url, headers=headers, json=json_body, params=params
            )
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ProviderTransientError(f"网络错误: {type(exc).__name__}") from exc

    if not resp.is_success:
        body = (resp.text or "").strip().replace("\n", " ")[:300]
        return resp.status_code, None, body or f"HTTP {resp.status_code}"
    if not resp.content:
        return resp.status_code, {}, None
    try:
        return resp.status_code, resp.json(), None
    except ValueError as exc:
        return resp.status_code, None, f"响应不是合法 JSON: {exc}"


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _iso(value: Any) -> Optional[str]:
    """把 ISO 字符串 / 毫秒时间戳 / 秒时间戳统一成 ISO 8601。"""
    if isinstance(value, str) and value:
        return value
    num = _num(value)
    if num is None or num <= 0:
        return None
    # 秒级（< 1e11）→ 毫秒
    return millis_to_iso(int(num * 1000) if num < 1e11 else int(num))


def _auth_failure(name: str, status: int) -> SubscriptionQuota:
    return SubscriptionQuota.failure(
        name, CredentialStatus.EXPIRED, f"认证失败（HTTP {status}），请检查 API Key 是否有效"
    )


def _api_failure(name: str, message: str) -> SubscriptionQuota:
    return SubscriptionQuota.failure(name, CredentialStatus.VALID, message)


def _bearer(account: QuotaAccount, field: str = "api_key") -> dict[str, str]:
    key = account.extra.get(field) or account.api_key or ""
    return {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }


def _region(account: QuotaAccount) -> str:
    region = str(account.extra.get("region") or "cn").strip().lower()
    return "intl" if region in ("intl", "en", "global", "us", "international") else "cn"


def _base_url(account: QuotaAccount) -> str:
    return str(account.extra.get("base_url") or "").strip()


# --------------------------------------------------------------------------
# 套餐窗口型
# --------------------------------------------------------------------------


async def query_kimi(account: QuotaAccount) -> SubscriptionQuota:
    """Kimi For Coding：``GET /coding/v1/usages``（5 小时 + 每周）"""
    base = "https://api.kimi.com/coding/v1"
    if _region(account) == "intl":
        base = "https://api.kimi.ai/coding/v1"

    headers = _bearer(account)
    status, body, err = await _request_json("GET", f"{base}/usages", headers)
    if status in (401, 403):
        return _auth_failure("kimi", status)
    if err is not None:
        return _api_failure("kimi", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("kimi", "响应结构异常")

    tiers = parse_kimi_usages(body)
    if not tiers:
        return _api_failure("kimi", "响应中没有任何额度窗口")

    plan_name = None
    try:
        st2, me, err2 = await _request_json("GET", f"{base}/me", headers, timeout=8.0)
        if err2 is None and isinstance(me, dict):
            level = me.get("user_level_name")
            if isinstance(level, str) and level:
                plan_name = level
    except ProviderTransientError:
        pass  # 套餐名是附加信息

    return SubscriptionQuota(
        tool="kimi",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=plan_name,
        queried_at=now_millis(),
    )


def parse_kimi_usages(body: dict) -> list[QuotaTier]:
    tiers: list[QuotaTier] = []

    limits = body.get("limits")
    if isinstance(limits, list):
        for item in limits:
            if not isinstance(item, dict):
                continue
            detail = item.get("detail")
            if not isinstance(detail, dict):
                continue
            limit = _num(detail.get("limit")) or 1.0
            remaining = _num(detail.get("remaining")) or 0.0
            used = max(0.0, limit - remaining)
            tiers.append(
                QuotaTier(
                    name="five_hour",
                    utilization=(used / limit) * 100.0 if limit > 0 else 0.0,
                    resets_at=_iso(detail.get("resetTime")),
                )
            )

    usage = body.get("usage")
    if isinstance(usage, dict):
        limit = _num(usage.get("limit")) or 1.0
        remaining = _num(usage.get("remaining")) or 0.0
        used = max(0.0, limit - remaining)
        tiers.append(
            QuotaTier(
                name="weekly_limit",
                utilization=(used / limit) * 100.0 if limit > 0 else 0.0,
                resets_at=_iso(usage.get("resetTime")),
            )
        )
    return tiers


async def query_zhipu(account: QuotaAccount) -> SubscriptionQuota:
    """智谱 GLM：``GET /api/monitor/usage/quota/limit``（**Authorization 不带 Bearer**）"""
    host = "https://open.bigmodel.cn" if _region(account) == "cn" else "https://api.z.ai"
    key = str(account.extra.get("api_key") or account.api_key or "")
    headers = {
        "Authorization": key,
        "Content-Type": "application/json",
        "Accept-Language": "zh-CN,zh",
        "User-Agent": USER_AGENT,
    }
    status, body, err = await _request_json(
        "GET", f"{host}/api/monitor/usage/quota/limit", headers
    )
    if status in (401, 403):
        return _auth_failure("zhipu", status)
    if err is not None:
        return _api_failure("zhipu", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("zhipu", "响应结构异常")

    if body.get("success") is False:
        return _api_failure("zhipu", f"接口返回错误：{body.get('msg') or '未知错误'}")

    data = body.get("data")
    if not isinstance(data, dict):
        return _api_failure("zhipu", "响应缺少 data 字段")

    tiers = parse_zhipu_tiers(data)
    if not tiers:
        return _api_failure("zhipu", "该账户没有 Coding Plan 窗口额度（可能是按量付费）")

    level = data.get("level")
    return SubscriptionQuota(
        tool="zhipu",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=level if isinstance(level, str) and level else None,
        queried_at=now_millis(),
    )


def _zhipu_window(item: dict) -> Optional[str]:
    unit = _num(item.get("unit"))
    if unit == 3.0:
        return "five_hour"
    if unit == 6.0:
        return "weekly_limit"
    return None


def parse_zhipu_tiers(data: dict) -> list[QuotaTier]:
    five_hour: Optional[tuple] = None
    weekly: Optional[tuple] = None
    unclassified: list[tuple] = []

    limits = data.get("limits")
    if isinstance(limits, list):
        for item in limits:
            if not isinstance(item, dict):
                continue
            limit_type = str(item.get("type") or "").upper()
            if limit_type not in ("TOKENS_LIMIT", "CREDIT_LIMIT"):
                continue
            percentage = _num(item.get("percentage")) or 0.0
            reset_ms = _num(item.get("nextResetTime"))
            entry = (reset_ms, percentage)
            window = _zhipu_window(item)
            if window == "five_hour" and five_hour is None:
                five_hour = entry
            elif window == "weekly_limit" and weekly is None:
                weekly = entry
            else:
                unclassified.append(entry)

    unclassified.sort(key=lambda e: (e[0] is not None, e[0] or 0.0))
    for entry in unclassified:
        if five_hour is None:
            five_hour = entry
        elif weekly is None:
            weekly = entry

    tiers: list[QuotaTier] = []
    for name, slot in (("five_hour", five_hour), ("weekly_limit", weekly)):
        if slot is None:
            continue
        reset_ms, percentage = slot
        tiers.append(
            QuotaTier(
                name=name,
                utilization=percentage,
                resets_at=millis_to_iso(int(reset_ms)) if reset_ms else None,
            )
        )
    return tiers


async def query_zhipu_team(account: QuotaAccount) -> SubscriptionQuota:
    """智谱团队版：同一端点 + ``bigmodel-organization`` / ``bigmodel-project`` 头"""
    org = str(account.extra.get("organization_id") or "").strip()
    project = str(account.extra.get("project_id") or "").strip()
    if not org or not project:
        return _api_failure("zhipu_team", "团队版需要填写组织 ID 与项目 ID")

    key = str(account.extra.get("api_key") or account.api_key or "")
    headers = {
        "Authorization": key,
        "bigmodel-organization": org,
        "bigmodel-project": project,
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    status, body, err = await _request_json(
        "GET", "https://open.bigmodel.cn/api/monitor/usage/quota/limit", headers
    )
    if status in (401, 403):
        return _auth_failure("zhipu_team", status)
    if err is not None:
        return _api_failure("zhipu_team", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("zhipu_team", "响应结构异常")
    if body.get("success") is False:
        return _api_failure("zhipu_team", f"接口返回错误：{body.get('msg') or '未知错误'}")

    data = body.get("data")
    if not isinstance(data, dict):
        return _api_failure("zhipu_team", "响应缺少 data 字段")
    tiers = parse_zhipu_tiers(data)
    if not tiers:
        return _api_failure("zhipu_team", "该团队套餐没有可显示的窗口额度")
    level = data.get("level")
    return SubscriptionQuota(
        tool="zhipu_team",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=level if isinstance(level, str) and level else None,
        queried_at=now_millis(),
    )


async def query_minimax(account: QuotaAccount) -> SubscriptionQuota:
    """MiniMax：``GET /v1/api/openplatform/coding_plan/remains``"""
    domain = "api.minimaxi.com" if _region(account) == "cn" else "api.minimax.io"
    headers = _bearer(account)
    headers["Content-Type"] = "application/json"
    status, body, err = await _request_json(
        "GET", f"https://{domain}/v1/api/openplatform/coding_plan/remains", headers
    )
    if status in (401, 403):
        return _auth_failure("minimax", status)
    if err is not None:
        return _api_failure("minimax", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("minimax", "响应结构异常")

    base_resp = body.get("base_resp")
    if isinstance(base_resp, dict):
        code = _num(base_resp.get("status_code"))
        if code not in (None, 0.0):
            return _api_failure(
                "minimax",
                f"接口返回错误（code {int(code)}）：{base_resp.get('status_msg') or '未知错误'}",
            )

    tiers = parse_minimax_tiers(body)
    if not tiers:
        return _api_failure("minimax", "响应中没有 general 模型的额度窗口")
    return SubscriptionQuota(
        tool="minimax",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


def parse_minimax_tiers(body: dict) -> list[QuotaTier]:
    tiers: list[QuotaTier] = []
    remains = body.get("model_remains")
    if not isinstance(remains, list):
        return tiers

    item = next(
        (e for e in remains if isinstance(e, dict) and e.get("model_name") == "general"), None
    )
    if item is None:
        return tiers

    interval_remaining = _num(item.get("current_interval_remaining_percent"))
    if interval_remaining is not None:
        tiers.append(
            QuotaTier(
                name="five_hour",
                utilization=100.0 - interval_remaining,
                resets_at=_iso(item.get("end_time")),
            )
        )

    weekly_status = _num(item.get("current_weekly_status"))
    if weekly_status in (1.0, 2.0):
        weekly_remaining = _num(item.get("current_weekly_remaining_percent"))
        if weekly_remaining is not None:
            tiers.append(
                QuotaTier(
                    name="weekly_limit",
                    utilization=100.0 - weekly_remaining,
                    resets_at=_iso(item.get("weekly_end_time")),
                )
            )
    return tiers


async def query_zenmux(account: QuotaAccount) -> SubscriptionQuota:
    """ZenMux：直接 GET 用户填的用量地址，解析 ``quota_5_hour`` / ``quota_7_day``"""
    base = _base_url(account)
    if not base:
        return _api_failure("zenmux", "ZenMux 需要填写用量地址（base_url）")

    status, body, err = await _request_json("GET", base, _bearer(account))
    if status in (401, 403):
        return _auth_failure("zenmux", status)
    if err is not None:
        return _api_failure("zenmux", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("zenmux", "响应结构异常")

    if body.get("success") is not True:
        return _api_failure("zenmux", f"接口返回错误：{body.get('message') or '未知错误'}")

    data = body.get("data")
    if not isinstance(data, dict):
        return _api_failure("zenmux", "响应缺少 data 字段")

    tiers = parse_zenmux_tiers(data)
    if not tiers:
        return _api_failure("zenmux", "响应中没有任何额度窗口")

    plan_tier = ""
    plan = data.get("plan")
    if isinstance(plan, dict):
        plan_tier = str(plan.get("tier") or "")
    status_text = str(data.get("account_status") or "")
    plan_name = f"{plan_tier} ({status_text})".strip() if plan_tier else None

    return SubscriptionQuota(
        tool="zenmux",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=plan_name,
        queried_at=now_millis(),
    )


def parse_zenmux_tiers(data: dict) -> list[QuotaTier]:
    tiers: list[QuotaTier] = []
    for key, name in (("quota_5_hour", "five_hour"), ("quota_7_day", "weekly_limit")):
        window = data.get(key)
        if not isinstance(window, dict):
            continue
        pct = _num(window.get("usage_percentage"))
        if pct is None:
            continue
        tiers.append(
            QuotaTier(
                name=name,
                utilization=pct * 100.0,
                resets_at=_iso(window.get("resets_at")),
                used_value_usd=_num(window.get("used_value_usd")),
                max_value_usd=_num(window.get("max_value_usd")),
            )
        )
    return tiers


async def query_opencode_go(account: QuotaAccount) -> SubscriptionQuota:
    """OpenCode Go：``GET /zen/go/v1/usage``（滚动 / 每周 / 每月）"""
    status, body, err = await _request_json(
        "GET", "https://opencode.ai/zen/go/v1/usage", _bearer(account)
    )
    if status == 403:
        return _api_failure("opencode_go", "API Key 有效但没有 OpenCode Go 订阅（HTTP 403）")
    if status in (401, 403):
        return _auth_failure("opencode_go", status)
    if err is not None:
        return _api_failure("opencode_go", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("opencode_go", "响应结构异常")

    tiers = parse_opencode_go_tiers(body)
    if not tiers:
        return _api_failure("opencode_go", "响应形态不认识（该端点未文档化，可能已变更）")
    return SubscriptionQuota(
        tool="opencode_go",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


def parse_opencode_go_tiers(body: dict) -> list[QuotaTier]:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return []
    tiers: list[QuotaTier] = []
    for key, name in (("rolling", "five_hour"), ("weekly", "weekly_limit"), ("monthly", "monthly")):
        window = usage.get(key)
        if not isinstance(window, dict):
            continue
        percent = _num(window.get("percent"))
        if percent is None:
            continue
        tiers.append(
            QuotaTier(
                name=name,
                utilization=percent,
                # percent 为 0 时上游给的是占位时间，丢弃
                resets_at=_iso(window.get("resetsAt")) if percent > 0 else None,
            )
        )
    return tiers


async def query_command_code(account: QuotaAccount) -> SubscriptionQuota:
    """Command Code：whoami → credits → subscriptions → usage/summary"""
    base = "https://api.commandcode.ai"
    headers = _bearer(account)

    status, whoami, err = await _request_json(
        "GET", f"{base}/alpha/whoami", headers, params={"limits": "1"}
    )
    if status == 401:
        return _auth_failure("command_code", status)
    if err is not None:
        return _api_failure("command_code", f"whoami 失败: {err}")

    org_id = None
    if isinstance(whoami, dict):
        org = whoami.get("org")
        if isinstance(org, dict):
            org_id = org.get("id") if isinstance(org.get("id"), str) else None
    params = {"orgId": org_id} if org_id else {}

    status, credits, err = await _request_json(
        "GET", f"{base}/alpha/billing/credits", headers, params=params
    )
    if status == 401:
        return _auth_failure("command_code", status)
    if err is not None:
        return _api_failure("command_code", f"credits 失败: {err}")

    summary_params: dict[str, str] = {}
    if org_id:
        summary_params["orgId"] = org_id
    status, subscription, sub_err = await _request_json(
        "GET", f"{base}/alpha/billing/subscriptions", headers, params=params
    )
    period_start = None
    if sub_err is None and isinstance(subscription, dict):
        data = subscription.get("data")
        if isinstance(data, dict):
            raw_start = data.get("currentPeriodStart")
            if isinstance(raw_start, str):
                period_start = raw_start
    if period_start:
        summary_params["since"] = period_start

    status, summary, err = await _request_json(
        "GET", f"{base}/alpha/usage/summary", headers, params=summary_params
    )
    if status == 401:
        return _auth_failure("command_code", status)
    if err is not None:
        return _api_failure("command_code", f"usage/summary 失败: {err}")

    quota = parse_command_code_quota(credits, subscription, summary)
    quota.tool = "command_code"
    return quota


def parse_command_code_quota(
    credits_response: Any, subscription_response: Any, summary_response: Any
) -> SubscriptionQuota:
    if not isinstance(credits_response, dict):
        return _api_failure("command_code", "响应结构异常")
    credit_root = credits_response.get("credits")
    if not isinstance(credit_root, dict):
        return _api_failure("command_code", "响应缺少 credits 字段")

    def _credit(key: str) -> float:
        return max(0.0, _num(credit_root.get(key)) or 0.0)

    total_remaining = _credit("monthlyCredits") + _credit("purchasedCredits") + _credit("freeCredits")
    total_spent = _num(summary_response.get("totalCost")) if isinstance(summary_response, dict) else None
    if total_spent is None:
        return _api_failure("command_code", "响应缺少 totalCost 字段")
    total_spent = max(0.0, total_spent)
    total_pool = total_spent + total_remaining

    period_end = None
    if isinstance(subscription_response, dict):
        data = subscription_response.get("data")
        if isinstance(data, dict):
            period_end = _iso(data.get("currentPeriodEnd"))

    tiers: list[QuotaTier] = []
    window_limits = credits_response.get("windowLimits") or credit_root.get("windowLimits")
    if isinstance(window_limits, dict) and window_limits.get("limited") is True:
        for key, name in (("fiveHour", "five_hour"), ("weekly", "weekly_limit")):
            window = window_limits.get(key)
            if not isinstance(window, dict):
                continue
            used = _num(window.get("used"))
            cap = _num(window.get("cap"))
            if used is None or cap is None or cap <= 0:
                continue
            tiers.append(
                QuotaTier(
                    name=name,
                    utilization=used / cap * 100.0,
                    resets_at=_iso(window.get("resetAt")),
                )
            )

    tiers.append(
        QuotaTier(
            name="monthly",
            utilization=(total_spent / total_pool * 100.0) if total_pool > 0 else 0.0,
            resets_at=period_end,
        )
    )

    return SubscriptionQuota(
        tool="command_code",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


async def query_opendesign(account: QuotaAccount) -> SubscriptionQuota:
    """OpenDesign：workspaces/current 取 id → billing/snapshot 取窗口

    注意：账单接口只认 AMR **控制面 controlKey**；ZCode / 推理配置里存的是
    运行时推理 Key（`sk-amr-ew__…`），一定被拒。所以这里对 401/404 都给出
    「需要 controlKey」的明确指引，而不是含糊的接口错误。
    """
    base = _base_url(account) or "https://amr-api.open-design.ai"
    base = base.rstrip("/")
    # 去掉推理地址里的 /v1 之类路径，只保留 origin
    from urllib.parse import urlparse

    try:
        parsed = urlparse(base)
        if parsed.scheme and parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}"
    except ValueError:
        pass
    # 控制面 host 与推理 host 不同：只做一次明确的候选回退
    candidates = [base]
    if "amr-link." in base:
        candidates.append(base.replace("amr-link.", "amr-api."))
    elif "amr-api." in base:
        candidates.append(base.replace("amr-api.", "amr-link."))
    candidates = list(dict.fromkeys(candidates))

    headers = _bearer(account, "control_key")
    headers["Content-Type"] = "application/json"

    last_status: Optional[int] = None
    last_error: Optional[str] = None

    for candidate in candidates:
        status, current, err = await _request_json(
            "GET", f"{candidate}/api/v1/workspaces/current", headers
        )
        last_status, last_error = status, err
        if status in (401, 403):
            return SubscriptionQuota.failure(
                "opendesign",
                CredentialStatus.EXPIRED,
                "OpenDesign 账单接口只认 AMR 控制面 controlKey"
                "（推理运行时 Key `sk-amr-ew__…` 会被拒），"
                "请到 OpenDesign 控制台复制 controlKey 后重新添加",
            )
        if status == 404 or err is not None:
            continue

        workspace_id = None
        if isinstance(current, dict):
            for key in ("workspaceId", "activeWorkspaceId"):
                value = current.get(key)
                if isinstance(value, str) and value.strip():
                    workspace_id = value.strip()
                    break
        if not workspace_id:
            workspace_id = str(account.extra.get("workspace_id") or "").strip() or None
        if not workspace_id:
            return _api_failure(
                "opendesign", "拿不到 workspace id（可在配置里手动填写 workspace_id）"
            )

        status2, snapshot, err2 = await _request_json(
            "GET", f"{candidate}/api/v1/workspaces/{workspace_id}/billing/snapshot", headers
        )
        if status2 in (401, 403):
            return SubscriptionQuota.failure(
                "opendesign",
                CredentialStatus.EXPIRED,
                "OpenDesign 账单接口只认 AMR 控制面 controlKey，请重新填 controlKey",
            )
        if err2 is not None:
            return _api_failure("opendesign", f"billing/snapshot 失败: {err2}")
        if not isinstance(snapshot, dict):
            return _api_failure("opendesign", "响应结构异常")

        tiers = parse_opendesign_tiers(snapshot)
        if not tiers:
            return _api_failure("opendesign", "快照里没有 designPlanWindows 额度")
        return SubscriptionQuota(
            tool="opendesign",
            credential_status=CredentialStatus.VALID,
            success=True,
            tiers=tiers,
            queried_at=now_millis(),
        )

    return _api_failure(
        "opendesign",
        f"控制面不可达（HTTP {last_status or 'n/a'}）：{last_error or '无响应'}；"
        "请确认使用 AMR 控制面地址并填写 controlKey",
    )


def parse_opendesign_tiers(body: dict) -> list[QuotaTier]:
    windows = body.get("designPlanWindows")
    if not isinstance(windows, list):
        return []
    tiers: list[QuotaTier] = []
    for window in windows:
        if not isinstance(window, dict):
            continue
        kind = window.get("kind")
        name = {"5h": "five_hour", "7d": "weekly_limit"}.get(kind)
        if not name:
            continue
        limit = _num(window.get("limitCredits"))
        remaining = _num(window.get("remainingCredits"))
        if limit is None or remaining is None or limit <= 0:
            continue
        used = max(0.0, min(limit, limit - remaining))
        tiers.append(
            QuotaTier(
                name=name,
                utilization=used / limit * 100.0,
                resets_at=_iso(window.get("resetsAt")),
            )
        )
    return tiers


async def query_volcengine(account: QuotaAccount) -> SubscriptionQuota:
    """火山方舟：控制面 OpenAPI（AK/SK 签名）。

    签名实现与 cc-switch 的 v4 一致；失败时明确提示「需要账号级 AK/SK」。
    """
    ak = str(account.extra.get("access_key") or "").strip()
    sk = str(account.extra.get("secret_key") or "").strip()
    if not ak or not sk:
        return _api_failure("volcengine", "需要账号级 AccessKey ID 与 Secret（不是推理 Key）")

    from app.services.subscription_quota.volcengine_sign import signed_post

    try:
        code, body, err = await signed_post(
            ak=ak,
            sk=sk,
            action="GetAFPUsage",
            version="2024-01-01",
            region="cn-beijing",
            host="open.volcengineapi.com",
            service="ark",
            extra_body={},
        )
    except ProviderTransientError as exc:
        return _api_failure("volcengine", f"网络错误: {exc}")

    if code in (401, 403):
        return _auth_failure("volcengine", int(code))
    if err is not None:
        # 换一个 Action 再试（Coding Plan）
        try:
            code2, body2, err2 = await signed_post(
                ak=ak,
                sk=sk,
                action="GetCodingPlanUsage",
                version="2024-01-01",
                region="cn-beijing",
                host="open.volcengineapi.com",
                service="ark",
                extra_body={},
            )
        except ProviderTransientError as exc:
            return _api_failure("volcengine", f"网络错误: {exc}")
        if err2 is not None:
            return _api_failure("volcengine", f"控制面调用失败: {err2}")
        body = body2

    tiers = parse_volcengine_tiers(body)
    if not tiers:
        return _api_failure("volcengine", "响应里没有可识别的额度窗口")
    return SubscriptionQuota(
        tool="volcengine",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


def parse_volcengine_tiers(body: Any) -> list[QuotaTier]:
    """火山返回 ``Result.{AFPCodingPlan|CodingPlan}``，窗口字段名以 ``*_usage``/``*_limit`` 为主。"""
    if not isinstance(body, dict):
        return []
    result = body.get("Result")
    if not isinstance(result, dict):
        result = body

    tiers: list[QuotaTier] = []
    for key, name in (
        ("FiveHour", "five_hour"),
        ("Weekly", "weekly_limit"),
        ("Monthly", "monthly"),
    ):
        window = result.get(key)
        if not isinstance(window, dict):
            continue
        used = _num(window.get("Usage")) or _num(window.get("Used"))
        limit = _num(window.get("Limit")) or _num(window.get("Total"))
        if used is None or limit is None or limit <= 0:
            continue
        tiers.append(
            QuotaTier(
                name=name,
                utilization=max(0.0, min(limit, used)) / limit * 100.0,
                resets_at=_iso(window.get("ResetTime")),
            )
        )
    return tiers


# --------------------------------------------------------------------------
# 余额型
# --------------------------------------------------------------------------


async def query_deepseek(account: QuotaAccount) -> SubscriptionQuota:
    """DeepSeek：``GET /user/balance``"""
    status, body, err = await _request_json(
        "GET", "https://api.deepseek.com/user/balance", _bearer(account)
    )
    if status in (401, 403):
        return _auth_failure("deepseek", status)
    if err is not None:
        return _api_failure("deepseek", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("deepseek", "响应结构异常")

    tiers = parse_deepseek_balance(body)
    if not tiers:
        return _api_failure("deepseek", "响应里没有余额信息")
    return SubscriptionQuota(
        tool="deepseek",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


def parse_deepseek_balance(body: dict) -> list[QuotaTier]:
    tiers: list[QuotaTier] = []
    infos = body.get("balance_infos")
    if isinstance(infos, list):
        for info in infos:
            if not isinstance(info, dict):
                continue
            currency = str(info.get("currency") or "CNY")
            total = _num(info.get("total_balance"))
            if total is None:
                continue
            tiers.append(
                QuotaTier(
                    name=f"balance_{currency}",
                    utilization=0.0,
                    resets_at=None,
                    used_value_usd=None,
                    max_value_usd=None,
                )
            )
            tiers[-1].balance_amount = total  # type: ignore[attr-defined]
            tiers[-1].balance_unit = currency  # type: ignore[attr-defined]
    # 同一账号会列出 CNY / USD 两个钱包，只保留有余额的
    tiers = [t for t in tiers if getattr(t, "balance_amount", 0) and t.balance_amount > 0] or tiers
    return tiers


async def query_stepfun(account: QuotaAccount) -> SubscriptionQuota:
    status, body, err = await _request_json(
        "GET", "https://api.stepfun.com/v1/accounts", _bearer(account)
    )
    if status in (401, 403):
        return _auth_failure("stepfun", status)
    if err is not None:
        return _api_failure("stepfun", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("stepfun", "响应结构异常")

    balance = _num(body.get("balance"))
    if balance is None:
        return _api_failure("stepfun", "响应里没有 balance 字段")
    return SubscriptionQuota(
        tool="stepfun",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier("balance_CNY", balance, "CNY")],
        queried_at=now_millis(),
    )


def balance_tier(name: str, amount: float, unit: str) -> QuotaTier:
    """余额型统一用 QuotaTier 承载：utilization=0（不表示已用百分比），金额放附加字段"""
    tier = QuotaTier(name=name, utilization=0.0, resets_at=None)
    tier.balance_amount = amount  # type: ignore[attr-defined]
    tier.balance_unit = unit  # type: ignore[attr-defined]
    return tier


async def query_siliconflow(account: QuotaAccount) -> SubscriptionQuota:
    domain = "api.siliconflow.cn" if _region(account) == "cn" else "api.siliconflow.com"
    status, body, err = await _request_json(
        "GET", f"https://{domain}/v1/user/info", _bearer(account)
    )
    if status in (401, 403):
        return _auth_failure("siliconflow", status)
    if err is not None:
        return _api_failure("siliconflow", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("siliconflow", "响应结构异常")

    data = body.get("data")
    if not isinstance(data, dict):
        return _api_failure("siliconflow", "响应缺少 data 字段")
    total = _num(data.get("totalBalance"))
    if total is None:
        return _api_failure("siliconflow", "响应缺少 totalBalance 字段")

    unit = "CNY" if _region(account) == "cn" else "USD"
    return SubscriptionQuota(
        tool="siliconflow",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier("balance_" + unit, total, unit)],
        queried_at=now_millis(),
    )


async def query_openrouter(account: QuotaAccount) -> SubscriptionQuota:
    status, body, err = await _request_json(
        "GET", "https://openrouter.ai/api/v1/credits", _bearer(account)
    )
    if status in (401, 403):
        return _auth_failure("openrouter", status)
    if err is not None:
        return _api_failure("openrouter", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("openrouter", "响应结构异常")

    data = body.get("data") if isinstance(body.get("data"), dict) else body
    credits = _num(data.get("total_credits"))
    usage = _num(data.get("total_usage"))
    if credits is None or usage is None:
        return _api_failure("openrouter", "响应缺少 total_credits / total_usage")
    remaining = credits - usage
    return SubscriptionQuota(
        tool="openrouter",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier("balance_USD", remaining, "USD")],
        queried_at=now_millis(),
    )


async def query_novita(account: QuotaAccount) -> SubscriptionQuota:
    status, body, err = await _request_json(
        "GET", "https://api.novita.ai/v3/user/balance", _bearer(account)
    )
    if status in (401, 403):
        return _auth_failure("novita", status)
    if err is not None:
        return _api_failure("novita", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("novita", "响应结构异常")

    available = _num(body.get("availableBalance"))
    if available is None:
        return _api_failure("novita", "响应缺少 availableBalance 字段")
    # 单位 0.0001 USD
    return SubscriptionQuota(
        tool="novita",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier("balance_USD", available / 10000.0, "USD")],
        queried_at=now_millis(),
    )


async def query_ollama_cloud(account: QuotaAccount) -> SubscriptionQuota:
    status, body, err = await _request_json(
        "GET", "https://ollama.com/api/balance", _bearer(account)
    )
    if status in (401, 403):
        return _auth_failure("ollama_cloud", status)
    if err is not None:
        return _api_failure("ollama_cloud", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("ollama_cloud", "响应结构异常")

    included = body.get("included")
    if not isinstance(included, dict):
        return _api_failure("ollama_cloud", "响应缺少 included 字段")

    balance = _num(included.get("balance_usd"))
    allowance = _num(included.get("allowance_usd"))
    if balance is not None and allowance and allowance > 0:
        used = max(0.0, min(allowance, allowance - balance))
        period = included.get("period")
        resets = _iso(period.get("until")) if isinstance(period, dict) else None
        return SubscriptionQuota(
            tool="ollama_cloud",
            credential_status=CredentialStatus.VALID,
            success=True,
            tiers=[QuotaTier(name="monthly", utilization=used / allowance * 100.0, resets_at=resets)],
            queried_at=now_millis(),
        )

    # 旧套餐：session / weekly 两档
    tiers: list[QuotaTier] = []
    for key, name in (("session", "five_hour"), ("weekly", "weekly_limit")):
        window = included.get(key)
        if not isinstance(window, dict):
            continue
        pct = _num(window.get("remaining_percent"))
        if pct is None:
            continue
        tiers.append(
            QuotaTier(name=name, utilization=100.0 - pct, resets_at=_iso(window.get("resets_at")))
        )
    if not tiers:
        return _api_failure("ollama_cloud", "响应里没有可识别的额度窗口")
    return SubscriptionQuota(
        tool="ollama_cloud",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


async def query_zhipu_payg(account: QuotaAccount) -> SubscriptionQuota:
    host = "https://open.bigmodel.cn" if _region(account) == "cn" else "https://api.z.ai"
    key = str(account.extra.get("api_key") or account.api_key or "")
    headers = {
        "Authorization": key,
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    status, body, err = await _request_json(
        "GET", f"{host}/api/biz/account/query-customer-account-report", headers
    )
    if status in (401, 403):
        return _auth_failure("zhipu_payg", status)
    if err is not None:
        return _api_failure("zhipu_payg", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("zhipu_payg", "响应结构异常")

    if body.get("success") is False:
        return _api_failure("zhipu_payg", f"接口返回错误：{body.get('msg') or '未知错误'}")

    data = body.get("data")
    if not isinstance(data, dict):
        return _api_failure("zhipu_payg", "响应缺少 data 字段")
    balance = _num(data.get("availableBalance"))
    if balance is None:
        return _api_failure("zhipu_payg", "响应缺少 availableBalance 字段")

    unit = "CNY" if _region(account) == "cn" else "USD"
    return SubscriptionQuota(
        tool="zhipu_payg",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier("balance_" + unit, balance, unit)],
        queried_at=now_millis(),
    )


# --------------------------------------------------------------------------
# 注册表
# --------------------------------------------------------------------------

QUERY_FUNCS: dict[str, Callable] = {
    "kimi": query_kimi,
    "zhipu": query_zhipu,
    "zhipu_team": query_zhipu_team,
    "minimax": query_minimax,
    "zenmux": query_zenmux,
    "opencode_go": query_opencode_go,
    "command_code": query_command_code,
    "opendesign": query_opendesign,
    "volcengine": query_volcengine,
    "deepseek": query_deepseek,
    "stepfun": query_stepfun,
    "siliconflow": query_siliconflow,
    "openrouter": query_openrouter,
    "novita": query_novita,
    "ollama_cloud": query_ollama_cloud,
    "zhipu_payg": query_zhipu_payg,
}


def _register_zcode() -> None:
    """ZCode 单独模块（避免循环导入）"""
    from app.services.subscription_quota.providers_zcode import query_zcode

    QUERY_FUNCS["zcode"] = query_zcode


_register_zcode()
