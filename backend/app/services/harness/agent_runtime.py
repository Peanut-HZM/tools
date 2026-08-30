"""AgentRuntime — ReAct 主循环

参考 spec §7.2

AgentRuntime 是 harness 的核心编排器：
- 驱动一轮 (turn) 的完整 ReAct 循环
- 在每次 LLM 调用前后串联 guardrail / memory / handoff / tool 执行
- 所有 DB / 遥测操作均 try/except 包裹，保证主循环不崩溃
"""
import asyncio
import json
import logging
import uuid
from typing import AsyncIterator, Optional

from app.models.harness_models import Branch
from app.services.harness.checkpoint_service import CheckpointService
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
        self._cached_memory_block = ""
        self._cached_skill_block = ""

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

        # 2a. checkpoint（after_user_message）
        await self._write_checkpoint("after_user_message")

        # 2b. 预取长期记忆（best-effort，不阻塞主循环）
        try:
            memory_entries = await self._retrieve_long_term_memory(user_message)
            self._cached_memory_block = self._build_memory_block(memory_entries)
        except Exception as e:
            logger.warning("记忆预取失败: %s", type(e).__name__)
            self._cached_memory_block = ""

        # 2c. 预取技能索引（best-effort，不阻塞主循环）
        try:
            self._cached_skill_block = await self._build_skill_block()
        except Exception as e:
            logger.warning("技能索引预取失败: %s", type(e).__name__)
            self._cached_skill_block = ""

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

                tool_schemas = self.tool_registry.to_function_schemas(tools)
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

                    # 持久化触发 handoff 的 LLM 响应
                    try:
                        self.session.append_assistant_message(llm_response)
                    except Exception as e:
                        logger.error(f"记录 handoff assistant 消息失败: {e}", exc_info=True)

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
                            # 构建合成 LLMResponse，使持久化的是 fallback 文本
                            llm_response = LLMResponse(
                                text_part=final_text,
                                tool_calls=[],
                                usage=llm_response.usage,
                            )
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
                        # checkpoint（before_tool）
                        await self._write_checkpoint("before_tool")
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
                        # checkpoint（after_tool）
                        await self._write_checkpoint("after_tool")
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

    def _ensure_main_branch(self) -> Optional[uuid.UUID]:
        """懒加载创建主线分支

        首次写入 checkpoint 时若 conversation.main_branch_id 为空，
        自动创建一个名为「主线」的 Branch 并回写到 conversation.main_branch_id。
        返回 main_branch_id；任何异常返回 None（调用方按"无分支"处理）。
        """
        try:
            conversation = self.session.conversation
            if not conversation.main_branch_id:
                # 预生成分支 id，保证 mock db 下 conversation.main_branch_id 也能被赋值
                branch = Branch(
                    id=uuid.uuid4(),
                    conversation_id=conversation.id,
                    name="主线",
                )
                self.ctx.db.add(branch)
                self.ctx.db.flush()
                conversation.main_branch_id = branch.id
                self.ctx.db.commit()
                logger.info(
                    "懒加载创建主线分支 conv=%s branch=%s",
                    conversation.id,
                    branch.id,
                )
            return conversation.main_branch_id
        except Exception as e:
            logger.error(f"创建主线分支失败: {e}", exc_info=True)
            try:
                self.ctx.db.rollback()
            except Exception:
                pass
            return None

    async def _write_checkpoint(self, phase: str):
        """写入 checkpoint（完整快照），通过 CheckpointService

        best-effort：任何异常均吞掉，不向主循环抛异常。
        - phase: after_user_message / before_tool / after_tool
        - step_index: 当前步数（after_user_message 时为 0）
        - branch_id: conversation.main_branch_id（缺失则懒加载创建）
        """
        try:
            branch_id = self._ensure_main_branch()
            if branch_id is None:
                return

            conversation = self.session.conversation
            cs = CheckpointService(self.ctx.db)
            cs.write_checkpoint(
                conversation_id=conversation.id,
                step_index=self._step_count,
                phase=phase,
                messages=list(self.session.messages),
                scratch_state=dict(self.session.scratch_state),
                branch_id=branch_id,
            )
        except Exception as e:
            logger.error(
                "写入 checkpoint 失败 (phase=%s): %s", phase, type(e).__name__, exc_info=True
            )

    def _build_messages_for_llm(self):
        """应用短期记忆策略 + 注入 system prompt + 长期记忆"""
        try:
            messages = apply_memory_policy(
                self.session.messages,
                policy=self._current_agent.memory_short_term_policy,
                window=getattr(self._current_agent, "memory_short_term_window", 20),
            )
        except Exception as e:
            logger.error(f"apply_memory_policy 失败: {e}", exc_info=True)
            messages = list(self.session.messages)

        result_dicts = [
            {
                "role": getattr(m, "role", "user"),
                "content": getattr(m, "content", "") or "",
            }
            for m in messages
        ]

        # 构建 system prompt（agent.system_prompt + 长期记忆注入块）
        system_parts = []
        agent_system_prompt = getattr(self._current_agent, "system_prompt", "")
        # 仅在是 str 类型时纳入（避免 MagicMock 等被 join）
        if isinstance(agent_system_prompt, str) and agent_system_prompt:
            system_parts.append(agent_system_prompt)

        # 长期记忆注入（由 run() 中预取后缓存在 self._cached_memory_block）
        memory_block = getattr(self, "_cached_memory_block", "")
        if isinstance(memory_block, str) and memory_block:
            system_parts.append(memory_block)

        # 技能索引注入（渐进披露：索引进 prompt，内容按需 skill_read）
        skill_block = getattr(self, "_cached_skill_block", "")
        if isinstance(skill_block, str) and skill_block:
            system_parts.append(skill_block)

        if system_parts:
            system_content = "\n\n".join(system_parts)
            # 插入到消息列表最前面（system role）
            result_dicts.insert(0, {"role": "system", "content": system_content})

        return result_dicts

    async def _build_skill_block(self) -> str:
        """构建技能索引注入块（渐进披露：索引进 prompt，内容按需 skill_read）

        - 未启用 / 无技能 / 查询失败 → 空串（不注入）
        - 索引上限 20 条由 SkillService.list_enabled 控制
        """
        if not getattr(self._current_agent, "memory_procedural_enabled", False):
            return ""
        try:
            agent_uuid = uuid.UUID(str(self._current_agent.id))
            user_uuid = uuid.UUID(str(self.ctx.user_id))
        except (ValueError, TypeError, AttributeError):
            return ""

        from app.services.harness.skill_service import SkillService

        skills = await SkillService(self.ctx.db).list_enabled(agent_uuid, user_uuid)
        if not skills:
            return ""
        lines = [
            "<procedural_memory>",
            "你可以使用以下技能（skill）。当任务匹配某技能的触发条件时，"
            "调用 skill_read(name=...) 获取完整内容后遵循执行：",
        ]
        for s_ in skills:
            lines.append(f"- {s_.name}: {s_.trigger} (使用次数: {s_.use_count})")
        lines.append("</procedural_memory>")
        return "\n".join(lines)

    async def _retrieve_long_term_memory(self, user_message: str) -> list:
        """检索长期记忆（best-effort，不阻塞主循环）

        - 当 agent.memory_long_term_enabled=False 时直接跳过
        - 当 memory_long_term_config.auto_inject=False 时跳过
        - embedding provider 创建失败时降级（不创建 provider，走关键词检索）
        - 任何异常都被捕获，记录 warning 后返回空列表
        """
        if not getattr(self._current_agent, "memory_long_term_enabled", False):
            return []

        cfg = getattr(self._current_agent, "memory_long_term_config", {}) or {}
        if not cfg.get("auto_inject", True):
            return []

        try:
            from app.services.harness.memory_service import MemoryService
            from app.services.harness.embeddings.factory import create_embedding_provider

            provider = None
            if cfg.get("embedding_provider"):
                try:
                    provider = create_embedding_provider(cfg)
                except Exception as e:
                    logger.warning(
                        "auto-inject embedding provider 创建失败: %s", type(e).__name__
                    )

            svc = MemoryService(db=self.ctx.db, embedding_provider=provider)
            query = (user_message or "")[:500]
            timeout = cfg.get("auto_inject_timeout_seconds", 5)
            top_k = cfg.get("auto_inject_top_k", 5)
            threshold = cfg.get("auto_inject_threshold", 0.7)

            results = await svc.search(
                uuid.UUID(str(self._current_agent.id)),
                uuid.UUID(str(self.ctx.user_id)),
                query,
                top_k=top_k,
                threshold=threshold,
                timeout_seconds=timeout,
            )
            return results
        except Exception as e:
            logger.warning("长期记忆检索失败: %s", type(e).__name__)
            return []

    def _build_memory_block(self, entries: list) -> str:
        """将记忆检索结果构建为 system prompt 注入块

        空结果返回空字符串，便于上层条件拼接。
        """
        if not entries:
            return ""

        lines = ["<long_term_memory>", "以下是与当前对话相关的长期记忆："]
        for e in entries:
            value_text = ""
            if isinstance(e.value, dict) and "text" in e.value:
                value_text = str(e.value["text"])
            else:
                value_text = json.dumps(e.value, ensure_ascii=False)
            lines.append(f"- [{e.key}]: {value_text} (相关度: {e.score:.2f})")
        lines.append("</long_term_memory>")
        return "\n".join(lines)

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
