"""数据库访问入口（兼容模块）

历史原因：早期代码使用 `from app.database import engine, SessionLocal`。
实际实现在 `app.models.base`，此处仅做符号转发，保持向后兼容。
"""
from app.models.base import engine, SessionLocal, get_db  # noqa: F401

__all__ = ["engine", "SessionLocal", "get_db"]