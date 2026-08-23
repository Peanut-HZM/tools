"""SelfDevelopedBackend 测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.image_gen.base import BackendContext
from app.services.image_gen.selfdev_backend import SelfDevelopedBackend


@pytest.mark.asyncio
async def test_new_conversation_returns_id():
    """首次对话：conversation_id=None → 生成新 UUID 返回"""
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value=("你好", []))

    executor = MagicMock()
    conv_repo = MagicMock()
    conv_repo.save = AsyncMock()
    conv_repo.load = AsyncMock(return_value=[])

    backend = SelfDevelopedBackend(
        orchestrator=orchestrator,
        executor=executor,
        conv_repo=conv_repo,
    )

    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="画一只猫",
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
    result = await backend.run(ctx)

    assert result.backend == "selfdev"
    assert result.conversation_id != ""  # 已生成
    conv_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_with_tool_call_generates_images():
    """brain 决定生成 → tool_call 执行 → 返回 image_urls"""
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value=(
        "图已生成",
        [{"image_urls": ["https://oss/1.png"], "tool_call_id": "call_1"}],
    ))

    executor = MagicMock()
    conv_repo = MagicMock()
    conv_repo.save = AsyncMock()
    conv_repo.load = AsyncMock(return_value=[])

    backend = SelfDevelopedBackend(
        orchestrator=orchestrator,
        executor=executor,
        conv_repo=conv_repo,
    )

    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="画一只猫",
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
    result = await backend.run(ctx)

    assert result.image_urls == ["https://oss/1.png"]
    assert result.answer_text == "图已生成"
