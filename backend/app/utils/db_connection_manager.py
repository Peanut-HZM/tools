from typing import Dict, Optional, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
import logging
from app.utils.encryption import EncryptionUtils
from app.models.database_tool_models import DatabaseType

logger = logging.getLogger(__name__)


class DBConnectionManager:
    _engines: Dict[str, Engine] = {}

    @classmethod
    def get_engine(cls, config_id: str, config: Dict[str, Any]) -> Engine:
        """
        Get or create an SQLAlchemy engine for the given configuration.
        config dict must contain: db_type, host, port, database_name, username, password (encrypted or plain?)
        We assume 'password' in config is PLAINTEXT if passed here,
        OR if it's from DB, we might need to decrypt it before calling this.
        Better: The caller decrypts the password.
        """
        # Include database_name in the key to support switching databases
        db_name = config.get("database_name", "")
        engine_key = f"{config_id}:{db_name}"

        if engine_key in cls._engines:
            # Check if engine is still valid (optional)
            return cls._engines[engine_key]

        engine = cls._create_engine(config)
        cls._engines[engine_key] = engine
        return engine

    @classmethod
    def _create_engine(cls, config: Dict[str, Any]) -> Engine:
        db_type = config.get("db_type")
        user = config.get("username")
        password = config.get("password") or ""
        host = config.get("host")
        port = config.get("port")
        db_name = config.get("database_name")
        charset = config.get("charset", "utf8mb4")

        # URL 编码用户名和密码，防止特殊字符（如 @、:、/ 等）导致解析错误
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)

        url = ""
        connect_args = {}

        if db_type == DatabaseType.POSTGRESQL:
            # postgresql://user:password@host:port/dbname
            # If db_name is empty, connect to default 'postgres' database
            target_db = db_name if db_name else "postgres"
            url = f"postgresql://{encoded_user}:{encoded_password}@{host}:{port}/{target_db}"
            # PostgreSQL 超时配置
            connect_timeout = config.get("connect_timeout", 10)
            if connect_timeout:
                connect_args["connect_timeout"] = connect_timeout

        elif db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
            # mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4
            # If db_name is empty, connect without selecting a database
            target_db = f"/{db_name}" if db_name else ""
            url = f"mysql+pymysql://{encoded_user}:{encoded_password}@{host}:{port}{target_db}?charset={charset}"
            # PyMySQL 超时配置（通过 connect_args 传递）
            connect_timeout = config.get("connect_timeout", 10)
            if connect_timeout:
                connect_args["connect_timeout"] = connect_timeout
            # 读写超时：防止查询执行过程中卡死（默认 30 秒）
            connect_args["read_timeout"] = config.get("read_timeout", 30)
            connect_args["write_timeout"] = config.get("write_timeout", 30)
            logger.info(
                f"MySQL 连接配置: host={host}, port={port}, db={db_name}, "
                f"connect_timeout={connect_args.get('connect_timeout')}s, "
                f"read_timeout={connect_args.get('read_timeout')}s, "
                f"write_timeout={connect_args.get('write_timeout')}s"
            )

        elif db_type == DatabaseType.SQLITE:
            # sqlite:///path/to/db
            # For sqlite, host might be the path
            url = f"sqlite:///{host}"

        elif db_type == DatabaseType.SQLSERVER:
            # mssql+pymssql://user:password@host:port/dbname
            # If db_name is empty, connect to 'master'
            target_db = db_name if db_name else "master"
            url = f"mssql+pymssql://{encoded_user}:{encoded_password}@{host}:{port}/{target_db}"

        elif db_type == DatabaseType.ORACLE:
            # oracle+cx_oracle://user:password@host:port/?service_name=dbname
            if not db_name:
                raise ValueError("Database name (Service Name) is required for Oracle")
            url = f"oracle+cx_oracle://{encoded_user}:{encoded_password}@{host}:{port}/?service_name={db_name}"

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        try:
            # 连接池配置
            pool_size = config.get("max_pool_size", 10)
            pool_recycle = 3600  # 1 小时回收连接，配合 pool_pre_ping 防止使用过期连接
            max_overflow = config.get(
                "max_overflow", 20
            )  # 允许超出 pool_size 的最大连接数
            pool_timeout = config.get(
                "pool_timeout", 30
            )  # 从连接池获取连接的等待超时（秒）

            logger.info(
                f"创建数据库引擎: pool_size={pool_size}, max_overflow={max_overflow}, "
                f"pool_recycle={pool_recycle}s, pool_timeout={pool_timeout}s, "
                f"pool_pre_ping=True"
            )

            engine = create_engine(
                url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # 每次从连接池取连接前先 ping 检测，防止 2013 错误
                connect_args=connect_args,
            )
            return engine
        except Exception as e:
            logger.error(f"Failed to create engine: {e}")
            raise

    @classmethod
    def test_connection(cls, config: Dict[str, Any]) -> bool:
        """Test connection without caching the engine"""
        try:
            # Create a temporary engine
            # We don't want to use the pool for testing usually, but create_engine default is pooled.
            # It's fine for testing.
            engine = cls._create_engine(config)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Dispose engine
            engine.dispose()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise e  # Re-raise to let caller handle the error message

    @classmethod
    def close_engine(cls, config_id: str):
        """Close engine(s) for a config"""
        keys_to_remove = [
            k for k in cls._engines.keys() if k.startswith(f"{config_id}:")
        ]
        for key in keys_to_remove:
            if key in cls._engines:
                try:
                    cls._engines[key].dispose()
                except:
                    pass
                del cls._engines[key]
