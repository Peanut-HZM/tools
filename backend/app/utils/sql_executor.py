import re
from typing import Dict, Any, List, Optional
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.utils.db_connection_manager import DBConnectionManager
from app.models.database_tool_models import SQLExecutionResult
import time
import logging
import datetime
import sqlparse

logger = logging.getLogger(__name__)

# 允许的 SQL 关键字白名单（含会话控制语句 PREPARE/EXECUTE/DEALLOCATE 等）
SQL_KEYWORDS = {
    'SELECT', 'INSERT', 'UPDATE', 'DELETE',
    'CREATE', 'ALTER', 'DROP', 'TRUNCATE',
    'SET', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN',
    'BEGIN', 'START', 'COMMIT', 'ROLLBACK', 'SAVEPOINT',
    'PREPARE', 'EXECUTE', 'DEALLOCATE',
    'CALL', 'USE', 'LOCK', 'UNLOCK',
    'GRANT', 'REVOKE', 'FLUSH', 'OPTIMIZE', 'ANALYZE',
    'REPLACE', 'MERGE', 'LOAD', 'HANDLER',
}

# 用于剥离 SQL 注释但保留字符串字面量的正则（含 '' / "" 转义识别）
_STRIP_COMMENTS_RE = re.compile(
    r"""('(?:[^'\\]|\\.|'')*')"""
    r"""|("(?:[^"\\]|\\.|(?:""))*")"""
    r"""|(--[^\r\n]*)"""
    r"""|(/\*[\s\S]*?\*/)""",
    re.DOTALL,
)


def strip_sql_comments(raw: str) -> str:
    """剥离 SQL 注释（行注释 -- 与块注释 /* */），保留字符串字面量内容"""
    def _replace(m):
        if m.group(1) or m.group(2):
            return m.group(0)
        return ''
    return _STRIP_COMMENTS_RE.sub(_replace, raw)


# 扫描状态机状态常量：正常 / 单引号字符串 / 双引号字符串 / 反引号标识符 / 行注释 / 块注释
_STATE_NORMAL = 'NORMAL'
_STATE_SQ = 'SQ'
_STATE_DQ = 'DQ'
_STATE_BT = 'BT'
_STATE_LC = 'LC'
_STATE_BC = 'BC'


def _advance_scan_state(sql: str, i: int, state: str) -> tuple:
    """字符级扫描状态机前进一步，返回 (新状态, 新位置)。

    指令与终止符只在 NORMAL 状态识别；字符串/注释内的 DELIMITER、分号、
    自定义终止符一律视为字面量。
    """
    ch = sql[i]
    two = sql[i:i + 2]
    if state == _STATE_NORMAL:
        if ch == "'":
            return _STATE_SQ, i + 1
        if ch == '"':
            return _STATE_DQ, i + 1
        if ch == '`':
            return _STATE_BT, i + 1
        if two == '--' and (i + 2 >= len(sql) or sql[i + 2] in ' \t\r\n'):
            return _STATE_LC, i + 2
        if ch == '#':
            return _STATE_LC, i + 1
        if two == '/*':
            return _STATE_BC, i + 2
        return _STATE_NORMAL, i + 1
    if state == _STATE_SQ:
        if ch == '\\':
            return _STATE_SQ, i + 2
        if ch == "'" and sql[i + 1:i + 2] == "'":
            return _STATE_SQ, i + 2
        if ch == "'":
            return _STATE_NORMAL, i + 1
        return _STATE_SQ, i + 1
    if state == _STATE_DQ:
        if ch == '\\':
            return _STATE_DQ, i + 2
        if ch == '"' and sql[i + 1:i + 2] == '"':
            return _STATE_DQ, i + 2
        if ch == '"':
            return _STATE_NORMAL, i + 1
        return _STATE_DQ, i + 1
    if state == _STATE_BT:
        if ch == '`' and sql[i + 1:i + 2] == '`':
            return _STATE_BT, i + 2
        if ch == '`':
            return _STATE_NORMAL, i + 1
        return _STATE_BT, i + 1
    if state == _STATE_LC:
        if ch == '\n':
            return _STATE_NORMAL, i + 1
        return _STATE_LC, i + 1
    # _STATE_BC
    if two == '*/':
        return _STATE_NORMAL, i + 2
    return _STATE_BC, i + 1


