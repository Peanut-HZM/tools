"""MCP endpoint 的 PAT 认证

纯 ASGI 中间件：校验 Authorization: Bearer pat_...，通过后把 user_id
写入 ContextVar 供工具函数读取；失败一律 401，绝不放行。
"""
import logging
from contextvars import ContextVar
from typing import Optional

from starlette.responses import JSONResponse

from app.services.user_token_service import UserTokenService

logger = logging.getLogger(__name__)

current_mcp_user_id: ContextVar[Optional[str]] = ContextVar("mcp_user_id", default=None)


def set_current_mcp_user_id(user_id: str):
    """设置当前 MCP 用户身份（中间件用；测试可直接调用）"""
    return current_mcp_user_id.set(user_id)


def reset_current_mcp_user_id(token) -> None:
    current_mcp_user_id.reset(token)


def get_current_mcp_user_id() -> str:
    """工具函数获取当前用户；缺失即拒绝（对应 ContextVar 未设置）"""
    uid = current_mcp_user_id.get()
    if not uid:
        raise PermissionError("MCP 用户身份缺失，拒绝执行")
    return uid


class PATAuthASGIMiddleware:
    """包在 streamable Starlette app 外层的 PAT 校验中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers", [])}
        auth_header = headers.get("authorization", "")
        token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
        user_id = UserTokenService.validate_token(token) if token else None
        if not user_id:
            logger.warning("MCP 认证失败：无效或缺失 API Token")
            resp = JSONResponse({"detail": "无效或缺失 API Token（请在 tools 个人中心创建 PAT）"},
                                status_code=401)
            await resp(scope, receive, send)
            return
        ctx = set_current_mcp_user_id(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_mcp_user_id(ctx)
