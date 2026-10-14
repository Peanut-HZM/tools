"""个人 API Token 的 Pydantic 请求/响应 DTO

明文 token 只存在于 UserTokenCreatedResponse（创建响应，仅此一次），
其余任何响应/日志不得包含明文或哈希。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateUserTokenRequest(BaseModel):
    """创建 API Token 请求"""
    name: str = Field(..., min_length=1, max_length=100, description="令牌名称，如 claude-code-local")
    expires_days: Optional[int] = Field(None, ge=1, le=3650, description="有效天数（空=永不过期）")


class UserTokenResponse(BaseModel):
    """Token 列表项（脱敏：无明文无哈希）"""
    id: str
    name: str
    token_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked: bool = False


class UserTokenCreatedResponse(UserTokenResponse):
    """创建成功响应：明文仅此一次返回"""
    token: str = Field(..., description="明文 Token，请立即保存，之后不可再查看")
