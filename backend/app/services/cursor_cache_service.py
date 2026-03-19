"""
Cursor 对话历史缓存服务
作者：huazm
描述：将 Cursor 原始数据同步到本地 SQLite 缓存数据库，提供高性能查询接口和 CRUD 操作
"""

import json
import logging
import math
import os
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from typing import List, Optional, Tuple

from app.models.cursor_history_models import (
    CursorMessage,
    CursorProject,
    CursorSession,
    SearchResultItem,
)
from app.services.cursor_history_service import (
    CursorHistoryService,
    DEFAULT_CURSOR_BASE_PATH,
    _get_paths,
)

logger = logging.getLogger(__name__)

# 缓存数据库路径
CACHE_DB_PATH = "cursor_history.db"

# 同步状态（全局变量，用于跟踪同步进度）
_sync_status = {
    "syncing": False,
    "progress": 0,
    "total": 0,
    "current_step": "",
    "last_sync_time": None,
    "error": None,
}
_sync_lock = threading.Lock()


class CursorCacheService:
    """Cursor 对话历史缓存服务，管理本地 SQLite 缓存数据库"""

    @classmethod
    def _get_conn(cls) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(CACHE_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @classmethod
    def init_db(cls):
        """
        初始化缓存数据库，创建所有必要的表
        包含：cursor_cache_projects、cursor_cache_sessions、cursor_cache_messages
        """
        logger.info("初始化缓存数据库表结构")
        conn = cls._get_conn()
        cursor = conn.cursor()

        # 项目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_cache_projects (
                workspace_hash TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                project_path TEXT,
                session_count INTEGER DEFAULT 0,
                git_remote_url TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 兼容旧表：如果已有表但缺少 git_remote_url 列，则自动添加
        try:
            cursor.execute("SELECT git_remote_url FROM cursor_cache_projects LIMIT 1")
        except Exception:
            cursor.execute("ALTER TABLE cursor_cache_projects ADD COLUMN git_remote_url TEXT")

        # 会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_cache_sessions (
                composer_id TEXT PRIMARY KEY,
                workspace_hash TEXT NOT NULL,
                name TEXT,
                created_at INTEGER,
                message_count INTEGER DEFAULT 0,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_hash) REFERENCES cursor_cache_projects(workspace_hash)
                    ON DELETE CASCADE
            )
        """)

        # 消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_cache_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                composer_id TEXT NOT NULL,
                message_type INTEGER DEFAULT 0,
                text TEXT DEFAULT '',
                code_blocks TEXT DEFAULT '[]',
                timestamp TEXT,
                thinking TEXT,
                tool_call TEXT,
                capability_type INTEGER,
                sort_order INTEGER DEFAULT 0,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (composer_id) REFERENCES cursor_cache_sessions(composer_id)
                    ON DELETE CASCADE
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_composer_id
            ON cursor_cache_messages(composer_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_sort
            ON cursor_cache_messages(composer_id, sort_order)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_workspace
            ON cursor_cache_sessions(workspace_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_text
            ON cursor_cache_messages(text)
        """)

        conn.commit()
        conn.close()
        logger.info("缓存数据库表结构初始化完成")

    @classmethod
    def get_sync_status(cls) -> dict:
        """获取当前同步状态"""
        with _sync_lock:
            return dict(_sync_status)

    @classmethod
    def _update_sync_status(cls, **kwargs):
        """更新同步状态（线程安全）"""
        with _sync_lock:
            _sync_status.update(kwargs)

    @classmethod
    def sync_all_data(cls, custom_base: Optional[str] = None):
        """
        全量同步 Cursor 数据到本地缓存
        流程：清空缓存 → 遍历所有项目 → 解析会话 → 解析消息 → 写入数据库
        参数：custom_base - 自定义 Cursor 基础路径
        """
        with _sync_lock:
            if _sync_status["syncing"]:
                logger.warning("同步任务已在运行中，跳过本次请求")
                return
            _sync_status["syncing"] = True
            _sync_status["progress"] = 0
            _sync_status["total"] = 0
            _sync_status["current_step"] = "准备中..."
            _sync_status["error"] = None

        try:
            cls.init_db()
            cls._do_sync(custom_base)
            cls._update_sync_status(
                syncing=False,
                current_step="同步完成",
                last_sync_time=datetime.now().isoformat(),
            )
            logger.info("全量同步完成")
        except Exception as e:
            logger.error("同步失败: %s", e, exc_info=True)
            cls._update_sync_status(
                syncing=False,
                current_step=f"同步失败: {str(e)}",
                error=str(e),
            )

    @staticmethod
    def _get_git_remote_url(path: str) -> Optional[str]:
        """
        获取指定路径的 Git 远程仓库 URL
        参数：path - 项目本地路径
        返回：规范化后的远程仓库 URL，如果不是 git 仓库则返回 None
        """
        if not path or not os.path.isdir(path):
            return None
        try:
            result = subprocess.run(
                ["git", "-C", path, "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                # 规范化 URL：统一去掉 .git 后缀和末尾斜杠，便于比较
                url = url.rstrip("/")
                if url.endswith(".git"):
                    url = url[:-4]
                return url
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug("获取 git remote URL 失败 (%s): %s", path, e)
        return None

    @classmethod
    def _do_sync(cls, custom_base: Optional[str] = None):
        """
        执行实际的同步逻辑
        核心改进：优先使用 Git 远程仓库 URL 合并同一项目的多个工作空间目录，
        回退到 project_name 合并，避免同一个项目在列表中重复出现
        """
        conn = cls._get_conn()
        cursor = conn.cursor()

        # 清空旧数据（全量同步）
        cls._update_sync_status(current_step="清空旧数据...")
        cursor.execute("DELETE FROM cursor_cache_messages")
        cursor.execute("DELETE FROM cursor_cache_sessions")
        cursor.execute("DELETE FROM cursor_cache_projects")
        conn.commit()
        logger.info("旧缓存数据已清空")

        # 获取所有原始项目（每个 workspace 目录一条记录）
        cls._update_sync_status(current_step="扫描项目...")
        raw_projects = CursorHistoryService.get_projects(custom_base=custom_base)
        logger.info("发现 %d 个原始工作空间目录", len(raw_projects))

        # 第一步：为每个项目获取 git 远程仓库 URL
        cls._update_sync_status(current_step="识别 Git 仓库...")
        git_urls: dict[str, Optional[str]] = {}
        for proj in raw_projects:
            if proj.project_path:
                git_url = cls._get_git_remote_url(proj.project_path)
                git_urls[proj.workspace_hash] = git_url
                if git_url:
                    logger.debug("项目 %s (%s) -> git: %s", proj.project_name, proj.project_path, git_url)
            else:
                git_urls[proj.workspace_hash] = None

        # 第二步：按 git URL（优先）或 project_name（回退）分组
        project_groups: dict[str, list] = {}
        for proj in raw_projects:
            git_url = git_urls.get(proj.workspace_hash)
            # 合并键优先级：Git 远程 URL > 项目名称
            merge_key = git_url or proj.project_name
            if merge_key not in project_groups:
                project_groups[merge_key] = []
            project_groups[merge_key].append(proj)

        total_merged = len(project_groups)
        logger.info(
            "合并后共 %d 个独立项目（原始 %d 个工作空间）",
            total_merged, len(raw_projects),
        )

        cls._update_sync_status(total=total_merged)

        synced_sessions = 0
        synced_messages = 0

        for proj_idx, (merge_key, group) in enumerate(project_groups.items()):
            # 使用会话数最多的工作空间作为主记录
            primary = max(group, key=lambda p: p.session_count)
            all_hashes = [p.workspace_hash for p in group]
            total_session_count = sum(p.session_count for p in group)
            # 获取该组的 git 远程 URL（从任意一个成员取即可）
            group_git_url = git_urls.get(primary.workspace_hash)

            cls._update_sync_status(
                current_step=f"同步项目: {primary.project_name} ({proj_idx + 1}/{total_merged})",
                progress=proj_idx,
            )

            # 写入合并后的项目
            cursor.execute("""
                INSERT OR REPLACE INTO cursor_cache_projects
                (workspace_hash, project_name, project_path, session_count, git_remote_url, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                primary.workspace_hash,
                primary.project_name,
                primary.project_path,
                total_session_count,
                group_git_url,
                datetime.now().isoformat(),
            ))

            # 遍历该项目的所有工作空间目录，获取所有会话
            for ws_hash in all_hashes:
                sessions = CursorHistoryService.get_sessions(
                    workspace_hash=ws_hash,
                    custom_base=custom_base,
                )
                logger.info(
                    "项目 %s (workspace: %s) 下有 %d 个会话",
                    primary.project_name, ws_hash, len(sessions),
                )

                for session in sessions:
                    # 所有会话统一关联到合并后的主 workspace_hash
                    cursor.execute("""
                        INSERT OR REPLACE INTO cursor_cache_sessions
                        (composer_id, workspace_hash, name, created_at, message_count, synced_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        session.composer_id,
                        primary.workspace_hash,
                        session.name,
                        session.created_at,
                        session.message_count,
                        datetime.now().isoformat(),
                    ))
                    synced_sessions += 1

                    # 获取该会话的所有消息（不分页，一次全量取）
                    messages, total, _, _ = CursorHistoryService.get_messages(
                        composer_id=session.composer_id,
                        custom_base=custom_base,
                        page=1,
                        page_size=10000,
                    )

                    # 批量写入消息
                    for sort_idx, msg in enumerate(messages):
                        code_blocks_json = json.dumps(
                            msg.code_blocks, ensure_ascii=False
                        ) if msg.code_blocks else "[]"
                        tool_call_json = json.dumps(
                            msg.tool_call, ensure_ascii=False
                        ) if msg.tool_call else None

                        cursor.execute("""
                            INSERT INTO cursor_cache_messages
                            (message_id, composer_id, message_type, text,
                             code_blocks, timestamp, thinking, tool_call,
                             capability_type, sort_order, synced_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            msg.message_id,
                            session.composer_id,
                            msg.message_type,
                            msg.text,
                            code_blocks_json,
                            msg.timestamp,
                            msg.thinking,
                            tool_call_json,
                            msg.capability_type,
                            sort_idx,
                            datetime.now().isoformat(),
                        ))
                        synced_messages += 1

            conn.commit()

        # 更新最终统计
        cls._update_sync_status(
            progress=total_merged,
            total=total_merged,
            current_step=(
                f"同步完成: {total_merged} 个项目, "
                f"{synced_sessions} 个会话, "
                f"{synced_messages} 条消息"
            ),
        )
        conn.close()
        logger.info(
            "同步完成: %d 个项目, %d 个会话, %d 条消息",
            total_merged, synced_sessions, synced_messages,
        )

    @classmethod
    def has_cache(cls) -> bool:
        """检查缓存数据库是否有数据"""
        try:
            conn = cls._get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='cursor_cache_projects'"
            )
            if not cur.fetchone():
                conn.close()
                return False
            cur.execute("SELECT COUNT(*) as cnt FROM cursor_cache_projects")
            cnt = cur.fetchone()["cnt"]
            conn.close()
            return cnt > 0
        except Exception:
            return False

    # ==================== 缓存查询方法 ====================

    @classmethod
    def get_cached_projects(cls) -> List[CursorProject]:
        """从缓存数据库获取项目列表"""
        conn = cls._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT workspace_hash, project_name, project_path, "
            "session_count, git_remote_url FROM cursor_cache_projects "
            "ORDER BY project_name"
        )
        rows = cur.fetchall()
        conn.close()

        projects = []
        for row in rows:
            projects.append(CursorProject(
                workspace_hash=row["workspace_hash"],
                project_name=row["project_name"],
                project_path=row["project_path"],
                session_count=row["session_count"],
                git_remote_url=row["git_remote_url"],
            ))
        return projects

    @classmethod
    def get_cached_sessions(
        cls, workspace_hash: str
    ) -> List[CursorSession]:
        """
        从缓存数据库获取指定项目的会话列表
        参数：workspace_hash - 项目的工作空间哈希值
        返回：会话列表
        """
        conn = cls._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT composer_id, workspace_hash, name, "
            "created_at, message_count "
            "FROM cursor_cache_sessions "
            "WHERE workspace_hash = ? "
            "ORDER BY created_at DESC",
            (workspace_hash,),
        )
        rows = cur.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            sessions.append(CursorSession(
                composer_id=row["composer_id"],
                name=row["name"],
                created_at=row["created_at"],
                message_count=row["message_count"],
            ))
        return sessions

    @classmethod
    def get_cached_messages(
        cls,
        composer_id: str,
        page: int = 1,
        page_size: int = 50,
        latest_first: bool = False,
    ) -> Tuple[List[CursorMessage], int, bool, int]:
        """
        从缓存数据库获取指定会话的消息列表，支持分页
        参数：
            composer_id - 会话 ID
            page - 页码
            page_size - 每页数量
            latest_first - 是否最新消息优先（反向分页）
        返回：(消息列表, 总数, 是否有更多, 总页数)
        """
        conn = cls._get_conn()
        cur = conn.cursor()

        # 获取总数
        cur.execute(
            "SELECT COUNT(*) as cnt FROM cursor_cache_messages "
            "WHERE composer_id = ?",
            (composer_id,),
        )
        total = cur.fetchone()["cnt"]
        total_pages = max(1, math.ceil(total / page_size))

        if latest_first:
            # 反向分页：page=1 返回最新的消息
            offset = max(0, total - page * page_size)
            limit = min(page_size, total - (page - 1) * page_size)
            cur.execute(
                "SELECT * FROM cursor_cache_messages "
                "WHERE composer_id = ? "
                "ORDER BY sort_order ASC "
                "LIMIT ? OFFSET ?",
                (composer_id, limit, offset),
            )
        else:
            offset = (page - 1) * page_size
            cur.execute(
                "SELECT * FROM cursor_cache_messages "
                "WHERE composer_id = ? "
                "ORDER BY sort_order ASC "
                "LIMIT ? OFFSET ?",
                (composer_id, page_size, offset),
            )

        rows = cur.fetchall()
        conn.close()

        messages = []
        for row in rows:
            # 解析 code_blocks JSON
            code_blocks = []
            if row["code_blocks"]:
                try:
                    code_blocks = json.loads(row["code_blocks"])
                except (json.JSONDecodeError, TypeError):
                    pass

            # 解析 tool_call JSON
            tool_call = None
            if row["tool_call"]:
                try:
                    tool_call = json.loads(row["tool_call"])
                except (json.JSONDecodeError, TypeError):
                    pass

            messages.append(CursorMessage(
                message_id=row["message_id"],
                message_type=row["message_type"],
                text=row["text"] or "",
                code_blocks=code_blocks,
                timestamp=row["timestamp"],
                thinking=row["thinking"],
                tool_call=tool_call,
                capability_type=row["capability_type"],
            ))

        has_more = page < total_pages
        return messages, total, has_more, total_pages

    @classmethod
    def search_cached_messages(
        cls, keyword: str, page: int = 1, page_size: int = 20
    ) -> dict:
        """
        全局搜索：同时搜索会话标题和消息内容
        参数：keyword - 搜索关键词, page - 页码, page_size - 每页数量
        返回：包含 results, total, total_pages 的字典
        """
        conn = cls._get_conn()
        cur = conn.cursor()
        like_param = f"%{keyword}%"

        # 1. 搜索会话标题匹配
        cur.execute(
            "SELECT s.composer_id, s.name as session_name, s.workspace_hash, "
            "p.project_name "
            "FROM cursor_cache_sessions s "
            "JOIN cursor_cache_projects p "
            "  ON s.workspace_hash = p.workspace_hash "
            "WHERE s.name LIKE ?",
            (like_param,),
        )
        title_rows = cur.fetchall()

        # 2. 搜索消息内容匹配
        cur.execute(
            "SELECT m.composer_id, m.message_type, m.text, "
            "s.name as session_name, s.workspace_hash, "
            "p.project_name "
            "FROM cursor_cache_messages m "
            "JOIN cursor_cache_sessions s "
            "  ON m.composer_id = s.composer_id "
            "JOIN cursor_cache_projects p "
            "  ON s.workspace_hash = p.workspace_hash "
            "WHERE m.text LIKE ?",
            (like_param,),
        )
        content_rows = cur.fetchall()
        conn.close()

        results = []

        # 处理会话标题匹配结果（去重，一个会话只出现一次）
        seen_title_composers = set()
        for row in title_rows:
            cid = row["composer_id"]
            if cid in seen_title_composers:
                continue
            seen_title_composers.add(cid)
            session_name = row["session_name"] or ""
            # 提取标题中的匹配片段
            idx = session_name.lower().find(keyword.lower())
            start = max(0, idx - 30)
            end = min(len(session_name), idx + len(keyword) + 30)
            matched = session_name[start:end]

            results.append(SearchResultItem(
                project_name=row["project_name"],
                workspace_hash=row["workspace_hash"],
                composer_id=cid,
                session_name=row["session_name"],
                matched_text=matched,
                message_type=-1,
                match_type="title",
            ))

        # 处理消息内容匹配结果
        for row in content_rows:
            text = row["text"] or ""
            idx = text.lower().find(keyword.lower())
            start = max(0, idx - 50)
            end = min(len(text), idx + len(keyword) + 50)
            matched = text[start:end]

            results.append(SearchResultItem(
                project_name=row["project_name"],
                workspace_hash=row["workspace_hash"],
                composer_id=row["composer_id"],
                session_name=row["session_name"],
                matched_text=matched,
                message_type=row["message_type"],
                match_type="content",
            ))

        # 计算分页
        total = len(results)
        total_pages = max(1, (total + page_size - 1) // page_size)
        # 确保页码有效
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_results = results[start_idx:end_idx]

        return {
            "results": paged_results,
            "total": total,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size,
        }

    # ==================== CRUD 操作 ====================

    @classmethod
    def batch_delete_projects(cls, workspace_hashes: list) -> int:
        """
        批量删除缓存中的多个项目及其所有会话和消息
        参数：workspace_hashes - 要删除的项目工作空间哈希值列表
        返回：成功删除的项目数量
        """
        if not workspace_hashes:
            return 0
        cls.init_db()
        conn = cls._get_conn()
        cur = conn.cursor()
        deleted_count = 0
        for ws_hash in workspace_hashes:
            # 先删除该项目下所有会话的消息
            cur.execute(
                "DELETE FROM cursor_cache_messages WHERE composer_id IN "
                "(SELECT composer_id FROM cursor_cache_sessions WHERE workspace_hash = ?)",
                (ws_hash,),
            )
            # 删除该项目下的所有会话
            cur.execute(
                "DELETE FROM cursor_cache_sessions WHERE workspace_hash = ?",
                (ws_hash,),
            )
            # 删除项目本身
            cur.execute(
                "DELETE FROM cursor_cache_projects WHERE workspace_hash = ?",
                (ws_hash,),
            )
            if cur.rowcount > 0:
                deleted_count += 1
        conn.commit()
        conn.close()
        logger.info("批量删除了 %d 个缓存项目", deleted_count)
        return deleted_count

    @classmethod
    def delete_project(cls, workspace_hash: str) -> bool:
        """
        删除缓存中的项目及其所有会话和消息
        参数：workspace_hash - 项目的工作空间哈希值
        返回：是否删除成功
        """
        # 确保缓存表已初始化，避免表不存在导致的错误
        cls.init_db()
        conn = cls._get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM cursor_cache_projects "
            "WHERE workspace_hash = ?",
            (workspace_hash,),
        )
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        if deleted:
            logger.info("已删除缓存项目: %s", workspace_hash)
        return deleted

    @classmethod
    def delete_session(cls, composer_id: str) -> bool:
        """
        删除缓存中的会话及其所有消息
        参数：composer_id - 会话 ID
        返回：是否删除成功
        """
        # 确保缓存表已初始化，避免表不存在导致的错误
        cls.init_db()
        conn = cls._get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM cursor_cache_sessions "
            "WHERE composer_id = ?",
            (composer_id,),
        )
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        if deleted:
            logger.info("已删除缓存会话: %s", composer_id)
        return deleted
