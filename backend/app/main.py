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
    deploy,
)
from app.routes import (
    ocr_routes,
    asr_routes,
    database_tool,
    redis_tool,
    ssh_tool,
    json_tool,
    resource_management,
    token_usage,
)
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
from datetime import datetime, timedelta
import asyncio
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.config.config import settings
from app.utils.usage_fetcher import UsageFetcher
from app.routes.token_usage import normalize_entries, apply_aggregation, compute_summary, merge_items
from app.services.token_usage_cache import set_cached_data
from app.models.base import Base, SessionLocal, engine
from app.services.token_usage_sync_service import sync_token_usage

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

    # 自动创建数据库表（Token Usage 相关模型）
    try:
        from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Token Usage 数据库表创建成功")
    except Exception as e:
        logger.warning(f"Token Usage 数据库表创建失败: {e}")

    # 启动后台清理任务
    manager = get_manager()
    cleanup_task = asyncio.create_task(manager.start_cleanup_task())

    # 启动数据库工具连接池空闲清理任务（每 5 分钟清理 15 分钟未使用的引擎）
    try:
        from app.utils.db_connection_manager import DBConnectionManager

        async def db_pool_cleanup_loop():
            while True:
                await asyncio.sleep(300)
                try:
                    cleaned = DBConnectionManager.cleanup_idle_engines(idle_timeout=900)
                    if cleaned:
                        logger.info(f"数据库连接池空闲清理: 已清理 {cleaned} 个引擎")
                except Exception as e:
                    logger.warning(f"数据库连接池清理失败: {e}")

        db_pool_cleanup_task = asyncio.create_task(db_pool_cleanup_loop())
    except Exception as e:
        logger.warning(f"数据库连接池清理任务启动失败: {e}")
        db_pool_cleanup_task = None

    # 启动 OpenClaw 连接
    try:
        from app.services.openclaw_service import openclaw_service

        await openclaw_service.start()
    except Exception as e:
        logger.warning(f"OpenClaw 连接启动失败（功能将不可用）: {e}")

    # 启动 Token Usage 缓存刷新任务（包含 DB 同步 + Redis 缓存刷新）
    cache_refresh_task = asyncio.create_task(refresh_token_usage_cache_periodically())

    yield

    # 关闭时
    logger.info("Shutting down application...")

    try:
        from app.services.openclaw_service import openclaw_service

        await openclaw_service.stop()
    except Exception as e:
        logger.error(f"OpenClaw 关闭异常: {e}")

    cleanup_task.cancel()
    cache_refresh_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await cache_refresh_task
    except asyncio.CancelledError:
        pass
    if 'db_pool_cleanup_task' in locals() and db_pool_cleanup_task is not None:
        db_pool_cleanup_task.cancel()
        try:
            await db_pool_cleanup_task
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

# Deploy info router
app.include_router(deploy.router, prefix="/api")

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

# Token Usage router
app.include_router(token_usage.router, prefix="/api")

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

# OpenClaw WebSocket router (mini-program)
from app.routes import openclaw_ws as openclaw_ws_router
app.include_router(openclaw_ws_router.router, prefix="/api")

# OpenClaw Admin router
from app.routes import openclaw_admin as openclaw_admin_router

app.include_router(openclaw_admin_router.router)


async def refresh_token_usage_cache_periodically():
    """每小时刷新 Token Usage 缓存（含 DB 同步）"""
    REFRESH_INTERVAL = 3600

    queries = [
        {"source": "claude", "report_type": "daily", "days": 7},
        {"source": "claude", "report_type": "daily", "days": 30},
        {"source": "claude", "report_type": "daily", "days": 90},
        {"source": "claude", "report_type": "monthly", "days": 90},
        {"source": "claude", "report_type": "monthly", "days": 180},
        {"source": "claude", "report_type": "monthly", "days": 365},
        {"source": "opencode", "report_type": "daily", "days": 30},
    ]

    while True:
        try:
            logger.info("开始 Token Usage 数据同步...")
            # 1. 同步 CLI 数据到数据库（增量）
            try:
                sync_token_usage(user_id="system", days=90)
                logger.info("DB 同步完成")
            except Exception as e:
                logger.warning(f"DB 同步失败（将在下次重试）: {e}")

            # 2. 刷新 Redis 缓存
            logger.info("开始刷新 Token Usage 缓存...")
            for q in queries:
                await _refresh_single_cache(q["source"], q["report_type"], q["days"])
            # 刷新聚合缓存
            aggregate_queries = [
                {"report_type": "daily", "days": 7},
                {"report_type": "daily", "days": 14},
                {"report_type": "daily", "days": 30},
                {"report_type": "daily", "days": 90},
                {"report_type": "weekly", "days": 56},
                {"report_type": "monthly", "days": 180},
            ]
            for q in aggregate_queries:
                await _refresh_aggregate_cache(q["report_type"], q["days"])
            logger.info(f"Token Usage DB 同步 + 缓存刷新完成，下次刷新在 {REFRESH_INTERVAL} 秒后")
        except Exception as e:
            logger.error(f"Token Usage 缓存刷新失败: {e}")

        await asyncio.sleep(REFRESH_INTERVAL)


