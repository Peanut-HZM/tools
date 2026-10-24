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
    created: Optional[datetime] = None
    children: Optional[List['FileNode']] = None
    # 文件类型元数据（可选，由后端在构建文件树时填充）
    extension: Optional[str] = None       # 文件扩展名，如 ".md"
    file_type: Optional[str] = None       # 文件类型分类，如 "markdown", "html"
    previewable: Optional[bool] = None    # 是否支持预览
    # 子树因节点数/深度超限而未完整扫描（前端需明确提示"内容已截断"）
    truncated: bool = False
    # 目录无权限访问（前端需提示，而不是伪装成空目录）
    inaccessible: bool = False


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


class ExcelOperation(BaseModel):
    """单条 Excel 编辑操作（按顺序应用）

    字段随 op 类型不同而不同，必填字段在服务层校验并返回 400：
      - set_cell:     sheet, row, col, value, kind(auto|str|number|bool|formula)
      - insert_row / delete_row / insert_col / delete_col: sheet, index, count
      - add_sheet:    title
      - rename_sheet: from_sheet, to_title
      - remove_sheet: sheet
    行列均为 1-based；insert 语义为"插入到第 index 行/列之前"。
    """
    op: str = Field(..., pattern="^(set_cell|insert_row|delete_row|insert_col|delete_col|add_sheet|rename_sheet|remove_sheet)$")
    sheet: Optional[str] = None
    row: Optional[int] = Field(default=None, ge=1)
    col: Optional[int] = Field(default=None, ge=1)
    index: Optional[int] = Field(default=None, ge=1)
    count: Optional[int] = Field(default=None, ge=1)
    value: Optional[str] = None
    kind: Optional[str] = Field(default=None, pattern="^(auto|str|number|bool|formula)$")
    title: Optional[str] = None
    from_sheet: Optional[str] = None
    to_title: Optional[str] = None


class ExcelSaveRequest(BaseModel):
    """Request to apply edit operations to an existing .xlsx file"""
    path: str
    operations: List[ExcelOperation]


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


class FileItem(BaseModel):
    """文件或文件夹信息"""
    name: str
    path: str
    type: str = Field(..., pattern="^(file|directory)$")
    size: int = 0  # 字节数，目录为 0
    modified_at: str  # ISO 时间字符串
    extension: str = ""  # 文件扩展名（目录为空）
    is_previewable: bool = False  # 是否可预览
    is_hidden: bool = False  # 是否为隐藏条目（以 . 开头），前端用于区分展示


class BrowseResponse(BaseModel):
    """目录浏览响应"""
    current_path: str
    breadcrumbs: List[dict]
    items: List[FileItem]
    total: int
    has_more: bool = False
