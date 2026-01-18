from fastapi import APIRouter, Query
from app.models import ToolsResponse, SearchResponse, CategoryResponse
from app.services.tools_service import tools_service

router = APIRouter(tags=["tools"])

@router.get("/tools", response_model=ToolsResponse)
def get_tools():
    """获取所有工具"""
    tools = tools_service.get_all_tools(include_offline=False)
    return ToolsResponse(tools=tools)

@router.get("/tools/search", response_model=SearchResponse)
def search_tools_endpoint(q: str = Query(..., description="搜索关键词")):
    """搜索工具"""
    tools = tools_service.search_tools(q)
    return SearchResponse(tools=tools, count=len(tools))

@router.get("/tools/category/{category}", response_model=CategoryResponse)
def get_tools_by_category_endpoint(category: str):
    """按分类获取工具"""
    tools = tools_service.get_tools_by_category(category)
    return CategoryResponse(tools=tools, category=category)
