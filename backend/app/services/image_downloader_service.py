import os
import logging
import io
import uuid
import time
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sqlalchemy import text, Column, String, Integer, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

from app.models.image_downloader_models import (
    ImageInfo, DownloadedImage, ImageHistoryRecord, ImageQuotaInfo
)
from app.services.oss_service import oss_service

logger = logging.getLogger(__name__)

Base = declarative_base()


class ImageHistory(Base):
    """图片下载历史记录表"""
    __tablename__ = 'image_history'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    original_url = Column(String, nullable=False)
    oss_url = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    content_type = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # 用于标记软删除（兼容旧表结构）
    is_deleted = Column(Boolean, default=False, nullable=True)
    deleted = Column(Boolean, default=False, nullable=True)


class ImageQuota(Base):
    """图片下载配额表"""
    __tablename__ = 'image_quota'

    user_id = Column(String, primary_key=True)
    daily_limit = Column(Integer, nullable=False, default=100)  # 每日 100 张
    daily_used = Column(Integer, nullable=False, default=0)
    daily_reset_date = Column(DateTime, nullable=False)
    monthly_limit = Column(Integer, nullable=False, default=3000)  # 每月 3000 张
    monthly_used = Column(Integer, nullable=False, default=0)
    monthly_reset_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class ImageDownloaderService:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._ensure_image_history_table()
        self._ensure_image_quota_table()

    def _get_db(self):
        """获取数据库连接"""
        if self.db_session:
            return self.db_session
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        return Session(next(get_db()))

    def _ensure_image_history_table(self):
        """确保 image_history 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'image_history'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE image_history (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        original_url VARCHAR NOT NULL,
                        oss_url VARCHAR NOT NULL,
                        filename VARCHAR NOT NULL,
                        file_size INTEGER NOT NULL,
                        width INTEGER,
                        height INTEGER,
                        content_type VARCHAR NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        is_deleted BOOLEAN DEFAULT FALSE
                    )
                """))
                db.execute(text("CREATE INDEX idx_image_history_user_id ON image_history(user_id)"))
                db.execute(text("CREATE INDEX idx_image_history_created_at ON image_history(created_at)"))
                db.commit()
                logger.info("Created image_history table")
        except Exception as e:
            logger.error(f"Error ensuring image_history table: {e}")
            if 'db' in locals():
                db.rollback()

    def _ensure_image_quota_table(self):
        """确保 image_quota 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'image_quota'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE image_quota (
                        user_id VARCHAR PRIMARY KEY,
                        daily_limit INTEGER NOT NULL DEFAULT 100,
                        daily_used INTEGER NOT NULL DEFAULT 0,
                        daily_reset_date TIMESTAMP NOT NULL,
                        monthly_limit INTEGER NOT NULL DEFAULT 3000,
                        monthly_used INTEGER NOT NULL DEFAULT 0,
                        monthly_reset_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """))
                # 初始化默认配额记录
                db.execute(text("""
                    INSERT INTO image_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date,
                                          created_at, updated_at)
                    SELECT 'default', 100, 0, NOW(), 3000, 0, NOW() + INTERVAL '1 month', NOW(), NOW()
                    WHERE NOT EXISTS (SELECT 1 FROM image_quota WHERE user_id = 'default')
                """))
                db.commit()
                logger.info("Created image_quota table")
        except Exception as e:
            logger.error(f"Error ensuring image_quota table: {e}")
            if 'db' in locals():
                db.rollback()

    def extract_images(self, url: str) -> List[ImageInfo]:
        """从网页提取图片"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            images = []
            img_tags = soup.find_all('img')

            for index, img in enumerate(img_tags):
                img_url = img.get('src') or img.get('data-src') or img.get('data-original')

                if not img_url:
                    continue

                absolute_url = urljoin(url, img_url)

                parsed = urlparse(absolute_url)
                if not parsed.scheme or not parsed.netloc:
                    continue

                if any(x in absolute_url.lower() for x in ['1x1', 'pixel', 'tracking']):
                    continue

                alt = img.get('alt', '')

                # 尝试获取尺寸
                width = img.get('width')
                height = img.get('height')
                try:
                    width = int(width) if width else None
                    height = int(height) if height else None
                except (ValueError, TypeError):
                    width = height = None

                images.append(ImageInfo(
                    url=absolute_url,
                    alt=alt,
                    index=index,
                    width=width,
                    height=height
                ))

            # 去重
            seen_urls = set()
            unique_images = []
            for img in images:
                if img.url not in seen_urls:
                    seen_urls.add(img.url)
                    unique_images.append(img)

            return unique_images

        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            raise

    def _save_history(self, user_id: str, original_url: str, oss_url: str,
                      filename: str, file_size: int, content_type: str,
                      width: Optional[int] = None, height: Optional[int] = None) -> str:
        """保存下载历史记录"""
        try:
            db = self._get_db()
            record_id = str(uuid.uuid4())

            record = {
                'id': record_id,
                'user_id': user_id,
                'original_url': original_url,
                'oss_url': oss_url,
                'filename': filename,
                'file_size': file_size,
                'width': width,
                'height': height,
                'content_type': content_type,
                'created_at': datetime.now()
            }

            db.execute(text("""
                INSERT INTO image_history (id, user_id, original_url, oss_url, filename,
                                          file_size, width, height, content_type, created_at)
                VALUES (:id, :user_id, :original_url, :oss_url, :filename,
                       :file_size, :width, :height, :content_type, :created_at)
            """), record)

            db.commit()
            logger.info(f"Saved image history record {record_id} for user {user_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error saving image history: {e}")
            if 'db' in locals():
                db.rollback()
            return None

    def get_history(self, user_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[ImageHistoryRecord], int]:
        """获取用户图片下载历史记录"""
        try:
            db = self._get_db()
            offset = (page - 1) * page_size

            # 获取总数
            total_result = db.execute(text("""
                SELECT COUNT(*) FROM image_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
            """), {'user_id': user_id})
            total = total_result.scalar()

            # 获取分页数据
            result = db.execute(text("""
                SELECT id, user_id, original_url, oss_url, filename, file_size,
                       width, height, content_type, created_at
                FROM image_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
                ORDER BY created_at DESC
                LIMIT :page_size OFFSET :offset
            """), {'user_id': user_id, 'page_size': page_size, 'offset': offset})

            records = []
            for row in result:
                record = ImageHistoryRecord(
                    id=row.id,
                    user_id=row.user_id,
                    original_url=row.original_url,
                    oss_url=row.oss_url,
                    filename=row.filename,
                    file_size=row.file_size,
                    width=row.width,
                    height=row.height,
                    content_type=row.content_type,
                    created_at=row.created_at
                )
                records.append(record)

            return records, total
        except Exception as e:
            logger.error(f"Error getting image history: {e}")
            return [], 0

    def _check_quota(self, user_id: str) -> ImageQuotaInfo:
        """检查用户配额"""
        try:
            db = self._get_db()
            today = date.today()

            result = db.execute(text("""
                SELECT user_id, daily_limit, daily_used, daily_reset_date,
                       monthly_limit, monthly_used, monthly_reset_date
                FROM image_quota
                WHERE user_id = :user_id
            """), {'user_id': user_id}).first()

            if not result:
                now = datetime.now()
                daily_reset = datetime.combine(today, datetime.min.time())
                monthly_reset = datetime(now.year, now.month, 1)
                if now.month == 12:
                    monthly_reset = datetime(now.year + 1, 1, 1)
                else:
                    monthly_reset = datetime(now.year, now.month + 1, 1)

                db.execute(text("""
                    INSERT INTO image_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date)
                    VALUES (:user_id, :daily_limit, 0, :daily_reset,
                           :monthly_limit, 0, :monthly_reset)
                """), {
                    'user_id': user_id,
                    'daily_limit': 100,
                    'daily_reset': daily_reset,
                    'monthly_limit': 3000,
                    'monthly_reset': monthly_reset
                })
                db.commit()

                return ImageQuotaInfo(
                    user_id=user_id,
                    daily_limit=100,
                    daily_used=0,
                    daily_remaining=100,
                    monthly_limit=3000,
                    monthly_used=0,
                    monthly_remaining=3000,
                    reset_date=daily_reset
                )

            daily_reset_date = result.daily_reset_date.date() if hasattr(result.daily_reset_date, 'date') else result.daily_reset_date
            if daily_reset_date < today:
                new_daily_reset = datetime.combine(today, datetime.min.time())
                db.execute(text("""
                    UPDATE image_quota
                    SET daily_used = 0, daily_reset_date = :daily_reset, updated_at = NOW()
                    WHERE user_id = :user_id
                """), {'daily_reset': new_daily_reset, 'user_id': user_id})
                db.commit()
                daily_used = 0
                daily_reset_date = new_daily_reset.date()
            else:
                daily_used = result.daily_used

            now = datetime.now()
            monthly_reset_date = result.monthly_reset_date.date() if hasattr(result.monthly_reset_date, 'date') else result.monthly_reset_date
            first_of_month = date(now.year, now.month, 1)
            if monthly_reset_date < first_of_month:
                if now.month == 12:
                    new_monthly_reset = datetime(now.year + 1, 1, 1)
                else:
                    new_monthly_reset = datetime(now.year, now.month + 1, 1)
                db.execute(text("""
                    UPDATE image_quota
                    SET monthly_used = 0, monthly_reset_date = :monthly_reset, updated_at = NOW()
                    WHERE user_id = :user_id
                """), {'monthly_reset': new_monthly_reset, 'user_id': user_id})
                db.commit()
                monthly_used = 0
            else:
                monthly_used = result.monthly_used

            return ImageQuotaInfo(
                user_id=user_id,
                daily_limit=result.daily_limit,
                daily_used=daily_used,
                daily_remaining=result.daily_limit - daily_used,
                monthly_limit=result.monthly_limit,
                monthly_used=monthly_used,
                monthly_remaining=result.monthly_limit - monthly_used,
                reset_date=datetime.combine(daily_reset_date, datetime.min.time()) if isinstance(daily_reset_date, date) else daily_reset_date
            )
        except Exception as e:
            logger.error(f"Error checking image quota: {e}")
            if 'db' in locals():
                db.rollback()
            return ImageQuotaInfo(
                user_id=user_id,
                daily_limit=100,
                daily_used=0,
                daily_remaining=100,
                monthly_limit=3000,
                monthly_used=0,
                monthly_remaining=3000,
                reset_date=datetime.now()
            )

    def _increment_quota_usage(self, user_id: str, count: int = 1):
        """增加用户配额使用量"""
        try:
            db = self._get_db()
            db.execute(text("""
                UPDATE image_quota
                SET daily_used = daily_used + :count,
                    monthly_used = monthly_used + :count,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """), {'count': count, 'user_id': user_id})
            db.commit()
            logger.info(f"Incremented image quota usage for user {user_id}: {count}")
        except Exception as e:
            logger.error(f"Error incrementing image quota: {e}")
            if 'db' in locals():
                db.rollback()

    def download_image(self, url: str, user_id: str, save_history: bool = True) -> DownloadedImage:
        """下载单张图片"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get('content-type', 'image/jpeg')

            parsed_url = urlparse(url)
            original_filename = os.path.basename(parsed_url.path)
            if not original_filename:
                original_filename = "image.jpg"

            file_extension = os.path.splitext(original_filename)[1]
            if not file_extension:
                if 'png' in content_type:
                    file_extension = '.png'
                elif 'gif' in content_type:
                    file_extension = '.gif'
                elif 'webp' in content_type:
                    file_extension = '.webp'
                else:
                    file_extension = '.jpg'

            unique_filename = f"{uuid.uuid4()}{file_extension}"
            object_name = f"users/{user_id}/images/{unique_filename}"

            image_data = response.content
            size = len(image_data)
            file_obj = io.BytesIO(image_data)

            oss_url = oss_service.upload_file(
                object_name=object_name,
                data=file_obj,
                size=size,
                content_type=content_type,
                uploaded_by=user_id
            )

            if not oss_url:
                raise Exception("Failed to upload image to OSS")

            # 保存图片历史
            if save_history and user_id:
                self._save_history(
                    user_id=user_id,
                    original_url=url,
                    oss_url=oss_url,
                    filename=unique_filename,
                    file_size=size,
                    content_type=content_type
                )
                self._increment_quota_usage(user_id, 1)

            return DownloadedImage(
                url=url,
                oss_url=oss_url,
                filename=unique_filename,
                size=size
            )

        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            raise

    def batch_download(self, user_id: str, image_urls: List[str], save_history: bool = True) -> Dict[str, Any]:
        """批量下载图片"""
        results = []
        errors = []

        for url in image_urls:
            try:
                # 检查配额
                quota_info = self._check_quota(user_id)
                if quota_info.daily_remaining <= 0:
                    errors.append({'url': url, 'error': '每日配额已用尽'})
                    continue
                if quota_info.monthly_remaining <= 0:
                    errors.append({'url': url, 'error': '每月配额已用尽'})
                    continue

                result = self.download_image(url, user_id, save_history)
                results.append(result)

            except Exception as e:
                logger.error(f"Batch download failed for {url}: {e}")
                errors.append({'url': url, 'error': str(e)})

        return {
            'success_count': len(results),
            'failed_count': len(errors),
            'images': results,
            'errors': errors
        }


image_downloader_service = ImageDownloaderService()
