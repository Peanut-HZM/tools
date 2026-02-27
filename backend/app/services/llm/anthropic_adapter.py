"""
Anthropic Claude LLM 适配器
"""

from typing import List, Optional
from anthropic import AsyncAnthropic

from .base import LLMProvider, Message, GenerationConfig, GenerationResult


class AnthropicAdapter(LLMProvider):
    """Anthropic Claude 适配器"""

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        super().__init__(api_key, base_url, model, **kwargs)
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.anthropic.com" else None,
            timeout=kwargs.get("timeout", 30),
        )

    async def generate(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        if config is None:
            config = GenerationConfig()

        # Anthropic 使用不同的消息格式
        system_msg = ""
        user_messages = []

        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        response = await self.client.messages.create(
            model=self.model,
            messages=user_messages,
            system=system_msg if system_msg else None,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        return GenerationResult(
            content=response.content[0].text,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            },
            model=self.model,
            finish_reason=response.stop_reason,
        )

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return True, ""
        except Exception as e:
            return False, str(e)
