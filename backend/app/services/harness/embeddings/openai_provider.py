"""OpenAI Embedding Provider（兼容 API 兼容服务）"""
import logging
from typing import List, Optional

from app.services.harness.embeddings.provider import TARGET_DIMENSION

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    """OpenAI text-embedding 系列模型"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def _get_client(self):
        from openai import AsyncOpenAI
        kwargs = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return AsyncOpenAI(**kwargs)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        response = await client.embeddings.create(
            input=texts, model=self._model
        )
        raw_vectors = [item.embedding for item in response.data]
        return [self._align_dimension(v, TARGET_DIMENSION) for v in raw_vectors]

    async def validate(self) -> bool:
        try:
            await self.embed(["test"])
            return True
        except Exception as e:
            logger.warning("OpenAI embedding validate 失败: %s", type(e).__name__)
            return False

    @staticmethod
    def _align_dimension(vec: List[float], target: int) -> List[float]:
        """对齐向量维度：补零或截断"""
        if len(vec) == target:
            return vec
        if len(vec) < target:
            return vec + [0.0] * (target - len(vec))
        # 截断 + warning
        logger.warning(
            "embedding 维度 %d > 目标 %d，截断可能损失精度",
            len(vec), target,
        )
        return vec[:target]