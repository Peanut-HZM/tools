"""
会话服务
处理对话的创建、消息管理和上下文维护
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import Conversation, Message
from app.core.logging import get_pm_agent_logger

# 获取专用的产品经理 Agent 日志记录器
logger = get_pm_agent_logger(__name__)


class ConversationService:
    """会话服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
        self, user_id: str, title: Optional[str] = None
    ) -> Conversation:
        """创建新会话"""
        logger.info(f"Creating new conversation for user_id={user_id}, title={title}")

        if not title:
            title = "新会话"

        conversation = Conversation(
            user_id=user_id,
            title=title,
            current_stage="requirement_clarification",
            version=1,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        logger.info(
            f"Conversation created successfully: id={conversation.id}, stage={conversation.current_stage}"
        )
        return conversation

    def get_conversation(
        self, conversation_id: str, user_id: str
    ) -> Optional[Conversation]:
        """获取会话详情"""
        logger.debug(
            f"Getting conversation: conversation_id={conversation_id}, user_id={user_id}"
        )
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def list_conversations(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> List[Conversation]:
        """获取用户会话列表"""
        logger.debug(
            f"Listing conversations for user_id={user_id}, skip={skip}, limit={limit}"
        )
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_stage(self, conversation_id: str, stage: str) -> bool:
        """更新会话阶段"""
        logger.info(
            f"Updating conversation stage: conversation_id={conversation_id}, new_stage={stage}"
        )

        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            logger.warning(f"Conversation not found: conversation_id={conversation_id}")
            return False

        old_stage = conversation.current_stage
        conversation.current_stage = stage
        self.db.commit()

        logger.info(
            f"Conversation stage updated: conversation_id={conversation_id}, {old_stage} -> {stage}"
        )
        return True

    def optimistic_lock_update(
        self, conversation_id: str, version: int, **kwargs
    ) -> tuple[bool, Optional[Conversation], str]:
        """
        乐观锁更新

        Returns:
            (是否成功, 会话对象, 错误信息)
        """
        logger.info(
            f"Optimistic lock update: conversation_id={conversation_id}, expected_version={version}"
        )

        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            logger.warning(
                f"Conversation not found for update: conversation_id={conversation_id}"
            )
            return False, None, "会话不存在"

        if conversation.version != version:
            logger.warning(
                f"Version conflict: conversation_id={conversation_id}, expected={version}, actual={conversation.version}"
            )
            return False, conversation, "版本冲突，请刷新后重试"

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)

        # 版本号 +1
        conversation.version += 1

        self.db.commit()
        self.db.refresh(conversation)

        logger.info(
            f"Optimistic lock update successful: conversation_id={conversation_id}, new_version={conversation.version}"
        )
        return True, conversation, ""


class MessageService:
    """消息服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_message(
        self,
        conversation_id: str,
        sender_type: str,
        content: str,
        message_type: str = "text",
    ) -> Message:
        """创建消息"""
        logger.info(
            f"Creating message: conversation_id={conversation_id}, sender={sender_type}, type={message_type}"
        )

        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            message_type=message_type,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        logger.debug(f"Message created: id={message.id}")
        return message

    def get_messages(
        self, conversation_id: str, limit: int = 50, before_id: Optional[str] = None
    ) -> List[Message]:
        """获取会话消息"""
        logger.debug(
            f"Getting messages: conversation_id={conversation_id}, limit={limit}, before_id={before_id}"
        )

        query = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        )

        if before_id:
            before_msg = self.db.query(Message).filter(Message.id == before_id).first()
            if before_msg:
                query = query.filter(Message.sent_at < before_msg.sent_at)

        return query.order_by(desc(Message.sent_at)).limit(limit).all()

    def build_context(
        self, conversation_id: str, max_messages: int = 20
    ) -> List[Dict[str, str]]:
        """
        构建对话上下文

        Returns:
            消息列表，格式 [{role: 'user'|'assistant', content: ''}]
        """
        logger.debug(
            f"Building context: conversation_id={conversation_id}, max_messages={max_messages}"
        )

        messages = self.get_messages(conversation_id, limit=max_messages)

        # 反转顺序（从早到晚）
        messages.reverse()

        context = []
        for msg in messages:
            role = "user" if msg.sender_type == "user" else "assistant"
            context.append({"role": role, "content": msg.content})

        logger.debug(f"Context built: {len(context)} messages")
        return context
