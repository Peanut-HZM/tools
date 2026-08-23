"""ToolExecutor 测试

覆盖：
  - text2img 基本流程：gateway 返回字节 → 上传 OSS → 返回签名 URL
  - img2img 带参考图：下载参考图后传给 gateway
  - 上传失败时跳过该张图
  - 无 URL 的 reference / mask 不触发下载
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.image_gen.tool_executor import ToolExecutor


def _make_tool_call(**overrides) -> dict:
    """构造 generate_image tool_call"""
    args = {
        "operation": "text2img",
        "prompt": "a cat",
        "size": "1024x1024",
        "n": 1,
    }
    args.update(overrides)
    return {"id": "call_1", "name": "generate_image", "arguments": args}


@pytest.mark.asyncio
async def test_execute_text2img():
    """text2img：gateway 返回 1 张图 → 上传 OSS → 返回 1 个签名 URL"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=[b"fake_image_bytes"])

    oss = MagicMock()
    oss.upload_file = MagicMock(return_value="https://oss/raw-url")
    oss.sign_url = MagicMock(return_value="https://oss/signed")

    executor = ToolExecutor(gateway=gateway, oss_svc=oss)
    result = await executor.execute(_make_tool_call())

    assert result["image_urls"] == ["https://oss/signed"]
    assert result["tool_call_id"] == "call_1"
    oss.upload_file.assert_called_once()
    oss.sign_url.assert_called_once()
    # 验证 sign_url 参数：method=GET, expires=SIGNED_URL_EXPIRES_RESULT
    call_args = oss.sign_url.call_args
    assert call_args[0][0] == "GET"
    assert call_args[0][2] == 3600  # SIGNED_URL_EXPIRES_RESULT


@pytest.mark.asyncio
async def test_execute_with_reference():
    """img2img 带参考图 URL：应先下载再传给 gateway"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=[b"fake"])

    oss = MagicMock()
    oss.upload_file = MagicMock(return_value="https://oss/raw-url")
    oss.sign_url = MagicMock(return_value="https://oss/signed")

    executor = ToolExecutor(gateway=gateway, oss_svc=oss)

    # mock httpx 下载
    mock_resp = MagicMock()
    mock_resp.content = b"ref_image_data"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await executor.execute(_make_tool_call(
            operation="img2img",
            prompt="改成水彩",
            reference_image_url="https://oss/ref.png",
        ))

    assert result["image_urls"] == ["https://oss/signed"]
    # 验证 gateway 收到了参考图字节
    call_kwargs = gateway.generate.call_args[1]
    assert call_kwargs["reference_image"] == b"ref_image_data"
    assert call_kwargs["operation"] == "img2img"


@pytest.mark.asyncio
async def test_execute_upload_failure_skips_image():
    """OSS 上传失败时该张图被跳过，不出现在 image_urls 中"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=[b"img1", b"img2"])

    oss = MagicMock()
    # 第一次上传成功，第二次失败
    oss.upload_file = MagicMock(side_effect=["https://oss/raw-1", None])
    oss.sign_url = MagicMock(return_value="https://oss/signed-1")

    executor = ToolExecutor(gateway=gateway, oss_svc=oss)
    result = await executor.execute(_make_tool_call(n=2))

    assert len(result["image_urls"]) == 1
    assert result["image_urls"][0] == "https://oss/signed-1"


@pytest.mark.asyncio
async def test_execute_no_reference_no_download():
    """没有 reference_image_url 时不触发下载"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=[b"fake"])

    oss = MagicMock()
    oss.upload_file = MagicMock(return_value="https://oss/raw-url")
    oss.sign_url = MagicMock(return_value="https://oss/signed")

    executor = ToolExecutor(gateway=gateway, oss_svc=oss)

    # 不 patch httpx，如果有下载调用会真正发起（可能超时或报错）
    result = await executor.execute(_make_tool_call())
    assert result["image_urls"] == ["https://oss/signed"]
    # 验证 gateway 的 reference_image 和 mask_image 均为 None
    call_kwargs = gateway.generate.call_args[1]
    assert call_kwargs["reference_image"] is None
    assert call_kwargs["mask_image"] is None
