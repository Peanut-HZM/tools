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

