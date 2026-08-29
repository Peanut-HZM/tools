"""Prompt 润色 helper

将中文图像描述转化为高质量英文 prompt，用于传给图像生成 provider。
通过 ctx.llm_gateway 调用 LLM 完成润色。

降级策略：LLM 不可用 / 超时 / 异常时返回原始 prompt，不阻塞生成。
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 判断字符串是否基本为英文（>80% ASCII 字母/空格/标点）
_ENGLISH_RATIO_THRESHOLD = 0.8
_ENGLISH_CHAR_RE = re.compile(r'[a-zA-Z\s\.,!?;:\'"()\-\[\]{}]')

# 润色 system prompt
_REFINE_SYSTEM_PROMPT = (
    "You are an expert image generation prompt engineer. "
    "Convert the following Chinese description into a high-quality English prompt "
    "for image generation. Keep key details, enhance composition descriptions, "
    "add quality modifiers (e.g., 'high quality', 'detailed', 'professional photography'). "
    "Return ONLY the English prompt, no explanation."
)

# 润色超时（秒）
_REFINE_TIMEOUT = 10.0


def _is_mostly_english(text: str) -> bool:
    """判断文本是否主要为英文"""
    if not text:
        return False
    chars = list(text)
    if not chars:
        return False
    en_count = sum(1 for c in chars if _ENGLISH_CHAR_RE.match(c))
    return (en_count / len(chars)) >= _ENGLISH_RATIO_THRESHOLD


async def refine_image_prompt(prompt: str, ctx) -> str:
    """润色图像生成 prompt

    Args:
        prompt: 原始 prompt（可能中文或英文）
        ctx: ToolContext（通过 ctx.llm_gateway 调用 LLM）

    Returns:
        润色后的英文 prompt。LLM 不可用时返回原始 prompt。
    """
    if not prompt or not prompt.strip():
        return ""

    stripped = prompt.strip()

    # 已经基本是英文 → 直接返回，不调 LLM
    if _is_mostly_english(stripped):
        return stripped

    # 无 LLM gateway → 降级返回原始
    gateway = getattr(ctx, "llm_gateway", None)
    if gateway is None:
        logger.debug("Prompt 润色：llm_gateway 不可用，返回原始 prompt")
        return stripped

    try:
        messages = [
            {"role": "system", "content": _REFINE_SYSTEM_PROMPT},
            {"role": "user", "content": stripped},
        ]

        result = await gateway.generate(
            category="text",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )

        # 解析返回值（gateway.generate 返回 dict 或 str）
        if isinstance(result, str):
            refined = result.strip()
        elif isinstance(result, dict):
            content = result.get("content", "")
            refined = content.strip() if isinstance(content, str) else str(content).strip()
        else:
            refined = getattr(result, "content", str(result)).strip()

        if not refined:
            logger.warning("Prompt 润色返回空值，使用原始 prompt")
            return stripped

        return refined

    except Exception as e:
        logger.warning("Prompt 润色失败（降级使用原始 prompt）: %s", e)
        return stripped
