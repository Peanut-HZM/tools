"""image_gen BuiltinTool — 图像生成工具

支持 4 种操作：text2img / img2img / inpaint / upload_edit
通过 ImageModelProvider 抽象支持多 provider，含 prompt 润色和 fallback 链。

参考 spec §5

安全说明：
- 入参 URL 强制校验 scheme（仅 http/https），阻断 file:// / javascript: / data: 等
- 出参 URL 同样校验后才组装为 Attachment，避免前端渲染危险 scheme
- 错误消息脱敏：仅回传 provider 已脱敏的 ImageGenError 文本，
  其余异常统一降级为通用提示，详细信息只写 logger
"""
import logging
import mimetypes
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
)
from app.services.harness.image_provider.registry import resolve_provider
from app.services.harness.tool_protocol import (
    Attachment,
    ToolContext,
    ToolResult,
)
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.prompt_refiner import refine_image_prompt

logger = logging.getLogger(__name__)

# 操作与必填字段映射
_OPERATION_REQUIRED_FIELDS = {
    "text2img": ["prompt"],
    "img2img": ["prompt", "reference_image_url"],
    "inpaint": ["prompt", "image_url", "mask_url"],
    "upload_edit": ["prompt", "image_url"],
}

# 需要做 URL 安全校验的入参字段
_URL_FIELDS = ("reference_image_url", "image_url", "mask_url")

# 允许的 URL scheme（阻断 file:// / javascript: / data: 等）
_ALLOWED_URL_SCHEMES = ("http", "https")

# URL 长度上限
_MAX_URL_LEN = 2048

# 允许的尺寸枚举（与 parameters_schema 保持一致）
_ALLOWED_SIZES = ("1024x1024", "1024x1792", "1792x1024", "512x512")
_DEFAULT_SIZE = "1024x1024"

# 单次生成图片数量范围
_MIN_N = 1
_MAX_N = 4

# style 长度上限（防止把超长文本塞进 provider 请求体）
_MAX_STYLE_LEN = 64


def _is_safe_http_url(raw: Any) -> bool:
    """校验 URL 是否为安全的 http/https 链接

    仅允许 http/https scheme 且必须带 host，长度受限。
    """
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
    return bool(parsed.netloc)


def _guess_image_name(url: str, index: int) -> Tuple[str, str]:
    """根据 URL 推断附件文件名与 MIME 类型

    无法识别时统一降级为 PNG。
    """
    try:
        path = urlparse(url).path
    except Exception:
        path = ""
    mime, _ = mimetypes.guess_type(path)
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    ext = mimetypes.guess_extension(mime) or ".png"
    if ext == ".jpe":  # guess_extension 对 image/jpeg 可能返回 .jpe
        ext = ".jpg"
    return f"generated_{index + 1}{ext}", mime


