from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List
import io
import os
import uuid
from app.services.oss_service import oss_service
from app.middleware.auth_middleware import get_current_user_id

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
async def download_image(url: str, user_id: str = Depends(get_current_user_id)):
    """
    下载图片并上传到OSS，返回OSS URL
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # Generate filename
        parsed_url = urlparse(url)
        original_filename = os.path.basename(parsed_url.path)
        if not original_filename:
            original_filename = "image.jpg"
            
        file_extension = os.path.splitext(original_filename)[1]
        if not file_extension:
            # Guess extension from content-type
            if 'png' in content_type: file_extension = '.png'
            elif 'gif' in content_type: file_extension = '.gif'
            elif 'webp' in content_type: file_extension = '.webp'
            else: file_extension = '.jpg'
            
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        object_name = f"users/{user_id}/images/{unique_filename}"
        
        # Read content to memory (be careful with large files, but images are usually okay)
        image_data = response.content
        size = len(image_data)
        file_obj = io.BytesIO(image_data)
        
        # Upload to OSS
        oss_url = oss_service.upload_file(
            object_name=object_name,
            data=file_obj,
            size=size,
            content_type=content_type,
            uploaded_by=user_id
        )
        
        if not oss_url:
            raise HTTPException(status_code=500, detail="Failed to upload image to OSS")
            
        return {"url": oss_url, "filename": unique_filename}
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process failed: {str(e)}")
