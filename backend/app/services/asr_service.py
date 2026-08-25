import re
import time
import logging
import httpx
import os
import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import uuid

from sqlalchemy import text, Column, String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

from app.models.asr_models import (
    ASRResponse, ASRHistoryRecord, ASRQuotaInfo,
    ASRExportFormat, ExportASRResponse,
    SpeakerDiarizationRequest, SpeakerDiarizationResponse, SpeakerSegment
)
from app.config.asr_config import asr_settings
from app.core.exceptions import QuotaExceeded
from app.models.base import SessionLocal
from app.services.llm_quota_service import LLMQuotaService

logger = logging.getLogger(__name__)

Base = declarative_base()


class ASRHistory(Base):
    """ASR 历史记录表"""
    __tablename__ = 'asr_history'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    original_audio_url = Column(String, nullable=True)
    recognized_text = Column(Text, nullable=False)
    language = Column(String, nullable=False, default='zh')
    duration_seconds = Column(Float, nullable=False)
    processing_time_ms = Column(Float, nullable=False)
    file_size = Column(Integer, nullable=True)
    audio_format = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # 用于标记软删除（兼容旧表结构）
    is_deleted = Column(Boolean, default=False, nullable=True)
    deleted = Column(Boolean, default=False, nullable=True)


class ASRQuota(Base):
    """ASR 配额表"""
    __tablename__ = 'asr_quota'

    user_id = Column(String, primary_key=True)
    daily_limit = Column(Integer, nullable=False, default=100)  # 每日 100 分钟
    daily_used = Column(Float, nullable=False, default=0.0)
    daily_reset_date = Column(DateTime, nullable=False)
    monthly_limit = Column(Integer, nullable=False, default=3000)  # 每月 3000 分钟
    monthly_used = Column(Float, nullable=False, default=0.0)
    monthly_reset_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class ASRService:
    def __init__(self, db_session=None):
        self.api_url = asr_settings.ASR_API_URL
        self.db_session = db_session
        self._ensure_asr_history_table()
        self._ensure_asr_quota_table()

    def _get_db(self):
        """获取数据库连接"""
        if self.db_session:
            return self.db_session
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        return Session(next(get_db()))

    def _ensure_asr_history_table(self):
        """确保 asr_history 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            # 检查表是否存在
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'asr_history'
            """))
            if not result.first():
                # 创建表
                db.execute(text("""
                    CREATE TABLE asr_history (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        original_audio_url VARCHAR,
                        recognized_text TEXT NOT NULL,
                        language VARCHAR NOT NULL DEFAULT 'zh',
                        duration_seconds FLOAT NOT NULL,
                        processing_time_ms FLOAT NOT NULL,
                        file_size INTEGER,
                        audio_format VARCHAR,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        is_deleted BOOLEAN DEFAULT FALSE
                    )
                """))
                db.execute(text("CREATE INDEX idx_asr_history_user_id ON asr_history(user_id)"))
                db.execute(text("CREATE INDEX idx_asr_history_created_at ON asr_history(created_at)"))
                db.commit()
                logger.info("Created asr_history table")
        except Exception as e:
            logger.error(f"Error ensuring asr_history table: {e}")
            if 'db' in locals():
                db.rollback()

    def _ensure_asr_quota_table(self):
        """确保 asr_quota 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'asr_quota'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE asr_quota (
                        user_id VARCHAR PRIMARY KEY,
                        daily_limit INTEGER NOT NULL DEFAULT 100,
                        daily_used FLOAT NOT NULL DEFAULT 0,
                        daily_reset_date TIMESTAMP NOT NULL,
                        monthly_limit INTEGER NOT NULL DEFAULT 3000,
                        monthly_used FLOAT NOT NULL DEFAULT 0,
                        monthly_reset_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """))
                # 初始化默认配额记录
                db.execute(text("""
                    INSERT INTO asr_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date,
                                          created_at, updated_at)
                    SELECT 'default', 100, 0, NOW(), 3000, 0, NOW() + INTERVAL '1 month', NOW(), NOW()
                    WHERE NOT EXISTS (SELECT 1 FROM asr_quota WHERE user_id = 'default')
                """))
                db.commit()
                logger.info("Created asr_quota table")
        except Exception as e:
            logger.error(f"Error ensuring asr_quota table: {e}")
            if 'db' in locals():
                db.rollback()

    def _clean_text(self, text: str) -> str:
        """
        清理 ASR 输出的文本，移除特殊标签
        """
        if not text:
            return ""
        # 移除 <|...|> 格式的标签
        cleaned = re.sub(r'<\|.*?\|>', '', text)
        # 移除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _save_history(self, user_id: str, audio_file_path: str, response: ASRResponse, language: str) -> str:
        """保存 ASR 历史记录"""
        try:
            db = self._get_db()
            record_id = str(uuid.uuid4())

            # 获取文件大小和格式
            file_size = os.path.getsize(audio_file_path) if os.path.exists(audio_file_path) else None
            audio_format = os.path.splitext(audio_file_path)[1].lstrip('.').lower() if audio_file_path else None

            record = {
                'id': record_id,
                'user_id': user_id,
                'original_audio_url': audio_file_path,
                'recognized_text': response.text,
                'language': language,
                'duration_seconds': response.duration,
                'processing_time_ms': response.processing_time * 1000,
                'file_size': file_size,
                'audio_format': audio_format,
                'created_at': datetime.now()
            }

            db.execute(text("""
                INSERT INTO asr_history (id, user_id, original_audio_url, recognized_text, language,
                                        duration_seconds, processing_time_ms, file_size, audio_format, created_at)
                VALUES (:id, :user_id, :original_audio_url, :recognized_text, :language,
                       :duration_seconds, :processing_time_ms, :file_size, :audio_format, :created_at)
            """), record)

            db.commit()
            logger.info(f"Saved ASR history record {record_id} for user {user_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error saving ASR history: {e}")
            if 'db' in locals():
                db.rollback()
            return None

    def get_history(self, user_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[ASRHistoryRecord], int]:
        """获取用户 ASR 历史记录"""
        try:
            db = self._get_db()
            offset = (page - 1) * page_size

            # 获取总数
            total_result = db.execute(text("""
                SELECT COUNT(*) FROM asr_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
            """), {'user_id': user_id})
            total = total_result.scalar()

            # 获取分页数据
            result = db.execute(text("""
                SELECT id, user_id, original_audio_url, recognized_text, language,
                       duration_seconds, processing_time_ms, file_size, audio_format, created_at
                FROM asr_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
                ORDER BY created_at DESC
                LIMIT :page_size OFFSET :offset
            """), {'user_id': user_id, 'page_size': page_size, 'offset': offset})

            records = []
            for row in result:
                record = ASRHistoryRecord(
                    id=row.id,
                    user_id=row.user_id,
                    original_audio_url=row.original_audio_url,
                    recognized_text=row.recognized_text,
                    language=row.language,
                    duration_seconds=row.duration_seconds,
                    processing_time_ms=row.processing_time_ms,
                    file_size=row.file_size,
                    audio_format=row.audio_format,
                    created_at=row.created_at
                )
                records.append(record)

            return records, total
        except Exception as e:
            logger.error(f"Error getting ASR history: {e}")
            return [], 0

    def _check_quota(self, user_id: str) -> ASRQuotaInfo:
        """检查用户配额"""
        try:
            db = self._get_db()
            today = date.today()

            # 获取或创建配额记录
            result = db.execute(text("""
                SELECT user_id, daily_limit, daily_used, daily_reset_date,
                       monthly_limit, monthly_used, monthly_reset_date
                FROM asr_quota
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
                    INSERT INTO asr_quota (user_id, daily_limit, daily_used, daily_reset_date,
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

                return ASRQuotaInfo(
                    user_id=user_id,
                    daily_limit=100,
                    daily_used=0,
                    daily_remaining=100,
                    monthly_limit=3000,
                    monthly_used=0,
                    monthly_remaining=3000,
                    reset_date=daily_reset
                )

            # 检查是否需要重置每日配额
            daily_reset_date = result.daily_reset_date.date() if hasattr(result.daily_reset_date, 'date') else result.daily_reset_date
            if daily_reset_date < today:
                # 重置每日配额
                new_daily_reset = datetime.combine(today, datetime.min.time())
                db.execute(text("""
                    UPDATE asr_quota
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
                # 重置每月配额
                if now.month == 12:
                    new_monthly_reset = datetime(now.year + 1, 1, 1)
                else:
                    new_monthly_reset = datetime(now.year, now.month + 1, 1)
                db.execute(text("""
                    UPDATE asr_quota
                    SET monthly_used = 0, monthly_reset_date = :monthly_reset, updated_at = NOW()
                    WHERE user_id = :user_id
                """), {'monthly_reset': new_monthly_reset, 'user_id': user_id})
                db.commit()
                monthly_used = 0
            else:
                monthly_used = result.monthly_used

            # 返回配额信息
            return ASRQuotaInfo(
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
            logger.error(f"Error checking ASR quota: {e}")
            if 'db' in locals():
                db.rollback()
            # 返回默认配额
            return ASRQuotaInfo(
                user_id=user_id,
                daily_limit=100,
                daily_used=0,
                daily_remaining=100,
                monthly_limit=3000,
                monthly_used=0,
                monthly_remaining=3000,
                reset_date=datetime.now()
            )

    def _increment_quota_usage(self, user_id: str, duration_minutes: float):
        """增加用户配额使用量"""
        try:
            db = self._get_db()
            db.execute(text("""
                UPDATE asr_quota
                SET daily_used = daily_used + :duration,
                    monthly_used = monthly_used + :duration,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """), {'duration': duration_minutes, 'user_id': user_id})
            db.commit()
            logger.info(f"Incremented ASR quota usage for user {user_id}: {duration_minutes} minutes")
        except Exception as e:
            logger.error(f"Error incrementing ASR quota: {e}")
            if 'db' in locals():
                db.rollback()

    def _format_srt(self, sentences: List[Dict], audio_duration: float) -> str:
        """格式化为 SRT 字幕格式"""
        srt_lines = []
        for i, sentence in enumerate(sentences, 1):
            start = sentence.get('start_time', 0)
            end = sentence.get('end_time', start + 1)
            text = sentence.get('text', '')

            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

            srt_lines.append(f"{i}")
            srt_lines.append(f"{format_time(start)} --> {format_time(end)}")
            srt_lines.append(text)
            srt_lines.append("")

        return "\n".join(srt_lines)

    def _format_vtt(self, sentences: List[Dict], audio_duration: float) -> str:
        """格式化为 VTT 字幕格式"""
        vtt_lines = ["WEBVTT", ""]
        for sentence in sentences:
            start = sentence.get('start_time', 0)
            end = sentence.get('end_time', start + 1)
            text = sentence.get('text', '')

            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

            vtt_lines.append(f"{format_time(start)} --> {format_time(end)}")
            vtt_lines.append(text)
            vtt_lines.append("")

        return "\n".join(vtt_lines)

    def _format_lrc(self, sentences: List[Dict], audio_duration: float) -> str:
        """格式化为 LRC 歌词格式"""
        lrc_lines = []
        for sentence in sentences:
            start = sentence.get('start_time', 0)
            text = sentence.get('text', '')

            def format_time(seconds):
                minutes = int(seconds // 60)
                secs = seconds % 60
                return f"[{minutes:02d}:{secs:05.2f}]"

            lrc_lines.append(f"{format_time(start)}{text}")

        return "\n".join(lrc_lines)

    def export_ocr_result(self, user_id: str, history_id: str, export_format: ASRExportFormat) -> ExportASRResponse:
        """导出 ASR 识别结果"""
        try:
            db = self._get_db()

            # 获取历史记录
            result = db.execute(text("""
                SELECT recognized_text, language, duration_seconds
                FROM asr_history
                WHERE id = :history_id AND user_id = :user_id
                  AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
            """), {'history_id': history_id, 'user_id': user_id}).first()

            if not result:
                raise ValueError("历史记录不存在或无权访问")

            recognized_text = result.recognized_text
            language = result.language
            duration = result.duration_seconds

            # 根据格式导出
            if export_format == ASRExportFormat.TXT:
                content = recognized_text
                file_name = f"asr_result_{history_id[:8]}.txt"
            elif export_format == ASRExportFormat.JSON:
                content = json.dumps({
                    'text': recognized_text,
                    'language': language,
                    'duration': duration
                }, ensure_ascii=False, indent=2)
                file_name = f"asr_result_{history_id[:8]}.json"
            elif export_format in [ASRExportFormat.SRT, ASRExportFormat.VTT, ASRExportFormat.LRC]:
                # 对于字幕格式，需要解析 sentences
                # 这里简单处理，将完整文本按句分割
                sentences = []
                # 简单的句子分割
                import re
                parts = re.split(r'[。！？.!?\n]', recognized_text)
                time_per_sentence = duration / max(len(parts), 1)
                for i, part in enumerate(parts):
                    if part.strip():
                        sentences.append({
                            'start_time': i * time_per_sentence,
                            'end_time': (i + 1) * time_per_sentence,
                            'text': part.strip()
                        })

                if export_format == ASRExportFormat.SRT:
                    content = self._format_srt(sentences, duration)
                    file_name = f"asr_result_{history_id[:8]}.srt"
                elif export_format == ASRExportFormat.VTT:
                    content = self._format_vtt(sentences, duration)
                    file_name = f"asr_result_{history_id[:8]}.vtt"
                else:  # LRC
                    content = self._format_lrc(sentences, duration)
                    file_name = f"asr_result_{history_id[:8]}.lrc"
            else:
                raise ValueError(f"不支持的导出格式：{export_format}")

            file_size = len(content.encode('utf-8'))

            return ExportASRResponse(
                file_name=file_name,
                content=content,
                file_size=file_size
            )
        except Exception as e:
            logger.error(f"Error exporting ASR result: {e}")
            raise

    def batch_process(self, user_id: str, audio_files: List[str], language: str = "zh", auto_save: bool = True) -> Dict:
        """批量处理 ASR 识别"""
        results = []
        history_ids = []
        errors = []

        for i, audio_file in enumerate(audio_files):
            try:
                # 检查配额
                quota_info = self._check_quota(user_id)
                if quota_info.daily_remaining <= 0:
                    errors.append({'file': audio_file, 'error': '每日配额已用尽'})
                    continue
                if quota_info.monthly_remaining <= 0:
                    errors.append({'file': audio_file, 'error': '每月配额已用尽'})
                    continue

                # 调用 ASR 识别
                response = self.predict(audio_file)
                results.append(response)

                # 保存历史记录
                if auto_save:
                    history_id = self._save_history(user_id, audio_file, response, language)
                    if history_id:
                        history_ids.append(history_id)
                        # 更新配额使用量
                        duration_minutes = response.duration / 60
                        self._increment_quota_usage(user_id, duration_minutes)

            except Exception as e:
                logger.error(f"Batch ASR failed for file {audio_file}: {e}")
                errors.append({'file': audio_file, 'error': str(e)})

        return {
            'success_count': len(results),
            'failed_count': len(errors),
            'results': results,
            'history_ids': history_ids,
            'errors': errors
        }

    def _quota_session(self):
        """获取 quota 操作用的 SQLAlchemy Session；非注入场景下创建短生命周期 Session。"""
        if self.db_session is not None:
            return self.db_session, False
        return SessionLocal(), True

    def predict(self, audio_file_path: str, language: str = "zh", user_id: Optional[str] = None, save_history: bool = False) -> ASRResponse:
        """
        调用远程 ASR 服务进行语音识别
        :param audio_file_path: 音频文件路径
        :param language: 语言
        :param user_id: 用户 ID（用于配额管理）
        :param save_history: 是否保存历史记录
        """
        start_time = time.time()

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # ---- quota 预占（Task 10）：duration 在调用后才可知，先以 0 占位；成功后按实际 duration * 10 校正 ----
        quota_db = None
        quota_owns_session = False
        quota_svc = None
        res_id = None
        if user_id:
            quota_db, quota_owns_session = self._quota_session()
            quota_svc = LLMQuotaService(quota_db)
            try:
                res_id = quota_svc.check_and_reserve(
                    user_id=user_id, category="asr", planned_tokens=0,
                )
            except QuotaExceeded as e:
                if quota_owns_session:
                    quota_db.close()
                logger.warning("ASR quota 预占失败: user=%s err=%s", user_id, e)
                raise

        try:
            target_url = f"{self.api_url}/asr-http/recognition"
            logger.info(f"Calling ASR API: {target_url}")

            with open(audio_file_path, "rb") as f:
                files = {"audio": (os.path.basename(audio_file_path), f, "audio/wav")}

                with httpx.Client(timeout=120.0) as client:
                    response = client.post(target_url, files=files)

                    if response.status_code != 200:
                        raise RuntimeError(f"ASR API error: {response.status_code} - {response.text}")

                    result = response.json()

                    code = result.get("code")
                    if code != 0:
                         message = result.get("message") or result.get("msg") or "ASR 识别失败"
                         raise RuntimeError(f"ASR failed with code {code}: {message}")

                    text = result.get("text", "")
                    text = self._clean_text(text)

                    # 获取音频时长（如果 API 返回）
                    duration = result.get("duration", 0.0)
                    if not duration:
                        # 尝试从文件中获取时长（需要安装 mutagen 库）
                        try:
                            from mutagen import File as MutagenFile
                            audio = MutagenFile(audio_file_path)
                            if audio:
                                duration = audio.info.length
                        except Exception:
                            duration = 0.0

            processing_time = time.time() - start_time

            asr_response = ASRResponse(
                text=text,
                duration=duration,
                processing_time=processing_time
            )

            # ---- quota 校正（Task 10）：用实际 duration * 10 写 usage_log ----
            if quota_svc is not None and res_id is not None:
                actual_tokens = max(1, int(duration * 10))
                quota_svc.record_usage(
                    user_id=user_id, category="asr",
                    actual_tokens=actual_tokens, reservation_id=res_id,
                    model_used="asr-http",
                )

            # 保存历史记录
            if save_history and user_id:
                self._save_history(user_id, audio_file_path, asr_response, language)
                # 更新配额
                duration_minutes = duration / 60
                self._increment_quota_usage(user_id, duration_minutes)

            return asr_response

        except Exception as e:
            # ---- quota 回滚（Task 10）：ASR 调用失败时回滚预留 ----
            if quota_svc is not None and res_id is not None:
                try:
                    quota_svc.rollback(res_id)
                except Exception:
                    pass
            logger.error(f"ASR prediction failed: {e}")
            raise
        finally:
            if quota_owns_session and quota_db is not None:
                quota_db.close()

    def speaker_diarization(self, user_id: str, audio_file: str, num_speakers: Optional[int] = None) -> SpeakerDiarizationResponse:
        """
        说话人分离功能
        :param user_id: 用户 ID
        :param audio_file: 音频文件路径
        :param num_speakers: 说话人数量，为空则自动检测
        """
        start_time = time.time()

        # 目前实现简化版本，调用 ASR 后按时间分割模拟说话人分离
        # 实际生产环境需要调用支持说话人分离的 ASR 服务

        try:
            # 调用 ASR 获取带时间戳的结果
            response = self.predict(audio_file, user_id=user_id, save_history=True)

            # 简单实现：按句子分割，轮流分配给不同说话人
            import re
            sentences = re.split(r'[。！？.!?\n]', response.text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # 自动检测说话人数量（默认 2 人）
            if num_speakers is None:
                num_speakers = 2 if len(sentences) > 2 else 1

            # 分配说话人
            segments = []
            time_per_sentence = response.duration / max(len(sentences), 1)

            for i, sentence in enumerate(sentences):
                speaker_num = (i % num_speakers) + 1
                segments.append(SpeakerSegment(
                    speaker=f"说话人{speaker_num}",
                    start_time=i * time_per_sentence,
                    end_time=(i + 1) * time_per_sentence,
                    text=sentence
                ))

            speakers = list(set([seg.speaker for seg in segments]))

            processing_time = time.time() - start_time

            return SpeakerDiarizationResponse(
                speakers=speakers,
                segments=segments,
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Speaker diarization failed: {e}")
            raise


asr_service = ASRService()
