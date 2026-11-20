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


def _opendesign_api_base(raw: str) -> str:
    """把任意 OpenDesign 地址推导成**控制面** origin

    对齐 cc-switch `opendesign_api_base()`：

    * 推理地址 `amr-link.open-design.ai` → 控制面 `amr-api.open-design.ai`
    * 已经是 `-api` → 原样保留
    * 认不出（不是 open-design.ai 域名）→ 回落官方默认

    账单接口在控制面 host 上；拿推理 host 去查只会得到 404。
    """
    from urllib.parse import urlparse

    default = "https://amr-api.open-design.ai"
    try:
        parsed = urlparse((raw or "").strip())
    except ValueError:
        return default

    host = (parsed.hostname or "").lower()
    if not host or not host.endswith("open-design.ai"):
        return default
    if "-api" in host:
        api_host = host
    elif "-link" in host:
        api_host = host.replace("-link", "-api")
    else:
        # 裸域名 / 未知子域：官方控制面是 amr-api
        api_host = "amr-api." + host if host != "open-design.ai" else "amr-api.open-design.ai"

    scheme = parsed.scheme or "https"
    return f"{scheme}://{api_host}"


async def query_opendesign(account: QuotaAccount) -> SubscriptionQuota:
    """OpenDesign（AMR 套餐，5 小时 + 7 天双窗口）

    查询链路（与 cc-switch 一致）：

    1. ``GET {api_base}/api/v1/workspaces/current`` 取 workspaceId
    2. ``GET {api_base}/api/v1/workspaces/{id}/billing/snapshot`` 取
       ``designPlanWindows``（额度字段是**字符串**形式的 credits）

    ## 凭据

    账单接口**只认 AMR 控制面 Key**（``vela_ctrl_…``）。而推理配置里存的是
    运行时推理 Key（``sk-amr-ew__…``），拿它查账单必被拒。因此这里的取 Key
    顺序是：

    1. `extra.control_key` —— 用户显式填的控制面 Key
    2. `api_key` —— 若本身已是控制面形态
    3. 本机 cc-switch 库里的控制面 Key（只读发现，见 `opendesign_key`）

    三者都不是控制面形态时，返回明确的「需要 controlKey」提示，
    **不会**拿推理 Key 去撞接口。
    """
    from app.services.subscription_quota.opendesign_key import (
        is_control_key,
        looks_like_runtime_key,
        resolve_control_key,
    )

    api_base = _opendesign_api_base(_base_url(account))

    control_key, key_source = resolve_control_key(
        str(account.extra.get("control_key") or ""),
        account.api_key or "",
    )
    if not control_key:
        # 说清楚「为什么不行」：区分「存的是推理 Key」和「根本没配」
        stored = str(account.extra.get("control_key") or "") or (account.api_key or "")
        if looks_like_runtime_key(stored):
            return SubscriptionQuota.failure(
                "opendesign",
                CredentialStatus.EXPIRED,
                "当前存的是运行时推理 Key（sk-amr-ew__…），账单接口不接受；"
                "请在 OpenDesign 控制台复制控制面 controlKey（vela_ctrl_…）后填入。",
            )
        return SubscriptionQuota.failure(
            "opendesign",
            CredentialStatus.NOT_FOUND,
            "缺少 AMR 控制面 controlKey（vela_ctrl_…）："
            "可手动填写，或先在本机 cc-switch 里配好用量脚本后点「从 cc-switch 同步」。",
        )

    headers = {
        "Authorization": f"Bearer {control_key}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }

    status, current, err = await _request_json(
        "GET", f"{api_base}/api/v1/workspaces/current", headers
    )

    if status in (401, 403):
        # Cloudflare 1010 是 UA 被拦，不是 Key 无效 —— 必须区分开，
        # 否则会误导用户去换一个其实没问题的 Key。
        if err and "error-1010" in err or (err and "Access denied" in err):
            return _api_failure(
                "opendesign",
                "请求被 OpenDesign 前置的 Cloudflare 拒绝（Error 1010，UA 拦截），"
                "不是 Key 失效；请稍后重试或换网络环境。",
            )
        return SubscriptionQuota.failure(
            "opendesign",
            CredentialStatus.EXPIRED,
            f"控制面拒绝了该 controlKey（HTTP {status}）；"
            "请确认它是 OpenDesign 控制台的 controlKey（vela_ctrl_…）且未过期。",
        )
    if err is not None:
        return _api_failure("opendesign", f"控制面不可达: {err}")

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
            "opendesign",
            "控制面没有返回 workspaceId（可在账号配置里手动填写 workspace_id）",
        )

    status2, snapshot, err2 = await _request_json(
        "GET",
        f"{api_base}/api/v1/workspaces/{workspace_id}/billing/snapshot",
        headers,
    )
    if status2 in (401, 403):
        return SubscriptionQuota.failure(
            "opendesign",
            CredentialStatus.EXPIRED,
            f"计费快照接口拒绝该 controlKey（HTTP {status2}），请重新确认控制面 Key。",
        )
    if err2 is not None:
        return _api_failure("opendesign", f"billing/snapshot 失败: {err2}")
    if not isinstance(snapshot, dict):
        return _api_failure("opendesign", "billing/snapshot 响应结构异常")

    tiers = parse_opendesign_tiers(snapshot)
    if not tiers:
        return _api_failure(
            "opendesign", "快照里没有可识别的 designPlanWindows 额度窗口"
        )

    logger.info(
        "OpenDesign 额度查询成功: workspace=%s 窗口=%d key来源=%s",
        workspace_id,
        len(tiers),
        key_source,
    )
    # plan.tier 是套餐代号（go / pro …），与其它供应商卡片上的套餐徽章一致
    plan_name = None
    plan = snapshot.get("plan")
    if isinstance(plan, dict):
        tier_name = plan.get("tier")
        if isinstance(tier_name, str) and tier_name.strip():
            plan_name = tier_name.strip()

    return SubscriptionQuota(
        tool="opendesign",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=plan_name,
        queried_at=now_millis(),
    )


