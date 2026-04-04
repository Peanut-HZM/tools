import os
import shutil
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from fastapi import UploadFile
from markitdown import MarkItDown
import uuid
import io
import time
from datetime import datetime, date
from sqlalchemy import text, Column, String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

from app.models.converter_models import (
    ConvertResponse, ConverterHistoryRecord, ConverterQuotaInfo
)
from app.services.oss_service import oss_service

logger = logging.getLogger(__name__)

Base = declarative_base()


class ConverterHistory(Base):
    """文档转换历史记录表"""
    __tablename__ = 'converter_history'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    original_file_name = Column(String, nullable=False)
    original_file_url = Column(String, nullable=True)
    markdown_file_url = Column(String, nullable=True)
    file_size = Column(Integer, nullable=False)
    output_size = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    word_count = Column(Integer, nullable=False)
    processing_time_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # 用于标记软删除（兼容旧表结构）
    is_deleted = Column(Boolean, default=False, nullable=True)
    deleted = Column(Boolean, default=False, nullable=True)


class ConverterQuota(Base):
    """文档转换配额表"""
    __tablename__ = 'converter_quota'

    user_id = Column(String, primary_key=True)
    daily_limit = Column(Integer, nullable=False, default=50)  # 每日 50 次
    daily_used = Column(Integer, nullable=False, default=0)
    daily_reset_date = Column(DateTime, nullable=False)
    monthly_limit = Column(Integer, nullable=False, default=1500)  # 每月 1500 次
    monthly_used = Column(Integer, nullable=False, default=0)
    monthly_reset_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class ConverterService:
    def __init__(self, temp_dir: str = "temp", db_session=None):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.md = MarkItDown()
        self.db_session = db_session
        self._ensure_converter_history_table()
        self._ensure_converter_quota_table()

    def _get_db(self):
        """获取数据库连接"""
        if self.db_session:
            return self.db_session
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        return Session(next(get_db()))

    def _ensure_converter_history_table(self):
        """确保 converter_history 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'converter_history'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE converter_history (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        original_file_name VARCHAR NOT NULL,
                        original_file_url VARCHAR,
                        markdown_file_url VARCHAR,
                        file_size INTEGER NOT NULL,
                        output_size INTEGER NOT NULL,
                        content_type VARCHAR NOT NULL,
                        word_count INTEGER NOT NULL,
                        processing_time_ms FLOAT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        is_deleted BOOLEAN DEFAULT FALSE
                    )
                """))
                db.execute(text("CREATE INDEX idx_converter_history_user_id ON converter_history(user_id)"))
                db.execute(text("CREATE INDEX idx_converter_history_created_at ON converter_history(created_at)"))
                db.commit()
                logger.info("Created converter_history table")
        except Exception as e:
            logger.error(f"Error ensuring converter_history table: {e}")
            if 'db' in locals():
                db.rollback()

    def _ensure_converter_quota_table(self):
        """确保 converter_quota 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'converter_quota'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE converter_quota (
                        user_id VARCHAR PRIMARY KEY,
                        daily_limit INTEGER NOT NULL DEFAULT 50,
                        daily_used INTEGER NOT NULL DEFAULT 0,
                        daily_reset_date TIMESTAMP NOT NULL,
                        monthly_limit INTEGER NOT NULL DEFAULT 1500,
                        monthly_used INTEGER NOT NULL DEFAULT 0,
                        monthly_reset_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """))
                # 初始化默认配额记录
                db.execute(text("""
                    INSERT INTO converter_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date,
                                          created_at, updated_at)
                    SELECT 'default', 50, 0, NOW(), 1500, 0, NOW() + INTERVAL '1 month', NOW(), NOW()
                    WHERE NOT EXISTS (SELECT 1 FROM converter_quota WHERE user_id = 'default')
                """))
                db.commit()
                logger.info("Created converter_quota table")
        except Exception as e:
            logger.error(f"Error ensuring converter_quota table: {e}")
            if 'db' in locals():
                db.rollback()

    def _save_history(self, user_id: str, file_name: str, original_file_url: str,
                      markdown_file_url: str, file_size: int, output_size: int,
                      content_type: str, word_count: int, processing_time_ms: float) -> str:
        """保存转换历史记录"""
        try:
            db = self._get_db()
            record_id = str(uuid.uuid4())

            record = {
                'id': record_id,
                'user_id': user_id,
                'original_file_name': file_name,
                'original_file_url': original_file_url,
                'markdown_file_url': markdown_file_url,
                'file_size': file_size,
                'output_size': output_size,
                'content_type': content_type,
                'word_count': word_count,
                'processing_time_ms': processing_time_ms,
                'created_at': datetime.now()
            }

            db.execute(text("""
                INSERT INTO converter_history (id, user_id, original_file_name, original_file_url,
                                               markdown_file_url, file_size, output_size, content_type,
                                               word_count, processing_time_ms, created_at)
                VALUES (:id, :user_id, :original_file_name, :original_file_url,
                       :markdown_file_url, :file_size, :output_size, :content_type,
                       :word_count, :processing_time_ms, :created_at)
            """), record)

            db.commit()
            logger.info(f"Saved converter history record {record_id} for user {user_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error saving converter history: {e}")
            if 'db' in locals():
                db.rollback()
            return None

    def get_history(self, user_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[ConverterHistoryRecord], int]:
        """获取用户转换历史记录"""
        try:
            db = self._get_db()
            offset = (page - 1) * page_size

            # 获取总数
            total_result = db.execute(text("""
                SELECT COUNT(*) FROM converter_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
            """), {'user_id': user_id})
            total = total_result.scalar()

            # 获取分页数据
            result = db.execute(text("""
                SELECT id, user_id, original_file_name, original_file_url, markdown_file_url,
                       file_size, output_size, content_type, word_count, processing_time_ms, created_at
                FROM converter_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
                ORDER BY created_at DESC
                LIMIT :page_size OFFSET :offset
            """), {'user_id': user_id, 'page_size': page_size, 'offset': offset})

            records = []
            for row in result:
                record = ConverterHistoryRecord(
                    id=row.id,
                    user_id=row.user_id,
                    original_file_name=row.original_file_name,
                    original_file_url=row.original_file_url,
                    markdown_file_url=row.markdown_file_url,
                    file_size=row.file_size,
                    output_size=row.output_size,
                    content_type=row.content_type,
                    word_count=row.word_count,
                    processing_time_ms=row.processing_time_ms,
                    created_at=row.created_at
                )
                records.append(record)

            return records, total
        except Exception as e:
            logger.error(f"Error getting converter history: {e}")
            return [], 0

    def _check_quota(self, user_id: str) -> ConverterQuotaInfo:
        """检查用户配额"""
        try:
            db = self._get_db()
            today = date.today()

            # 获取或创建配额记录
            result = db.execute(text("""
                SELECT user_id, daily_limit, daily_used, daily_reset_date,
                       monthly_limit, monthly_used, monthly_reset_date
                FROM converter_quota
                WHERE user_id = :user_id
            """), {'user_id': user_id}).first()

            if not result:
                # 创建新的配额记录
                now = datetime.now()
                daily_reset = datetime.combine(today, datetime.min.time())
                monthly_reset = datetime(now.year, now.month, 1)
                if now.month == 12:
                    monthly_reset = datetime(now.year + 1, 1, 1)
                else:
                    monthly_reset = datetime(now.year, now.month + 1, 1)

                db.execute(text("""
                    INSERT INTO converter_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date)
                    VALUES (:user_id, :daily_limit, 0, :daily_reset,
                           :monthly_limit, 0, :monthly_reset)
                """), {
                    'user_id': user_id,
                    'daily_limit': 50,
                    'daily_reset': daily_reset,
                    'monthly_limit': 1500,
                    'monthly_reset': monthly_reset
                })
                db.commit()

                return ConverterQuotaInfo(
                    user_id=user_id,
                    daily_limit=50,
                    daily_used=0,
                    daily_remaining=50,
                    monthly_limit=1500,
                    monthly_used=0,
                    monthly_remaining=1500,
                    reset_date=daily_reset
                )

            # 检查是否需要重置每日配额
            daily_reset_date = result.daily_reset_date.date() if hasattr(result.daily_reset_date, 'date') else result.daily_reset_date
            if daily_reset_date < today:
                new_daily_reset = datetime.combine(today, datetime.min.time())
                db.execute(text("""
                    UPDATE converter_quota
                    SET daily_used = 0, daily_reset_date = :daily_reset, updated_at = NOW()
                    WHERE user_id = :user_id
                """), {'daily_reset': new_daily_reset, 'user_id': user_id})
                db.commit()
                daily_used = 0
                daily_reset_date = new_daily_reset.date()
            else:
                daily_used = result.daily_used

            # 检查是否需要重置每月配额
            now = datetime.now()
            monthly_reset_date = result.monthly_reset_date.date() if hasattr(result.monthly_reset_date, 'date') else result.monthly_reset_date
            first_of_month = date(now.year, now.month, 1)
            if monthly_reset_date < first_of_month:
                if now.month == 12:
                    new_monthly_reset = datetime(now.year + 1, 1, 1)
                else:
                    new_monthly_reset = datetime(now.year, now.month + 1, 1)
                db.execute(text("""
                    UPDATE converter_quota
                    SET monthly_used = 0, monthly_reset_date = :monthly_reset, updated_at = NOW()
                    WHERE user_id = :user_id
                """), {'monthly_reset': new_monthly_reset, 'user_id': user_id})
                db.commit()
                monthly_used = 0
            else:
                monthly_used = result.monthly_used

            return ConverterQuotaInfo(
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
            logger.error(f"Error checking converter quota: {e}")
            if 'db' in locals():
                db.rollback()
            return ConverterQuotaInfo(
                user_id=user_id,
                daily_limit=50,
                daily_used=0,
                daily_remaining=50,
                monthly_limit=1500,
                monthly_used=0,
                monthly_remaining=1500,
                reset_date=datetime.now()
            )

    def _increment_quota_usage(self, user_id: str, count: int = 1):
        """增加用户配额使用量"""
        try:
            db = self._get_db()
            db.execute(text("""
                UPDATE converter_quota
                SET daily_used = daily_used + :count,
                    monthly_used = monthly_used + :count,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """), {'count': count, 'user_id': user_id})
            db.commit()
            logger.info(f"Incremented converter quota usage for user {user_id}: {count}")
        except Exception as e:
            logger.error(f"Error incrementing converter quota: {e}")
            if 'db' in locals():
                db.rollback()

    async def convert_file(self, file: UploadFile, user_id: str = "anonymous", save_history: bool = True) -> ConvertResponse:
        """
        Convert uploaded file to markdown using MarkItDown.
        Also upload both input and output to OSS.
        """
        start_time = time.time()
        temp_file_path = None

        try:
            # 1. Save uploaded file to temp directory
            suffix = os.path.splitext(file.filename)[1] if file.filename else '.bin'
            temp_file_path = self.temp_dir / f"{uuid.uuid4()}{suffix}"
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Get file size
            file_size = os.path.getsize(temp_file_path)
            content_type = file.content_type or "application/octet-stream"
            original_filename = file.filename or "unknown"

            # 2. Upload Input File to OSS
            ext = os.path.splitext(original_filename)[1]
            input_obj_name = f"users/{user_id}/converter/input/{uuid.uuid4()}{ext}"

            with open(temp_file_path, "rb") as f:
                file_data = f.read()

            oss_service.upload_file(
                object_name=input_obj_name,
                data=io.BytesIO(file_data),
                size=file_size,
                content_type=content_type,
                uploaded_by=user_id
            )

            # 3. Convert file
            result = self.md.convert(str(temp_file_path))

            markdown_content = ""
            if result and result.text_content:
                markdown_content = result.text_content

            output_size = len(markdown_content.encode('utf-8'))
            word_count = len(markdown_content)

            # 4. Upload Output Markdown to OSS
            markdown_file_url = None
            if markdown_content:
                output_obj_name = f"users/{user_id}/converter/output/{uuid.uuid4()}.md"
                md_bytes = markdown_content.encode('utf-8')

                oss_service.upload_file(
                    object_name=output_obj_name,
                    data=io.BytesIO(md_bytes),
                    size=len(md_bytes),
                    content_type="text/markdown",
                    uploaded_by=user_id
                )
                markdown_file_url = output_obj_name

            processing_time_ms = (time.time() - start_time) * 1000

            # 5. Save history
            history_id = None
            if save_history and user_id and user_id != "anonymous":
                history_id = self._save_history(
                    user_id=user_id,
                    file_name=original_filename,
                    original_file_url=input_obj_name,
                    markdown_file_url=markdown_file_url,
                    file_size=file_size,
                    output_size=output_size,
                    content_type=content_type,
                    word_count=word_count,
                    processing_time_ms=processing_time_ms
                )
                # Increment quota usage
                self._increment_quota_usage(user_id, 1)

            return ConvertResponse(
                content=markdown_content,
                file_name=original_filename,
                file_size=file_size,
                output_size=output_size
            )

        except Exception as e:
            logger.error(f"Error converting file {file.filename}: {str(e)}")
            raise Exception(f"Failed to convert file: {str(e)}")
        finally:
            # Clean up temp file
            if temp_file_path and temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file_path}: {str(e)}")

    async def batch_convert(self, user_id: str, files: List[UploadFile], auto_save: bool = True) -> Dict[str, Any]:
        """批量转换文档"""
        results = []
        history_ids = []
        errors = []

        for file in files:
            try:
                # Check quota
                quota_info = self._check_quota(user_id)
                if quota_info.daily_remaining <= 0:
                    errors.append({'file': file.filename, 'error': '每日配额已用尽'})
                    continue
                if quota_info.monthly_remaining <= 0:
                    errors.append({'file': file.filename, 'error': '每月配额已用尽'})
                    continue

                # Convert file
                result = await self.convert_file(file, user_id=user_id, save_history=auto_save)
                results.append(result)

            except Exception as e:
                logger.error(f"Batch convert failed for file {file.filename}: {e}")
                errors.append({'file': file.filename, 'error': str(e)})

        return {
            'success_count': len(results),
            'failed_count': len(errors),
            'results': results,
            'history_ids': history_ids,
            'errors': errors
        }

    def save_content(self, user_id: str, content: str, file_name: Optional[str] = None) -> Tuple[str, str, int]:
        """保存编辑后的内容到 OSS"""
        try:
            if not file_name:
                file_name = f"document_{uuid.uuid4()}.md"
            elif not file_name.endswith('.md'):
                file_name += '.md'

            obj_name = f"users/{user_id}/converter/edit/{uuid.uuid4()}_{file_name}"
            md_bytes = content.encode('utf-8')

            oss_service.upload_file(
                object_name=obj_name,
                data=io.BytesIO(md_bytes),
                size=len(md_bytes),
                content_type="text/markdown",
                uploaded_by=user_id
            )

            return file_name, obj_name, len(md_bytes)
        except Exception as e:
            logger.error(f"Error saving content: {e}")
            raise


converter_service = ConverterService()
