"""
Cursor 对话历史服务
作者：huazm
描述：读取本地 Cursor 的 SQLite 数据库，解析项目、会话和消息数据
"""

import json
import logging
import os
import platform
import sqlite3
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote

from app.models.cursor_history_models import (
    CursorMessage,
    CursorProject,
    CursorSession,
    SearchResultItem,
)

logger = logging.getLogger(__name__)

# 获取真实的用户主目录（避免 HOME 环境变量被其他模块覆盖的问题）
# config.py 中为了 PaddleOCR 缓存重写了 HOME，导致 expanduser("~") 返回错误路径
# Windows 使用 os.environ 获取 USERPROFILE，Unix 使用 pwd 模块
if platform.system() == "Windows":
    _REAL_HOME = os.environ.get("USERPROFILE", "")
else:
    import pwd
    _REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir

# Cursor 数据存储默认基础路径
DEFAULT_CURSOR_BASE_PATH = os.path.join(
    _REAL_HOME, "Library", "Application Support", "Cursor", "User"
)


def _get_paths(custom_base: Optional[str] = None):
    """
    根据自定义路径或默认路径，返回 (base_path, workspace_storage_path, global_state_db_path)
    参数：custom_base - 自定义 Cursor User 基础路径
    返回：路径三元组
    """
    base = custom_base if custom_base and os.path.isdir(custom_base) else DEFAULT_CURSOR_BASE_PATH
    workspace = os.path.join(base, "workspaceStorage")
    global_db = os.path.join(base, "globalStorage", "state.vscdb")
    return base, workspace, global_db


