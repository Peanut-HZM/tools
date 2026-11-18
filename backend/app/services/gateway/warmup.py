"""每日预热（对齐 magpie 的 Daily warm-up）

**目的**：Claude / ChatGPT 的 5 小时窗口从「第一次请求」开始计时。如果每天在固定
时间先发一次最小请求，窗口就会在你真正干活前开启，一天里能多用一个窗口。

**安全边界**：
* 默认关闭，必须用户显式开启
* 只对明确列出的账号生效（`warmup.targets`）
* 每次只发 `max_tokens=1` 的最小请求，成本可忽略
* 失败只记日志，不重试、不影响主流程
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.services.gateway.proxy import RouteTarget, forward_json, resolve_targets

logger = logging.getLogger(__name__)


@dataclass
class WarmupResult:
    provider_id: str
    label: str
    ok: bool
    status_code: Optional[int] = None
    message: Optional[str] = None


WARMUP_TEXT = "ping"
WARMUP_MAX_TOKENS = 1


async def warmup_account(
    user_id: str, provider_id: str, model: str, protocol: str = "anthropic"
) -> WarmupResult:
    """对某个供应商的第一个可用账号发一次最小请求"""
    try:
        targets = resolve_targets(user_id, f"{provider_id}/{model}", protocol=protocol)
    except Exception as exc:
        return WarmupResult(provider_id, provider_id, False, message=str(exc))

    if not targets:
        return WarmupResult(provider_id, provider_id, False, message="没有可用账号")

    target: RouteTarget = targets[0]
    body = {
        "model": model,
        "max_tokens": WARMUP_MAX_TOKENS,
        "messages": [{"role": "user", "content": WARMUP_TEXT}],
    }
    try:
        status, payload = await forward_json(target, protocol, body)
    except Exception as exc:
        logger.info("预热 %s 失败: %s", provider_id, exc)
        return WarmupResult(provider_id, target.account.label, False, message=str(exc))

    ok = 200 <= status < 300
    message = None if ok else str(payload)[:200]
    logger.info(
        "预热 %s（%s）→ HTTP %s %s",
        provider_id,
        target.account.label,
        status,
        "" if ok else message,
    )
    return WarmupResult(provider_id, target.account.label, ok, status_code=status, message=message)


async def run_warmup(user_id: str, targets: list[dict]) -> list[WarmupResult]:
    """批量预热（串行，避免同时开启多个窗口造成瞬间压力）"""
    results: list[WarmupResult] = []
    for item in targets:
        provider_id = str(item.get("providerId") or "")
        model = str(item.get("model") or "")
        protocol = str(item.get("protocol") or "anthropic")
        if not provider_id or not model:
            continue
        results.append(await warmup_account(user_id, provider_id, model, protocol))
        await asyncio.sleep(1.0)
    return results


def next_run_at(hour: int, minute: int) -> str:
    """下次执行时间（本地时区，仅供展示）"""
    now = datetime.now()
    candidate = now.replace(hour=max(0, min(23, hour)), minute=max(0, min(59, minute)), second=0, microsecond=0)
    if candidate <= now:
        from datetime import timedelta

        candidate += timedelta(days=1)
    return candidate.isoformat(timespec="seconds")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
