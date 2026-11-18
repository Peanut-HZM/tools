"""网关转发核心：模型解析 → 账号选择 → 掩码 → 转发 → 还原

设计要点（对齐 magpie）：

* **协议透传**：OpenAI Chat 与 Anthropic Messages 原样转发，只改 base_url 与鉴权头
* **多账号 failover**：同 provider 多个账号时，失败或额度耗尽的自动换下一个
* **隐私掩码**：请求离开前脱敏，回复回到 agent 前还原
* **只读边界**：网关不改写任何 CLI 配置文件，只提供端点供用户手动指向
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from app.services.gateway.masking import MaskingSession, mask_request_body
from app.services.gateway.upstreams import get_upstream, resolve_base
from app.services.subscription_quota.accounts import QuotaAccount, list_accounts

logger = logging.getLogger(__name__)

UPSTREAM_TIMEOUT = 300.0


class GatewayError(RuntimeError):
    """网关自身错误（无可用账号、模型未知等）"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class RouteTarget:
    """解析出来的一个可转发目标"""

    provider_id: str
    model: str
    account: QuotaAccount
    base_url: str


def parse_model(model: str) -> tuple[Optional[str], str]:
    """``kimi/k3`` → ("kimi", "k3")；无前缀时返回 (None, model)"""
    if "/" in model:
        provider, _, rest = model.partition("/")
        if provider and rest:
            return provider, rest
    return None, model


def _accounts_for(user_id: str, provider_id: str) -> list[QuotaAccount]:
    return [
        a
        for a in list_accounts(user_id, only_enabled=True)
        if a.provider_id == provider_id
    ]


def resolve_targets(
    user_id: str,
    model: str,
    *,
    protocol: str,
) -> list[RouteTarget]:
    """按模型名解析出候选目标列表（顺序即失败切换顺序）"""
    provider_id, bare_model = parse_model(model)

    if provider_id is None:
        # 没写前缀：用第一个「支持该协议」的供应商
        candidates: list[RouteTarget] = []
        for account in list_accounts(user_id, only_enabled=True):
            spec = get_upstream(account.provider_id)
            if spec is None:
                continue
            base = resolve_base(account.provider_id, account.extra, protocol)
            if base:
                candidates.append(
                    RouteTarget(
                        provider_id=account.provider_id,
                        model=bare_model,
                        account=account,
                        base_url=base,
                    )
                )
        if not candidates:
            raise GatewayError(
                f"模型 {model!r} 没有写供应商前缀，且没有可用的 {protocol} 供应商",
                status_code=400,
            )
        return candidates

    accounts = sorted(_accounts_for(user_id, provider_id), key=lambda a: a.sort_order)
    if not accounts:
        raise GatewayError(f"供应商 {provider_id!r} 还没有配置账号", status_code=404)

    targets: list[RouteTarget] = []
    for account in accounts:
        base = resolve_base(provider_id, account.extra, protocol)
        if not base:
            logger.debug("供应商 %s 的账号 %s 不支持 %s 协议", provider_id, account.id, protocol)
            continue
        targets.append(
            RouteTarget(
                provider_id=provider_id,
                model=bare_model,
                account=account,
                base_url=base,
            )
        )

    if not targets:
        raise GatewayError(
            f"供应商 {provider_id!r} 没有可用于 {protocol} 协议的入口地址", status_code=400
        )
    return targets


def build_upstream_request(
    target: RouteTarget, protocol: str, body: dict
) -> tuple[str, dict[str, str], dict]:
    """构造发往上游的 (url, headers, body)"""
    spec = get_upstream(target.provider_id)
    api_key = target.account.api_key or target.account.extra.get("api_key") or ""
    if not api_key:
        raise GatewayError(f"账号 {target.account.label} 缺少 API Key", status_code=400)

    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}

    if protocol == "anthropic":
        url = f"{target.base_url.rstrip('/')}/v1/messages"
        if spec and spec.auth_style == "x-api-key":
            headers["x-api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        if spec and spec.anthropic_beta:
            headers["anthropic-beta"] = spec.anthropic_beta
        if body.get("stream"):
            headers["Accept"] = "text/event-stream"
    else:
        url = f"{target.base_url.rstrip('/')}/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        if body.get("stream"):
            headers["Accept"] = "text/event-stream"

    patched = dict(body)
    patched["model"] = target.model
    return url, headers, patched


async def forward_json(
    target: RouteTarget,
    protocol: str,
    body: dict,
) -> tuple[int, dict]:
    """非流式转发，返回 (status, json)"""
    url, headers, patched = build_upstream_request(target, protocol, body)
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=patched)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise GatewayError(f"上游网络错误: {type(exc).__name__}", status_code=502) from exc

    try:
        payload = resp.json()
    except ValueError:
        payload = {"error": {"message": (resp.text or "")[:500]}}

    return resp.status_code, payload


async def forward_stream(
    target: RouteTarget,
    protocol: str,
    body: dict,
) -> AsyncIterator[bytes]:
    """流式转发，逐块 yield 上游原始字节"""
    url, headers, patched = build_upstream_request(target, protocol, body)
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            async with client.stream("POST", url, headers=headers, json=patched) as resp:
                if resp.status_code >= 400:
                    raw = await resp.aread()
                    raise GatewayError(
                        f"上游返回 {resp.status_code}: {raw[:300].decode('utf-8', 'ignore')}",
                        status_code=resp.status_code,
                    )
                async for chunk in resp.aiter_raw():
                    if chunk:
                        yield chunk
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise GatewayError(f"上游网络错误: {type(exc).__name__}", status_code=502) from exc


def prepare_masked_body(
    body: dict, session: MaskingSession
) -> tuple[dict, int]:
    """对请求体做隐私掩码（只处理文本内容，结构不变）"""
    if not session.enabled:
        return body, 0

    messages = body.get("messages")
    if not isinstance(messages, list):
        return body, 0

    masked_messages, hits = mask_request_body(messages, session)
    patched = dict(body)
    patched["messages"] = masked_messages

    # 系统提示同样可能带密钥
    system = patched.get("system")
    if isinstance(system, str):
        masked_system, system_hits = session.mask(system)
        patched["system"] = masked_system
        hits += system_hits
    elif isinstance(system, list):
        masked_system, system_hits = mask_request_body(system, session)
        patched["system"] = masked_system
        hits += system_hits

    return patched, hits


def sse_unmask_bytes(chunk: bytes, session: MaskingSession) -> bytes:
    """把 SSE 分块里的占位符还原成原值

    SSE 的 data 行是 JSON；占位符是纯 ASCII，可以在字节层面安全替换。
    这里按 UTF-8 解码后替换再编码，失败时原样返回。
    """
    if not session.mapping:
        return chunk
    try:
        text = chunk.decode("utf-8")
    except UnicodeDecodeError:
        return chunk
    restored = session.unmask(text)
    if restored == text:
        return chunk
    return restored.encode("utf-8")


def sse_event(payload: dict) -> bytes:
    """构造一条 SSE 事件（用于网关自己产生的错误 / 心跳）"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
