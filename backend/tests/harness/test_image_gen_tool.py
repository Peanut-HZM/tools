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
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenResult,
)
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.image_gen import ImageGenTool


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
