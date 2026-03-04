"""
健康检查路由
用于监控服务状态
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import logging

from app.api.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    基础健康检查

    返回服务是否运行
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    就绪检查

    检查服务是否准备好接收请求（数据库连接等）
    """
    checks = {
        "database": "unknown",
        "timestamp": time.time(),
    }

    # 检查数据库连接
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = f"error: {str(e)}"
        db_status = "unhealthy"

    overall_status = "healthy" if checks["database"] == "connected" else "unhealthy"

    return {
        "status": overall_status,
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check():
    """
    存活检查

    Kubernetes 等容器编排系统用于判断是否重启容器
    """
    return {
        "status": "alive",
        "timestamp": time.time(),
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    详细健康检查

    包含所有依赖项的详细状态
    """
    import sys
    import os

    checks = {}
    overall_healthy = True

    # 1. 数据库检查
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_time = (time.time() - start) * 1000  # ms
        checks["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_time, 2),
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_healthy = False

    # 2. 内存检查
    try:
        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        memory_percent = process.memory_percent()
        checks["memory"] = {
            "status": "warning" if memory_percent > 80 else "healthy",
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "percent": round(memory_percent, 2),
        }

        if memory_percent > 90:
            overall_healthy = False
    except ImportError:
        checks["memory"] = {
            "status": "unknown",
            "error": "psutil not installed",
        }
    except Exception as e:
        checks["memory"] = {
            "status": "unknown",
            "error": str(e),
        }

    # 3. 磁盘检查
    try:
        import psutil

        disk = psutil.disk_usage("/")
        disk_percent = disk.percent

        checks["disk"] = {
            "status": "warning" if disk_percent > 80 else "healthy",
            "percent": round(disk_percent, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
        }

        if disk_percent > 90:
            overall_healthy = False
    except Exception as e:
        checks["disk"] = {
            "status": "unknown",
            "error": str(e),
        }

    # 4. Python 版本
    checks["python"] = {
        "version": sys.version,
        "version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
        },
    }

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": time.time(),
        "checks": checks,
    }
