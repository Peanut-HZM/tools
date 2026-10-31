"""
远程 PostgreSQL 引擎适配

复用现有的 app.config.database 连接池（app/models/base.py 的 SQLAlchemy engine），
不新建连接池 —— 项目连接预算已统一收敛为一套。
"""
import logging

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def get_remote_engine() -> Engine:
    """获取远程 PG 的 SQLAlchemy engine（复用全局单例）"""
    from app.models.base import engine

    return engine


def remote_connection():
    """获取远程库的 SQLAlchemy 连接上下文管理器"""
    return get_remote_engine().begin()


def ensure_remote_column(table: str, column: str, ddl: str) -> bool:
    """幂等为远程表加列（可重复执行）"""
    from app.storage.ddl import ensure_column

    with get_remote_engine().begin() as conn:
        return ensure_column(conn, table, column, ddl)
