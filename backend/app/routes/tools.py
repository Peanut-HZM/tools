from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.models import ToolsResponse, SearchResponse, CategoryResponse, Category, CategoryCreateRequest
from app.services.tools_service import tools_service
from app.services.system_monitor_service import get_system_info, get_resource_usage, get_process_list, kill_process

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


# ==================== 系统性能监控 ====================

@router.get("/system-monitor/info")
def get_system_info_endpoint():
    """获取系统基本信息"""
    try:
        return get_system_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.get("/system-monitor/usage")
def get_resource_usage_endpoint():
    """获取实时资源占用"""
    try:
        return get_resource_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资源占用失败: {str(e)}")


@router.get("/system-monitor/processes")
def get_process_list_endpoint(
    sort_by: str = Query("cpu_percent", description="排序字段: cpu_percent, memory_percent, pid, memory_rss, num_threads, name"),
    sort_order: str = Query("desc", description="排序方向: asc 或 desc"),
    search: Optional[str] = Query(None, description="搜索进程名"),
    project_type: Optional[str] = Query(None, description="项目类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=10, le=200, description="每页数量"),
):
    """获取进程列表（支持排序、搜索、项目类型过滤、分页）"""
    try:
        return get_process_list(
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            project_type=project_type,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程列表失败: {str(e)}")


@router.post("/system-monitor/processes/{pid}/kill")
def kill_process_endpoint(pid: int):
    """终止指定进程"""
    try:
        success = kill_process(pid)
        if not success:
            raise HTTPException(status_code=404, detail=f"进程 {pid} 不存在或无法终止")
        return {"success": True, "pid": pid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"终止进程失败: {str(e)}")