def parse_opendesign_tiers(body: dict) -> list[QuotaTier]:
    """解析 ``billing/snapshot`` 的 ``designPlanWindows``

    实测响应（2026-11）::

        {"kind": "5h", "windowStart": "...", "resetsAt": "...",
         "remainingCredits": "48598", "limitCredits": "50000"}

    要点：

    * 额度字段是**字符串**形式的 credits，必须走 `_num` 转换
    * `kind` 只有 `5h` / `7d` 两种是套餐窗口，其余忽略
    * `limitCredits <= 0` 视为脏数据跳过（避免除零）
    * `remainingCredits` 缺失时按 0 已用处理（不编造额度）
    """
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
        if limit is None or limit <= 0:
            continue
        remaining = _num(window.get("remainingCredits"))
        used = 0.0 if remaining is None else max(0.0, min(limit, limit - remaining))
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
# 从 agent-hub 合并过来的通用模板（newapi / sub2api / generic_balance / manual）
# --------------------------------------------------------------------------


async def query_newapi(account: QuotaAccount) -> SubscriptionQuota:
    """NewAPI 中转站：``GET {base}/api/user/self``，quota ÷ 500000 = USD"""
    base = _base_url(account).rstrip("/")
    if not base:
        return _api_failure("newapi", "NewAPI 需要填写站点地址（base_url）")

    headers = {
        "Authorization": f"Bearer {account.api_key or ''}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    user_id = account.extra.get("user_id")
    if user_id:
        headers["New-Api-User"] = str(user_id)

    status, body, err = await _request_json("GET", f"{base}/api/user/self", headers)
    if status in (401, 403):
        return _auth_failure("newapi", status)
    if err is not None:
        return _api_failure("newapi", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("newapi", "响应结构异常")

    if body.get("success") is False:
        return _api_failure("newapi", f"站点返回错误：{body.get('message') or '未知错误'}")

    data = body.get("data") if isinstance(body.get("data"), dict) else body
    quota = _num(data.get("quota"))
    used = _num(data.get("used_quota"))
    if quota is None:
        return _api_failure("newapi", "响应缺少 quota 字段")

    # NewAPI 的 quota 单位是 1/500000 USD
    total_usd = quota / 500000.0
    used_usd = (used or 0.0) / 500000.0
    remaining = total_usd - used_usd
    return SubscriptionQuota(
        tool="newapi",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier("balance_USD", remaining, "USD")],
        queried_at=now_millis(),
    )


async def query_sub2api(account: QuotaAccount) -> SubscriptionQuota:
    """Sub2API 中转站：``GET {base}/v1/usage`` → quota{limit,used}"""
    base = _base_url(account).rstrip("/")
    if not base:
        return _api_failure("sub2api", "Sub2API 需要填写站点地址（base_url）")

    status, body, err = await _request_json("GET", f"{base}/v1/usage", _bearer(account))
    if status in (401, 403):
        return _auth_failure("sub2api", status)
    if err is not None:
        return _api_failure("sub2api", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("sub2api", "响应结构异常")

    quota = body.get("quota") if isinstance(body.get("quota"), dict) else body
    limit = _num(quota.get("limit"))
    used = _num(quota.get("used"))
    if limit is None or limit <= 0:
        return _api_failure("sub2api", "响应缺少有效的 limit 字段")

    used_value = used or 0.0
    tiers = [
        QuotaTier(
            name="monthly",
            utilization=max(0.0, min(100.0, used_value / limit * 100.0)),
            resets_at=None,
        )
    ]
    return SubscriptionQuota(
        tool="sub2api",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        queried_at=now_millis(),
    )


async def query_generic_balance(account: QuotaAccount) -> SubscriptionQuota:
    """通用余额：``GET {base}/user/balance``，自动识别字段名"""
    base = _base_url(account).rstrip("/")
    if not base:
        return _api_failure("generic_balance", "通用余额需要填写站点地址（base_url）")

    status, body, err = await _request_json("GET", f"{base}/user/balance", _bearer(account))
    if status in (401, 403):
        return _auth_failure("generic_balance", status)
    if err is not None:
        return _api_failure("generic_balance", f"接口错误: {err}")
    if not isinstance(body, dict):
        return _api_failure("generic_balance", "响应结构异常")

    data = body.get("data") if isinstance(body.get("data"), dict) else body
    amount = None
    unit = "USD"
    for key in ("balance", "total_balance", "availableBalance", "available_balance", "totalBalance"):
        value = _num(data.get(key))
        if value is not None:
            amount = value
            break
    if amount is None:
        infos = data.get("balance_infos")
        if isinstance(infos, list):
            for info in infos:
                if not isinstance(info, dict):
                    continue
                value = _num(info.get("total_balance"))
                if value is not None:
                    amount = value
                    unit = str(info.get("currency") or "USD")
                    break
    if amount is None:
        return _api_failure("generic_balance", "响应里找不到可识别的余额字段")

    return SubscriptionQuota(
        tool="generic_balance",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[balance_tier(f"balance_{unit}", amount, unit)],
        queried_at=now_millis(),
    )


async def query_manual_quota(account: QuotaAccount) -> SubscriptionQuota:
    """手动额度订阅：不查网络，直接读账号上的 manual_total / manual_used"""
    total = float(account.manual_total or 0)
    used = float(account.manual_used or 0)
    unit = account.quota_unit or "credits"

    if total <= 0:
        # 没有总额度时按余额型展示「已用」
        tier = balance_tier(f"balance_{unit}", used, unit)
        return SubscriptionQuota(
            tool="manual",
            credential_status=CredentialStatus.VALID,
            success=True,
            tiers=[tier],
            queried_at=now_millis(),
        )

    utilization = max(0.0, min(100.0, used / total * 100.0))
    tier = QuotaTier(
        name=f"manual_{account.window_type or 'none'}",
        utilization=utilization,
        resets_at=account.window_reset_at or None,
    )
    tier.balance_amount = max(0.0, total - used)
    tier.balance_unit = unit
    return SubscriptionQuota(
        tool="manual",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=[tier],
        plan_name=account.label or None,
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
    # ---- 从 agent-hub 合并 ----
    "newapi": query_newapi,
    "sub2api": query_sub2api,
    "generic_balance": query_generic_balance,
    "manual": query_manual_quota,
}


def _register_zcode() -> None:
    """ZCode 单独模块（避免循环导入）"""
    from app.services.subscription_quota.providers_zcode import query_zcode

    QUERY_FUNCS["zcode"] = query_zcode


_register_zcode()
