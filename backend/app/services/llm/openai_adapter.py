"""
OpenAI LLM 适配器
"""

import json
import logging
from typing import List, Optional, Any
import httpx
from openai import AsyncOpenAI

from .base import LLMProvider, Message, GenerationConfig, GenerationResult
from .exceptions import RecoverableFailure, UnrecoverableFailure

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMProvider):
    """OpenAI GPT 适配器"""

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        super().__init__(api_key, base_url, model, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None,
            timeout=kwargs.get("timeout", 30),
        )

    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        if config is None:
            config = GenerationConfig()

        formatted_messages = self.format_messages(messages)

        # 构造请求参数
        create_kwargs = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        # 支持工具调用（OpenAI function calling）
        tools = kwargs.get("tools")
        if tools:
            # 转换为 OpenAI tools 格式
            create_kwargs["tools"] = self._convert_tools(tools)

        try:
            response = await self.client.chat.completions.create(**create_kwargs)
        except Exception as e:
            # 将 OpenAI SDK 异常映射到兜底链异常体系
            # 401/403 → 鉴权错，不可恢复
            # 400 参数错 → 不可恢复
            # 404 模型不存在 → 可恢复（让兜底链尝试下一个模型）
            # 429 限流 / 5xx → 可恢复
            status = getattr(e, "status_code", None)
            if status in (401, 403):
                raise UnrecoverableFailure(f"OpenAI 鉴权失败: {e}") from e
            if status == 400:
                raise UnrecoverableFailure(f"OpenAI 请求参数错误: {e}") from e
            logger.warning("[openai_adapter] API error status=%s: %s", status, e)
            raise RecoverableFailure(f"OpenAI API 错误 ({status}): {e}") from e

        choice = response.choices[0]

        # 处理工具调用
        tool_calls_result = None
        if choice.message.tool_calls:
            tool_calls_result = []
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                tool_calls_result.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })
            logger.info(
                "[openai_adapter] tool_calls=%d model=%s",
                len(tool_calls_result),
                self.model,
            )

        return GenerationResult(
            content=choice.message.content or "",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=self.model,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls_result,
        )

    @staticmethod
    def _convert_tools(tools: List[Any]) -> List[dict]:
        """将自研 tool 定义转换为 OpenAI tools 格式

        自研格式示例：
          {"name": "generate_image", "arguments": {"operation": ..., "prompt": ...}}
        OpenAI 格式：
          {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        """
        result = []
        for t in tools:
            if isinstance(t, dict):
                name = t.get("name", "")
                # 如果已经是 OpenAI 格式（有 function 字段），直接使用
                if "function" in t:
                    result.append(t)
                else:
                    # 从 arguments 推断参数 schema
                    args = t.get("arguments", {})
                    properties = {}
                    required = []
                    for k, v in args.items():
                        prop = {"type": "string"}
                        if isinstance(v, int):
                            prop = {"type": "integer"}
                        elif isinstance(v, float):
                            prop = {"type": "number"}
                        elif isinstance(v, bool):
                            prop = {"type": "boolean"}
                        properties[k] = prop
                        required.append(k)
                    result.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": t.get("description", name),
                            "parameters": {
                                "type": "object",
                                "properties": properties,
                                "required": required,
                            },
                        },
                    })
            else:
                # 非 dict 直接透传
                result.append(t)
        return result

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return True, ""
        except Exception as e:
            return False, str(e)

    async def generate_stream(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ):
        """流式生成文本"""
        if config is None:
            config = GenerationConfig()

        formatted_messages = self.format_messages(messages)

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
