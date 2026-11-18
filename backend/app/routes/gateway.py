"""本地网关（对齐 magpie 的 127.0.0.1:3425）

对外提供三个入口：

* ``POST /api/gateway/v1/chat/completions`` — OpenAI Chat 兼容
* ``POST /api/gateway/v1/messages`` — Anthropic Messages 兼容
* ``GET  /api/gateway/v1/models`` — 可用模型目录（``provider/model``）

同时提供设置接口（开关、端口、掩码、路由组、意图路由、预热、插件）。

**边界**：网关不改写任何 CLI 配置；是否把 agent 指过来由用户自己决定。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.routes.auth import get_current_user_id
from app.services.gateway.config_store import (
    GatewayConfig,
    load_config,
    save_config,
)
from app.services.gateway.intent import classify, group_target
from app.services.gateway.masking import MaskingSession
from app.services.gateway.plugins import PluginContext, apply_plugins, discover_plugins
from app.services.gateway.proxy import (
    GatewayError,
    forward_json,
    forward_stream,
    prepare_masked_body,
    resolve_targets,
    sse_event,
    sse_unmask_bytes,
)
from app.services.gateway.warmup import next_run_at, run_warmup
from app.services.subscription_quota.accounts import list_accounts
from app.services.subscription_quota.registry import get_spec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateway", tags=["gateway"])


class ConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    port: Optional[int] = Field(default=None, ge=1024, le=65535)
    host: Optional[str] = None
    masking: Optional[dict] = None
    groups: Optional[dict] = None
    intentRouting: Optional[bool] = None
    failover: Optional[dict] = None


class WarmupRequest(BaseModel):
    targets: list[dict] = Field(default_factory=list, description="[{providerId, model, protocol}]")


def _require_user(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        return get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")


def _masking_session(config: GatewayConfig) -> MaskingSession:
    cfg = config.masking
    return MaskingSession(
        enabled=bool(cfg.get("enabled")),
        extra_words=tuple(cfg.get("extraWords") or ()),
        mask_cards=bool(cfg.get("maskCards")),
        mask_ids=bool(cfg.get("maskIds")),
    )


def _resolve_by_group(user_id: str, group_name: str) -> Optional[str]:
    """把 ``group/xxx`` 解析成第一个有账号的成员模型名"""
    config = load_config()
    members = config.groups.get(group_name) or []
    for member in members:
        if not isinstance(member, str) or "/" not in member:
            continue
        provider_id = member.split("/", 1)[0]
        if any(a.provider_id == provider_id for a in list_accounts(user_id, only_enabled=True)):
            return member
    return None


def _apply_routing(user_id: str, body: dict) -> tuple[dict, Optional[str]]:
    """意图路由 + 路由组解析；返回 (body, 生效的说明)"""
    config = load_config()
    model = body.get("model")
    if not isinstance(model, str):
        return body, None

    patched = dict(body)

    # 1) 意图路由：只在开启且模型本身不是显式 provider/model 时生效
    if config.intent_routing and "/" not in model:
        result = classify(body.get("messages") or [])
        if result is not None:
            target = result.target
            group = group_target(target)
            resolved = _resolve_by_group(user_id, group) if group else target
            if resolved:
                patched["model"] = resolved
                return patched, f"intent:{result.rule}→{resolved}"

    # 2) 路由组
    group = group_target(model)
    if group:
        resolved = _resolve_by_group(user_id, group)
        if not resolved:
            raise GatewayError(f"路由组 {group!r} 没有可用成员", status_code=400)
        patched["model"] = resolved
        return patched, f"group:{group}→{resolved}"

    return patched, None


async def _dispatch(
    user_id: str,
    protocol: str,
    body: dict,
) -> tuple[int, dict, dict]:
    """非流式：带 failover 的转发；返回 (status, payload, meta)"""
    config = load_config()
    session = _masking_session(config)
    masked_body, masked_hits = prepare_masked_body(body, session)

    # 插件（在掩码之后、路由之前；插件看不到明文）
    masked_body, plugins_applied = apply_plugins(
        masked_body,
        PluginContext(
            protocol=protocol,
            provider_id=None,
            model=masked_body.get("model"),
        ),
    )

    routed_body, route_note = _apply_routing(user_id, masked_body)
    model = routed_body.get("model")
    if not isinstance(model, str) or not model:
        raise GatewayError("请求缺少 model 字段", status_code=400)

    targets = resolve_targets(user_id, model, protocol=protocol)
    max_retries = int(config.failover.get("maxRetries") or 0) + 1
    if not config.failover.get("enabled", True):
        max_retries = 1

    last_error: Optional[str] = None
    for index, target in enumerate(targets[:max_retries]):
        try:
            status, payload = await forward_json(target, protocol, routed_body)
        except GatewayError as exc:
            last_error = str(exc)
            logger.info("账号 %s 转发失败（%s），尝试下一个", target.account.label, exc)
            continue

        if 400 <= status < 500 and status not in (429,):
            # 确定性错误（参数错 / 鉴权错）：不重试其它账号
            restored = session.unmask_obj(payload)
            return status, restored, {
                "providerId": target.provider_id,
                "accountId": target.account.id,
                "routedBy": route_note,
                "maskedValues": masked_hits,
                "plugins": plugins_applied,
                "attempts": index + 1,
            }

        if status >= 500 or status == 429:
            last_error = f"HTTP {status}"
            logger.info("账号 %s 返回 %s，切换下一个", target.account.label, status)
            continue

        restored = session.unmask_obj(payload)
        return status, restored, {
            "providerId": target.provider_id,
            "accountId": target.account.id,
            "routedBy": route_note,
            "maskedValues": masked_hits,
            "plugins": plugins_applied,
            "attempts": index + 1,
        }

    raise GatewayError(
        f"所有账号都失败（{len(targets)} 个候选）：{last_error or '未知错误'}",
        status_code=502,
    )


async def _dispatch_stream(
    user_id: str,
    protocol: str,
    body: dict,
):
    """流式：带 failover 的转发，逐块还原掩码"""
    config = load_config()
    session = _masking_session(config)
    masked_body, masked_hits = prepare_masked_body(body, session)
    masked_body, plugins_applied = apply_plugins(
        masked_body,
        PluginContext(protocol=protocol, provider_id=None, model=masked_body.get("model")),
    )
    routed_body, route_note = _apply_routing(user_id, masked_body)

    model = routed_body.get("model")
    if not isinstance(model, str) or not model:
        raise GatewayError("请求缺少 model 字段", status_code=400)

    targets = resolve_targets(user_id, model, protocol=protocol)
    max_retries = int(config.failover.get("maxRetries") or 0) + 1
    if not config.failover.get("enabled", True):
        max_retries = 1

    headers = {
        "X-Gateway-Routed-By": route_note or "direct",
        "X-Gateway-Masked-Values": str(masked_hits),
        "X-Gateway-Plugins": ",".join(plugins_applied) or "-",
    }

    async def generate():
        last_error: Optional[str] = None
        for index, target in enumerate(targets[:max_retries]):
            try:
                async for chunk in forward_stream(target, protocol, routed_body):
                    yield sse_unmask_bytes(chunk, session)
                return
            except GatewayError as exc:
                last_error = str(exc)
                logger.info(
                    "流式：账号 %s 失败（%s），尝试下一个", target.account.label, exc
                )
                continue
        # 全部失败：以 SSE 形式把错误发给调用方
        yield sse_event(
            {
                "error": {
                    "message": f"所有账号都失败：{last_error or '未知错误'}",
                    "type": "gateway_error",
                }
            }
        )

    return StreamingResponse(generate(), media_type="text/event-stream", headers=headers)


# ---------------------------------------------------------------- 协议端点


@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """OpenAI Chat 兼容入口"""
    user_id = _require_user(authorization)
    try:
        body: Any = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="请求体不是合法 JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")

    try:
        if body.get("stream"):
            return await _dispatch_stream(user_id, "openai", body)
        status, payload, meta = await _dispatch(user_id, "openai", body)
        return JSONResponse(payload, status_code=status, headers={
            "X-Gateway-Provider": meta["providerId"],
            "X-Gateway-Routed-By": meta["routedBy"] or "direct",
            "X-Gateway-Masked-Values": str(meta["maskedValues"]),
            "X-Gateway-Plugins": ",".join(meta["plugins"]) or "-",
            "X-Gateway-Attempts": str(meta["attempts"]),
        })
    except GatewayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/v1/messages")
async def anthropic_messages(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
):
    """Anthropic Messages 兼容入口"""
    user_id = _require_user(authorization or (f"Bearer {x_api_key}" if x_api_key else None))
    try:
        body: Any = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="请求体不是合法 JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")

    try:
        if body.get("stream"):
            return await _dispatch_stream(user_id, "anthropic", body)
        status, payload, meta = await _dispatch(user_id, "anthropic", body)
        return JSONResponse(payload, status_code=status, headers={
            "X-Gateway-Provider": meta["providerId"],
            "X-Gateway-Routed-By": meta["routedBy"] or "direct",
            "X-Gateway-Masked-Values": str(meta["maskedValues"]),
            "X-Gateway-Plugins": ",".join(meta["plugins"]) or "-",
            "X-Gateway-Attempts": str(meta["attempts"]),
        })
    except GatewayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/v1/models")
def list_models(authorization: Optional[str] = Header(None)):
    """可用模型目录：已配置账号的供应商 + 路由组"""
    user_id = _require_user(authorization)
    config = load_config()

    data: list[dict] = []
    seen: set[str] = set()
    for account in list_accounts(user_id, only_enabled=True):
        spec = get_spec(account.provider_id)
        name = spec.name if spec else account.provider_id
        entry_id = f"{account.provider_id}/*"
        if entry_id in seen:
            continue
        seen.add(entry_id)
        data.append(
            {
                "id": entry_id,
                "object": "model",
                "owned_by": name,
                "provider_id": account.provider_id,
                "label": account.label,
            }
        )

    for group_name in config.groups:
        data.append(
            {
                "id": f"group/{group_name}",
                "object": "model",
                "owned_by": "gateway",
                "members": config.groups.get(group_name) or [],
            }
        )

    return {"object": "list", "data": data}


# ---------------------------------------------------------------- 设置


@router.get("/config")
def get_config(authorization: Optional[str] = Header(None)):
    """读取网关设置（不含任何密钥）"""
    _require_user(authorization)
    config = load_config()
    plugins = [p.to_public_dict() for p in discover_plugins()]
    return {
        "config": config.to_dict(),
        "plugins": plugins,
        "endpoints": {
            "openai": "/api/gateway/v1/chat/completions",
            "anthropic": "/api/gateway/v1/messages",
            "models": "/api/gateway/v1/models",
        },
        "hint": (
            "把 CLI 的 base_url 指到 "
            f"http://{config.host}:{config.port}/api/gateway；"
            "本工具不会自动改写任何配置文件"
        ),
    }


@router.put("/config")
def update_config(
    req: ConfigUpdateRequest,
    authorization: Optional[str] = Header(None),
):
    """更新网关设置"""
    _require_user(authorization)
    config = load_config()
    updates = {k: v for k, v in req.model_dump(exclude_none=True).items()}
    if not updates:
        return {"config": config.to_dict()}

    merged = dict(config.data)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    updated = save_config(GatewayConfig(data=merged))
    logger.info("网关设置已更新: %s", list(updates.keys()))
    return {"config": updated.to_dict()}


@router.post("/warmup/run")
async def run_warmup_now(
    req: WarmupRequest,
    authorization: Optional[str] = Header(None),
):
    """立即执行一次预热（需要显式传 targets，避免误消耗额度）"""
    user_id = _require_user(authorization)
    if not req.targets:
        raise HTTPException(status_code=400, detail="需要提供至少一个 targets 项")

    results = await run_warmup(user_id, req.targets)
    return {
        "results": [
            {
                "providerId": r.provider_id,
                "label": r.label,
                "ok": r.ok,
                "statusCode": r.status_code,
                "message": r.message,
            }
            for r in results
        ]
    }


@router.get("/warmup/schedule")
def warmup_schedule(
    hour: int = 9,
    minute: int = 0,
    authorization: Optional[str] = Header(None),
):
    """预热计划（仅展示下次执行时间；实际执行由用户手动触发或外部定时器调用）"""
    _require_user(authorization)
    return {"nextRunAt": next_run_at(hour, minute), "hour": hour, "minute": minute}
