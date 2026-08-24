"""有序 LLM 兜底链

按 category 查询 LLMModel（priority ASC, id ASC），逐个调用直到成功。
分类：
  - text 类（text / voice / vision / embedding / ocr）走 get_provider
  - image_gen 走 ImageGenFactory
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.constants.llm_categories import LLMCategory
from app.core.security import decrypt_api_key
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider
from app.services.llm.exceptions import (
    AllModelsUnavailableError,
    RecoverableFailure,
    UnrecoverableFailure,
)
from app.services.llm.factory import get_provider
from app.services.llm.image_gen_factory import ImageGenFactory

logger = logging.getLogger(__name__)


class OrderedLLMGateway:
    """有序模型调用网关

    按 priority ASC 遍历 category 下所有可用模型，依次尝试调用。
    - RecoverableFailure → 跳过，试下一个
    - UnrecoverableFailure → 立即抛出
    - 全部失败 → AllModelsUnavailableError
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    async def generate(self, category: str, **kwargs) -> Any:
        """按兜底链调用模型，返回第一个成功的结果"""
        models = self._models_by_category(category)
        if not models:
            raise AllModelsUnavailableError([])

        models = self._ordered(models)
        is_image_gen = category == LLMCategory.IMAGE_GEN

        failures: list[tuple[str, str]] = []
        for model in models:
            try:
                adapter = self._build_adapter(model, is_image_gen)
                logger.info(
                    "[gateway] trying model=%s priority=%s", model.id, model.priority
                )
                result = await adapter.generate(**kwargs)
                logger.info("[gateway] OK model=%s", model.id)
                return result
            except RecoverableFailure as e:
                logger.warning(
                    "[gateway] FAIL model=%s reason=%s; trying next", model.id, e
                )
                failures.append((str(model.id), str(e)))
                continue
            except UnrecoverableFailure as e:
                logger.error("[gateway] FATAL model=%s reason=%s", model.id, e)
                raise

        raise AllModelsUnavailableError(failures)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _models_by_category(self, category: str) -> list[LLMModel]:
        """查询 category 下所有 is_active=True 且 provider.is_active=True 的模型"""
        return (
            self.db.query(LLMModel)
            .join(LLMProvider, LLMModel.provider_id == LLMProvider.id)
            .filter(
                LLMModel.category == category,
                LLMModel.is_active == True,  # noqa: E712
                LLMProvider.is_active == True,  # noqa: E712
            )
            .all()
        )

    @staticmethod
    def _ordered(models: list[LLMModel]) -> list[LLMModel]:
        """按 priority ASC, id ASC 排序"""
        return sorted(models, key=lambda m: (m.priority, str(m.id)))

    def _build_adapter(self, model: LLMModel, is_image_gen: bool):
        """根据分类选择对应 Factory 并构造 adapter"""
        provider = model.provider
        api_key = decrypt_api_key(provider.api_key_encrypted)
        extra = self._parse_request_params(model.request_params)

        if is_image_gen:
            return ImageGenFactory.get(
                provider_type=provider.provider_type,
                api_key=api_key,
                base_url=provider.base_url,
                model_name=model.model_name,
                **extra,
            )
        return get_provider(
            provider_type=provider.provider_type,
            api_key=api_key,
            base_url=provider.base_url,
            model=model.model_name,
            **extra,
        )

    @staticmethod
    def _parse_request_params(raw: Any) -> dict:
        """LLMModel.request_params 为 Text(JSON)，解析为 dict"""
        if raw is None or raw == "":
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