def _split_by_terminator(segment: str, terminator: str) -> list:
    """自定义终止符 segment 内按终止符切分语句（仅 NORMAL 状态匹配）。

    与 mysql CLI 语义一致：自定义终止符生效期间分号不结束语句；
    EOF 余留的非空白内容作为一条语句。
    """
    statements = []
    buf = []
    state = _STATE_NORMAL
    i = 0
    while i < len(segment):
        if state == _STATE_NORMAL and segment.startswith(terminator, i):
            statements.append(''.join(buf))
            buf = []
            i += len(terminator)
            continue
        start = i
        state, i = _advance_scan_state(segment, i, state)
        buf.append(segment[start:i])
    remainder = ''.join(buf)
    if remainder.strip():
        statements.append(remainder)
    return [s for s in statements if s.strip()]


# DELIMITER 指令：独占一行、大小写不敏感、形如 DELIMITER <终止符>
_DELIMITER_DIRECTIVE_RE = re.compile(
    r'^[ \t]*DELIMITER[ \t]+(\S+)[ \t]*(?:\r?\n)?$', re.IGNORECASE
)


def _split_segments(sql: str) -> list:
    """按 DELIMITER 指令行把脚本切成 (segment 文本, 生效终止符) 列表。

    指令行本身不进入任何 segment；指令仅在整行处于 NORMAL 状态时识别。
    """
    segments = []
    segment_buf = []
    line_buf = []
    line_all_normal = True
    terminator = ';'
    state = _STATE_NORMAL
    i = 0
    while i < len(sql):
        start = i
        state, i = _advance_scan_state(sql, i, state)
        ch = sql[start]
        line_buf.append(sql[start:i])
        if state != _STATE_NORMAL:
            line_all_normal = False
        if ch == '\n' or i >= len(sql):
            raw_line = ''.join(line_buf)
            directive = (
                _DELIMITER_DIRECTIVE_RE.match(raw_line)
                if line_all_normal and state == _STATE_NORMAL
                else None
            )
            if directive:
                segments.append((''.join(segment_buf), terminator))
                segment_buf = []
                terminator = directive.group(1)
            else:
                segment_buf.extend(line_buf)
            line_buf = []
            line_all_normal = state == _STATE_NORMAL
    segments.append((''.join(segment_buf), terminator))
    return segments


# 切分后仍以 DELIMITER 开头的语句 = 非标准写法（行中指令、缺参数等）
_DELIMITER_LEFTOVER_RE = re.compile(r'^DELIMITER(\s|$)', re.IGNORECASE)

_DELIMITER_ERROR_MESSAGE = (
    'DELIMITER 是 mysql 客户端指令，仅支持独占一行的写法：DELIMITER <终止符>'
)


def split_sql_script(sql: str) -> list:
    """把 SQL 脚本切分为语句列表（感知 mysql 客户端 DELIMITER 指令）。

    默认 ';' 终止符的 segment 委托 sqlparse.split（保留 BEGIN...END 不切语义）；
    自定义终止符的 segment 按终止符直接切断、段内不二次切分。
    非标准 DELIMITER 写法抛 ValueError（中文消息）。
    """
    statements = []
    for segment_text, terminator in _split_segments(sql):
        if not segment_text.strip():
            continue
        if terminator == ';':
            statements.extend(sqlparse.split(segment_text))
        else:
            statements.extend(_split_by_terminator(segment_text, terminator))
    for stmt in statements:
        if _DELIMITER_LEFTOVER_RE.match(strip_sql_comments(stmt).strip()):
            raise ValueError(_DELIMITER_ERROR_MESSAGE)
    return [s for s in statements if s.strip()]


def is_executable_statement(stmt: str) -> bool:
    """判断一条语句是否包含可执行的 SQL 关键字（注释剥离后再判定）"""
    stripped = stmt.strip()
    if not stripped or stripped == ';':
        return False
    upper_no_comments = strip_sql_comments(stripped).upper()
    return any(kw in upper_no_comments for kw in SQL_KEYWORDS)


