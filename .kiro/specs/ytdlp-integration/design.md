# Design Document - yt-dlp Integration

## Overview

本设计文档描述了如何将 yt-dlp 集成到视频下载器中，实现服务器端视频下载功能。系统将使用 yt-dlp 的 Python API 下载 HLS 流媒体和其他复杂格式的视频，并通过异步任务和流式传输提供良好的用户体验。

## Architecture

### High-Level Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │────────▶│   Backend    │────────▶│   yt-dlp    │
│   (React)   │         │  (FastAPI)   │         │   Library   │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │                         │
      │                        ▼                         ▼
      │                 ┌──────────────┐         ┌─────────────┐
      │                 │  Task Queue  │         │ Video Sites │
      │                 │  (In-Memory) │         │ (YouTube等) │
      │                 └──────────────┘         └─────────────┘
      │                        │
      ▼                        ▼
┌─────────────┐         ┌──────────────┐
│  Progress   │         │   Temp Dir   │
│  Updates    │         │  (/tmp/...)  │
└─────────────┘         └──────────────┘
```

### Component Diagram

```
Backend Components:
├── video_downloader.py (existing)
│   ├── extract_videos()
│   └── download_video() (updated)
├── ytdlp_service.py (new)
│   ├── YtdlpDownloader
│   ├── download_with_ytdlp()
│   ├── get_video_formats()
│   └── get_download_progress()
├── download_manager.py (new)
│   ├── DownloadTask
│   ├── create_task()
│   ├── get_task_status()
│   └── cleanup_old_tasks()
└── config.py (new)
    ├── YTDLP_OPTIONS
    ├── MAX_FILE_SIZE
    └── TEMP_DIR
```

## Components and Interfaces

### 1. YtdlpService (ytdlp_service.py)

核心下载服务，封装 yt-dlp 功能。

```python
class YtdlpDownloader:
    """yt-dlp 下载器封装类"""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.ydl_opts = self._get_default_options()
    
    def download(self, url: str, quality: str = 'best') -> str:
        """
        下载视频并返回文件路径
        
        Args:
            url: 视频URL
            quality: 质量选项 (best, 1080p, 720p, 480p)
        
        Returns:
            下载的文件路径
        
        Raises:
            DownloadError: 下载失败
        """
        pass
    
    def get_formats(self, url: str) -> List[VideoFormat]:
        """
        获取视频的所有可用格式
        
        Args:
            url: 视频URL
        
        Returns:
            格式列表
        """
        pass
    
    def get_info(self, url: str) -> Dict:
        """
        获取视频信息（不下载）
        
        Args:
            url: 视频URL
        
        Returns:
            视频元数据
        """
        pass
```

### 2. DownloadManager (download_manager.py)

管理下载任务的生命周期。

```python
class DownloadTask:
    """下载任务数据模型"""
    task_id: str
    url: str
    status: str  # pending, downloading, completed, failed
    progress: float  # 0-100
    file_path: Optional[str]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

class DownloadManager:
    """下载任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, DownloadTask] = {}
        self.downloader = YtdlpDownloader(TEMP_DIR)
    
    async def create_task(self, url: str, quality: str) -> str:
        """创建下载任务并返回任务ID"""
        pass
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务状态"""
        pass
    
    async def download_task(self, task_id: str):
        """执行下载任务（后台运行）"""
        pass
    
    def cleanup_old_tasks(self):
        """清理旧任务和临时文件"""
        pass
```

### 3. API Endpoints

#### POST /api/tools/download-video-ytdlp
创建下载任务

**Request:**
```json
{
  "url": "https://example.com/video.m3u8",
  "quality": "best"
}
```

**Response:**
```json
{
  "task_id": "abc123",
  "status": "pending",
  "message": "下载任务已创建"
}
```

#### GET /api/tools/download-task/{task_id}
查询任务状态

**Response:**
```json
{
  "task_id": "abc123",
  "status": "downloading",
  "progress": 45.5,
  "file_size": "125MB",
  "speed": "2.5MB/s",
  "eta": "30s"
}
```

#### GET /api/tools/download-file/{task_id}
下载完成的文件

**Response:**
- 200: 文件流
- 404: 任务不存在或未完成

#### GET /api/tools/video-formats
获取视频可用格式

**Request:**
```
?url=https://example.com/video
```

**Response:**
```json
{
  "formats": [
    {
      "format_id": "137",
      "quality": "1080p",
      "ext": "mp4",
      "filesize": 125000000
    },
    {
      "format_id": "136",
      "quality": "720p",
      "ext": "mp4",
      "filesize": 75000000
    }
  ]
}
```

## Data Models

### VideoFormat
```python
class VideoFormat(BaseModel):
    format_id: str
    quality: str  # 1080p, 720p, etc.
    ext: str  # mp4, webm, etc.
    filesize: Optional[int]
    vcodec: str
    acodec: str
    fps: Optional[int]
```

### DownloadRequest
```python
class DownloadRequest(BaseModel):
    url: HttpUrl
    quality: str = "best"  # best, 1080p, 720p, 480p, worst
```

### DownloadResponse
```python
class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str
```

### TaskStatus
```python
class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, downloading, completed, failed
    progress: float  # 0-100
    file_size: Optional[str]
    speed: Optional[str]
    eta: Optional[str]
    error: Optional[str]
