from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List
import io

router = APIRouter(tags=["image-downloader"])

class ImageExtractRequest(BaseModel):
    url: HttpUrl

class ImageInfo(BaseModel):
    url: str
    alt: str
    index: int

class ImageExtractResponse(BaseModel):
    images: List[ImageInfo]
    count: int

@router.post("/tools/extract-images", response_model=ImageExtractResponse)
async def extract_images(request: ImageExtractRequest):
    """
    从指定网页提取所有图片URL
    """
    try:
        # 发送HTTP请求获取网页内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(str(request.url), headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 提取所有图片
        images = []
        img_tags = soup.find_all('img')
        
        for index, img in enumerate(img_tags):
            # 获取图片URL
            img_url = img.get('src') or img.get('data-src') or img.get('data-original')
            
            if not img_url:
                continue
            
            # 转换为绝对URL
            absolute_url = urljoin(str(request.url), img_url)
            
            # 过滤掉无效的URL
            parsed = urlparse(absolute_url)
            if not parsed.scheme or not parsed.netloc:
                continue
            
            # 过滤掉太小的图片（可能是图标或像素追踪）
            # 这里简单判断URL，实际使用中可以获取图片尺寸
            if any(x in absolute_url.lower() for x in ['1x1', 'pixel', 'tracking']):
                continue
            
            # 获取alt属性
            alt = img.get('alt', '')
            
            images.append(ImageInfo(
                url=absolute_url,
                alt=alt,
                index=index
            ))
        
        # 去重（基于URL）
        seen_urls = set()
        unique_images = []
        for img in images:
            if img.url not in seen_urls:
                seen_urls.add(img.url)
                unique_images.append(img)
        
        return ImageExtractResponse(
            images=unique_images,
            count=len(unique_images)
        )
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法访问该网页: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"提取图片失败: {str(e)}"
        )

@router.get("/tools/download-image")
async def download_image(url: str):
    """
    代理下载图片，解决跨域问题
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': url,
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        }
        
        # 减少超时时间，避免长时间等待
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # 获取内容类型
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # 获取文件扩展名
        ext = 'jpg'
        if 'png' in content_type:
            ext = 'png'
        elif 'gif' in content_type:
            ext = 'gif'
        elif 'webp' in content_type:
            ext = 'webp'
        elif 'svg' in content_type:
            ext = 'svg'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            ext = 'jpg'
        
        # 从URL中提取文件名
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        url_filename = parsed_url.path.split('/')[-1]
        if url_filename and '.' in url_filename:
            filename = url_filename
        else:
            filename = f"image.{ext}"
        
        # 返回图片流
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
            detail="下载超时，请稍后重试或使用右键另存为"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法下载图片: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"下载失败: {str(e)}"
        )
