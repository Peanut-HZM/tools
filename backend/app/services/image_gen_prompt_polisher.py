"""
Task 8.1 — ImageGenPromptPolisher 提示词润色服务
Task 14 — 迁移到 OrderedLLMGateway（替代已废弃的 LLMFallbackService）

通过 OrderedLLMGateway 按 category 兜底链调用 LLM，
把用户输入的原始提示词转换为更适合图像生成模型的英文提示词。

依赖：
- LLMModelService.get_default_model(category) — 取指定类别的默认模型（仅用于
  前置校验、system prompt 措辞与分类选择；实际调用顺序由网关按 priority 决定）
- OrderedLLMGateway.generate(category, messages) — 按 priority 兜底链调用

失败语义（graceful degradation）：
- 找不到润色模型（image_polish / chat 均无默认） → 返回原 prompt + warning
- provider 配置不完整（缺 api_key / base_url） → 返回原 prompt + warning
- model 缺 model_name → 返回原 prompt + warning
- LLM 调用失败（任何异常，含 AllModelsUnavailableError） → 返回原 prompt + warning
- LLM 返回空内容 → 返回原 prompt

注意：所有失败路径绝不抛异常，外层 ImageGenService 可无脑调用。
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.constants.llm_categories import LLMCategory
from app.services.llm.base import Message
from app.services.llm.exceptions import AllModelsUnavailableError
from app.services.llm.ordered_gateway import OrderedLLMGateway
from app.services.llm_model_service import LLMModelService

logger = logging.getLogger(__name__)


class ImageGenPromptPolisher:
    """图像生成提示词润色器

    通过 OrderedLLMGateway 把用户原始中文/短提示词润色为英文、
    更适合目标图像模型理解的高质量 prompt。
    """

    def __init__(
        self,
        db: Session,
        gateway: Optional[OrderedLLMGateway] = None,
    ):
        self._db = db
        self._model_svc = LLMModelService(db)
        self._gateway = gateway or OrderedLLMGateway(db)

    async def polish(
        self,
        prompt: str,
        user_id: str,
        target_operation: str = "text2img",
    ) -> str:
        """
        润色提示词。

        Args:
            prompt: 原始提示词
            user_id: 调用者 ID（预留审计，当前未使用）
            target_operation: 图像操作类型，影响 system prompt 措辞

        Returns:
            润色后的提示词；任何失败都返回原 prompt（不抛异常）
        """
        # 1. 找润色模型：text 类别
        #    （仅用于前置校验与 system prompt 措辞；实际兜底链由网关按 priority 驱动）
        model = self._model_svc.get_default_model(category=LLMCategory.TEXT)
        category = LLMCategory.TEXT
        if not model:
            logger.warning("[image-gen-polish] 无可用默认模型（text），返回原提示词")
            return prompt

        # 2. 校验 provider 配置
        provider = model.provider
        if not provider:
            logger.warning("[image-gen-polish] 模型 %s 缺少 provider 关联，返回原提示词", model.id)
            return prompt
        if not provider.api_key_encrypted:
            logger.warning("[image-gen-polish] provider %s 缺少 api_key，返回原提示词", provider.id)
            return prompt
        if not provider.base_url:
            logger.warning("[image-gen-polish] provider %s 缺少 base_url，返回原提示词", provider.id)
            return prompt
        if not model.model_name:
            logger.warning("[image-gen-polish] 模型 %s 缺少 model_name，返回原提示词", model.id)
            return prompt

        # 3. 构造 system prompt
        system_msg = (
            f"你是图像生成提示词优化专家。根据用户目标 ({target_operation}) "
            f"优化以下提示词，使其更适合 {model.model_name} 类模型。"
            f"返回英文版本。原始提示：{prompt}"
        )

        # 4. 调用 OrderedLLMGateway 兜底链
        messages = [
            Message(role="system", content=system_msg),
            Message(role="user", content=prompt),
        ]
        try:
            result = await self._gateway.generate(category=category, messages=messages)

            # 兼容 GenerationResult（.content）与纯字符串两种返回形态
            content = getattr(result, "content", result)
            if not content:
                logger.warning("[image-gen-polish] LLM 返回空结果，返回原提示词")
                return prompt
            return content
        except Exception as e:
            logger.warning("[image-gen-polish] 润色失败: %s，返回原提示词", e)
            return prompt
