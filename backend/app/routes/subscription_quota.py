"""订阅套餐额度 API

只读本机 CLI 登录凭据，查询官方订阅额度。响应中**绝不包含任何 token**。
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.routes.auth import get_current_user_id
from app.services.subscription_quota import (
    KNOWN_TOOLS,
    query_quotas,
)
from app.services.subscription_quota.service import (
    TOOL_DISPLAY_NAMES,
    clear_cache,
    describe_credentials,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription-quota", tags=["subscription-quota"])


class QueryRequest(BaseModel):
    tools: Optional[List[str]] = Field(
        default=None, description="要查询的供应商 id；为空时查询全部"
    )
    force_refresh: bool = Field(default=False, description="是否跳过 60 秒缓存")


def _require_user(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        return get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")


@router.get("/providers")
def list_providers(authorization: Optional[str] = Header(None)):
    """列出支持的供应商与本地凭据状态（不含 token）"""
    _require_user(authorization)
    return {
        "tools": list(KNOWN_TOOLS),
        "displayNames": TOOL_DISPLAY_NAMES,
        "providers": describe_credentials(),
    }


@router.post("/query")
async def query(
    req: Optional[QueryRequest] = None,
    authorization: Optional[str] = Header(None),
):
    """查询订阅额度（并发，单家失败不影响其它家）"""
    req = req or QueryRequest()
    user_id = _require_user(authorization)
    logger.info(
        "订阅额度查询: user=%s tools=%s force_refresh=%s",
        user_id,
        req.tools or "all",
        req.force_refresh,
    )
    if req.force_refresh:
        clear_cache()
    quotas = await query_quotas(req.tools, force_refresh=req.force_refresh)
    logger.info(
        "订阅额度查询完成: user=%s 返回 %d 家（成功 %d 家）",
        user_id,
        len(quotas),
        sum(1 for q in quotas if q.success),
    )
    return {
        "quotas": [q.to_dict() for q in quotas],
        "queriedAt": int(__import__("time").time() * 1000),
    }
