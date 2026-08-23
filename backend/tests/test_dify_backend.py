"""DifyBackend 单元测试

覆盖范围：
  ✓ text2img 分发 — 调用 chat_text2img 并返回 BackendResult
  ✓ BackendResult 字段映射 — answer / image_urls / conversation_id / backend
  ✓ img2img 分发 — 调用 chat_img2img（含 bytes→URL 转换）
  ✓ inpaint 分发 — 调用 chat_inpaint（含参考图 + 蒙版上传）
  ✓ upload_edit 分发 — 调用 chat_upload_edit
  ✓ 未知 operation — 抛出 ValueError
  ✓ oss_svc 缺失 — 需要上传时抛 RuntimeError
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.image_gen.base import BackendContext, BackendResult
from app.services.image_gen.dify_backend import DifyBackend


# ============================================================
# Helpers
# ============================================================

def _make_ctx(**overrides) -> BackendContext:
    """构造 BackendContext 的默认值，允许覆盖任意字段"""
    defaults = dict(
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
    defaults.update(overrides)
    return BackendContext(**defaults)


def _make_chat_result(**overrides):
    """构造模拟的 ChatRunResult"""
    defaults = dict(
        answer="你好",
        image_urls=["https://oss/1.png"],
        conversation_id="dify-cid",
        model_used="dify-model",
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_dify_client(**chat_mocks):
    """创建 mock DifyClient，可指定各 chat_* 方法的返回值"""
    client = MagicMock()
    for op_name, return_value in chat_mocks.items():
        mock_method = AsyncMock(return_value=return_value)
        setattr(client, op_name, mock_method)
    return client


def _make_oss_svc():
    """创建 mock OssService：upload_file 返回 None，sign_url 返回固定 URL"""
    oss = MagicMock()
    oss.upload_file = MagicMock(return_value=None)
    oss.sign_url = MagicMock(return_value="https://signed-oss/test.png")
    return oss


# ============================================================
# 1. text2img — 基本调用
# ============================================================

class TestDifyBackendText2Img:
    """text2img 基本调用"""

    @pytest.mark.asyncio
    async def test_dify_backend_calls_dify_client(self):
        """brief 标准用例：text2img 调用 chat_text2img"""
        dify_client = _make_dify_client(
            chat_text2img=_make_chat_result(),
        )
        backend = DifyBackend(dify_client=dify_client)

        ctx = _make_ctx(operation="text2img", query="a cat")
        result = await backend.run(ctx)

        assert result.image_urls == ["https://oss/1.png"]
        assert result.answer_text == "你好"
        assert result.conversation_id == "dify-cid"
        assert result.backend == "dify"

        # 验证 chat_text2img 被调用
        dify_client.chat_text2img.assert_called_once()

    @pytest.mark.asyncio
    async def test_text2img_passes_query_and_size(self):
        """验证 query / size / n / conversation_id 都透传到 chat_text2img"""
        dify_client = _make_dify_client(
            chat_text2img=_make_chat_result(),
        )
        backend = DifyBackend(dify_client=dify_client)

        user_id = uuid.uuid4()
        ctx = _make_ctx(
            user_id=user_id,
            operation="text2img",
            query="一只可爱的猫",
            conversation_id="conv-abc",
            size="1024x1792",
            n=2,
        )
        await backend.run(ctx)

        call_kwargs = dify_client.chat_text2img.call_args.kwargs
        assert call_kwargs["prompt"] == "一只可爱的猫"
        assert call_kwargs["size"] == "1024x1792"
        assert call_kwargs["n"] == 2
        assert call_kwargs["conversation_id"] == "conv-abc"
        assert call_kwargs["user_id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_text2img_empty_result(self):
        """追问场景：image_urls 为空、answer 是文本"""
        dify_client = _make_dify_client(
            chat_text2img=_make_chat_result(
                answer="你想要什么风格？",
                image_urls=[],
                conversation_id="conv-new",
                model_used="",
            ),
        )
        backend = DifyBackend(dify_client=dify_client)
        ctx = _make_ctx(operation="text2img")

        result = await backend.run(ctx)

        assert result.image_urls == []
        assert result.answer_text == "你想要什么风格？"
        assert result.conversation_id == "conv-new"
        assert result.model_used == ""
        assert result.backend == "dify"


# ============================================================
# 2. img2img
# ============================================================

class TestDifyBackendImg2Img:
    """img2img 调用"""

    @pytest.mark.asyncio
    async def test_img2img_calls_with_oss_url(self):
        """img2img 把 bytes 上传到 OSS 后传给 chat_img2img"""
        dify_client = _make_dify_client(
            chat_img2img=_make_chat_result(),
        )
        oss_svc = _make_oss_svc()
        backend = DifyBackend(dify_client=dify_client, oss_svc=oss_svc)

        ctx = _make_ctx(
            operation="img2img",
            reference_image=b"\x89PNG fake image",
            reference_mime="image/png",
            strength=0.7,
        )
        result = await backend.run(ctx)

        # OSS 上传
        oss_svc.upload_file.assert_called_once()
        oss_svc.sign_url.assert_called_once()

        # chat_img2img 调用参数
        call_kwargs = dify_client.chat_img2img.call_args.kwargs
        assert call_kwargs["reference_url"] == "https://signed-oss/test.png"
        assert call_kwargs["strength"] == 0.7
        assert call_kwargs["prompt"] == "a cat"

        # 结果
        assert result.backend == "dify"
        assert result.image_urls == ["https://oss/1.png"]

    @pytest.mark.asyncio
    async def test_img2img_default_strength(self):
        """strength 未指定时默认 0.6"""
        dify_client = _make_dify_client(
            chat_img2img=_make_chat_result(),
        )
        oss_svc = _make_oss_svc()
        backend = DifyBackend(dify_client=dify_client, oss_svc=oss_svc)

        ctx = _make_ctx(
            operation="img2img",
            reference_image=b"fake",
            strength=None,
        )
        await backend.run(ctx)

        call_kwargs = dify_client.chat_img2img.call_args.kwargs
        assert call_kwargs["strength"] == 0.6


# ============================================================
# 3. inpaint
# ============================================================

class TestDifyBackendInpaint:
    """inpaint 调用"""

    @pytest.mark.asyncio
    async def test_inpaint_uploads_both_images(self):
        """inpaint 需要参考图 + 蒙版，都上传到 OSS"""
        dify_client = _make_dify_client(
            chat_inpaint=_make_chat_result(),
        )
        oss_svc = _make_oss_svc()
        backend = DifyBackend(dify_client=dify_client, oss_svc=oss_svc)

        ctx = _make_ctx(
            operation="inpaint",
            reference_image=b"ref-bytes",
            mask_image=b"mask-bytes",
        )
        await backend.run(ctx)

        # 两次上传：ref + mask
        assert oss_svc.upload_file.call_count == 2

        call_kwargs = dify_client.chat_inpaint.call_args.kwargs
        assert call_kwargs["image_url"] == "https://signed-oss/test.png"
        assert call_kwargs["mask_url"] == "https://signed-oss/test.png"
        assert call_kwargs["prompt"] == "a cat"


# ============================================================
# 4. upload_edit
# ============================================================

class TestDifyBackendUploadEdit:
    """upload_edit 调用"""

    @pytest.mark.asyncio
    async def test_upload_edit_passes_edit_type(self):
        """upload_edit 传 edit_type 和 prompt"""
        dify_client = _make_dify_client(
            chat_upload_edit=_make_chat_result(),
        )
        oss_svc = _make_oss_svc()
        backend = DifyBackend(dify_client=dify_client, oss_svc=oss_svc)

        ctx = _make_ctx(
            operation="upload_edit",
            reference_image=b"ref-bytes",
            edit_type="upscale",
        )
        await backend.run(ctx)

        call_kwargs = dify_client.chat_upload_edit.call_args.kwargs
        assert call_kwargs["edit_type"] == "upscale"
        assert call_kwargs["image_url"] == "https://signed-oss/test.png"

    @pytest.mark.asyncio
    async def test_upload_edit_default_edit_type(self):
        """edit_type 未指定时默认 upscale"""
        dify_client = _make_dify_client(
            chat_upload_edit=_make_chat_result(),
        )
        oss_svc = _make_oss_svc()
        backend = DifyBackend(dify_client=dify_client, oss_svc=oss_svc)

        ctx = _make_ctx(
            operation="upload_edit",
            reference_image=b"ref-bytes",
            edit_type=None,
        )
        await backend.run(ctx)

        call_kwargs = dify_client.chat_upload_edit.call_args.kwargs
        assert call_kwargs["edit_type"] == "upscale"


# ============================================================
# 5. 错误处理
# ============================================================

class TestDifyBackendErrors:
    """错误处理"""

    @pytest.mark.asyncio
    async def test_unknown_operation_raises_value_error(self):
        """未知的 operation 抛 ValueError"""
        dify_client = _make_dify_client()
        backend = DifyBackend(dify_client=dify_client)
        ctx = _make_ctx(operation="unknown_op")

        with pytest.raises(ValueError, match="未知 operation"):
            await backend.run(ctx)

    @pytest.mark.asyncio
    async def test_oss_missing_raises_for_img2img(self):
        """img2img 需要 OSS 但未配置时抛 RuntimeError"""
        dify_client = _make_dify_client(
            chat_img2img=_make_chat_result(),
        )
        # 不传 oss_svc
        backend = DifyBackend(dify_client=dify_client)

        ctx = _make_ctx(
            operation="img2img",
            reference_image=b"need-oss",
        )

        with pytest.raises(RuntimeError, match="需要 OSS 服务"):
            await backend.run(ctx)

    @pytest.mark.asyncio
    async def test_text2img_no_oss_needed(self):
        """text2img 不需要 OSS，即使不配置也能正常运行"""
        dify_client = _make_dify_client(
            chat_text2img=_make_chat_result(),
        )
        # 不传 oss_svc
        backend = DifyBackend(dify_client=dify_client)
        ctx = _make_ctx(operation="text2img")

        result = await backend.run(ctx)
        assert result.backend == "dify"


# ============================================================
# 6. BackendResult 字段
# ============================================================

class TestDifyBackendResultMapping:
    """BackendResult 字段映射"""

    @pytest.mark.asyncio
    async def test_result_is_backend_result_instance(self):
        """返回结果必须是 BackendResult 实例"""
        dify_client = _make_dify_client(
            chat_text2img=_make_chat_result(),
        )
        backend = DifyBackend(dify_client=dify_client)
        ctx = _make_ctx(operation="text2img")

        result = await backend.run(ctx)
        assert isinstance(result, BackendResult)

    @pytest.mark.asyncio
    async def test_all_fields_mapped(self):
        """所有 BackendResult 字段都被正确填充"""
        dify_client = _make_dify_client(
            chat_text2img=_make_chat_result(
                answer="test answer",
                image_urls=["https://a.png", "https://b.png"],
                conversation_id="conv-xyz",
                model_used="doubao-v2",
            ),
        )
        backend = DifyBackend(dify_client=dify_client)
        ctx = _make_ctx(operation="text2img")

        result = await backend.run(ctx)

        assert result.image_urls == ["https://a.png", "https://b.png"]
        assert result.answer_text == "test answer"
        assert result.conversation_id == "conv-xyz"
        assert result.model_used == "doubao-v2"
        assert result.backend == "dify"
