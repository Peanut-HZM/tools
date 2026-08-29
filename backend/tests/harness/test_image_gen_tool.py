"""image_gen BuiltinTool 测试

覆盖：
1. 工具 metadata（name / display_name / parameters_schema）
2. text2img 成功路径（含 attachments 组装）
3. img2img 缺少 reference_image_url 返回错误
4. inpaint 缺少 mask_url 返回错误
5. 无效 operation 返回错误
6. fallback 链：主 provider retryable 失败 → 切到备选
7. fallback 链：全部失败 → 返回 ToolResult.error
8. fatal 错误不触发 fallback
9. 空 prompt 返回错误
10. 成功时 emit image_generated 事件

另含补充用例：upload_edit 正常路径、危险 URL 拒绝、空 provider 链、
参数归一化、prompt 润色降级、_resolve_provider_chain 过滤逻辑。
"""
import socket
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenResult,
)
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.image_gen import ImageGenTool, _is_safe_http_url


@pytest.fixture(autouse=True)
def _patch_dns(monkeypatch):
    """全局 mock socket.getaddrinfo，避免测试触发真实 DNS 查询。

    - IP 字面量直接原样返回，交给黑名单判定
    - 已知测试 hostname（如 example.com / oss.example.com）解析为公网 IP
    - hostname 含 'private' 时解析为内网 IP 10.0.0.1
    - 其它 hostname 一律解析失败，对应 SSRF 防护中"保守拒绝"的语义
    """
    import ipaddress

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


def _make_ctx(agent=None, event_emitter=None, llm_gateway=None, db=None):
    """构造测试用 ToolContext（MagicMock 版）"""
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-1"
    ctx.conversation_id = "conv-1"
    ctx.agent_id = "agent-1"
    ctx.agent = agent or MagicMock(
        default_model_id="model-uuid-1",
        fallback_model_ids=["model-uuid-2"],
    )
    ctx.event_emitter = event_emitter
    ctx.llm_gateway = llm_gateway
    ctx.db = db if db is not None else MagicMock()
    ctx.oss_service = MagicMock()
    return ctx


def _patch_refine(value="a cat"):
    """patch prompt 润色，避免测试依赖 LLM"""
    return patch(
        "app.services.harness.tools.image_gen.refine_image_prompt",
        new_callable=AsyncMock,
        return_value=value,
    )


