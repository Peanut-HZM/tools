"""个人 API Token 路由

JWT 认证（现有用户体系）下创建/列出/撤销 PAT。
PAT 供 MCP endpoint（/mcp/k8s）认证使用，与 JWT 体系相互独立。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.middleware.auth_middleware import get_current_user_id
from app.models.user_api_token_models import (
    CreateUserTokenRequest,
    UserTokenCreatedResponse,
    UserTokenResponse,
)
from app.services.user_token_service import UserTokenService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-tokens", tags=["user-api-tokens"])


@router.post("", response_model=UserTokenCreatedResponse)
async def create_token(
    request: CreateUserTokenRequest,
    user_id: str = Depends(get_current_user_id),
):
    """创建 API Token（明文仅此一次返回）"""
    resp, _plain = UserTokenService.generate_token(
        user_id, request.name, request.expires_days
    )
    return resp


@router.get("", response_model=List[UserTokenResponse])
async def list_tokens(user_id: str = Depends(get_current_user_id)):
    """列出当前用户的 API Token（脱敏）"""
    return UserTokenService.list_tokens(user_id)


@router.delete("/{token_id}")
async def revoke_token(token_id: str, user_id: str = Depends(get_current_user_id)):
    """撤销 Token"""
    if not UserTokenService.revoke_token(user_id, token_id):
        raise HTTPException(status_code=404, detail="Token 不存在或已撤销")
    return {"message": "已撤销"}
