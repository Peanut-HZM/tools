from fastapi import APIRouter, HTTPException, Query
from app.services.holiday_service import get_holidays, list_cached_years
from app.services.lunar_service import get_month_lunar_data, get_or_calculate_lunar_data
from datetime import date, timedelta
from typing import List

router = APIRouter(prefix="/api/tools", tags=["calendar"])


@router.get("/holidays/{year}")
async def get_year_holidays(year: int):
    """
    获取指定年份的假期数据
    优先从本地缓存读取，没有则从远程获取并缓存
    """
    # 验证年份范围
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="年份必须在 2000-2100 之间")
    
    holidays = await get_holidays(year)
    
    if holidays is None:
        raise HTTPException(
            status_code=404, 
            detail=f"无法获取 {year} 年的假期数据，可能该年份数据尚未发布"
        )
    
    return holidays


@router.get("/holidays")
async def get_cached_years():
    """获取已缓存的年份列表"""
    years = list_cached_years()
    return {"cached_years": years}


@router.get("/lunar/{year}/{month}")
async def get_lunar_month(year: int, month: int):
    """
    获取指定年月的农历数据
    """
    if year < 1900 or year > 2100:
        raise HTTPException(status_code=400, detail="年份必须在 1900-2100 之间")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="月份必须在 1-12 之间")
    
    lunar_data = get_month_lunar_data(year, month)
    return {"lunar_data": lunar_data}


@router.get("/lunar/range")
async def get_lunar_range(
    start: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取日期范围内的农历数据
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
    
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    
    if (end_date - start_date).days > 100:
        raise HTTPException(status_code=400, detail="日期范围不能超过100天")
    
    result = []
    current = start_date
    while current <= end_date:
        lunar_data = get_or_calculate_lunar_data(current)
        if lunar_data:
            result.append(lunar_data)
        current = current + timedelta(days=1)
    
    return {"lunar_data": result}
