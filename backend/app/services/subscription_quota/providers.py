"""各供应商的官方订阅额度查询

每个 provider 接受「凭据读取结果」，返回统一的 :class:`SubscriptionQuota`。
实现对照 cc-switch：
* ``src-tauri/src/services/subscription.rs``（Claude / Codex / Gemini）
* ``src-tauri/src/services/coding_plan.rs``（Kimi / MiniMax / 智谱）

约定：
* 网络 / 超时等瞬时失败 → 抛 :class:`ProviderTransientError`，由编排层转成
  可重试的失败结果（不伪造数据）
* 鉴权失败 / 非 2xx / 响应体不合法 → 返回 ``success=False`` 的真实错误
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.services.subscription_quota.credentials import Credential
from app.services.subscription_quota.models import (
    CredentialStatus,
    QuotaTier,
    SubscriptionQuota,
    millis_to_iso,
    now_millis,
)

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 15.0
USER_AGENT = "ToolboxSubscriptionQuota/1.0"


class ProviderTransientError(RuntimeError):
    """瞬时错误（网络 / 超时 / 读体中断）"""


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------


async def _get_json(
    url: str,
    headers: dict[str, str],
    *,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> tuple[Optional[int], Any, Optional[str]]:
    """GET → (status, json, error)

    * 网络错误 → 抛 ProviderTransientError
    * 非 2xx → 返回 (status, None, 响应片段)
    * JSON 解析失败 → 返回 (status, None, 错误描述)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ProviderTransientError(f"网络错误: {type(exc).__name__}") from exc

    if not resp.is_success:
        body = (resp.text or "").strip().replace("\n", " ")[:300]
        return resp.status_code, None, body or f"HTTP {resp.status_code}"
    try:
        return resp.status_code, resp.json(), None
    except ValueError as exc:
        return resp.status_code, None, f"响应不是合法 JSON: {exc}"


async def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict,
    *,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> tuple[Optional[int], Any, Optional[str]]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ProviderTransientError(f"网络错误: {type(exc).__name__}") from exc

    if not resp.is_success:
        body = (resp.text or "").strip().replace("\n", " ")[:300]
        return resp.status_code, None, body or f"HTTP {resp.status_code}"
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


def _auth_error(tool: str, status: int) -> SubscriptionQuota:
    return SubscriptionQuota.failure(
        tool,
        CredentialStatus.EXPIRED,
        f"认证失败（HTTP {status}），请重新登录该 CLI",
    )


# ---------------------------------------------------------------------------
# Claude（Anthropic OAuth）
# ---------------------------------------------------------------------------

CLAUDE_TIER_ORDER = ("five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet")


def parse_claude_usage(body: dict) -> list[QuotaTier]:
    """解析 Anthropic ``/api/oauth/usage`` 响应

    兼容两种形态：
    * 旧版顶层窗口：``{"five_hour": {"utilization": 13, "resets_at": ...}}``
    * 新版 ``limits[]``：``{"kind": "weekly_scoped", "scope": {"model": {"display_name": "Opus"}}, "percent": 40}``
    """
    tiers: list[QuotaTier] = []
    for name in CLAUDE_TIER_ORDER:
        window = body.get(name)
        if not isinstance(window, dict):
            continue
        utilization = _num(window.get("utilization"))
        if utilization is None:
            continue
        tiers.append(
            QuotaTier(
                name=name,
                utilization=utilization,
                resets_at=window.get("resets_at"),
            )
        )

    # 新格式里模型专属周限额放在 limits[]，覆盖同名旧窗口
    limits = body.get("limits")
    if isinstance(limits, list):
        scoped = {"fable": "seven_day_fable", "opus": "seven_day_opus", "sonnet": "seven_day_sonnet"}
        seen: set[str] = set()
        for item in limits:
            if not isinstance(item, dict):
                continue
            if item.get("kind") != "weekly_scoped" or item.get("group") != "weekly":
                continue
            scope = item.get("scope")
            surface = None
            if isinstance(scope, dict):
                surface = scope.get("surface")
            if surface:
                # 特定使用场景的子限额不并入整个模型的周限额
                continue
            model_name = ""
            if isinstance(scope, dict):
                model = scope.get("model")
                if isinstance(model, dict):
                    model_name = str(model.get("display_name") or "")
            tier_name = scoped.get(model_name.strip().lower())
            if not tier_name or tier_name in seen:
                continue
            percent = _num(item.get("percent"))
            if percent is None or percent < 0:
                continue
            seen.add(tier_name)
            tier = QuotaTier(
                name=tier_name,
                utilization=percent,
                resets_at=item.get("resets_at"),
            )
            existing = next((t for t in tiers if t.name == tier_name), None)
            if existing is not None:
                tiers[tiers.index(existing)] = tier
            else:
                tiers.append(tier)

    order = {name: index for index, name in enumerate(CLAUDE_TIER_ORDER)}
    tiers.sort(key=lambda t: order.get(t.name, len(order)))
    return tiers


