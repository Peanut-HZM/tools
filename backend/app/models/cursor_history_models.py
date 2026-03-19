"""
Cursor 对话历史查看器 - 数据模型
作者：huazm
描述：定义 Cursor 对话历史相关的请求和响应模型
"""

from pydantic import BaseModel
from typing import Optional, List


class CursorProject(BaseModel):
    """Cursor 项目信息模型"""
    # 工作区存储的哈希目录名
    workspace_hash: str
    # 项目名称（从路径中提取）
    project_name: str
    # 项目完整路径
    project_path: Optional[str] = None
    # 该项目下的会话数量
    session_count: int = 0
    # Git 远程仓库地址（用于项目去重）
    git_remote_url: Optional[str] = None


class CursorSession(BaseModel):
    """Cursor 会话（Composer）信息模型"""
    # 会话唯一标识
    composer_id: str
    # 会话名称
    name: Optional[str] = None
    # 创建时间戳（毫秒）
    created_at: Optional[int] = None
    # 消息数量
    message_count: int = 0
    # 所属工作区哈希
    workspace_hash: Optional[str] = None


class CursorMessage(BaseModel):
    """Cursor 消息模型"""
    # 消息ID
    message_id: str
    # 消息类型：1=用户消息, 2=AI回复
    message_type: int = 0
    # 消息文本内容
    text: str = ""
    # 代码块列表
    code_blocks: List[dict] = []
    # 消息创建时间戳（毫秒）- 支持整数或字符串格式
    timestamp: Optional[str] = None
    # AI 思考/推理内容（capabilityType=30）- 支持字符串或字典格式
    thinking: Optional[str] = None
    # 工具调用信息（capabilityType=15），包含 toolName, status 等
    tool_call: Optional[dict] = None
    # 能力类型：None=普通消息, 30=思考, 15=工具调用
    capability_type: Optional[int] = None


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    projects: List[CursorProject]
    total: int


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[CursorSession]
    total: int
    project_name: Optional[str] = None


class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[CursorMessage]
    total: int
    session_name: Optional[str] = None
    # 当前页码（从1开始）
    page: int = 1
    # 每页数量
    page_size: int = 50
    # 总页数
    total_pages: int = 1
    # 是否有更多数据（向上加载历史时，表示是否还有更早的消息）
    has_more: bool = False


class SearchResultItem(BaseModel):
    """搜索结果项"""
    # 项目名称
    project_name: str
    # 工作区哈希
    workspace_hash: str
    # 会话ID
    composer_id: str
    # 会话名称
    session_name: Optional[str] = None
    # 匹配的消息文本片段
    matched_text: str = ""
    # 消息类型（0=消息内容匹配, 1=用户消息, 2=AI消息, -1=会话标题匹配）
    message_type: int = 0
    # 匹配类型：title=会话标题匹配, content=消息内容匹配
    match_type: str = "content"


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResultItem]
    total: int
    query: str
    # 当前页码
    page: int = 1
    # 每页数量
    page_size: int = 20
    # 总页数
    total_pages: int = 1


class WorkspacePathResponse(BaseModel):
    """工作空间路径响应"""
    # 当前使用的路径
    path: str
    # 路径是否有效
    valid: bool
    # 默认路径
    default_path: str


class ExportData(BaseModel):
    """导出数据"""
    # 会话信息
    composer_id: str
    session_name: Optional[str] = None
    workspace_hash: Optional[str] = None
    project_name: Optional[str] = None
    created_at: Optional[int] = None
    # 消息列表
    messages: List[CursorMessage]
    # 统计信息
    total_messages: int
    user_messages: int
    ai_messages: int


class ExportResponse(BaseModel):
    """导出响应"""
    success: bool
    format: str  # markdown, json, html
    data: str  # 导出内容
    filename: str


class ExportRequest(BaseModel):
    """导出请求"""
    composer_id: str
    session_name: Optional[str] = None
    workspace_hash: Optional[str] = None
    format: str = "markdown"  # markdown, json, html
    include_code_blocks: bool = True
    include_timestamps: bool = True
    include_avatars: bool = False


class FavoriteRequest(BaseModel):
    """收藏请求"""
    composer_id: str
    session_name: Optional[str] = None
    project_name: Optional[str] = None
    workspace_hash: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None


class FavoriteItem(BaseModel):
    """收藏项"""
    id: int
    composer_id: str
    session_name: Optional[str] = None
    project_name: Optional[str] = None
    workspace_hash: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None
    created_at: str


class FavoriteListResponse(BaseModel):
    """收藏列表响应"""
    favorites: List[FavoriteItem]
    total: int


class StatsOverview(BaseModel):
    """统计概览"""
    total_sessions: int
    total_messages: int
    today_sessions: int
    today_messages: int
    total_projects: int


class StatsTrendItem(BaseModel):
    """统计趋势项"""
    date: str
    sessions: int
    messages: int


class StatsResponse(BaseModel):
    """统计响应"""
    overview: StatsOverview
    trends: List[StatsTrendItem]


class BatchDeleteProjectsRequest(BaseModel):
    """批量删除项目请求"""
    # 要删除的项目工作空间哈希列表
    workspace_hashes: List[str]

