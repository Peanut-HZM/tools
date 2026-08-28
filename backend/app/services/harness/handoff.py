"""Handoff 机制 — Agent 之间的委派

参考 spec §7.5
"""
import logging
import re
from typing import Callable, List, Optional

from app.services.harness.tool_protocol import ToolCall

logger = logging.getLogger(__name__)

# 控制字符（ASCII 0x00-0x1f、0x7f-0x9f）与 JSON-significant 引号 / 反斜杠，
# 用于剥离潜在 prompt injection 内容，避免恶意 agent name/description 污染 tool description。
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_QUOTE_CHARS = re.compile(r'["\\]')


def _sanitize_for_description(text: str, max_len: int = 200) -> str:
    """Sanitize text for embedding in tool description to prevent prompt injection."""
    if not text:
        return ""
    # 去除控制字符与 JSON-significant 引号
    text = _CONTROL_CHARS.sub("", text)
    text = _QUOTE_CHARS.sub("", text)
    # 截断到最大长度
    return text[:max_len].strip()


def generate_handoff_tools(agent, load_agent_by_slug: Callable) -> List[dict]:
    """为每个可委派目标生成一个 handoff 工具"""
    tools = []
    for target_slug in agent.can_handoff_to or []:
        try:
            target = load_agent_by_slug(target_slug)
            if not target or not target.is_active:
                continue

            safe_name = _sanitize_for_description(target.name or "")
            safe_desc = _sanitize_for_description(target.description or "")

            tools.append({
                "name": f"handoff_to_{target.slug.replace('-', '_')}",
                "description": f"将任务委派给 {safe_name}：{safe_desc}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "委派原因（给用户的说明）",
                        },
                    },
                    "required": ["reason"],
                },
            })
        except Exception as e:
            logger.warning(f"加载 handoff 目标失败 slug={target_slug}: {e}")

    return tools


def detect_handoff(
    tool_calls: List[ToolCall],
    agent,
    load_agent_by_slug: Callable,
) -> Optional[object]:
    """检测 tool_calls 中是否包含 handoff 调用"""
    for call in tool_calls:
        if call.name.startswith("handoff_to_"):
            slug_part = call.name[len("handoff_to_"):]
            target_slug = slug_part.replace("_", "-")

            if target_slug not in (agent.can_handoff_to or []):
                logger.warning(f"Handoff 目标 {target_slug} 不在可委派列表中")
                continue

            try:
                target = load_agent_by_slug(target_slug)
                if target and target.is_active:
                    return target
            except Exception as e:
                logger.error(f"加载 handoff 目标失败: {e}")

    return None
