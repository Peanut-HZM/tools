"""
会话服务
处理对话的创建、消息管理和上下文维护
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import Conversation, Message


class ConversationService:
    """会话服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
        self, user_id: str, title: Optional[str] = None
    ) -> Conversation:
        """创建新会话"""
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
        return conversation

    def get_conversation(
        self, conversation_id: str, user_id: str
    ) -> Optional[Conversation]:
        """获取会话详情"""
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def list_conversations(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> List[Conversation]:
        """获取用户会话列表"""
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
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            return False

        conversation.current_stage = stage
        self.db.commit()
        return True

    def optimistic_lock_update(
        self, conversation_id: str, version: int, **kwargs
    ) -> tuple[bool, Optional[Conversation], str]:
        """
        乐观锁更新

        Returns:
            (是否成功, 会话对象, 错误信息)
        """
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            return False, None, "会话不存在"

        if conversation.version != version:
            return False, conversation, "版本冲突，请刷新后重试"

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)

        # 版本号 +1
        conversation.version += 1

        self.db.commit()
        self.db.refresh(conversation)
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
        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            message_type=message_type,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(
        self, conversation_id: str, limit: int = 50, before_id: Optional[str] = None
    ) -> List[Message]:
        """获取会话消息"""
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
        messages = self.get_messages(conversation_id, limit=max_messages)

        # 反转顺序（从早到晚）
        messages.reverse()

        context = []
        for msg in messages:
            role = "user" if msg.sender_type == "user" else "assistant"
            context.append({"role": role, "content": msg.content})

        return context
