"""
Agent模型
用于存储AI Agent配置
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class Agent(Base):
    """Agent配置表"""

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # Agent名称
    description = Column(Text, nullable=False)  # Agent描述
    system_prompt = Column(Text, nullable=False)  # 系统提示词
    icon = Column(String(50), default="fa-robot")  # 图标
    icon_color = Column(String(100), default="bg-blue-500")  # 图标颜色
    category = Column(String(50), default="AI工具")  # 分类
    is_active = Column(Boolean, default=True)  # 是否启用
    is_default = Column(Boolean, default=False)  # 是否为默认Agent
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, category={self.category})>"
