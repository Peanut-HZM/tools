"""EmbeddingProvider 工厂"""
import logging
import os
from typing import Optional

from app.services.harness.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)


def create_embedding_provider(config: dict) -> EmbeddingProvider:
    """根据配置创建 EmbeddingProvider

    config 格式:
    {
        "embedding_provider": "openai" | "dashscope",
        "embedding_model": "text-embedding-3-small",
        "embedding_api_key": "sk-...",       # 可选，fallback 到环境变量
        "embedding_base_url": "https://...",  # 可选（仅 openai）
    }
    """
    provider_type = config.get("embedding_provider", "openai")
    model = config.get("embedding_model", "text-embedding-3-small")

    # API key 解析：配置 > 环境变量
    api_key = config.get("embedding_api_key") or os.environ.get(
        "EMBEDDING_API_KEY"
    ) or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("embedding API key 未配置（设置 embedding_api_key 或 OPENAI_API_KEY 环境变量）")

    if provider_type == "openai":
        from app.services.harness.embeddings.openai_provider import OpenAIEmbeddingProvider
        base_url = config.get("embedding_base_url")
        return OpenAIEmbeddingProvider(
            api_key=api_key, model=model, base_url=base_url
        )
    elif provider_type == "dashscope":
        from app.services.harness.embeddings.dashscope_provider import DashScopeEmbeddingProvider
        return DashScopeEmbeddingProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"不支持的 embedding provider: {provider_type}")