class TestImageGenTool:
    # ---- 1. 工具 metadata ----

    def test_tool_metadata(self):
        """工具基础元信息符合约定"""
        tool = ImageGenTool()
        assert tool.name == "image_gen"
        assert tool.display_name == "图像生成"

        props = tool.parameters_schema.get("properties", {})
        assert "operation" in props
        assert props["operation"]["enum"] == [
            "text2img",
            "img2img",
            "inpaint",
            "upload_edit",
        ]
        assert "prompt" in props
        assert tool.parameters_schema.get("required") == ["operation", "prompt"]

        # to_function_schema 可直接给 LLM 使用
        schema = tool.to_function_schema()
        assert schema["name"] == "image_gen"
        assert "operation" in schema["parameters"]["properties"]

    # ---- 2. text2img 成功路径 ----

    @pytest.mark.asyncio
    async def test_text2img_success(self):
        """text2img 成功返回 attachments + content"""
        tool = ImageGenTool()
        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
            elapsed_seconds=2.5,
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is True
        assert result.content_type == "json"
        assert len(result.attachments) == 1
        assert result.attachments[0].type == "image"
        assert result.attachments[0].url == "https://oss.example.com/img.png"
        assert result.attachments[0].mime_type == "image/png"
        assert result.content["operation"] == "text2img"
        assert result.content["image_count"] == 1
        assert result.metadata["model_used"] == "wanx-v1"
        assert result.metadata["elapsed_seconds"] == 2.5

        # provider 收到润色后的 prompt 与归一化参数
        called_prompt, called_params = mock_provider.text2img.call_args[0]
        assert called_prompt == "a cat"
        assert called_params.model_name == "wanx-v1"
        assert called_params.size == "1024x1024"
        assert called_params.n == 1

    # ---- 3. img2img 缺少 reference_image_url ----

    @pytest.mark.asyncio
    async def test_img2img_missing_reference_returns_error(self):
        """img2img 未提供 reference_image_url 时报错"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "img2img", "prompt": "修改这张图"},
            ctx,
        )
        assert result.success is False
        assert "reference_image_url" in (result.error_message or "")

    # ---- 4. inpaint 缺少 mask_url ----

    @pytest.mark.asyncio
    async def test_inpaint_missing_mask_returns_error(self):
        """inpaint 未提供 mask_url 时报错"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {
                "operation": "inpaint",
                "prompt": "修改区域",
                "image_url": "https://example.com/img.png",
            },
            ctx,
        )
        assert result.success is False
        assert "mask_url" in (result.error_message or "")

    # ---- 5. 无效 operation ----

    @pytest.mark.asyncio
    async def test_invalid_operation_returns_error(self):
        """未知 operation 返回错误且不触碰 provider"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        with patch.object(tool, "_resolve_provider_chain") as chain:
            result = await tool.execute(
                {"operation": "invalid_op", "prompt": "test"},
                ctx,
            )
        assert result.success is False
        assert "invalid_op" in (result.error_message or "")
        chain.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_operation_returns_error(self):
        """缺失 operation 返回错误"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute({"prompt": "test"}, ctx)
        assert result.success is False
        assert "无效操作" in (result.error_message or "")

    # ---- 6. fallback：retryable 错误切换到备选 ----

    @pytest.mark.asyncio
    async def test_fallback_on_retryable_error(self):
        """主 provider retryable 失败 → 切到备选 provider"""
        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("timeout", retryable=True)

        secondary = AsyncMock()
        secondary.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/fallback.png"],
            model_used="hailuo-v1",
        )

        ctx = _make_ctx()

        with patch.object(
            tool,
            "_resolve_provider_chain",
            return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)],
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is True
        assert result.metadata.get("model_used") == "hailuo-v1"
        assert result.attachments[0].url == "https://oss.example.com/fallback.png"
        primary.text2img.assert_called_once()
        secondary.text2img.assert_called_once()

    # ---- 7. 全部 provider 失败 ----

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_error(self):
        """所有 provider 失败 → ToolResult.error"""
        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("timeout", retryable=True)
        secondary = AsyncMock()
        secondary.text2img.side_effect = ImageGenError("auth failed", retryable=False)

        ctx = _make_ctx()

        with patch.object(
            tool,
            "_resolve_provider_chain",
            return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)],
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        assert "所有图像模型均不可用" in (result.error_message or "")
        primary.text2img.assert_called_once()
        secondary.text2img.assert_called_once()

    @pytest.mark.asyncio
    async def test_unexpected_exception_message_is_sanitized(self):
        """非 ImageGenError 异常不把内部细节泄漏到 LLM 上下文"""
        tool = ImageGenTool()

        provider = AsyncMock()
        provider.text2img.side_effect = RuntimeError(
            "/internal/path/secret.py sk-abcdef1234567890"
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        message = result.error_message or ""
        assert "所有图像模型均不可用" in message
        assert "/internal/path" not in message
        assert "sk-abcdef" not in message

    # ---- 8. fatal 错误不触发 fallback ----

    @pytest.mark.asyncio
    async def test_fatal_error_stops_fallback(self):
        """fatal 错误不触发 fallback（直接失败）"""
        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("invalid api key", retryable=False)
        secondary = AsyncMock()

        ctx = _make_ctx()

        with patch.object(
            tool,
            "_resolve_provider_chain",
            return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)],
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        secondary.text2img.assert_not_called()

    # ---- 9. 空 prompt ----

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_error(self):
        """空 prompt 返回错误"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "text2img", "prompt": ""},
            ctx,
        )
        assert result.success is False
        assert "prompt" in (result.error_message or "").lower()

    @pytest.mark.asyncio
    async def test_whitespace_prompt_returns_error(self):
        """纯空白 prompt 返回错误"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "text2img", "prompt": "   "},
            ctx,
        )
        assert result.success is False
        assert "prompt" in (result.error_message or "").lower()

    # ---- 10. image_generated 事件 ----

    @pytest.mark.asyncio
    async def test_emits_image_generated_event(self):
        """成功时通过 event_emitter 发送 image_generated 事件"""
        tool = ImageGenTool()
        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
            elapsed_seconds=1.5,
        )

        emitter = AsyncMock()
        ctx = _make_ctx(event_emitter=emitter)

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]
        ):
            with _patch_refine():
                await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        emitter.assert_called_once()
        event = emitter.call_args[0][0]
        assert event.type == "image_generated"
        assert event.payload["urls"] == ["https://oss.example.com/img.png"]
        assert event.payload["metadata"]["model_used"] == "wanx-v1"
        assert event.payload["metadata"]["operation"] == "text2img"

    @pytest.mark.asyncio
    async def test_no_event_on_failure(self):
        """失败时不发送 image_generated 事件"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.text2img.side_effect = ImageGenError("boom", retryable=False)

        emitter = AsyncMock()
        ctx = _make_ctx(event_emitter=emitter)

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        emitter.assert_not_called()


class TestImageGenToolOperations:
    """其余操作分发 + URL 安全校验"""

    @pytest.mark.asyncio
    async def test_upload_edit_success(self):
        """upload_edit 正常路径：instruction 使用润色后 prompt"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.upload_edit.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/edited.png"],
            model_used="seedream-v1",
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("seedream-v1", provider)]
        ):
            with _patch_refine("make it brighter"):
                result = await tool.execute(
                    {
                        "operation": "upload_edit",
                        "prompt": "调亮一点",
                        "image_url": "https://example.com/src.png",
                    },
                    ctx,
                )

        assert result.success is True
        image_url, instruction, _params = provider.upload_edit.call_args[0]
        assert image_url == "https://example.com/src.png"
        assert instruction == "make it brighter"

    @pytest.mark.asyncio
    async def test_inpaint_success_passes_urls(self):
        """inpaint 正确传递 image_url / mask_url"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.inpaint.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/inpaint.png"],
            model_used="wanx-v1",
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            with _patch_refine("repaint the area"):
                result = await tool.execute(
                    {
                        "operation": "inpaint",
                        "prompt": "重绘这块",
                        "image_url": "https://example.com/src.png",
                        "mask_url": "https://example.com/mask.png",
                    },
                    ctx,
                )

        assert result.success is True
        prompt, image_url, mask_url, _params = provider.inpaint.call_args[0]
        assert prompt == "repaint the area"
        assert image_url == "https://example.com/src.png"
        assert mask_url == "https://example.com/mask.png"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_url",
        [
            "file:///etc/passwd",
            "javascript:alert(1)",
            "data:image/png;base64,AAAA",
            "http://",
        ],
    )
    async def test_unsafe_reference_url_rejected(self, bad_url):
        """危险 scheme 的入参 URL 被拒绝"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {
                "operation": "img2img",
                "prompt": "改图",
                "reference_image_url": bad_url,
            },
            ctx,
        )
        assert result.success is False
        assert "reference_image_url" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_unsafe_result_url_dropped_from_attachments(self):
        """provider 返回的危险 URL 不进入 attachments"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.text2img.return_value = ImageGenResult(
            image_urls=["javascript:alert(1)", "https://oss.example.com/ok.png"],
            model_used="wanx-v1",
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is True
        assert len(result.attachments) == 1
        assert result.attachments[0].url == "https://oss.example.com/ok.png"
        assert result.content["image_count"] == 1

    @pytest.mark.asyncio
    async def test_empty_provider_chain_returns_error(self):
        """无可用图像模型时返回错误"""
        tool = ImageGenTool()
        ctx = _make_ctx()

        with patch.object(tool, "_resolve_provider_chain", return_value=[]):
            with _patch_refine():
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        assert "无可用图像模型" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_param_normalization(self):
        """非法 size / n / style 被归一化"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            with _patch_refine():
                result = await tool.execute(
                    {
                        "operation": "text2img",
                        "prompt": "一只猫",
                        "size": "9999x9999",
                        "n": 99,
                        "style": "  anime  ",
                    },
                    ctx,
                )

        assert result.success is True
        _prompt, params = provider.text2img.call_args[0]
        assert params.size == "1024x1024"
        assert params.n == 4
        assert params.style == "anime"

    @pytest.mark.asyncio
    async def test_invalid_n_falls_back_to_one(self):
        """n 非数字时降级为 1"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
        )

        ctx = _make_ctx()

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            with _patch_refine():
                await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫", "n": "abc"},
                    ctx,
                )

        _prompt, params = provider.text2img.call_args[0]
        assert params.n == 1

    @pytest.mark.asyncio
    async def test_prompt_refine_degrades_to_original(self):
        """润色不可用（无 llm_gateway）时使用原始 prompt"""
        tool = ImageGenTool()
        provider = AsyncMock()
        provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
        )

        ctx = _make_ctx(llm_gateway=None)

        with patch.object(
            tool, "_resolve_provider_chain", return_value=[("wanx-v1", provider)]
        ):
            result = await tool.execute(
                {"operation": "text2img", "prompt": "一只猫"},
                ctx,
            )

        assert result.success is True
        called_prompt, _params = provider.text2img.call_args[0]
        assert called_prompt == "一只猫"


class TestResolveProviderChain:
    """provider 链解析逻辑"""

    @staticmethod
    def _make_model(model_name, category="image_gen", is_active=True):
        model = MagicMock()
        model.model_name = model_name
        model.category = category
        model.is_active = is_active
        model.provider = MagicMock()
        return model

    @staticmethod
    def _make_db(models_by_id):
        """构造能按 model_id 返回不同 LLMModel 的 db mock"""
        db = MagicMock()
        calls = {"ids": []}

        def _query(_model_cls):
            query = MagicMock()

            def _filter(criterion):
                # criterion 是 SQLAlchemy BinaryExpression，从右值取 model_id
                model_id = criterion.right.value
                calls["ids"].append(model_id)
                filtered = MagicMock()
                filtered.first.return_value = models_by_id.get(model_id)
                return filtered

            query.filter.side_effect = _filter
            return query

        db.query.side_effect = _query
        db.calls = calls
        return db

    def test_chain_orders_default_then_fallback(self):
        """主模型在前，fallback 依次在后"""
        tool = ImageGenTool()
        models = {
            "m1": self._make_model("wanx-v1"),
            "m2": self._make_model("hailuo-v1"),
        }
        db = self._make_db(models)
        agent = MagicMock(default_model_id="m1", fallback_model_ids=["m2"])
        ctx = _make_ctx(agent=agent, db=db)

        with patch(
            "app.services.harness.tools.image_gen.resolve_provider",
            side_effect=lambda p, oss_client=None: MagicMock(name="provider"),
        ):
            chain = tool._resolve_provider_chain(ctx)

        assert [name for name, _ in chain] == ["wanx-v1", "hailuo-v1"]

    def test_chain_filters_non_image_and_inactive(self):
        """过滤非 image_gen 分类与未启用的模型"""
        tool = ImageGenTool()
        models = {
            "m1": self._make_model("gpt-4o", category="text"),
            "m2": self._make_model("wanx-v1", is_active=False),
            "m3": self._make_model("hailuo-v1"),
        }
        db = self._make_db(models)
        agent = MagicMock(default_model_id="m1", fallback_model_ids=["m2", "m3"])
        ctx = _make_ctx(agent=agent, db=db)

        with patch(
            "app.services.harness.tools.image_gen.resolve_provider",
            side_effect=lambda p, oss_client=None: MagicMock(),
        ):
            chain = tool._resolve_provider_chain(ctx)

        assert [name for name, _ in chain] == ["hailuo-v1"]

    def test_chain_dedupes_model_ids(self):
        """主模型与 fallback 重复时只解析一次"""
        tool = ImageGenTool()
        models = {"m1": self._make_model("wanx-v1")}
        db = self._make_db(models)
        agent = MagicMock(default_model_id="m1", fallback_model_ids=["m1"])
        ctx = _make_ctx(agent=agent, db=db)

        with patch(
            "app.services.harness.tools.image_gen.resolve_provider",
            side_effect=lambda p, oss_client=None: MagicMock(),
        ):
            chain = tool._resolve_provider_chain(ctx)

        assert len(chain) == 1
        assert db.calls["ids"] == ["m1"]

    def test_chain_skips_unresolvable_provider(self):
        """resolve_provider 抛错时跳过该模型，不中断链解析"""
        tool = ImageGenTool()
        models = {
            "m1": self._make_model("wanx-v1"),
            "m2": self._make_model("hailuo-v1"),
        }
        db = self._make_db(models)
        agent = MagicMock(default_model_id="m1", fallback_model_ids=["m2"])
        ctx = _make_ctx(agent=agent, db=db)

        def _resolve(provider, oss_client=None):
            if _resolve.count == 0:
                _resolve.count += 1
                raise ImageGenError("图像 Provider 不支持: unknown")
            return MagicMock()

        _resolve.count = 0

        with patch(
            "app.services.harness.tools.image_gen.resolve_provider", side_effect=_resolve
        ):
            chain = tool._resolve_provider_chain(ctx)

        assert [name for name, _ in chain] == ["hailuo-v1"]

    def test_chain_empty_without_agent(self):
        """无 Agent 配置时返回空链"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        ctx.agent = None
        assert tool._resolve_provider_chain(ctx) == []

    def test_chain_empty_without_db(self):
        """无 DB 会话时返回空链"""
        tool = ImageGenTool()
        ctx = _make_ctx()
        ctx.db = None
        assert tool._resolve_provider_chain(ctx) == []

    def test_chain_empty_without_model_ids(self):
        """Agent 未配置任何模型时返回空链"""
        tool = ImageGenTool()
        agent = MagicMock(default_model_id=None, fallback_model_ids=[])
        ctx = _make_ctx(agent=agent)
        assert tool._resolve_provider_chain(ctx) == []


