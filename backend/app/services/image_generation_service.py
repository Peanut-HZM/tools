"""
Task 5.1 — ImageGenService（图像生成编排层）

编排流程：
  1. 降级检查 → 2. 提示词润色 → 3. 配额预留 →
  4. 上传参考图/蒙版 OSS → 生成签名 URL →
  5. 调 Dify → 6. 下载结果图 → 上传结果 OSS →
  7. 写历史 (completed) → 8. 提交配额 → 9. 重置降级计数 →
  10. 返回 GenerationResult

失败分支：释放配额 + 写 failed 历史 + 记录降级失败
取消分支（CancelledError）：释放配额 + 写 cancelled 历史
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import DifyError, QuotaExceeded, ServiceDegraded
from app.services.dify_client import DifyClient, DifyRunResult, ChatRunResult
from app.services.image_gen_history_service import ImageGenHistoryService
from app.services.image_gen_quota_service import ImageGenQuotaService
from app.utils.image_gen_constants import (
    OPERATION_TEXT2IMG,
    OPERATION_IMG2IMG,
    OPERATION_INPAINT,
    OPERATION_UPLOAD_EDIT,
    OSS_PREFIX_REF,
    OSS_PREFIX_MASK,
    OSS_PREFIX_RESULT,
    SIGNED_URL_EXPIRES_REF,
    SIGNED_URL_EXPIRES_RESULT,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_CANCELLED,
)

logger = logging.getLogger(__name__)


# ============================================================
# 返回结构
# ============================================================

@dataclass
class GenerationResult:
    """生成结果（返回给路由层）"""
    history_id: str
    image_urls: List[str]       # 1 小时签名 URL
    model_used: str
    duration_ms: int
    operation: str
    prompt: str


# ============================================================
# ImageGenService
# ============================================================

class ImageGenService:
    """
    图像生成编排服务。

    依赖注入：
      - db: SQLAlchemy session
      - dify_client: Dify 工作流客户端
      - quota_svc: 配额服务
      - oss_svc: OSS 存储服务（OssService 或兼容 mock）
      - history_svc: 历史记录服务
      - degradation_svc: 降级服务（可选，Phase 9 实现）
      - prompt_polisher: 提示词润色器（可选，Phase 8 实现）
    """

    def __init__(
        self,
        db: Session,
        dify_client: DifyClient,
        quota_svc: ImageGenQuotaService,
        oss_svc: Any,
        history_svc: ImageGenHistoryService,
        degradation_svc: Optional[Any] = None,
        prompt_polisher: Optional[Any] = None,
    ):
        self.db = db
        self.dify_client = dify_client
        self.quota_svc = quota_svc
        self.oss_svc = oss_svc
        self.history_svc = history_svc
        self.degradation_svc = degradation_svc
        self.prompt_polisher = prompt_polisher

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def generate(
        self,
        user_id: str,
        operation: str,
        prompt: str,
        # operation-specific params
        reference_image_bytes: Optional[bytes] = None,
        mask_bytes: Optional[bytes] = None,
        edit_type: Optional[str] = None,
        # common params
        size: str = "1024x1024",
        n: int = 1,
        style: Optional[str] = None,
        strength: float = 0.6,
        model_preference: str = "auto",
        polish_prompt: bool = False,
    ) -> GenerationResult:
        """
        图像生成主入口 — 编排所有步骤。

        Raises:
            ServiceDegraded: 服务降级中
            QuotaExceeded: 配额不足
            DifyError: Dify 调用失败
        """
        start_time = time.monotonic()

        # ---- 1. 降级检查 ----
        if self.degradation_svc is not None and self.degradation_svc.is_degraded():
            logger.warning("服务降级中，拒绝请求: user=%s op=%s", user_id, operation)
            raise ServiceDegraded()

        # ---- 2. 提示词润色 ----
        if polish_prompt and self.prompt_polisher is not None:
            prompt = await self.prompt_polisher.polish(prompt)
            logger.debug("提示词已润色: user=%s", user_id)

        # ---- 3. 配额预留 ----
        self.quota_svc.check_and_reserve(user_id, operation, n)

        # ---- 4-9. 执行生成（含异常处理） ----
        try:
            result = await self._do_generate(
                user_id=user_id,
                operation=operation,
                prompt=prompt,
                reference_image_bytes=reference_image_bytes,
                mask_bytes=mask_bytes,
                edit_type=edit_type,
                size=size,
                n=n,
                style=style,
                strength=strength,
                model_preference=model_preference,
                start_time=start_time,
            )
            return result

        except DifyError as e:
            # Dify 调用失败：释放配额 + 写 failed 历史 + 记录降级
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._write_failed_history(
                user_id=user_id,
                operation=operation,
                prompt=prompt,
                error_message=str(e),
                duration_ms=duration_ms,
                params=self._build_params(size, n, style, strength, model_preference),
            )
            self.quota_svc.release()
            if self.degradation_svc is not None:
                self.degradation_svc.record_failure()
            logger.error("Dify 调用失败: user=%s op=%s err=%s", user_id, operation, e)
            raise

        except asyncio.CancelledError:
            # 请求被取消：释放配额 + 写 cancelled 历史
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._write_cancelled_history(
                user_id=user_id,
                operation=operation,
                prompt=prompt,
                duration_ms=duration_ms,
                params=self._build_params(size, n, style, strength, model_preference),
            )
            self.quota_svc.release()
            logger.info("请求被取消: user=%s op=%s", user_id, operation)
            raise

    # ------------------------------------------------------------------
    # 多轮对话生成入口
    # ------------------------------------------------------------------

    async def chat_generate(
        self,
        user_id: str,
        operation: str,
        prompt: str,
        conversation_id: Optional[str],
        params: Dict[str, Any],
        reference_bytes: Optional[bytes] = None,
        mask_bytes: Optional[bytes] = None,
        edit_type: Optional[str] = None,
    ) -> ChatRunResult:
        """
        多轮对话生成入口。

        流程：
          1. 降级检查（同 generate）
          2. 上传参考图/蒙版 → 生成签名 URL
          3. 调对应 chat_* 方法
          4. 若 LLM 触发 <<GENERATE>> 且有图片 → 走完整 OSS + 历史 + 配额流程
          5. 若仅为追问 → 仅返回 answer + conversation_id
        """
        start_time = time.monotonic()

        # ---- 1. 降级检查 ----
        if self.degradation_svc is not None and self.degradation_svc.is_degraded():
            logger.warning("服务降级中，拒绝对话请求: user=%s op=%s", user_id, operation)
            raise ServiceDegraded()

        # ---- 2. 上传参考图/蒙版 ----
        reference_oss_key = None
        mask_oss_key = None
        reference_url = None
        mask_url = None

        if reference_bytes is not None:
            reference_oss_key = self._upload_to_oss(reference_bytes, OSS_PREFIX_REF, "image/png")
            reference_url = self.oss_svc.sign_url("GET", reference_oss_key, SIGNED_URL_EXPIRES_REF)

        if mask_bytes is not None:
            mask_oss_key = self._upload_to_oss(mask_bytes, OSS_PREFIX_MASK, "image/png")
            mask_url = self.oss_svc.sign_url("GET", mask_oss_key, SIGNED_URL_EXPIRES_REF)

        # ---- 3. 调对应 chat_* 方法 ----
        if operation == OPERATION_TEXT2IMG:
            dify_result = await self.dify_client.chat_text2img(
                prompt=prompt,
                conversation_id=conversation_id,
                size=params["size"],
                n=params.get("n", 1),
                style=params.get("style"),
                model_preference=params.get("model_preference", "auto"),
                user_id=user_id,
            )
        elif operation == OPERATION_IMG2IMG:
            dify_result = await self.dify_client.chat_img2img(
                prompt=prompt,
                reference_url=reference_url,
                conversation_id=conversation_id,
                strength=params.get("strength", 0.6),
                size=params["size"],
                model_preference=params.get("model_preference", "auto"),
                user_id=user_id,
            )
        elif operation == OPERATION_INPAINT:
            dify_result = await self.dify_client.chat_inpaint(
                prompt=prompt,
                image_url=reference_url,
                mask_url=mask_url,
                conversation_id=conversation_id,
                size=params["size"],
                model_preference=params.get("model_preference", "auto"),
                user_id=user_id,
            )
        elif operation == OPERATION_UPLOAD_EDIT:
            dify_result = await self.dify_client.chat_upload_edit(
                image_url=reference_url,
                edit_type=edit_type or "upscale",
                conversation_id=conversation_id,
                prompt=prompt,
                user_id=user_id,
            )
        else:
            raise DifyError(f"未知操作类型: {operation}", kind="config_error")

        # ---- 4. 判断是否触发生成 ----
        has_generate_marker = "<<GENERATE>>" in dify_result.answer
        has_images = len(dify_result.image_urls) > 0

        if not (has_generate_marker and has_images):
            # 仅追问：返回 answer + conversation_id（不扣配额、不写历史）
            logger.info(
                "对话追问: user=%s op=%s conv=%s",
                user_id, operation, dify_result.conversation_id,
            )
            return dify_result

        # ---- 5. 触发生成：走完整流程 ----
        self.quota_svc.check_and_reserve(user_id, operation, dify_result.image_urls and 1)

        try:
            # 下载结果图 → 上传 OSS
            result_oss_keys = []
            for idx, img_url in enumerate(dify_result.image_urls):
                img_bytes = await self._download_image(img_url)
                oss_key = self._upload_to_oss(img_bytes, OSS_PREFIX_RESULT, "image/png")
                result_oss_keys.append(oss_key)
            primary_result_key = result_oss_keys[0] if result_oss_keys else ""

            duration_ms = int((time.monotonic() - start_time) * 1000)
            history = self.history_svc.create_record(
                user_id=user_id,
                operation=operation,
                status=STATUS_SUCCESS,
                result_oss_key=primary_result_key,
                prompt=prompt,
                params=params,
                reference_oss_key=reference_oss_key,
                mask_oss_key=mask_oss_key,
                model_used=dify_result.model_used,
                duration_ms=duration_ms,
                conversation_id=dify_result.conversation_id,
            )
            self.quota_svc.commit()
            if self.degradation_svc is not None:
                self.degradation_svc.reset_failure_count()

            # 记录 history_id，供上层 /chat 端点透传
            dify_result.history_id = history.id

            # 生成签名 URL 返回
            signed_urls = [
                self.oss_svc.sign_url("GET", key, SIGNED_URL_EXPIRES_RESULT)
                for key in result_oss_keys
            ]

            # 覆盖 result 的 image_urls 为签名 URL
            dify_result.image_urls = signed_urls
            logger.info(
                "对话生成成功: user=%s op=%s history=%s conv=%s",
                user_id, operation, history.id, dify_result.conversation_id,
            )
            return dify_result

        except Exception:
            # 任何异常（DifyError / 网络错误 / OSS 异常等）都必须释放预留配额，
            # 避免配额永久被占用（详见 final-review Important #1）
            self.quota_svc.release()
            raise

    # ------------------------------------------------------------------
    # 内部编排逻辑
    # ------------------------------------------------------------------

    async def _do_generate(
        self,
        user_id: str,
        operation: str,
        prompt: str,
        reference_image_bytes: Optional[bytes],
        mask_bytes: Optional[bytes],
        edit_type: Optional[str],
        size: str,
        n: int,
        style: Optional[str],
        strength: float,
        model_preference: str,
        start_time: float,
    ) -> GenerationResult:
        """
        实际生成流程（配额已预留后调用）。

        步骤：
          a. 上传参考图/蒙版到 OSS → 生成 300s 签名 URL
          b. 调 Dify 对应 operation
          c. 下载结果图 → 上传 OSS
          d. 写 completed 历史
          e. 提交配额
          f. 重置降级计数
          g. 返回 GenerationResult
        """
        params = self._build_params(size, n, style, strength, model_preference)

        # ---- a. 上传参考图/蒙版 → 签名 URL ----
        reference_oss_key = None
        mask_oss_key = None
        reference_url = None
        mask_url = None

        if reference_image_bytes is not None:
            reference_oss_key = self._upload_to_oss(
                reference_image_bytes, OSS_PREFIX_REF, "image/png",
            )
            reference_url = self.oss_svc.sign_url("GET", reference_oss_key, SIGNED_URL_EXPIRES_REF)

        if mask_bytes is not None:
            mask_oss_key = self._upload_to_oss(
                mask_bytes, OSS_PREFIX_MASK, "image/png",
            )
            mask_url = self.oss_svc.sign_url("GET", mask_oss_key, SIGNED_URL_EXPIRES_REF)

        # ---- b. 调 Dify ----
        dify_result: DifyRunResult = await self._call_dify(
            operation=operation,
            prompt=prompt,
            reference_url=reference_url,
            mask_url=mask_url,
            edit_type=edit_type,
            size=size,
            n=n,
            style=style,
            strength=strength,
            model_preference=model_preference,
            user_id=user_id,
        )

        # ---- c. 下载结果图 → 上传 OSS ----
        result_oss_keys = []
        for idx, img_url in enumerate(dify_result.image_urls):
            img_bytes = await self._download_image(img_url)
            oss_key = self._upload_to_oss(img_bytes, OSS_PREFIX_RESULT, "image/png")
            result_oss_keys.append(oss_key)

        # 第一张图的 key 作为主 result_oss_key
        primary_result_key = result_oss_keys[0] if result_oss_keys else ""

        # ---- d. 写 completed 历史 ----
        duration_ms = int((time.monotonic() - start_time) * 1000)
        # 多图时 params 中保存完整 key 列表
        if len(result_oss_keys) > 1:
            params["result_oss_keys"] = result_oss_keys

        history = self.history_svc.create_record(
            user_id=user_id,
            operation=operation,
            status=STATUS_SUCCESS,
            result_oss_key=primary_result_key,
            prompt=prompt,
            params=params,
            reference_oss_key=reference_oss_key,
            mask_oss_key=mask_oss_key,
            model_used=dify_result.model_used,
            duration_ms=duration_ms,
        )

        # ---- e. 提交配额 ----
        self.quota_svc.commit()

        # ---- f. 重置降级计数 ----
        if self.degradation_svc is not None:
            self.degradation_svc.reset_failure_count()

        # ---- g. 生成签名 URL 返回 ----
        signed_urls = []
        for key in result_oss_keys:
            signed_url = self.oss_svc.sign_url("GET", key, SIGNED_URL_EXPIRES_RESULT)
            signed_urls.append(signed_url)

        logger.info(
            "生成成功: user=%s op=%s history=%s n=%d duration=%dms",
            user_id, operation, history.id, len(result_oss_keys), duration_ms,
        )

        return GenerationResult(
            history_id=history.id,
            image_urls=signed_urls,
            model_used=dify_result.model_used,
            duration_ms=duration_ms,
            operation=operation,
            prompt=prompt,
        )

    # ------------------------------------------------------------------
    # Dify 调用分发
    # ------------------------------------------------------------------

    async def _call_dify(
        self,
        operation: str,
        prompt: str,
        reference_url: Optional[str],
        mask_url: Optional[str],
        edit_type: Optional[str],
        size: str,
        n: int,
        style: Optional[str],
        strength: float,
        model_preference: str,
        user_id: str,
    ) -> DifyRunResult:
        """根据 operation 分发到对应的 DifyClient 方法"""
        if operation == OPERATION_TEXT2IMG:
            return await self.dify_client.run_text2img(
                prompt=prompt,
                size=size,
                n=n,
                style=style,
                model_preference=model_preference,
                user_id=user_id,
            )
        elif operation == OPERATION_IMG2IMG:
            if not reference_url:
                raise DifyError("img2img 需要参考图", kind="config_error")
            return await self.dify_client.run_img2img(
                prompt=prompt,
                reference_url=reference_url,
                strength=strength,
                size=size,
                model_preference=model_preference,
                user_id=user_id,
            )
        elif operation == OPERATION_INPAINT:
            if not reference_url or not mask_url:
                raise DifyError("inpaint 需要参考图和蒙版图", kind="config_error")
            return await self.dify_client.run_inpaint(
                prompt=prompt,
                image_url=reference_url,
                mask_url=mask_url,
                size=size,
                model_preference=model_preference,
                user_id=user_id,
            )
        elif operation == OPERATION_UPLOAD_EDIT:
            if not reference_url:
                raise DifyError("upload_edit 需要待编辑图", kind="config_error")
            return await self.dify_client.run_upload_edit(
                image_url=reference_url,
                edit_type=edit_type or "upscale",
                prompt=prompt,
                user_id=user_id,
            )
        else:
            raise DifyError(f"未知操作类型: {operation}", kind="config_error")

    # ------------------------------------------------------------------
    # OSS 辅助方法
    # ------------------------------------------------------------------

    def _upload_to_oss(self, content: bytes, prefix: str, content_type: str) -> str:
        """上传字节到 OSS，返回 object key"""
        key = f"{prefix}/{uuid.uuid4().hex}.png"
        data = io.BytesIO(content)
        self.oss_svc.upload_file(
            object_name=key,
            data=data,
            size=len(content),
            content_type=content_type,
            uploaded_by="image-gen",
        )
        return key

    async def _download_image(self, url: str) -> bytes:
        """
        下载图片字节。

        优先使用 oss_svc.download_file（若 url 是 OSS 签名 URL），
        否则用 httpx 下载。
        """
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    # ------------------------------------------------------------------
    # 失败/取消历史写入
    # ------------------------------------------------------------------

    def _write_failed_history(
        self,
        user_id: str,
        operation: str,
        prompt: str,
        error_message: str,
        duration_ms: int,
        params: dict,
    ) -> None:
        """写入失败历史记录（result_oss_key 为空串）"""
        try:
            self.history_svc.create_record(
                user_id=user_id,
                operation=operation,
                status=STATUS_FAILED,
                result_oss_key="",
                prompt=prompt,
                params=params,
                error_message=error_message,
                duration_ms=duration_ms,
            )
            self.db.commit()
        except Exception:
            logger.error("写入失败历史时出错", exc_info=True)
            self.db.rollback()

    def _write_cancelled_history(
        self,
        user_id: str,
        operation: str,
        prompt: str,
        duration_ms: int,
        params: dict,
    ) -> None:
        """写入取消历史记录（result_oss_key 为空串）"""
        try:
            self.history_svc.create_record(
                user_id=user_id,
                operation=operation,
                status=STATUS_CANCELLED,
                result_oss_key="",
                prompt=prompt,
                params=params,
                duration_ms=duration_ms,
            )
            self.db.commit()
        except Exception:
            logger.error("写入取消历史时出错", exc_info=True)
            self.db.rollback()

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _build_params(
        size: str,
        n: int,
        style: Optional[str],
        strength: float,
        model_preference: str,
    ) -> dict:
        """构建 params JSON 字典"""
        return {
            "size": size,
            "n": n,
            "style": style,
            "strength": strength,
            "model_preference": model_preference,
        }

    # ------------------------------------------------------------------
    # BackendRegistry 分发入口（M5 策略拆分）
    # ------------------------------------------------------------------

    async def chat_generate_dispatch(
        self,
        backend: str,
        user_id: uuid.UUID,
        operation: str,
        query: str,
        conversation_id: Optional[str],
        reference_image: Optional[bytes],
        mask_image: Optional[bytes],
        size: str,
        n: int,
        strength: Optional[float] = None,
        edit_type: Optional[str] = None,
    ):
        """按 backend 参数通过 BackendRegistry 分发到对应后端

        本方法只负责：
          1. 构造 BackendContext
          2. 从 BackendRegistry 取对应后端
          3. 调用 backend.run(ctx)
          4. 返回 BackendResult

        quota / OSS / history 等共享逻辑不在此处（在调用方）。
        """
        from app.services.image_gen.backends import BackendRegistry
        from app.services.image_gen.base import BackendContext

        ctx = BackendContext(
            user_id=user_id,
            operation=operation,
            query=query,
            conversation_id=conversation_id,
            reference_image=reference_image,
            reference_mime=None,
            mask_image=mask_image,
            mask_mime=None,
            size=size,
            n=n,
            strength=strength,
            edit_type=edit_type,
        )
        logger.info("[chat_generate_dispatch] backend=%s op=%s user=%s", backend, operation, user_id)
        backend_impl = BackendRegistry.get(backend)
        return await backend_impl.run(ctx)

    # ------------------------------------------------------------------
    # 后端懒加载注册
    # ------------------------------------------------------------------

    def _ensure_backends_registered(self) -> None:
        """懒加载注册图像生成后端

        生产环境在首次请求时注册（依赖 ImageGenService 已注入的 db / dify_client / oss_svc）。
        测试环境由测试手动 BackendRegistry.register 覆盖即可（注册同名后端等价于替换）。
        """
        from app.services.image_gen.backends import BackendRegistry
        from app.services.image_gen.dify_backend import DifyBackend
        from app.services.image_gen.selfdev_backend import SelfDevelopedBackend
        from app.services.image_gen.agent_orchestrator import AgentOrchestrator
        from app.services.image_gen.tool_executor import ToolExecutor
        from app.services.image_gen.conversation_repo import ConversationRepository
        from app.services.llm.ordered_gateway import OrderedLLMGateway

        # dify 后端：包装 DifyClient
        if "dify" not in BackendRegistry._REGISTRY:
            BackendRegistry.register("dify", DifyBackend(
                dify_client=self.dify_client,
                oss_svc=self.oss_svc,
            ))

        # selfdev 后端：自研 Agent 编排
        if "selfdev" not in BackendRegistry._REGISTRY:
            gateway = OrderedLLMGateway(db=self.db)
            BackendRegistry.register("selfdev", SelfDevelopedBackend(
                orchestrator=AgentOrchestrator(gateway=gateway),
                executor=ToolExecutor(gateway=gateway, oss_svc=self.oss_svc),
                conv_repo=ConversationRepository(db=self.db),
            ))

    # ------------------------------------------------------------------
    # 带 quota + history 的 dispatch 入口（M7 自研路径接入）
    # ------------------------------------------------------------------

    async def chat_generate_dispatch_with_quota(
        self,
        backend: str,
        user_id: uuid.UUID,
        operation: str,
        query: str,
        conversation_id: Optional[str],
        reference_image: Optional[bytes],
        mask_image: Optional[bytes],
        size: str,
        n: int,
        strength: Optional[float] = None,
        edit_type: Optional[str] = None,
    ):
        """按 backend 分发 + quota / history 共享逻辑

        流程：
          1. check_and_reserve（预留 quota）
          2. 调用 chat_generate_dispatch 执行实际生成
          3. 若 result.image_urls 非空 → commit quota + 写 history
          4. 若 image_urls 为空 → release quota
          5. 任何异常 → release quota 并抛出
        """
        # 0. 确保后端已注册（懒加载：生产环境首次请求时注册，测试环境由测试手动注册覆盖）
        self._ensure_backends_registered()

        # 1. 预留 quota（无论后续是否生成）
        # user_id 在此处是 uuid.UUID 对象，但 image_gen_quota.user_id 是 varchar，
        # 必须转成字符串，否则 PostgreSQL 无法比较 uuid = varchar
        self.quota_svc.check_and_reserve(user_id=str(user_id), operation=operation)

        try:
            # 2. 走 dispatch
            result = await self.chat_generate_dispatch(
                backend=backend,
                user_id=user_id,
                operation=operation,
                query=query,
                conversation_id=conversation_id,
                reference_image=reference_image,
                mask_image=mask_image,
                size=size,
                n=n,
                strength=strength,
                edit_type=edit_type,
            )

            # 3. quota commit or release
            if result.image_urls:
                self.quota_svc.commit()
                # 4. 写历史记录（带 backend 字段）
                self.history_svc.create_record(
                    user_id=str(user_id),
                    operation=operation,
                    status=STATUS_SUCCESS,
                    prompt=query,
                    model_used=result.model_used,
                    conversation_id=result.conversation_id,
                    backend=result.backend,
                )
            else:
                # image_urls 为空 → 释放预留
                self.quota_svc.release()

            return result
        except Exception:
            # 任何异常都必须释放预留配额
            self.quota_svc.release()
            raise

    # ------------------------------------------------------------------
    # 委托方法 — 历史查询
    # ------------------------------------------------------------------

    def get_history(self, user_id: str, skip: int = 0, limit: int = 20, **kwargs):
        """委托给 HistoryService 查询历史记录"""
        return self.history_svc.list_records(user_id, skip, limit, **kwargs)
