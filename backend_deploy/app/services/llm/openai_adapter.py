"""
OpenAI LLM 适配器
"""

from typing import List, Optional
import httpx
from openai import AsyncOpenAI

from .base import LLMProvider, Message, GenerationConfig, GenerationResult


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
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        if config is None:
            config = GenerationConfig()

        formatted_messages = self.format_messages(messages)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        return GenerationResult(
            content=response.choices[0].message.content,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=self.model,
            finish_reason=response.choices[0].finish_reason,
        )

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
