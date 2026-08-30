"""video_gen BuiltinTool — 视频生成工具

支持 text2video（文字生成视频）操作。
通过 VideoModelProvider 抽象支持多 provider，含 prompt 润色和 fallback 链。

安全说明（与 image_gen 一致）：
- 出参 URL 校验 scheme（仅 http/https）
- 错误消息脱敏：仅回传已脱敏的 VideoGenError 文本
- SSRF 防护由 provider 内部 _resolve_and_check_ip 保障
"""
import logging
import mimetypes
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

from app.services.harness.video_provider.base import (
    VideoGenError,
    VideoGenParams,
    VideoGenResult,
    _resolve_and_check_ip,
)
from app.services.harness.tool_protocol import (
    Attachment,
    ToolContext,
    ToolResult,
)
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.prompt_refiner import refine_image_prompt

logger = logging.getLogger(__name__)

# 允许的 URL scheme
_ALLOWED_URL_SCHEMES = ("http", "https")
_MAX_URL_LEN = 2048

# MiniMax 视频参数范围
_ALLOWED_RESOLUTIONS = ("480P", "768P", "2K")
_DEFAULT_RESOLUTION = "768P"
_ALLOWED_RATIOS = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
_DEFAULT_RATIO = "16:9"
_MIN_DURATION = 4
_MAX_DURATION = 15
_DEFAULT_DURATION = 5


def _is_safe_http_url(raw: Any) -> bool:
    """校验 URL 是否为安全的 http/https 链接"""
    if not raw or not isinstance(raw, str):
        return False
    candidate = raw.strip()
    if not candidate or len(candidate) > _MAX_URL_LEN:
        return False
    try:
        parsed = urlparse(candidate)
    except Exception:
        return False
    if parsed.scheme.lower() not in _ALLOWED_URL_SCHEMES:
        return False
    if parsed.username or parsed.password:
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if not _resolve_and_check_ip(hostname):
        return False
    return True


def _guess_video_name(url: str) -> Tuple[str, str]:
    """推断附件文件名与 MIME 类型"""
    try:
        path = urlparse(url).path
    except Exception:
        path = ""
    mime, _ = mimetypes.guess_type(path)
    if not mime or not mime.startswith("video/"):
        mime = "video/mp4"
    ext = mimetypes.guess_extension(mime) or ".mp4"
    return f"video-gen{ext}", mime


