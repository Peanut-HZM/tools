from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date


class QuotaSummary(BaseModel):
    """单个工具的配额摘要"""
    tool_name: str = Field(..., description="工具名称")
    tool_display_name: str = Field(..., description="工具显示名称")
    daily_limit: int = Field(..., description="每日限制")
    daily_used: int = Field(..., description="每日已用")
    daily_remaining: int = Field(..., description="每日剩余")
    monthly_limit: int = Field(..., description="每月限制")
    monthly_used: int = Field(..., description="每月已用")
    monthly_remaining: int = Field(..., description="每月剩余")
    reset_date: datetime = Field(..., description="重置日期")


class UnifiedQuotaResponse(BaseModel):
    """统一配额响应"""
    user_id: str = Field(..., description="用户 ID")
    tools: List[QuotaSummary] = Field(..., description="各工具配额")
    total_daily_limit: int = Field(..., description="总每日限制")
    total_daily_used: int = Field(..., description="总每日已用")
    total_daily_remaining: int = Field(..., description="总每日剩余")
    total_monthly_limit: int = Field(..., description="总每月限制")
    total_monthly_used: int = Field(..., description="总每月已用")
    total_monthly_remaining: int = Field(..., description="总每月剩余")


class HistoryItem(BaseModel):
    """历史记录项"""
    id: str = Field(..., description="记录 ID")
    tool_name: str = Field(..., description="工具名称")
    operation_type: str = Field(..., description="操作类型")
    description: str = Field(..., description="操作描述")
    input_size: Optional[int] = Field(None, description="输入大小")
    output_size: Optional[int] = Field(None, description="输出大小")
    created_at: datetime = Field(..., description="创建时间")


class UnifiedHistoryResponse(BaseModel):
    """统一历史记录响应"""
    records: List[HistoryItem] = Field(..., description="历史记录列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="每页数量")


class UsageStatistics(BaseModel):
    """使用统计"""
    date: str = Field(..., description="日期")
    tool_name: str = Field(..., description="工具名称")
    operation_count: int = Field(..., description="操作次数")
    total_input_size: int = Field(..., description="总输入大小")
    total_output_size: int = Field(..., description="总输出大小")


class DailyUsageResponse(BaseModel):
    """每日使用统计响应"""
    user_id: str = Field(..., description="用户 ID")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    statistics: List[UsageStatistics] = Field(..., description="使用统计列表")


class DashboardSummary(BaseModel):
    """仪表板摘要"""
    user_id: str = Field(..., description="用户 ID")
    total_operations_today: int = Field(..., description="今日总操作数")
    most_used_tool: Optional[str] = Field(None, description="最常用工具")
    quota_usage_percentage: float = Field(..., description="配额使用百分比")
    tools_summary: List[QuotaSummary] = Field(..., description="工具配额摘要")
