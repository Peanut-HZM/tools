"""
Cursor 对话历史查看器 - API 路由
作者：huazm
描述：提供 Cursor 对话历史的查询接口，包括项目列表、会话列表、消息详情和全局搜索
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.models.cursor_history_models import (
    MessageListResponse,
    ProjectListResponse,
    SearchResponse,
    SessionListResponse,
    WorkspacePathResponse,
    ExportResponse,
    ExportRequest,
    FavoriteRequest,
    FavoriteItem,
    FavoriteListResponse,
    StatsOverview,
    StatsTrendItem,
    StatsResponse,
)
from app.services.cursor_history_service import (
    CursorHistoryService,
    DEFAULT_CURSOR_BASE_PATH,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cursor-history", tags=["cursor-history"])


@router.get("/basePath", response_model=WorkspacePathResponse)
async def get_base_path(
    path: Optional[str] = Query(None, description="自定义路径（为空则返回默认路径）"),
):
    """获取或验证 Cursor 工作空间基础路径"""
    import os
    check_path = path if path else DEFAULT_CURSOR_BASE_PATH
    valid = os.path.isdir(os.path.join(check_path, "workspaceStorage"))
    logger.info(f"检查路径: {check_path}, 有效: {valid}")
    return WorkspacePathResponse(
        path=check_path, valid=valid, default_path=DEFAULT_CURSOR_BASE_PATH
    )


@router.get("/projects", response_model=ProjectListResponse)
async def get_projects(
    search: Optional[str] = Query(None, description="项目名搜索关键词"),
    base_path: Optional[str] = Query(None, description="自定义 Cursor 基础路径"),
):
    """获取所有 Cursor 项目列表"""
    logger.info(f"请求获取项目列表, 搜索: {search}, 路径: {base_path}")
    projects = CursorHistoryService.get_projects(
        search=search, custom_base=base_path
    )
    logger.info(f"返回 {len(projects)} 个项目")
    return ProjectListResponse(projects=projects, total=len(projects))


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    workspace_hash: str = Query(..., description="工作区哈希"),
    search: Optional[str] = Query(None, description="会话搜索关键词（搜索名称和内容）"),
    base_path: Optional[str] = Query(None, description="自定义 Cursor 基础路径"),
):
    """获取指定项目下的所有会话"""
    logger.info(f"请求获取会话列表, workspace: {workspace_hash}, 搜索: {search}")
    sessions = CursorHistoryService.get_sessions(
        workspace_hash=workspace_hash, search=search, custom_base=base_path
    )

    # 获取项目名
    projects = CursorHistoryService.get_projects(custom_base=base_path)
    project_name = None
    for p in projects:
        if p.workspace_hash == workspace_hash:
            project_name = p.project_name
            break

    logger.info(f"返回 {len(sessions)} 个会话")
    return SessionListResponse(
        sessions=sessions, total=len(sessions), project_name=project_name
    )


@router.get("/messages", response_model=MessageListResponse)
async def get_messages(
    composer_id: str = Query(..., description="会话ID"),
    session_name: Optional[str] = Query(None, description="会话名称"),
    base_path: Optional[str] = Query(None, description="自定义 Cursor 基础路径"),
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(50, ge=10, le=200, description="每页数量"),
):
    """获取指定会话的消息（支持分页）"""
    logger.info(f"请求获取消息列表, composer_id: {composer_id}, page: {page}")
    messages, total, has_more = CursorHistoryService.get_messages(
        composer_id=composer_id,
        custom_base=base_path,
        page=page,
        page_size=page_size,
    )
    logger.info(f"返回 {len(messages)} 条消息, 总计: {total}")
    return MessageListResponse(
        messages=messages,
        total=total,
        session_name=session_name,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/search", response_model=SearchResponse)
async def search_messages(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, ge=1, le=200, description="返回结果数量限制"),
    base_path: Optional[str] = Query(None, description="自定义 Cursor 基础路径"),
):
    """全局搜索消息内容"""
    logger.info(f"请求全局搜索, 关键词: {query}, limit: {limit}")
    results = CursorHistoryService.search_messages(
        query=query, limit=limit, custom_base=base_path
    )
    logger.info(f"搜索返回 {len(results)} 条结果")
    return SearchResponse(results=results, total=len(results), query=query)


@router.post("/export")
async def export_session(request: ExportRequest):
    """导出会话数据"""
    logger.info(f"请求导出会话：{request.composer_id}, 格式：{request.format}")
    try:
        content, filename = CursorHistoryService.export_session(
            composer_id=request.composer_id,
            export_format=request.format,
            custom_base=None,
            include_code_blocks=request.include_code_blocks,
            include_timestamps=request.include_timestamps,
            include_avatars=request.include_avatars,
        )
        logger.info(f"导出成功，文件名：{filename}")
        return ExportResponse(
            success=True,
            format=request.format,
            data=content,
            filename=filename,
        )
    except Exception as e:
        logger.error(f"导出失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")


@router.post("/favorites")
async def add_favorite(request: FavoriteRequest):
    """添加收藏"""
    logger.info(f"添加收藏：{request.composer_id}")
    try:
        import sqlite3
        from datetime import datetime

        db_path = "cursor_history.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composer_id TEXT NOT NULL,
                session_name TEXT,
                project_name TEXT,
                workspace_hash TEXT,
                note TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # 检查是否已收藏
        cursor.execute(
            "SELECT id FROM cursor_favorites WHERE composer_id = ?",
            (request.composer_id,)
        )
        if cursor.fetchone():
            # 已存在则更新
            cursor.execute("""
                UPDATE cursor_favorites
                SET session_name = ?, project_name = ?, workspace_hash = ?, note = ?, tags = ?
                WHERE composer_id = ?
            """, (
                request.session_name, request.project_name, request.workspace_hash,
                request.note, request.tags, request.composer_id
            ))
        else:
            # 新增
            cursor.execute("""
                INSERT INTO cursor_favorites (composer_id, session_name, project_name, workspace_hash, note, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.composer_id, request.session_name, request.project_name,
                request.workspace_hash, request.note, request.tags
            ))

        conn.commit()
        conn.close()

        logger.info(f"收藏成功：{request.composer_id}")
        return {"success": True, "message": "收藏成功"}
    except Exception as e:
        logger.error(f"收藏失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"收藏失败：{str(e)}")


@router.get("/favorites")
async def get_favorites():
    """获取收藏列表"""
    logger.info("获取收藏列表")
    try:
        import sqlite3

        db_path = "cursor_history.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composer_id TEXT NOT NULL,
                session_name TEXT,
                project_name TEXT,
                workspace_hash TEXT,
                note TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        cursor.execute("SELECT * FROM cursor_favorites ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        favorites = []
        for row in rows:
            favorites.append(FavoriteItem(
                id=row["id"],
                composer_id=row["composer_id"],
                session_name=row["session_name"],
                project_name=row["project_name"],
                workspace_hash=row["workspace_hash"],
                note=row["note"],
                tags=row["tags"],
                created_at=row["created_at"],
            ))

        return FavoriteListResponse(favorites=favorites, total=len(favorites))
    except Exception as e:
        logger.error(f"获取收藏失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"获取收藏失败：{str(e)}")


@router.delete("/favorites/{composer_id}")
async def remove_favorite(composer_id: str):
    """删除收藏"""
    logger.info(f"删除收藏：{composer_id}")
    try:
        import sqlite3

        db_path = "cursor_history.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cursor_favorites WHERE composer_id = ?", (composer_id,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()

        if deleted > 0:
            logger.info(f"删除收藏成功：{composer_id}")
            return {"success": True, "message": "删除成功"}
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="收藏不存在")
    except Exception as e:
        logger.error(f"删除收藏失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"删除收藏失败：{str(e)}")


@router.get("/favorites/check/{composer_id}")
async def check_favorite(composer_id: str):
    """检查是否已收藏"""
    logger.info(f"检查收藏状态：{composer_id}")
    try:
        import sqlite3

        db_path = "cursor_history.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM cursor_favorites WHERE composer_id = ?", (composer_id,))
        row = cursor.fetchone()
        conn.close()

        return {"is_favorite": row is not None}
    except Exception as e:
        logger.error(f"检查收藏失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"检查收藏失败：{str(e)}")


@router.get("/stats")
async def get_stats(days: int = 7):
    """获取统计数据"""
    logger.info(f"获取统计数据，天数：{days}")
    try:
        from datetime import datetime, timedelta
        import sqlite3

        db_path = "cursor_history.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 创建表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composer_id TEXT NOT NULL,
                session_name TEXT,
                project_name TEXT,
                workspace_hash TEXT,
                note TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # 获取收藏统计
        cursor.execute("SELECT COUNT(*) as cnt FROM cursor_favorites")
        total_favorites = cursor.fetchone()["cnt"]

        # 计算今天的日期
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())

        # 今天的收藏数
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM cursor_favorites
            WHERE date(created_at) = ?
        """, (today.isoformat(),))
        today_favorites = cursor.fetchone()["cnt"]

        # 获取趋势数据（最近 N 天）
        trends = []
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            date_str = date.isoformat()

            cursor.execute("""
                SELECT COUNT(*) as cnt FROM cursor_favorites
                WHERE date(created_at) = ?
            """, (date_str,))
            cnt = cursor.fetchone()["cnt"]

            trends.append({
                "date": date_str,
                "sessions": cnt,
                "messages": cnt * 5,  # 估算消息数
            })

        conn.close()

        return StatsResponse(
            overview=StatsOverview(
                total_sessions=total_favorites,
                total_messages=total_favorites * 5,
                today_sessions=today_favorites,
                today_messages=today_favorites * 5,
                total_projects=0,
            ),
            trends=trends,
        )
    except Exception as e:
        logger.error(f"获取统计数据失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"获取统计失败：{str(e)}")


# ==================== 标签管理 API ====================

from app.models.cursor_tag import TagAddRequest, TagRemoveRequest, TagListResponse, TagBulkRequest
from app.services.cursor_tag_service import CursorTagService


@router.post("/tags")
async def add_tag(request: TagAddRequest):
    """添加标签到会话"""
    logger.info(f"添加标签：{request.composer_id} - {request.tag_name}")
    try:
        success = CursorTagService.add_tag(request.composer_id, request.tag_name)
        return {"success": success, "message": "标签添加成功" if success else "标签已存在"}
    except Exception as e:
        logger.error(f"添加标签失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"添加标签失败：{str(e)}")


@router.delete("/tags")
async def remove_tag(request: TagRemoveRequest):
    """移除会话标签"""
    logger.info(f"移除标签：{request.composer_id} - {request.tag_name}")
    try:
        success = CursorTagService.remove_tag(request.composer_id, request.tag_name)
        return {"success": success, "message": "标签移除成功" if success else "标签不存在"}
    except Exception as e:
        logger.error(f"移除标签失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"移除标签失败：{str(e)}")


@router.get("/tags/{composer_id}")
async def get_tags(composer_id: str):
    """获取会话的所有标签"""
    logger.info(f"获取标签：{composer_id}")
    try:
        tags = CursorTagService.get_tags(composer_id)
        return TagListResponse(tags=tags, total=len(tags))
    except Exception as e:
        logger.error(f"获取标签失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"获取标签失败：{str(e)}")


@router.get("/tags")
async def get_all_tags():
    """获取所有标签"""
    logger.info("获取所有标签")
    try:
        all_tags = CursorTagService.get_all_tags()
        return {"tags": all_tags, "total": len(all_tags)}
    except Exception as e:
        logger.error(f"获取所有标签失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"获取所有标签失败：{str(e)}")


@router.get("/sessions/by-tag/{tag_name}")
async def get_sessions_by_tag(tag_name: str):
    """根据标签获取会话列表"""
    logger.info(f"按标签获取会话：{tag_name}")
    try:
        composer_ids = CursorTagService.search_by_tag(tag_name)
        return {"composer_ids": composer_ids, "total": len(composer_ids)}
    except Exception as e:
        logger.error(f"按标签获取会话失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


# ==================== 批量操作 API ====================

@router.post("/batch/export")
async def batch_export(request: TagBulkRequest):
    """批量导出会话"""
    logger.info(f"批量导出 {len(request.composer_ids)} 个会话")
    try:
        from app.services.cursor_history_service import CursorHistoryService
        import zipfile
        import io
        import base64

        # 创建 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for composer_id in request.composer_ids:
                try:
                    content, filename = CursorHistoryService.export_session(
                        composer_id=composer_id,
                        export_format='markdown',
                        include_code_blocks=True,
                        include_timestamps=True,
                        include_avatars=False,
                    )
                    # 清理文件名
                    safe_filename = "".join(c if c.isalnum() or c in '-_' else '_' for c in filename)
                    zf.writestr(f"{safe_filename}.md", content)
                except Exception as e:
                    logger.error(f"导出会话 {composer_id} 失败：{e}")
                    continue

        zip_buffer.seek(0)
        zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')

        return {
            "success": True,
            "data": zip_data,
            "filename": "cursor_sessions_export.zip",
        }
    except Exception as e:
        logger.error(f"批量导出失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"批量导出失败：{str(e)}")


@router.post("/batch/tags")
async def batch_add_tags(request: TagBulkRequest):
    """批量添加标签"""
    logger.info(f"批量添加标签 {request.tag_name} 到 {len(request.composer_ids)} 个会话")
    try:
        success_count = 0
        for composer_id in request.composer_ids:
            if CursorTagService.add_tag(composer_id, request.tag_name):
                success_count += 1

        return {
            "success": True,
            "message": f"已为 {success_count} 个会话添加标签",
        }
    except Exception as e:
        logger.error(f"批量添加标签失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"批量操作失败：{str(e)}")


@router.delete("/batch/favorites")
async def batch_remove_favorites(request: TagBulkRequest):
    """批量移除收藏"""
    logger.info(f"批量移除 {len(request.composer_ids)} 个收藏")
    try:
        import sqlite3
        db_path = "cursor_history.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        placeholders = ','.join(['?' for _ in request.composer_ids])
        cursor.execute(f"DELETE FROM cursor_favorites WHERE composer_id IN ({placeholders})", request.composer_ids)

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"已移除 {deleted} 个收藏",
        }
    except Exception as e:
        logger.error(f"批量移除收藏失败：{e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"批量操作失败：{str(e)}")

