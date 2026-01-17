# Models package
from pydantic import BaseModel
from typing import Literal

# Tool models (from old models.py)
Category = Literal["全部工具", "文本工具", "转换工具", "计算工具", "设计工具", "实用工具"]

class Tool(BaseModel):
    id: str
    icon: str
    iconColor: str
    title: str
    description: str
    rating: float
    usageCount: str
    category: str

class ToolsResponse(BaseModel):
    tools: list[Tool]

class SearchResponse(BaseModel):
    tools: list[Tool]
    count: int

class CategoryResponse(BaseModel):
    tools: list[Tool]
    category: str

# Re-export from submodules
from app.models.auth_models import *
from app.models.file_models import *
from app.models.config_models import *
from app.models.search_models import *
