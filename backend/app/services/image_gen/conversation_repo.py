"""自研图像生成路径的对话仓库

提供 ImageGenSelfDevConversation 的 CRUD 操作：
- save: upsert 对话记录（按 conversation_id 去重）
- load: 按 conversation_id 加载消息列表
- load_by_id: 按 conversation_id + user_id 加载，强制用户隔离
"""

from __future__ import annotations

import logging
import uuid as uuid_module
from typing import Any, Union

from sqlalchemy.orm import Session

from app.models.image_gen_conversation import ImageGenSelfDevConversation

logger = logging.getLogger(__name__)

# user_id 兼容类型：接受 UUID 或 str，统一转 str 后写入 String(64) 列
UserId = Union[str, uuid_module.UUID]


def _to_str_user_id(user_id: UserId) -> str:
    """将 UUID 或 str 统一为 str，避免 SQLAlchemy 对 String(64) 列写入 UUID 对象"""
    if isinstance(user_id, uuid_module.UUID):
        return str(user_id)
    return user_id


class ConversationRepository:
    """自研对话历史 CRUD

    所有写操作自动 commit；调用方不应在同一 Session 上混用其它事务边界。
    """

    def __init__(self, db: Session):
        self.db = db

    async def save(
        self,
        user_id: UserId,
        conversation_id: str,
        operation: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """保存对话（upsert）

        - 已存在同 conversation_id 记录 → 更新 messages
        - 否则 → 新建记录
        """
        uid = _to_str_user_id(user_id)
        existing = (
            self.db.query(ImageGenSelfDevConversation)
            .filter_by(conversation_id=conversation_id)
            .first()
        )
        if existing:
            existing.messages = messages
            logger.info(
                "[conv_repo] update conversation_id=%s messages=%d",
                conversation_id, len(messages),
            )
        else:
            record = ImageGenSelfDevConversation(
                user_id=uid,
                conversation_id=conversation_id,
                operation=operation,
                messages=messages,
            )
            self.db.add(record)
            logger.info(
                "[conv_repo] create conversation_id=%s user_id=%s",
                conversation_id, uid,
            )
        self.db.commit()

    async def load(self, conversation_id: str) -> list[dict[str, Any]]:
        """按 conversation_id 加载消息列表；不存在返回空列表"""
        record = (
            self.db.query(ImageGenSelfDevConversation)
            .filter_by(conversation_id=conversation_id)
            .first()
        )
        if not record:
            return []
        return list(record.messages or [])

    async def load_by_id(
        self,
        conversation_id: str,
        user_id: UserId,
    ) -> list[dict[str, Any]]:
        """按 conversation_id + user_id 加载（多用户隔离）

        若 conversation_id 存在但不属于当前 user_id，返回空列表（不抛异常），
        避免越权读取其它用户的对话内容。
        """
        uid = _to_str_user_id(user_id)
        record = (
            self.db.query(ImageGenSelfDevConversation)
            .filter_by(conversation_id=conversation_id, user_id=uid)
            .first()
        )
        if not record:
            return []
        return list(record.messages or [])
