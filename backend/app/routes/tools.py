from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.models import ToolsResponse, SearchResponse, CategoryResponse, Category, CategoryCreateRequest
from app.services.tools_service import tools_service

router = APIRouter(tags=["tools"])

@router.get("/categories", response_model=List[Category])
def get_categories():
    """获取所有工具分类"""
    return tools_service.get_all_categories()

@router.post("/categories", response_model=Category)
def create_category(request: CategoryCreateRequest):
    """创建工具分类"""
    try:
        category = tools_service.create_category(request)
        if not category:
            raise HTTPException(status_code=500, detail="Failed to create category")
        return category
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/categories/{cat_id}", response_model=Category)
def update_category(cat_id: str, request: CategoryCreateRequest):
    """更新工具分类"""
    try:
        category = tools_service.update_category(cat_id, request)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/categories/{cat_id}")
def delete_category(cat_id: str):
    """删除工具分类"""
    try:
        success = tools_service.delete_category(cat_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tools", response_model=ToolsResponse)
def get_tools(
    platform: Optional[str] = Query(None, description="平台过滤: pc 或 mobile"),
    category: Optional[str] = Query(None, description="分类过滤")
):
    """获取所有工具（支持 platform 和 category 过滤）"""
    tools = tools_service.get_tools_for_platform(platform, category)
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
