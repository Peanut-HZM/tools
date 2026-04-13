from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List
import re
import io
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["video-downloader"])

class VideoExtractRequest(BaseModel):
    url: HttpUrl

class VideoInfo(BaseModel):
    url: str
    type: str  # video/mp4, video/webm, etc.
    source: str  # video, source, iframe, etc.
    index: int
    duration: float = 0.0  # 视频时长（秒）

class VideoExtractResponse(BaseModel):
    videos: List[VideoInfo]
    count: int

@router.post("/tools/extract-videos", response_model=VideoExtractResponse)
async def extract_videos(request: VideoExtractRequest):
    """
    从指定网页提取所有视频URL
    """
    try:
        # 发送HTTP请求获取网页内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(str(request.url), headers=headers, timeout=10)
        response.raise_for_status()
        
        # 获取页面内容
        html_content = response.text
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        videos = []
        index = 0
        
        logger.debug("开始提取视频，URL: %s", request.url)
        
        def is_static_image(url: str) -> bool:
            """判断URL是否是静态图片（非视频/GIF）"""
            url_lower = url.lower()
            
            # 检查是否是静态图片格式
            static_image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.svg', '.ico']
            if any(ext in url_lower for ext in static_image_extensions):
                return True
            
            # 检查是否在纯图片目录（不包含gifs目录）
            if '/pics/' in url_lower and '/gifs/' not in url_lower:
                return True
            
            return False
        
        def should_include_video(url: str) -> bool:
            """判断是否应该包含这个视频"""
            # 必须是有效的URL
            if not is_valid_video_url(url):
                return False
            
            # 过滤静态图片
            if is_static_image(url):
                logger.debug("过滤静态图片: %s", url[:80])
                return False
            
            return True
        
        # 1. 提取 <video> 标签
        video_tags = soup.find_all('video')
        logger.debug("找到 %d 个 <video> 标签", len(video_tags))
        
        for video in video_tags:
            # 从video标签的src属性获取
            video_src = video.get('src')
            if video_src:
                absolute_url = urljoin(str(request.url), video_src)
                if should_include_video(absolute_url):
                    logger.debug("从video.src找到: %s", absolute_url)
                    videos.append(VideoInfo(
                        url=absolute_url,
                        type=get_video_type(absolute_url),
                        source='video',
                        index=index
                    ))
                    index += 1
            
            # 从video标签的data-src属性获取（懒加载）
            data_src = video.get('data-src') or video.get('data-video-src')
            if data_src:
                absolute_url = urljoin(str(request.url), data_src)
                if should_include_video(absolute_url):
                    logger.debug("从video.data-src找到: %s", absolute_url)
                    videos.append(VideoInfo(
                        url=absolute_url,
                        type=get_video_type(absolute_url),
                        source='video',
                        index=index
                    ))
                    index += 1
            
            # 从video标签内的source标签获取
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src') or source.get('data-src')
                if src:
                    absolute_url = urljoin(str(request.url), src)
                    if should_include_video(absolute_url):
                        video_type = source.get('type', get_video_type(absolute_url))
                        logger.debug("从source找到: %s", absolute_url)
                        videos.append(VideoInfo(
                            url=absolute_url,
                            type=video_type,
                            source='source',
                            index=index
                        ))
                        index += 1
        
        # 2. 提取 <source> 标签（独立的）
        source_tags = soup.find_all('source')
        logger.debug("找到 %d 个 <source> 标签", len(source_tags))
        
        for source in source_tags:
            src = source.get('src') or source.get('data-src')
            if src and is_video_extension(src):
                absolute_url = urljoin(str(request.url), src)
                if should_include_video(absolute_url):
                    video_type = source.get('type', get_video_type(absolute_url))
                    logger.debug("从独立source找到: %s", absolute_url)
                    videos.append(VideoInfo(
                        url=absolute_url,
                        type=video_type,
                        source='source',
                        index=index
                    ))
                    index += 1
        
        # 3. 提取嵌入的iframe视频（YouTube, Vimeo等）
        iframe_tags = soup.find_all('iframe')
        logger.debug("找到 %d 个 <iframe> 标签", len(iframe_tags))
        
        for iframe in iframe_tags:
            src = iframe.get('src') or iframe.get('data-src')
            if src:
                # 检查是否是视频平台
                if is_video_iframe(src):
                    absolute_url = urljoin(str(request.url), src)
                    logger.debug("从iframe找到视频平台: %s", absolute_url)
                    videos.append(VideoInfo(
                        url=absolute_url,
                        type='iframe',
                        source='iframe',
                        index=index
                    ))
                    index += 1
        
        # 4. 从页面脚本中提取视频URL（增强版）
        scripts = soup.find_all('script')
        logger.debug("找到 %d 个 <script> 标签", len(scripts))
        
        script_video_count = 0
        for script in scripts:
            if script.string:
                # 查找常见的视频URL模式（更宽松的匹配）
                video_patterns = [
                    r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.webm[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.ogg[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.mpd[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.mov[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.avi[^\s<>"\']*',
                    r'https?://[^\s<>"\']+?\.flv[^\s<>"\']*',
                ]
                
                for pattern in video_patterns:
                    video_urls = re.findall(pattern, script.string, re.IGNORECASE)
                    for video_url in video_urls:
                        # 清理URL（移除可能的尾部字符）
                        video_url = video_url.rstrip('\\",;)}]')
                        # 使用统一的过滤函数
                        if should_include_video(video_url):
                            logger.debug("从script找到: %s", video_url)
                            videos.append(VideoInfo(
                                url=video_url,
                                type=get_video_type(video_url),
                                source='script',
                                index=index
                            ))
                            index += 1
                            script_video_count += 1
        
        logger.debug("从script中找到 %d 个视频（已过滤静态图片）", script_video_count)
        
        # 5. 从HTML内容中直接搜索视频URL（作为备用）
        html_video_count = 0
        video_patterns = [
            r'https?://[^\s<>"\']+?\.mp4[^\s<>"\']*',
            r'https?://[^\s<>"\']+?\.webm[^\s<>"\']*',
            r'https?://[^\s<>"\']+?\.m3u8[^\s<>"\']*',
            # 添加更多模式来匹配可能的视频URL
            r'"(https?://[^"]+?/videos?/[^"]+?\.mp4[^"]*)"',
            r'"(https?://[^"]+?/media/[^"]+?\.mp4[^"]*)"',
            r'"(https?://[^"]+?/stream/[^"]+?\.mp4[^"]*)"',
        ]
        
        for pattern in video_patterns:
            video_urls = re.findall(pattern, html_content, re.IGNORECASE)
            for video_url in video_urls:
                # 如果是元组（带括号的捕获组），取第一个元素
                if isinstance(video_url, tuple):
                    video_url = video_url[0]
                video_url = video_url.rstrip('\\",;)}]')
                # 使用统一的过滤函数
                if should_include_video(video_url):
                    videos.append(VideoInfo(
                        url=video_url,
                        type=get_video_type(video_url),
                        source='html',
                        index=index
                    ))
                    index += 1
                    html_video_count += 1
        
        logger.debug("从HTML内容中找到 %d 个视频", html_video_count)
        
        # 6. 查找所有包含video关键字的属性
        all_tags = soup.find_all(True)
        data_attr_count = 0
        for tag in all_tags:
            for attr in ['data-video', 'data-video-url', 'data-src', 'data-mp4', 'data-webm']:
                value = tag.get(attr)
                if value and is_video_extension(value):
                    absolute_url = urljoin(str(request.url), value)
                    if should_include_video(absolute_url):
                        logger.debug("从data属性找到: %s", absolute_url)
                        videos.append(VideoInfo(
                            url=absolute_url,
                            type=get_video_type(absolute_url),
                            source='data-attribute',
                            index=index
                        ))
                        index += 1
                        data_attr_count += 1
        
        logger.debug("从data属性中找到 %d 个视频", data_attr_count)
        
        # 7. 专门查找高质量/完整视频（查找包含质量标识的URL）
        quality_patterns = [
            r'https?://[^\s<>"\']+?(?:1080P|720P|480P|original)[^\s<>"\']*?\.mp4[^\s<>"\']*',
            r'https?://[^\s<>"\']+?(?:1080P|720P|480P|original)[^\s<>"\']*?\.webm[^\s<>"\']*',
            r'https?://[^\s<>"\']+?/(?:hd|high|full)[^\s<>"\']*?\.mp4[^\s<>"\']*',
        ]
        
        hq_video_count = 0
        for pattern in quality_patterns:
            video_urls = re.findall(pattern, html_content, re.IGNORECASE)
            for video_url in video_urls:
                video_url = video_url.rstrip('\\",;)}]')
                if should_include_video(video_url):
                    logger.debug("从质量标识找到高质量视频: %s", video_url[:100])
                    videos.append(VideoInfo(
                        url=video_url,
                        type=get_video_type(video_url),
                        source='html',
                        index=index
                    ))
                    index += 1
                    hq_video_count += 1
        
        logger.debug("找到 %d 个高质量视频", hq_video_count)
        
        # 去重（基于URL）
        seen_urls = set()
        unique_videos = []
        for video in videos:
            if video.url not in seen_urls:
                seen_urls.add(video.url)
                unique_videos.append(video)
        
        logger.debug("去重后共 %d 个唯一视频", len(unique_videos))
        
        # 获取视频时长（仅对非iframe视频）
        logger.debug("开始获取视频时长...")
        for video in unique_videos:
            if video.source != 'iframe':
                duration = get_video_duration(video.url)
                video.duration = duration
                if duration > 0:
                    logger.debug("视频时长: %.1f秒 - %s", duration, video.url[:80])
        
        # 按时长逆序排序（时长最长的在前面）
        unique_videos.sort(key=lambda v: v.duration, reverse=True)
        logger.debug("已按时长排序")
        
        return VideoExtractResponse(
            videos=unique_videos,
            count=len(unique_videos)
        )
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法访问该网页: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"提取视频失败: {str(e)}"
        )

def is_valid_video_url(url: str) -> bool:
    """检查URL是否有效"""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False

def get_video_duration(url: str) -> float:
    """
    尝试获取视频时长（秒）
    注意：这个方法可能不总是有效，因为需要下载部分视频数据
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Range': 'bytes=0-1048576'  # 只下载前1MB来获取元数据
        }
        
        # 设置短超时，避免等待太久
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        
        # 尝试从Content-Range或Content-Length获取文件大小
        content_length = response.headers.get('Content-Length')
        if content_length:
            # 根据文件大小粗略估算时长（假设平均码率）
            # 这只是一个粗略估计
            file_size_mb = int(content_length) / (1024 * 1024)
            # 假设平均码率为 2 Mbps
            estimated_duration = (file_size_mb * 8) / 2
            return estimated_duration
        
        return 0.0
    except:
        return 0.0

def is_video_extension(url: str) -> bool:
    """检查URL是否包含视频扩展名"""
    video_extensions = [
        '.mp4', '.webm', '.ogg', '.mov', '.avi', '.flv', '.wmv', 
        '.m3u8', '.mpd', '.mkv', '.m4v', '.3gp', '.ts'
    ]
    url_lower = url.lower()
    return any(ext in url_lower for ext in video_extensions)

def get_video_type(url: str) -> str:
    """根据URL获取视频类型"""
    url_lower = url.lower()
    if '.mp4' in url_lower or '.m4v' in url_lower:
        return 'video/mp4'
    elif '.webm' in url_lower:
        return 'video/webm'
    elif '.ogg' in url_lower:
        return 'video/ogg'
    elif '.m3u8' in url_lower:
        return 'application/x-mpegURL'
    elif '.mpd' in url_lower:
        return 'application/dash+xml'
    elif '.mov' in url_lower:
        return 'video/quicktime'
    elif '.avi' in url_lower:
        return 'video/x-msvideo'
    elif '.flv' in url_lower:
        return 'video/x-flv'
    elif '.mkv' in url_lower:
        return 'video/x-matroska'
    elif '.ts' in url_lower:
        return 'video/mp2t'
    else:
        return 'video/mp4'

def is_video_iframe(url: str) -> bool:
    """检查iframe URL是否是视频平台"""
    video_platforms = [
        'youtube.com', 'youtu.be', 'youtube-nocookie.com',
        'vimeo.com', 'player.vimeo.com',
        'dailymotion.com', 'dai.ly',
        'bilibili.com', 'b23.tv',
        'twitch.tv',
        'facebook.com/video', 'fb.watch',
        'tiktok.com',
        'instagram.com',
        'twitter.com', 'x.com',
        'streamable.com',
        'wistia.com',
        'brightcove.com',
        'jwplayer.com',
        'videopress.com',
    ]
    url_lower = url.lower()
    return any(platform in url_lower for platform in video_platforms)

@router.get("/tools/download-video")
async def download_video(url: str):
    """
    代理下载视频，解决跨域问题
    支持普通视频和HLS流媒体
    """
    # 检查是否是HLS流媒体（.m3u8或.ts文件）
    if '.m3u8' in url.lower() or '/hls/' in url.lower() or '.ts' in url.lower():
        # HLS流媒体，需要特殊处理
        # 尝试找到master.m3u8文件
        if '.ts' in url:
            # 如果是.ts分段，尝试构建m3u8 URL
            base_url = url.split('/seg-')[0] if '/seg-' in url else url.rsplit('/', 1)[0]
            m3u8_url = f"{base_url}/master.m3u8"
            
            error_msg = (
                "⚠️ 这是HLS流媒体视频（.ts分段文件），无法直接下载。\n\n"
                "📝 推荐下载方法：\n\n"
                "1️⃣ 使用 ffmpeg（推荐）：\n"
                f"   ffmpeg -i \"{m3u8_url}\" -c copy output.mp4\n\n"
                "2️⃣ 使用 yt-dlp：\n"
                f"   yt-dlp \"{m3u8_url}\"\n\n"
                "3️⃣ 使用 IDM 或其他专业下载工具\n\n"
                f"💡 M3U8播放列表地址：\n{m3u8_url}\n\n"
                "ℹ️ HLS视频由多个.ts分段组成，需要下载所有分段并合并。"
            )
        else:
            error_msg = (
                "⚠️ 这是HLS流媒体视频（.m3u8播放列表），需要使用专业工具下载。\n\n"
                "📝 推荐下载方法：\n\n"
                "1️⃣ 使用 ffmpeg（推荐）：\n"
                f"   ffmpeg -i \"{url}\" -c copy output.mp4\n\n"
                "2️⃣ 使用 yt-dlp：\n"
                f"   yt-dlp \"{url}\"\n\n"
                "3️⃣ 使用 IDM 或其他专业下载工具\n\n"
                "ℹ️ HLS视频由多个分段组成，需要专业工具下载并合并。"
            )
        
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    try:
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': url,
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5'
        }
        
        # 设置较长的超时时间，因为视频文件可能很大
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # 获取内容类型
        content_type = response.headers.get('content-type', 'video/mp4')
        
        # 获取文件扩展名
        ext = 'mp4'
        if 'webm' in content_type:
            ext = 'webm'
        elif 'ogg' in content_type:
            ext = 'ogg'
        elif 'quicktime' in content_type or 'mov' in content_type:
            ext = 'mov'
        elif 'x-msvideo' in content_type:
            ext = 'avi'
        elif 'x-flv' in content_type:
            ext = 'flv'
        elif 'x-matroska' in content_type:
            ext = 'mkv'
        
        # 从URL中提取文件名
        parsed_url = urlparse(url)
        url_filename = parsed_url.path.split('/')[-1]
        if url_filename and '.' in url_filename:
            filename = url_filename
        else:
            filename = f"video.{ext}"
        
        # 返回视频流
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': '*'
            }
        )
        
    except requests.Timeout:
        raise HTTPException(
            status_code=408,
            detail="下载超时，视频文件可能太大，请使用专业下载工具"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法下载视频: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"下载失败: {str(e)}"
        )
