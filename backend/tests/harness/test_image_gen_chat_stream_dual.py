"""_run_image_gen_with_shadow 单元测试（Phase2-Plan3 Task 3）

覆盖 2 个场景：
1. dual 模式下调用 DifyImageGenExecutor 并返回结构化结果
2. 非 dual 模式（dify）下直接返回 skipped，不调用任何 executor
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_shadow_invokes_dify_executor_in_dual_mode():
    """dual 模式：应调用 DifyImageGenExecutor.execute 并返回其结果"""
    from app.api.routes.chat_stream import _run_image_gen_with_shadow

    fake_result = {
        "success": True,
        "image_urls": ["https://example.com/img.png"],
        "backend": "dify",
    }
    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(return_value=fake_result)

    with patch(
        "app.api.routes.chat_stream.settings"
    ) as mock_settings, patch(
        "app.services.harness.image_gen_backend.executors.DifyImageGenExecutor",
        return_value=mock_executor,
    ) as mock_cls:
        mock_settings.IMAGE_GEN_BACKEND = "dual"
        args = {"prompt": "一只猫"}
        ctx = {"user_id": "u1"}

        result = await _run_image_gen_with_shadow(args, ctx)

    mock_cls.assert_called_once()
    mock_executor.execute.assert_awaited_once_with(args, ctx)
    assert result == fake_result


@pytest.mark.asyncio
async def test_shadow_skips_when_not_dual_mode():
    """非 dual 模式（如 dify）：应直接返回 skipped，不调用任何 executor"""
    from app.api.routes.chat_stream import _run_image_gen_with_shadow

    with patch(
        "app.api.routes.chat_stream.settings"
    ) as mock_settings:
        mock_settings.IMAGE_GEN_BACKEND = "dify"
        result = await _run_image_gen_with_shadow({"prompt": "x"}, {})

    assert result == {"skipped": True, "reason": "not dual mode"}


@pytest.mark.asyncio
async def test_shadow_returns_structured_dict_on_executor_exception():
    """executor 抛异常：应捕获异常、脱敏日志，并返回结构化错误 dict"""
    from app.api.routes.chat_stream import _run_image_gen_with_shadow

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(side_effect=RuntimeError("secret db error"))

    with patch(
        "app.api.routes.chat_stream.settings"
    ) as mock_settings, patch(
        "app.services.harness.image_gen_backend.executors.DifyImageGenExecutor",
        return_value=mock_executor,
    ):
        mock_settings.IMAGE_GEN_BACKEND = "dual"
        result = await _run_image_gen_with_shadow({"prompt": "x"}, {})

    assert result["success"] is False
    assert result["error"] == "shadow_failed"
    assert result["backend"] == "dify"
