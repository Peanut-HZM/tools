"""订阅额度查询编排层

* 并发查询各供应商（单家失败不影响其它家）
* 60 秒进程内短缓存，避免频繁刷新打爆官方接口
* 缓存与并发都用最简单的结构，不引入额外依赖
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Iterable, Optional

from app.services.subscription_quota.credentials import (
    CREDENTIAL_READERS,
    Credential,
    detect_credentials,
)
from app.services.subscription_quota.models import (
    CredentialStatus,
    SubscriptionQuota,
)
from app.services.subscription_quota.providers import PROVIDERS, ProviderTransientError

logger = logging.getLogger(__name__)

#: 支持的供应商（顺序即前端展示顺序）
KNOWN_TOOLS: tuple[str, ...] = (
    "claude",
    "codex",
    "gemini",
    "kimi",
    "minimax",
    "zhipu",
)

#: 展示名（前端也有一份，后端返回用于兜底）
TOOL_DISPLAY_NAMES = {
    "claude": "Claude Code",
    "codex": "Codex (ChatGPT)",
    "gemini": "Gemini CLI",
    "kimi": "Kimi Code",
    "minimax": "MiniMax",
    "zhipu": "智谱 GLM",
}

CACHE_TTL_SECONDS = 60.0

_cache_lock = threading.Lock()
#: tool -> (expires_at_monotonic, result)
_cache: dict[str, tuple[float, SubscriptionQuota]] = {}


def _cache_get(tool: str) -> Optional[SubscriptionQuota]:
    with _cache_lock:
        entry = _cache.get(tool)
        if entry is None:
            return None
        expires_at, result = entry
        if expires_at <= time.monotonic():
            _cache.pop(tool, None)
            return None
        return result


def _cache_put(tool: str, result: SubscriptionQuota) -> None:
    with _cache_lock:
        _cache[tool] = (time.monotonic() + CACHE_TTL_SECONDS, result)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def describe_credentials() -> list[dict]:
    """列出所有供应商与本地凭据状态（**不含任何 token**）"""
    detected = detect_credentials()
    rows = []
    for tool in KNOWN_TOOLS:
        cred: Credential = detected.get(tool) or Credential()
        rows.append(
            {
                "tool": tool,
                "displayName": TOOL_DISPLAY_NAMES.get(tool, tool),
                "credentialStatus": cred.status,
                "credentialMessage": cred.message,
                "hasCredential": bool(cred.token),
                "supported": tool in PROVIDERS,
            }
        )
    return rows


async def _query_one(tool: str) -> SubscriptionQuota:
    query = PROVIDERS.get(tool)
    if query is None:
        return SubscriptionQuota.not_found(tool)

    reader = CREDENTIAL_READERS.get(tool)
    if reader is None:
        return SubscriptionQuota.not_found(tool)

    try:
        cred = reader()
    except Exception as exc:
        logger.warning("读取 %s 凭据异常: %s", tool, exc)
        return SubscriptionQuota.failure(
            tool, CredentialStatus.PARSE_ERROR, f"读取凭据异常: {type(exc).__name__}"
        )

    if not cred.token and cred.status in (
        CredentialStatus.NOT_FOUND,
        CredentialStatus.PARSE_ERROR,
    ):
        # 没有凭据就不打网络请求，直接如实返回
        if cred.status == CredentialStatus.NOT_FOUND:
            return SubscriptionQuota.not_found(tool)
        return SubscriptionQuota.failure(
            tool, CredentialStatus.PARSE_ERROR, cred.message or "凭据解析失败"
        )

    try:
        return await query(cred)
    except ProviderTransientError as exc:
        return SubscriptionQuota.failure(
            tool, cred.status or CredentialStatus.VALID, f"网络请求失败: {exc}"
        )
    except Exception as exc:  # 单家异常不影响其它家
        logger.exception("查询 %s 额度异常", tool)
        return SubscriptionQuota.failure(
            tool, CredentialStatus.VALID, f"查询异常: {type(exc).__name__}: {exc}"
        )


async def query_quotas(
    tools: Optional[Iterable[str]] = None,
    *,
    force_refresh: bool = False,
) -> list[SubscriptionQuota]:
    """并发查询指定供应商的额度

    :param tools: 供应商 id 列表；省略时查全部
    :param force_refresh: True 时忽略缓存
    """
    if tools is None:
        selected = list(KNOWN_TOOLS)
    else:
        selected = [t for t in tools if t in KNOWN_TOOLS]

    results: dict[str, SubscriptionQuota] = {}
    pending: list[str] = []
    for tool in selected:
        if not force_refresh:
            cached = _cache_get(tool)
            if cached is not None:
                results[tool] = cached
                continue
        pending.append(tool)

    if pending:
        tasks = [asyncio.create_task(_query_one(tool)) for tool in pending]
        done = await asyncio.gather(*tasks, return_exceptions=True)
        for tool, outcome in zip(pending, done):
            if isinstance(outcome, BaseException):
                logger.warning("查询 %s 额度出现未捕获异常: %s", tool, outcome)
                result = SubscriptionQuota.failure(
                    tool, CredentialStatus.VALID, f"查询异常: {type(outcome).__name__}"
                )
            else:
                result = outcome
            results[tool] = result
            _cache_put(tool, result)

    return [results[tool] for tool in selected if tool in results]
