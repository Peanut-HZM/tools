"""DbQueryTool — 数据库只读查询工具（安全加固版）

参考 spec §6.6 内置工具清单

安全加固（2026-08-29）:
- 使用 sqlparse 解析 SQL，防止正则绕过
- 阻止危险 PostgreSQL 函数（dblink_exec / lo_import / pg_read_file 等）
- 阻止 INTO 子句（防止 INSERT INTO ... SELECT 绕过）
- 阻止 COPY / DDL 语句
- 表级别 allowlist / blocklist 访问控制
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Function, Parenthesis
from sqlparse.tokens import DML, Keyword

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)


# 危险 SQL 关键词（只读工具拒绝这些）— 作为第一道防线保留
_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

# 危险 PostgreSQL 函数（即使包裹在 SELECT 里也能执行写操作或读文件）
_DANGEROUS_FUNCTIONS = {
    # 写操作 / 远程执行
    "dblink_exec",
    "dblink_send_query",
    # 文件系统读取
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_ls_logdir",
    "pg_ls_waldir",
    "pg_ls_archive_statusdir",
    # 大对象（可绕过表权限）
    "lo_import",
    "lo_export",
    "lo_creat",
    "lo_create",
    "lo_unlink",
    # COPY 相关
    "copy_to",
    "copy_from",
    # 服务端执行
    "pg_backend_cancel",
    "pg_terminate_backend",
    "pg_cancel_backend",
    # 配置/信息泄露
    "pg_read_all_settings",
    "pg_read_all_stats",
    "pg_stat_file",
    # 动态 SQL 执行（可注入写操作）
    "exec",
    "execute",
}

_DANGEROUS_FUNC_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(f) for f in _DANGEROUS_FUNCTIONS) + r")\s*\(",
    re.IGNORECASE,
)

# INTO 子句检测（INSERT INTO ... SELECT 绕过）
_INTO_PATTERN = re.compile(
    r"\bINTO\b",
    re.IGNORECASE,
)

# COPY 语句
_COPY_PATTERN = re.compile(
    r"^\s*COPY\b",
    re.IGNORECASE,
)


def _strip_sql_comments(sql: str) -> str:
    """去除 SQL 注释（行注释 -- 和块注释 /* */）

    行注释匹配到行尾或字符串末尾，兼容 .strip() 去除尾部换行后的情况。
    """
    return re.sub(r"--[^\n]*(?:\n|$)|/\*.*?\*/", " ", sql, flags=re.DOTALL).strip()


def _extract_table_names(parsed_statement) -> Set[str]:
    """从 sqlparse 解析的 statement 中提取表名

    处理 FROM / JOIN 后的 Identifier 和 IdentifierList。
    返回小写表名集合。
    """
    tables: Set[str] = set()
    _from_seen = False

    for token in parsed_statement.tokens:
        # 检测 FROM / JOIN keyword
        if token.ttype is Keyword and token.normalized.upper() in (
            "FROM", "JOIN", "INNER JOIN", "LEFT JOIN",
            "RIGHT JOIN", "FULL JOIN", "CROSS JOIN",
            "LEFT OUTER JOIN", "RIGHT OUTER JOIN", "FULL OUTER JOIN",
        ):
            _from_seen = True
            continue

        if _from_seen:
            if token.is_whitespace:
                continue
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    name = identifier.get_real_table_name()
                    if name:
                        tables.add(name.lower())
                _from_seen = False
            elif isinstance(token, Identifier):
                name = token.get_real_table_name()
                if name:
                    tables.add(name.lower())
                _from_seen = False
            elif token.ttype is not None:
                # 遇到非标识符的 token（如逗号、WHERE），停止提取
                _from_seen = False

    # 也检查 subqueries（Parenthesis 中的 SELECT）
    for token in parsed_statement.flatten():
        pass  # flatten 不保留结构，跳过

    return tables


def _extract_table_names_robust(sql_clean: str) -> Set[str]:
    """从清理后的 SQL 中用正则提取表名（作为 sqlparse 的补充）

    匹配 FROM/JOIN 后的标识符（含 schema.table 格式）。
    """
    tables: Set[str] = set()
    # 匹配 FROM/JOIN 后面的表名（可选 schema.table）
    pattern = re.compile(
        r"""\b(?:FROM|JOIN|INNER\s+JOIN|LEFT\s+(?:OUTER\s+)?JOIN|"""
        r"""RIGHT\s+(?:OUTER\s+)?JOIN|FULL\s+(?:OUTER\s+)?JOIN|CROSS\s+JOIN)"""
        r"""\s+("?)(\w+)\1(?:\s*\.\s*("?)(\w+)\3)?""",
        re.IGNORECASE,
    )
    for m in pattern.finditer(sql_clean):
        schema = m.group(2)
        table = m.group(4)
        if table:
            # schema.table 格式
            tables.add(f"{schema.lower()}.{table.lower()}")
            tables.add(table.lower())
        else:
            tables.add(schema.lower())
    return tables


def _validate_sql_select_only(sql: str) -> Optional[str]:
    """验证 SQL 只包含安全的只读 SELECT 查询

    返回 None 表示通过，返回字符串表示失败原因。
    """
    # 第一道防线：正则关键词
    if _WRITE_KEYWORDS.search(sql):
        return "检测到写操作关键词（INSERT/UPDATE/DELETE/DROP 等）"

    if _COPY_PATTERN.search(sql):
        return "不允许 COPY 语句"

    if _DANGEROUS_FUNC_PATTERN.search(sql):
        return "检测到危险的数据库函数调用"

    # 第二道防线：sqlparse 解析验证
    try:
        parsed = sqlparse.parse(sql)
    except Exception as e:
        return f"SQL 解析失败: {e}"

    if not parsed:
        return "SQL 为空"

    for statement in parsed:
        # 跳过空语句
        stmt_type = statement.get_type()
        if stmt_type is None:
            # sqlparse 无法识别类型时，做进一步检查
            stripped = str(statement).strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if not (upper.startswith("SELECT") or upper.startswith("WITH")):
                return f"不允许的 SQL 语句类型: {stripped[:50]}"
        elif stmt_type.upper() not in ("SELECT", "UNKNOWN"):
            return f"不允许的 SQL 语句类型: {stmt_type}"

        # 检查 INTO 子句（防止 INSERT INTO ... SELECT 绕过）
        stmt_upper = str(statement).upper()
        # SELECT ... INTO 或 INSERT INTO 都应阻止
        if _INTO_PATTERN.search(stmt_upper):
            # 排除 SELECT INTO 在变量声明中的合法用法（PL/pgSQL）
            # 但在普通 SQL 查询中，INTO 几乎总是写操作
            return "不允许 INTO 子句（防止写操作绕过）"

        # 检查是否包含 UNNEST + 写操作的组合
        # sqlparse 的 get_type() 对复杂 CTE 可能返回 UNKNOWN
        if stmt_type and stmt_type.upper() == "UNKNOWN":
            # 对于 UNKNOWN 类型，确保核心仍是 SELECT
            first_keyword = None
            for token in statement.tokens:
                if token.ttype is DML:
                    first_keyword = token.normalized.upper()
                    break
                if token.ttype is Keyword and token.normalized.upper() in (
                    "WITH", "SELECT",
                ):
                    first_keyword = token.normalized.upper()
                    break
            if first_keyword and first_keyword not in ("SELECT", "WITH"):
                return f"不允许的 SQL 语句: {first_keyword}"

    return None


class DbQueryTool(BuiltinTool):
    """数据库只读查询工具（安全加固版）

    安全措施:
    1. sqlparse 解析验证，只允许 SELECT 语句
    2. 阻止危险 PostgreSQL 函数
    3. 阻止 INTO 子句
    4. 表级别 allowlist / blocklist
    5. 强制行数限制

    重要: 此工具应部署为只读数据库用户。表级别控制是额外防线，
    不能替代数据库层面的权限控制。
    """

    name = "db_query"
    display_name = "数据库查询"
    description = (
        "在数据库中执行只读 SQL 查询，返回结果。"
        "仅支持 SELECT 语句，禁止写操作。"
        "受表级别访问控制保护。"
    )
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

    def __init__(
        self,
        config: dict = None,
        allowed_schemas: Optional[List[str]] = None,
        allowed_tables: Optional[List[str]] = None,
        blocked_tables: Optional[List[str]] = None,
    ):
        super().__init__(config)
        self.allowed_schemas = [s.lower() for s in (allowed_schemas or ["public"])]
        self.allowed_tables = (
            {t.lower() for t in allowed_tables} if allowed_tables else None
        )
        self.blocked_tables = {
            t.lower() for t in (blocked_tables or ["users", "sessions", "api_keys", "secrets"])
        }

    def _check_table_access(self, sql: str) -> Optional[str]:
        """检查 SQL 中引用的表是否在允许范围内

        返回 None 表示通过，返回字符串表示失败原因。
        """
        sql_clean = _strip_sql_comments(sql)

        # 用两种方式提取表名，取并集
        tables: Set[str] = set()

        # 方法 1: sqlparse
        try:
            parsed = sqlparse.parse(sql_clean)
            for stmt in parsed:
                tables |= _extract_table_names(stmt)
        except Exception:
            pass

        # 方法 2: 正则（作为补充）
        tables |= _extract_table_names_robust(sql_clean)

        if not tables:
            # 无法提取表名（可能是 SELECT 1 这样的表达式），放行
            return None

        for table in tables:
            # 去掉 schema 前缀，用纯表名检查
            bare_table = table.split(".")[-1] if "." in table else table

            # 检查 blocklist
            if bare_table in self.blocked_tables or table in self.blocked_tables:
                return f"Access denied: table '{bare_table}' is blocked"

            # 检查 allowed_tables（如果设置了）
            if self.allowed_tables is not None:
                if bare_table not in self.allowed_tables and table not in self.allowed_tables:
                    return f"Access denied: table '{bare_table}' is not in the allowlist"

            # 检查 schema（仅对带 schema 前缀的表名）
            if "." in table:
                schema = table.split(".")[0]
                if schema not in self.allowed_schemas:
                    return f"Access denied: schema '{schema}' is not allowed"

        return None

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        sql = args.get("sql", "").strip()
        if not sql:
            return ToolResult.error("sql 不能为空")

        limit = min(int(args.get("limit", 100)), 1000)

        # 去除注释后检查
        sql_clean = _strip_sql_comments(sql)
        if not sql_clean:
            return ToolResult.error("sql 不能为空")

        # 安全检查 1: 验证 SQL 是只读 SELECT
        validation_error = _validate_sql_select_only(sql_clean)
        if validation_error:
            logger.warning("DbQueryTool SQL 验证失败: %s | SQL: %.200s", validation_error, sql)
            return ToolResult.error(f"SQL 验证失败: {validation_error}")

        # 安全检查 2: 表级别访问控制
        table_error = self._check_table_access(sql_clean)
        if table_error:
            logger.warning("DbQueryTool 表访问被拒: %s | SQL: %.200s", table_error, sql)
            return ToolResult.error(table_error)

        if ctx.db is None:
            return ToolResult.error("数据库连接不可用")

        try:
            from sqlalchemy import text as sa_text
            result = ctx.db.execute(sa_text(sql))
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
