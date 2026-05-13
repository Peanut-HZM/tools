"""
密码审计日志模型
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import INET
from datetime import datetime
from app.models.base import Base


class PasswordAuditLog(Base):
    """密码审计日志表（记录登录、修改密码、重置密码等操作）"""
    __tablename__ = "password_audit_logs"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True)           # 操作用户 ID
    action_type = Column(String(20), nullable=False, default="login")   # 操作类型: login / change_password / admin_reset
    success = Column(Boolean, nullable=False, default=True)             # 是否成功
    error_message = Column(Text)                                         # 错误信息（失败时）
    ip_address = Column(INET)                                           # 请求 IP 地址
    device_info = Column(Text)                                           # 设备信息（User-Agent 等）
    actor_user_id = Column(String(36))                                   # 执行操作的用户 ID（如管理员重置他人密码）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_audit_user_id', 'user_id'),
        Index('idx_audit_action_type', 'action_type'),
        Index('idx_audit_created_at', 'created_at'),
        Index('idx_audit_user_action', 'user_id', 'action_type'),
    )
