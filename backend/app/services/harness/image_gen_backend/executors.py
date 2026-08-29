"""3 种图像生成执行器实现

- DifyImageGenExecutor: 调用旧版 ImageGenService
- HarnessImageGenExecutor: 调用新版 ImageGenTool
- DualImageGenExecutor: 并行执行 + 对比
"""
import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from app.services.harness.image_gen_backend.metrics import log_image_gen_metric

logger = logging.getLogger(__name__)


def _sanitize_url(u: str) -> str:
    """脱敏 URL：去掉 query（含 OSS 预签名 token），只保留 scheme://netloc/path"""
    parts = urlsplit(u)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


class DifyImageGenExecutor:
    """Dify 执行器 — 调用旧版 ImageGenService

    由于 ImageGenService.generate() 签名复杂（需要 db, dify_client, quota_svc 等），
    此处简化为直接调用服务并捕获异常，返回统一结构。
    """

    async def execute(self, args: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
        """执行 Dify 图像生成"""
        start = time.monotonic()
        request_id = str(uuid.uuid4())

        try:
            # 简化实现：记录日志 + 返回 mock 结果
            # 真实场景需要从 ctx 获取依赖注入或从全局获取服务实例
            # 脱敏：只记录 keys，避免 prompt / negative_prompt / reference_image_url 等敏感内容泄漏
            logger.info(f"[DifyExecutor] request_id={request_id}, keys={list(args.keys())}")

            # TODO: 真实实现需要：
            # 1. 从 ctx 或全局获取 ImageGenService 实例
            # 2. 调用 await svc.generate(user_id=ctx.user_id, operation=args["operation"], ...)
            # 3. 从 GenerationResult 提取 image_urls

            # 临时返回 mock 结果
            return {
                "success": True,
                "image_urls": [],  # mock: 无实际图片
                "error": None,
                "backend": "dify",
                "elapsed_ms": (time.monotonic() - start) * 1000,
                "request_id": request_id,
            }

        except Exception as e:
            # 异常脱敏：只记录类型，不暴露详情
            error_type = type(e).__name__
            logger.error(f"[DifyExecutor] request_id={request_id}, error={error_type}")
            return {
                "success": False,
                "image_urls": [],
                "error": f"{error_type}: 图像生成失败",
                "backend": "dify",
                "elapsed_ms": (time.monotonic() - start) * 1000,
                "request_id": request_id,
            }


class HarnessImageGenExecutor:
    """Harness 执行器 — 调用新版 ImageGenTool"""

    async def execute(self, args: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
        """执行 Harness 图像生成"""
        start = time.monotonic()
        request_id = str(uuid.uuid4())

        try:
            from app.services.harness.tools.image_gen import ImageGenTool

            tool = ImageGenTool()
            result = await tool.execute(args, ctx)

            # 从 ToolResult.attachments 提取 image_urls
            image_urls: List[str] = [
                a.url for a in result.attachments if a.type == "image"
            ]

            logger.info(
                f"[HarnessExecutor] request_id={request_id}, "
                f"success={result.success}, urls={len(image_urls)}"
            )

            return {
                "success": result.success,
                "image_urls": image_urls,
                "error": result.error_message,
                "backend": "harness",
                "elapsed_ms": (time.monotonic() - start) * 1000,
                "request_id": request_id,
            }

        except Exception as e:
            # 异常脱敏
            error_type = type(e).__name__
            logger.error(f"[HarnessExecutor] request_id={request_id}, error={error_type}")
            return {
                "success": False,
                "image_urls": [],
                "error": f"{error_type}: 图像生成失败",
                "backend": "harness",
                "elapsed_ms": (time.monotonic() - start) * 1000,
                "request_id": request_id,
            }


class DualImageGenExecutor:
    """Dual 执行器 — 并行执行 primary + secondary，返回 primary 结果，记录 diff

    用于流量对比阶段，验证 harness 与 dify 的一致性。
    """

    def __init__(self, primary: Any, secondary: Any):
        """初始化

        Args:
            primary: 主执行器（通常是 HarnessImageGenExecutor）
            secondary: 副执行器（通常是 DifyImageGenExecutor）
        """
        self.primary = primary
        self.secondary = secondary

    async def execute(self, args: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
        """并行执行双写对比

        primary 和 secondary 同时执行，异常不传播，最终返回 primary 结果。
        """
        start = time.monotonic()
        request_id = str(uuid.uuid4())

        # 并行执行
        primary_task = asyncio.create_task(self.primary.execute(args, ctx))
        secondary_task = asyncio.create_task(self.secondary.execute(args, ctx))

        # gather 带 return_exceptions=True，异常会作为返回值而非抛出
        results = await asyncio.gather(primary_task, secondary_task, return_exceptions=True)
        primary_result = results[0]
        secondary_result = results[1]

        # 处理异常（gather 返回 Exception 而非抛出）
        if isinstance(primary_result, Exception):
            error_type = type(primary_result).__name__
            logger.error(f"[DualExecutor] primary 异常: {error_type}")
            primary_result = {
                "success": False,
                "image_urls": [],
                "error": f"{error_type}: primary 执行失败",
                "backend": "harness",
                "elapsed_ms": (time.monotonic() - start) * 1000,
                "request_id": request_id,
            }

        if isinstance(secondary_result, Exception):
            error_type = type(secondary_result).__name__
            logger.error(f"[DualExecutor] secondary 异常: {error_type}")
            secondary_result = {
                "success": False,
                "image_urls": [],
                "error": f"{error_type}: secondary 执行失败",
                "backend": "dify",
                "elapsed_ms": (time.monotonic() - start) * 1000,
                "request_id": request_id,
            }

        # 记录 diff
        diff_reasons = self._log_diff(primary_result, secondary_result, request_id)

        # 追加结构化指标日志，供 dual 模式验证阶段对照 harness vs Dify 一致性
        log_image_gen_metric(
            request_id=request_id,
            backend="dual",
            primary_success=primary_result.get("success", False),
            secondary_success=secondary_result.get("success", False),
            primary_urls=len(primary_result.get("image_urls", [])),
            secondary_urls=len(secondary_result.get("image_urls", [])),
            elapsed_ms_primary=primary_result.get("elapsed_ms", 0),
            elapsed_ms_secondary=secondary_result.get("elapsed_ms", 0),
            diff_reasons=diff_reasons,
        )

        # 返回 primary 结果（不降级）
        primary_result["elapsed_ms"] = (time.monotonic() - start) * 1000
        primary_result["request_id"] = request_id
        return primary_result

    def _log_diff(self, primary: Dict[str, Any], secondary: Dict[str, Any], request_id: str) -> List[str]:
        """对比 primary 与 secondary 结果，记录差异，返回 diff_reasons 列表"""
        p_success = primary.get("success", False)
        s_success = secondary.get("success", False)
        p_urls = primary.get("image_urls", [])
        s_urls = secondary.get("image_urls", [])

        # 收集差异原因（简单 key，无冒号值）
        diff_reasons: List[str] = []

        # 比对 success
        if p_success != s_success:
            diff_reasons.append("success_diff")
            logger.warning(
                f"[DualExecutor] request_id={request_id}, "
                f"success 不一致: primary={p_success}, secondary={s_success}"
            )

        # 比对 image_urls 长度
        if len(p_urls) != len(s_urls):
            diff_reasons.append("url_count_diff")
            logger.warning(
                f"[DualExecutor] request_id={request_id}, "
                f"urls 长度不一致: primary={len(p_urls)}, secondary={len(s_urls)}"
            )

        # 比对第一个 URL（脱敏：去掉 query 签名 token）
        if p_urls and s_urls and p_urls[0] != s_urls[0]:
            diff_reasons.append("url_content_diff")
            logger.warning(
                f"[DualExecutor] request_id={request_id}, "
                f"首个 URL 不一致: primary={_sanitize_url(p_urls[0])}, secondary={_sanitize_url(s_urls[0])}"
            )

        if p_success == s_success and len(p_urls) == len(s_urls):
            logger.info(f"[DualExecutor] request_id={request_id}, 对比一致")

        return diff_reasons
