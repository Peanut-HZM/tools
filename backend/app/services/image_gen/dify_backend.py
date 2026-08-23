"""Dify 后端：包装现有 DifyClient.chat_* 多轮对话调用

按 BackendContext.operation 分发到对应的 chat_* 方法，
将 ChatRunResult 适配为统一的 BackendResult。

设计要点：
- 仅负责"调用 Dify"这一层，不处理配额 / 历史 / 降级（由上层编排）
- 需要 bytes → OSS URL 的转换（img2img / inpaint / upload_edit 需要签名 URL）
- DifyClient 不变，本类仅做参数映射 + 结果适配

参考：spec §5.2, plan Phase 3, task-17 brief
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Any, Optional

from app.services.dify_client import DifyClient
from app.services.image_gen.base import (
    BackendContext,
    BackendResult,
    IImageGenerationBackend,
)

logger = logging.getLogger(__name__)


# OSS 上传默认前缀（与 image_generation_service.py 保持一致）
_OSS_PREFIX_REF = "image-gen/ref"
_OSS_PREFIX_MASK = "image-gen/mask"
# 默认签名过期时间（秒）— 仅用于给 Dify 临时访问
_SIGNED_URL_EXPIRES = 300


class DifyBackend(IImageGenerationBackend):
    """Dify 后端 —— 包装 DifyClient 的 chat_* 多轮对话接口

    依赖注入：
      - dify_client: DifyClient（必需）
      - oss_svc: OssService 或兼容对象（可选；img2img / inpaint / upload_edit 必需）
    """

    def __init__(
        self,
        dify_client: DifyClient,
        oss_svc: Optional[Any] = None,
    ) -> None:
        self._dify = dify_client
        self._oss = oss_svc

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def run(self, ctx: BackendContext) -> BackendResult:
        """按 operation 分发到对应的 chat_* 方法"""
        logger.info("[dify_backend] operation=%s user=%s", ctx.operation, ctx.user_id)

        user_str = str(ctx.user_id)

        if ctx.operation == "text2img":
            chat_result = await self._dify.chat_text2img(
                prompt=ctx.query,
                conversation_id=ctx.conversation_id,
                size=ctx.size,
                n=ctx.n,
                style=None,
                model_preference="auto",
                user_id=user_str,
            )

        elif ctx.operation == "img2img":
            ref_url = self._upload_bytes_to_url(
                ctx.reference_image, ctx.reference_mime, _OSS_PREFIX_REF,
            )
            chat_result = await self._dify.chat_img2img(
                prompt=ctx.query,
                reference_url=ref_url,
                conversation_id=ctx.conversation_id,
                strength=ctx.strength if ctx.strength is not None else 0.6,
                size=ctx.size,
                model_preference="auto",
                user_id=user_str,
            )

        elif ctx.operation == "inpaint":
            ref_url = self._upload_bytes_to_url(
                ctx.reference_image, ctx.reference_mime, _OSS_PREFIX_REF,
            )
            mask_url = self._upload_bytes_to_url(
                ctx.mask_image, ctx.mask_mime, _OSS_PREFIX_MASK,
            )
            chat_result = await self._dify.chat_inpaint(
                prompt=ctx.query,
                image_url=ref_url,
                mask_url=mask_url,
                conversation_id=ctx.conversation_id,
                size=ctx.size,
                model_preference="auto",
                user_id=user_str,
            )

        elif ctx.operation == "upload_edit":
            ref_url = self._upload_bytes_to_url(
                ctx.reference_image, ctx.reference_mime, _OSS_PREFIX_REF,
            )
            chat_result = await self._dify.chat_upload_edit(
                image_url=ref_url,
                edit_type=ctx.edit_type or "upscale",
                conversation_id=ctx.conversation_id,
                prompt=ctx.query,
                user_id=user_str,
            )

        else:
            raise ValueError(f"未知 operation: {ctx.operation}")

        # 适配 ChatRunResult → BackendResult
        return BackendResult(
            image_urls=list(chat_result.image_urls or []),
            answer_text=chat_result.answer or "",
            conversation_id=chat_result.conversation_id or "",
            model_used=chat_result.model_used or "",
            backend="dify",
        )

    # ------------------------------------------------------------------
    # 内部工具：bytes → 签名 URL
    # ------------------------------------------------------------------

    def _upload_bytes_to_url(
        self,
        content: Optional[bytes],
        mime: Optional[str],
        prefix: str,
    ) -> str:
        """把 bytes 上传到 OSS 并返回签名 URL。

        Args:
            content: 图片字节（None 时返回空字符串，由 DifyClient 抛错）
            mime: MIME 类型（默认 image/png）
            prefix: OSS 对象名前缀

        Raises:
            RuntimeError: 需要 OSS 但未配置
        """
        if content is None:
            return ""

        if self._oss is None:
            raise RuntimeError(
                "[dify_backend] 需要 OSS 服务来上传参考图/蒙版，但未配置 oss_svc"
            )

        key = f"{prefix}/{uuid.uuid4().hex}.png"
        data = io.BytesIO(content)
        self._oss.upload_file(
            object_name=key,
            data=data,
            size=len(content),
            content_type=mime or "image/png",
            uploaded_by="image-gen",
        )
        signed_url = self._oss.sign_url("GET", key, _SIGNED_URL_EXPIRES)
        logger.debug("[dify_backend] 已上传 %d 字节 → %s", len(content), key)
        return signed_url or ""
