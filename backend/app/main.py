from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import tools, image_downloader, video_downloader, ytdlp_routes, calendar, key_generator, converter, oss, admin
from app.routes import ocr_routes, asr_routes, database_tool, redis_tool, ssh_tool
from app.routes import auth
from app.routes import markdown_editor
from app.services.download_manager import get_manager
import asyncio
import logging
import os

from app.config.config import settings

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
    
    yield
    
    # 关闭时
    logger.info("Shutting down application...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="MasterGO Tool Aggregation API",
    lifespan=lifespan
)

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

@app.get("/")
def read_root():
    return {"message": "MasterGO Tool Aggregation API"}
