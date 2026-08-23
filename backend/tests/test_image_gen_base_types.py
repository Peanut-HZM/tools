# backend/tests/test_image_gen_base_types.py
"""IImageGenerationBackend 接口测试"""

import uuid

import pytest

from app.services.image_gen.base import BackendContext, BackendResult, IImageGenerationBackend


def test_backend_context_required_fields():
    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        reference_mime=None,
        mask_image=None,
        mask_mime=None,
        size="1024x1024",
        n=1,
        strength=None,
        edit_type=None,
    )
    assert ctx.operation == "text2img"


def test_backend_result_required_fields():
    r = BackendResult(
        image_urls=["https://oss/1.png"],
        answer_text="done",
        conversation_id="cid",
        model_used="gpt-4",
        backend="selfdev",
    )
    assert r.image_urls


@pytest.mark.asyncio
async def test_interface_is_abstract():
    """不能直接实例化抽象类"""
    with pytest.raises(TypeError):
        IImageGenerationBackend()
