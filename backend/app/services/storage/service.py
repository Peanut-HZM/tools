"""
StorageService — unified storage service with DB management
"""
import logging
import os
from typing import BinaryIO, Any
from datetime import datetime

from app.config.config import settings
from app.config.database import get_pooled_db_connection, release_db_connection
from .factory import create_provider
from .base import StorageProvider

logger = logging.getLogger(__name__)


class StorageService:
    """统一文件存储服务（存储操作 + DB 记录管理）"""

    def __init__(self):
        self._provider: StorageProvider = create_provider()
        self._init_db()

    @property
    def provider(self) -> StorageProvider:
        return self._provider

    def _init_db(self):
        """初始化数据库表"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS oss_files (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        file_path VARCHAR(500) NOT NULL UNIQUE,
                        url VARCHAR(500) NOT NULL,
                        file_type VARCHAR(50),
                        size BIGINT,
                        uploaded_by VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                release_db_connection(conn)

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        uploaded_by: str = "system",
        metadata: dict[str, str] | None = None,
    ) -> str | None:
        """上传文件 + 保存 DB 记录，metadata 透传给 provider"""
        try:
            url = self._provider.upload_file(
                object_name, data, size, content_type, metadata=metadata
            )
            self._save_file_record(
                filename=os.path.basename(object_name),
                file_path=object_name,
                url=url,
                file_type=content_type,
                size=size,
                uploaded_by=uploaded_by,
            )
            return url
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    def _save_file_record(
        self,
        filename: str,
        file_path: str,
        url: str,
        file_type: str,
        size: int,
        uploaded_by: str,
    ):
        """保存文件记录到数据库"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO oss_files (filename, file_path, url, file_type, size, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_path) DO UPDATE SET
                        url = EXCLUDED.url,
                        file_type = EXCLUDED.file_type,
                        size = EXCLUDED.size,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (filename, file_path, url, file_type, size, uploaded_by),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving file record: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                release_db_connection(conn)

    def delete_file(self, object_name: str) -> bool:
        """删除文件 + 删除 DB 记录"""
        try:
            self._provider.delete_file(object_name)
            conn = None
            try:
                conn = get_pooled_db_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM oss_files WHERE file_path = %s", (object_name,)
                    )
                conn.commit()
            except Exception as e:
                logger.error(f"Error deleting file record from DB: {e}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    release_db_connection(conn)
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def list_files_db(
        self, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """从数据库列出文件"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM oss_files
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()
                files = []
                for row in rows:
                    files.append(
                        {
                            "id": row["id"],
                            "name": row["filename"],
                            "path": row["file_path"],
                            "url": row["url"],
                            "type": row["file_type"],
                            "size": row["size"],
                            "uploaded_by": row["uploaded_by"],
                            "created_at": (
                                row["created_at"].isoformat()
                                if row["created_at"]
                                else None
                            ),
                        }
                    )
                return files
        except Exception as e:
            logger.error(f"Error listing files from DB: {e}")
            return []
        finally:
            if conn:
                release_db_connection(conn)

    def list_files(
        self, prefix: str = "", max_keys: int = 100
    ) -> list[dict]:
        """从存储后端列出文件"""
        return self._provider.list_files(prefix, max_keys)

    def get_object(self, object_name: str) -> BinaryIO:
        """获取文件内容流"""
        return self._provider.get_object(object_name)

    def download_file(self, object_name_or_url: str) -> bytes:
        """获取文件完整内容（支持 object_key 或完整 URL）"""
        return self._provider.download_file(object_name_or_url)

    def sign_url(
        self, method: str, object_name: str, expires: int = 3600
    ) -> str:
        """生成签名访问 URL"""
        return self._provider.sign_url(method, object_name, expires)

    def head_object(self, object_name: str) -> dict | None:
        """获取文件元数据"""
        return self._provider.head_object(object_name)

    def is_available(self) -> bool:
        """检查存储服务是否可用"""
        return self._provider is not None

    def update_file_url(self, object_name: str, new_url: str):
        """更新数据库中文件的 URL（用于迁移脚本）"""
        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE oss_files SET url = %s WHERE file_path = %s",
                    (new_url, object_name),
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating file URL: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                release_db_connection(conn)