class VideoGenTool(BuiltinTool):
    """视频生成工具"""

    name = "video_gen"
    display_name = "视频生成"
    description = (
        "根据文字描述生成短视频（text2video）。"
        "支持设置分辨率、时长和宽高比。生成的视频自动保存到文件服务器。"
    )
    parameters_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "视频内容描述（中文即可，系统自动润色为英文）",
            },
            "resolution": {
                "type": "string",
                "enum": list(_ALLOWED_RESOLUTIONS),
                "default": _DEFAULT_RESOLUTION,
                "description": "视频分辨率（480P/768P/2K）",
            },
            "duration": {
                "type": "integer",
                "minimum": _MIN_DURATION,
                "maximum": _MAX_DURATION,
                "default": _DEFAULT_DURATION,
                "description": "视频时长（4-15秒）",
            },
            "ratio": {
                "type": "string",
                "enum": list(_ALLOWED_RATIOS),
                "default": _DEFAULT_RATIO,
                "description": "视频宽高比",
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "video_url": {"type": "string"},
            "model_used": {"type": "string"},
            "revised_prompt": {"type": "string"},
            "task_id": {"type": "string"},
        },
    }

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        """执行视频生成

        流程：参数校验 → prompt 润色 → 解析 provider 链 → 依次尝试 → 组装结果 + 发事件
        """
        args = args or {}

        # 1. 参数校验
        prompt = str(args.get("prompt") or "").strip()
        if not prompt:
            return ToolResult.error("prompt 不能为空")

        # 2. Prompt 润色
        revised_prompt = await refine_image_prompt(prompt, ctx)
        if not revised_prompt:
            revised_prompt = prompt

        # 3. 构造参数
        params = VideoGenParams(
            resolution=self._normalize_resolution(args.get("resolution")),
            duration=self._normalize_duration(args.get("duration")),
            ratio=self._normalize_ratio(args.get("ratio")),
        )

        # 4. 解析 provider 链
        provider_chain = self._resolve_provider_chain(ctx)
        if not provider_chain:
            return ToolResult.error("无可用视频模型，请在 Agent 配置中绑定视频模型")

        last_error: Optional[BaseException] = None
        for model_name, provider in provider_chain:
            # 取消检查
            cancel_event = getattr(ctx, "cancel_event", None)
            if cancel_event is not None and getattr(cancel_event, "is_set", None):
                try:
                    if cancel_event.is_set():
                        return ToolResult.error("视频生成已取消")
                except Exception:
                    pass

            try:
                params.model_name = model_name
                result = await provider.text2video(revised_prompt, params)

                # 5. 结果 URL 安全校验
                safe_url = result.video_url if _is_safe_http_url(result.video_url) else ""
                if not safe_url:
                    logger.warning("视频 URL 不安全: %s", result.video_url[:100] if result.video_url else "")
                    return ToolResult.error("视频生成结果 URL 不安全")

                file_name, mime_type = _guess_video_name(safe_url)
                attachment = Attachment(
                    type="file", url=safe_url, mime_type=mime_type, name=file_name
                )

                tool_result = ToolResult(
                    success=True,
                    content={
                        "video_url": safe_url,
                        "model_used": result.model_used,
                        "revised_prompt": result.revised_prompt or revised_prompt,
                        "task_id": result.task_id,
                    },
                    content_type="json",
                    metadata={
                        "model_used": result.model_used,
                        "elapsed_seconds": result.elapsed_seconds,
                        "task_id": result.task_id,
                    },
                    attachments=[attachment],
                )

                logger.info(
                    "视频生成成功 model=%s elapsed=%.2fs",
                    result.model_used, result.elapsed_seconds,
                )

                # 6. 发送 video_generated 事件
                await self._emit_event(ctx, result, safe_url)

                return tool_result

            except VideoGenError as e:
                logger.warning(
                    "视频生成失败 model=%s retryable=%s error=%s",
                    model_name, e.retryable, e,
                )
                last_error = e
                if not e.retryable:
                    break
                continue
            except Exception as e:
                logger.error(
                    "视频生成异常 model=%s error=%s",
                    model_name, type(e).__name__, exc_info=True,
                )
                last_error = e
                break

        return ToolResult.error(self._build_failure_message(last_error))

    # ------------------------------------------------------------------
    # 参数归一化
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_resolution(raw: Any) -> str:
        if isinstance(raw, str) and raw.strip() in _ALLOWED_RESOLUTIONS:
            return raw.strip()
        return _DEFAULT_RESOLUTION

    @staticmethod
    def _normalize_duration(raw: Any) -> int:
        try:
            value = int(raw) if raw is not None else _DEFAULT_DURATION
        except (TypeError, ValueError):
            return _DEFAULT_DURATION
        return min(max(value, _MIN_DURATION), _MAX_DURATION)

    @staticmethod
    def _normalize_ratio(raw: Any) -> str:
        if isinstance(raw, str) and raw.strip() in _ALLOWED_RATIOS:
            return raw.strip()
        return _DEFAULT_RATIO

    @staticmethod
    def _build_failure_message(last_error: Optional[BaseException]) -> str:
        base = "所有视频模型均不可用"
        if isinstance(last_error, VideoGenError):
            detail = str(last_error).strip()
            if detail:
                return f"{base}：{detail}"
            return base
        if last_error is not None:
            return f"{base}：内部错误，请稍后重试"
        return base

    # ------------------------------------------------------------------
    # Provider 链解析
    # ------------------------------------------------------------------

    def _resolve_provider_chain(self, ctx: ToolContext) -> List[Tuple[str, object]]:
        """从 Agent 配置解析视频 provider 链

        查找 category="video_gen" 的模型；若无则尝试 category="image_gen"
        中 provider_type 含 "minimax" 的模型（兼容复用）。
        """
        chain: List[Tuple[str, object]] = []

        agent = getattr(ctx, "agent", None)
        if agent is None:
            return chain

        db = getattr(ctx, "db", None)
        if db is None:
            return chain

        oss = getattr(ctx, "oss_service", None)

        # 收集候选 model ID
        model_ids: List[Any] = []
        seen = set()
        default_model_id = getattr(agent, "default_model_id", None)
        if default_model_id:
            model_ids.append(default_model_id)
            seen.add(str(default_model_id))
        for fallback_id in (getattr(agent, "fallback_model_ids", None) or []):
            if not fallback_id or str(fallback_id) in seen:
                continue
            model_ids.append(fallback_id)
            seen.add(str(fallback_id))

        from app.models.llm_model import LLMModel
        from app.services.harness.video_provider.registry import resolve_provider

        for model_id in model_ids:
            try:
                llm_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
                if llm_model is None:
                    continue
                if llm_model.category not in ("video_gen", "image_gen"):
                    continue
                if not llm_model.is_active:
                    continue

                provider = resolve_provider(llm_model.provider, oss_client=oss)
                chain.append((llm_model.model_name, provider))
            except Exception as e:
                logger.warning("解析视频模型失败 model_id=%s: %s", model_id, type(e).__name__)
                continue

        # 如果没有通过 Agent 绑定找到模型，尝试直接查找数据库中的 video_gen 模型
        if not chain:
            try:
                from app.models.llm_model import LLMModel as LM
                from app.services.harness.video_provider.registry import resolve_provider as rp

                video_models = (
                    db.query(LM)
                    .filter(LM.category == "video_gen", LM.is_active == True)  # noqa: E712
                    .order_by(LM.priority.desc())
                    .all()
                )
                for m in video_models:
                    try:
                        p = rp(m.provider, oss_client=oss)
                        chain.append((m.model_name, p))
                    except Exception as e:
                        logger.warning("解析视频模型失败 model=%s: %s", m.model_name, type(e).__name__)
            except Exception as e:
                logger.warning("查找 video_gen 模型失败: %s", type(e).__name__)

        return chain

    async def _emit_event(self, ctx: ToolContext, result: VideoGenResult, url: str) -> None:
        """发送 video_generated 事件"""
        emitter = getattr(ctx, "event_emitter", None)
        if emitter is None:
            return
        try:
            from app.services.harness.events import Event

            event = Event.video_generated(
                url=url,
                metadata={
                    "model_used": result.model_used,
                    "elapsed_seconds": result.elapsed_seconds,
                    "task_id": result.task_id,
                },
            )
            await emitter(event)
        except Exception as e:
            logger.warning("发送 video_generated 事件失败: %s", type(e).__name__)
