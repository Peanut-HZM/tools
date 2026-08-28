"""Handoff 机制 — Agent 之间的委派

参考 spec §7.5
"""
import logging
from typing import Callable, List, Optional

from app.services.harness.tool_protocol import ToolCall

logger = logging.getLogger(__name__)


def generate_handoff_tools(agent, load_agent_by_slug: Callable) -> List[dict]:
    """为每个可委派目标生成一个 handoff 工具"""
    tools = []
    for target_slug in agent.can_handoff_to or []:
        try:
            target = load_agent_by_slug(target_slug)
            if not target or not target.is_active:
                continue

            tools.append({
                "name": f"handoff_to_{target.slug.replace('-', '_')}",
                "description": f"将任务委派给 {target.name}：{target.description or ''}",
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
