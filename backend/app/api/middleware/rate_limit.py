"""
限流中间件
基于 Redis 实现请求限流
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.rate_limiter import RateLimiter
from app.config.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件

    使用滑动窗口算法对 API 请求进行限流
    支持按用户级别设置不同的限流规则
    """

    # 默认限流配置
    DEFAULT_RATE_LIMITS = {
        "normal": 50,  # 普通用户: 50次/小时
        "premium": 200,  # 高级用户: 200次/小时
    }

    # 需要限流的路径（不包括管理端）
    LIMITED_PATHS = [
        "/api/v1/conversations",
        "/api/v1/messages",
        "/api/v1/prd",
        "/api/v1/competitors",
    ]

    # 不需要限流的路径
    EXCLUDED_PATHS = [
        "/api/v1/admin",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    ]

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter,
        rate_limits: Optional[dict] = None,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.rate_limits = rate_limits or self.DEFAULT_RATE_LIMITS

    def _should_limit(self, path: str) -> bool:
        """判断路径是否需要限流"""
        # 排除不需要限流的路径
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return False

        # 检查是否在限流路径中
        for limited in self.LIMITED_PATHS:
            if path.startswith(limited):
                return True

        return False

    def _get_user_limit(self, user_level: str = "normal") -> int:
        """获取用户级别的限流阈值"""
        return self.rate_limits.get(user_level, self.rate_limits["normal"])

    def _get_user_id_from_request(self, request: Request) -> Optional[str]:
        """从请求中获取用户ID"""
        # 尝试从请求状态获取用户ID
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # 尝试从 Authorization header 获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # 这里可以解析 token 获取用户 ID
            # 暂时返回 None，由下游处理
            return None

        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 检查是否需要限流
        if not self._should_limit(request.url.path):
            return await call_next(request)

        # 获取用户ID
        user_id = self._get_user_id_from_request(request)

        # 如果无法获取用户ID，跳过限流（或者返回 401）
        if not user_id:
            # 尝试从请求中获取 guest ID
            guest_id = request.client.host if request.client else "guest"
            user_id = f"guest:{guest_id}"

        # 确定用户级别（这里应该从数据库或缓存获取）
        # 暂时默认为普通用户
        user_level = "normal"

        # 获取限流阈值
        limit = self._get_user_limit(user_level)

        # 检查限流
        allowed, current_count, remaining_seconds = self.rate_limiter.check_limit(
            user_id, limit
        )

        if not allowed:
            # 返回限流错误
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "您已达到本小时的调用上限，请稍后重试",
                    "limit": limit,
                    "current_count": current_count,
                    "reset_in_seconds": remaining_seconds,
                },
                headers={
                    "Retry-After": str(remaining_seconds)
                    if remaining_seconds
                    else "3600",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(remaining_seconds)
                    if remaining_seconds
                    else "3600",
                },
            )

        # 增加计数
        new_count = self.rate_limiter.increment_counter(user_id)

        # 处理请求
        response = await call_next(request)

        # 在响应头中添加限流信息
        remaining = max(0, limit - new_count)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


def create_rate_limit_middleware(app: ASGIApp, redis_client) -> RateLimitMiddleware:
    """
    创建限流中间件

    Args:
        app: FastAPI 应用
        redis_client: Redis 客户端

    Returns:
        配置好的限流中间件
    """
    rate_limiter = RateLimiter(redis_client)

    # 从配置中读取限流规则
    rate_limits = {
        "normal": getattr(settings, "RATE_LIMIT_NORMAL", 50),
        "premium": getattr(settings, "RATE_LIMIT_PREMIUM", 200),
    }

    return RateLimitMiddleware(app, rate_limiter=rate_limiter, rate_limits=rate_limits)
