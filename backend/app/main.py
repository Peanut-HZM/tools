from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import tools, image_downloader, video_downloader, ytdlp_routes, calendar, key_generator, converter
from app.routes import auth
from app.routes import markdown_editor
from app.services.download_manager import get_manager
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# JWT Configuration (can be overridden by environment variables)
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours default

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:5179",
        "http://localhost:5180",
        "http://localhost:3000",
    ],
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

@app.get("/")
def read_root():
    return {"message": "MasterGO Tool Aggregation API"}
