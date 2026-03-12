"""
LLM Provider 抽象基类
定义所有 LLM 供应商的统一接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass


@dataclass
class Message:
    """消息对象"""

    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class GenerationConfig:
    """生成配置"""

    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30


@dataclass
class GenerationResult:
    """生成结果"""

    content: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    model: str
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.extra_params = kwargs

    @abstractmethod
    async def generate(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """
        生成文本

        Args:
            messages: 消息列表
            config: 生成配置

        Returns:
            生成结果
        """
        pass

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """
        测试连接

        Returns:
            (是否成功, 错误信息)
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, messages: List[Message], config: Optional[GenerationConfig] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        pass

    def format_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """格式化消息为供应商特定格式 (默认实现)"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
