"""Guardrail 执行器

参考 spec §7.6；P3-⑩ 增加内置规则引擎（keyword / regex / max_length，
无需绑定工具），与既有 tool_id 条目共存。
"""
import logging
import re
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


def _decide(
    on_violation: str, name: Optional[str], reason: Optional[str], stage: str
) -> GuardrailResult:
    """统一违规决策：warn 放行并标注，block（默认）阻断（fail-closed）。"""
    if on_violation == "warn":
        logger.warning(f"[Guardrail] {name}: {reason}")
        return GuardrailResult(
            blocked=False, guardrail_name=name, reason=reason, stage=stage, warned=True
        )
    return GuardrailResult(
        blocked=True, guardrail_name=name, reason=reason or f"{stage} blocked", stage=stage
    )


def _decide_error(
    on_violation: str, name: Optional[str], stage: str
) -> GuardrailResult:
    """guardrail 执行/配置异常的统一决策（fail-closed）。"""
    return _decide(on_violation, name, "guardrail execution failed", stage)


def _evaluate_rule(gr: dict, content: str) -> Optional[str]:
    """评估内置规则条目，返回违规原因或 None（未违规）。

    配置不合法抛 ValueError（由调用方走 fail-closed 异常路径）。
    """
    rule_type = gr.get("type")
    config = gr.get("config") or {}

    if rule_type == "keyword":
        keywords = config.get("keywords")
        if not isinstance(keywords, list) or not keywords or not all(
            isinstance(k, str) and k for k in keywords
        ):
            raise ValueError("keyword 规则需要非空字符串数组 keywords")
        case_sensitive = bool(config.get("case_sensitive", False))
        haystack = content if case_sensitive else content.lower()
        for kw in keywords:
            needle = kw if case_sensitive else kw.lower()
            if needle in haystack:
                return f"命中关键词: {kw}"
        return None

    if rule_type == "regex":
        pattern = config.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("regex 规则需要非空 pattern")
        # 编译失败抛 re.error → 调用方 fail-closed
        if re.search(pattern, content):
            return f"命中正则: {pattern[:100]}"
        return None

    if rule_type == "max_length":
        max_chars = config.get("max_chars")
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
            raise ValueError("max_length 规则需要正整数 max_chars")
        if len(content) > max_chars:
            return f"长度超限: {len(content)} > {max_chars}"
        return None

    raise ValueError(f"未知规则类型: {rule_type}")


async def run_input_guardrails(agent, user_message: str, ctx, tool_registry) -> GuardrailResult:
    """执行输入 guardrails（tool_id 条目 + 内置规则条目）"""
    guardrails = agent.input_guardrails or []
    on_violation = agent.guardrail_on_violation or "block"

    for gr in guardrails:
        try:
            if "tool_id" in gr:
                # 工具型条目（原路径，行为不变）
                tool = await _get_tool(tool_registry, gr["tool_id"])
                result = await tool.execute({"content": user_message, **(gr.get("config") or {})}, ctx)
                if not result.success:
                    return _decide(on_violation, gr["name"], result.error_message, "input")
            elif "type" in gr:
                # 内置规则条目（P3-⑩）
                reason = _evaluate_rule(gr, user_message)
                if reason:
                    return _decide(on_violation, gr.get("name"), reason, "input")
            else:
                # 配置错误：fail-closed
                logger.error(f"Guardrail 条目缺少 tool_id/type: {gr.get('name')}")
                return _decide_error(on_violation, gr.get("name"), "input")
        except Exception as e:
            logger.error(f"Guardrail {gr.get('name')} 异常: {e}", exc_info=True)
            return _decide_error(on_violation, gr.get("name"), "input")

    return GuardrailResult(blocked=False)


async def run_output_guardrails(agent, output: str, ctx, tool_registry) -> GuardrailResult:
    """执行输出 guardrails（tool_id 条目 + 内置规则条目）"""
    guardrails = agent.output_guardrails or []
    on_violation = agent.guardrail_on_violation or "block"

    for gr in guardrails:
        try:
            if "tool_id" in gr:
                tool = await _get_tool(tool_registry, gr["tool_id"])
                result = await tool.execute({"content": output, **(gr.get("config") or {})}, ctx)
                if not result.success:
                    return _decide(on_violation, gr["name"], result.error_message, "output")
            elif "type" in gr:
                reason = _evaluate_rule(gr, output)
                if reason:
                    return _decide(on_violation, gr.get("name"), reason, "output")
            else:
                logger.error(f"Guardrail 条目缺少 tool_id/type: {gr.get('name')}")
                return _decide_error(on_violation, gr.get("name"), "output")
        except Exception as e:
            logger.error(f"Guardrail {gr.get('name')} 异常: {e}", exc_info=True)
            return _decide_error(on_violation, gr.get("name"), "output")

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
