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


def get_connection_pool(min_conn: Optional[int] = None, max_conn: Optional[int] = None):
    """获取或创建连接池（单例懒加载）"""
    global _pool
    if _pool is None:
        min_conn = min_conn if min_conn is not None else settings.DB_PSYCOPG_POOL_MIN_CONN
        max_conn = max_conn if max_conn is not None else settings.DB_PSYCOPG_POOL_MAX_CONN
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


def _health_check_enabled() -> bool:
    """判断是否启用数据库连接健康检查"""
    return getattr(settings, "DB_HEALTH_CHECK", "false").lower() == "true"


def get_pooled_db_connection():
    """从连接池获取连接，若连接已失效则重取一次（健康检查可配置）"""
    import time
    wait_start = time.time()
    pool = get_connection_pool()
    try:
        # 设置获取连接的超时，避免连接池耗尽时无限阻塞
        conn = pool.getconn(key=None)
    except Exception as e:
        wait_time = time.time() - wait_start
        logger.error(f"从连接池获取连接失败（等待 {wait_time:.2f}s）: {e}")
        raise ConnectionError(f"数据库连接池繁忙，请稍后重试: {e}")

    if not _health_check_enabled():
        return conn

    # 通过轻量查询验证连接是否真正可用
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as e:
        logger.warning(f"数据库连接健康检查失败，尝试重新获取连接: {e}")
        # 探针失败时重试一次，避免无限循环
        try:
            pool.putconn(conn, close=True)
        except Exception as close_err:
            logger.debug(f"回收已关闭连接时发生异常: {close_err}")
            try:
                if not getattr(conn, "closed", 0):
                    conn.close()
            except Exception:
                pass
        conn = pool.getconn(key=None)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as retry_err:
            logger.error(f"重新获取的数据库连接仍无效: {retry_err}")
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass
            raise ConnectionError(f"无法获取有效的数据库连接: {retry_err}")

    return conn


def close_connection_pool():
    """关闭 psycopg2 连接池，避免热重载残留进程继续占用数据库连接。"""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("数据库连接池已关闭")


def release_db_connection(conn):
    """释放连接回池，失败时不影响业务"""
    if conn is None:
        return
    global _pool
    pool = _pool  # 读取一次，避免多线程竞态
    if pool is None:
        try:
            if not getattr(conn, "closed", 0):
                conn.close()
        except Exception:
            pass
        return
    try:
        pool.putconn(conn, key=None)
    except Exception as e:
        logger.warning(f"释放数据库连接回池失败: {e}")
        try:
            if not getattr(conn, "closed", 0):
                conn.close()
        except Exception:
            pass
