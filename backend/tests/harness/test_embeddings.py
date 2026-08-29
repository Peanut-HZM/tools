"""EmbeddingProvider 单元测试"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.harness.embeddings.provider import EmbeddingProvider, TARGET_DIMENSION
from app.services.harness.embeddings.factory import create_embedding_provider
from app.services.harness.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.services.harness.embeddings.dashscope_provider import DashScopeEmbeddingProvider


# --- 维度对齐测试 ---

def test_pad_to_target_dimension():
    """不足 1536 维时补零"""
    vec = [0.1, 0.2, 0.3]
    result = OpenAIEmbeddingProvider._align_dimension(vec, TARGET_DIMENSION)
    assert len(result) == TARGET_DIMENSION
    assert result[0] == 0.1
    assert result[3] == 0.0


def test_truncate_to_target_dimension():
    """超过 1536 维时截断"""
    vec = [0.1] * 2000
    result = OpenAIEmbeddingProvider._align_dimension(vec, TARGET_DIMENSION)
    assert len(result) == TARGET_DIMENSION


def test_exact_dimension_noop():
    """恰好 1536 维时不变"""
    vec = [0.1] * TARGET_DIMENSION
    result = OpenAIEmbeddingProvider._align_dimension(vec, TARGET_DIMENSION)
    assert result == vec


# --- OpenAI Provider 测试 ---

@pytest.mark.asyncio
async def test_openai_provider_embed():
    """OpenAI provider 调用 API 返回向量"""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

    # 源码在 _get_client() 内做 lazy import: from openai import AsyncOpenAI
    # 因此 patch 源模块 openai，而不是 provider 模块
    with patch("openai.AsyncOpenAI") as mock_client:
        instance = mock_client.return_value
        instance.embeddings.create = AsyncMock(return_value=mock_response)

        provider = OpenAIEmbeddingProvider(
            api_key="sk-test", model="text-embedding-3-small"
        )
        result = await provider.embed(["hello"])
        assert len(result) == 1
        assert len(result[0]) == TARGET_DIMENSION


@pytest.mark.asyncio
async def test_openai_provider_validate():
    """validate() 调用 embed 验证可用性"""
    with patch.object(OpenAIEmbeddingProvider, "embed", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [[0.1] * 1536]
        provider = OpenAIEmbeddingProvider(api_key="sk-test", model="text-embedding-3-small")
        assert await provider.validate() is True


# --- DashScope Provider 测试 ---

@pytest.mark.asyncio
async def test_dashscope_provider_embed():
    """DashScope provider 调用 API 返回向量"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.output = {"embeddings": [{"embedding": [0.2] * 1024}]}

    # 源码在 embed() 内做 lazy import: import dashscope
    # 通过 sys.modules 注入 mock 模块
    import sys
    mock_ds = MagicMock()
    mock_ds.TextEmbedding.call = AsyncMock(return_value=mock_response)

    with patch.dict(sys.modules, {"dashscope": mock_ds}):
        provider = DashScopeEmbeddingProvider(
            api_key="sk-test", model="text-embedding-v3"
        )
        result = await provider.embed(["hello"])
        assert len(result) == 1
        assert len(result[0]) == TARGET_DIMENSION  # 补零到 1536


# --- 工厂测试 ---

def test_factory_openai():
    """工厂创建 OpenAI provider"""
    config = {
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "embedding_api_key": "sk-test",
    }
    provider = create_embedding_provider(config)
    assert isinstance(provider, OpenAIEmbeddingProvider)


def test_factory_dashscope():
    """工厂创建 DashScope provider"""
    config = {
        "embedding_provider": "dashscope",
        "embedding_model": "text-embedding-v3",
        "embedding_api_key": "sk-test",
    }
    provider = create_embedding_provider(config)
    assert isinstance(provider, DashScopeEmbeddingProvider)


def test_factory_unknown_raises():
    """未知 provider 抛异常"""
    config = {"embedding_provider": "unknown", "embedding_api_key": "sk-test"}
    with pytest.raises(ValueError, match="不支持的 embedding provider"):
        create_embedding_provider(config)


def test_factory_missing_api_key_fallback_to_env():
    """缺少 api_key 时从环境变量 fallback"""
    import os
    config = {"embedding_provider": "openai", "embedding_model": "text-embedding-3-small"}
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-test"}):
        provider = create_embedding_provider(config)
        assert isinstance(provider, OpenAIEmbeddingProvider)