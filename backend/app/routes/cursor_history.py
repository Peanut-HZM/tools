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

