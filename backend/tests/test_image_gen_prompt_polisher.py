"""
ImageGenPromptPolisher 单元测试

润色器使用 OrderedLLMGateway 走 text 类别调用 LLM，
把用户原始提示词转换为更适合图像生成模型的英文提示词。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.image_gen_prompt_polisher import ImageGenPromptPolisher
from app.services.llm.exceptions import AllModelsUnavailableError


# ============================================================
# Fixtures
# ============================================================

def _make_provider(
    api_key_encrypted: str = "encrypted-key",
    base_url: str = "https://api.example.com",
    provider_type: str = "openai",
):
    return SimpleNamespace(
        id="provider-id-1234",
        api_key_encrypted=api_key_encrypted,
        base_url=base_url,
        provider_type=provider_type,
    )


_MISSING = object()


def _make_model(
    model_name: str = "gpt-4o",
    model_id: str = "model-id-5678",
    category: str = "text",
    provider=_MISSING,
):
    if provider is _MISSING:
        provider = _make_provider()
    return SimpleNamespace(
        id=model_id,
        name="Test Model",
        model_name=model_name,
        category=category,
        provider=provider,
    )


@pytest.fixture
def mock_model_svc():
    svc = MagicMock()
    svc.get_default_model = MagicMock()
    return svc


@pytest.fixture
def mock_gateway():
    gw = AsyncMock()
    gw.generate = AsyncMock()
    return gw


def _build_polisher(mock_model_svc, mock_gateway) -> ImageGenPromptPolisher:
    polisher = ImageGenPromptPolisher.__new__(ImageGenPromptPolisher)
    polisher._db = MagicMock()
    polisher._model_svc = mock_model_svc
    polisher._gateway = mock_gateway
    return polisher


# ============================================================
# 1. 成功路径
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_optimized_prompt(mock_model_svc, mock_gateway):
    """正常路径：text 模型存在 → 调用网关 → 返回润色后的内容"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = (
        "a majestic cat sitting on a windowsill, golden hour lighting"
    )

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("一只可爱的猫", user_id="user-1")

    assert result == "a majestic cat sitting on a windowsill, golden hour lighting"
    mock_model_svc.get_default_model.assert_called_once_with(category="text")
    mock_gateway.generate.assert_called_once()


# ============================================================
# 2. 使用 text 类别
# ============================================================

@pytest.mark.asyncio
async def test_polish_uses_text_category(mock_model_svc, mock_gateway):
    """润色器使用 text 类别调用网关"""
    model = _make_model(model_name="dalle-3")
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = "polished prompt"

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "polished prompt"
    mock_model_svc.get_default_model.assert_called_once_with(category="text")
    call_kwargs = mock_gateway.generate.call_args.kwargs
    assert call_kwargs["category"] == "text"


# ============================================================
# 3. 无默认模型 → 原 prompt + warning
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_no_model_found(
    mock_model_svc, mock_gateway, caplog
):
    """text 类别无默认 → 返回原 prompt，记 warning"""
    mock_model_svc.get_default_model.return_value = None

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_gateway.generate.assert_not_called()
    assert any("无可用默认模型" in rec.message for rec in caplog.records)


# ============================================================
# 4. 网关抛异常 → 原 prompt + warning
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_gateway_fails(
    mock_model_svc, mock_gateway, caplog
):
    """网关抛异常 → 不冒泡，返回原 prompt + warning"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.side_effect = RuntimeError("LLM service down")

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    assert any("润色失败" in rec.message for rec in caplog.records)


# ============================================================
# 5. 网关返回空 → 原 prompt
# ============================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("empty_value", [None, ""])
async def test_polish_returns_original_when_gateway_returns_empty(
    mock_model_svc, mock_gateway, empty_value, caplog
):
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = empty_value

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    assert any("LLM 返回空结果" in rec.message for rec in caplog.records)


# ============================================================
# 6. provider 配置不完整 → 原 prompt
# ============================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing_field,provider_kwargs",
    [
        ("provider=None", {}),
        ("api_key_encrypted", {"api_key_encrypted": "", "base_url": "https://api.example.com"}),
        ("base_url", {"api_key_encrypted": "encrypted", "base_url": ""}),
    ],
)
async def test_polish_returns_original_when_provider_config_incomplete(
    mock_model_svc, mock_gateway, missing_field, provider_kwargs, caplog
):
    if missing_field == "provider=None":
        model = _make_model(provider=None)
    else:
        provider = _make_provider(**provider_kwargs)
        model = _make_model(provider=provider)

    mock_model_svc.get_default_model.return_value = model

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_gateway.generate.assert_not_called()
    assert any("返回原提示词" in rec.message for rec in caplog.records)


# ============================================================
# 7. system prompt 包含 operation 和 model_name
# ============================================================

@pytest.mark.asyncio
async def test_polish_system_prompt_includes_operation_and_model(
    mock_model_svc, mock_gateway
):
    model = _make_model(model_name="dall-e-3-xl")
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = "polished"

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    await polisher.polish(
        "一只可爱的猫咪", user_id="user-1", target_operation="img2img"
    )

    call_kwargs = mock_gateway.generate.call_args.kwargs
    messages = call_kwargs["messages"]
    assert len(messages) == 2
    system_msg = messages[0].content

    assert messages[0].role == "system"
    assert "img2img" in system_msg
    assert "dall-e-3-xl" in system_msg
    assert "一只可爱的猫咪" in system_msg
    assert "图像生成提示词优化专家" in system_msg

    assert messages[1].role == "user"
    assert messages[1].content == "一只可爱的猫咪"
    assert call_kwargs["category"] == "text"


# ============================================================
# 8. model 缺 model_name → 原 prompt
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_model_missing_model_name(
    mock_model_svc, mock_gateway, caplog
):
    model = _make_model(model_name="")
    mock_model_svc.get_default_model.return_value = model

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_gateway.generate.assert_not_called()
    assert any("model_name" in rec.message for rec in caplog.records)


# ============================================================
# 9. 兼容 GenerationResult 返回形态
# ============================================================

@pytest.mark.asyncio
async def test_polish_accepts_generation_result(mock_model_svc, mock_gateway):
    """网关返回 GenerationResult（.content）时，提取 content 返回"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = SimpleNamespace(
        content="polished content", usage={}, model="gpt-4o"
    )

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "polished content"
