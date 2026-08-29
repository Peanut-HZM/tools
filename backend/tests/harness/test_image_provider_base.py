"""ImageModelProvider 抽象接口 + 数据结构测试"""
import pytest
from app.services.harness.image_provider.base import (
    ImageGenParams,
    ImageGenResult,
    ImageGenError,
    ImageModelProvider,
)


class TestImageGenParams:
    def test_defaults(self):
        p = ImageGenParams()
        assert p.size == "1024x1024"
        assert p.n == 1
        assert p.style is None
        assert p.model_name == ""
        assert p.request_params == {}

    def test_custom_values(self):
        p = ImageGenParams(size="512x512", n=4, style="anime", model_name="wanx-v1")
        assert p.size == "512x512"
        assert p.n == 4
        assert p.style == "anime"
        assert p.model_name == "wanx-v1"


class TestImageGenResult:
    def test_fields(self):
        r = ImageGenResult(
            image_urls=["https://oss.example.com/img1.png"],
            model_used="wanx-v1",
            revised_prompt="a cat sitting on a mat",
            elapsed_seconds=3.5,
        )
        assert len(r.image_urls) == 1
        assert r.model_used == "wanx-v1"
        assert r.revised_prompt == "a cat sitting on a mat"
        assert r.elapsed_seconds == 3.5

    def test_defaults(self):
        r = ImageGenResult(image_urls=["url"], model_used="m")
        assert r.revised_prompt == ""
        assert r.elapsed_seconds == 0.0


class TestImageGenError:
    def test_retryable(self):
        e = ImageGenError("timeout", retryable=True)
        assert e.retryable is True
        assert str(e) == "timeout"

    def test_fatal(self):
        e = ImageGenError("invalid api key", retryable=False)
        assert e.retryable is False


class TestImageModelProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ImageModelProvider(base_url="http://x", api_key="k")

    def test_concrete_subclass(self):
        class MockProvider(ImageModelProvider):
            async def text2img(self, prompt, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            async def img2img(self, prompt, reference_image, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            async def inpaint(self, prompt, image_url, mask_url, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            async def upload_edit(self, image_url, instruction, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            def validate_config(self):
                pass

        p = MockProvider(base_url="http://x", api_key="k")
        assert p.base_url == "http://x"
        assert p.api_key == "k"
