"""
yt-dlp 视频下载 API 路由
提供视频下载、任务管理、格式查询等接口
"""

import asyncio
import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
import aiofiles

from app.services.download_manager import get_manager, TaskStatus
from app.services.ytdlp_service import get_downloader, DownloadError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ytdlp-downloader"])

# 数据模型
class DownloadRequest(BaseModel):
    url: HttpUrl
    quality: str = "best"  # best, worst, 1080p, 720p, 480p, 360p

class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    file_size: Optional[str] = None
    speed: Optional[str] = None
    eta: Optional[str] = None
    error: Optional[str] = None

class VideoFormatResponse(BaseModel):
    format_id: str
    quality: str
    ext: str
    filesize: Optional[int]
    vcodec: str
    acodec: str
    fps: Optional[int]
    resolution: str

class VideoFormatsResponse(BaseModel):
    formats: list[VideoFormatResponse]
    count: int

class StatsResponse(BaseModel):
    total_tasks: int
    pending: int
    downloading: int
    completed: int
    failed: int
    success_rate: float


# 辅助函数
def format_bytes(bytes_value: int) -> str:
    """格式化字节数"""
    if bytes_value < 1024:
        return f"{bytes_value}B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f}KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024:.1f}MB"
    else:
        return f"{bytes_value / 1024 / 1024 / 1024:.1f}GB"


def format_speed(bytes_per_sec: float) -> str:
    """格式化速度"""
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f}B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f}KB/s"
    else:
        return f"{bytes_per_sec / 1024 / 1024:.1f}MB/s"


def format_time(seconds: float) -> str:
    """格式化时间"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


# API 端点
@router.post("/tools/download-video-ytdlp", response_model=DownloadResponse)
async def create_download_task(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    创建视频下载任务
    
    - **url**: 视频URL
    - **quality**: 视频质量 (best, worst, 1080p, 720p, 480p, 360p)
    
    返回任务ID，可用于查询下载进度
    """
    try:
        manager = get_manager()
        
        # 创建任务
        task_id = manager.create_task(str(request.url), request.quality)
        
        # 在后台执行下载
        background_tasks.add_task(manager.download_task, task_id)
        
        return DownloadResponse(
            task_id=task_id,
            status="pending",
            message="下载任务已创建，正在排队中..."
        )
        
    except Exception as e:
        logger.error(f"Failed to create download task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"创建下载任务失败: {str(e)}"
        )


@router.get("/tools/download-task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询下载任务状态
    
    - **task_id**: 任务ID
    
    返回任务的详细状态信息
    """
    manager = get_manager()
    task = manager.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    
    # 格式化响应
    response = TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=round(task.progress, 2),
        error=task.error
    )
    
    # 添加下载统计信息
    if task.status == TaskStatus.DOWNLOADING:
        if task.total_bytes > 0:
            response.file_size = format_bytes(task.total_bytes)
        if task.speed > 0:
            response.speed = format_speed(task.speed)
        if task.eta > 0:
            response.eta = format_time(task.eta)
    
    return response


@router.get("/tools/download-file/{task_id}")
async def download_file(task_id: str):
    """
    下载已完成的视频文件
    
    - **task_id**: 任务ID
    
    返回视频文件流
    """
    manager = get_manager()
    task = manager.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态: {task.status.value}"
        )
    
    if not task.file_path or not os.path.exists(task.file_path):
        raise HTTPException(
            status_code=404,
            detail="文件不存在"
        )
    
    # 获取文件名
    filename = os.path.basename(task.file_path)
    
    # 流式传输文件
    async def file_iterator():
        async with aiofiles.open(task.file_path, 'rb') as f:
            while chunk := await f.read(8192):
                yield chunk
    
    return StreamingResponse(
        file_iterator(),
        media_type='video/mp4',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': '*'
        }
    )


@router.get("/tools/video-formats", response_model=VideoFormatsResponse)
async def get_video_formats(url: str):
    """
    获取视频的所有可用格式
    
    - **url**: 视频URL
    
    返回格式列表
    """
    try:
        downloader = get_downloader()
        
        # 在线程池中执行（避免阻塞）
        formats = await asyncio.to_thread(downloader.get_formats, url)
        
        # 转换为响应格式
        format_list = [
            VideoFormatResponse(
                format_id=fmt.format_id,
                quality=fmt.quality,
                ext=fmt.ext,
                filesize=fmt.filesize,
                vcodec=fmt.vcodec,
                acodec=fmt.acodec,
                fps=fmt.fps,
                resolution=fmt.resolution
            )
            for fmt in formats
        ]
        
        return VideoFormatsResponse(
            formats=format_list,
            count=len(format_list)
        )
        
    except DownloadError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get video formats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取视频格式失败: {str(e)}"
        )


@router.delete("/tools/download-task/{task_id}")
async def cancel_task(task_id: str):
    """
    取消下载任务
    
    - **task_id**: 任务ID
    """
    manager = get_manager()
    
    if not manager.get_task(task_id):
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    
    success = manager.cancel_task(task_id)
    
    if success:
        return {"message": "任务已取消"}
    else:
        raise HTTPException(
            status_code=400,
            detail="无法取消该任务（可能已完成或失败）"
        )


@router.get("/tools/download-stats", response_model=StatsResponse)
async def get_download_stats():
    """
    获取下载统计信息
    
    返回所有任务的统计数据
    """
    manager = get_manager()
    stats = manager.get_stats()
    
    return StatsResponse(**stats)