async def query_claude(cred: Credential) -> SubscriptionQuota:
    if cred.status == CredentialStatus.NOT_FOUND:
        return SubscriptionQuota.not_found("claude")
    if cred.status == CredentialStatus.PARSE_ERROR:
        return SubscriptionQuota.failure(
            "claude", CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )
    if not cred.token:
        return SubscriptionQuota.failure(
            "claude", cred.status, cred.message or "未检测到 Claude Code 登录"
        )

    status, body, err = await _get_json(
        "https://api.anthropic.com/api/oauth/usage",
        {
            "Authorization": f"Bearer {cred.token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    if status in (401, 403):
        return _auth_error("claude", status)
    if err is not None:
        return SubscriptionQuota.failure("claude", CredentialStatus.VALID, f"接口错误: {err}")
    if not isinstance(body, dict):
        return SubscriptionQuota.failure("claude", CredentialStatus.VALID, "响应结构异常")

    return SubscriptionQuota(
        tool="claude",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=parse_claude_usage(body),
        queried_at=now_millis(),
    )


# ---------------------------------------------------------------------------
# Codex（ChatGPT）
# ---------------------------------------------------------------------------

CODEX_PLAN_LABELS = {
    "free": "Free",
    "go": "Go",
    "plus": "Plus",
    "prolite": "Pro 100",
    "pro": "Pro 200",
    "promax": "Pro 500",
    "team": "Business",
    "self_serve_business_usage_based": "Business",
    "self_serve_business_prolite": "Business Premium",
    "edu": "Edu",
    "edu_plus": "Edu Plus",
    "edu_pro": "Edu Pro",
}


def codex_plan_label(plan_type: Optional[str]) -> Optional[str]:
    if not plan_type:
        return None
    key = plan_type.strip().lower()
    if key in ("", "unknown"):
        return None
    label = CODEX_PLAN_LABELS.get(key)
    if label:
        return label
    if key == "business" or key == "ent26" or key.startswith("enterprise"):
        return "Enterprise"
    return " ".join(word.capitalize() for word in key.replace("-", "_").split("_") if word)


def window_tier_name(seconds: Optional[int]) -> str:
    if seconds == 18000:
        return "five_hour"
    if seconds == 604800:
        return "seven_day"
    if seconds == 2592000:
        return "30_day"
    if not seconds:
        return "unknown"
    hours = seconds // 3600
    if hours >= 24:
        return f"{hours // 24}_day"
    return f"{hours}_hour"


def parse_codex_usage(body: dict) -> tuple[list[QuotaTier], Optional[str], Optional[float]]:
    """返回 (tiers, plan_type, credits_balance)"""
    tiers: list[QuotaTier] = []
    rate_limit = body.get("rate_limit")
    if isinstance(rate_limit, dict):
        for key in ("primary_window", "secondary_window"):
            window = rate_limit.get(key)
            if not isinstance(window, dict):
                continue
            used = _num(window.get("used_percent"))
            if used is None:
                continue
            seconds = None
            raw_seconds = _num(window.get("limit_window_seconds"))
            if raw_seconds is not None:
                seconds = int(raw_seconds)
            reset_at = _num(window.get("reset_at"))
            tiers.append(
                QuotaTier(
                    name=window_tier_name(seconds),
                    utilization=used,
                    # 已用量为 0 时上游可能返回占位重置时间，隐藏以免虚假倒计时
                    resets_at=None
                    if used == 0.0
                    else millis_to_iso(int(reset_at * 1000) if reset_at else None),
                )
            )

    plan_type = body.get("plan_type") if isinstance(body.get("plan_type"), str) else None

    credits_balance = None
    credits = body.get("credits")
    if isinstance(credits, dict):
        has_credits = credits.get("has_credits") is True
        unlimited = credits.get("unlimited") is True
        balance = _num(credits.get("balance"))
        if has_credits and not unlimited and balance is not None and balance > 0:
            credits_balance = balance

    return tiers, plan_type, credits_balance


async def query_codex(cred: Credential) -> SubscriptionQuota:
    if cred.status == CredentialStatus.NOT_FOUND:
        return SubscriptionQuota.not_found("codex")
    if cred.status == CredentialStatus.PARSE_ERROR:
        return SubscriptionQuota.failure(
            "codex", CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )
    if not cred.token:
        return SubscriptionQuota.failure(
            "codex", cred.status, cred.message or "未检测到 Codex 登录"
        )

    headers = {
        "Authorization": f"Bearer {cred.token}",
        "User-Agent": "codex-cli",
        "Accept": "application/json",
    }
    account_id = cred.extras.get("account_id")
    if account_id:
        headers["ChatGPT-Account-Id"] = str(account_id)

    status, body, err = await _get_json("https://chatgpt.com/backend-api/wham/usage", headers)
    if status in (401, 403):
        return _auth_error("codex", status)
    if err is not None:
        return SubscriptionQuota.failure("codex", CredentialStatus.VALID, f"接口错误: {err}")
    if not isinstance(body, dict):
        return SubscriptionQuota.failure("codex", CredentialStatus.VALID, "响应结构异常")

    tiers, plan_type, _credits = parse_codex_usage(body)
    return SubscriptionQuota(
        tool="codex",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=tiers,
        plan_name=codex_plan_label(plan_type),
        queried_at=now_millis(),
    )


# ---------------------------------------------------------------------------
# Gemini（Google Cloud Code Assist）
# ---------------------------------------------------------------------------

def classify_gemini_model(model_id: str) -> str:
    if "flash-lite" in model_id:
        return "gemini_flash_lite"
    if "flash" in model_id:
        return "gemini_flash"
    if "pro" in model_id:
        return "gemini_pro"
    return model_id or "unknown"


def parse_gemini_buckets(buckets: list) -> list[QuotaTier]:
    """按模型分类，取每类最低 remainingFraction（最少剩余）"""
    best: dict[str, tuple[float, Optional[str]]] = {}
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        model_id = str(bucket.get("modelId") or "unknown")
        category = classify_gemini_model(model_id)
        remaining = _num(bucket.get("remainingFraction"))
        remaining = 1.0 if remaining is None else max(0.0, min(1.0, remaining))
        reset_time = bucket.get("resetTime")
        current = best.get(category)
        if current is None or remaining < current[0]:
            best[category] = (remaining, reset_time if isinstance(reset_time, str) else None)

    order = {"gemini_pro": 0, "gemini_flash": 1, "gemini_flash_lite": 2}
    tiers = [
        QuotaTier(name=name, utilization=(1.0 - remaining) * 100.0, resets_at=reset)
        for name, (remaining, reset) in best.items()
    ]
    tiers.sort(key=lambda t: order.get(t.name, 99))
    return tiers


def extract_project_id(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("id", "projectId"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
    return None


async def query_gemini(cred: Credential) -> SubscriptionQuota:
    if cred.status == CredentialStatus.NOT_FOUND:
        return SubscriptionQuota.not_found("gemini")
    if cred.status == CredentialStatus.PARSE_ERROR:
        return SubscriptionQuota.failure(
            "gemini", CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )
    if not cred.token:
        return SubscriptionQuota.failure(
            "gemini", cred.status, cred.message or "未检测到 Gemini CLI 登录"
        )

    headers = {
        "Authorization": f"Bearer {cred.token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    status, body, err = await _post_json(
        "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist",
        headers,
        {"metadata": {"ideType": "GEMINI_CLI", "pluginType": "GEMINI"}},
    )
    if status in (401, 403):
        return _auth_error("gemini", status)
    if err is not None:
        return SubscriptionQuota.failure("gemini", CredentialStatus.VALID, f"接口错误: {err}")

    project_id = None
    if isinstance(body, dict):
        project_id = extract_project_id(body.get("cloudaicompanionProject"))

    quota_payload: dict[str, Any] = {}
    if project_id:
        quota_payload["project"] = project_id

    status2, body2, err2 = await _post_json(
        "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota",
        headers,
        quota_payload,
    )
    if status2 in (401, 403):
        return _auth_error("gemini", status2)
    if err2 is not None:
        return SubscriptionQuota.failure("gemini", CredentialStatus.VALID, f"接口错误: {err2}")

    buckets = []
    if isinstance(body2, dict) and isinstance(body2.get("buckets"), list):
        buckets = body2["buckets"]

    return SubscriptionQuota(
        tool="gemini",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=parse_gemini_buckets(buckets),
        queried_at=now_millis(),
    )


# ---------------------------------------------------------------------------
# Kimi For Coding
# ---------------------------------------------------------------------------

KIMI_BASE_URL = "https://api.kimi.com/coding/v1"


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
            limit = _num(detail.get("limit"))
            remaining = _num(detail.get("remaining"))
            if limit is None:
                limit = 1.0
            if remaining is None:
                remaining = 0.0
            used = max(0.0, limit - remaining)
            utilization = (used / limit) * 100.0 if limit > 0 else 0.0
            tiers.append(
                QuotaTier(
                    name="five_hour",
                    utilization=utilization,
                    resets_at=detail.get("resetTime")
                    if isinstance(detail.get("resetTime"), str)
                    else millis_to_iso(int(_num(detail.get("resetTime")) or 0) or None),
                )
            )

    usage = body.get("usage")
    if isinstance(usage, dict):
        limit = _num(usage.get("limit"))
        remaining = _num(usage.get("remaining"))
        if limit is None:
            limit = 1.0
        if remaining is None:
            remaining = 0.0
        used = max(0.0, limit - remaining)
        utilization = (used / limit) * 100.0 if limit > 0 else 0.0
        reset_raw = usage.get("resetTime")
        tiers.append(
            QuotaTier(
                name="weekly_limit",
                utilization=utilization,
                resets_at=reset_raw
                if isinstance(reset_raw, str)
                else millis_to_iso(int(_num(reset_raw) or 0) or None),
            )
        )
    return tiers


async def query_kimi(cred: Credential) -> SubscriptionQuota:
    if cred.status == CredentialStatus.NOT_FOUND:
        return SubscriptionQuota.not_found("kimi")
    if cred.status == CredentialStatus.PARSE_ERROR:
        return SubscriptionQuota.failure(
            "kimi", CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )
    if not cred.token:
        return SubscriptionQuota.failure("kimi", cred.status, cred.message or "未检测到 Kimi Code 登录")

    headers = {
        "Authorization": f"Bearer {cred.token}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    status, body, err = await _get_json(f"{KIMI_BASE_URL}/usages", headers)
    if status in (401, 403):
        return _auth_error("kimi", status)
    if err is not None:
        return SubscriptionQuota.failure("kimi", CredentialStatus.VALID, f"接口错误: {err}")
    if not isinstance(body, dict):
        return SubscriptionQuota.failure("kimi", CredentialStatus.VALID, "响应结构异常")

    plan_name = None
    try:
        status2, me, err2 = await _get_json(f"{KIMI_BASE_URL}/me", headers, timeout=8.0)
        if err2 is None and isinstance(me, dict):
            level = me.get("user_level_name")
            if isinstance(level, str) and level:
                plan_name = level
    except ProviderTransientError:
        # 套餐名是附加信息，查询失败不影响额度
        pass

    return SubscriptionQuota(
        tool="kimi",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=parse_kimi_usages(body),
        plan_name=plan_name,
        queried_at=now_millis(),
    )


# ---------------------------------------------------------------------------
# MiniMax
# ---------------------------------------------------------------------------

MINIMAX_QUOTA_URL = "https://api.minimaxi.com/v1/api/openplatform/coding_plan/remains"


def parse_minimax_tiers(body: dict) -> list[QuotaTier]:
    tiers: list[QuotaTier] = []
    remains = body.get("model_remains")
    if not isinstance(remains, list):
        return tiers

    item = next(
        (
            entry
            for entry in remains
            if isinstance(entry, dict) and entry.get("model_name") == "general"
        ),
        None,
    )
    if item is None:
        return tiers

    interval_remaining = _num(item.get("current_interval_remaining_percent"))
    if interval_remaining is not None:
        reset_raw = _num(item.get("end_time"))
        tiers.append(
            QuotaTier(
                name="five_hour",
                utilization=100.0 - interval_remaining,
                resets_at=millis_to_iso(int(reset_raw)) if reset_raw else None,
            )
        )

    weekly_status = _num(item.get("current_weekly_status"))
    # 1 = 正常计时，2 = 本周额度已耗尽（照常展示），3 = 无周限额（不展示）
    if weekly_status in (1.0, 2.0):
        weekly_remaining = _num(item.get("current_weekly_remaining_percent"))
        if weekly_remaining is not None:
            reset_raw = _num(item.get("weekly_end_time"))
            tiers.append(
                QuotaTier(
                    name="weekly_limit",
                    utilization=100.0 - weekly_remaining,
                    resets_at=millis_to_iso(int(reset_raw)) if reset_raw else None,
                )
            )
    return tiers


async def query_minimax(cred: Credential) -> SubscriptionQuota:
    if cred.status == CredentialStatus.NOT_FOUND:
        return SubscriptionQuota.not_found("minimax")
    if cred.status == CredentialStatus.PARSE_ERROR:
        return SubscriptionQuota.failure(
            "minimax", CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )
    if not cred.token:
        return SubscriptionQuota.failure(
            "minimax", cred.status, cred.message or "未检测到 MiniMax 登录"
        )

    status, body, err = await _get_json(
        MINIMAX_QUOTA_URL,
        {
            "Authorization": f"Bearer {cred.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    if status in (401, 403):
        return _auth_error("minimax", status)
    if err is not None:
        return SubscriptionQuota.failure("minimax", CredentialStatus.VALID, f"接口错误: {err}")
    if not isinstance(body, dict):
        return SubscriptionQuota.failure("minimax", CredentialStatus.VALID, "响应结构异常")

    base_resp = body.get("base_resp")
    if isinstance(base_resp, dict):
        code = _num(base_resp.get("status_code"))
        if code not in (None, 0.0):
            message = base_resp.get("status_msg") or "未知错误"
            return SubscriptionQuota.failure(
                "minimax", CredentialStatus.VALID, f"接口返回错误（code {int(code)}）：{message}"
            )

    return SubscriptionQuota(
        tool="minimax",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=parse_minimax_tiers(body),
        queried_at=now_millis(),
    )


# ---------------------------------------------------------------------------
# 智谱 GLM
# ---------------------------------------------------------------------------

ZHIPU_QUOTA_URL = "https://open.bigmodel.cn/api/monitor/usage/quota/limit"


def _zhipu_window(item: dict) -> Optional[str]:
    """按 ``unit`` 判定窗口：3 → 5 小时，6 → 每周"""
    unit = _num(item.get("unit"))
    if unit == 3.0:
        return "five_hour"
    if unit == 6.0:
        return "weekly_limit"
    return None


def parse_zhipu_tiers(data: dict) -> list[QuotaTier]:
    """解析 ``data.limits[]``（个人版与团队版同一形态）"""
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

    # unit 缺失时的兜底：按重置时间升序依次填入仍空缺的窗口
    unclassified.sort(key=lambda item: (item[0] is not None, item[0] or 0.0))
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


async def query_zhipu(cred: Credential) -> SubscriptionQuota:
    if cred.status == CredentialStatus.NOT_FOUND:
        return SubscriptionQuota.not_found("zhipu")
    if cred.status == CredentialStatus.PARSE_ERROR:
        return SubscriptionQuota.failure(
            "zhipu", CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )
    if not cred.token:
        return SubscriptionQuota.failure("zhipu", cred.status, cred.message or "未检测到智谱登录")

    # 智谱的 Authorization 不带 Bearer 前缀（cc-switch 同款）
    status, body, err = await _get_json(
        ZHIPU_QUOTA_URL,
        {
            "Authorization": cred.token,
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh",
            "User-Agent": USER_AGENT,
        },
    )
    if status in (401, 403):
        return _auth_error("zhipu", status)
    if err is not None:
        return SubscriptionQuota.failure("zhipu", CredentialStatus.VALID, f"接口错误: {err}")
    if not isinstance(body, dict):
        return SubscriptionQuota.failure("zhipu", CredentialStatus.VALID, "响应结构异常")

    if body.get("success") is False:
        message = body.get("msg") or "未知错误"
        return SubscriptionQuota.failure(
            "zhipu", CredentialStatus.VALID, f"接口返回错误：{message}"
        )

    data = body.get("data")
    if not isinstance(data, dict):
        return SubscriptionQuota.failure("zhipu", CredentialStatus.VALID, "响应缺少 data 字段")

    level = data.get("level")
    return SubscriptionQuota(
        tool="zhipu",
        credential_status=CredentialStatus.VALID,
        success=True,
        tiers=parse_zhipu_tiers(data),
        plan_name=level if isinstance(level, str) and level else None,
        queried_at=now_millis(),
    )


# ---------------------------------------------------------------------------
# 注册表
# ---------------------------------------------------------------------------

PROVIDERS = {
    "claude": query_claude,
    "codex": query_codex,
    "gemini": query_gemini,
    "kimi": query_kimi,
    "minimax": query_minimax,
    "zhipu": query_zhipu,
}
