"""
流式对话接口
用于实时返回 AI 生成的内容

v1 起已迁移到 LLMProvider + LLMModel（原 llm_configs 表仅保留用于回滚过渡）。
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_db, get_current_user
from app.services.conversation_service import ConversationService, MessageService
from app.services.agent_management_service import AgentService as AgentManagementService
from app.services.llm.factory import get_provider
from app.services.llm.base import Message, GenerationConfig
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider
from app.core.security import decrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _get_default_model(db: Session) -> Optional[LLMModel]:
    """获取默认 LLM 模型（is_default=True 且活跃）。"""
    return (
        db.query(LLMModel)
        .options(joinedload(LLMModel.provider))
        .filter(
            LLMModel.is_default == True,
            LLMModel.is_active == True,
            LLMProvider.is_active == True,
        )
        .first()
    )


def _parse_request_params(raw: Any) -> Dict[str, Any]:
    """解析 request_params（Text 形式的 JSON 字符串）。"""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


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

            # 获取 LLM 模型
            if llm_config_id:
                model = (
                    db.query(LLMModel)
                    .options(joinedload(LLMModel.provider))
                    .filter(LLMModel.id == llm_config_id)
                    .first()
                )
                if not model:
                    model = _get_default_model(db)
            else:
                model = _get_default_model(db)

            if not model:
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
            api_key = decrypt_api_key(model.provider.api_key_encrypted)
            request_params = _parse_request_params(model.request_params)
            provider = get_provider(
                provider_type=model.provider.provider_type,
                api_key=api_key,
                base_url=model.provider.base_url,
                model=model.model_name,
                **request_params,
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

            # 保存 AI 消息到数据库（包含token统计信息）
            # 注：llm_config_id 列名保留用于过渡期兼容，实际存储的是 LLMModel.id
            agent_message = msg_service.create_message(
                conversation_id=conversation_id,
                sender_type="agent",
                content=full_content,
            )

            agent_message.prompt_tokens = prompt_tokens
            agent_message.completion_tokens = completion_tokens
            agent_message.total_tokens = total_tokens
            agent_message.llm_config_id = model.id
            agent_message.llm_model_name = model.model_name
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
                "llm_model_name": model.model_name,
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
