"""
百度文心一言 LLM 适配器
支持百度文心一言 ERNIE 系列模型
"""

from typing import List, Optional, Dict
import httpx
import hashlib
import time
import base64
import json

from .base import LLMProvider, Message, GenerationConfig, GenerationResult


class BaiduWenxinAdapter(LLMProvider):
    """百度文心一言适配器

    百度文心一言使用不同的 API 格式：
    - 鉴权方式：AK/SK 签名
    - API 端点：https://aip.baidubce.com/rpc/2.0/ai_custom/v1
    - 消息格式：百度特定的 JSON 格式
    """

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        """
        初始化百度文心一言适配器

        Args:
            api_key: API Key (可以包含 access_token 或需要单独获取)
            base_url: API 基础 URL
            model: 模型名称 (如 ernie-bot, ernie-bot-turbo)
            **kwargs: 额外参数，可包含 secret_key
        """
        super().__init__(api_key, base_url, model, **kwargs)
        self.secret_key = kwargs.get("secret_key", "")
        self.access_token = None
        self.token_expires_at = 0

        # 默认使用百度云 ERNIE API
        self._base_url = base_url or "https://aip.baidubce.com"

    async def _get_access_token(self) -> str:
        """
        获取访问令牌

        使用 AK/SK 获取 access_token
        """
        current_time = time.time()

        # 如果已有 token 且未过期，直接返回
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token

        # 获取新 token
        # 注意：实际使用时需要使用真实的 AK/SK
        auth_url = f"{self._base_url}/oauth/2.0/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_url,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                # 提前 5 分钟过期
                self.token_expires_at = (
                    current_time + data.get("expires_in", 2592000) - 300
                )
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {response.text}")

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """
        将消息转换为百度格式

        百度 ERNIE API 使用不同的消息格式
        """
        converted = []
        for msg in messages:
            # 百度使用 "user" 和 "assistant" 而不是 "user" 和 "assistant"
            role = msg.role
            if role == "system":
                role = "system"
            elif role == "assistant":
                role = "assistant"
            else:
                role = "user"

            converted.append({"role": role, "content": msg.content})

        return converted

    async def generate(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """生成文本"""
        if config is None:
            config = GenerationConfig()

        # 获取 access token
        try:
            access_token = await self._get_access_token()
        except Exception as e:
            # 如果无法获取 token，尝试直接使用 API Key
            access_token = self.api_key

        # 构建请求
        url = f"{self._base_url}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{self.model}"

        headers = {
            "Content-Type": "application/json",
        }

        params = {
            "access_token": access_token,
        }

        # 构建消息
        converted_messages = self._convert_messages(messages)

        payload = {
            "messages": converted_messages,
            "temperature": config.temperature,
            "max_output_tokens": config.max_tokens,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                json=payload,
                timeout=config.timeout,
            )

            if response.status_code != 200:
                raise Exception(f"API request failed: {response.text}")

            data = response.json()

            # 检查错误
            if "error_code" in data:
                raise Exception(f"API error: {data.get('error_msg', data)}")

            return GenerationResult(
                content=data.get("result", ""),
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get(
                        "completion_tokens", 0
                    ),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
                model=self.model,
                finish_reason=data.get("finish_reason", "stop"),
            )

    async def test_connection(self) -> tuple[bool, str]:
        """测试连接"""
        try:
            # 尝试获取 access token
            access_token = await self._get_access_token()
            if access_token:
                return True, ""
            return False, "Failed to get access token"
        except httpx.TimeoutException:
            return False, "Connection timeout"
        except httpx.ConnectError as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, str(e)

    async def generate_stream(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ):
        """流式生成文本

        注意：百度 ERNIE 不支持流式输出，此处返回完整结果
        """
        result = await self.generate(messages, config)
        yield result.content
