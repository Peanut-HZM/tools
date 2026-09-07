"""
Pydantic models for file operations - Markdown Editor
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class FileNode(BaseModel):
    """Represents a file or directory node in the tree"""
    name: str
    path: str
    type: str = Field(..., pattern="^(file|directory)$")
    size: Optional[int] = None
    modified: Optional[datetime] = None
    children: Optional[List['FileNode']] = None
    # 文件类型元数据（可选，由后端在构建文件树时填充）
    extension: Optional[str] = None       # 文件扩展名，如 ".md"
    file_type: Optional[str] = None       # 文件类型分类，如 "markdown", "html"
    previewable: Optional[bool] = None    # 是否支持预览


class FileContent(BaseModel):
    """File content with metadata"""
    path: str
    content: str
    size: int
    modified: datetime


class FileRawContent(BaseModel):
    """文件原始内容（支持二进制文件）

    对于文本文件：text 字段包含内容，data 为 None
    对于二进制文件：data 字段包含 base64 编码的数据，text 为 None
    """
    path: str
    content_type: str  # MIME type
    size: int
    modified: datetime
    data: Optional[str] = None  # base64 编码的二进制数据（仅二进制文件）
    text: Optional[str] = None  # 文本内容（仅文本文件）


class SaveRequest(BaseModel):
    """Request to save file content"""
    path: str
    content: str


class SaveResult(BaseModel):
    """Result of save operation"""
    success: bool
    message: str
    modified: Optional[datetime] = None


class CreateRequest(BaseModel):
    """Request to create a new file"""
    path: str
    content: Optional[str] = ""


class CreateResult(BaseModel):
    """Result of create operation"""
    success: bool
    path: str
    message: Optional[str] = None


class RenameRequest(BaseModel):
    """Request to rename a file"""
    old_path: str
    new_path: str


class RenameResult(BaseModel):
    """Result of rename operation"""
    success: bool
    message: str
    old_path: str
    new_path: str


class DeleteResult(BaseModel):
    """Result of delete operation"""
    success: bool
    message: str
    path: str


class DirectoryCreateRequest(BaseModel):
    """Request to create a directory"""
    path: str


class DirectoryDeleteRequest(BaseModel):
    """Request to delete a directory"""
    path: str
    recursive: bool = False


class SetRootRequest(BaseModel):
    """Request to set root directory"""
    path: str


class RootPathResponse(BaseModel):
    """Response with current root path"""
    path: str
    exists: bool


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    path: Optional[str] = None
    details: Optional[str] = None
