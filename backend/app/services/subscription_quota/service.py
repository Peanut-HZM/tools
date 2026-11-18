"""订阅额度查询编排层（v2）

两路来源：
1. **用户添加的账号**（`subscription_quota_accounts` 表）——一个提供商一条，靠 API Key
2. **本机 CLI 订阅**（Claude / Codex / Gemini）——自动发现已有登录

只返回**已配置**的项；未配置的供应商不会出现在结果里。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Iterable, Optional

from app.services.subscription_quota.accounts import (
    QuotaAccount,
    list_accounts,
)
from app.services.subscription_quota.credentials import (
    CREDENTIAL_READERS,
    Credential,
    detect_credentials,
)
from app.services.subscription_quota.local_credentials import discover_local_accounts
from app.services.subscription_quota.models import (
    CredentialStatus,
    SubscriptionQuota,
)
from app.services.subscription_quota.providers import PROVIDERS as LEGACY_PROVIDERS
from app.services.subscription_quota.providers_full import (
    QUERY_FUNCS,
    ProviderTransientError,
)
from app.services.subscription_quota.registry import (
    ALL_PROVIDER_IDS,
    MANUAL_PROVIDER_IDS,
    PROVIDER_SPECS,
    SUBSCRIPTION_IDS,
    get_spec,
)

logger = logging.getLogger(__name__)

#: 兼容旧引用
KNOWN_TOOLS = ALL_PROVIDER_IDS

TOOL_DISPLAY_NAMES = {spec.id: spec.name for spec in PROVIDER_SPECS}

CACHE_TTL_SECONDS = 60.0
_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, SubscriptionQuota]] = {}


def _cache_key(user_id: str, account_id: str) -> str:
    return f"{user_id}:{account_id}"


def _cache_get(key: str) -> Optional[SubscriptionQuota]:
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expires_at, result = entry
        if expires_at <= time.monotonic():
            _cache.pop(key, None)
            return None
        return result


def _cache_put(key: str, result: SubscriptionQuota) -> None:
    with _cache_lock:
        _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, result)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def describe_credentials() -> list[dict]:
    """本机订阅类凭据状态（只用于 subscription 类供应商，不含 token）"""
    detected = detect_credentials()
    rows = []
    for tool in SUBSCRIPTION_IDS:
        spec = get_spec(tool)
        cred: Credential = detected.get(tool) or Credential()
        rows.append(
            {
                "providerId": tool,
                "name": spec.name if spec else tool,
                "credentialStatus": cred.status,
                "credentialMessage": cred.message,
                "hasCredential": bool(cred.token),
                "localSource": spec.local_source if spec else None,
            }
        )
    return rows


async def _query_subscription(tool: str) -> SubscriptionQuota:
    """订阅类：靠本机 CLI 登录"""
    reader = CREDENTIAL_READERS.get(tool)
    query = LEGACY_PROVIDERS.get(tool)
    if reader is None or query is None:
        return SubscriptionQuota.not_found(tool)

    try:
        cred = reader()
    except Exception as exc:
        logger.warning("读取 %s 凭据异常: %s", tool, exc)
        return SubscriptionQuota.failure(
            tool, CredentialStatus.PARSE_ERROR, f"读取凭据异常: {type(exc).__name__}"
        )

    if not cred.token:
        return (
            SubscriptionQuota.not_found(tool)
            if cred.status == CredentialStatus.NOT_FOUND
            else SubscriptionQuota.failure(
                tool, CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
            )
        )

    try:
        return await query(cred)
    except ProviderTransientError as exc:
        return SubscriptionQuota.failure(tool, CredentialStatus.VALID, f"网络请求失败: {exc}")
    except Exception as exc:
        logger.exception("查询订阅 %s 额度异常", tool)
        return SubscriptionQuota.failure(
            tool, CredentialStatus.VALID, f"查询异常: {type(exc).__name__}: {exc}"
        )


async def _query_account(account: QuotaAccount) -> SubscriptionQuota:
    """用户添加的账号（或本机自动发现的虚拟账号）"""
    func = QUERY_FUNCS.get(account.provider_id)
    if func is None:
        return SubscriptionQuota.failure(
            account.provider_id, CredentialStatus.PARSE_ERROR, "未知供应商类型"
        )
    if not account.api_key and not account.extra.get("control_key") and not (
        account.extra.get("access_key") and account.extra.get("secret_key")
    ):
        return SubscriptionQuota.failure(
            account.provider_id, CredentialStatus.NOT_FOUND, "该账号没有配置 API Key"
        )

    try:
        quota = await func(account)
    except ProviderTransientError as exc:
        return SubscriptionQuota.failure(
            account.provider_id, CredentialStatus.VALID, f"网络请求失败: {exc}"
        )
    except Exception as exc:
        logger.exception("查询账号 %s 额度异常", account.id)
        return SubscriptionQuota.failure(
            account.provider_id, CredentialStatus.VALID, f"查询异常: {type(exc).__name__}: {exc}"
        )

    # 用账号标签覆盖显示名，方便多账号区分
    if account.label:
        quota.label = account.label  # type: ignore[attr-defined]
    return quota


async def query_for_accounts(
    user_id: str,
    account_ids: Optional[Iterable[str]] = None,
    *,
    force_refresh: bool = False,
    include_local: bool = True,
) -> list[dict]:
    """查询指定账号（默认全部已启用账号）的额度。

    已配置但查询失败的也返回（带真实错误原因）；未配置的不会出现。
    本机 CLI 凭据（如 Kimi Code 登录）会作为虚拟账号一并查询。
    """
    accounts = list_accounts(user_id, only_enabled=True)

    if include_local and not account_ids:
        # 本机凭据作为虚拟账号，但与库里同 provider 的账号去重
        # （导入脚本会把同样的 Key 写进库，避免同一份额度显示两次）
        stored_providers = {a.provider_id for a in accounts}
        for local in discover_local_accounts():
            if local.provider_id in stored_providers:
                continue
            accounts.append(local)

    if account_ids is not None:
        wanted = {str(a) for a in account_ids}
        accounts = [a for a in accounts if a.id in wanted]

    tasks = []
    keys = []
    for account in accounts:
        key = _cache_key(user_id, account.id)
        keys.append((account, key))
        tasks.append(None)

    results: list[dict] = []
    pending: list[tuple[QuotaAccount, str]] = []
    for account, key in keys:
        if not force_refresh:
            cached = _cache_get(key)
            if cached is not None:
                results.append(_decorate(cached, account))
                continue
        pending.append((account, key))

    if pending:
        outcomes = await asyncio.gather(
            *[asyncio.create_task(_query_account(acc)) for acc, _ in pending],
            return_exceptions=True,
        )
        for (account, key), outcome in zip(pending, outcomes):
            if isinstance(outcome, BaseException):
                logger.warning("账号 %s 查询异常: %s", account.id, outcome)
                quota = SubscriptionQuota.failure(
                    account.provider_id, CredentialStatus.VALID, f"查询异常: {type(outcome).__name__}"
                )
            else:
                quota = outcome
            _cache_put(key, quota)
            results.append(_decorate(quota, account))

    # 保持账号顺序
    order = {a.id: i for i, a in enumerate(accounts)}
    results.sort(key=lambda item: order.get(item["accountId"], 0))
    return results


def _decorate(quota: SubscriptionQuota, account: QuotaAccount) -> dict:
    """把账号信息合并进返回结构（不含 Key）"""
    data = quota.to_dict()
    data["accountId"] = account.id
    data["providerId"] = account.provider_id
    spec = get_spec(account.provider_id)
    data["label"] = account.label or (spec.name if spec else account.provider_id)
    data["kind"] = spec.kind if spec else "window"
    data["maskedKey"] = account.masked_key()
    # 本机自动发现的账号标记（前端可显示「本机登录」）
    data["isLocal"] = account.id.startswith("local:")
    data["readOnly"] = account.id.startswith("local:")
    return data


async def query_subscriptions(
    *, force_refresh: bool = False
) -> list[dict]:
    """查询本机订阅类（Claude / Codex / Gemini）额度，只返回有凭据的。"""
    detected = detect_credentials()
    targets = [tool for tool in SUBSCRIPTION_IDS if (detected.get(tool) and detected[tool].token)]
    if not targets:
        return []

    outcomes = await asyncio.gather(
        *[asyncio.create_task(_query_subscription(tool)) for tool in targets],
        return_exceptions=True,
    )

    results: list[dict] = []
    for tool, outcome in zip(targets, outcomes):
        if isinstance(outcome, BaseException):
            logger.warning("订阅 %s 查询异常: %s", tool, outcome)
            quota = SubscriptionQuota.failure(
                tool, CredentialStatus.VALID, f"查询异常: {type(outcome).__name__}"
            )
        else:
            quota = outcome
        data = quota.to_dict()
        spec = get_spec(tool)
        data["providerId"] = tool
        data["label"] = spec.name if spec else tool
        data["kind"] = "subscription"
        data["accountId"] = None
        data["maskedKey"] = None
        results.append(data)
    return results


async def query_quotas(
    tools: Optional[Iterable[str]] = None,
    *,
    force_refresh: bool = False,
    user_id: Optional[str] = None,
) -> list[SubscriptionQuota]:
    """兼容旧接口：仅用于订阅类（无用户上下文时的内部调用）"""
    return await asyncio.gather(
        *[asyncio.create_task(_query_subscription(tool)) for tool in (tools or SUBSCRIPTION_IDS)],
    )
