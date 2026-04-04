import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import text

from app.models.resource_models import (
    QuotaSummary, UnifiedQuotaResponse,
    HistoryItem, UnifiedHistoryResponse,
    UsageStatistics, DailyUsageResponse,
    DashboardSummary
)

logger = logging.getLogger(__name__)


class ResourceManagementService:
    """统一资源管理服务"""

    # 工具配置
    TOOLS_CONFIG = {
        'ocr': {
            'display_name': 'OCR 文字识别',
            'quota_table': 'ocr_quota',
            'history_table': 'ocr_history',
            'daily_column': 'daily_used',
            'monthly_column': 'monthly_used'
        },
        'asr': {
            'display_name': 'ASR 语音识别',
            'quota_table': 'asr_quota',
            'history_table': 'asr_history',
            'daily_column': 'daily_used',
            'monthly_column': 'monthly_used'
        },
        'converter': {
            'display_name': '文档转换器',
            'quota_table': 'converter_quota',
            'history_table': 'converter_history',
            'daily_column': 'daily_used',
            'monthly_column': 'monthly_used'
        },
        'image_downloader': {
            'display_name': '图片下载器',
            'quota_table': 'image_quota',
            'history_table': 'image_history',
            'daily_column': 'daily_used',
            'monthly_column': 'monthly_used'
        },
        'json_tool': {
            'display_name': 'JSON 工具',
            'quota_table': 'json_quota',
            'history_table': 'json_history',
            'daily_column': 'daily_used',
            'monthly_column': 'monthly_used'
        },
        'database_tool': {
            'display_name': '数据库工具',
            'quota_table': None,  # 暂不设配额
            'history_table': 'database_tool_history',
            'daily_column': None,
            'monthly_column': None
        },
        'redis_tool': {
            'display_name': 'Redis 工具',
            'quota_table': None,
            'history_table': 'redis_tool_history',
            'daily_column': None,
            'monthly_column': None
        },
        'ssh_tool': {
            'display_name': 'SSH 工具',
            'quota_table': None,
            'history_table': 'ssh_tool_history',
            'daily_column': None,
            'monthly_column': None
        }
    }

    def __init__(self, db_session=None):
        self.db_session = db_session

    def _get_db(self):
        """获取数据库连接"""
        if self.db_session:
            return self.db_session
        from app.database.db import get_db
        from sqlalchemy.orm import Session
        return Session(next(get_db()))

    def get_unified_quota(self, user_id: str) -> UnifiedQuotaResponse:
        """获取用户统一配额信息"""
        db = self._get_db()
        tools_summary = []
        total_daily_limit = 0
        total_daily_used = 0
        total_daily_remaining = 0
        total_monthly_limit = 0
        total_monthly_used = 0
        total_monthly_remaining = 0

        for tool_name, config in self.TOOLS_CONFIG.items():
            if not config['quota_table']:
                continue

            try:
                result = db.execute(text(f"""
                    SELECT daily_limit, daily_used, monthly_limit, monthly_used, daily_reset_date
                    FROM {config['quota_table']}
                    WHERE user_id = :user_id
                """), {'user_id': user_id}).first()

                if result:
                    daily_limit = result.daily_limit or 0
                    daily_used = result.daily_used or 0
                    monthly_limit = result.monthly_limit or 0
                    monthly_used = result.monthly_used or 0
                    daily_remaining = daily_limit - daily_used
                    monthly_remaining = monthly_limit - monthly_used
                    reset_date = result.daily_reset_date or datetime.now()

                    tools_summary.append(QuotaSummary(
                        tool_name=tool_name,
                        tool_display_name=config['display_name'],
                        daily_limit=daily_limit,
                        daily_used=daily_used,
                        daily_remaining=daily_remaining,
                        monthly_limit=monthly_limit,
                        monthly_used=monthly_used,
                        monthly_remaining=monthly_remaining,
                        reset_date=reset_date
                    ))

                    total_daily_limit += daily_limit
                    total_daily_used += daily_used
                    total_daily_remaining += daily_remaining
                    total_monthly_limit += monthly_limit
                    total_monthly_used += monthly_used
                    total_monthly_remaining += monthly_remaining

            except Exception as e:
                logger.warning(f"Failed to get quota for {tool_name}: {e}")

        return UnifiedQuotaResponse(
            user_id=user_id,
            tools=tools_summary,
            total_daily_limit=total_daily_limit,
            total_daily_used=total_daily_used,
            total_daily_remaining=total_daily_remaining,
            total_monthly_limit=total_monthly_limit,
            total_monthly_used=total_monthly_used,
            total_monthly_remaining=total_monthly_remaining
        )

    def get_unified_history(self, user_id: str, page: int = 1, page_size: int = 50,
                            tool_filter: Optional[str] = None) -> UnifiedHistoryResponse:
        """获取用户统一历史记录"""
        db = self._get_db()
        offset = (page - 1) * page_size

        # 构建 UNION ALL 查询
        queries = []
        for tool_name, config in self.TOOLS_CONFIG.items():
            if tool_filter and tool_name != tool_filter:
                continue
            if not config['history_table']:
                continue

            # 根据不同工具构建查询
            if tool_name == 'ocr':
                query = text(f"""
                    SELECT id, '{tool_name}' as tool_name, 'ocr' as operation_type,
                           original_file_name as description, file_size as input_size,
                           output_size, created_at
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                """)
            elif tool_name == 'asr':
                query = text(f"""
                    SELECT id, '{tool_name}' as tool_name, 'asr' as operation_type,
                           original_audio_url as description, file_size as input_size,
                           NULL as output_size, created_at
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                """)
            elif tool_name == 'converter':
                query = text(f"""
                    SELECT id, '{tool_name}' as tool_name, 'convert' as operation_type,
                           original_file_name as description, file_size as input_size,
                           output_size, created_at
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                """)
            elif tool_name == 'image_downloader':
                query = text(f"""
                    SELECT id, '{tool_name}' as tool_name, 'download' as operation_type,
                           filename as description, file_size as input_size,
                           NULL as output_size, created_at
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                """)
            elif tool_name == 'json_tool':
                query = text(f"""
                    SELECT id, '{tool_name}' as tool_name, operation_type,
                           operation_type as description, input_size,
                           output_size, created_at
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                """)
            else:
                continue

            queries.append(query)

        if not queries:
            return UnifiedHistoryResponse(records=[], total=0, page=page, page_size=page_size)

        # 合并查询
        union_query = " UNION ALL ".join([f"({q})" for q in queries])
        union_query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        # 获取总数
        count_query = f"SELECT COUNT(*) FROM ({' UNION ALL '.join([f'({q})' for q in queries])}) as all_history"
        total_result = db.execute(text(count_query), {'user_id': user_id}).scalar()

        # 获取分页数据
        result = db.execute(text(union_query), {
            'user_id': user_id,
            'limit': page_size,
            'offset': offset
        })

        records = []
        for row in result:
            records.append(HistoryItem(
                id=row.id,
                tool_name=row.tool_name,
                operation_type=row.operation_type,
                description=row.description or f"{row.operation_type} operation",
                input_size=row.input_size,
                output_size=row.output_size,
                created_at=row.created_at
            ))

        return UnifiedHistoryResponse(
            records=records,
            total=total_result or 0,
            page=page,
            page_size=page_size
        )

    def get_daily_usage(self, user_id: str, days: int = 7) -> DailyUsageResponse:
        """获取用户每日使用统计"""
        db = self._get_db()
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        statistics = []

        for tool_name, config in self.TOOLS_CONFIG.items():
            if not config['history_table']:
                continue

            try:
                result = db.execute(text(f"""
                    SELECT DATE(created_at) as stat_date,
                           COUNT(*) as operation_count,
                           COALESCE(SUM(input_size), 0) as total_input_size,
                           COALESCE(SUM(output_size), 0) as total_output_size
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND DATE(created_at) BETWEEN :start_date AND :end_date
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                    GROUP BY DATE(created_at)
                    ORDER BY stat_date
                """), {
                    'user_id': user_id,
                    'start_date': start_date,
                    'end_date': end_date
                })

                for row in result:
                    statistics.append(UsageStatistics(
                        date=str(row.stat_date),
                        tool_name=tool_name,
                        operation_count=row.operation_count,
                        total_input_size=row.total_input_size or 0,
                        total_output_size=row.total_output_size or 0
                    ))

            except Exception as e:
                logger.warning(f"Failed to get daily usage for {tool_name}: {e}")

        return DailyUsageResponse(
            user_id=user_id,
            start_date=str(start_date),
            end_date=str(end_date),
            statistics=statistics
        )

    def get_dashboard_summary(self, user_id: str) -> DashboardSummary:
        """获取仪表板摘要"""
        # 获取配额信息
        quota_response = self.get_unified_quota(user_id)

        # 计算今日总操作数
        db = self._get_db()
        today = date.today()

        total_operations = 0
        tool_operations = {}

        for tool_name, config in self.TOOLS_CONFIG.items():
            if not config['history_table']:
                continue

            try:
                result = db.execute(text(f"""
                    SELECT COUNT(*) as cnt
                    FROM {config['history_table']}
                    WHERE user_id = :user_id
                      AND DATE(created_at) = :today
                      AND (is_deleted IS NULL OR is_deleted = FALSE)
                """), {'user_id': user_id, 'today': today}).scalar()

                if result:
                    total_operations += result
                    tool_operations[tool_name] = result

            except Exception as e:
                logger.warning(f"Failed to count operations for {tool_name}: {e}")

        # 找出最常用工具
        most_used_tool = None
        if tool_operations:
            most_used_tool = max(tool_operations, key=tool_operations.get)

        # 计算配额使用百分比
        quota_percentage = 0.0
        if quota_response.total_daily_limit > 0:
            quota_percentage = round(
                (quota_response.total_daily_used / quota_response.total_daily_limit) * 100,
                2
            )

        return DashboardSummary(
            user_id=user_id,
            total_operations_today=total_operations,
            most_used_tool=most_used_tool,
            quota_usage_percentage=quota_percentage,
            tools_summary=quota_response.tools
        )


resource_management_service = ResourceManagementService()
