"""
Task 3.1 — DifyClient 单元测试

TDD：先写测试，后写实现。
覆盖范围（14+ 用例）：
  ✓ run_text2img 成功 — 验证 URL / headers / body / 响应解析
  ✓ run_img2img 成功 — 验证 reference_url / strength 在 inputs
  ✓ run_inpaint 成功 — 验证 image_url / mask_url 在 inputs
  ✓ run_upload_edit 成功 — 验证 image_url / edit_type / prompt
  ✓ HTTP 404 → kind="workflow_not_found"
  ✓ HTTP 401 → kind="auth_error"
  ✓ HTTP 429 → kind="rate_limit"
  ✓ HTTP 5xx → kind="http_error"
  ✓ 超时 → kind="timeout"
  ✓ 连接失败 → kind="connection_error"
  ✓ 工作流 status=failed → kind="workflow_failed"
  ✓ 工作流 status=stopped → kind="workflow_stopped"
  ✓ 空 image_urls → kind="empty_result"
  ✓ 配置缺失 workflow → kind="config_error"
  ✓ test_connection 成功 / 配置不完整
"""

import sys
import time
import json
import pytest
import httpx
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.dify_client import DifyClient, DifyRunResult
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


def _make_mock_client(post_response=None, get_response=None,
                      post_side_effect=None, get_side_effect=None):
    """
    创建 mock httpx.AsyncClient。
    支持正常返回（return_value）和异常（side_effect）。
    """
    mock_client = MagicMock()

    # POST 方法（工作流调用）
    if post_side_effect:
        mock_client.post = AsyncMock(side_effect=post_side_effect)
    else:
        mock_client.post = AsyncMock(return_value=post_response or _make_mock_response())

    # GET 方法（连通性测试）
    if get_side_effect:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    else:
        mock_client.get = AsyncMock(return_value=get_response or _make_mock_response())

    # async context manager: async with httpx.AsyncClient(...) as client:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return mock_client


def _make_success_response(image_urls=None, model_used="doubao-seedream"):
    """构造 Dify 工作流成功响应"""
    return _make_mock_response(
        status_code=200,
        json_data={
            "task_id": "test-task-001",
            "workflow_run_id": "run-abc-123",
            "data": {
                "id": "run-abc-123",
                "workflow_id": "wf-text2img-001",
                "status": "succeeded",
                "outputs": {
                    "image_urls": image_urls or ["https://cdn.test.com/img1.png"],
                    "model_used": model_used,
                },
            },
        },
    )


# ============================================================
# 1. 成功调用 — 4 个 operation
# ============================================================

