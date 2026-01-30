"""
下载任务管理器
管理视频下载任务的生命周期、进度跟踪和文件清理
"""

import asyncio
import uuid
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
from enum import Enum

from app.services.ytdlp_service import get_downloader, DownloadError

logger = logging.getLogger(__name__)

# 配置
# 使用项目根目录下的downloads文件夹
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # 从backend/app/services/回到项目根目录
TEMP_DIR = str(PROJECT_ROOT / "downloads")
CLEANUP_INTERVAL = 3600  # 1小时
TASK_EXPIRY = 3600  # 任务过期时间：1小时


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadTask:
    """下载任务数据模型"""
    
    def __init__(self, task_id: str, url: str, quality: str = 'best'):
        self.task_id = task_id
        self.url = url
        self.quality = quality
        self.status = TaskStatus.PENDING
        self.progress = 0.0  # 0-100
        self.file_path: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 下载统计
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0  # bytes/s
        self.eta = 0  # seconds
    
    def update_progress(self, downloaded: int, total: int, speed: float, eta: float):
        """更新下载进度"""
        self.downloaded_bytes = downloaded
        self.total_bytes = total
        self.speed = speed
        self.eta = eta
        
        if total > 0:
            self.progress = (downloaded / total) * 100
        
        self.updated_at = datetime.now()
    
    def mark_completed(self, file_path: str):
        """标记任务完成"""
        self.status = TaskStatus.COMPLETED
        self.file_path = file_path
        self.progress = 100.0
        self.updated_at = datetime.now()
    
    def mark_failed(self, error: str):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.updated_at = datetime.now()
    
    def mark_cancelled(self):
        """标记任务取消"""
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'url': self.url,
            'quality': self.quality,
            'status': self.status.value,
            'progress': round(self.progress, 2),
            'file_path': self.file_path,
            'error': self.error,
            'downloaded_bytes': self.downloaded_bytes,
            'total_bytes': self.total_bytes,
            'speed': self.speed,
            'eta': self.eta,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class DownloadManager:
    """下载任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, DownloadTask] = {}
        self.downloader = get_downloader()
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 并发控制
        self.max_concurrent = 5
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 启动清理任务
        self._cleanup_task = None
    
    def create_task(self, url: str, quality: str = 'best') -> str:
        """
        创建下载任务并返回任务ID
        
        Args:
            url: 视频URL
            quality: 质量选项
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task = DownloadTask(task_id, url, quality)
        self.tasks[task_id] = task
        
        logger.info(f"Created download task: {task_id} for URL: {url}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务对象，如果不存在返回None
        """
        return self.tasks.get(task_id)
    
    async def download_task(self, task_id: str):
        """
        执行下载任务（后台运行）
        
        Args:
            task_id: 任务ID
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        # 使用信号量控制并发
        async with self.semaphore:
            try:
                # 更新状态为下载中
                task.status = TaskStatus.DOWNLOADING
                task.updated_at = datetime.now()
                
                # 注册进度回调
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        speed = d.get('speed', 0) or 0
                        eta = d.get('eta', 0) or 0
                        
                        task.update_progress(downloaded, total, speed, eta)
                        
                        logger.debug(f"Task {task_id}: {task.progress:.1f}% - {speed/1024/1024:.2f}MB/s")
                    
                    elif d['status'] == 'finished':
                        logger.info(f"Task {task_id}: Download finished, now post-processing...")
                
                self.downloader.register_progress_callback(task_id, progress_hook)
                
                # 使用 asyncio.to_thread 在线程池中执行下载
                file_path = await asyncio.to_thread(
                    self.downloader.download,
                    task.url,
                    task.quality,
                    task_id
                )
                
                # 标记完成
                task.mark_completed(file_path)
                logger.info(f"Task {task_id} completed successfully: {file_path}")
                
            except DownloadError as e:
                task.mark_failed(str(e))
                logger.error(f"Task {task_id} failed: {e}")
            except Exception as e:
                task.mark_failed(f"未知错误: {str(e)}")
                logger.error(f"Task {task_id} failed with unexpected error: {e}", exc_info=True)
            finally:
                # 注销进度回调
                self.downloader.unregister_progress_callback(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消下载任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功取消
        """
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.PENDING, TaskStatus.DOWNLOADING]:
            task.mark_cancelled()
            logger.info(f"Task {task_id} cancelled")
            return True
        
        return False
    
    def cleanup_old_tasks(self):
        """清理旧任务和临时文件"""
        now = datetime.now()
        expired_tasks = []
        
        for task_id, task in list(self.tasks.items()):
            # 删除超过1小时的已完成或失败任务
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if (now - task.updated_at).total_seconds() > TASK_EXPIRY:
                    # 删除文件
                    if task.file_path and os.path.exists(task.file_path):
                        try:
                            os.remove(task.file_path)
                            logger.info(f"Deleted file: {task.file_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete file {task.file_path}: {e}")
                    
                    expired_tasks.append(task_id)
        
        # 删除过期任务
        for task_id in expired_tasks:
            del self.tasks[task_id]
            logger.info(f"Removed expired task: {task_id}")
        
        if expired_tasks:
            logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")
    
    def get_stats(self) -> Dict:
        """获取下载统计"""
        total = len(self.tasks)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        downloading = sum(1 for t in self.tasks.values() if t.status == TaskStatus.DOWNLOADING)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        
        return {
            'total_tasks': total,
            'pending': pending,
            'downloading': downloading,
            'completed': completed,
            'failed': failed,
            'success_rate': (completed / total * 100) if total > 0 else 0,
        }
    
    async def start_cleanup_task(self):
        """启动后台清理任务"""
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL)
            try:
                self.cleanup_old_tasks()
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", exc_info=True)


# 全局管理器实例
_manager_instance = None


def get_manager() -> DownloadManager:
    """获取全局管理器实例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DownloadManager()
    return _manager_instance