class ImageGenTool(BuiltinTool):
    """图像生成工具"""

    name = "image_gen"
    display_name = "图像生成"
    description = (
        "生成或编辑图像。支持文生图(text2img)、图生图(img2img)、"
        "局部重绘(inpaint)、指令编辑(upload_edit)四种操作。"
    )
    parameters_schema = {
        "type": "object",
        "required": ["operation", "prompt"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["text2img", "img2img", "inpaint", "upload_edit"],
                "description": "操作类型",
            },
            "prompt": {
                "type": "string",
                "description": "图像描述或编辑指令（中文即可，系统自动润色为英文）",
            },
            "reference_image_url": {
                "type": "string",
                "description": "参考图片 URL（img2img 时必填，仅支持 http/https）",
            },
            "mask_url": {
                "type": "string",
                "description": "遮罩图片 URL（inpaint 时必填，仅支持 http/https）",
            },
            "image_url": {
                "type": "string",
                "description": "原始图片 URL（inpaint/upload_edit 时必填，仅支持 http/https）",
            },
            "size": {
                "type": "string",
                "enum": list(_ALLOWED_SIZES),
                "default": _DEFAULT_SIZE,
                "description": "输出尺寸",
            },
            "n": {
                "type": "integer",
                "minimum": _MIN_N,
                "maximum": _MAX_N,
                "default": 1,
                "description": "生成张数",
            },
            "style": {
                "type": "string",
                "description": "风格预设（可选）",
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "image_urls": {"type": "array", "items": {"type": "string"}},
            "model_used": {"type": "string"},
            "revised_prompt": {"type": "string"},
            "image_count": {"type": "integer"},
        },
    }

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        """执行图像生成

        流程：参数校验 → prompt 润色 → 解析 provider 链 → 依次尝试 → 组装结果 + 发事件
        """
        args = args or {}

        # 1. 参数校验
        validation_error = self._validate_args(args)
        if validation_error:
            return ToolResult.error(validation_error)

        operation = str(args.get("operation", "")).strip()
        prompt = str(args.get("prompt") or "").strip()

        # 2. Prompt 润色（LLM 不可用时自动降级为原始 prompt）
        revised_prompt = await refine_image_prompt(prompt, ctx)
        if not revised_prompt:
            # 润色返回空串属于异常情况，退回原始 prompt 保证可用
            revised_prompt = prompt

        # 3. 构造 provider 参数
        params = ImageGenParams(
            size=self._normalize_size(args.get("size")),
            n=self._normalize_n(args.get("n")),
            style=self._normalize_style(args.get("style")),
        )

        # 4. 模型选择 + Fallback 链
        provider_chain = self._resolve_provider_chain(ctx)
        if not provider_chain:
            logger.warning(
                "图像生成无可用模型 agent_id=%s", getattr(ctx, "agent_id", None)
            )
            return ToolResult.error("无可用图像模型，请在 Agent 配置中绑定图像模型")

        last_error: Optional[BaseException] = None
        for model_name, provider in provider_chain:
            # 支持用户中途取消
            cancel_event = getattr(ctx, "cancel_event", None)
            if cancel_event is not None and getattr(cancel_event, "is_set", None):
                try:
                    if cancel_event.is_set():
                        logger.info("图像生成被取消 operation=%s", operation)
                        return ToolResult.error("图像生成已取消")
                except Exception:  # pragma: no cover - 取消检查失败不应阻塞主流程
                    pass

            try:
                params.model_name = model_name
                result = await self._dispatch(provider, operation, revised_prompt, args, params)

                # 5. 结果组装（出参 URL 同样做 scheme 校验）
                safe_urls = [u for u in (result.image_urls or []) if _is_safe_http_url(u)]
                dropped = len(result.image_urls or []) - len(safe_urls)
                if dropped > 0:
                    logger.warning(
                        "图像生成结果中有 %s 个不安全 URL 被丢弃 model=%s", dropped, model_name
                    )

                attachments: List[Attachment] = []
                for idx, url in enumerate(safe_urls):
                    file_name, mime_type = _guess_image_name(url, idx)
                    attachments.append(
                        Attachment(type="image", url=url, mime_type=mime_type, name=file_name)
                    )

                tool_result = ToolResult(
                    success=True,
                    content={
                        "operation": operation,
                        "model_used": result.model_used,
                        "revised_prompt": result.revised_prompt or revised_prompt,
                        "image_urls": safe_urls,
                        "image_count": len(safe_urls),
                    },
                    content_type="json",
                    metadata={
                        "model_used": result.model_used,
                        "elapsed_seconds": result.elapsed_seconds,
                        "operation": operation,
                    },
                    attachments=attachments,
                )

                logger.info(
                    "图像生成成功 operation=%s model=%s count=%s elapsed=%.2fs",
                    operation,
                    result.model_used,
                    len(safe_urls),
                    result.elapsed_seconds,
                )

                # 6. 发送 image_generated 事件
                await self._emit_event(ctx, result, operation, safe_urls)

                return tool_result

            except ImageGenError as e:
                logger.warning(
                    "图像生成失败 model=%s operation=%s retryable=%s error_type=%s",
                    model_name,
                    operation,
                    e.retryable,
                    type(e).__name__,
                )
                last_error = e
                if not e.retryable:
                    # fatal 错误（鉴权失败/参数错误）不触发 fallback
                    break
                continue
            except Exception as e:
                logger.error(
                    "图像生成异常 model=%s operation=%s error_type=%s",
                    model_name,
                    operation,
                    type(e).__name__,
                    exc_info=True,
                )
                last_error = e
                break

        return ToolResult.error(self._build_failure_message(last_error))

    # ------------------------------------------------------------------
    # 参数校验 / 归一化
    # ------------------------------------------------------------------

    def _validate_args(self, args: dict) -> Optional[str]:
        """校验入参，返回错误信息；合法时返回 None"""
        operation_raw = args.get("operation")
        operation = str(operation_raw).strip() if isinstance(operation_raw, str) else ""
        if operation not in _OPERATION_REQUIRED_FIELDS:
            return (
                f"无效操作: {operation or operation_raw}，"
                f"支持: {list(_OPERATION_REQUIRED_FIELDS.keys())}"
            )

        prompt_raw = args.get("prompt")
        prompt = prompt_raw.strip() if isinstance(prompt_raw, str) else ""
        if not prompt:
            return "prompt 不能为空"

        # 必填字段检查（prompt 已单独校验）
        for field_name in _OPERATION_REQUIRED_FIELDS[operation]:
            if field_name == "prompt":
                continue
            if not args.get(field_name):
                return f"操作 {operation} 需要参数: {field_name}"

        # URL 字段安全校验（仅校验实际传入的字段）
        for field_name in _URL_FIELDS:
            value = args.get(field_name)
            if value and not _is_safe_http_url(value):
                return f"参数 {field_name} 必须是合法的 http/https URL"

        return None

    @staticmethod
    def _normalize_size(raw: Any) -> str:
        """归一化尺寸，非法值降级为默认尺寸"""
        if isinstance(raw, str) and raw.strip() in _ALLOWED_SIZES:
            return raw.strip()
        if raw:
            logger.warning("图像尺寸不受支持，降级为 %s", _DEFAULT_SIZE)
        return _DEFAULT_SIZE

    @staticmethod
    def _normalize_n(raw: Any) -> int:
        """归一化生成张数，非法值降级为 1，并夹在 [1, 4]"""
        try:
            value = int(raw) if raw is not None else _MIN_N
        except (TypeError, ValueError):
            logger.warning("参数 n 非法，降级为 %s", _MIN_N)
            return _MIN_N
        return min(max(value, _MIN_N), _MAX_N)

    @staticmethod
    def _normalize_style(raw: Any) -> Optional[str]:
        """归一化 style，非字符串或空值返回 None"""
        if not isinstance(raw, str):
            return None
        style = raw.strip()
        if not style:
            return None
        return style[:_MAX_STYLE_LEN]

    @staticmethod
    def _build_failure_message(last_error: Optional[BaseException]) -> str:
        """构造对外失败消息（脱敏）

        ImageGenError 的消息由各 provider 生成时已做脱敏（不含 body/API key/内部路径），
        可直接透出；其余异常统一降级为通用提示，细节只留在日志中。
        """
        base = "所有图像模型均不可用"
        if isinstance(last_error, ImageGenError):
            detail = str(last_error).strip()
            if detail:
                return f"{base}：{detail}"
            return base
        if last_error is not None:
            return f"{base}：内部错误，请稍后重试"
        return base

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _dispatch(
        self,
        provider,
        operation: str,
        prompt: str,
        args: dict,
        params: ImageGenParams,
    ) -> ImageGenResult:
        """分发到 provider 的具体操作方法"""
        if operation == "text2img":
            return await provider.text2img(prompt, params)
        if operation == "img2img":
            return await provider.img2img(prompt, args["reference_image_url"], params)
        if operation == "inpaint":
            return await provider.inpaint(prompt, args["image_url"], args["mask_url"], params)
        if operation == "upload_edit":
            return await provider.upload_edit(args["image_url"], prompt, params)
        raise ValueError(f"未知操作: {operation}")

    def _resolve_provider_chain(self, ctx: ToolContext) -> List[Tuple[str, object]]:
        """从 Agent 配置解析 provider 链（主模型 + fallback）

        只保留 category="image_gen" 且 is_active=True 的模型，按
        default_model_id → fallback_model_ids 的声明顺序排列。

        Returns:
            [(model_name, provider_instance), ...] 按优先级排序
        """
        chain: List[Tuple[str, object]] = []

        agent = getattr(ctx, "agent", None)
        if agent is None:
            logger.warning("图像生成缺少 Agent 配置，无法解析模型链")
            return chain

        db = getattr(ctx, "db", None)
        if db is None:
            logger.warning("图像生成缺少 DB 会话，无法解析模型链")
            return chain

        oss = getattr(ctx, "oss_service", None)

        # 收集候选 model ID（主模型 + fallback），去重且保持顺序
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

        if not model_ids:
            logger.warning("Agent 未配置任何图像模型 agent_id=%s", getattr(ctx, "agent_id", None))
            return chain

        from app.models.llm_model import LLMModel

        for model_id in model_ids:
            try:
                llm_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
                if llm_model is None:
                    logger.debug("图像模型不存在 model_id=%s", model_id)
                    continue
                if llm_model.category != "image_gen":
                    logger.debug(
                        "跳过非图像模型 model_id=%s category=%s", model_id, llm_model.category
                    )
                    continue
                if not llm_model.is_active:
                    logger.debug("跳过未启用的图像模型 model_id=%s", model_id)
                    continue

                provider = resolve_provider(llm_model.provider, oss_client=oss)
                chain.append((llm_model.model_name, provider))
            except Exception as e:
                logger.warning(
                    "解析图像模型失败 model_id=%s error_type=%s", model_id, type(e).__name__
                )
                continue

        return chain

    async def _emit_event(
        self,
        ctx: ToolContext,
        result: ImageGenResult,
        operation: str,
        urls: Optional[List[str]] = None,
    ) -> None:
        """通过 event_emitter 发送 image_generated 事件

        事件发送失败不影响工具结果（仅记录日志）。
        """
        emitter = getattr(ctx, "event_emitter", None)
        if emitter is None:
            return
        try:
            from app.services.harness.events import Event

            event = Event.image_generated(
                urls=urls if urls is not None else list(result.image_urls or []),
                metadata={
                    "model_used": result.model_used,
                    "operation": operation,
                    "elapsed_seconds": result.elapsed_seconds,
                },
            )
            await emitter(event)
        except Exception as e:
            logger.warning("发送 image_generated 事件失败: %s", type(e).__name__)
