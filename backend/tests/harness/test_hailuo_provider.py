"""海螺 AI (MiniMax) Provider 测试

使用 mock 验证：
1. text2img/img2img/inpaint/upload_edit 请求构造正确
2. 成功响应解析正确
3. retryable 错误（5xx/timeout）正确标记
4. fatal 错误（401/参数错误）正确标记
5. validate_config 检查 api_key
6. provider 注册为 minimax_image
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import ImageGenError, ImageGenParams
from app.services.harness.image_provider.hailuo import HailuoProvider


@pytest.fixture
def provider():
    return HailuoProvider(
        base_url="https://api.minimax.chat/v1",
        api_key="test-hailuo-key",
        oss_client=MagicMock(),
    )


class TestHailuoProvider:
    # ----- text2img -----

    @pytest.mark.asyncio
    async def test_text2img_success(self, provider):
        """text2img 成功场景：请求构造 + 响应解析"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "image_urls": ["https://cdn.minimax.com/generated.png"],
                "model": "hailuo-v1",
            }
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="hailuo-v1")
                result = await provider.text2img("一只猫", params)

        # 验证请求 URL 正确
        mock_post.assert_awaited_once()
        call_url = mock_post.call_args[0][0]
        assert call_url.endswith("/image/generation")

        # 验证请求体
        call_body = mock_post.call_args[1]["json"]
        assert call_body["model"] == "hailuo-v1"
        assert call_body["prompt"] == "一只猫"
        assert call_body["size"] == "1024x1024"
        assert call_body["n"] == 1

        # 验证结果
        assert result.image_urls == ["https://my-oss.com/img.png"]
        assert result.model_used == "hailuo-v1"

    @pytest.mark.asyncio
    async def test_text2img_with_style(self, provider):
        """text2img 带 style 参数"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"image_urls": ["https://cdn.minimax.com/img.png"]}
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img.png"):
                params = ImageGenParams(size="1024x1024", n=1, style="anime", model_name="hailuo-v1")
                await provider.text2img("一只猫", params)

        call_body = mock_post.call_args[1]["json"]
        assert call_body["style"] == "anime"

    @pytest.mark.asyncio
    async def test_text2img_timeout_is_retryable(self, provider):
        """超时错误标记为 retryable"""
        import httpx
        with patch.object(provider, "_http_post", new_callable=AsyncMock, side_effect=httpx.ReadTimeout("timeout")):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is True
            # 精确断言：异常消息不应泄露原始异常细节
            assert str(exc_info.value) == "MiniMax 请求超时"

    # ----- img2img -----

    @pytest.mark.asyncio
    async def test_img2img_success(self, provider):
        """img2img 成功场景"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"image_urls": ["https://cdn.minimax.com/img2img.png"]}
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img2img.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="hailuo-v1")
                result = await provider.img2img("变成油画风格", "https://oss.example.com/ref.png", params)

        call_url = mock_post.call_args[0][0]
        assert call_url.endswith("/image/img2img")
        call_body = mock_post.call_args[1]["json"]
        assert call_body["reference_image"] == "https://oss.example.com/ref.png"
        assert result.image_urls == ["https://my-oss.com/img2img.png"]

    # ----- inpaint -----

    @pytest.mark.asyncio
    async def test_inpaint_success(self, provider):
        """inpaint 成功场景"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"image_urls": ["https://cdn.minimax.com/inpaint.png"]}
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/inpaint.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="hailuo-v1")
                result = await provider.inpaint(
                    "添加一只帽子",
                    "https://oss.example.com/img.png",
                    "https://oss.example.com/mask.png",
                    params,
                )

        call_url = mock_post.call_args[0][0]
        assert call_url.endswith("/image/inpaint")
        call_body = mock_post.call_args[1]["json"]
        assert call_body["image_url"] == "https://oss.example.com/img.png"
        assert call_body["mask_url"] == "https://oss.example.com/mask.png"
        assert result.image_urls == ["https://my-oss.com/inpaint.png"]

    # ----- upload_edit -----

    @pytest.mark.asyncio
    async def test_upload_edit_success(self, provider):
        """upload_edit 成功场景"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"image_urls": ["https://cdn.minimax.com/edit.png"]}
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/edit.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="hailuo-v1")
                result = await provider.upload_edit(
                    "https://oss.example.com/img.png",
                    "把背景换成海滩",
                    params,
                )

        call_url = mock_post.call_args[0][0]
        assert call_url.endswith("/image/edit")
        call_body = mock_post.call_args[1]["json"]
        assert call_body["image_url"] == "https://oss.example.com/img.png"
        assert call_body["prompt"] == "把背景换成海滩"
        assert result.image_urls == ["https://my-oss.com/edit.png"]

    # ----- 错误处理 -----

    @pytest.mark.asyncio
    async def test_401_is_fatal(self, provider):
        """401 鉴权错误标记为 fatal"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is False
            # 异常消息中只包含 status_code，不泄露响应体
            assert "Unauthorized" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_500_is_retryable(self, provider):
        """500 服务端错误标记为 retryable"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("test", params)
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_429_is_retryable(self, provider):
        """429 限流错误标记为 retryable"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("test", params)
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_no_image_urls_raises(self, provider):
        """API 返回空 image_urls 时抛出 retryable 错误"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"image_urls": []}}

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError, match="未返回图片 URL"):
                await provider.text2img("test", params)

    # ----- validate_config -----

    def test_validate_config_with_key(self, provider):
        """有 api_key 时 validate_config 通过"""
        provider.validate_config()

    def test_validate_config_without_key(self):
        """无 api_key 时 validate_config 抛异常"""
        p = HailuoProvider(base_url="http://x", api_key="", oss_client=None)
        with pytest.raises(ImageGenError, match="api_key"):
            p.validate_config()

    # ----- 注册 -----

    def test_registered_as_minimax_image(self):
        """Provider 注册为 minimax_image"""
        from app.services.harness.image_provider.registry import _PROVIDER_MAP
        from app.services.harness.image_provider import hailuo  # noqa: F401
        assert "minimax_image" in _PROVIDER_MAP
        assert _PROVIDER_MAP["minimax_image"] is HailuoProvider
