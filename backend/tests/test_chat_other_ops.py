"""
Task 4 — chat_img2img / chat_inpaint / chat_upload_edit 单元测试

TDD：先写测试，后写实现。
覆盖范围：
  ✓ chat_img2img — 验证 reference_url / strength / size / model_preference 在 inputs
  ✓ chat_inpaint — 验证 image_url / mask_url / size / model_preference 在 inputs
  ✓ chat_upload_edit — 验证 image_url / edit_type 在 inputs，prompt 允许为空
  ✓ 配置缺失时抛出 config_error
  ✓ 多轮 conversation_id 传递
  ✓ 响应解析（ChatRunResult）
"""

import sys
import json
import pytest
import httpx
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.dify_client import DifyClient, ChatRunResult
from app.core.exceptions import DifyError
from app.services.dify_config_service import DifyConfig


# ============================================================
# Fixtures & Helpers
# ============================================================

def _make_config(**overrides) -> DifyConfig:
    """构造标准测试用 DifyConfig"""
    defaults = dict(
        api_url="https://dify.test.com/v1",
        app_api_key="app-test-key-12345",
        workflow_text2img="wf-text2img-001",
        workflow_img2img="wf-img2img-002",
        workflow_inpaint="wf-inpaint-003",
        workflow_upload_edit="wf-upload-edit-004",
        default_timeout=60.0,
    )
    defaults.update(overrides)
    return DifyConfig(**defaults)


def _make_config_svc(config=None):
    """创建 mock DifyConfigService"""
    cfg = config or _make_config()
    svc = MagicMock()
    svc.get_config = MagicMock(return_value=cfg)
    return svc


