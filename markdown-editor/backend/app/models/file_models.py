"""
Pydantic models for file operations
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


class FileContent(BaseModel):
    """File content with metadata"""
    path: str
    content: str
    size: int
    modified: datetime


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


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    path: Optional[str] = None
    details: Optional[str] = None
