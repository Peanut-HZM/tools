"""image_gen 端到端集成测试

使用 mock provider + mock gateway 验证完整流程：
用户 prompt → prompt 润色 → provider 调用 → 结果组装 → 事件发送

覆盖场景：
1. 完整 text2img 流程（prompt 润色 + provider 调用 + 事件发送）
2. fallback 链：primary 抛 retryable ImageGenError，secondary 成功
3. prompt 润色失败时降级到原始 prompt，provider 仍被调用
"""
import socket
import ipaddress
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.tools.image_gen import ImageGenTool
from app.services.harness.image_provider.base import ImageGenResult
from app.services.harness.tool_protocol import ToolContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_dns(monkeypatch):
    """全局 mock socket.getaddrinfo，避免测试触发真实 DNS 查询。

    - 已知测试 hostname（如 example.com / oss.example.com）解析为公网 IP
    - hostname 含 'private' 时解析为内网 IP 10.0.0.1（触发 SSRF 拦截）
    - 其它 hostname 一律解析失败，对应 SSRF 防护中"保守拒绝"的语义
    """
    _PUBLIC_IP_TABLE = {
        "example.com": "93.184.216.34",
        "oss.example.com": "93.184.216.34",
    }

    def _fake_getaddrinfo(host, port=None, *args, **kwargs):
        try:
            ip = ipaddress.ip_address(host)
            family = socket.AF_INET6 if ip.version == 6 else socket.AF_INET
            return [(family, socket.SOCK_STREAM, 6, "", (host, 0))]
        except ValueError:
            pass
        if "private" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0))]
        if host in _PUBLIC_IP_TABLE:
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (_PUBLIC_IP_TABLE[host], 0))
            ]
        raise socket.gaierror("mocked: no entry for %s" % host)

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


@pytest.fixture
def mock_ctx():
    """构造满足 image_gen execute 所需的最小 ToolContext mock"""
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-1"
    ctx.conversation_id = "conv-1"
    ctx.agent_id = "agent-1"
    ctx.agent = MagicMock(
        default_model_id="model-uuid-1",
        fallback_model_ids=["model-uuid-2"],
    )
    ctx.event_emitter = AsyncMock()
    # LLM gateway：默认返回 dict 格式，_extract_content 会取 "content"
    ctx.llm_gateway = AsyncMock()
    ctx.llm_gateway.generate.return_value = {
        "content": "a beautiful cat on a table, high quality",
        "usage": {"total_tokens": 30},
    }
    ctx.db = MagicMock()
    ctx.oss_service = MagicMock()
    # execute 内部会检查 cancel_event，mock 为不取消
    ctx.cancel_event = MagicMock()
    ctx.cancel_event.is_set.return_value = False
    return ctx


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------

class TestImageGenIntegration:
    """image_gen 端到端集成测试"""

    @pytest.mark.asyncio
    async def test_full_text2img_flow(self, mock_ctx):
        """完整 text2img 流程：prompt 润色 → provider 调用 → 结果组装 → 事件发送"""
        tool = ImageGenTool()

        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/cat.png"],
            model_used="wanx-v1",
            revised_prompt="a beautiful cat on a table, high quality",
            elapsed_seconds=3.0,
        )

        # mock refine_image_prompt 避免 asyncio.wait_for 计时不确定性
        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]), \
             patch("app.services.harness.tools.image_gen.refine_image_prompt",
                   new_callable=lambda: _async_return("a beautiful cat on a table, high quality")):
            result = await tool.execute(
                {"operation": "text2img", "prompt": "一只漂亮的猫坐在桌子上", "size": "1024x1024", "n": 1},
                mock_ctx,
            )

        # 验证工具结果
        assert result.success is True
        assert len(result.attachments) == 1
        assert result.attachments[0].type == "image"
        assert result.attachments[0].url == "https://oss.example.com/cat.png"
        assert result.metadata["model_used"] == "wanx-v1"
        assert result.content["image_count"] == 1

        # 验证 prompt 润色被调用（中文 prompt 需要润色）
        import app.services.harness.tools.image_gen as image_gen_mod
        # refine_image_prompt 被 patch，直接验证 provider 收到了润色后的 prompt
        mock_provider.text2img.assert_called_once()
        call_args = mock_provider.text2img.call_args
        assert call_args[0][0] == "a beautiful cat on a table, high quality"

        # 验证 image_generated 事件被发送
        mock_ctx.event_emitter.assert_called_once()
        event = mock_ctx.event_emitter.call_args[0][0]
        assert event.type == "image_generated"
        assert "https://oss.example.com/cat.png" in event.payload["urls"]

    @pytest.mark.asyncio
    async def test_full_flow_with_fallback(self, mock_ctx):
        """fallback 链：primary 抛 retryable ImageGenError，secondary 成功"""
        from app.services.harness.image_provider.base import ImageGenError

        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("rate limit exceeded", retryable=True)

        secondary = AsyncMock()
        secondary.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/cat-fallback.png"],
            model_used="hailuo-v1",
        )

        with patch.object(tool, "_resolve_provider_chain",
                          return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)]), \
             patch("app.services.harness.tools.image_gen.refine_image_prompt",
                   new_callable=lambda: _async_return("a cat")):
            result = await tool.execute(
                {"operation": "text2img", "prompt": "一只猫"},
                mock_ctx,
            )

        # fallback 成功：使用 secondary 的结果
        assert result.success is True
        assert result.metadata["model_used"] == "hailuo-v1"
        assert result.attachments[0].url == "https://oss.example.com/cat-fallback.png"

        # primary 被调用一次并失败，secondary 被调用一次并成功
        primary.text2img.assert_called_once()
        secondary.text2img.assert_called_once()

    @pytest.mark.asyncio
    async def test_prompt_refine_degrades_gracefully(self, mock_ctx):
        """prompt 润色失败时降级到原始 prompt，provider 仍被调用

        实际 graceful degradation 发生在 refine_image_prompt 内部：
        它捕获所有异常后返回原始 prompt。此处模拟该行为：函数返回原始 prompt。
        """
        tool = ImageGenTool()

        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/cat.png"],
            model_used="wanx-v1",
        )

        original_prompt = "一只猫"

        # refine_image_prompt 降级行为：返回原始 prompt（模拟 LLM 不可用时的内部 catch）
        async def _refine_returns_original(prompt, ctx):
            return prompt  # 与真实函数降级行为一致

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]), \
             patch("app.services.harness.tools.image_gen.refine_image_prompt",
                   side_effect=_refine_returns_original):
            result = await tool.execute(
                {"operation": "text2img", "prompt": original_prompt},
                mock_ctx,
            )

        # 即使 prompt 润色降级，provider 仍被调用且流程正常完成
        assert result.success is True
        mock_provider.text2img.assert_called_once()

        # provider 收到的是原始 prompt（润色降级后的结果）
        call_args = mock_provider.text2img.call_args
        assert call_args[0][0] == original_prompt


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _async_return(value):
    """返回一个 AsyncMock，调用时始终返回 value"""
    m = AsyncMock()
    m.return_value = value
    return m
