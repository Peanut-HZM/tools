"""
LLM 服务
用于调用大模型生成回复

v1 起已迁移到 LLMProvider + LLMModel（原 llm_configs 表仅保留用于回滚过渡）。
"""

import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload

from app.services.llm.factory import get_provider
from app.services.llm.base import Message, GenerationConfig
from app.services.conversation_service import MessageService
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider
from app.core.security import decrypt_api_key

logger = logging.getLogger(__name__)


def _get_default_model(db: Session) -> Optional[LLMModel]:
    """
    获取默认 LLM 模型（is_default=True 且活跃）。
    若 provider 已停用则不会返回。
    """
    return (
        db.query(LLMModel)
        .join(LLMModel.provider)  # INNER JOIN：用于 is_active 过滤，避免笛卡尔积
        .options(joinedload(LLMModel.provider))  # LEFT OUTER JOIN：一次取回 provider 字段
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


async def generate_agent_response(
    db: Session,
    conversation_id: str,
    user_message: str,
    llm_config_id: Optional[str] = None,
) -> str:
    """
    生成 AI 回复

    Args:
        db: 数据库会话
        conversation_id: 对话 ID
        user_message: 用户消息内容
        llm_config_id: 指定的 LLM 模型 ID，为空则使用默认模型（参数名保留兼容旧接口）

    Returns:
        AI 生成的回复内容
    """
    try:
        # 1. 获取 LLM 模型
        if llm_config_id:
            model = (
                db.query(LLMModel)
                .options(joinedload(LLMModel.provider))
                .filter(LLMModel.id == llm_config_id)
                .first()
            )
            if not model:
                logger.warning(
                    f"指定的 LLM 模型 {llm_config_id} 不存在，使用默认模型"
                )
                model = _get_default_model(db)
        else:
            model = _get_default_model(db)

        if not model:
            logger.error("没有可用的 LLM 模型")
            return "抱歉，系统尚未配置 AI 模型，请联系管理员配置。"

        logger.info(
            f"使用 LLM 模型: {model.name} ({model.provider.provider_type})"
        )

        # 2. 获取对话历史
        msg_service = MessageService(db)
        history = msg_service.build_context(conversation_id, max_messages=10)

        # 3. 构建消息列表
        messages = _build_messages(history, user_message)

        # 4. 解密 API Key 并创建 provider
        api_key = decrypt_api_key(model.provider.api_key_encrypted)
        request_params = _parse_request_params(model.request_params)
        provider = get_provider(
            provider_type=model.provider.provider_type,
            api_key=api_key,
            base_url=model.provider.base_url,
            model=model.model_name,
            **request_params,
        )

        # 5. 生成回复
        message_objects = [
            Message(role=msg["role"], content=msg["content"]) for msg in messages
        ]
        result = await provider.generate(
            messages=message_objects, config=GenerationConfig()
        )

        return result.content

    except Exception as e:
        logger.error(f"生成 AI 回复失败: {e}", exc_info=True)
        return f"抱歉，AI 服务暂时不可用。错误: {str(e)}"


def _build_messages(
    history: List[Dict[str, str]], user_message: str
) -> List[Dict[str, str]]:
    """
    构建消息列表，包含系统提示和历史对话
    """
    # 系统提示词
    system_prompt = """你是一个专业的产品经理助手，帮助用户进行产品规划和设计。

你的职责包括：
1. 理解用户需求，进行需求澄清
2. 协助进行市场研究和竞品分析
3. 设计产品架构和功能模块
4. 撰写详细的产品需求文档（PRD）

请用中文回复，保持专业、友好、有条理的对话风格。
如果用户的需求不够清晰，请主动提问帮助澄清。"""

    messages = [{"role": "system", "content": system_prompt}]

    # 添加历史对话
    for msg in history:
        messages.append(msg)

    # 添加当前用户消息
    messages.append({"role": "user", "content": user_message})

    return messages
