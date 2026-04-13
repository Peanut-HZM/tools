"""
对话路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from app.api.dependencies import get_db, get_current_user
from app.services.conversation_service import ConversationService, MessageService
from app.services.agent_service import generate_agent_response
from app.models import Conversation, Message


def _conversation_to_dict(conv: Conversation) -> dict:
    """将 SQLAlchemy Conversation 对象转换为字典"""
    return {
        "id": str(conv.id),
        "user_id": str(conv.user_id),
        "title": conv.title,
        "current_stage": conv.current_stage,
        "version": conv.version,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def _message_to_dict(msg: Message) -> dict:
    """将 SQLAlchemy Message 对象转换为字典"""
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_type": msg.sender_type,
        "content": msg.content,
        "message_type": msg.message_type,
        "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
    }


router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    """创建会话请求"""

    title: Optional[str] = Field(None, max_length=200)
    initial_message: Optional[str] = Field(None, description="用户的第一条消息")


class ConversationUpdate(BaseModel):
    """更新会话请求"""

    title: Optional[str] = Field(None, max_length=200)
    version: int = Field(..., description="当前版本号（用于乐观锁）")


class ConversationResponse(BaseModel):
    """会话响应"""

    id: str
    user_id: str
    title: Optional[str]
    current_stage: str
    version: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """创建消息请求"""

    content: str = Field(..., min_length=1)
    action: str = Field(
        default="chat",
        description="动作类型: chat, analyze_competitor, generate_prd, export",
    )
    llm_config_id: Optional[str] = Field(
        default=None,
        description="指定 LLM 配置 ID，为空则使用默认配置",
    )


class MessageResponse(BaseModel):
    """消息响应"""

    id: str
    conversation_id: str
    sender_type: str
    content: str
    message_type: str
    sent_at: str

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """聊天响应"""

    user_message: MessageResponse
    agent_message: MessageResponse
    stage_changed: bool
    new_stage: Optional[str]


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取会话列表"""
    service = ConversationService(db)
    conversations = service.list_conversations(
        user_id=current_user["id"], skip=skip, limit=limit
    )
    return [_conversation_to_dict(c) for c in conversations]


@router.post(
    "", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建新会话"""
    service = ConversationService(db)
    conversation = service.create_conversation(
        user_id=current_user["id"], title=data.title
    )

    # 如果有初始消息，创建消息
    if data.initial_message:
        msg_service = MessageService(db)
        msg_service.create_message(
            conversation_id=str(conversation.id),
            sender_type="user",
            content=data.initial_message,
        )

    return _conversation_to_dict(conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取会话详情"""
    service = ConversationService(db)
    conversation = service.get_conversation(conversation_id, current_user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    return _conversation_to_dict(conversation)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新会话（乐观锁）"""
    service = ConversationService(db)

    success, conversation, error = service.optimistic_lock_update(
        conversation_id=conversation_id, version=data.version, title=data.title
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    if not success:
        raise HTTPException(status_code=409, detail=error)

    return _conversation_to_dict(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除会话及其所有消息"""
    service = ConversationService(db)
    success = service.delete_conversation(conversation_id, current_user["id"])

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    before_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取会话消息"""
    # 验证会话所有权
    conv_service = ConversationService(db)
    conversation = conv_service.get_conversation(conversation_id, current_user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    msg_service = MessageService(db)
    messages = msg_service.get_messages(
        conversation_id, limit=limit, before_id=before_id
    )

    return [_message_to_dict(m) for m in messages]


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发送消息并获取 AI 响应"""
    # 验证会话所有权
    conv_service = ConversationService(db)
    conversation = conv_service.get_conversation(conversation_id, current_user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 创建用户消息
    msg_service = MessageService(db)
    user_message = msg_service.create_message(
        conversation_id=conversation_id, sender_type="user", content=data.content
    )

    # 调用 AI 服务生成响应
    agent_content = await generate_agent_response(
        db=db,
        conversation_id=conversation_id,
        user_message=data.content,
        llm_config_id=data.llm_config_id,
    )

    agent_message = msg_service.create_message(
        conversation_id=conversation_id, sender_type="agent", content=agent_content
    )

    return ChatResponse(
        user_message=_message_to_dict(user_message),
        agent_message=_message_to_dict(agent_message),
        stage_changed=False,
        new_stage=None,
    )