class TestRunText2ImgSuccess:
    """text2img 成功调用"""

    @pytest.mark.asyncio
    async def test_run_text2img_success(self):
        """验证 URL / headers / body / 响应解析"""
        mock_resp = _make_success_response(
            image_urls=["https://cdn.test.com/generated.png"],
            model_used="doubao-seedream-3",
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.run_text2img(
                prompt="一只可爱的猫咪",
                size="1024x1024",
                n=2,
                style="natural",
                model_preference="doubao",
                user_id="user-001",
            )

        # 验证请求 URL
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://dify.test.com/v1/workflows/run"

        # 验证 Authorization header
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer app-test-key-12345"
        assert headers["Content-Type"] == "application/json"

        # 验证 body inputs
        body = call_args[1]["json"]
        assert body["response_mode"] == "blocking"
        assert body["user"] == "user-001"
        inputs = body["inputs"]
        assert inputs["prompt"] == "一只可爱的猫咪"
        assert inputs["size"] == "1024x1024"
        assert inputs["n"] == 2
        assert inputs["style"] == "natural"
        assert inputs["model_preference"] == "doubao"

        # 验证返回结果
        assert isinstance(result, DifyRunResult)
        assert result.image_urls == ["https://cdn.test.com/generated.png"]
        assert result.model_used == "doubao-seedream-3"
        assert result.elapsed_seconds > 0
        assert isinstance(result.raw_response, dict)


class TestRunImg2ImgSuccess:
    """img2img 成功调用"""

    @pytest.mark.asyncio
    async def test_run_img2img_with_strength(self):
        """验证 reference_url / strength 在 inputs"""
        mock_resp = _make_success_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.run_img2img(
                prompt="把猫咪变成油画风格",
                reference_url="https://oss.test.com/ref.png",
                strength=0.7,
                size="1024x1024",
                model_preference="auto",
                user_id="user-002",
            )

        call_args = mock_client.post.call_args
        body = call_args[1]["json"]
        inputs = body["inputs"]
        assert inputs["prompt"] == "把猫咪变成油画风格"
        assert inputs["reference_url"] == "https://oss.test.com/ref.png"
        assert inputs["strength"] == 0.7
        assert inputs["size"] == "1024x1024"
        assert inputs["model_preference"] == "auto"

        assert isinstance(result, DifyRunResult)
        assert len(result.image_urls) > 0


class TestRunInpaintSuccess:
    """inpaint 成功调用"""

    @pytest.mark.asyncio
    async def test_run_inpaint_with_mask(self):
        """验证 image_url / mask_url 在 inputs"""
        mock_resp = _make_success_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.run_inpaint(
                prompt="替换背景为蓝天",
                image_url="https://oss.test.com/original.png",
                mask_url="https://oss.test.com/mask.png",
                size="1024x1024",
                model_preference="auto",
                user_id="user-003",
            )

        call_args = mock_client.post.call_args
        body = call_args[1]["json"]
        inputs = body["inputs"]
        assert inputs["prompt"] == "替换背景为蓝天"
        assert inputs["image_url"] == "https://oss.test.com/original.png"
        assert inputs["mask_url"] == "https://oss.test.com/mask.png"

        assert isinstance(result, DifyRunResult)


class TestRunUploadEditSuccess:
    """upload_edit 成功调用"""

    @pytest.mark.asyncio
    async def test_run_upload_edit_with_edit_type(self):
        """验证 image_url / edit_type / prompt"""
        mock_resp = _make_success_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.run_upload_edit(
                image_url="https://oss.test.com/photo.png",
                edit_type="upscale",
                prompt="高清化",
                user_id="user-004",
            )

        call_args = mock_client.post.call_args
        body = call_args[1]["json"]
        inputs = body["inputs"]
        assert inputs["image_url"] == "https://oss.test.com/photo.png"
        assert inputs["edit_type"] == "upscale"
        assert inputs["prompt"] == "高清化"

        assert isinstance(result, DifyRunResult)


# ============================================================
# 2. HTTP 错误分类
# ============================================================

class TestHttpErrorClassification:
    """HTTP 状态码 → DifyError.kind 映射"""

    @pytest.mark.asyncio
    async def test_http_404_raises_workflow_not_found(self):
        """404 → kind='workflow_not_found'"""
        mock_resp = _make_mock_response(status_code=404, text="Workflow not found")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "workflow_not_found"

    @pytest.mark.asyncio
    async def test_http_401_raises_auth_error(self):
        """401 → kind='auth_error'"""
        mock_resp = _make_mock_response(status_code=401, text="Unauthorized")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "auth_error"

    @pytest.mark.asyncio
    async def test_http_429_raises_rate_limit(self):
        """429 → kind='rate_limit'"""
        mock_resp = _make_mock_response(status_code=429, text="Rate limit exceeded")
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "rate_limit"

    @pytest.mark.asyncio
    async def test_http_5xx_raises_http_error(self):
        """500/502/503 → kind='http_error'"""
        for status in [500, 502, 503]:
            mock_resp = _make_mock_response(status_code=status, text="Server Error")
            mock_client = _make_mock_client(post_response=mock_resp)
            client = DifyClient(config_svc=_make_config_svc())

            with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
                with pytest.raises(DifyError) as exc_info:
                    await client.run_text2img(
                        prompt="test", size="1024x1024", n=1,
                        style=None, model_preference="auto", user_id="u1",
                    )

            assert exc_info.value.kind == "http_error", f"status={status} should be http_error"


# ============================================================
# 3. 超时 / 连接错误
# ============================================================

class TestTimeoutAndConnection:
    """超时和连接错误"""

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """httpx.TimeoutException → kind='timeout'"""
        mock_client = _make_mock_client(
            post_side_effect=httpx.TimeoutException("Request timed out"),
        )
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
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
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "connection_error"


# ============================================================
# 4. 工作流状态错误
# ============================================================

class TestWorkflowStatusErrors:
    """Dify 响应 status 字段异常"""

    @pytest.mark.asyncio
    async def test_workflow_status_failed_raises_workflow_failed(self):
        """status='failed' → kind='workflow_failed'"""
        mock_resp = _make_mock_response(
            status_code=200,
            json_data={
                "workflow_run_id": "run-fail",
                "data": {
                    "id": "run-fail",
                    "workflow_id": "wf-001",
                    "status": "failed",
                    "error": "模型推理超时",
                    "outputs": {},
                },
            },
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "workflow_failed"

    @pytest.mark.asyncio
    async def test_workflow_status_stopped_raises_workflow_stopped(self):
        """status='stopped' → kind='workflow_stopped'"""
        mock_resp = _make_mock_response(
            status_code=200,
            json_data={
                "workflow_run_id": "run-stop",
                "data": {
                    "id": "run-stop",
                    "workflow_id": "wf-001",
                    "status": "stopped",
                    "outputs": {},
                },
            },
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "workflow_stopped"


# ============================================================
# 5. 空结果 / 配置缺失
# ============================================================

class TestEmptyResultAndConfigError:
    """空结果和配置错误"""

    @pytest.mark.asyncio
    async def test_empty_image_urls_raises_empty_result(self):
        """image_urls 为空 → kind='empty_result'"""
        mock_resp = _make_mock_response(
            status_code=200,
            json_data={
                "workflow_run_id": "run-empty",
                "data": {
                    "id": "run-empty",
                    "workflow_id": "wf-001",
                    "status": "succeeded",
                    "outputs": {
                        "image_urls": [],
                        "model_used": "doubao",
                    },
                },
            },
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(DifyError) as exc_info:
                await client.run_text2img(
                    prompt="test", size="1024x1024", n=1,
                    style=None, model_preference="auto", user_id="u1",
                )

        assert exc_info.value.kind == "empty_result"

    @pytest.mark.asyncio
    async def test_config_missing_workflow_raises_config_error(self):
        """workflow id 为空 → kind='config_error'"""
        config_svc = _make_config_svc(_make_config(workflow_text2img=""))
        client = DifyClient(config_svc=config_svc)

        with pytest.raises(DifyError) as exc_info:
            await client.run_text2img(
                prompt="test", size="1024x1024", n=1,
                style=None, model_preference="auto", user_id="u1",
            )

        assert exc_info.value.kind == "config_error"

    @pytest.mark.asyncio
    async def test_config_missing_img2img_workflow(self):
        """img2img workflow 未配置 → kind='config_error'"""
        config_svc = _make_config_svc(_make_config(workflow_img2img=""))
        client = DifyClient(config_svc=config_svc)

        with pytest.raises(DifyError) as exc_info:
            await client.run_img2img(
                prompt="test", reference_url="https://x.com/img.png",
                strength=0.5, size="1024x1024",
                model_preference="auto", user_id="u1",
            )

        assert exc_info.value.kind == "config_error"

    @pytest.mark.asyncio
    async def test_config_missing_inpaint_workflow(self):
        """inpaint workflow 未配置 → kind='config_error'"""
        config_svc = _make_config_svc(_make_config(workflow_inpaint=""))
        client = DifyClient(config_svc=config_svc)

        with pytest.raises(DifyError) as exc_info:
            await client.run_inpaint(
                prompt="test", image_url="https://x.com/img.png",
                mask_url="https://x.com/mask.png",
                size="1024x1024", model_preference="auto", user_id="u1",
            )

        assert exc_info.value.kind == "config_error"

    @pytest.mark.asyncio
    async def test_config_missing_upload_edit_workflow(self):
        """upload_edit workflow 未配置 → kind='config_error'"""
        config_svc = _make_config_svc(_make_config(workflow_upload_edit=""))
        client = DifyClient(config_svc=config_svc)

        with pytest.raises(DifyError) as exc_info:
            await client.run_upload_edit(
                image_url="https://x.com/img.png",
                edit_type="upscale", prompt=None,
                user_id="u1",
            )

        assert exc_info.value.kind == "config_error"


# ============================================================
# 6. test_connection — 连通性测试
# ============================================================

class TestTestConnection:
    """test_connection 方法"""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """连通性测试成功"""
        mock_resp = _make_mock_response(status_code=200)
        mock_client = _make_mock_client(get_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            ok, msg = await client.test_connection()

        assert ok is True

    @pytest.mark.asyncio
    async def test_connection_missing_config(self):
        """配置不完整（api_url 为空）→ 返回 (False, ...)"""
        config_svc = _make_config_svc(_make_config(api_url=""))
        client = DifyClient(config_svc=config_svc)

        ok, msg = await client.test_connection()

        assert ok is False
        assert "配置" in msg or "不完整" in msg

    @pytest.mark.asyncio
    async def test_connection_http_error(self):
        """连通性测试 HTTP 非 200 → (False, ...)"""
        mock_resp = _make_mock_response(status_code=403, text="Forbidden")
        mock_client = _make_mock_client(get_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            ok, msg = await client.test_connection()

        assert ok is False
        assert "403" in msg


# ============================================================
# 7. 超时参数传递 / 自定义 timeout
# ============================================================

class TestTimeoutParameter:
    """timeout 参数传递"""

    @pytest.mark.asyncio
    async def test_custom_timeout_passed_to_httpx(self):
        """自定义 timeout 传递给 httpx.AsyncClient"""
        mock_resp = _make_success_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            await client.run_text2img(
                prompt="test", size="1024x1024", n=1,
                style=None, model_preference="auto",
                user_id="u1", timeout=120.0,
            )

        # 验证 timeout 参数被传递给 AsyncClient
        mock_cls.assert_called_once_with(timeout=120.0)

    @pytest.mark.asyncio
    async def test_default_timeout_from_config(self):
        """不指定 timeout 时使用 config.default_timeout"""
        mock_resp = _make_success_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc(_make_config(default_timeout=90.0))
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            await client.run_text2img(
                prompt="test", size="1024x1024", n=1,
                style=None, model_preference="auto", user_id="u1",
            )

        mock_cls.assert_called_once_with(timeout=90.0)


# ============================================================
# 8. 响应解析边界情况
# ============================================================

class TestResponseParsing:
    """响应解析边界情况"""

    @pytest.mark.asyncio
    async def test_image_urls_as_json_string(self):
        """image_urls 为 JSON 字符串时自动解析"""
        mock_resp = _make_mock_response(
            status_code=200,
            json_data={
                "workflow_run_id": "run-json",
                "data": {
                    "id": "run-json",
                    "workflow_id": "wf-001",
                    "status": "succeeded",
                    "outputs": {
                        "image_urls": '["https://cdn.test.com/a.png", "https://cdn.test.com/b.png"]',
                        "model_used": "qwen",
                    },
                },
            },
        )
        mock_client = _make_mock_client(post_response=mock_resp)
        client = DifyClient(config_svc=_make_config_svc())

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            result = await client.run_text2img(
                prompt="test", size="1024x1024", n=2,
                style=None, model_preference="auto", user_id="u1",
            )

        assert result.image_urls == [
            "https://cdn.test.com/a.png",
            "https://cdn.test.com/b.png",
        ]
        assert result.model_used == "qwen"

    @pytest.mark.asyncio
    async def test_user_id_defaults_to_anonymous(self):
        """user_id 为空时默认 'anonymous'"""
        mock_resp = _make_success_response()
        mock_client = _make_mock_client(post_response=mock_resp)
        config_svc = _make_config_svc()
        client = DifyClient(config_svc=config_svc)

        with patch("app.services.dify_client.httpx.AsyncClient", return_value=mock_client):
            await client.run_text2img(
                prompt="test", size="1024x1024", n=1,
                style=None, model_preference="auto", user_id="",
            )

        call_args = mock_client.post.call_args
        body = call_args[1]["json"]
        assert body["user"] == "anonymous"
