"""
密码重置日志模型
"""
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import INET
from datetime import datetime
from app.models.base import Base


class PasswordResetLog(Base):
    """密码重置日志表"""
    __tablename__ = "password_reset_logs"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False)  # 被重置密码的用户 ID
    reset_by_user_id = Column(String(36), nullable=False)  # 执行重置的管理员用户 ID
    reset_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(INET)  # 请求 IP 地址

    # 创建索引
    __table_args__ = (
        Index('idx_password_reset_logs_user_id', 'user_id'),
        Index('idx_password_reset_logs_reset_at', 'reset_at'),
    )
