"""Prompt 润色 helper 测试

验证：
1. 正常润色（中文 → 英文）
2. LLM 不可用时降级返回原始 prompt
3. LLM 超时时降级返回原始 prompt
4. 空 prompt 返回空字符串
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.harness.tools.prompt_refiner import refine_image_prompt
from app.services.harness.tool_protocol import ToolContext


def _make_ctx(llm_gateway=None):
    return ToolContext(
        user_id="user-1",
        conversation_id="conv-1",
        agent_id="agent-1",
        llm_gateway=llm_gateway,
    )


class TestRefineImagePrompt:
    @pytest.mark.asyncio
    async def test_normal_refinement(self):
        """LLM 正常返回英文 prompt"""
        mock_gateway = AsyncMock()
        mock_gateway.generate.return_value = {
            "content": "a beautiful cat sitting on a wooden table, high quality, detailed",
            "usage": {"total_tokens": 50},
        }

        ctx = _make_ctx(llm_gateway=mock_gateway)
        result = await refine_image_prompt("一只漂亮的猫坐在桌子上", ctx)

        assert "cat" in result
        assert len(result) > 0
        mock_gateway.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_empty(self):
        """空 prompt 返回空字符串"""
        ctx = _make_ctx()
        result = await refine_image_prompt("", ctx)
        assert result == ""

    @pytest.mark.asyncio
    async def test_whitespace_prompt_returns_empty(self):
        """纯空白 prompt 返回空字符串"""
        ctx = _make_ctx()
        result = await refine_image_prompt("   ", ctx)
        assert result == ""

    @pytest.mark.asyncio
    async def test_llm_unavailable_fallback(self):
        """LLM 不可用时返回原始 prompt"""
        mock_gateway = AsyncMock()
        mock_gateway.generate.side_effect = Exception("LLM service unavailable")

        ctx = _make_ctx(llm_gateway=mock_gateway)
        original = "一只漂亮的猫"
        result = await refine_image_prompt(original, ctx)

        assert result == original

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self):
        """LLM 超时时返回原始 prompt"""
        import asyncio
        mock_gateway = AsyncMock()
        mock_gateway.generate.side_effect = asyncio.TimeoutError()

        ctx = _make_ctx(llm_gateway=mock_gateway)
        original = "日落风景"
        result = await refine_image_prompt(original, ctx)

        assert result == original

    @pytest.mark.asyncio
    async def test_no_gateway_fallback(self):
        """ctx.llm_gateway 为 None 时返回原始 prompt"""
        ctx = _make_ctx(llm_gateway=None)
        original = "一只狗"
        result = await refine_image_prompt(original, ctx)
        assert result == original

    @pytest.mark.asyncio
    async def test_already_english_passthrough(self):
        """已经是英文的 prompt 直接返回（不调 LLM）"""
        mock_gateway = AsyncMock()
        ctx = _make_ctx(llm_gateway=mock_gateway)

        result = await refine_image_prompt("a beautiful sunset over the ocean", ctx)

        assert result == "a beautiful sunset over the ocean"
        mock_gateway.generate.assert_not_called()
