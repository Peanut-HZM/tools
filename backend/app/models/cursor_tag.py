"""Cursor 标签数据模型"""
from pydantic import BaseModel
from typing import Optional, List


class CursorTag(BaseModel):
    """标签信息"""
    id: Optional[int] = None
    composer_id: str
    tag_name: str
    created_at: Optional[str] = None


class TagAddRequest(BaseModel):
    """添加标签请求"""
    composer_id: str
    tag_name: str


class TagRemoveRequest(BaseModel):
    """移除标签请求"""
    composer_id: str
    tag_name: str


class TagListResponse(BaseModel):
    """标签列表响应"""
    tags: List[CursorTag]
    total: int


class TagBulkRequest(BaseModel):
    """批量操作请求"""
    composer_ids: List[str]
    tag_name: Optional[str] = None
