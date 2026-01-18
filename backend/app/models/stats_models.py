"""
Tool Statistics Models
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ToolStat(BaseModel):
    tool_id: str
    tool_name: str
    visit_count: int
    last_visited: datetime

class ToolVisitRequest(BaseModel):
    tool_id: str
    tool_name: str

class DashboardStats(BaseModel):
    total_tools: int
    total_visits: int
    popular_tools: List[ToolStat]