class SQLExecutor:
    @staticmethod
    def execute(
        config_id: str,
        config: Dict[str, Any],
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> SQLExecutionResult:
        start_time = time.time()
        engine = DBConnectionManager.get_engine(config_id, config)

        try:
            with engine.connect() as conn:
                # 切分 SQL 为多条语句，过滤空/纯注释/无合法关键字的语句
                statements = [
                    s for s in split_sql_script(sql)
                    if is_executable_statement(s)
                ]

                if not statements:
                    return SQLExecutionResult(
                        success=True, execution_time_ms=0, affected_rows=0
                    )

                last_result = None
                total_affected = 0

                # Execute all statements
                for i, stmt_str in enumerate(statements):
                    # Skip empty statements that might remain
                    if not stmt_str.strip():
                        continue

                    # ------------------------------------------------------------------
                    # 百分号处理策略
                    # ------------------------------------------------------------------
                    # SQLAlchemy 2.0 text() 编译器始终将 % 翻倍为 %%（DBAPI pyformat 转义）。
                    # DBAPI 层（cursor.execute）只在有参数时执行 sql % params，把 %% 还原为 %。
                    # 当无参数时，DBAPI 不做 % 处理，编译后的 %% 会原样发送到数据库。
                    #
                    # 因此：
                    #   有 params：不做任何预处理。编译器 % → %% 后由 DBAPI % 操作还原。
                    #   无 params：先让编译器 % → %%，再撤销 %% → %，抵消编译器多余的转义。
                    #
                    # 旧代码 replace("%", "%%") 导致双重翻倍：
                    #   %(1x) → replace %(2x) → compile %(4x) → DBAPI(无处理) → DB 看到 %%%%
                    # ------------------------------------------------------------------

                    if not params:
                        # 无 params：DBAPI 不会执行 % 操作，必须手动撤销编译器的 %% 转义

                        # 步骤 1: 先转义冒号，防止 text() 把 JSON 的 :key 当作绑定参数
                        # （\: 是 SQLAlchemy 的字面冒号转义；保留 :: 即 PG 类型转换）
                        stmt_with_escaped_colons = re.sub(
                            r'(?<!:)(?<!\\):([a-zA-Z_]\w*|\d+)',
                            r'\\:\1',
                            stmt_str,
                        )

                        # 步骤 2: 编译（编译器把 % → %%），然后撤销 %% → %
                        # 最终结果：用户输入 %，DB 看到 %（LIKE 通配符正确）
                        compiled = text(stmt_with_escaped_colons).compile(
                            dialect=engine.dialect
                        )
                        final_sql = str(compiled).replace('%%', '%')
                        stmt = text(final_sql)
                    else:
                        # 有 params：完整处理链会自动还原 %
                        # 编译器 % → %%，DBAPI 执行 sql % params 时 %% → %
                        stmt = text(stmt_str)

                    # Execute
                    if params:
                        result = conn.execute(stmt, params)
                    else:
                        result = conn.execute(stmt)

                    if not result.returns_rows:
                        total_affected += result.rowcount

                    last_result = result

                # Commit transaction
                conn.commit()

                execution_time = (time.time() - start_time) * 1000

                if last_result and last_result.returns_rows:
                    # Fetch results from the last query
                    columns = list(last_result.keys())
                    rows = [dict(row._mapping) for row in last_result.fetchall()]

                    # Handle serialization
                    serialized_rows = []
                    for row in rows:
                        new_row = {}
                        for k, v in row.items():
                            if isinstance(v, (datetime.datetime, datetime.date)):
                                new_row[k] = v.isoformat()
                            elif isinstance(v, Decimal):
                                new_row[k] = float(v)
                            elif isinstance(v, int) and abs(v) > 9007199254740991:
                                new_row[k] = str(v)
                            else:
                                new_row[k] = v
                        serialized_rows.append(new_row)

                    return SQLExecutionResult(
                        success=True,
                        sql_type="SELECT",
                        affected_rows=len(serialized_rows),
                        execution_time_ms=execution_time,
                        result_data=serialized_rows,
                        columns=columns,
                    )
                else:
                    # DML/DDL
                    return SQLExecutionResult(
                        success=True,
                        sql_type="DML/DDL",
                        affected_rows=total_affected,
                        execution_time_ms=execution_time,
                    )

        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            execution_time = (time.time() - start_time) * 1000
            return SQLExecutionResult(
                success=False, execution_time_ms=execution_time, error_message=str(e)
            )
