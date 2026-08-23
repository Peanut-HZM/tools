"""图像生成适配器抽象基类

与 LLMProvider 平级，不共用基类——图像生成无 messages / 无流式语义。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Optional

from app.services.llm.exceptions import OperationNotSupportedError


class ImageGenAdapter(ABC):
    """图像生成适配器基类

    子类需实现：
      - SUPPORTED_OPERATIONS: 类属性，列出支持的 operation
      - _do_generate: 实际生成逻辑（由 generate 在鉴权后调用）
      - test_connection: 连接测试
    """

    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset()
    """子类覆盖：支持的 operation 集合"""

    # provider_type 供 ensure_supported 抛错时使用；子类可覆盖
    provider_type: str = "image_gen"

    async def generate(
        self,
        operation: str,
        prompt: str,
        *,
        size: str = "1024x1024",
        n: int = 1,
        reference_image: Optional[bytes] = None,
        reference_mime: Optional[str] = None,
        mask_image: Optional[bytes] = None,
        mask_mime: Optional[str] = None,
        strength: Optional[float] = None,
        edit_type: Optional[str] = None,
        **provider_specific,
    ) -> list[bytes]:
        """生成图像，返回 N 张图的二进制列表

        先检查 operation 是否在 SUPPORTED_OPERATIONS 中，
        不支持则抛 OperationNotSupportedError；支持则委托给 _do_generate。
        """
        self.ensure_supported(operation)
        return await self._do_generate(
            operation,
            prompt,
            size=size,
            n=n,
            reference_image=reference_image,
            reference_mime=reference_mime,
            mask_image=mask_image,
            mask_mime=mask_mime,
            strength=strength,
            edit_type=edit_type,
            **provider_specific,
        )

    @abstractmethod
    async def _do_generate(
        self,
        operation: str,
        prompt: str,
        *,
        size: str = "1024x1024",
        n: int = 1,
        reference_image: Optional[bytes] = None,
        reference_mime: Optional[str] = None,
        mask_image: Optional[bytes] = None,
        mask_mime: Optional[str] = None,
        strength: Optional[float] = None,
        edit_type: Optional[str] = None,
        **provider_specific,
    ) -> list[bytes]:
        """子类实现实际生成逻辑"""

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """连接测试。返回 (成功, 消息)。"""

    def supports_operation(self, operation: str) -> bool:
        """判断当前 adapter 是否支持该 operation"""
        return operation in self.SUPPORTED_OPERATIONS

    def ensure_supported(self, operation: str) -> None:
        """不支持时抛 OperationNotSupportedError"""
        if not self.supports_operation(operation):
            raise OperationNotSupportedError(self.provider_type, operation)