async def _refresh_single_cache(source: str, report_type: str, days: int):
    """刷新单个查询的缓存，使用线程池执行 CLI 调用"""
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(
        None, lambda: _fetch_raw_data(source, report_type, days)
    )

    if "error" in raw:
        logger.warning(f"缓存刷新失败 {source}/{report_type}/{days}天: {raw['error']}")
        return

    items = normalize_entries(raw, report_type)
    items = apply_aggregation(items, report_type)
    summary = compute_summary(items)

    cache_data = {
        "items": [item.model_dump() for item in items],
        "summary": summary.model_dump(),
        "cache_time": datetime.now().isoformat(),
    }

    set_cached_data(
        source=source,
        report_type=report_type,
        days=days,
        data=cache_data,
    )
    logger.info(f"缓存已刷新: {source}/{report_type}/{days}天")


def _fetch_raw_data(source: str, report_type: str, days: int) -> dict:
    """同步获取原始数据（在线程池中执行）"""
    if source == "claude":
        since_date = datetime.now() - timedelta(days=days)
        since = since_date.strftime("%Y%m%d")
        raw = UsageFetcher.fetch_claude(
            report_type="daily",
            since=since,
            breakdown=False,
        )
    else:
        raw = UsageFetcher.fetch_opencode(days=days)
    return raw


async def _refresh_aggregate_cache(report_type: str, days: int):
    """刷新聚合缓存：并发获取两个数据源，合并后写入 Redis"""
    loop = asyncio.get_event_loop()
    since_date = datetime.now() - timedelta(days=days)
    since = since_date.strftime("%Y%m%d")

    claude_raw, opencode_raw = await asyncio.gather(
        loop.run_in_executor(None, lambda: UsageFetcher.fetch_claude(
            report_type="daily", since=since, breakdown=False
        )),
        loop.run_in_executor(None, lambda: UsageFetcher.fetch_opencode(days=days)),
        return_exceptions=True,
    )

    if isinstance(claude_raw, Exception):
        logger.warning(f"聚合缓存: claude 异常: {claude_raw}")
        claude_raw = {"error": str(claude_raw)}
    if isinstance(opencode_raw, Exception):
        logger.warning(f"聚合缓存: opencode 异常: {opencode_raw}")
        opencode_raw = {"error": str(opencode_raw)}

    # 两个都失败则跳过
    if "error" in claude_raw and "error" in opencode_raw:
        logger.error(
            f"聚合缓存刷新失败 {report_type}/{days}天: "
            f"claude={claude_raw.get('error')}, opencode={opencode_raw.get('error')}"
        )
        return

    # 分别规范化 + 聚合 + 合并
    items_a = (
        normalize_entries(claude_raw, report_type) if "error" not in claude_raw else []
    )
    items_b = (
        normalize_entries(opencode_raw, report_type) if "error" not in opencode_raw else []
    )
    items_a = apply_aggregation(items_a, report_type)
    items_b = apply_aggregation(items_b, report_type)
    merged = merge_items(items_a, items_b)
    summary = compute_summary(merged)

    cache_data = {
        "items": [item.model_dump() for item in merged],
        "summary": summary.model_dump(),
        "cache_time": datetime.now().isoformat(),
    }

    set_cached_data(
        source="aggregate",
        report_type=report_type,
        days=days,
        data=cache_data,
    )
    logger.info(f"聚合缓存已刷新: {report_type}/{days}天")


@app.get("/")
def read_root():
    return {"message": "Tool Aggregation API"}
