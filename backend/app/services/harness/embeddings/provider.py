"""EmbeddingProvider 协议 + 常量"""
from typing import Protocol, List

# DB 固定维度（与 migration VECTOR(1536) 一致）
TARGET_DIMENSION = 1536


class EmbeddingProvider(Protocol):
    """向量生成提供者协议"""

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding，返回维度对齐到 TARGET_DIMENSION"""
        ...

    async def validate(self) -> bool:
        """验证 API 可用性（发一次测试请求）"""
        ...