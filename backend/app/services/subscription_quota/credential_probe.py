"""从 cc-switch 导入前，先实际探测哪个候选凭据真的可用

## 为什么需要探测

cc-switch 里**同一个供应商往往有多条配置**（给 claude / codex / opencode 各配一份，
或新旧 Key 并存）。它们的 Key 不一定都有效：

* Kimi For Coding 在 `opencode` 那条里存的是 `options.apiKey`，可能是**旧的失效 Key**；
  真正能用的是 `claude` 那条 `env.ANTHROPIC_AUTH_TOKEN`。
* 智谱同一个人有多个账号（Team HZM / Peanut / LYD），只有一个开通了 coding plan。

盲目取「第一条」会把失效 Key 导进来，卡片就永远显示「认证失败 / 不存在 coding plan」。
这里对每个候选**真实发一次额度查询**，只保留成功的那条。

## 约束

* **只读**：只发 GET 额度查询请求，不改任何配置、不写库
* **超时可容忍**：单条探测失败（网络/超时）不算失败，继续试下一个候选
* **并发 + 上限**：同一供应商的候选并发探测，避免导入被拖慢
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.providers_full import (
    QUERY_FUNCS,
    ProviderTransientError,
)

logger = logging.getLogger(__name__)

#: 单个候选的探测超时（秒）—— 导入是交互式操作，不能等太久
PROBE_TIMEOUT = 12.0


def _make_probe_account(candidate: dict) -> QuotaAccount:
    """把 cc-switch 候选包装成查询用的临时账号（不入库）"""
    provider_id = str(candidate.get("provider_id") or "")
    extra: dict = {}
    if candidate.get("region"):
        extra["region"] = candidate["region"]
    if candidate.get("base_url"):
        extra["base_url"] = candidate["base_url"]
    # 查询实现优先读 extra["api_key"]，这里统一塞进去，保证与真实账号行为一致
    extra["api_key"] = candidate.get("api_key") or ""

    return QuotaAccount(
        id=f"probe:{provider_id}",
        user_id="probe",
        provider_id=provider_id,
        label=str(candidate.get("source_name") or ""),
        api_key=str(candidate.get("api_key") or ""),
        extra=extra,
        enabled=True,
    )


async def probe_candidate(candidate: dict) -> tuple[bool, str]:
    """真实查一次额度，返回（是否可用, 原因说明）"""
    provider_id = str(candidate.get("provider_id") or "")
    func = QUERY_FUNCS.get(provider_id)
    if func is None:
        # 没有查询实现的供应商无法探测，只能认为「未知」
        return False, f"无查询实现（{provider_id}）"

    account = _make_probe_account(candidate)
    if not account.api_key:
        return False, "该候选没有 Key"

    try:
        quota = await asyncio.wait_for(func(account), timeout=PROBE_TIMEOUT)
    except ProviderTransientError as exc:
        return False, f"网络错误: {exc}"
    except asyncio.TimeoutError:
        return False, f"探测超时（{PROBE_TIMEOUT}s）"
    except Exception as exc:  # 探测失败绝不能让整个导入崩掉
        logger.warning("探测 %s 候选失败: %s", provider_id, exc)
        return False, f"探测异常: {type(exc).__name__}"

    if getattr(quota, "success", False):
        return True, "可用"
    reason = getattr(quota, "error", None) or getattr(quota, "credential_message", None) or ""
    status = getattr(quota, "credential_status", None)
    status_value = getattr(status, "value", status)
    return False, f"不可用（{status_value}）{(': ' + str(reason)) if reason else ''}"


async def pick_working_candidate(candidates: list[dict]) -> Optional[dict]:
    """从同一供应商的多个候选中挑出**实际可用**的那条。

    策略：
    1. 并发探测全部候选
    2. 有可用的 → 优先返回「控制面 Key」那条（额度查询更准），否则返回第一个可用的
    3. 全部不可用 → 返回 ``None``（调用方据此跳过，避免把失效 Key 存进来）

    只有 1 个候选时也会探测一次 —— 这样失效 Key 不会被默默写入。
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        ok, reason = await probe_candidate(candidates[0])
        if ok:
            return candidates[0]
        logger.info(
            "cc-switch 候选不可用，跳过导入: %s / %s —— %s",
            candidates[0].get("provider_id"),
            candidates[0].get("source_name"),
            reason,
        )
        return None

    results = await asyncio.gather(*(probe_candidate(c) for c in candidates))

    usable: list[dict] = []
    for candidate, (ok, reason) in zip(candidates, results):
        logger.info(
            "cc-switch 候选探测: %s / %s(%s) -> %s",
            candidate.get("provider_id"),
            candidate.get("source_name"),
            candidate.get("source_app"),
            "可用" if ok else reason,
        )
        if ok:
            usable.append(candidate)

    if not usable:
        return None

    # 控制面 Key 优先（额度/账单查询更准确）
    for candidate in usable:
        if candidate.get("from_control_key"):
            return candidate
    return usable[0]
