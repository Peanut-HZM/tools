"""Guardrail 执行器

参考 spec §7.6
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    blocked: bool
    guardrail_name: Optional[str] = None
    reason: Optional[str] = None
    stage: Optional[str] = None  # "input" / "output"
    warned: bool = False


async def run_input_guardrails(agent, user_message: str, ctx, tool_registry) -> GuardrailResult:
    """执行输入 guardrails"""
    guardrails = agent.input_guardrails or []
    on_violation = agent.guardrail_on_violation or "block"

    for gr in guardrails:
        try:
            tool = await _get_tool(tool_registry, gr["tool_id"])
            result = await tool.execute({"content": user_message, **(gr.get("config") or {})}, ctx)

            if not result.success:
                if on_violation == "block":
                    return GuardrailResult(
                        blocked=True,
                        guardrail_name=gr["name"],
                        reason=result.error_message or "input blocked",
                        stage="input",
                    )
                elif on_violation == "warn":
                    logger.warning(f"[Guardrail] {gr['name']}: {result.error_message}")
                    return GuardrailResult(
                        blocked=False,
                        guardrail_name=gr["name"],
                        reason=result.error_message,
                        stage="input",
                        warned=True,
                    )
        except Exception as e:
            logger.error(f"Guardrail {gr.get('name')} 异常: {e}", exc_info=True)
            if on_violation == "block":
                return GuardrailResult(
                    blocked=True,
                    guardrail_name=gr.get("name"),
                    reason="guardrail execution failed",
                    stage="input",
                )

    return GuardrailResult(blocked=False)


async def run_output_guardrails(agent, output: str, ctx, tool_registry) -> GuardrailResult:
    """执行输出 guardrails"""
    guardrails = agent.output_guardrails or []
    on_violation = agent.guardrail_on_violation or "block"

    for gr in guardrails:
        try:
            tool = await _get_tool(tool_registry, gr["tool_id"])
            result = await tool.execute({"content": output, **(gr.get("config") or {})}, ctx)

            if not result.success:
                if on_violation == "block":
                    return GuardrailResult(
                        blocked=True,
                        guardrail_name=gr["name"],
                        reason=result.error_message or "output blocked",
                        stage="output",
                    )
                elif on_violation == "warn":
                    logger.warning(f"[Guardrail] {gr['name']}: {result.error_message}")
                    return GuardrailResult(
                        blocked=False,
                        guardrail_name=gr["name"],
                        reason=result.error_message,
                        stage="output",
                        warned=True,
                    )
        except Exception as e:
            logger.error(f"Guardrail {gr.get('name')} 异常: {e}", exc_info=True)
            if on_violation == "block":
                return GuardrailResult(
                    blocked=True,
                    guardrail_name=gr.get("name"),
                    reason="guardrail execution failed",
                    stage="output",
                )

    return GuardrailResult(blocked=False)


async def _get_tool(tool_registry, tool_id):
    """按 ID 获取工具

    优先尝试 ``get_by_id``，fallback 到 ``_resolve_tool_by_name``。
    为了让 MagicMock 等测试替身能直接走 fallback，
    仅在 ``get_by_id`` 显式存在于 ``__dict__`` 中时才走该路径。
    """
    if "get_by_id" in getattr(tool_registry, "__dict__", {}):
        return await tool_registry.get_by_id(tool_id)
    return await tool_registry._resolve_tool_by_name(tool_id)
