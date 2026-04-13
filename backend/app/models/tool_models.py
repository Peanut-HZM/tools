from pydantic import BaseModel
from typing import Optional, List

class Category(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Tool(BaseModel):
    id: str
    icon: str
    iconColor: str
    title: str
    description: str
    rating: float
    usageCount: str
    category: str  # Still using category name for now, or change to category_id? Let's keep name for compatibility but validate it.
    status: str = "online"
    sort_order: int = 0
    custom_icon_url: Optional[str] = None
    show_pc: bool = True
    show_mobile: bool = True
    created_at: Optional[str] = None

class ToolCreateRequest(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    iconColor: str
    category: str
    status: str = "online"

class CategoryCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0

class ToolsResponse(BaseModel):
    tools: List[Tool]

class SearchResponse(BaseModel):
    tools: List[Tool]
    count: int

class CategoryResponse(BaseModel):
    tools: List[Tool]
    category: str

class ToolUpdateRequest(BaseModel):
    """行编辑更新请求，所有字段可选"""
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    iconColor: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    show_pc: Optional[bool] = None
    show_mobile: Optional[bool] = None

class ToolsPaginatedResponse(BaseModel):
    tools: List[Tool]
    total: int
    page: int
    page_size: int
    total_pages: int

