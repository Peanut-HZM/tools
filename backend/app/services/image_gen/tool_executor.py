"""图像生成 tool 执行器

收到 brain 的 generate_image tool_call 后：
  1. 解析 arguments（operation / prompt / 参考图 URL 等）
  2. 若有参考图 / 蒙版图 URL，先下载到内存
  3. 走 OrderedLLMGateway.generate(category="image_gen", ...) 调 image_gen adapter
  4. 将结果字节上传 OSS
  5. 生成签名 URL 并返回
"""

from __future__ import annotations

import logging
import uuid
from io import BytesIO
from typing import Any

import httpx

from app.services.llm.ordered_gateway import OrderedLLMGateway
from app.services.oss_service import OssService
from app.utils.image_gen_constants import (
    OSS_PREFIX_RESULT,
    SIGNED_URL_EXPIRES_RESULT,
)

logger = logging.getLogger(__name__)


class ToolExecutor:
    """图像生成 tool 执行器

    将 brain 输出的 generate_image tool_call 翻译为对 image_gen adapter 的调用，
    并把生成的图片上传 OSS、返回签名 URL。
    """

    def __init__(self, gateway: OrderedLLMGateway, oss_svc: OssService):
        self._gateway = gateway
        self._oss = oss_svc

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    async def execute(self, tool_call: dict) -> dict[str, Any]:
        """执行 generate_image tool_call

        Args:
            tool_call: {"id": "...", "name": "generate_image", "arguments": {...}}

        Returns:
            {"image_urls": [...], "tool_call_id": "..."}
        """
        args = tool_call["arguments"]
        operation: str = args["operation"]
        prompt: str = args["prompt"]
        size: str = args.get("size", "1024x1024")
        n: int = args.get("n", 1)
        strength: float | None = args.get("strength")
        edit_type: str | None = args.get("edit_type")

        # 下载参考图 / 蒙版图（如有）
        reference_image = await self._download(args.get("reference_image_url"))
        mask_image = await self._download(args.get("mask_image_url"))

        # 调 image_gen adapter
        images_bytes: list[bytes] = await self._gateway.generate(
            category="image_gen",
            operation=operation,
            prompt=prompt,
            size=size,
            n=n,
            reference_image=reference_image,
            mask_image=mask_image,
            strength=strength,
            edit_type=edit_type,
        )

        # 上传 OSS 并生成签名 URL
        image_urls: list[str] = []
        for img in images_bytes:
            url = self._upload_and_sign(img)
            if url:
                image_urls.append(url)

        logger.info(
            "[tool_executor] operation=%s generated=%d images",
            operation,
            len(image_urls),
        )
        return {"image_urls": image_urls, "tool_call_id": tool_call["id"]}

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _upload_and_sign(self, data: bytes) -> str | None:
        """将图片字节上传 OSS 并返回签名 URL；上传失败返回 None"""
        object_name = f"{OSS_PREFIX_RESULT}/{uuid.uuid4().hex}.png"
        result = self._oss.upload_file(
            object_name=object_name,
            data=BytesIO(data),
            size=len(data),
            content_type="image/png",
            uploaded_by="image-gen",
        )
        if result is None:
            logger.error("[tool_executor] OSS 上传失败 object=%s", object_name)
            return None
        # 生成签名 URL，前端通过该 URL 访问图片
        return self._oss.sign_url("GET", object_name, SIGNED_URL_EXPIRES_RESULT)

    async def _download(self, url: str | None) -> bytes | None:
        """从 URL 下载图片（可能是 OSS 签名 URL 或任意 https URL）"""
        if not url:
            return None
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
