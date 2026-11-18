"""订阅套餐额度 API（v2：支持用户自助添加任意供应商）

只返回**已配置**的账号与本机已登录的订阅。
响应中**绝不包含**明文 API Key（只返回掩码）。
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.routes.auth import get_current_user_id
from app.services.subscription_quota.accounts import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from app.services.subscription_quota.registry import (
    MANUAL_PROVIDER_IDS,
    PROVIDER_SPECS,
    SUBSCRIPTION_IDS,
    get_spec,
)
from app.services.subscription_quota.service import (
    TOOL_DISPLAY_NAMES,
    clear_cache,
    describe_credentials,
    query_for_accounts,
    query_subscriptions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription-quota", tags=["subscription-quota"])


# ---------------------------------------------------------------- 请求模型


class AccountCreateRequest(BaseModel):
    provider_id: str = Field(..., description="供应商 id，见 /providers")
    label: str = Field(default="", description="自定义显示名，例如「工作号」")
    api_key: Optional[str] = Field(default=None, description="API Key（服务端加密存储）")
    extra: dict = Field(default_factory=dict, description="额外字段：region / base_url / control_key 等")


class AccountUpdateRequest(BaseModel):
    label: Optional[str] = None
    api_key: Optional[str] = None
    extra: Optional[dict] = None
    enabled: Optional[bool] = None


class QueryRequest(BaseModel):
    account_ids: Optional[List[str]] = Field(
        default=None, description="只查这些账号；为空查全部已启用账号"
    )
    include_subscriptions: bool = Field(default=True, description="是否同时查询本机订阅")
    force_refresh: bool = Field(default=False)


class TestRequest(BaseModel):
    """测试连接时可直接传临时凭据，不必先保存"""

    api_key: Optional[str] = None
    extra: dict = Field(default_factory=dict)


def _require_user(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        return get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")


# ---------------------------------------------------------------- 供应商目录


@router.get("/providers")
def list_providers(authorization: Optional[str] = Header(None)):
    """供应商目录：每个供应商需要哪些字段、是否已配置。"""
    user_id = _require_user(authorization)
    accounts = list_accounts(user_id)
    configured: dict[str, int] = {}
    for account in accounts:
        configured[account.provider_id] = configured.get(account.provider_id, 0) + 1

    return {
        "providers": [
            {
                **spec.to_public_dict(),
                "configuredCount": configured.get(spec.id, 0),
                "addable": spec.id in MANUAL_PROVIDER_IDS,
            }
            for spec in PROVIDER_SPECS
        ],
        "displayNames": TOOL_DISPLAY_NAMES,
        "subscriptionIds": list(SUBSCRIPTION_IDS),
        "manualProviderIds": list(MANUAL_PROVIDER_IDS),
    }


@router.get("/subscriptions")
def list_subscriptions(authorization: Optional[str] = Header(None)):
    """本机订阅类凭据状态（Claude / Codex / Gemini）+ 可自动识别的本地凭据"""
    _require_user(authorization)
    from app.services.subscription_quota.local_credentials import local_credential_notes

    return {
        "subscriptions": describe_credentials(),
        "localCredentials": [
            {
                "providerId": note.provider_id,
                "name": note.name,
                "status": note.status,
                "message": note.message,
            }
            for note in local_credential_notes()
        ],
    }


# ---------------------------------------------------------------- 账号 CRUD


@router.get("/accounts")
def get_accounts(authorization: Optional[str] = Header(None)):
    """我的供应商账号（只返回掩码 Key）"""
    user_id = _require_user(authorization)
    return {"accounts": [account.to_public_dict() for account in list_accounts(user_id)]}


@router.post("/accounts")
def add_account(
    req: AccountCreateRequest,
    authorization: Optional[str] = Header(None),
):
    """添加一个供应商账号（一个 API Key 即可）"""
    user_id = _require_user(authorization)
    spec = get_spec(req.provider_id)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"未知供应商: {req.provider_id}")
    if spec.kind == "subscription":
        raise HTTPException(
            status_code=400,
            detail=f"{spec.name} 使用本机 CLI 登录凭据，无需手动添加",
        )

    extra = dict(req.extra or {})
    # api_key 也可以放在 extra 里（部分供应商用 control_key 等命名）
    if req.api_key:
        extra.setdefault("api_key", req.api_key)

    account = create_account(
        user_id,
        req.provider_id,
        label=req.label or spec.name,
        api_key=req.api_key,
        extra=extra,
    )
    clear_cache()
    logger.info("用户 %s 添加订阅额度账号 provider=%s", user_id, req.provider_id)
    return {"account": account.to_public_dict()}


@router.put("/accounts/{account_id}")
def edit_account(
    account_id: str,
    req: AccountUpdateRequest,
    authorization: Optional[str] = Header(None),
):
    user_id = _require_user(authorization)
    existing = get_account(user_id, account_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    extra = req.extra
    if req.api_key:
        extra = dict(extra if extra is not None else existing.extra)
        extra["api_key"] = req.api_key

    updated = update_account(
        user_id,
        account_id,
        label=req.label,
        api_key=req.api_key,
        extra=extra,
        enabled=req.enabled,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    clear_cache()
    return {"account": updated.to_public_dict()}


@router.delete("/accounts/{account_id}")
def remove_account(account_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user(authorization)
    if not delete_account(user_id, account_id):
        raise HTTPException(status_code=404, detail="账号不存在")
    clear_cache()
    return {"success": True}


@router.post("/accounts/{account_id}/test")
def test_account(
    account_id: str,
    req: TestRequest = TestRequest(),
    authorization: Optional[str] = Header(None),
):
    """测试单个账号是否可查询（可传临时凭据，不落库）"""
    import asyncio

    user_id = _require_user(authorization)
    account = get_account(user_id, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    if req.api_key:
        account.api_key = req.api_key
    if req.extra:
        merged = dict(account.extra)
        merged.update(req.extra)
        account.extra = merged

    from app.services.subscription_quota.service import _decorate, _query_account

    # FastAPI 的同步端点里用独立事件循环执行异步查询
    quota = asyncio.run(_query_account(account))
    return {"quota": _decorate(quota, account)}


# ---------------------------------------------------------------- 额度查询


@router.post("/query")
async def query_quotas_endpoint(
    req: Optional[QueryRequest] = None,
    authorization: Optional[str] = Header(None),
):
    """查询已配置账号的额度（只返回已配置项）"""
    req = req or QueryRequest()
    user_id = _require_user(authorization)

    if req.force_refresh:
        clear_cache()

    accounts_quota = await query_for_accounts(
        user_id, req.account_ids, force_refresh=req.force_refresh
    )

    subscriptions: list[dict] = []
    if req.include_subscriptions:
        subscriptions = await query_subscriptions(force_refresh=req.force_refresh)

    # 「已配置」只统计用户自己添加的账号或本机已登录的订阅（不含虚拟本地账号）
    user_account_count = len([q for q in accounts_quota if not q.get("isLocal")])
    has_subscription = any(s.get("success") or s.get("credentialStatus") != "not_found"
                           for s in subscriptions)
    configured = user_account_count > 0 or has_subscription

    ok = sum(1 for q in accounts_quota if q.get("success")) + sum(
        1 for q in subscriptions if q.get("success")
    )
    logger.info(
        "订阅额度查询: user=%s 账号 %d 个（含本地 %d）/ 订阅 %d 个（成功 %d）",
        user_id,
        len(accounts_quota),
        len(accounts_quota) - user_account_count,
        len(subscriptions),
        ok,
    )

    return {
        "accounts": accounts_quota,
        "subscriptions": subscriptions,
        "queriedAt": int(time.time() * 1000),
        "configured": configured,
    }
