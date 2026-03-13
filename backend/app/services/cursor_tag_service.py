"""Cursor 标签服务"""
import sqlite3
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "cursor_history.db"


class CursorTagService:
    """标签服务类"""

    @staticmethod
    def init_db():
        """初始化标签表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composer_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(composer_id, tag_name)
            )
        """)
        conn.commit()
        conn.close()
        logger.info("cursor_tags 表初始化完成")

    @staticmethod
    def add_tag(composer_id: str, tag_name: str) -> bool:
        """添加标签"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO cursor_tags (composer_id, tag_name) VALUES (?, ?)",
                (composer_id, tag_name)
            )
            conn.commit()
            added = cursor.rowcount > 0
            conn.close()
            if added:
                logger.info(f"添加标签成功：{composer_id} - {tag_name}")
            return added
        except Exception as e:
            logger.error(f"添加标签失败：{e}")
            return False

    @staticmethod
    def remove_tag(composer_id: str, tag_name: str) -> bool:
        """移除标签"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cursor_tags WHERE composer_id = ? AND tag_name = ?",
                (composer_id, tag_name)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            if deleted:
                logger.info(f"移除标签成功：{composer_id} - {tag_name}")
            return deleted
        except Exception as e:
            logger.error(f"移除标签失败：{e}")
            return False

    @staticmethod
    def get_tags(composer_id: str) -> List['CursorTag']:
        """获取会话的所有标签"""
        try:
            from app.models.cursor_tag import CursorTag
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM cursor_tags WHERE composer_id = ? ORDER BY created_at DESC",
                (composer_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [CursorTag(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"获取标签失败：{e}")
            return []

    @staticmethod
    def get_all_tags() -> List[str]:
        """获取所有不重复的标签名"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT tag_name FROM cursor_tags ORDER BY tag_name")
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取所有标签失败：{e}")
            return []

    @staticmethod
    def search_by_tag(tag_name: str) -> List[str]:
        """根据标签搜索会话 ID 列表"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT composer_id FROM cursor_tags WHERE tag_name = ?",
                (tag_name,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"按标签搜索失败：{e}")
            return []


# 初始化表
CursorTagService.init_db()
