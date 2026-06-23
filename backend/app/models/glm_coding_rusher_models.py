"""GLM-Coding Pro 抢购工具数据库模型"""

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime
from sqlalchemy.sql import func

from app.models.base import Base


class GlmCodingRusherConfig(Base):
    """抢购配置表"""
    __tablename__ = "glm_coding_rusher_configs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    target_package = Column(String(32), nullable=False, default="pro")
    sale_time = Column(String(8), nullable=False, default="10:00")
    preheat_seconds = Column(Integer, nullable=False, default=90)
    refresh_interval_ms = Column(Integer, nullable=False, default=500)
    timeout_seconds = Column(Integer, nullable=False, default=60)
    headless = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GlmCodingRusherLog(Base):
    """抢购日志表"""
    __tablename__ = "glm_coding_rusher_logs"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    phase = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class GlmCodingRusherTask(Base):
    """抢购任务记录表"""
    __tablename__ = "glm_coding_rusher_tasks"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    config_snapshot = Column(Text, nullable=False, default="{}")
    result = Column(String(32), nullable=False, default="running")
    refresh_count = Column(Integer, nullable=False, default=0)
    payment_url = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
