"""
防抖中间件
防止短时间内重复调用相同的 API
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Set
import time
from collections import defaultdict
import hashlib


class DebounceMiddleware(BaseHTTPMiddleware):
    """
    防抖中间件

    在指定时间窗口内，阻止相同的请求重复提交
    """

    def __init__(
        self,
        app,
        window_seconds: int = 30,  # 时间窗口（秒）
        max_requests: int = 1,  # 时间窗口内允许的最大请求数
    ):
        super().__init__(app)
        self.window_seconds = window_seconds
        self.max_requests = max_requests

        # 存储请求时间戳：{request_hash: [timestamp1, timestamp2, ...]}
        self._request_timestamps: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 只对 POST 请求进行防抖
        if request.method != "POST":
            return await call_next(request)

        # 生成请求的唯一标识
        request_hash = await self._hash_request(request)
        current_time = time.time()

        # 清理过期的时间戳
        self._cleanup_expired_timestamps(current_time)

        # 检查是否在时间窗口内重复
        timestamps = self._request_timestamps.get(request_hash, [])
        recent_requests = [
            ts for ts in timestamps if current_time - ts < self.window_seconds
        ]

        if len(recent_requests) >= self.max_requests:
            # 在时间窗口内重复请求
            wait_time = self.window_seconds - (current_time - recent_requests[0])
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "请求过于频繁",
                    "message": f"请在 {int(wait_time)} 秒后重试",
                    "wait_seconds": int(wait_time),
                },
            )

        # 记录请求时间戳
        self._request_timestamps[request_hash].append(current_time)

        # 继续处理请求
        return await call_next(request)

    async def _hash_request(self, request: Request) -> str:
        """
        生成请求的唯一哈希值

        考虑因素：
        - 请求路径
        - 用户 ID（从认证头）
        - 请求体内容
        """
        # 获取请求体
        body = await request.body()

        # 获取用户 ID（如果有）
        user_id = request.headers.get("Authorization", "anonymous")

        # 组合关键信息
        key_parts = [request.url.path, user_id, body.decode("utf-8", errors="ignore")]

        # 生成哈希
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _cleanup_expired_timestamps(self, current_time: float):
        """清理过期的时间戳"""
        expired_keys = []

        for key, timestamps in self._request_timestamps.items():
            # 只保留时间窗口内的时间戳
            self._request_timestamps[key] = [
                ts
                for ts in timestamps
                if current_time - ts < self.window_seconds * 2  # 保留 2 倍窗口用于清理
            ]

            if not self._request_timestamps[key]:
                expired_keys.append(key)

        # 删除空键
        for key in expired_keys:
            del self._request_timestamps[key]


def setup_debounce_middleware(app, window_seconds: int = 30, max_requests: int = 1):
    """设置防抖中间件"""
    app.add_middleware(
        DebounceMiddleware, window_seconds=window_seconds, max_requests=max_requests
    )