```

## Implementation Details

### yt-dlp Options Configuration

```python
YTDLP_OPTIONS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': '%(id)s.%(ext)s',
    'quiet': False,
    'no_warnings': False,
    'extract_flat': False,
    'socket_timeout': 30,
    'retries': 3,
    'fragment_retries': 3,
    'http_chunk_size': 10485760,  # 10MB
    'concurrent_fragment_downloads': 5,
    'max_filesize': 524288000,  # 500MB
    'progress_hooks': [progress_hook],
}
```

### Progress Hook Implementation

```python
def progress_hook(d):
    """yt-dlp 进度回调"""
    if d['status'] == 'downloading':
        task_id = d.get('task_id')
        if task_id:
            progress = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            # 更新任务状态
            manager.update_task_progress(task_id, progress, speed, eta)
    
    elif d['status'] == 'finished':
        task_id = d.get('task_id')
        if task_id:
            manager.mark_task_completed(task_id, d['filename'])
```

### Async Download Implementation

```python
async def download_video_async(task_id: str, url: str, quality: str):
    """异步下载视频"""
    try:
        # 更新状态为下载中
        manager.update_task_status(task_id, 'downloading')
        
        # 使用 yt-dlp 下载
        file_path = await asyncio.to_thread(
            downloader.download,
            url,
            quality,
            task_id=task_id
        )
        
        # 更新状态为完成
        manager.mark_task_completed(task_id, file_path)
        
    except Exception as e:
        # 更新状态为失败
        manager.mark_task_failed(task_id, str(e))
        logger.error(f"Download failed for task {task_id}: {e}")
```

### Temporary File Cleanup

```python
async def cleanup_task():
    """定期清理任务（后台任务）"""
    while True:
        await asyncio.sleep(3600)  # 每小时运行一次
        
        now = datetime.now()
        for task_id, task in list(manager.tasks.items()):
            # 删除超过1小时的已完成任务
            if task.status in ['completed', 'failed']:
                if (now - task.updated_at).seconds > 3600:
                    if task.file_path and os.path.exists(task.file_path):
                        os.remove(task.file_path)
                    del manager.tasks[task_id]
```

## Error Handling

### Error Types

```python
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
```

### Error Handling Strategy

```python
try:
    file_path = downloader.download(url, quality)
except NetworkError as e:
    return {"error": "网络连接失败，请检查网络后重试"}
except FormatNotAvailableError as e:
    return {"error": "请求的视频质量不可用，请选择其他质量"}
except FileSizeLimitError as e:
    return {"error": "视频文件超过500MB限制"}
except UnsupportedSiteError as e:
    return {"error": "该网站暂不支持，请使用其他下载方式"}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"error": "下载失败，请稍后重试"}
```

## Testing Strategy

### Unit Tests

1. **YtdlpDownloader Tests**
   - 测试基本下载功能
   - 测试格式选择
   - 测试错误处理

2. **DownloadManager Tests**
   - 测试任务创建
   - 测试任务状态更新
   - 测试任务清理

### Integration Tests

1. **API Endpoint Tests**
   - 测试创建下载任务
   - 测试查询任务状态
   - 测试文件下载

2. **End-to-End Tests**
   - 测试完整下载流程
   - 测试进度更新
   - 测试错误恢复

### Property-Based Tests

**Property 1: 下载完整性**
*For any* 成功下载的视频，文件应该存在且大小大于0

**Property 2: 任务状态一致性**
*For any* 下载任务，状态转换应该遵循：pending → downloading → (completed | failed)

**Property 3: 临时文件清理**
*For any* 超过1小时的已完成任务，其临时文件应该被删除

## Security Considerations

### URL Validation
```python
def validate_url(url: str) -> bool:
    """验证URL安全性"""
    # 检查协议
    if not url.startswith(('http://', 'https://')):
        return False
    
    # 检查是否为本地地址
    parsed = urlparse(url)
    if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
        return False
    
    # 检查是否为内网地址
    if is_private_ip(parsed.hostname):
        return False
    
    return True
```

### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/tools/download-video-ytdlp")
@limiter.limit("10/minute")  # 每分钟最多10次
async def create_download_task(request: DownloadRequest):
    pass
```

### File Size Limits
```python
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

ydl_opts = {
    'max_filesize': MAX_FILE_SIZE,
    # ...
}
```

## Performance Optimization

### Concurrent Downloads
```python
MAX_CONCURRENT_DOWNLOADS = 5
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

async def download_with_limit(task_id: str, url: str, quality: str):
    async with download_semaphore:
        await download_video_async(task_id, url, quality)
```

### Caching Video Info
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_video_info_cached(url: str) -> Dict:
    """缓存视频信息"""
    return downloader.get_info(url)
```

### Streaming Response
```python
async def stream_file(file_path: str):
    """流式传输文件"""
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(8192):
            yield chunk
```

## Deployment Considerations

### Dependencies
```txt
yt-dlp>=2023.12.30
aiofiles>=23.2.1
slowapi>=0.1.9
```

### Environment Variables
```bash
YTDLP_TEMP_DIR=/tmp/ytdlp_downloads
YTDLP_MAX_FILE_SIZE=524288000
YTDLP_MAX_CONCURRENT=5
YTDLP_CLEANUP_INTERVAL=3600
```

### Docker Configuration
```dockerfile
# 安装 ffmpeg（yt-dlp 需要）
RUN apt-get update && apt-get install -y ffmpeg

# 创建临时目录
RUN mkdir -p /tmp/ytdlp_downloads && chmod 777 /tmp/ytdlp_downloads
```

---

**创建时间**: 2024-12-28  
**状态**: 📝 设计文档  
**版本**: 1.0.0
