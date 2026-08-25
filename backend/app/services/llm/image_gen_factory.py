"""ImageGenAdapter 工厂

按 provider_type 分发到对应的 ImageGenAdapter 子类。
"""

from __future__ import annotations

from typing import Optional

from app.services.llm.doubao_seedream_adapter import DoubaoSeedreamAdapter
from app.services.llm.exceptions import UnknownProviderError
from app.services.llm.hailuo_adapter import HailuoAdapter
from app.services.llm.image_gen_base import ImageGenAdapter
from app.services.llm.openai_image_adapter import OpenAIImageAdapter
from app.services.llm.qwen_image_adapter import QwenImageAdapter


class ImageGenFactory:
    """按 provider_type 返回对应的 ImageGenAdapter"""

    _REGISTRY: dict[str, type[ImageGenAdapter]] = {
        "doubao_seedream": DoubaoSeedreamAdapter,
        "qwen_image": QwenImageAdapter,
        "hailuo": HailuoAdapter,
        "openai_image": OpenAIImageAdapter,
        # 阿里云百炼平台的 image_gen 模型（如 qwen-image-*、wanx-*）
        # 走 DashScope 原生 API，与 qwen_image 同协议
        "aliyun": QwenImageAdapter,
    }

    @classmethod
    def get(
        cls,
        provider_type: str,
        api_key: str,
        base_url: Optional[str],
        model_name: str,
        **kw,
    ) -> ImageGenAdapter:
        """根据 provider_type 获取对应的适配器实例"""
        if provider_type not in cls._REGISTRY:
            raise UnknownProviderError(provider_type)
        adapter_cls = cls._REGISTRY[provider_type]
        return adapter_cls(api_key=api_key, base_url=base_url, model=model_name, **kw)
