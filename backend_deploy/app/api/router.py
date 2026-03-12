"""
API Router 配置
集中管理所有 API 路由
"""

from fastapi import APIRouter, FastAPI
from app.api.routes import (
    llm_config,
    conversations,
    prd,
    chat_stream,
    admin_conversations,
    agents,
    competitor,
)

# 创建 API v1 路由
api_router = APIRouter(prefix="/api/v1")

# 会话管理
api_router.include_router(conversations.router, tags=["会话管理"])

# PRD 管理
api_router.include_router(prd.router, tags=["PRD管理"])

# 竞品分析
api_router.include_router(competitor.router, tags=["竞品分析"])

# 大模型配置（管理员）
api_router.include_router(
    llm_config.router, prefix="/admin", tags=["大模型配置（管理员）"]
)

# 聊天流（Server-Sent Events）
api_router.include_router(chat_stream.router, tags=["聊天流"])

# 管理员会话管理
api_router.include_router(
    admin_conversations.router, prefix="/admin", tags=["管理员会话管理"]
)

# Agent 管理
api_router.include_router(agents.router, tags=["Agent管理"])


def register_routes(app: FastAPI) -> None:
    """
    注册所有 API 路由到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    # 注册 API v1 路由
    app.include_router(api_router)