def _make_mock_response(status_code=200, json_data=None, text=""):
    """创建 mock httpx 响应"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or json.dumps(json_data or {})
    return resp


def _make_mock_client(post_response=None, post_side_effect=None):
    """创建 mock httpx.AsyncClient（支持 async with）"""
    mock_client = MagicMock()
    if post_side_effect:
        mock_client.post = AsyncMock(side_effect=post_side_effect)
    else:
        mock_client.post = AsyncMock(return_value=post_response or _make_mock_response())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _make_chat_response(
    conversation_id="conv-xyz",
    answer="ok",
    images=None,
    model_used="",
    polish_prompt="",
):
    """构造 Chatflow 成功响应"""
    metadata = {}
    if images is not None:
        metadata["images"] = images
    if model_used:
        metadata["model_used"] = model_used
    if polish_prompt:
        metadata["polish_prompt"] = polish_prompt
    return _make_mock_response(
        status_code=200,
        json_data={
            "conversation_id": conversation_id,
            "message_id": "msg-1",
            "answer": answer,
            "metadata": metadata,
        },
    )


# ============================================================
# 1. chat_img2img
# ============================================================

class TestChatImg2Img:
    """chat_img2img 调用测试"""

    @pytest.mark.asyncio
    async def test_chat_img2img_passes_reference_url_and_strength(self):
        """验证 reference_url / strength / size / model_preference 在 inputs 中"""
        mock_resp = _make_chat_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_img2img(
                prompt="改成水彩",
                reference_url="https://oss/x.png",
                conversation_id="conv-1",
                strength=0.6,
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )

        # 验证请求 URL
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://dify.test.com/v1/chat-messages"

        # 验证 body
        body = call_args[1]["json"]
        assert body["inputs"]["reference_url"] == "https://oss/x.png"
        assert body["inputs"]["strength"] == 0.6
        assert body["inputs"]["size"] == "1024x1024"
        assert body["inputs"]["model_preference"] == "auto"
        assert body["query"] == "改成水彩"
        assert body["conversation_id"] == "conv-1"
        assert body["response_mode"] == "blocking"
        assert body["user"] == "u1"

        # 验证返回结果
        assert isinstance(result, ChatRunResult)
        assert result.conversation_id == "conv-xyz"

    @pytest.mark.asyncio
    async def test_chat_img2img_with_images_in_response(self):
        """img2img 返回带图片的响应"""
        mock_resp = _make_chat_response(
            answer="已转换 <<GENERATE>>",
            images=["https://cdn.test.com/result.png"],
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_img2img(
                prompt="油画风",
                reference_url="https://oss/ref.png",
                conversation_id=None,
                strength=0.8,
                size="1024x1024",
                model_preference="doubao",
                user_id="u1",
            )

        assert result.image_urls == ["https://cdn.test.com/result.png"]

    @pytest.mark.asyncio
    async def test_chat_img2img_config_missing_raises(self):
        """workflow_img2img 未配置时抛出 config_error"""
        config = _make_config(workflow_img2img="")
        client = DifyClient(config_svc=_make_config_svc(config))

        with pytest.raises(DifyError) as exc_info:
            await client.chat_img2img(
                prompt="test",
                reference_url="https://oss/x.png",
                conversation_id=None,
                strength=0.5,
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )
        assert exc_info.value.kind == "config_error"


# ============================================================
# 2. chat_inpaint
# ============================================================

class TestChatInpaint:
    """chat_inpaint 调用测试"""

    @pytest.mark.asyncio
    async def test_chat_inpaint_passes_image_and_mask(self):
        """验证 image_url / mask_url / size / model_preference 在 inputs 中"""
        mock_resp = _make_chat_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_inpaint(
                prompt="改成花",
                image_url="https://oss/img.png",
                mask_url="https://oss/mask.png",
                conversation_id=None,
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://dify.test.com/v1/chat-messages"

        body = call_args[1]["json"]
        assert body["inputs"]["image_url"] == "https://oss/img.png"
        assert body["inputs"]["mask_url"] == "https://oss/mask.png"
        assert body["inputs"]["size"] == "1024x1024"
        assert body["inputs"]["model_preference"] == "auto"
        assert body["query"] == "改成花"
        assert body["conversation_id"] == ""
        assert body["response_mode"] == "blocking"

        assert isinstance(result, ChatRunResult)

    @pytest.mark.asyncio
    async def test_chat_inpaint_with_conversation_id(self):
        """多轮对话：传入已有的 conversation_id"""
        mock_resp = _make_chat_response(conversation_id="conv-existing")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            await client.chat_inpaint(
                prompt="继续编辑",
                image_url="https://oss/img.png",
                mask_url="https://oss/mask.png",
                conversation_id="conv-existing",
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )

        body = mock_client.post.call_args[1]["json"]
        assert body["conversation_id"] == "conv-existing"

    @pytest.mark.asyncio
    async def test_chat_inpaint_config_missing_raises(self):
        """workflow_inpaint 未配置时抛出 config_error"""
        config = _make_config(workflow_inpaint="")
        client = DifyClient(config_svc=_make_config_svc(config))

        with pytest.raises(DifyError) as exc_info:
            await client.chat_inpaint(
                prompt="test",
                image_url="https://oss/img.png",
                mask_url="https://oss/mask.png",
                conversation_id=None,
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )
        assert exc_info.value.kind == "config_error"


# ============================================================
# 3. chat_upload_edit
# ============================================================

class TestChatUploadEdit:
    """chat_upload_edit 调用测试"""

    @pytest.mark.asyncio
    async def test_chat_upload_edit_passes_edit_type(self):
        """验证 image_url / edit_type 在 inputs 中，prompt 允许为空"""
        mock_resp = _make_chat_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_upload_edit(
                image_url="https://oss/img.png",
                edit_type="upscale",
                conversation_id=None,
                prompt="",
                user_id="u1",
            )

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://dify.test.com/v1/chat-messages"

        body = call_args[1]["json"]
        assert body["inputs"]["image_url"] == "https://oss/img.png"
        assert body["inputs"]["edit_type"] == "upscale"
        assert body["query"] == ""  # upload_edit 允许 prompt 为空
        assert body["conversation_id"] == ""
        assert body["response_mode"] == "blocking"
        assert body["user"] == "u1"

        assert isinstance(result, ChatRunResult)

    @pytest.mark.asyncio
    async def test_chat_upload_edit_with_prompt(self):
        """带 prompt 的上传编辑"""
        mock_resp = _make_chat_response(answer="已完成风格迁移 <<GENERATE>>")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_upload_edit(
                image_url="https://oss/img.png",
                edit_type="style_transfer",
                conversation_id=None,
                prompt="赛博朋克风格",
                user_id="u1",
            )

        body = mock_client.post.call_args[1]["json"]
        assert body["query"] == "赛博朋克风格"
        assert body["inputs"]["edit_type"] == "style_transfer"

    @pytest.mark.asyncio
    async def test_chat_upload_edit_config_missing_raises(self):
        """workflow_upload_edit 未配置时抛出 config_error"""
        config = _make_config(workflow_upload_edit="")
        client = DifyClient(config_svc=_make_config_svc(config))

        with pytest.raises(DifyError) as exc_info:
            await client.chat_upload_edit(
                image_url="https://oss/img.png",
                edit_type="upscale",
                conversation_id=None,
                prompt="",
                user_id="u1",
            )
        assert exc_info.value.kind == "config_error"


# ============================================================
# 4. 错误处理（共享 _call_chat 逻辑）
# ============================================================

class TestChatOtherOpsErrors:
    """chat_img2img / chat_inpaint / chat_upload_edit 共享错误处理"""

    @pytest.mark.asyncio
    async def test_http_401_raises_auth_error(self):
        """401 → kind='auth_error'"""
        mock_resp = _make_mock_response(status_code=401, text="Unauthorized")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.chat_img2img(
                    prompt="test", reference_url="https://oss/x.png",
                    conversation_id=None, strength=0.5,
                    size="1024x1024", model_preference="auto", user_id="u1",
                )
        assert exc_info.value.kind == "auth_error"

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """超时 → kind='timeout'"""
        mock_client = _make_mock_client(
            post_side_effect=httpx.TimeoutException("Request timed out"),
        )
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.chat_inpaint(
                    prompt="test", image_url="https://oss/img.png",
                    mask_url="https://oss/mask.png", conversation_id=None,
                    size="1024x1024", model_preference="auto", user_id="u1",
                )
        assert exc_info.value.kind == "timeout"

    @pytest.mark.asyncio
    async def test_connection_error_raises_connection_error(self):
        """连接失败 → kind='connection_error'"""
        mock_client = _make_mock_client(
            post_side_effect=httpx.ConnectError("Connection refused"),
        )
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.chat_upload_edit(
                    image_url="https://oss/img.png", edit_type="upscale",
                    conversation_id=None, prompt="", user_id="u1",
                )
        assert exc_info.value.kind == "connection_error"
