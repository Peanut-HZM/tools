"""
SQLAlchemy 基础模型
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.config import settings

logger = logging.getLogger(__name__)

# 使用现有的数据库配置
DATABASE_URL = settings.DATABASE_URL

# 创建引擎
engine_kwargs = {
    "connect_args": {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    # 关键防御：连接归还连接池时强制 rollback。
    # 背景：后台任务（如 token_usage_background_sync/warm_query_cache）如果发生
    # 异常且未显式 rollback，该连接会被返回到连接池时处于 PG transaction aborted
    # 状态。下一个请求复用该连接时，所有 ORM lazy 属性访问都会返回列键字符串
    # （如 'token_usage_records_id'）而非真实值，导致 500。
    # 此处设置 pool_reset_on_return='rollback'，确保无论调用方是否正确
    # rollback，归还的连接都会从干净的事务状态开始。
    "pool_reset_on_return": "rollback",
}

if not DATABASE_URL.startswith("sqlite"):
    # 开发环境连接远程 PostgreSQL 时，限制单进程连接预算，避免热重载进程耗尽服务端连接。
    engine_kwargs.update(
        {
            "pool_size": settings.DB_SQLALCHEMY_POOL_SIZE,
            "max_overflow": settings.DB_SQLALCHEMY_MAX_OVERFLOW,
            "pool_timeout": settings.DB_SQLALCHEMY_POOL_TIMEOUT,
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础类
Base = declarative_base()


def get_db():
    """获取数据库会话

    关键防御：
    1. 每次 yield 前做 ORM 级健康检查，确保 session 不是被污染的；
    2. 为每个事务设置 PostgreSQL 锁等待超时（lock_timeout）与语句超时（statement_timeout）。

    第 2 条是全局兜底：PostgreSQL 默认对行锁等待无限期（无 lock_timeout），
    一旦多个请求并发更新同一行（如 course_statistics.view_count 自增），
    后到的请求会无限期等锁。而本项目数据库会话是同步 SQLAlchemy，
    等锁期间会占住 event loop，最终把整个后端冻结（连 /openapi.json 都超时）。
    设置 lock_timeout 后，锁等待超过阈值即报错回滚，最多短暂阻塞而不会永久冻结。
    SET LOCAL 只在当前事务内生效，事务结束自动恢复，不影响连接池中其他会话。
    """
    db = SessionLocal()
    try:
        # 防御：确保 session 处于干净的事务状态
        try:
            db.rollback()
            # ORM 级健康检查
            from app.models.llm_config import LLMConfig
            health_result = db.query(LLMConfig.id).limit(1).all()
            logger.info("[get_db] ORM 健康检查 (id=%s, result=%s)", id(db), health_result)
        except Exception as rb_exc:
            logger.warning("[get_db] ORM 健康检查失败: %s", rb_exc)
            try:
                db.close()
            except Exception:
                pass
            db = SessionLocal()
        # 锁等待/语句超时兜底（仅 PostgreSQL；SQLite 无此概念）
        try:
            if not DATABASE_URL.startswith("sqlite"):
                db.execute(text("SET LOCAL lock_timeout = '5s'"))
                db.execute(text("SET LOCAL statement_timeout = '30s'"))
        except Exception as st_exc:
            logger.warning("[get_db] 设置锁/语句超时失败: %s", st_exc)
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass
