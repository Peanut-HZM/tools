"""
Author: Claude Code
Created: 2026-04-26
Purpose: Backup file storage and metadata management service
"""

import os
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKUPS_DIR = PROJECT_ROOT / "backups"
METADATA_DB = PROJECT_ROOT / "backups.db"

# 确保备份目录存在
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class BackupRecord:
    """备份记录数据类"""

    def __init__(
        self,
        id: str,
        user_id: str,
        config_id: str,
        database_name: str,
        file_name: str,
        file_path: str,
        file_size: int,
        backup_mode: str,
        tables_count: int,
        tables_list: Optional[List[str]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        created_at: Optional[str] = None,
        downloaded_count: int = 0,
    ):
        self.id = id
        self.user_id = user_id
        self.config_id = config_id
        self.database_name = database_name
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size
        self.backup_mode = backup_mode
        self.tables_count = tables_count
        self.tables_list = tables_list or []
        self.status = status
        self.error_message = error_message
        self.created_at = created_at or datetime.now().isoformat()
        self.downloaded_count = downloaded_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "config_id": self.config_id,
            "database_name": self.database_name,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "backup_mode": self.backup_mode,
            "tables_count": self.tables_count,
            "tables_list": self.tables_list,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "downloaded_count": self.downloaded_count,
        }


class BackupStorage:
    """备份存储服务 — 文件存储 + SQLite 元数据管理"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if BackupStorage._initialized:
            return
        BackupStorage._initialized = True
        self._init_metadata_db()

    def _init_metadata_db(self):
        """初始化 SQLite 元数据数据库"""
        try:
            with sqlite3.connect(str(METADATA_DB)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backup_records (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        config_id TEXT NOT NULL,
                        database_name TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        backup_mode TEXT NOT NULL,
                        tables_count INTEGER NOT NULL,
                        tables_list TEXT,
                        status TEXT DEFAULT 'success',
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        downloaded_count INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_backup_user
                    ON backup_records(user_id, created_at DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_backup_config
                    ON backup_records(config_id, database_name)
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to init backup metadata DB: {e}")
            raise

    def _get_user_backup_dir(self, user_id: str) -> Path:
        """获取用户备份目录"""
        user_dir = BACKUPS_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def save_backup(
        self,
        user_id: str,
        config_id: str,
        database_name: str,
        backup_mode: str,
        tables: List[str],
        sql_content: str,
    ) -> BackupRecord:
        """保存备份文件并记录元数据"""
        backup_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = {
            "structure_and_data": "full",
            "structure_only": "structure",
            "data_only": "data",
        }.get(backup_mode, "backup")
        file_name = f"backup_{database_name}_{timestamp}_{mode_suffix}.sql"

        user_dir = self._get_user_backup_dir(user_id)
        file_path = user_dir / file_name

        # 写入文件
        file_path.write_text(sql_content, encoding="utf-8")
        file_size = file_path.stat().st_size

        record = BackupRecord(
            id=backup_id,
            user_id=user_id,
            config_id=config_id,
            database_name=database_name,
            file_name=file_name,
            file_path=str(file_path),
            file_size=file_size,
            backup_mode=backup_mode,
            tables_count=len(tables),
            tables_list=tables,
            status="success",
            created_at=datetime.now().isoformat(),
        )

        # 写入元数据
        self._insert_record(record)

        logger.info(
            f"Backup saved: {file_name} ({file_size} bytes, {len(tables)} tables)"
        )
        return record

    def _insert_record(self, record: BackupRecord):
        """插入备份记录到元数据数据库"""
        with sqlite3.connect(str(METADATA_DB)) as conn:
            conn.execute(
                """
                INSERT INTO backup_records
                (id, user_id, config_id, database_name, file_name, file_path,
                 file_size, backup_mode, tables_count, tables_list, status,
                 error_message, created_at, downloaded_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.user_id,
                    record.config_id,
                    record.database_name,
                    record.file_name,
                    record.file_path,
                    record.file_size,
                    record.backup_mode,
                    record.tables_count,
                    json.dumps(record.tables_list),
                    record.status,
                    record.error_message,
                    record.created_at,
                    record.downloaded_count,
                ),
            )
            conn.commit()

    def get_record(self, backup_id: str, user_id: str) -> Optional[BackupRecord]:
        """获取备份记录（带用户隔离）"""
        with sqlite3.connect(str(METADATA_DB)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM backup_records WHERE id = ? AND user_id = ?",
                (backup_id, user_id),
            ).fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def list_records(
        self,
        user_id: str,
        config_id: Optional[str] = None,
        database_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取备份记录列表"""
        conditions = ["user_id = ?"]
        params = [user_id]

        if config_id:
            conditions.append("config_id = ?")
            params.append(config_id)
        if database_name:
            conditions.append("database_name = ?")
            params.append(database_name)

        where_clause = " AND ".join(conditions)

        with sqlite3.connect(str(METADATA_DB)) as conn:
            conn.row_factory = sqlite3.Row

            # 总数
            count_row = conn.execute(
                f"SELECT COUNT(*) FROM backup_records WHERE {where_clause}",
                params,
            ).fetchone()
            total = count_row[0] if count_row else 0

            # 分页数据
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""
                SELECT * FROM backup_records
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()

            records = [self._row_to_record(row).to_dict() for row in rows]

            return {
                "records": records,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }

    def delete_record(self, backup_id: str, user_id: str) -> bool:
        """删除备份文件和元数据"""
        record = self.get_record(backup_id, user_id)
        if not record:
            return False

        # 删除文件
        try:
            file_path = Path(record.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Backup file deleted: {record.file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete backup file: {e}")

        # 删除元数据
        with sqlite3.connect(str(METADATA_DB)) as conn:
            conn.execute(
                "DELETE FROM backup_records WHERE id = ? AND user_id = ?",
                (backup_id, user_id),
            )
            conn.commit()

        return True

    def increment_download_count(self, backup_id: str, user_id: str) -> bool:
        """增加下载计数"""
        with sqlite3.connect(str(METADATA_DB)) as conn:
            cursor = conn.execute(
                """
                UPDATE backup_records
                SET downloaded_count = downloaded_count + 1
                WHERE id = ? AND user_id = ?
                """,
                (backup_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def cleanup_old_backups(self, days: int = 30) -> int:
        """清理超过指定天数的备份文件"""
        cutoff = datetime.now().isoformat()
        # 简化实现：实际应该解析 created_at 比较
        # 这里仅做占位，实际清理可以通过外部定时任务
        return 0

    def _row_to_record(self, row: sqlite3.Row) -> BackupRecord:
        """将数据库行转换为 BackupRecord"""
        tables_list = []
        tables_json = row["tables_list"]
        if tables_json:
            try:
                tables_list = json.loads(tables_json)
            except json.JSONDecodeError:
                pass

        return BackupRecord(
            id=row["id"],
            user_id=row["user_id"],
            config_id=row["config_id"],
            database_name=row["database_name"],
            file_name=row["file_name"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            backup_mode=row["backup_mode"],
            tables_count=row["tables_count"],
            tables_list=tables_list,
            status=row["status"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            downloaded_count=row["downloaded_count"],
        )


# 单例实例
backup_storage = BackupStorage()
