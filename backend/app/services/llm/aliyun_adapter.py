"""
阿里云通义千问 LLM 适配器
支持阿里云灵积 DashScope 的 Qwen 系列模型
"""

import json
import logging
from typing import List, Optional, Dict, Any
import httpx

from .base import LLMProvider, Message, GenerationConfig, GenerationResult
from .exceptions import RecoverableFailure, UnrecoverableFailure

logger = logging.getLogger(__name__)


class AliyunQwenAdapter(LLMProvider):
    """阿里云通义千问适配器

    阿里云通义千问 (DashScope) 使用 OpenAI 兼容格式：
    - API 端点：https://dashscope.aliyuncs.com/compatible-mode/v1
    - 支持 OpenAI 兼容格式，也支持原生格式
    - 鉴权：API-Key 在 Header 中
    """

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        """
        初始化阿里云通义千问适配器

        Args:
            api_key: DashScope API Key
            base_url: API 基础 URL (默认 https://dashscope.aliyuncs.com)
            model: 模型名称 (如 qwen-turbo, qwen-max)
            **kwargs: 额外参数
        """
        super().__init__(api_key, base_url, model, **kwargs)

        # 默认使用 DashScope OpenAI 兼容 API
        self._base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

        self.client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=kwargs.get("timeout", 30),
        )

    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """生成文本"""
        if config is None:
            config = GenerationConfig()

        formatted_messages = self.format_messages(messages)

        # 使用 OpenAI 兼容格式
        url = "/chat/completions"

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        # 支持工具调用（OpenAI 兼容格式）
        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = tools

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = e.response.text[:500]
            if status in (401, 403):
                raise UnrecoverableFailure(f"Aliyun 鉴权失败: {body}") from e
            if status == 400:
                raise UnrecoverableFailure(f"Aliyun 请求参数错误: {body}") from e
            logger.warning("[aliyun_adapter] HTTP error status=%s: %s", status, body)
            raise RecoverableFailure(f"Aliyun HTTP 错误 ({status}): {body}") from e
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise RecoverableFailure(f"Aliyun 网络错误: {e}") from e

        data = response.json()
        choice = data["choices"][0].get("message", {})

        # 处理工具调用
        tool_calls_result = None
        raw_tool_calls = choice.get("tool_calls")
        if raw_tool_calls:
            tool_calls_result = []
            for tc in raw_tool_calls:
                try:
                    fn = tc.get("function", {})
                    args = json.loads(fn.get("arguments", "{}") or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls_result.append({
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "arguments": args,
                })
            logger.info(
                "[aliyun_adapter] tool_calls=%d model=%s",
                len(tool_calls_result), self.model,
            )

        return GenerationResult(
            content=choice.get("content") or "",
            usage={
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
            model=self.model,
            finish_reason=data["choices"][0].get("finish_reason"),
            tool_calls=tool_calls_result,
        )

    async def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            # 使用模型列表端点测试
            url = "/models"
            response = await self.client.get(url)

            if response.status_code == 200:
                return True, ""
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
        except httpx.TimeoutException:
            return False, "Connection timeout"
        except httpx.ConnectError as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, str(e)

    async def generate_stream(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ):
        """流式生成文本"""
        if config is None:
            config = GenerationConfig()

        formatted_messages = self.format_messages(messages)

        url = "/chat/completions"

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": True,
        }

        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json

                    try:
                        chunk_data = json.loads(data)
                        if chunk_data.get("choices"):
                            delta = chunk_data["choices"][0].get("delta", {})
                            if delta.get("content"):
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    def close(self):
        """关闭客户端"""
        if hasattr(self, "client"):
            import asyncio

            asyncio.create_task(self.client.aclose())


class AliyunQwenNativeAdapter(AliyunQwenAdapter):
    """
    阿里云通义千问原生适配器

    使用 DashScope 原生 API 格式（非 OpenAI 兼容）
    """

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        # 使用原生 API 端点
        if not base_url:
            base_url = "https://dashscope.aliyuncs.com/api/v1"
        super().__init__(api_key, base_url, model, **kwargs)

    async def generate(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """使用原生格式生成文本"""
        if config is None:
            config = GenerationConfig()

        # 转换消息格式
        converted_messages = self._convert_to_native_format(messages)

        url = f"/services/aigc/text-generation/generation"

        payload = {
            "model": self.model,
            "input": {"messages": converted_messages},
            "parameters": {
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "result_format": "message",
            },
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        output = data.get("output", {})
        choices = output.get("choices", {})

        return GenerationResult(
            content=choices.get("message", {}).get("content", ""),
            usage={
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
            model=self.model,
            finish_reason=choices.get("finish_reason"),
        )

    def _convert_to_native_format(self, messages: List[Message]) -> List[Dict]:
        """转换为原生格式，兼容 Message 对象与 dict"""
        converted = []
        for msg in messages:
            if isinstance(msg, dict):
                converted.append(msg)
            else:
                converted.append({"role": msg.role, "content": msg.content})
        return converted
