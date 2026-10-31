"""
本地 SQLite 引擎与建表

关键约束：
1. 延迟创建 —— 不在应用启动时建库。服务器部署下绝大多数用户只用远程存储，
   不该为每人生成空 SQLite 文件；也避免只读磁盘导致整个应用启动失败。
2. 失败不降级 —— 本地库创建失败时抛明确异常，禁止降级到内存库
   （内存库会让用户以为配置已保存，重启即丢失）。
3. 关联表必须建 —— sql_execution_history 等表有外键依赖 db_configs，
   漏建会导致本地执行历史写入失败。
"""
import logging
from contextlib import contextmanager

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine

from app.storage.paths import get_local_db_path

logger = logging.getLogger(__name__)

metadata = MetaData()

# ============ 5 张主表（4 个工具的配置 + users） ============

users = Table(
    "users", metadata,
    Column("user_id", String(64), primary_key=True),
    Column("username", String(50), nullable=False),
    Column("email", String(100)),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(20), default="user"),
    Column("created_at", DateTime, server_default=func.now()),
)

db_configs = Table(
    "db_configs", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("alias", String(32), nullable=False),
    Column("db_type", String(20), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False),
    Column("database_name", String(255)),
    Column("username", String(100), nullable=False),
    Column("password_encrypted", Text, nullable=False),
    Column("environment", String(20)),
    Column("group_name", String(50)),
    Column("charset", String(50)),
    Column("connect_timeout", Integer, default=10),
    Column("max_pool_size", Integer, default=10),
    Column("ssl_mode", String(20)),
    Column("ssl_cert_path", Text),
    Column("extra_config", Text),
    Column("is_active", Boolean, default=True),
    Column("last_connected_at", DateTime),
    # 注意：不设 default —— 本地/远程共用同一份 Table 定义，
    # 默认值必须由 Repository 按实例绑定的位置注入（见 repository.py）
    Column("storage_location", String(16), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("deleted", Boolean, default=False),
)

k8s_connections = Table(
    "k8s_connections", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("name", String(128), nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("cluster_name", String(255), nullable=False),
    Column("context_name", String(255), nullable=False),
    Column("server", String(512), nullable=False),
    Column("auth_type", String(32), nullable=False),
    Column("auth_data_encrypted", Text),
    Column("ca_cert_encrypted", Text),
    Column("namespace_filter", Text, default="[]"),
    Column("is_metrics_available", Boolean, default=False),
    Column("last_test_at", DateTime),
    Column("last_test_error", Text),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("sort_order", Integer, default=0),
    Column("deleted", Boolean, default=False),
    Column("storage_location", String(16), nullable=False),
)

ssh_configs = Table(
    "ssh_configs", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("alias", String(64), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False, default=22),
    Column("username", String(128), nullable=False),
    Column("password_encrypted", Text),
    Column("private_key_encrypted", Text),
    Column("passphrase_encrypted", Text),
    Column("group_name", String(64)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("deleted", Boolean, default=False),
    Column("storage_location", String(16), nullable=False),
)

redis_configs = Table(
    "redis_configs", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("alias", String(64), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False),
    Column("username", String(128)),
    Column("password_encrypted", Text),
    Column("db", Integer, default=0),
    Column("group_name", String(64)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("deleted", Boolean, default=False),
    Column("storage_location", String(16), nullable=False),
)

# ============ 4 张关联表 ============

sql_execution_history = Table(
    "sql_execution_history", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("db_config_id", String(64), nullable=False),
    Column("sql_statement", Text, nullable=False),
    Column("sql_type", String(20)),
    Column("execution_status", String(20), nullable=False),
    Column("affected_rows", Integer),
    Column("execution_time_ms", Integer),
    Column("error_message", Text),
    Column("result_data", Text),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

db_scan_history = Table(
    "db_scan_history", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("db_config_id", String(64), nullable=False),
    Column("scan_result", Text),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

table_schema_cache = Table(
    "table_schema_cache", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("db_config_id", String(64), nullable=False),
    Column("schema_data", Text, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
)

user_display_preferences = Table(
    "user_display_preferences", metadata,
    Column("user_id", String(64), primary_key=True),
    Column("visible_connections", Text),
    Column("visible_databases", Text),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
)

# ============ 引擎管理 ============

_engine: Engine | None = None


def get_local_engine() -> Engine:
    """获取（延迟创建并缓存）本地 SQLite engine。

    失败时抛明确异常，禁止降级到内存库。
    """
    global _engine

    if _engine is not None:
        return _engine

    db_path = get_local_db_path()
    try:
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            pool_reset_on_return="rollback",
        )
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        raise RuntimeError(f"本地存储不可用：{db_path} —— {exc}") from exc

    _engine = engine
    logger.info("本地 SQLite 引擎已创建：%s", db_path)
    return engine


def reset_local_engine() -> None:
    """清空引擎缓存（测试隔离用）"""
    global _engine

    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_local_tables(engine: Engine | None = None) -> None:
    """幂等建表（可重复执行）"""
    target = engine or get_local_engine()
    metadata.create_all(bind=target)
    logger.info("本地 SQLite 表结构已就绪")


@contextmanager
def get_local_session():
    """本地库会话上下文管理器"""
    from sqlalchemy.orm import sessionmaker

    engine = get_local_engine()
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
