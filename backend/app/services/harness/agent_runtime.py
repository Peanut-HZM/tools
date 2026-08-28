"""AgentRuntime — ReAct 主循环

参考 spec §7.2

AgentRuntime 是 harness 的核心编排器：
- 驱动一轮 (turn) 的完整 ReAct 循环
- 在每次 LLM 调用前后串联 guardrail / memory / handoff / tool 执行
- 所有 DB / 遥测操作均 try/except 包裹，保证主循环不崩溃
"""
import asyncio
import logging
from typing import AsyncIterator, Optional

from app.services.harness.events import Event
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.llm_bridge import LLMFunctionBridge, LLMResponse
from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.session import Session
from app.services.harness.memory_policy import apply_memory_policy
from app.services.harness.guardrail import run_input_guardrails, run_output_guardrails
from app.services.harness.handoff import detect_handoff, generate_handoff_tools

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Agent 执行引擎

    一次 turn 的执行器。跨 turn 状态存在 Session 中。
    """

    def __init__(
        self,
        agent,
        tool_registry: ToolRegistry,
        llm_bridge: LLMFunctionBridge,
        session: Session,
        ctx: ToolContext,
    ):
        self.agent = agent
        self._current_agent = agent
        self.tool_registry = tool_registry
        self.llm_bridge = llm_bridge
        self.session = session
        self.ctx = ctx
        self._step_count = 0

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    async def run(self, user_message: str) -> AsyncIterator[Event]:
        """执行一次 turn，yield Event 序列"""

        # 1. 输入 guardrail
        try:
            gr_result = await run_input_guardrails(
                self._current_agent, user_message, self.ctx, self.tool_registry
            )
            if gr_result.blocked:
                yield Event.guardrail_triggered(
                    gr_result.guardrail_name, gr_result.reason, "input"
                )
                yield Event.done(self._fallback_message("input_blocked"))
                return
        except Exception as e:
            logger.error(f"输入 guardrail 异常: {e}", exc_info=True)

        # 2. 记录用户消息到 session
        try:
            self.session.append_user_message(user_message)
        except Exception as e:
            logger.error(f"记录用户消息失败: {e}", exc_info=True)

        # 3. 创建 trace（best-effort）
        trace = self._safe_start_trace(user_message)

        final_text = None

        try:
            for step_index in range(self._current_agent.max_steps_per_turn):
                self._step_count = step_index + 1

                # 取消检查
                if self.ctx.cancel_event and self.ctx.cancel_event.is_set():
                    yield Event.error("cancelled", recoverable=False)
                    break

                # 4a. 应用短期记忆策略
                messages_dicts = self._build_messages_for_llm()

                # 4b. 加载可用工具
                tools = await self._safe_get_tools()

                # handoff 工具 schemas
                handoff_tools_schemas = self._safe_generate_handoff_tools()

                tool_schemas = self.llm_bridge.to_function_schemas(tools)
                all_schemas = tool_schemas + handoff_tools_schemas

                # 4c. 调用 LLM
                step = self._safe_start_step(trace)
                try:
                    llm_response = await self.llm_bridge.generate(
                        messages=messages_dicts,
                        tools=all_schemas,
                        model=str(self._current_agent.default_model_id)
                        if self._current_agent.default_model_id
                        else None,
                        fallback_models=self._current_agent.fallback_model_ids,
                        generation_params=self._current_agent.generation_params,
                    )
                except Exception as e:
                    self._safe_end_step(step, error=str(e))
                    logger.error(f"LLM 调用失败: {e}", exc_info=True)
                    yield Event.error("LLM 调用失败")
                    yield Event.done(self._fallback_message("llm_error"))
                    return

                usage = llm_response.usage or {}
                self._safe_end_step(
                    step,
                    tokens=usage.get("total_tokens", 0),
                    llm_model=usage.get("model"),
                )

                # 4d. 发射中间事件（thinking / text）
                if llm_response.thinking_part:
                    yield Event.thinking_delta(llm_response.thinking_part)
                if llm_response.text_part:
                    yield Event.text_delta(llm_response.text_part)

                # 4e. 解析响应
                tool_calls = llm_response.tool_calls or []

                # 检查 handoff
                handoff_target = self._safe_detect_handoff(tool_calls)
                if handoff_target:
                    from_agent_info = {
                        "id": str(self._current_agent.id),
                        "name": getattr(self._current_agent, "name", ""),
                    }
                    to_agent_info = {
                        "id": str(handoff_target.id),
                        "name": getattr(handoff_target, "name", ""),
                    }
                    yield Event.handoff(from_agent_info, to_agent_info, "handoff requested")

                    self._current_agent = handoff_target
                    self.session.agent = handoff_target
                    continue

                # 无工具调用 → 最终回复
                if not tool_calls:
                    final_text = llm_response.text_part or ""

                    # 输出 guardrail
                    try:
                        gr_result = await run_output_guardrails(
                            self._current_agent, final_text, self.ctx, self.tool_registry
                        )
                        if gr_result.blocked:
                            yield Event.guardrail_triggered(
                                gr_result.guardrail_name, gr_result.reason, "output"
                            )
                            final_text = self._fallback_message("output_blocked")
                    except Exception as e:
                        logger.error(f"输出 guardrail 异常: {e}", exc_info=True)

                    yield Event.text_complete(final_text)
                    yield Event.done(final_text, usage=llm_response.usage)

                    try:
                        self.session.append_assistant_message(llm_response)
                    except Exception as e:
                        logger.error(f"记录 assistant 消息失败: {e}", exc_info=True)
                    break
                else:
                    # 有工具调用 → 执行并继续循环
                    try:
                        self.session.append_assistant_message(llm_response)
                    except Exception as e:
                        logger.error(f"记录 assistant 消息失败: {e}", exc_info=True)

                    for call in tool_calls:
                        yield Event.tool_call_start(call)
                        try:
                            tool_result = await self.tool_registry.execute(call, self.ctx)
                        except Exception as e:
                            logger.error(f"工具执行失败 {call.name}: {e}", exc_info=True)
                            from app.services.harness.tool_protocol import ToolResult
                            tool_result = ToolResult.error(f"工具执行异常: {e}")
                        yield Event.tool_result(call, tool_result)
                        try:
                            self.session.append_tool_message(call, tool_result)
                        except Exception as e:
                            logger.error(f"记录 tool 消息失败: {e}", exc_info=True)
            else:
                # for 循环正常结束（没 break）→ 达到最大步数
                yield Event.error(
                    f"达到最大步数限制 ({self._current_agent.max_steps_per_turn})",
                    recoverable=True,
                )
                yield Event.done(self._fallback_message("max_steps"))

        except asyncio.CancelledError:
            yield Event.error("cancelled", recoverable=False)
            raise
        except Exception as e:
            logger.error("AgentRuntime 未预期异常", exc_info=True)
            yield Event.error("内部错误")
            yield Event.done(self._fallback_message("internal_error"))
        finally:
            # persist — best-effort
            try:
                self.session.persist(self.ctx.db)
            except Exception as e:
                logger.error(f"Session persist 失败: {e}", exc_info=True)

            # end trace — best-effort
            self._safe_end_trace(trace, final_text)

    # ------------------------------------------------------------------
    # 内部辅助方法（全部 best-effort，不向主循环抛异常）
    # ------------------------------------------------------------------

    def _build_messages_for_llm(self):
        """应用短期记忆策略并转换为 OpenAI 风格消息字典列表"""
        try:
            messages = apply_memory_policy(
                self.session.messages,
                policy=self._current_agent.memory_short_term_policy,
                window=getattr(self._current_agent, "memory_short_term_window", 20),
            )
        except Exception as e:
            logger.error(f"apply_memory_policy 失败: {e}", exc_info=True)
            messages = list(self.session.messages)

        return [
            {
                "role": getattr(m, "role", "user"),
                "content": getattr(m, "content", "") or "",
            }
            for m in messages
        ]

    async def _safe_get_tools(self):
        """获取工具列表（失败时返回空列表）"""
        try:
            return await self.tool_registry.get_tools_for_agent(
                self._current_agent.id, self.ctx
            )
        except Exception as e:
            logger.error(f"加载工具列表失败: {e}", exc_info=True)
            return []

    def _safe_generate_handoff_tools(self):
        """生成 handoff 工具 schemas（失败时返回空列表）"""
        try:
            return generate_handoff_tools(
                self._current_agent,
                load_agent_by_slug=self._load_agent_by_slug,
            )
        except Exception as e:
            logger.error(f"生成 handoff 工具失败: {e}", exc_info=True)
            return []

    def _safe_detect_handoff(self, tool_calls):
        """检测 handoff（失败时返回 None）"""
        try:
            return detect_handoff(
                tool_calls, self._current_agent, self._load_agent_by_slug
            )
        except Exception as e:
            logger.error(f"handoff 检测失败: {e}", exc_info=True)
            return None

    def _safe_start_trace(self, user_message: str):
        """创建 trace，失败时返回 fallback 对象"""
        try:
            return self.ctx.trace_recorder.start_trace(
                conversation_id=str(self.session.conversation.id),
                agent_id=str(self._current_agent.id),
                user_id=str(self.ctx.user_id),
                input_text=user_message,
            )
        except Exception as e:
            logger.error(f"Trace 创建失败: {e}", exc_info=True)
            # 返回一个 dummy trace，使后续 start_step / end_trace 可以安全调用
            return _FallbackTrace()

    def _safe_start_step(self, trace):
        """创建 trace step，失败时返回 None"""
        try:
            return self.ctx.trace_recorder.start_step(trace.id, "llm_call")
        except Exception as e:
            logger.error(f"Trace step 创建失败: {e}", exc_info=True)
            return None

    def _safe_end_step(self, step, **kwargs):
        """结束 trace step，失败时仅记录日志"""
        if step is None:
            return
        try:
            self.ctx.trace_recorder.end_step(step, **kwargs)
        except Exception as e:
            logger.error(f"Trace step 结束失败: {e}", exc_info=True)

    def _safe_end_trace(self, trace, final_text):
        """结束 trace，失败时仅记录日志"""
        if trace is None:
            return
        try:
            self.ctx.trace_recorder.end_trace(
                trace,
                output_text=final_text,
                total_steps=self._step_count,
                status="success" if final_text else "error",
            )
        except Exception as e:
            logger.error(f"Trace end 失败: {e}", exc_info=True)

    def _load_agent_by_slug(self, slug: str):
        """按 slug 加载 agent（用于 handoff）"""
        try:
            from app.models.agent import Agent
            return (
                self.ctx.db.query(Agent)
                .filter(Agent.slug == slug, Agent.is_active == True)
                .first()
            )
        except Exception as e:
            logger.error(f"加载 agent slug={slug} 失败: {e}", exc_info=True)
            return None

    def _fallback_message(self, reason: str) -> str:
        """根据原因返回用户友好的兜底消息"""
        messages = {
            "input_blocked": "抱歉，您的输入未通过安全校验。",
            "output_blocked": "抱歉，AI 输出未通过校验。",
            "llm_error": "抱歉，AI 服务暂时不可用，请稍后重试。",
            "max_steps": "抱歉，任务过于复杂，我未能完成。请简化问题再试。",
            "internal_error": "抱歉，发生了内部错误，请联系管理员。",
        }
        return messages.get(reason, "抱歉，发生了未知错误。")


class _FallbackTrace:
    """trace 创建失败时的 dummy 对象，避免后续代码对 None 做属性访问"""

    def __init__(self):
        self.id = "trace-fallback"
