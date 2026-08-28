"""DbQueryTool — 数据库只读查询工具

参考 spec §6.6 内置工具清单
"""
import logging
import re
from typing import Any, Dict, List

from sqlalchemy import text

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)


# 危险 SQL 关键词（只读工具拒绝这些）
_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class DbQueryTool(BuiltinTool):
    """数据库只读查询工具"""

    name = "db_query"
    display_name = "数据库查询"
    description = "在数据库中执行只读 SQL 查询，返回结果。仅支持 SELECT 语句，禁止写操作。"
    parameters_schema = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "SELECT SQL 语句（禁止 INSERT/UPDATE/DELETE/DROP 等）",
            },
            "limit": {
                "type": "integer",
                "description": "最大返回行数",
                "default": 100,
                "maximum": 1000,
            },
        },
        "required": ["sql"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "columns": {"type": "array", "items": {"type": "string"}},
            "rows": {"type": "array"},
            "row_count": {"type": "integer"},
        },
    }

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        sql = args.get("sql", "").strip()
        if not sql:
            return ToolResult.error("sql 不能为空")

        limit = min(int(args.get("limit", 100)), 1000)

        # 安全检查：拒绝写操作
        if _WRITE_KEYWORDS.search(sql):
            return ToolResult.error(
                "这是只读查询工具，不允许 INSERT/UPDATE/DELETE/DROP 等写操作"
            )

        # 强制 SELECT 开头（剥离注释后判断，避免通过注释绕过）
        sql_clean = re.sub(
            r"--[^\n]*\n|/\*.*?\*/", " ", sql, flags=re.DOTALL
        ).strip()
        upper = sql_clean.upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            return ToolResult.error("只允许 SELECT / WITH ... SELECT 语句")

        if ctx.db is None:
            return ToolResult.error("数据库连接不可用")

        try:
            result = ctx.db.execute(text(sql))
            rows = result.fetchmany(limit)

            columns: List[str] = list(result.keys()) if result.returns_rows else []
            data: List[Dict[str, Any]] = [
                dict(zip(columns, row)) for row in rows
            ]

            return ToolResult.json(
                {"columns": columns, "rows": data, "row_count": len(data)},
                metadata={"sql": sql[:200], "limit": limit},
            )

        except Exception as e:
            logger.error("DbQueryTool 查询失败: %s", e, exc_info=True)
            return ToolResult.error(f"查询失败: {e}")
