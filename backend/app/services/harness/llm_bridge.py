"""LLMFunctionBridge — 工具与 LLM 的桥接

参考 spec §6.5

屏蔽 OpenAI / Claude 等 provider 的工具调用格式差异：
- build_request: 把 ToolProtocol 列表转为 LLM function schema
- parse_tool_calls: 同时支持 OpenAI 的 tool_calls 数组与 Claude 的 content tool_use blocks
- build_tool_result_messages: 把 ToolResult 包装为 tool role message 喂回 LLM
- generate: 调用 OrderedLLMGateway 并把结果归一化为 LLMResponse
"""
import json
import logging
from typing import Any, Dict, List, Tuple

from app.constants.llm_categories import LLMCategory
from app.services.harness.tool_protocol import ToolCall, ToolProtocol, ToolResult

logger = logging.getLogger(__name__)


class LLMResponse:
    """LLM 响应归一化结构

    屏蔽 provider 差异，统一暴露给上层：
    - text_part: 最终文本回复
    - thinking_part: 思考过程（Claude extended thinking 等）
    - tool_calls: 解析后的 ToolCall 列表
    - usage: token 使用统计
    - raw: provider 原始响应
    """

    def __init__(
        self,
        text_part: str = "",
        thinking_part: str = "",
        tool_calls: List[ToolCall] = None,
        usage: dict = None,
        raw: Any = None,
    ):
        self.text_part = text_part
        self.thinking_part = thinking_part
        self.tool_calls = tool_calls or []
        self.usage = usage or {}
        self.raw = raw

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMFunctionBridge:
    """工具与 LLM 的桥接

    职责：
    1. 把 ToolProtocol 列表转为 LLM function schema
    2. 把 LLM 的 tool_use response 解析为 ToolCall 列表
    3. 把 ToolResult 转回 LLM 能理解的 message

    不感知具体 provider，差异由 OrderedLLMGateway 屏蔽。
    """

    def __init__(self, gateway, default_category: str = None):
        """
        Args:
            gateway: OrderedLLMGateway 实例（或其他实现了 generate 的网关）
            default_category: 默认 LLM 分类（默认 text）
        """
        self.gateway = gateway
        self.default_category = default_category or LLMCategory.TEXT

    # ------------------------------------------------------------------
    # request 构造
    # ------------------------------------------------------------------

    def build_request(
        self,
        messages: List[dict],
        tools: List[ToolProtocol],
        model: str = None,
        fallback_models: List[str] = None,
        generation_params: Dict[str, Any] = None,
    ) -> dict:
        """构建带工具的 LLM 请求

        返回的 dict 可直接展开为 OrderedLLMGateway.generate 的 kwargs（不含 category）。
        """
        request: Dict[str, Any] = {
            "messages": messages,
        }

        if tools:
            request["tools"] = [t.to_function_schema() for t in tools]

        if model:
            request["model"] = model
        if fallback_models:
            request["fallback_models"] = fallback_models
        if generation_params:
            # generation_params 与内置字段可能重名，传入值优先级更高
            request.update(generation_params)

        return request

    # ------------------------------------------------------------------
    # 调用
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[dict],
        tools: List[dict],
        model: str = None,
        fallback_models: List[str] = None,
        generation_params: Dict[str, Any] = None,
        stream: bool = False,
        category: str = None,
    ) -> LLMResponse:
        """调用 LLM 并返回解析后的响应

        Args:
            messages: OpenAI 风格消息列表
            tools: 已经过 to_function_schema() 转换的工具 schema 列表
            model: 指定模型名（可选）
            fallback_models: 兜底模型列表（可选）
            generation_params: temperature / max_tokens 等透传参数
            stream: 是否流式（Phase 1 未实现，保留接口）
            category: LLM 分类（默认 text）
        """
        request = {
            "messages": messages,
        }
        if tools:
            request["tools"] = tools
        if model:
            request["model"] = model
        if fallback_models:
            request["fallback_models"] = fallback_models
        if generation_params:
            request.update(generation_params)

        cat = category or self.default_category

        try:
            result = await self.gateway.generate(category=cat, **request)
        except Exception as e:
            logger.error(f"LLM 调用失败 category={cat}: {e}", exc_info=True)
            raise

        return self._adapt_response(result)

    # ------------------------------------------------------------------
    # 响应解析
    # ------------------------------------------------------------------

    def parse_tool_calls(self, response: dict) -> List[ToolCall]:
        """从 LLM 响应解析工具调用

        支持格式：
        - OpenAI: response.tool_calls（数组，每项含 id / function.name / function.arguments）
        - Claude: response.content 中 type=="tool_use" 的 block（含 id / name / input）
        """
        if not response:
            return []

        # OpenAI 格式
        tool_calls_raw = response.get("tool_calls") or []
        if tool_calls_raw:
            calls: List[ToolCall] = []
            for tc in tool_calls_raw:
                func = tc.get("function", {}) if isinstance(tc, dict) else {}
                name = func.get("name", "") if isinstance(func, dict) else ""
                args_str = func.get("arguments", "{}") if isinstance(func, dict) else "{}"
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    logger.warning(f"工具调用参数 JSON 解析失败 name={name}: {args_str!r}")
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                calls.append(ToolCall(
                    id=tc.get("id", f"call_{name}") if isinstance(tc, dict) else f"call_{name}",
                    name=name,
                    arguments=args,
                ))
            return calls

        # Claude 格式（content blocks）
        content = response.get("content", [])
        if isinstance(content, list):
            calls = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    input_args = block.get("input", {}) or {}
                    if not isinstance(input_args, dict):
                        input_args = {}
                    calls.append(ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=input_args,
                    ))
            return calls

        return []

    def build_tool_result_messages(
        self, calls_and_results: List[Tuple[ToolCall, ToolResult]]
    ) -> List[dict]:
        """构建工具结果消息（喂回 LLM）

        对每对 (call, result) 生成一条 role="tool" 的消息，包含：
        - tool_call_id: 对应的 ToolCall.id
        - name: 工具名
        - content: ToolResult.to_llm_text()
        """
        messages = []

        for call, result in calls_and_results:
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                "content": result.to_llm_text(),
            })

        return messages

    # ------------------------------------------------------------------
    # 响应归一化
    # ------------------------------------------------------------------

    def _adapt_response(self, result) -> LLMResponse:
        """把 gateway 返回值适配为 LLMResponse

        支持：
        - str: 纯文本回复
        - dict: OpenAI / Claude 风格响应
        - object: 含 .content / .usage 属性的 provider 原生对象
        """
        if isinstance(result, str):
            return LLMResponse(
                text_part=result,
                thinking_part="",
                tool_calls=[],
                usage={},
                raw=result,
            )

        if isinstance(result, dict):
            # content 在 Claude 格式下也可能是 list（text + tool_use 混合）
            content_raw = result.get("content", "")
            if isinstance(content_raw, list):
                # 混合内容块：提取 text 部分，tool_use 由 parse_tool_calls 处理
                texts = [
                    b.get("text", "")
                    for b in content_raw
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                text_part = "\n".join(t for t in texts if t) or ""
            else:
                text_part = content_raw or ""

            tool_calls = self.parse_tool_calls(result)
            usage = result.get("usage", {}) or {}
            thinking_part = result.get("thinking", "") or ""
            return LLMResponse(
                text_part=text_part,
                thinking_part=thinking_part,
                tool_calls=tool_calls,
                usage=usage,
                raw=result,
            )

        # 对象形式（provider 原生响应）
        text_part = getattr(result, "content", "") or ""
        usage = getattr(result, "usage", {}) or {}
        return LLMResponse(
            text_part=text_part,
            thinking_part="",
            tool_calls=[],
            usage=usage,
            raw=result,
        )