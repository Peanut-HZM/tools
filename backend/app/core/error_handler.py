"""
错误处理器
统一错误响应格式
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class ErrorHandler:
    """全局错误处理器"""

    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 HTTP 异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )

    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "服务器内部错误",
                "message": str(exc) if False else "请稍后重试",
                "path": request.url.path,
            },
        )
