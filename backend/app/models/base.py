"""
SQLAlchemy 基础模型
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.config import settings

# 使用现有的数据库配置
DATABASE_URL = settings.DATABASE_URL

# 创建引擎
engine_kwargs = {
    "connect_args": {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
    "pool_pre_ping": True,
    "pool_recycle": 1800,
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
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