class TestUrlSsrfProtection:
    """测试 _is_safe_http_url 的 SSRF / parser-differential 防护

    DNS 由 autouse fixture mock 的 socket.getaddrinfo 提供，避免真实查询。
    """

    # ---- parser-differential: userinfo ----

    def test_url_with_userinfo_rejected(self):
        """包含 userinfo 的 URL 被拒绝（如 http://attacker@10.0.0.1/）"""
        assert _is_safe_http_url("http://attacker.com@10.0.0.1/admin") is False

    def test_url_with_password_userinfo_rejected(self):
        """包含 password 的 userinfo 也被拒绝"""
        assert _is_safe_http_url("http://user:pass@10.0.0.1/admin") is False

    # ---- SSRF: 内网 IP 直接出现 ----

    def test_url_with_loopback_ip_rejected(self):
        """127.0.0.1 等 loopback 被拒绝"""
        assert _is_safe_http_url("http://127.0.0.1/admin") is False

    def test_url_with_private_ip_rejected(self):
        """10/8 / 172.16/12 / 192.168/16 私网 IP 被拒绝"""
        assert _is_safe_http_url("http://192.168.1.1/admin") is False
        assert _is_safe_http_url("http://10.0.0.5/admin") is False
        assert _is_safe_http_url("http://172.16.0.1/admin") is False

    def test_url_with_link_local_ip_rejected(self):
        """169.254/16 link-local（如 AWS metadata）被拒绝"""
        assert (
            _is_safe_http_url("http://169.254.169.254/latest/meta-data/") is False
        )

    def test_url_with_zero_network_rejected(self):
        """0.0.0.0/8 被拒绝"""
        assert _is_safe_http_url("http://0.0.0.0/admin") is False

    def test_url_with_ipv6_loopback_rejected(self):
        """IPv6 loopback ::1 被拒绝"""
        assert _is_safe_http_url("http://[::1]/admin") is False

    # ---- SSRF: 补充黑名单覆盖 ----

    def test_url_with_cgnat_ip_rejected(self):
        """100.64.0.0/10 CGNAT 被拒绝"""
        assert _is_safe_http_url("http://100.64.1.1/admin") is False

    def test_url_with_benchmark_ip_rejected(self):
        """198.18.0.0/15 benchmark 段被拒绝"""
        assert _is_safe_http_url("http://198.18.0.1/admin") is False

    def test_url_with_multicast_ip_rejected(self):
        """224.0.0.0/4 组播被拒绝"""
        assert _is_safe_http_url("http://224.0.0.1/admin") is False

    def test_url_with_reserved_ip_rejected(self):
        """240.0.0.0/4 保留段被拒绝"""
        assert _is_safe_http_url("http://240.0.0.1/admin") is False

    def test_url_with_ipv6_link_local_rejected(self):
        """fe80::/10 IPv6 link-local 被拒绝"""
        assert _is_safe_http_url("http://[fe80::1]/admin") is False

    def test_url_with_ipv6_ula_rejected(self):
        """fc00::/7 IPv6 ULA 被拒绝"""
        assert _is_safe_http_url("http://[fd00::1]/admin") is False

    def test_url_with_ipv4_mapped_ipv6_rejected(self):
        """IPv4 映射的 IPv6 私网地址被拒绝"""
        assert _is_safe_http_url("http://[::ffff:10.0.0.1]/admin") is False

    # ---- SSRF: DNS 解析到内网 ----

    def test_hostname_resolving_to_private_ip_rejected(self):
        """hostname 解析到私网 IP 时被拒绝（防止 DNS rebinding）"""
        assert _is_safe_http_url("https://private.invalid/img.png") is False

    def test_hostname_dns_failure_rejected(self):
        """DNS 解析失败时保守拒绝"""
        assert _is_safe_http_url("https://nonexistent.example.org/img.png") is False

    # ---- 正向用例 ----

    def test_valid_url_accepted(self):
        """公网 IP 的合法 URL 被接受"""
        assert _is_safe_http_url("https://example.com/image.png") is True

    # ---- 输入类型与长度边界 ----

    def test_non_string_input_rejected(self):
        """None / int / list 等非字符串输入被拒绝"""
        assert _is_safe_http_url(None) is False
        assert _is_safe_http_url(123) is False
        assert _is_safe_http_url(["url"]) is False
        assert _is_safe_http_url({"url": "x"}) is False

    def test_empty_string_rejected(self):
        """空字符串 / 纯空白字符串被拒绝"""
        assert _is_safe_http_url("") is False
        assert _is_safe_http_url("   ") is False

    def test_overlong_url_rejected(self):
        """超过 _MAX_URL_LEN 的 URL 被拒绝"""
        long_url = "https://example.com/" + ("a" * 3000)
        assert _is_safe_http_url(long_url) is False

    def test_unsafe_scheme_still_rejected(self):
        """危险 scheme 仍然被拒绝（回归保护）"""
        assert _is_safe_http_url("file:///etc/passwd") is False
        assert _is_safe_http_url("javascript:alert(1)") is False
        assert _is_safe_http_url("data:image/png;base64,AAAA") is False

