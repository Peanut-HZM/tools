"""海螺（MiniMax）图像生成适配器

当前 MiniMax 公开 API 仅 text2img 稳定；其余 operation 抛 OperationNotSupportedError，
由 OrderedLLMGateway 自动跳过。
"""

from __future__ import annotations

from typing import ClassVar, Optional

from app.services.llm.image_gen_base import ImageGenAdapter


class HailuoAdapter(ImageGenAdapter):
    """海螺适配器（占位）"""

    provider_type: str = "hailuo"
    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset({"text2img"})

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", **kw):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    async def _do_generate(self, operation, prompt, **kw):
        # TODO: 实际接入 MiniMax API（API 端点/鉴权待确认）
        raise NotImplementedError("Hailuo adapter 待接入实际 API")

    async def test_connection(self) -> tuple[bool, str]:
        """连接测试（占位）"""
        return (True, "ok")
