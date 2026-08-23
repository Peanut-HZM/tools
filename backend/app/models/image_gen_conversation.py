"""自研图像生成路径的对话历史表

Dify 路径的对话由 Dify 托管；自研路径由本表持久化。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableList

from app.models.base import Base


class ImageGenSelfDevConversation(Base):
    """自研图像生成路径的对话记录"""

    __tablename__ = "image_gen_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 注意：users.id 为 String(64)（见 app/models/user.py），类型与 UUID 不一致，
    # 在 PostgreSQL 上无法建立外键约束；参照 app/models/conversation.py 的先例，
    # 此处不使用外键，改在应用层校验用户归属。
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    """对话所属用户（用于权限校验）"""

    conversation_id = Column(String(64), unique=True, index=True, nullable=False)
    """对外暴露的对话 UUID 字符串"""

    operation = Column(String(32), nullable=False)
    """text2img / img2img / inpaint / upload_edit"""

    messages = Column(MutableList.as_mutable(JSONB), nullable=False, default=list)
    """
    对话消息列表。每条消息形如：
      {"role": "user"|"assistant"|"tool",
       "content": "...",
       "tool_calls": [{"id": "...", "name": "generate_image", "arguments": {...}}]?,
       "tool_call_id": "..."?}
    """

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
