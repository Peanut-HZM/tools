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
# 连接池统一（原 psycopg2 ThreadedConnectionPool 已废弃）
#
# 所有服务（auth_service / monitor / database_tool / http_client 等）
# 通过 get_pooled_db_connection() / release_db_connection() 获取连接。
# 底层统一走 SQLAlchemy engine 的 QueuePool，总预算收敛为一套。
# ============================================================

from contextlib import contextmanager


class _PooledRawConnection:
    """透明代理：让旧 API (get_pooled_db_connection / release_db_connection) 继续工作，
    但连接实际来自 SQLAlchemy engine 池。

    - conn.cursor() / conn.commit() / conn.rollback() / conn.closed
      全部委托到内部 psycopg2 连接，行为与之前一致
    - conn.close() 归还到 SA 池而非物理关闭
    - cursor_factory 默认 RealDictCursor（与旧 ThreadedConnectionPool 兼容）
    """

    def __init__(self, fairy):
        self._fairy = fairy
        self._raw = fairy.dbapi_connection
        # 保持与原 ThreadedConnectionPool 相同的默认游标类型
        self._raw.cursor_factory = RealDictCursor

    # -------- 显式委托 --------

    def cursor(self, *args, **kwargs):
        return self._raw.cursor(*args, **kwargs)

    def commit(self):
        return self._raw.commit()

    def rollback(self):
        return self._raw.rollback()

    def close(self):
        """归还到 SA 池；若 fairy 已失效则直接关闭底层连接"""
        try:
            self._fairy.close()
        except Exception:
            try:
                if not getattr(self._raw, "closed", 0):
                    self._raw.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # -------- 透传 psycopg2 connection 的其他属性 --------

    @property
    def closed(self):
        return getattr(self._raw, "closed", 0)

    def __getattr__(self, name):
        # 仅当实例本身找不到属性时走这里（避免与显式方法冲突）
        return getattr(self._raw, name)


@contextmanager
def get_raw_db_connection():
    """上下文管理器版本：从 SA engine 池借底层 psycopg2 连接。

    推荐新代码使用此接口；旧代码继续使用 get_pooled_db_connection / release_db_connection。
    """
    from app.models.base import engine
    fairy = engine.pool.connect()
    raw = _PooledRawConnection(fairy)
    try:
        yield raw
    finally:
        raw.close()


def _do_health_check(conn: _PooledRawConnection) -> None:
    """用 SELECT 1 探活连接，失败时由调用方决定是否重试"""
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()


def get_pooled_db_connection():
    """从 SQLAlchemy engine 池获取连接（健康检查可配置）。

    返回 _PooledRawConnection：
    - 接口兼容原 psycopg2 connection（cursor / commit / rollback / closed）
    - close() 归还到 SA 池而非物理关闭
    """
    import time
    from app.models.base import engine

    wait_start = time.time()
    try:
        fairy = engine.pool.connect()
    except Exception as e:
        wait_time = time.time() - wait_start
        logger.error(f"从引擎池获取连接失败（等待 {wait_time:.2f}s）: {e}")
        raise ConnectionError(f"数据库连接池繁忙，请稍后重试: {e}")

    conn = _PooledRawConnection(fairy)

    if not _health_check_enabled():
        return conn

    # 通过轻量查询验证连接是否真正可用
    try:
        _do_health_check(conn)
    except Exception as e:
        logger.warning(f"数据库连接健康检查失败，尝试重新获取连接: {e}")
        conn.close()
        try:
            fairy = engine.pool.connect()
            conn = _PooledRawConnection(fairy)
            _do_health_check(conn)
        except Exception as retry_err:
            logger.error(f"重新获取的数据库连接仍无效: {retry_err}")
            try:
                conn.close()
            except Exception:
                pass
            raise ConnectionError(f"无法获取有效的数据库连接: {retry_err}")

    return conn


def release_db_connection(conn):
    """释放连接回 SA 引擎池。

    接受 _PooledRawConnection（新路径）或任何有 .close() 的对象（向后兼容）。
    """
    if conn is None:
        return
    try:
        conn.close()
    except Exception as e:
        logger.warning(f"释放数据库连接失败: {e}")
        try:
            if not getattr(conn, "closed", 0):
                conn.close()
        except Exception:
            pass


def close_connection_pool():
    """关闭 SQLAlchemy 引擎连接池（热重载时释放残留连接）。"""
    from app.models.base import engine
    try:
        engine.dispose()
        logger.info("数据库引擎连接池已释放")
    except Exception as e:
        logger.warning(f"数据库引擎连接池释放失败: {e}")
