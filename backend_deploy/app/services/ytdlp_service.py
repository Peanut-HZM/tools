"""
yt-dlp 视频下载服务
封装 yt-dlp 功能，提供视频下载、格式查询等功能
"""

import os
import uuid
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path
import yt_dlp
import imageio_ffmpeg

logger = logging.getLogger(__name__)

# 配置
# 使用项目根目录下的downloads文件夹
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # 从backend/app/services/回到项目根目录
TEMP_DIR = str(PROJECT_ROOT / "downloads")
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
DOWNLOAD_TIMEOUT = 600  # 10分钟


class VideoFormat:
    """视频格式信息"""
    def __init__(self, format_dict: Dict):
        self.format_id = format_dict.get('format_id', '')
        self.ext = format_dict.get('ext', 'mp4')
        self.quality = self._parse_quality(format_dict)
        self.filesize = format_dict.get('filesize') or format_dict.get('filesize_approx', 0)
        self.vcodec = format_dict.get('vcodec', 'unknown')
        self.acodec = format_dict.get('acodec', 'unknown')
        self.fps = format_dict.get('fps')
        self.resolution = format_dict.get('resolution', 'unknown')
        
    def _parse_quality(self, format_dict: Dict) -> str:
        """解析质量标识"""
        height = format_dict.get('height')
        if height:
            if height >= 2160:
                return '4K'
            elif height >= 1440:
                return '2K'
            elif height >= 1080:
                return '1080p'
            elif height >= 720:
                return '720p'
            elif height >= 480:
                return '480p'
            elif height >= 360:
                return '360p'
            else:
                return f'{height}p'
        return format_dict.get('format_note', 'unknown')
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'format_id': self.format_id,
            'quality': self.quality,
            'ext': self.ext,
            'filesize': self.filesize,
            'vcodec': self.vcodec,
            'acodec': self.acodec,
            'fps': self.fps,
            'resolution': self.resolution
        }


class DownloadError(Exception):
    """下载错误基类"""
    pass


class NetworkError(DownloadError):
    """网络错误"""
    pass


class FormatNotAvailableError(DownloadError):
    """格式不可用"""
    pass


class FileSizeLimitError(DownloadError):
    """文件大小超限"""
    pass


class UnsupportedSiteError(DownloadError):
    """不支持的网站"""
    pass


class YtdlpDownloader:
    """yt-dlp 下载器封装类"""
    
    def __init__(self, temp_dir: str = TEMP_DIR):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取 ffmpeg 路径
        self.ffmpeg_location = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"Using ffmpeg at: {self.ffmpeg_location}")
        
        # 进度回调存储
        self.progress_callbacks: Dict[str, Callable] = {}
    
    def _get_ydl_opts(self, task_id: Optional[str] = None, quality: str = 'best') -> Dict:
        """获取 yt-dlp 配置选项"""
        
        # 根据质量选择格式
        if quality == 'best':
            format_selector = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality == 'worst':
            format_selector = 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst'
        else:
            # 指定质量 (1080p, 720p, 480p, etc.)
            height = quality.replace('p', '').replace('P', '')
            format_selector = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
        
        opts = {
            'format': format_selector,
            'outtmpl': str(self.temp_dir / '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'http_chunk_size': 10485760,  # 10MB
            'concurrent_fragment_downloads': 5,
            'max_filesize': MAX_FILE_SIZE,
            'ffmpeg_location': self.ffmpeg_location,
            'merge_output_format': 'mp4',
        }
        
        # 添加进度回调
        if task_id and task_id in self.progress_callbacks:
            opts['progress_hooks'] = [self.progress_callbacks[task_id]]
        
        return opts
    
    def register_progress_callback(self, task_id: str, callback: Callable):
        """注册进度回调函数"""
        self.progress_callbacks[task_id] = callback
    
    def unregister_progress_callback(self, task_id: str):
        """注销进度回调函数"""
        if task_id in self.progress_callbacks:
            del self.progress_callbacks[task_id]
    
    def download(self, url: str, quality: str = 'best', task_id: Optional[str] = None) -> str:
        """
        下载视频并返回文件路径
        
        Args:
            url: 视频URL
            quality: 质量选项 (best, worst, 1080p, 720p, 480p, 360p)
            task_id: 任务ID（用于进度回调）
        
        Returns:
            下载的文件路径
        
        Raises:
            DownloadError: 下载失败
        """
        try:
            ydl_opts = self._get_ydl_opts(task_id, quality)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 先获取信息
                info = ydl.extract_info(url, download=False)
                
                # 检查文件大小（如果可用）
                filesize = info.get('filesize') or info.get('filesize_approx', 0)
                if filesize and filesize > MAX_FILE_SIZE:
                    raise FileSizeLimitError(f"视频文件大小 ({filesize / 1024 / 1024:.1f}MB) 超过限制 (500MB)")
                
                # 下载视频
                info = ydl.extract_info(url, download=True)
                
                # 获取下载的文件路径
                if 'requested_downloads' in info:
                    file_path = info['requested_downloads'][0]['filepath']
                else:
                    # 构建文件路径
                    video_id = info.get('id', str(uuid.uuid4()))
                    ext = info.get('ext', 'mp4')
                    file_path = str(self.temp_dir / f"{video_id}.{ext}")
                
                if not os.path.exists(file_path):
                    raise DownloadError(f"下载完成但文件不存在: {file_path}")
                
                logger.info(f"Video downloaded successfully: {file_path}")
                return file_path
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if 'Unsupported URL' in error_msg or 'not supported' in error_msg:
                raise UnsupportedSiteError(f"该网站暂不支持: {error_msg}")
            elif 'HTTP Error' in error_msg or 'URLError' in error_msg:
                raise NetworkError(f"网络连接失败: {error_msg}")
            elif 'format' in error_msg.lower():
                raise FormatNotAvailableError(f"请求的视频质量不可用: {error_msg}")
            else:
                raise DownloadError(f"下载失败: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise DownloadError(f"下载失败: {str(e)}")
    
    def get_formats(self, url: str) -> List[VideoFormat]:
        """
        获取视频的所有可用格式
        
        Args:
            url: 视频URL
        
        Returns:
            格式列表
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                formats = []
                if 'formats' in info:
                    # 过滤出有视频的格式
                    for fmt in info['formats']:
                        if fmt.get('vcodec') != 'none':
                            formats.append(VideoFormat(fmt))
                
                # 按质量排序（从高到低）
                formats.sort(key=lambda x: x.filesize or 0, reverse=True)
                
                return formats
                
        except Exception as e:
            logger.error(f"Error getting formats: {e}")
            raise DownloadError(f"获取视频格式失败: {str(e)}")
    
    def get_info(self, url: str) -> Dict:
        """
        获取视频信息（不下载）
        
        Args:
            url: 视频URL
        
        Returns:
            视频元数据
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'description': info.get('description'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'filesize': info.get('filesize') or info.get('filesize_approx'),
                }
                
        except Exception as e:
            logger.error(f"Error getting info: {e}")
            raise DownloadError(f"获取视频信息失败: {str(e)}")


# 全局下载器实例
_downloader_instance = None


def get_downloader() -> YtdlpDownloader:
    """获取全局下载器实例"""
    global _downloader_instance
    if _downloader_instance is None:
        _downloader_instance = YtdlpDownloader()
    return _downloader_instance
