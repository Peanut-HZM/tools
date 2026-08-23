"""QwenImageAdapter 测试"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm.qwen_image_adapter import QwenImageAdapter
from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure


@pytest.mark.asyncio
async def test_text2img_happy():
    """测试异步轮询正常流程：POST 提交任务 → GET 轮询 SUCCEEDED → 下载图片"""
    a = QwenImageAdapter(api_key="x", base_url="https://x.com", model="m")

    # POST 提交任务返回 task_id
    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json = lambda: {"output": {"task_id": "task-123"}}

    # GET 轮询返回 SUCCEEDED
    mock_poll_resp = AsyncMock()
    mock_poll_resp.status_code = 200
    mock_poll_resp.json = lambda: {
        "output": {
            "task_status": "SUCCEEDED",
            "results": [{"url": "https://oss/qwen.png"}],
        }
    }

    # GET 下载图片
    mock_img_resp = AsyncMock()
    mock_img_resp.content = b"qwen_fake"
    mock_img_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_resp)
        # 第一次 get 返回轮询结果，第二次 get 返回图片
        mock_client.get = AsyncMock(side_effect=[mock_poll_resp, mock_img_resp])
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await a.generate("text2img", "a dog")

    assert result == [b"qwen_fake"]


@pytest.mark.asyncio
async def test_rate_limit_is_recoverable():
    """测试提交任务时 429 限流应抛出 RecoverableFailure"""
    a = QwenImageAdapter(api_key="x", base_url="https://x.com", model="m")

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
    """测试提交任务时 401 鉴权失败应抛出 UnrecoverableFailure"""
    a = QwenImageAdapter(api_key="x", base_url="https://x.com", model="m")

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
async def test_poll_auth_error_is_unrecoverable():
    """测试轮询端点返回 401 时应抛出 UnrecoverableFailure（Finding 1）"""
    import httpx as _httpx

    a = QwenImageAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json = lambda: {"output": {"task_id": "task-123"}}

    mock_poll_resp = AsyncMock()
    mock_poll_resp.status_code = 401
    mock_poll_resp.text = "token expired"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.get = AsyncMock(return_value=mock_poll_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(UnrecoverableFailure):
            await a.generate("text2img", "x")


@pytest.mark.asyncio
async def test_poll_network_error_is_recoverable():
    """测试轮询时网络连接异常应抛出 RecoverableFailure（Finding 3）"""
    import httpx as _httpx

    a = QwenImageAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json = lambda: {"output": {"task_id": "task-123"}}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.get = AsyncMock(side_effect=_httpx.ConnectError("connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RecoverableFailure):
            await a.generate("text2img", "x")


@pytest.mark.asyncio
async def test_download_failure_is_recoverable():
    """测试轮询成功后下载图片失败应抛出 RecoverableFailure（Finding 2）"""
    import httpx as _httpx

    a = QwenImageAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json = lambda: {"output": {"task_id": "task-123"}}

    mock_poll_resp = AsyncMock()
    mock_poll_resp.status_code = 200
    mock_poll_resp.json = lambda: {
        "output": {
            "task_status": "SUCCEEDED",
            "results": [{"url": "https://oss/qwen.png"}],
        }
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_resp)
        # 轮询成功，但下载图片时抛出 HTTPStatusError
        mock_client.get = AsyncMock(
            side_effect=[
                mock_poll_resp,
                _httpx.HTTPStatusError("500 CDN error", request=None, response=AsyncMock()),
            ]
        )
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RecoverableFailure):
            await a.generate("text2img", "x")
