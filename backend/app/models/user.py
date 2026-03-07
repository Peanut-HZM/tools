"""
用户认证数据模型
"""

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
