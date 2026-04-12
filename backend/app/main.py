from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import (
    tools,
    image_downloader,
    video_downloader,
    ytdlp_routes,
    calendar,
    key_generator,
    converter,
    oss,
    admin,
)
from app.routes import ocr_routes, asr_routes, database_tool, redis_tool, ssh_tool, json_tool, resource_management
from app.routes import auth, contact_message
from app.routes import markdown_editor
from app.routes import cross_share
from app.routes import course_platform
from app.routes import http_client
from app.routes import course_platform_admin
from app.routes import tech_contents
from app.routes import cursor_history
from app.api.routes import llm_config, conversations, prd, messages, health
from app.services.download_manager import get_manager
import asyncio
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.config.config import settings

# 配置日志目录为项目根目录下的 logs 文件夹
PROJECT_ROOT = Path(__file__).parent.parent  # backend/app/main.py -> backend
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志格式
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(log_format)

# 配置文件处理器（按大小轮转，保留5个备份，每个最大10MB）
file_handler = RotatingFileHandler(
    LOGS_DIR / "app.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)

# 配置控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO, handlers=[file_handler, console_handler], format=log_format
)

# 配置 uvicorn 日志，确保启动错误也写入文件
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.addHandler(file_handler)
uvicorn_logger.setLevel(logging.INFO)

uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.addHandler(file_handler)
uvicorn_error_logger.setLevel(logging.INFO)

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addHandler(file_handler)
uvicorn_access_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# JWT Configuration (from settings)
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting application...")

    # 启动后台清理任务
    manager = get_manager()
    cleanup_task = asyncio.create_task(manager.start_cleanup_task())

    # 启动 OpenClaw 连接
    try:
        from app.services.openclaw_service import openclaw_service
        await openclaw_service.start()
    except Exception as e:
        logger.warning(f"OpenClaw 连接启动失败（功能将不可用）: {e}")

    yield

    # 关闭时
    logger.info("Shutting down application...")

    try:
        from app.services.openclaw_service import openclaw_service
        await openclaw_service.stop()
    except Exception as e:
        logger.error(f"OpenClaw 关闭异常: {e}")

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Tool Aggregation API", lifespan=lifespan)

# Configure CORS - Updated to support Authorization header
cors_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["*"],
)

# Include routers
app.include_router(tools.router, prefix="/api")
app.include_router(image_downloader.router, prefix="/api")
app.include_router(video_downloader.router, prefix="/api")
app.include_router(ytdlp_routes.router, prefix="/api")
app.include_router(calendar.router)
app.include_router(key_generator.router)

# Authentication router
app.include_router(auth.router)

# Markdown Editor router
app.include_router(markdown_editor.router)

# Document Converter router
app.include_router(converter.router)

# OSS router
app.include_router(oss.router)

# Admin router
app.include_router(admin.router)

# OCR & ASR routers
app.include_router(ocr_routes.router, prefix="/api")
app.include_router(asr_routes.router, prefix="/api")

# Database Tool router
app.include_router(database_tool.router, prefix="/api")

# Redis Tool router
app.include_router(redis_tool.router, prefix="/api")

# SSH Tool router
app.include_router(ssh_tool.router, prefix="/api")

# JSON Tool router
app.include_router(json_tool.router, prefix="/api")

# Resource Management router
app.include_router(resource_management.router, prefix="/api")

# CrossShare router
app.include_router(cross_share.router)

# Course Platform router
app.include_router(course_platform.router)

# Course Platform Admin router
app.include_router(course_platform_admin.router)

# Tech Contents router
app.include_router(tech_contents.router)

# Product Manager Agent routers
app.include_router(llm_config.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(prd.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")

# Health check router
app.include_router(health.router, prefix="/api/v1")
app.include_router(llm_config.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(prd.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(llm_config.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(prd.router, prefix="/api/v1")

# Chat stream router (SSE)
from app.api.routes import chat_stream, admin_conversations

app.include_router(chat_stream.router, prefix="/api/v1")

# Admin conversation management router
app.include_router(admin_conversations.router, prefix="/api/v1")

# Agent management router
from app.api.routes import agents as agents_router

app.include_router(agents_router.router, prefix="/api/v1")

# Contact Message router
app.include_router(contact_message.router)

# Cursor History router
app.include_router(cursor_history.router, prefix="/api")

# OpenClaw router
from app.routes import openclaw as openclaw_router

# HTTP Client router
app.include_router(http_client.router, prefix="/api")

# OpenClaw router (SSE streaming)
app.include_router(openclaw_router.router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Tool Aggregation API"}
