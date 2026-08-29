"""短期记忆策略

参考 spec §7.7

Phase 1 策略：
- full: 全部消息
- sliding_window: 永远保留 system + 最近 window 条
- summary: 退化为 sliding_window（无 LLM 摘要，留待 Phase 3）
- 未知策略: 降级为 full
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


def apply_memory_policy(messages: List, policy: str, window: int = 20) -> List:
    """应用短期记忆策略

    Args:
        messages: 完整消息历史
        policy: "full" / "sliding_window" / "summary"
        window: 滑动窗口大小（仅 sliding_window / summary 生效）

    Returns:
        处理后的消息列表（用于 LLM 上下文）
    """
    if not messages:
        return []

    if policy == "full":
        return list(messages)

    if policy == "sliding_window":
        # 永远保留 system 消息
        system_msgs = [m for m in messages if getattr(m, "role", None) == "system"]
        other_msgs = [m for m in messages if getattr(m, "role", None) != "system"]

        # 保留最近 window 条非 system 消息
        recent = other_msgs[-window:] if len(other_msgs) > window else other_msgs

        return system_msgs + recent

    if policy == "summary":
        # Phase 1：退化为 sliding_window（没有 LLM 摘要）
        # Phase 3：实现真正的摘要（调用 LLM 总结早期消息）
        logger.debug("memory_policy: summary 策略 Phase 1 退化为 sliding_window")
        return apply_memory_policy(messages, "sliding_window", window)

    # 未知策略，降级为 full
    logger.warning(f"memory_policy: 未知策略 {policy!r}，降级为 full")
    return list(messages)
