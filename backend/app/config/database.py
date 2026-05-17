"""
数据库配置模块
"""
import os
from typing import Optional
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# 数据库配置（从环境变量读取）
from app.config.config import settings

DATABASE_URL = settings.DATABASE_URL

# 解析数据库URL
def parse_database_url(url: str) -> dict:
    """解析数据库URL"""
    # 格式: postgresql://user:password@host:port/database
    try:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "")
        
        # 分离认证信息和连接信息
        if "@" in url:
            auth_part, conn_part = url.split("@", 1)
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                # URL 解码密码（处理特殊字符如 *=%2A, #=%23）
                password = unquote(password)
            else:
                user = auth_part
                password = ""
        else:
            user = "postgres"
            password = ""
            conn_part = url
        
        # 分离主机和数据库
        if "/" in conn_part:
            host_part, database = conn_part.split("/", 1)
        else:
            host_part = conn_part
            database = "postgres"
        
        # 分离主机和端口
        if ":" in host_part:
            host, port = host_part.split(":", 1)
            port = int(port)
        else:
            host = host_part
            port = 5432
        
        return {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": database
        }
    except Exception as e:
        logger.error(f"解析数据库URL失败: {e}")
        raise


def get_db_config() -> dict:
    """获取数据库配置"""
    return parse_database_url(DATABASE_URL)


def get_db_connection():
    """获取数据库连接"""
    config = get_db_config()
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise


def test_connection() -> bool:
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False


# ============================================================
# 连接池支持
# ============================================================

_pool = None


def get_connection_pool(min_conn: int = 2, max_conn: int = 10):
    """获取或创建连接池（单例懒加载）"""
    global _pool
    if _pool is None:
        config = get_db_config()
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            cursor_factory=RealDictCursor,
        )
        logger.info(f"数据库连接池初始化完成 (min={min_conn}, max={max_conn})")
    return _pool


def get_pooled_db_connection():
    """从连接池获取连接"""
    pool = get_connection_pool()
    return pool.getconn()


def release_db_connection(conn):
    """释放连接回池"""
    pool = get_connection_pool()
    pool.putconn(conn)
