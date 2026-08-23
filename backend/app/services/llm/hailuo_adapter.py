"""海螺图像生成适配器（桩实现）

Task 12 将补充真实实现；此处仅提供最小骨架让 Factory 可导入、可实例化。
"""

from __future__ import annotations

from typing import ClassVar, Optional

from app.services.llm.image_gen_base import ImageGenAdapter


class HailuoAdapter(ImageGenAdapter):
    """海螺适配器"""

    provider_type: str = "hailuo"
    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset({"text2img"})

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", **kw):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def _do_generate(self, operation, prompt, **kw):
        raise NotImplementedError("真实实现将在 Task 12 补充")

    async def test_connection(self) -> tuple[bool, str]:
        raise NotImplementedError("真实实现将在 Task 12 补充")
