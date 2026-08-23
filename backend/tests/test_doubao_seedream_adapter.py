"""DoubaoSeedreamAdapter 测试"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm.doubao_seedream_adapter import DoubaoSeedreamAdapter
from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure


@pytest.mark.asyncio
async def test_text2img_happy():
    """测试 text2img 正常流程：POST 返回 url，GET 下载图片二进制"""
    a = DoubaoSeedreamAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_post = AsyncMock()
    mock_post.status_code = 200
    mock_post.json = lambda: {"data": [{"url": "https://oss/a.png"}]}

    mock_get = AsyncMock()
    mock_get.content = b"fake"
    mock_get.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post)
        mock_client.get = AsyncMock(return_value=mock_get)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await a.generate("text2img", "a cat")

    assert result == [b"fake"]


@pytest.mark.asyncio
async def test_rate_limit_is_recoverable():
    """测试 429 限流应抛出 RecoverableFailure"""
    a = DoubaoSeedreamAdapter(api_key="x", base_url="https://x.com", model="m")

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
    a = DoubaoSeedreamAdapter(api_key="x", base_url="https://x.com", model="m")

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
