"""Harness 异常定义

参考 spec §5.9 错误码规范
"""
from typing import Optional


class HarnessError(Exception):
    """Harness 基础异常"""

    def __init__(self, message: str, code: str = "internal_error", details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ToolExecutionError(HarnessError):
    """工具执行失败"""

    def __init__(self, tool_name: str, message: str):
        super().__init__(message, code="tool_execution_failed", details={"tool_name": tool_name})
        self.tool_name = tool_name


class ToolNotFoundError(HarnessError):
    """工具未找到"""

    def __init__(self, tool_name: str):
        super().__init__(
            f"Tool not found: {tool_name}",
            code="tool_not_found",
            details={"tool_name": tool_name},
        )
        self.tool_name = tool_name


class ToolNotAvailableError(HarnessError):
    """工具当前不可用"""

    def __init__(self, tool_name: str):
        super().__init__(
            f"Tool not available: {tool_name}",
            code="tool_not_available",
            details={"tool_name": tool_name},
        )
        self.tool_name = tool_name


class AgentNotFoundError(HarnessError):
    """Agent 未找到"""

    def __init__(self, agent_id: Optional[str] = None, slug: Optional[str] = None):
        identifier = f"slug={slug}" if slug else f"id={agent_id}"
        super().__init__(
            f"Agent not found: {identifier}",
            code="agent_not_found",
            details={"agent_id": agent_id, "slug": slug},
        )


class AgentDisabledError(HarnessError):
    """Agent 已禁用"""

    def __init__(self, agent_id: str):
        super().__init__("Agent is disabled", code="agent_disabled", details={"agent_id": agent_id})


class HandoffError(HarnessError):
    """Handoff 失败"""

    def __init__(self, message: str, target_slug: Optional[str] = None):
        super().__init__(message, code="invalid_handoff", details={"target_slug": target_slug})
        self.target_slug = target_slug


class GuardrailBlockedError(HarnessError):
    """Guardrail 阻断"""

    def __init__(self, guardrail_name: str, stage: str, reason: str):
        super().__init__(
            reason,
            code="guardrail_blocked",
            details={"guardrail_name": guardrail_name, "stage": stage, "reason": reason},
        )
        self.guardrail_name = guardrail_name
        self.stage = stage


class MaxStepsReachedError(HarnessError):
    """达到最大步数"""

    def __init__(self, max_steps: int):
        super().__init__(
            f"Max steps reached: {max_steps}",
            code="max_steps_reached",
            details={"max_steps": max_steps},
        )
        self.max_steps = max_steps


class CancelledError(HarnessError):
    """用户取消"""

    def __init__(self):
        super().__init__("Cancelled", code="cancelled")
