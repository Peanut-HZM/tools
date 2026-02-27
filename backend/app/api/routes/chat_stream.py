"""
流式对话接口
用于实时返回 AI 生成的内容
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.api.dependencies import get_db, get_current_user
from app.services.conversation_service import ConversationService, MessageService
from app.services.llm_config_service import LLMConfigService
from app.services.agent_management_service import AgentService as AgentManagementService
from app.services.llm.factory import get_provider
from app.services.llm.base import Message, GenerationConfig
from app.core.security import decrypt_api_key

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: str,
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    流式对话接口
    使用 SSE (Server-Sent Events) 实时返回 AI 生成的内容
    """
    content = request.get("content", "")
    llm_config_id = request.get("llm_config_id")
    agent_id = request.get("agent_id")

    # 验证会话所有权
    conv_service = ConversationService(db)
    conversation = conv_service.get_conversation(conversation_id, current_user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 创建用户消息
    msg_service = MessageService(db)
    user_message = msg_service.create_message(
        conversation_id=conversation_id, sender_type="user", content=content
    )
    user_msg_dict = {
        "id": str(user_message.id),
        "conversation_id": str(user_message.conversation_id),
        "sender_type": user_message.sender_type,
        "content": user_message.content,
        "message_type": user_message.message_type,
        "sent_at": user_message.sent_at.isoformat() if user_message.sent_at else None,
    }

    async def generate_stream():
        try:
            # 发送用户消息
            yield f"data: {json.dumps({'type': 'user_message', 'data': user_msg_dict}, ensure_ascii=False)}\n\n"

            # 获取 LLM 配置
            config_service = LLMConfigService(db)
            if llm_config_id:
                config = config_service.get_config(llm_config_id)
                if not config:
                    config = config_service.get_default_config()
            else:
                config = config_service.get_default_config()

            if not config:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有可用的 LLM 配置'}, ensure_ascii=False)}\n\n"
                return

            # 获取对话历史
            history = msg_service.build_context(conversation_id, max_messages=10)

            # 获取Agent的系统提示词
            agent_service = AgentManagementService(db)
            if agent_id:
                agent = agent_service.get_agent(agent_id)
                system_prompt = agent.system_prompt if agent else "你是一个智能AI助手。"
            else:
                default_agent = agent_service.get_default_agent()
                system_prompt = (
                    default_agent.system_prompt
                    if default_agent
                    else "你是一个智能AI助手。"
                )

            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ]
            for msg in history:
                messages.append(msg)
            messages.append({"role": "user", "content": content})

            # 解密 API Key 并创建 provider
            api_key = decrypt_api_key(config.api_key_encrypted)
            provider = get_provider(
                provider_type=config.provider_type,
                api_key=api_key,
                base_url=config.base_url,
                model=config.model_name,
                **(config.request_params or {}),
            )

            # 流式生成
            full_content = ""
            message_objects = [
                Message(role=msg["role"], content=msg["content"]) for msg in messages
            ]

            async for chunk in provider.generate_stream(
                message_objects, GenerationConfig()
            ):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 计算token数量（估算）
            prompt_tokens = sum(len(m["content"]) // 4 for m in messages)
            completion_tokens = len(full_content) // 4
            total_tokens = prompt_tokens + completion_tokens

            # 保存 AI 消息到数据库（包含token统计）
            agent_message = msg_service.create_message(
                conversation_id=conversation_id,
                sender_type="agent",
                content=full_content,
            )

            # 更新token统计信息
            agent_message.prompt_tokens = prompt_tokens
            agent_message.completion_tokens = completion_tokens
            agent_message.total_tokens = total_tokens
            agent_message.llm_config_id = config.id
            agent_message.llm_model_name = config.model_name
            db.commit()

            agent_msg_dict = {
                "id": str(agent_message.id),
                "conversation_id": str(agent_message.conversation_id),
                "sender_type": agent_message.sender_type,
                "content": agent_message.content,
                "message_type": agent_message.message_type,
                "sent_at": agent_message.sent_at.isoformat()
                if agent_message.sent_at
                else None,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "llm_model_name": config.model_name,
            }

            # 发送完成消息
            yield f"data: {json.dumps({'type': 'done', 'data': agent_msg_dict}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