class CursorHistoryService:
    """Cursor 对话历史服务类，负责读取和解析 Cursor 本地数据"""

    @staticmethod
    def _extract_project_name(uri: str) -> str:
        """从 file:// URI 中提取项目名称"""
        if not uri:
            return "未知项目"
        # 移除 file:// 前缀并解码
        path = unquote(uri.replace("file://", ""))
        return os.path.basename(path) or path

    @staticmethod
    def _extract_project_path(uri: str) -> Optional[str]:
        """从 file:// URI 中提取项目完整路径"""
        if not uri:
            return None
        return unquote(uri.replace("file://", ""))

    @staticmethod
    def _safe_db_query(db_path: str, query: str, params: tuple = ()) -> list:
        """安全地执行 SQLite 查询，失败时返回空列表"""
        try:
            if not os.path.exists(db_path):
                logger.warning(f"数据库文件不存在: {db_path}")
                return []
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"查询数据库失败: {db_path}, 错误: {str(e)}")
            return []

    @classmethod
    def get_projects(
        cls, search: Optional[str] = None, custom_base: Optional[str] = None
    ) -> List[CursorProject]:
        """
        获取所有 Cursor 项目列表
        参数：search - 可选的项目名搜索关键词，custom_base - 自定义基础路径
        返回：项目列表
        """
        logger.info(f"获取 Cursor 项目列表, 搜索关键词: {search}")
        _, workspace_path, _ = _get_paths(custom_base)
        projects = []

        if not os.path.isdir(workspace_path):
            logger.warning(f"工作区存储路径不存在: {workspace_path}")
            return projects

        for dir_name in os.listdir(workspace_path):
            dir_path = os.path.join(workspace_path, dir_name)
            if not os.path.isdir(dir_path):
                continue

            # 读取 workspace.json 获取项目路径
            workspace_json_path = os.path.join(dir_path, "workspace.json")
            project_name = dir_name
            project_path = None

            if os.path.exists(workspace_json_path):
                try:
                    with open(workspace_json_path, "r") as f:
                        workspace_data = json.load(f)
                    folder_uri = workspace_data.get("folder")
                    if folder_uri:
                        project_name = cls._extract_project_name(folder_uri)
                        project_path = cls._extract_project_path(folder_uri)
                except Exception as e:
                    logger.debug(f"读取 workspace.json 失败: {workspace_json_path}, {e}")

            # 搜索过滤
            if search and search.lower() not in project_name.lower():
                continue

            # 获取会话数量
            state_db = os.path.join(dir_path, "state.vscdb")
            session_count = cls._count_sessions(state_db)

            # 只显示有会话数据的项目
            if session_count > 0:
                projects.append(CursorProject(
                    workspace_hash=dir_name,
                    project_name=project_name,
                    project_path=project_path,
                    session_count=session_count,
                ))

        # 按会话数量降序排列
        projects.sort(key=lambda p: p.session_count, reverse=True)
        logger.info(f"找到 {len(projects)} 个有效项目")
        return projects

    @classmethod
    def _count_sessions(cls, state_db_path: str) -> int:
        """统计工作区数据库中的会话数量"""
        rows = cls._safe_db_query(
            state_db_path,
            "SELECT value FROM ItemTable WHERE key = 'composer.composerData'",
        )
        if not rows:
            return 0
        try:
            data = json.loads(rows[0]["value"])
            all_composers = data.get("allComposers", [])
            return len(all_composers)
        except (json.JSONDecodeError, KeyError):
            return 0

    @classmethod
    def get_sessions(
        cls,
        workspace_hash: str,
        search: Optional[str] = None,
        custom_base: Optional[str] = None,
    ) -> List[CursorSession]:
        """
        获取指定项目下的所有会话
        参数：workspace_hash - 工作区哈希，search - 可选搜索关键词（同时匹配会话名和消息内容）
              custom_base - 自定义基础路径
        返回：会话列表
        """
        logger.info(f"获取会话列表, workspace: {workspace_hash}, 搜索: {search}")
        _, workspace_path, global_db = _get_paths(custom_base)
        state_db = os.path.join(workspace_path, workspace_hash, "state.vscdb")
        rows = cls._safe_db_query(
            state_db,
            "SELECT value FROM ItemTable WHERE key = 'composer.composerData'",
        )
        if not rows:
            return []

        try:
            data = json.loads(rows[0]["value"])
            all_composers = data.get("allComposers", [])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析 composerData 失败: {e}")
            return []

        sessions = []
        search_lower = search.lower() if search else None

        for composer in all_composers:
            composer_id = composer.get("composerId", "")
            name = composer.get("name") or composer.get("title") or ""
            created_at = composer.get("createdAt")

            # 搜索过滤：先匹配会话名称
            name_matched = True
            if search_lower:
                name_matched = search_lower in (name or "").lower()
                # 如果名称不匹配，再搜索消息内容
                if not name_matched:
                    content_matched = cls._search_in_messages(
                        composer_id, search_lower, global_db
                    )
                    if not content_matched:
                        continue

            # 计算消息数量（从全局数据库查询）
            msg_count = cls._count_messages(composer_id, global_db)

            sessions.append(CursorSession(
                composer_id=composer_id,
                name=name if name else f"会话 {composer_id[:8]}",
                created_at=created_at,
                message_count=msg_count,
                workspace_hash=workspace_hash,
            ))

        # 按创建时间降序排列
        sessions.sort(key=lambda s: s.created_at or 0, reverse=True)
        logger.info(f"找到 {len(sessions)} 个会话")
        return sessions

    @classmethod
    def _count_messages(cls, composer_id: str, global_db: str = "") -> int:
        """统计指定会话的消息数量"""
        if not global_db:
            _, _, global_db = _get_paths()
        rows = cls._safe_db_query(
            global_db,
            "SELECT COUNT(*) as cnt FROM cursorDiskKV WHERE key LIKE ?",
            (f"bubbleId:{composer_id}:%",),
        )
        if rows:
            return rows[0].get("cnt", 0)
        return 0

    @classmethod
    def _search_in_messages(
        cls, composer_id: str, search_lower: str, global_db: str
    ) -> bool:
        """
        检查指定会话的消息中是否包含搜索关键词
        参数：composer_id - 会话ID，search_lower - 小写搜索词，global_db - 全局数据库路径
        返回：是否匹配
        """
        rows = cls._safe_db_query(
            global_db,
            "SELECT value FROM cursorDiskKV WHERE key LIKE ? AND value LIKE ? LIMIT 1",
            (f"bubbleId:{composer_id}:%", f"%{search_lower}%"),
        )
        return len(rows) > 0

    @classmethod
    def get_messages(
        cls,
        composer_id: str,
        custom_base: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        latest_first: bool = False,
    ) -> tuple:
        """
        获取指定会话的消息（支持分页）
        参数：composer_id - 会话ID, custom_base - 自定义基础路径
              page - 页码（从1开始）, page_size - 每页数量
              latest_first - 是否从最新消息开始加载（反向分页）
        返回：(消息列表, 总数, 是否有更多, 总页数)
        """
        logger.info(
            f"获取消息列表, composer_id: {composer_id}, "
            f"page: {page}, page_size: {page_size}, "
            f"latest_first: {latest_first}"
        )
        _, _, global_db = _get_paths(custom_base)
        rows = cls._safe_db_query(
            global_db,
            "SELECT key, value FROM cursorDiskKV WHERE key LIKE ? ORDER BY key",
            (f"bubbleId:{composer_id}:%",),
        )

        # 解析所有消息（包括 thinking、tool_call 等类型）
        all_messages = []
        for row in rows:
            key = row.get("key", "")
            # key 格式: bubbleId:{composerId}:{messageIndex}
            parts = key.split(":")
            message_id = parts[-1] if len(parts) >= 3 else key

            # 跳过 value 为空的行
            value_str = row.get("value")
            if not value_str:
                logger.debug(f"跳过 value 为空的行：key={key}")
                continue

            try:
                val = json.loads(value_str)
            except json.JSONDecodeError:
                logger.debug(f"解析 JSON 失败：key={key}")
                continue

            text = val.get("text", "")
            raw_msg_type = val.get("type", 0)
            # Cursor 消息类型映射：1=用户，2=AI（不是 0！）
            # 统一映射为：1=用户，0=AI
            msg_type = 0 if raw_msg_type == 2 else raw_msg_type
            code_blocks = val.get("codeBlocks", [])
            created_at = val.get("createdAt")
            capability_type = val.get("capabilityType")

            # 解析 thinking 内容（capabilityType=30）
            thinking = None
            if capability_type == 30:
                thinking_val = val.get("thinking")
                if isinstance(thinking_val, dict):
                    # thinking 可能是字典格式 {"text": "...", "signature": "..."}
                    thinking = thinking_val.get("text", "") or text or ""
                elif isinstance(thinking_val, str):
                    thinking = thinking_val or text or ""
                else:
                    thinking = text or ""

            # 解析工具调用信息（capabilityType=15）
            tool_call = None
            if capability_type == 15:
                tool_former = val.get("toolFormerData")
                if tool_former and isinstance(tool_former, dict):
                    tool_call = {
                        "toolName": tool_former.get("toolName", ""),
                        "status": tool_former.get("status", ""),
                        "responseText": tool_former.get("responseText", ""),
                    }
                elif tool_former and isinstance(tool_former, list) and len(tool_former) > 0:
                    # 有时 toolFormerData 是列表
                    first = tool_former[0] if isinstance(tool_former[0], dict) else {}
                    tool_call = {
                        "toolName": first.get("toolName", ""),
                        "status": first.get("status", ""),
                        "responseText": first.get("responseText", ""),
                    }

            # 跳过完全空的消息（没有任何有效内容）
            if not text and not code_blocks and not thinking and not tool_call:
                continue

            all_messages.append(CursorMessage(
                message_id=message_id,
                message_type=msg_type,
                text=text,
                code_blocks=code_blocks,
                timestamp=created_at,
                thinking=thinking,
                tool_call=tool_call,
                capability_type=capability_type,
            ))

        total = len(all_messages)
        import math
        total_pages = max(1, math.ceil(total / page_size))

        if latest_first:
            # 反向分页：page=1 返回最后 page_size 条，
            # page=2 返回倒数第二批，以此类推
            # 每页内消息保持时间正序（旧→新）
            end_idx = max(0, total - (page - 1) * page_size)
            start_idx = max(0, end_idx - page_size)
            paged_messages = all_messages[start_idx:end_idx]
            has_more = start_idx > 0
        else:
            # 正向分页：page=1 返回最前面的消息
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paged_messages = all_messages[start_idx:end_idx]
            has_more = end_idx < total

        logger.info(
            f"找到 {total} 条消息, 返回 {len(paged_messages)} 条"
            f" [{start_idx}:{end_idx}], "
            f"has_more: {has_more}, latest_first: {latest_first}"
        )
        return paged_messages, total, has_more, total_pages

    @classmethod
    def search_messages(
        cls, query: str, limit: int = 50,
        custom_base: Optional[str] = None,
    ) -> List[SearchResultItem]:
        """
        全局搜索消息内容
        参数：query - 搜索关键词, limit - 返回结果数量限制
              custom_base - 自定义基础路径
        返回：搜索结果列表
        """
        logger.info(f"全局搜索消息, 关键词: {query}, limit: {limit}")
        if not query:
            return []

        _, _, global_db = _get_paths(custom_base)
        # 在全局数据库中搜索包含关键词的消息
        rows = cls._safe_db_query(
            global_db,
            "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' AND value LIKE ? LIMIT ?",
            (f"%{query}%", limit * 2),
        )

        # 构建 composerId 到项目名的映射
        project_map = cls._build_project_map(custom_base)

        results = []
        for row in rows:
            if len(results) >= limit:
                break

            key = row.get("key", "")
            parts = key.split(":")
            if len(parts) < 3:
                continue

            composer_id = parts[1]

            # 跳过 value 为空的行
            value_str = row.get("value")
            if not value_str:
                continue

            try:
                val = json.loads(value_str)
            except json.JSONDecodeError:
                continue

            text = val.get("text", "")
            if query.lower() not in text.lower():
                continue

            # 提取匹配文本片段（前后各取100字符）
            idx = text.lower().find(query.lower())
            start = max(0, idx - 100)
            end = min(len(text), idx + len(query) + 100)
            matched_text = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")

            # 获取项目名和会话名
            proj_info = project_map.get(composer_id, {})

            results.append(SearchResultItem(
                project_name=proj_info.get("project_name", "未知项目"),
                workspace_hash=proj_info.get("workspace_hash", ""),
                composer_id=composer_id,
                session_name=proj_info.get("session_name"),
                matched_text=matched_text,
                message_type=val.get("type", 0),
            ))

        logger.info(f"搜索到 {len(results)} 条结果")
        return results

    @classmethod
    def get_base_path(cls) -> str:
        """获取当前默认基础路径"""
        return DEFAULT_CURSOR_BASE_PATH

    @classmethod
    def _build_project_map(
        cls, custom_base: Optional[str] = None
    ) -> dict:
        """
        构建 composerId 到项目信息的映射
        参数：custom_base - 自定义基础路径
        返回：{composerId: {project_name, workspace_hash, session_name}}
        """
        _, workspace_path, _ = _get_paths(custom_base)
        project_map = {}
        if not os.path.isdir(workspace_path):
            return project_map

        for dir_name in os.listdir(workspace_path):
            dir_path = os.path.join(workspace_path, dir_name)
            if not os.path.isdir(dir_path):
                continue

            # 获取项目名
            workspace_json_path = os.path.join(dir_path, "workspace.json")
            project_name = dir_name
            if os.path.exists(workspace_json_path):
                try:
                    with open(workspace_json_path, "r") as f:
                        wd = json.load(f)
                    folder_uri = wd.get("folder")
                    if folder_uri:
                        project_name = cls._extract_project_name(folder_uri)
                except Exception:
                    pass

            # 获取会话列表
            state_db = os.path.join(dir_path, "state.vscdb")
            rows = cls._safe_db_query(
                state_db,
                "SELECT value FROM ItemTable WHERE key = 'composer.composerData'",
            )
            if not rows:
                continue

            try:
                data = json.loads(rows[0]["value"])
                for c in data.get("allComposers", []):
                    cid = c.get("composerId", "")
                    project_map[cid] = {
                        "project_name": project_name,
                        "workspace_hash": dir_name,
                        "session_name": c.get("name") or c.get("title"),
                    }
            except (json.JSONDecodeError, KeyError):
                pass

        return project_map

    @classmethod
    def export_session(
        cls,
        composer_id: str,
        export_format: str = "markdown",
        custom_base: Optional[str] = None,
        include_code_blocks: bool = True,
        include_timestamps: bool = True,
        include_avatars: bool = False,
    ) -> tuple:
        """
        导出指定会话的数据
        参数：composer_id - 会话 ID, export_format - 导出格式 (markdown/json/html)
              custom_base - 自定义基础路径
              include_code_blocks - 是否包含代码块
              include_timestamps - 是否包含时间戳
              include_avatars - 是否包含头像标记
        返回：(导出内容，文件名)
        """
        logger.info(f"导出会话：{composer_id}, 格式：{export_format}")

        # 获取项目信息
        project_map = cls._build_project_map(custom_base)
        proj_info = project_map.get(composer_id, {})
        project_name = proj_info.get("project_name", "未知项目")
        session_name = proj_info.get("session_name") or f"会话 {composer_id[:8]}"

        # 获取所有消息
        messages, total, _ = cls.get_messages(composer_id, custom_base, 1, 1000)

        # 统计数据
        user_messages = sum(1 for m in messages if m.message_type == 1)
        ai_messages = sum(1 for m in messages if m.message_type == 0)

        if export_format == "json":
            content = cls._export_json(
                composer_id, session_name, project_name, messages,
                total, user_messages, ai_messages, include_code_blocks
            )
            filename = f"{session_name}.json"
        elif export_format == "html":
            content = cls._export_html(
                composer_id, session_name, project_name, messages,
                include_code_blocks, include_timestamps, include_avatars
            )
            filename = f"{session_name}.html"
        else:  # markdown
            content = cls._export_markdown(
                composer_id, session_name, project_name, messages,
                include_code_blocks, include_timestamps
            )
            filename = f"{session_name}.md"

        return content, filename

    @classmethod
    def _export_json(
        cls, composer_id: str, session_name: str, project_name: str,
        messages: List[CursorMessage], total: int, user_messages: int, ai_messages: int,
        include_code_blocks: bool = True
    ) -> str:
        """导出为 JSON 格式"""
        from datetime import datetime

        data = {
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "format": "json",
                "source": "Cursor History"
            },
            "session": {
                "composer_id": composer_id,
                "name": session_name,
                "project": project_name,
            },
            "statistics": {
                "total_messages": total,
                "user_messages": user_messages,
                "ai_messages": ai_messages,
            },
            "messages": []
        }

        for msg in messages:
            msg_data = {
                "message_id": msg.message_id,
                "message_type": "user" if msg.message_type == 1 else "ai",
                "text": msg.text,
            }
            if include_code_blocks and msg.code_blocks:
                msg_data["code_blocks"] = msg.code_blocks
            data["messages"].append(msg_data)

        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def _export_markdown(
        cls, composer_id: str, session_name: str, project_name: str,
        messages: List[CursorMessage], include_code_blocks: bool = True,
        include_timestamps: bool = True
    ) -> str:
        """导出为 Markdown 格式"""
        from datetime import datetime

        lines = [
            f"# {session_name}",
            "",
            f"**项目**: {project_name}",
            f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ]

        for i, msg in enumerate(messages, 1):
            role = "用户" if msg.message_type == 1 else "AI"
            prefix = f"## {role}" if msg.message_type == 1 else f"## 🤖 {role}"

            if include_timestamps:
                lines.append(f"{prefix} #{i}")
            else:
                lines.append(prefix)
            lines.append("")
            lines.append(msg.text)
            lines.append("")

            if include_code_blocks and msg.code_blocks:
                for j, block in enumerate(msg.code_blocks, 1):
                    code_text = block if isinstance(block, str) else json.dumps(block, ensure_ascii=False, indent=2)
                    lines.append(f"```")
                    lines.append(code_text)
                    lines.append(f"```")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _export_html(
        cls, composer_id: str, session_name: str, project_name: str,
        messages: List[CursorMessage], include_code_blocks: bool = True,
        include_timestamps: bool = True, include_avatars: bool = False
    ) -> str:
        """导出为 HTML 格式"""
        from datetime import datetime

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{session_name} - Cursor 对话历史</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-message-user: #7c3aed20;
            --bg-message-ai: #334155;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-user: #8b5cf6;
            --accent-ai: #10b981;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0; color: var(--text-primary); }}
        .header p {{ color: var(--text-secondary); margin: 10px 0 0; }}
        .message {{
            margin-bottom: 24px;
            padding: 16px 20px;
            border-radius: 12px;
            max-width: 85%;
        }}
        .message-user {{
            background: var(--bg-message-user);
            border: 1px solid var(--accent-user)30;
            margin-left: auto;
        }}
        .message-ai {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
        }}
        .message-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .avatar {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }}
        .avatar-user {{ background: var(--accent-user); }}
        .avatar-ai {{ background: var(--accent-ai); }}
        .message-content {{
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .code-block {{
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
            overflow-x: auto;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 13px;
        }}
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: var(--accent-user);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ background: white; color: black; }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">打印 / 保存为 PDF</button>
    <div class="container">
        <div class="header">
            <h1>{session_name}</h1>
            <p>项目：{project_name} | 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>共 {len(messages)} 条消息</p>
        </div>
"""

        for i, msg in enumerate(messages, 1):
            role = "用户" if msg.message_type == 1 else "AI"
            role_class = "user" if msg.message_type == 1 else "ai"
            avatar = "👤" if msg.message_type == 1 else "🤖"

            html += f"""
        <div class="message message-{role_class}">
            <div class="message-header">
                {f'<div class="avatar avatar-{role_class}">{avatar}</div>' if include_avatars else ''}
                <span>{role}</span>
                {f'<span>#{i}</span>' if include_timestamps else ''}
            </div>
            <div class="message-content">{msg.text.replace('<', '&lt;').replace('>', '&gt;')}</div>
"""

            if include_code_blocks and msg.code_blocks:
                for block in msg.code_blocks:
                    code_text = block if isinstance(block, str) else json.dumps(block, ensure_ascii=False, indent=2)
                    html += f'<pre class="code-block"><code>{code_text.replace('<', '&lt;').replace('>', '&gt;')}</code></pre>'

            html += """
        </div>
"""

        html += """
    </div>
</body>
</html>
"""
        return html

