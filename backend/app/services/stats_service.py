"""
Statistics Service - Handles tool usage tracking
"""
import logging
from app.models.stats_models import DashboardStats
from app.services.tools_service import tools_service

logger = logging.getLogger(__name__)

class StatsService:
    """Service for tracking tool statistics"""
    
    def __init__(self):
        """Initialize StatsService"""
        pass
            
    def record_visit(self, tool_id: str, tool_name: str) -> bool:
        """Record a visit to a tool"""
        return tools_service.record_visit(tool_id)
        
    def get_dashboard_stats(self) -> DashboardStats:
        """Get aggregated dashboard statistics"""
        stats_data = tools_service.get_tool_stats()
        
        # Convert to DashboardStats model
        # Note: popular_tools dict keys match ToolStat model (tool_id, tool_name, visit_count, last_visited)
        # but we need to ensure types are correct.
        
        return DashboardStats(**stats_data)

# Singleton instance
stats_service = StatsService()
