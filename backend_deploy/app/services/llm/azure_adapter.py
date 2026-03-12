"""
Azure OpenAI LLM 适配器
支持 Azure OpenAI 服务
"""

from typing import List, Optional
import httpx

from .base import LLMProvider, Message, GenerationConfig, GenerationResult


class AzureOpenAIAdapter(LLMProvider):
    """Azure OpenAI 适配器

    Azure OpenAI 与标准 OpenAI API 略有不同：
    - 需要使用 Azure 的 API 版本
    - 使用 api-version 查询参数
    - 部署名称（而非模型名称）
    """

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        """
        初始化 Azure OpenAI 适配器

        Args:
            api_key: Azure API Key
            base_url: Azure 端点 URL (如 https://<resource>.openai.azure.com)
            model: 部署名称（不是模型名称）
            **kwargs: 额外参数，可包含 api_version
        """
        super().__init__(api_key, base_url, model, **kwargs)
        self.api_version = kwargs.get("api_version", "2024-02-15-preview")

        # 构建完整的 API URL
        self._build_client()

    def _build_client(self):
        """构建 HTTP 客户端"""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=self.extra_params.get("timeout", 30),
        )

    async def generate(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """生成文本"""
        if config is None:
            config = GenerationConfig()

        formatted_messages = self.format_messages(messages)

        # Azure OpenAI API 路径
        url = f"/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"

        response = await self.client.post(
            url,
            json={
                "messages": formatted_messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()

        return GenerationResult(
            content=data["choices"][0]["message"]["content"],
            usage={
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
            model=self.model,
            finish_reason=data["choices"][0].get("finish_reason"),
        )

    async def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            # 使用模型列表端点测试
            url = f"/openai/models?api-version={self.api_version}"
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

        url = f"/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"

        async with self.client.stream(
            "POST",
            url,
            json={
                "messages": formatted_messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream": True,
            },
        ) as response:
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
