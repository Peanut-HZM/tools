"""DashScope (通义千问) Embedding Provider"""
import logging
from typing import List, Optional

from app.services.harness.embeddings.provider import TARGET_DIMENSION
from app.services.harness.embeddings.openai_provider import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


class DashScopeEmbeddingProvider:
    """通义千问 text-embedding 系列模型"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v3",
    ):
        self._api_key = api_key
        self._model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        import dashscope
        dashscope.api_key = self._api_key

        response = await dashscope.TextEmbedding.call(
            model=self._model, input=texts
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope embedding 失败: {response.status_code}"
            )
        raw_vectors = [
            item["embedding"] for item in response.output["embeddings"]
        ]
        return [
            OpenAIEmbeddingProvider._align_dimension(v, TARGET_DIMENSION)
            for v in raw_vectors
        ]

    async def validate(self) -> bool:
        try:
            await self.embed(["test"])
            return True
        except Exception as e:
            logger.warning("DashScope embedding validate 失败: %s", type(e).__name__)
            return False