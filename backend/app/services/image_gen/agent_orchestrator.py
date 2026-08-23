"""自研 Agent 对话编排器

维护 brain LLM 多轮调用：
  1. 发 messages + tools 给 brain（由 OrderedLLMGateway 透传）
  2. 若返回 tool_call：执行，把结果喂回去，继续循环
  3. 若无 tool_call：content 即最终回答，结束

防死循环：max_iterations 上限。

注意（相对 brief 的修正）：
  - assistant 消息只应在处理一次 LLM 响应时追加一次，而不是每个 tool_call 都追加，
    否则多个 tool_call 会重复写入同一条 assistant 消息。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.llm.ordered_gateway import OrderedLLMGateway

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """自研 Agent 编排器"""

    def __init__(self, gateway: OrderedLLMGateway, max_iterations: int = 5):
        self._gateway = gateway
        self._max_iterations = max_iterations

    async def run(
        self,
        messages: list[dict],
        tools: list[dict],
        executor: Optional[Any] = None,
    ) -> tuple[str, list[dict]]:
        """跑对话循环

        Args:
            messages: 初始消息列表（OpenAI 格式）
            tools: 工具定义列表，会透传给 gateway.generate
            executor: 工具执行器，需实现 `async execute(call) -> result`

        Returns:
            (final_answer_text, list_of_tool_results)
        """
        tool_results: list[dict] = []
        current_messages: list[dict] = list(messages)

        for iteration in range(self._max_iterations):
            logger.info(
                "[orchestrator] iteration=%d messages=%d",
                iteration, len(current_messages),
            )

            # gateway.generate 通过 **kwargs 透传 tools 给底层 adapter
            response = await self._gateway.generate(
                category="chat",
                messages=current_messages,
                tools=tools,
            )

            # 兼容属性访问与字典两种形态
            content = self._get_field(response, "content")
            tool_calls = self._get_field(response, "tool_calls") or []

            if not tool_calls:
                # 无 tool_call → 最终回答
                return content or "", tool_results

            # 有 tool_call 但没 executor → 配置错误
            if executor is None:
                raise ValueError("tool_call 返回但 executor 为 None")

            # 修正 brief 中的 bug：assistant 消息只追加一次（在 tool 循环之外）
            current_messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            for call in tool_calls:
                call_id = self._get_field(call, "id")
                call_name = self._get_field(call, "name")
                logger.info(
                    "[orchestrator] tool_call name=%s id=%s",
                    call_name, call_id,
                )

                result = await executor.execute(call)
                tool_results.append(result)

                # 把每个 tool 的执行结果作为 tool message 喂回去
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": str(result),
                })

        # 超过最大轮次，best-effort 返回当前累积的 tool_results
        logger.warning(
            "[orchestrator] hit max_iterations=%d", self._max_iterations,
        )
        return "", tool_results

    @staticmethod
    def _get_field(obj: Any, name: str) -> Any:
        """兼容 dict / 对象两种字段访问方式"""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)
