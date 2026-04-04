from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List

from app.models.resource_models import (
    UnifiedQuotaResponse, UnifiedHistoryResponse,
    DailyUsageResponse, DashboardSummary
)
from app.services.resource_management_service import resource_management_service
from app.middleware.auth_middleware import get_current_user_id

router = APIRouter(prefix="/resources", tags=["统一资源管理"])


@router.get("/quota", response_model=UnifiedQuotaResponse)
async def get_unified_quota(user_id: str = Depends(get_current_user_id)):
    """获取用户统一配额信息（所有工具汇总）"""
    try:
        return resource_management_service.get_unified_quota(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=UnifiedHistoryResponse)
async def get_unified_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    tool: Optional[str] = Query(None, description="工具过滤"),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户统一历史记录（跨工具查询）"""
    try:
        return resource_management_service.get_unified_history(
            user_id=user_id,
            page=page,
            page_size=page_size,
            tool_filter=tool
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage", response_model=DailyUsageResponse)
async def get_daily_usage(
    days: int = Query(7, ge=1, le=30, description="天数"),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户每日使用统计"""
    try:
        return resource_management_service.get_daily_usage(user_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(user_id: str = Depends(get_current_user_id)):
    """获取仪表板摘要"""
    try:
        return resource_management_service.get_dashboard_summary(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
