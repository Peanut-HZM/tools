"""通义万相 Provider 测试

使用 mock httpx 验证：
1. text2img 请求构造正确
2. 成功响应解析正确
3. retryable 错误（5xx/timeout）正确标记
4. fatal 错误（401/参数错误）正确标记
5. validate_config 检查 api_key
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import ImageGenError, ImageGenParams
from app.services.harness.image_provider.tongyi import TongyiWanxiangProvider


@pytest.fixture
def provider():
    return TongyiWanxiangProvider(
        base_url="https://dashscope.aliyuncs.com/api/v1",
        api_key="test-api-key",
        oss_client=MagicMock(),
    )


class TestTongyiWanxiangProvider:
    @pytest.mark.asyncio
    async def test_text2img_success(self, provider):
        """text2img 成功场景"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": {
                "task_id": "task-123",
                "results": [{"url": "https://oss.example.com/generated.png"}]
            },
            "usage": {"image_count": 1}
        }

        # mock 轮询响应
        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {
            "output": {
                "task_status": "SUCCEEDED",
                "results": [{"url": "https://oss.example.com/generated.png"}]
            }
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(provider, "_http_get", new_callable=AsyncMock, return_value=poll_response):
                with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img.png"):
                    params = ImageGenParams(size="1024x1024", n=1, model_name="wanx-v1")
                    result = await provider.text2img("一只猫", params)

        assert result.image_urls == ["https://my-oss.com/img.png"]
        assert result.model_used == "wanx-v1"

    @pytest.mark.asyncio
    async def test_text2img_timeout_is_retryable(self, provider):
        """超时错误标记为 retryable"""
        import httpx
        with patch.object(provider, "_http_post", new_callable=AsyncMock, side_effect=httpx.ReadTimeout("timeout")):
            params = ImageGenParams(model_name="wanx-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_text2img_401_is_fatal(self, provider):
        """401 鉴权错误标记为 fatal"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="wanx-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_text2img_500_is_retryable(self, provider):
        """500 服务端错误标记为 retryable"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="wanx-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is True

    def test_validate_config_with_api_key(self, provider):
        """有 api_key 时 validate_config 通过"""
        provider.validate_config()  # 不抛异常

    def test_validate_config_without_api_key(self):
        """无 api_key 时 validate_config 抛异常"""
        p = TongyiWanxiangProvider(base_url="http://x", api_key="", oss_client=None)
        with pytest.raises(ImageGenError, match="api_key"):
            p.validate_config()

    def test_registered_as_qwen_image(self):
        """Provider 注册为 qwen_image"""
        from app.services.harness.image_provider.registry import _PROVIDER_MAP
        # 触发导入
        from app.services.harness.image_provider import tongyi  # noqa: F401
        assert "qwen_image" in _PROVIDER_MAP
        assert _PROVIDER_MAP["qwen_image"] is TongyiWanxiangProvider
