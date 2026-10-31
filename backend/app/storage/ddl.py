"""
双方言幂等 DDL 辅助

背景：PostgreSQL 支持 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，
但 SQLite 不支持（实测 `ALTER TABLE t ADD COLUMN IF NOT EXISTS b INT`
报 `near "EXISTS": syntax error`）。故统一用「先探测、再加列」的方式，
两端通用且可重复执行。
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


def _is_postgres(conn) -> bool:
    """判断连接方言"""
    dialect = getattr(conn, "dialect", None)
    if dialect is not None:
        return dialect.name == "postgresql"
    return False


def column_exists(conn, table: str, column: str) -> bool:
    """判断列是否存在（PostgreSQL / SQLite 双方言）

    Args:
        conn: SQLAlchemy Connection
        table: 表名
        column: 列名

    Returns:
        列存在返回 True；表不存在也返回 False
    """
    if _is_postgres(conn):
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c LIMIT 1"
            ),
            {"t": table, "c": column},
        ).first()
        return row is not None

    # SQLite：PRAGMA table_info 返回 (cid, name, type, notnull, dflt_value, pk)
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def ensure_column(conn, table: str, column: str, ddl: str) -> bool:
    """幂等加列：列已存在则跳过。

    Args:
        conn: SQLAlchemy Connection
        table: 表名
        column: 列名
        ddl: ADD COLUMN 子句（不含表名与 ADD COLUMN 关键字），如
             "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'"

    Returns:
        True = 本次实际执行了加列；False = 列已存在，未执行
    """
    if column_exists(conn, table, column):
        return False

    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    conn.commit()
    logger.info("已为表 %s 添加列 %s", table, column)
    return True
