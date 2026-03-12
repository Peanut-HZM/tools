"""
LLM Provider 工厂
根据配置创建对应的适配器实例
"""

from typing import Optional, Dict, Type
from .base import LLMProvider
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .azure_adapter import AzureOpenAIAdapter
from .baidu_adapter import BaiduWenxinAdapter
from .aliyun_adapter import AliyunQwenAdapter


# 适配器注册表
ADAPTER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "azure_openai": AzureOpenAIAdapter,
    "baidu": BaiduWenxinAdapter,
    "aliyun": AliyunQwenAdapter,
    "other": OpenAIAdapter,  # 通用 OpenAI 兼容格式
}


def get_provider(
    provider_type: str, api_key: str, base_url: str, model: str, **kwargs
) -> Optional[LLMProvider]:
    """
    根据供应商类型获取适配器实例

    Args:
        provider_type: 供应商类型
        api_key: API Key
        base_url: API 基础 URL
        model: 模型名称
        **kwargs: 额外参数

    Returns:
        适配器实例
    """
    adapter_class = ADAPTER_REGISTRY.get(provider_type)
    if adapter_class is None:
        # 对于未知供应商类型，默认使用 OpenAI 兼容格式
        # 大多数 LLM 供应商都提供 OpenAI 兼容的 API 接口
        adapter_class = OpenAIAdapter

    return adapter_class(api_key, base_url, model, **kwargs)


def list_supported_providers() -> list[str]:
    """获取支持的供应商列表"""
    return list(ADAPTER_REGISTRY.keys())
