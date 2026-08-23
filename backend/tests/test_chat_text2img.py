"""
Task 3 — chat_text2img 单元测试

TDD：先写测试，后写实现。
覆盖范围：
  ✓ chat_text2img 成功 — 验证 URL / headers / body / 响应解析
  ✓ chat_text2img 提取 images — metadata.images 有值时提取为 image_urls
  ✓ <<GENERATE>> 标记 — answer 含标记 + metadata.images 有值 → 图片被提取
  ✓ conversation_id 传递 — 多轮对话时传入已有的 conversation_id
  ✓ inputs 字段 — size / n / style / model_preference 全部在 inputs 中
  ✓ response_mode 为 blocking
  ✓ user_id 为空时默认 anonymous
  ✓ conversation_id 为 None 时发送空字符串
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
    """创建 mock DifyConfigService，get_config() 返回固定 config"""
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
    """创建 mock httpx.AsyncClient"""
    mock_client = MagicMock()
    if post_side_effect:
        mock_client.post = AsyncMock(side_effect=post_side_effect)
    else:
        mock_client.post = AsyncMock(return_value=post_response or _make_mock_response())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _make_chat_response(
    conversation_id="conv-abc",
    answer="你想要什么风格？",
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
# 1. 基本调用 — chat_text2img
# ============================================================

class TestChatText2ImgBasic:
    """chat_text2img 基本调用"""

    @pytest.mark.asyncio
    async def test_chat_text2img_posts_to_chat_messages(self):
        """验证 URL / headers / body / 响应解析"""
        mock_resp = _make_chat_response(
            conversation_id="conv-abc",
            answer="你想要什么风格？",
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_text2img(
                prompt="一只猫",
                conversation_id=None,
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="user-1",
            )

        # 验证请求 URL
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://dify.test.com/v1/chat-messages"

        # 验证 Authorization header
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer app-test-key-12345"
        assert headers["Content-Type"] == "application/json"

        # 验证 body
        body = call_args[1]["json"]
        assert body["query"] == "一只猫"
        assert body["response_mode"] == "blocking"
        assert body["user"] == "user-1"
        assert body["conversation_id"] == ""

        # 验证 inputs
        inputs = body["inputs"]
        assert inputs["size"] == "1024x1024"
        assert inputs["n"] == 1
        assert inputs["style"] == "auto"
        assert inputs["model_preference"] == "auto"

        # 验证返回结果
        assert isinstance(result, ChatRunResult)
        assert result.conversation_id == "conv-abc"
        assert result.answer == "你想要什么风格？"
        assert result.image_urls == []

    @pytest.mark.asyncio
    async def test_chat_text2img_with_conversation_id(self):
        """多轮对话：传入已有的 conversation_id"""
        mock_resp = _make_chat_response(
            conversation_id="conv-abc",
            answer="好的，我来生成",
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            await client.chat_text2img(
                prompt="生成一只猫",
                conversation_id="conv-abc",
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="user-1",
            )

        call_args = mock_client.post.call_args
        body = call_args[1]["json"]
        assert body["conversation_id"] == "conv-abc"


# ============================================================
# 2. 图片提取
# ============================================================

class TestChatText2ImgImageExtraction:
    """chat_text2img 图片提取"""

    @pytest.mark.asyncio
    async def test_chat_text2img_extracts_images_from_metadata(self):
        """metadata.images 有值时提取为 image_urls（含 <<GENERATE>> 标记）"""
        mock_resp = _make_chat_response(
            answer="生成完成 <<GENERATE>>",
            images=["https://x.com/a.png"],
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_text2img(
                prompt="猫",
                conversation_id=None,
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="u1",
            )

        assert "<<GENERATE>>" in result.answer
        assert result.image_urls == ["https://x.com/a.png"]

    @pytest.mark.asyncio
    async def test_chat_text2img_multiple_images(self):
        """多张图片提取"""
        mock_resp = _make_chat_response(
            answer="生成完成 <<GENERATE>>",
            images=["https://x.com/a.png", "https://x.com/b.png"],
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_text2img(
                prompt="两只猫",
                conversation_id=None,
                size="1024x1024",
                n=2,
                style="auto",
                model_preference="auto",
                user_id="u1",
            )

        assert len(result.image_urls) == 2

    @pytest.mark.asyncio
    async def test_chat_text2img_no_images_when_metadata_empty(self):
        """metadata 无 images 字段时 image_urls 为空"""
        mock_resp = _make_chat_response(
            answer="你想要什么风格？",
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_text2img(
                prompt="猫",
                conversation_id=None,
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="u1",
            )

        assert result.image_urls == []

    @pytest.mark.asyncio
    async def test_chat_text2img_images_as_json_string(self):
        """images 为 JSON 字符串时自动解析"""
        mock_resp = _make_mock_response(
            status_code=200,
            json_data={
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "answer": "<<GENERATE>>",
                "metadata": {
                    "images": '["https://x.com/a.png", "https://x.com/b.png"]',
                },
            },
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.chat_text2img(
                prompt="猫",
                conversation_id=None,
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="u1",
            )

        assert result.image_urls == ["https://x.com/a.png", "https://x.com/b.png"]


# ============================================================
# 3. user_id 默认值
# ============================================================

class TestChatText2ImgUserId:
    """user_id 默认值"""

    @pytest.mark.asyncio
    async def test_user_id_defaults_to_anonymous(self):
        """user_id 为空时默认 'anonymous'"""
        mock_resp = _make_chat_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            await client.chat_text2img(
                prompt="test",
                conversation_id=None,
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="",
            )

        call_args = mock_client.post.call_args
        body = call_args[1]["json"]
        assert body["user"] == "anonymous"


# ============================================================
# 4. HTTP 错误 / 超时 / 连接错误
# ============================================================

class TestChatText2ImgErrors:
    """chat_text2img 错误处理"""

    @pytest.mark.asyncio
    async def test_http_401_raises_auth_error(self):
        """401 → kind='auth_error'"""
        mock_resp = _make_mock_response(status_code=401, text="Unauthorized")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.chat_text2img(
                    prompt="test", conversation_id=None,
                    size="1024x1024", n=1, style="auto",
                    model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "auth_error"

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """httpx.TimeoutException → kind='timeout'"""
        mock_client = _make_mock_client(
            post_side_effect=httpx.TimeoutException("Request timed out"),
        )
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.chat_text2img(
                    prompt="test", conversation_id=None,
                    size="1024x1024", n=1, style="auto",
                    model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "timeout"

    @pytest.mark.asyncio
    async def test_connection_error_raises_connection_error(self):
        """httpx.ConnectError → kind='connection_error'"""
        mock_client = _make_mock_client(
            post_side_effect=httpx.ConnectError("Connection refused"),
        )
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.chat_text2img(
                    prompt="test", conversation_id=None,
                    size="1024x1024", n=1, style="auto",
                    model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "connection_error"


# ============================================================
# 5. _parse_chat_response 单元测试
# ============================================================

class TestParseChatResponse:
    """_parse_chat_response 解析逻辑"""

    def test_parse_basic_response(self):
        """基本响应解析"""
        client = DifyClient(config_svc=_make_config_svc())
        data = {
            "conversation_id": "conv-1",
            "answer": "hello",
            "metadata": {},
        }
        result = client._parse_chat_response(data)
        assert result.conversation_id == "conv-1"
        assert result.answer == "hello"
        assert result.image_urls == []

    def test_parse_with_model_and_polish_prompt(self):
        """提取 model_used 和 polish_prompt"""
        client = DifyClient(config_svc=_make_config_svc())
        data = {
            "conversation_id": "conv-1",
            "answer": "<<GENERATE>>",
            "metadata": {
                "images": ["https://x.com/a.png"],
                "model_used": "doubao-seedream",
                "polish_prompt": "a cute cat",
            },
        }
        result = client._parse_chat_response(data)
        assert result.model_used == "doubao-seedream"
        assert result.polish_prompt == "a cute cat"
        assert result.image_urls == ["https://x.com/a.png"]

    def test_parse_metadata_none(self):
        """metadata 为 None 时不报错"""
        client = DifyClient(config_svc=_make_config_svc())
        data = {
            "conversation_id": "conv-1",
            "answer": "hello",
            "metadata": None,
        }
        result = client._parse_chat_response(data)
        assert result.image_urls == []

    def test_parse_images_invalid_json_string(self):
        """images 为无效 JSON 字符串时返回空列表"""
        client = DifyClient(config_svc=_make_config_svc())
        data = {
            "conversation_id": "conv-1",
            "answer": "<<GENERATE>>",
            "metadata": {"images": "not-valid-json"},
        }
        result = client._parse_chat_response(data)
        assert result.image_urls == []

    def test_parse_raw_response_preserved(self):
        """raw_response 保留原始数据"""
        client = DifyClient(config_svc=_make_config_svc())
        data = {
            "conversation_id": "conv-1",
            "answer": "hello",
            "metadata": {},
        }
        result = client._parse_chat_response(data)
        assert result.raw_response is data
