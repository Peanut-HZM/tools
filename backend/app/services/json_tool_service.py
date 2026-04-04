import json
import logging
import time
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text, Column, String, Integer, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

from app.models.json_tool_models import (
    JSONFormatResponse, JSONMinifyResponse, JSONValidateResponse,
    JSONCompareResponse, JSONDiffItem, JSONConvertResponse,
    JSONHistoryRecord, JSONQuotaInfo, JSONConvertFormat
)

logger = logging.getLogger(__name__)

Base = declarative_base()


class JSONHistory(Base):
    """JSON 操作历史记录表"""
    __tablename__ = 'json_history'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    operation_type = Column(String, nullable=False)
    input_size = Column(Integer, nullable=False)
    output_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # 用于标记软删除（兼容旧表结构）
    is_deleted = Column(Boolean, default=False, nullable=True)
    deleted = Column(Boolean, default=False, nullable=True)


class JSONQuota(Base):
    """JSON 操作配额表"""
    __tablename__ = 'json_quota'

    user_id = Column(String, primary_key=True)
    daily_limit = Column(Integer, nullable=False, default=200)  # 每日 200 次
    daily_used = Column(Integer, nullable=False, default=0)
    daily_reset_date = Column(DateTime, nullable=False)
    monthly_limit = Column(Integer, nullable=False, default=6000)  # 每月 6000 次
    monthly_used = Column(Integer, nullable=False, default=0)
    monthly_reset_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class JSONToolService:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._ensure_json_history_table()
        self._ensure_json_quota_table()

    def _get_db(self):
        """获取数据库连接"""
        if self.db_session:
            return self.db_session
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        return Session(next(get_db()))

    def _ensure_json_history_table(self):
        """确保 json_history 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'json_history'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE json_history (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        operation_type VARCHAR NOT NULL,
                        input_size INTEGER NOT NULL,
                        output_size INTEGER,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        is_deleted BOOLEAN DEFAULT FALSE
                    )
                """))
                db.execute(text("CREATE INDEX idx_json_history_user_id ON json_history(user_id)"))
                db.execute(text("CREATE INDEX idx_json_history_created_at ON json_history(created_at)"))
                db.commit()
                logger.info("Created json_history table")
        except Exception as e:
            logger.error(f"Error ensuring json_history table: {e}")
            if 'db' in locals():
                db.rollback()

    def _ensure_json_quota_table(self):
        """确保 json_quota 表存在"""
        if not self.db_session:
            return
        try:
            db = self._get_db()
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'json_quota'
            """))
            if not result.first():
                db.execute(text("""
                    CREATE TABLE json_quota (
                        user_id VARCHAR PRIMARY KEY,
                        daily_limit INTEGER NOT NULL DEFAULT 200,
                        daily_used INTEGER NOT NULL DEFAULT 0,
                        daily_reset_date TIMESTAMP NOT NULL,
                        monthly_limit INTEGER NOT NULL DEFAULT 6000,
                        monthly_used INTEGER NOT NULL DEFAULT 0,
                        monthly_reset_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """))
                # 初始化默认配额记录
                db.execute(text("""
                    INSERT INTO json_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date,
                                          created_at, updated_at)
                    SELECT 'default', 200, 0, NOW(), 6000, 0, NOW() + INTERVAL '1 month', NOW(), NOW()
                    WHERE NOT EXISTS (SELECT 1 FROM json_quota WHERE user_id = 'default')
                """))
                db.commit()
                logger.info("Created json_quota table")
        except Exception as e:
            logger.error(f"Error ensuring json_quota table: {e}")
            if 'db' in locals():
                db.rollback()

    def _save_history(self, user_id: str, operation_type: str, input_size: int, output_size: Optional[int] = None) -> str:
        """保存操作历史记录"""
        try:
            db = self._get_db()
            record_id = str(uuid.uuid4())

            record = {
                'id': record_id,
                'user_id': user_id,
                'operation_type': operation_type,
                'input_size': input_size,
                'output_size': output_size,
                'created_at': datetime.now()
            }

            db.execute(text("""
                INSERT INTO json_history (id, user_id, operation_type, input_size, output_size, created_at)
                VALUES (:id, :user_id, :operation_type, :input_size, :output_size, :created_at)
            """), record)

            db.commit()
            logger.info(f"Saved JSON history record {record_id} for user {user_id}")
            return record_id
        except Exception as e:
            logger.error(f"Error saving JSON history: {e}")
            if 'db' in locals():
                db.rollback()
            return None

    def get_history(self, user_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[JSONHistoryRecord], int]:
        """获取用户 JSON 操作历史记录"""
        try:
            db = self._get_db()
            offset = (page - 1) * page_size

            # 获取总数
            total_result = db.execute(text("""
                SELECT COUNT(*) FROM json_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
            """), {'user_id': user_id})
            total = total_result.scalar()

            # 获取分页数据
            result = db.execute(text("""
                SELECT id, user_id, operation_type, input_size, output_size, created_at
                FROM json_history
                WHERE user_id = :user_id AND (is_deleted IS NULL OR is_deleted = FALSE) AND (deleted IS NULL OR deleted = FALSE)
                ORDER BY created_at DESC
                LIMIT :page_size OFFSET :offset
            """), {'user_id': user_id, 'page_size': page_size, 'offset': offset})

            records = []
            for row in result:
                record = JSONHistoryRecord(
                    id=row.id,
                    user_id=row.user_id,
                    operation_type=row.operation_type,
                    input_size=row.input_size,
                    output_size=row.output_size,
                    created_at=row.created_at
                )
                records.append(record)

            return records, total
        except Exception as e:
            logger.error(f"Error getting JSON history: {e}")
            return [], 0

    def _check_quota(self, user_id: str) -> JSONQuotaInfo:
        """检查用户配额"""
        try:
            db = self._get_db()
            today = date.today()

            result = db.execute(text("""
                SELECT user_id, daily_limit, daily_used, daily_reset_date,
                       monthly_limit, monthly_used, monthly_reset_date
                FROM json_quota
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
                    INSERT INTO json_quota (user_id, daily_limit, daily_used, daily_reset_date,
                                          monthly_limit, monthly_used, monthly_reset_date)
                    VALUES (:user_id, :daily_limit, 0, :daily_reset,
                           :monthly_limit, 0, :monthly_reset)
                """), {
                    'user_id': user_id,
                    'daily_limit': 200,
                    'daily_reset': daily_reset,
                    'monthly_limit': 6000,
                    'monthly_reset': monthly_reset
                })
                db.commit()

                return JSONQuotaInfo(
                    user_id=user_id,
                    daily_limit=200,
                    daily_used=0,
                    daily_remaining=200,
                    monthly_limit=6000,
                    monthly_used=0,
                    monthly_remaining=6000,
                    reset_date=daily_reset
                )

            daily_reset_date = result.daily_reset_date.date() if hasattr(result.daily_reset_date, 'date') else result.daily_reset_date
            if daily_reset_date < today:
                new_daily_reset = datetime.combine(today, datetime.min.time())
                db.execute(text("""
                    UPDATE json_quota
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
                    UPDATE json_quota
                    SET monthly_used = 0, monthly_reset_date = :monthly_reset, updated_at = NOW()
                    WHERE user_id = :user_id
                """), {'monthly_reset': new_monthly_reset, 'user_id': user_id})
                db.commit()
                monthly_used = 0
            else:
                monthly_used = result.monthly_used

            return JSONQuotaInfo(
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
            logger.error(f"Error checking JSON quota: {e}")
            if 'db' in locals():
                db.rollback()
            return JSONQuotaInfo(
                user_id=user_id,
                daily_limit=200,
                daily_used=0,
                daily_remaining=200,
                monthly_limit=6000,
                monthly_used=0,
                monthly_remaining=6000,
                reset_date=datetime.now()
            )

    def _increment_quota_usage(self, user_id: str, count: int = 1):
        """增加用户配额使用量"""
        try:
            db = self._get_db()
            db.execute(text("""
                UPDATE json_quota
                SET daily_used = daily_used + :count,
                    monthly_used = monthly_used + :count,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """), {'count': count, 'user_id': user_id})
            db.commit()
            logger.info(f"Incremented JSON quota usage for user {user_id}: {count}")
        except Exception as e:
            logger.error(f"Error incrementing JSON quota: {e}")
            if 'db' in locals():
                db.rollback()

    def format_json(self, user_id: str, content: str, indent: int = 2, sort_keys: bool = False) -> JSONFormatResponse:
        """格式化 JSON"""
        try:
            original_size = len(content)
            parsed = json.loads(content)
            formatted = json.dumps(parsed, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
            formatted_size = len(formatted)

            # 保存历史
            self._save_history(user_id, 'format', original_size, formatted_size)
            self._increment_quota_usage(user_id, 1)

            return JSONFormatResponse(
                content=formatted,
                original_size=original_size,
                formatted_size=formatted_size
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的 JSON 格式：{str(e)}")
        except Exception as e:
            logger.error(f"Format JSON failed: {e}")
            raise

    def minify_json(self, user_id: str, content: str) -> JSONMinifyResponse:
        """压缩 JSON"""
        try:
            original_size = len(content)
            parsed = json.loads(content)
            minified = json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
            minified_size = len(minified)
            compression_ratio = round((1 - minified_size / original_size) * 100, 2) if original_size > 0 else 0

            # 保存历史
            self._save_history(user_id, 'minify', original_size, minified_size)
            self._increment_quota_usage(user_id, 1)

            return JSONMinifyResponse(
                content=minified,
                original_size=original_size,
                minified_size=minified_size,
                compression_ratio=compression_ratio
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的 JSON 格式：{str(e)}")
        except Exception as e:
            logger.error(f"Minify JSON failed: {e}")
            raise

    def validate_json(self, user_id: str, content: str) -> JSONValidateResponse:
        """校验 JSON"""
        try:
            json.loads(content)

            # 保存历史
            self._save_history(user_id, 'validate', len(content), None)
            self._increment_quota_usage(user_id, 1)

            return JSONValidateResponse(
                valid=True,
                error_message=None,
                error_line=None,
                error_column=None
            )
        except json.JSONDecodeError as e:
            # 尝试解析错误位置
            error_line = None
            error_column = None
            error_message = str(e)

            # 解析错误位置
            if hasattr(e, 'lineno') and hasattr(e, 'colno'):
                error_line = e.lineno
                error_column = e.colno

            return JSONValidateResponse(
                valid=False,
                error_message=error_message,
                error_line=error_line,
                error_column=error_column
            )

    def compare_json(self, user_id: str, json1: str, json2: str) -> JSONCompareResponse:
        """比较两个 JSON"""
        try:
            parsed1 = json.loads(json1)
            parsed2 = json.loads(json2)

            differences = []

            def compare_values(obj1, obj2, path=""):
                if type(obj1) != type(obj2):
                    differences.append(JSONDiffItem(
                        path=path,
                        type="changed",
                        old_value=obj1,
                        new_value=obj2
                    ))
                    return

                if isinstance(obj1, dict):
                    all_keys = set(obj1.keys()) | set(obj2.keys())
                    for key in all_keys:
                        new_path = f"{path}.{key}" if path else key
                        if key not in obj1:
                            differences.append(JSONDiffItem(
                                path=new_path,
                                type="added",
                                old_value=None,
                                new_value=obj2[key]
                            ))
                        elif key not in obj2:
                            differences.append(JSONDiffItem(
                                path=new_path,
                                type="removed",
                                old_value=obj1[key],
                                new_value=None
                            ))
                        else:
                            compare_values(obj1[key], obj2[key], new_path)
                elif isinstance(obj1, list):
                    max_len = max(len(obj1), len(obj2))
                    for i in range(max_len):
                        new_path = f"{path}[{i}]"
                        if i >= len(obj1):
                            differences.append(JSONDiffItem(
                                path=new_path,
                                type="added",
                                old_value=None,
                                new_value=obj2[i]
                            ))
                        elif i >= len(obj2):
                            differences.append(JSONDiffItem(
                                path=new_path,
                                type="removed",
                                old_value=obj1[i],
                                new_value=None
                            ))
                        else:
                            compare_values(obj1[i], obj2[i], new_path)
                else:
                    if obj1 != obj2:
                        differences.append(JSONDiffItem(
                            path=path,
                            type="changed",
                            old_value=obj1,
                            new_value=obj2
                        ))

            compare_values(parsed1, parsed2)

            # 保存历史
            self._save_history(user_id, 'compare', len(json1) + len(json2), len(differences))
            self._increment_quota_usage(user_id, 1)

            return JSONCompareResponse(
                are_equal=len(differences) == 0,
                differences=differences,
                diff_count=len(differences)
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的 JSON 格式：{str(e)}")
        except Exception as e:
            logger.error(f"Compare JSON failed: {e}")
            raise

    def convert_json(self, user_id: str, content: str, target_format: JSONConvertFormat) -> JSONConvertResponse:
        """转换 JSON 为其他格式"""
        try:
            parsed = json.loads(content)

            if target_format == JSONConvertFormat.XML:
                result = self._json_to_xml(parsed)
            elif target_format == JSONConvertFormat.YAML:
                import yaml
                result = yaml.dump(parsed, allow_unicode=True, default_flow_style=False)
            elif target_format == JSONConvertFormat.CSV:
                result = self._json_to_csv(parsed)
            elif target_format == JSONConvertFormat.TOML:
                import toml
                result = toml.dumps(parsed)
            else:
                raise ValueError(f"不支持的转换格式：{target_format}")

            # 保存历史
            self._save_history(user_id, f'convert_{target_format.value}', len(content), len(result))
            self._increment_quota_usage(user_id, 1)

            return JSONConvertResponse(
                content=result,
                format=target_format.value
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的 JSON 格式：{str(e)}")
        except ImportError as e:
            raise ValueError(f"缺少依赖库：{str(e)}")
        except Exception as e:
            logger.error(f"Convert JSON failed: {e}")
            raise

    def _json_to_xml(self, obj, root_name="root") -> str:
        """JSON 转 XML"""
        def to_xml_element(obj, name):
            if isinstance(obj, dict):
                attrs = ""
                children = ""
                for k, v in obj.items():
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        attrs += f' {k}="{self._xml_escape(str(v))}"'
                    else:
                        children += to_xml_element(v, k)
                return f"<{name}{attrs}>{children}</{name}>"
            elif isinstance(obj, list):
                return "".join(to_xml_element(item, name) for item in obj)
            else:
                return f"<{name}>{self._xml_escape(str(obj))}</{name}>"

        return f'<?xml version="1.0" encoding="UTF-8"?>\n{to_xml_element(obj, root_name)}'

    def _xml_escape(self, s: str) -> str:
        """XML 转义"""
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

    def _json_to_csv(self, obj) -> str:
        """JSON 转 CSV"""
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            headers = list(obj[0].keys())
            lines = [','.join(headers)]
            for item in obj:
                values = [str(item.get(h, '')).replace(',', ' ') for h in headers]
                lines.append(','.join(values))
            return '\n'.join(lines)
        elif isinstance(obj, dict):
            headers = list(obj.keys())
            values = [str(obj.get(h, '')).replace(',', ' ') for h in headers]
            return ','.join(headers) + '\n' + ','.join(values)
        else:
            raise ValueError("CSV 转换仅支持 JSON 对象数组或对象")


json_tool_service = JSONToolService()
