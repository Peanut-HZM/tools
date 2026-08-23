"""OpenAIImageAdapter 测试"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm.openai_image_adapter import OpenAIImageAdapter
from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure, OperationNotSupportedError


@pytest.mark.asyncio
async def test_text2img_happy():
    """测试 text2img 正常流程：POST 返回 url，GET 下载图片二进制"""
    a = OpenAIImageAdapter(api_key="x", base_url="https://x.com", model="dall-e-3")

    mock_post = AsyncMock()
    mock_post.status_code = 200
    mock_post.json = lambda: {"data": [{"url": "https://oss/dalle.png"}]}

    mock_get = AsyncMock()
    mock_get.content = b"dalle_fake"
    mock_get.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post)
        mock_client.get = AsyncMock(return_value=mock_get)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await a.generate("text2img", "a cat")

    assert result == [b"dalle_fake"]


@pytest.mark.asyncio
async def test_rate_limit_is_recoverable():
    """测试 429 限流应抛出 RecoverableFailure"""
    a = OpenAIImageAdapter(api_key="x", base_url="https://x.com", model="dall-e-3")

    mock_resp = AsyncMock()
    mock_resp.status_code = 429
    mock_resp.text = "rate limited"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RecoverableFailure):
            await a.generate("text2img", "x")


@pytest.mark.asyncio
async def test_auth_error_is_unrecoverable():
    """测试 401 鉴权失败应抛出 UnrecoverableFailure"""
    a = OpenAIImageAdapter(api_key="x", base_url="https://x.com", model="dall-e-3")

    mock_resp = AsyncMock()
    mock_resp.status_code = 401
    mock_resp.text = "unauthorized"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(UnrecoverableFailure):
            await a.generate("text2img", "x")


@pytest.mark.asyncio
async def test_unsupported_operation():
    """测试 DALL-E 3 不支持 img2img，应抛出 OperationNotSupportedError"""
    a = OpenAIImageAdapter(api_key="x", base_url="https://x.com", model="dall-e-3")

    with pytest.raises(OperationNotSupportedError):
        await a.generate("img2img", "a cat")
