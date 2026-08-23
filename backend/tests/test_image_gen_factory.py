"""ImageGenFactory 测试"""

import pytest

from app.services.llm.exceptions import UnknownProviderError
from app.services.llm.image_gen_base import ImageGenAdapter
from app.services.llm.image_gen_factory import ImageGenFactory


def test_get_unknown_provider_raises():
    with pytest.raises(UnknownProviderError):
        ImageGenFactory.get("unknown_type", api_key="x", base_url=None, model_name="m")


def test_get_doubao_seedream():
    a = ImageGenFactory.get(
        "doubao_seedream", api_key="x", base_url="https://ark.cn-beijing.volces.com", model_name="doubao-seedream-3-0-t2i-250415"
    )
    assert isinstance(a, ImageGenAdapter)


def test_get_qwen_image():
    a = ImageGenFactory.get(
        "qwen_image", api_key="x", base_url="https://dashscope.aliyuncs.com", model_name="wanxiang-v1"
    )
    assert isinstance(a, ImageGenAdapter)


def test_get_hailuo():
    a = ImageGenFactory.get("hailuo", api_key="x", base_url=None, model_name="hailuo-t2i")
    assert isinstance(a, ImageGenAdapter)


def test_get_openai_image():
    a = ImageGenFactory.get("openai_image", api_key="x", base_url="https://api.openai.com", model_name="dall-e-3")
    assert isinstance(a, ImageGenAdapter)
