"""
Task 8.1 — ImageGenPromptPolisher 单元测试

覆盖范围（9 个用例）：
  1. test_polish_returns_optimized_prompt — 成功路径返回润色后内容
  2. test_polish_uses_image_polish_category_first — 优先选 image_polish 类别
  3. test_polish_falls_back_to_chat_when_no_image_polish_model — 兜底 chat 类别
  4. test_polish_returns_original_when_no_model_found — 两类都无 → 原 prompt + warning
  5. test_polish_returns_original_when_fallback_fails — fallback 抛异常 → 原 prompt + warning
  6. test_polish_returns_original_when_fallback_returns_empty — fallback 返回 None/"" → 原 prompt
  7. test_polish_returns_original_when_provider_config_incomplete — provider 字段缺失 → 原 prompt
  8. test_polish_system_prompt_includes_operation_and_model — 验证 system_msg 包含 operation 和 model_name
  9. test_polish_returns_original_when_model_missing_model_name — model 缺 model_name → 原 prompt
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.image_gen_prompt_polisher import ImageGenPromptPolisher


# ============================================================
# Fixtures
# ============================================================

def _make_provider(
    api_key_encrypted: str = "encrypted-key",
    base_url: str = "https://api.example.com",
    provider_type: str = "openai",
):
    """构造 mock LLMProvider"""
    return SimpleNamespace(
        id="provider-id-1234",
        api_key_encrypted=api_key_encrypted,
        base_url=base_url,
        provider_type=provider_type,
    )


_MISSING = object()  # 哨兵：区分“未传”和“显式 None”


def _make_model(
    model_name: str = "gpt-4o",
    model_id: str = "model-id-5678",
    category: str = "image_polish",
    provider=_MISSING,
):
    """构造 mock LLMModel

    provider=_MISSING → 使用默认 mock provider；
    provider=None → 显式让 model.provider = None；
    其他值 → 使用传入的 provider。
    """
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
    """模拟 LLMModelService"""
    svc = MagicMock()
    svc.get_default_model = MagicMock()
    return svc


@pytest.fixture
def mock_fallback_svc():
    """模拟 LLMFallbackService"""
    svc = AsyncMock()
    svc.generate_with_fallback = AsyncMock()
    return svc


def _build_polisher(mock_model_svc, mock_fallback_svc) -> ImageGenPromptPolisher:
    """构建 ImageGenPromptPolisher，注入 mock 依赖"""
    # 直接构造，绕过 __init__ 中的真实 LLMModelService 实例化
    polisher = ImageGenPromptPolisher.__new__(ImageGenPromptPolisher)
    polisher._db = MagicMock()
    polisher._model_svc = mock_model_svc
    polisher._fallback_svc = mock_fallback_svc
    return polisher


# ============================================================
# 1. 成功路径：返回润色后的 prompt
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_optimized_prompt(mock_model_svc, mock_fallback_svc):
    """正常路径：image_polish 模型存在 → 调用 LLM → 返回润色后的内容"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_fallback_svc.generate_with_fallback.return_value = (
        "a majestic cat sitting on a windowsill, golden hour lighting"
    )

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)
    result = await polisher.polish("一只可爱的猫", user_id="user-1")

    assert result == "a majestic cat sitting on a windowsill, golden hour lighting"
    mock_model_svc.get_default_model.assert_called_once_with(category="image_polish")
    mock_fallback_svc.generate_with_fallback.assert_called_once()


# ============================================================
# 2. 优先选 image_polish 类别
# ============================================================

@pytest.mark.asyncio
async def test_polish_uses_image_polish_category_first(mock_model_svc, mock_fallback_svc):
    """image_polish 存在时，不调用 chat 类别"""
    polish_model = _make_model(category="image_polish", model_name="dalle-3")
    mock_model_svc.get_default_model.return_value = polish_model
    mock_fallback_svc.generate_with_fallback.return_value = "polished prompt"

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "polished prompt"
    # 只调用一次 get_default_model（image_polish 命中，不查 chat）
    mock_model_svc.get_default_model.assert_called_once_with(category="image_polish")
    # 验证 fallback 用的 model id
    call_kwargs = mock_fallback_svc.generate_with_fallback.call_args.kwargs
    assert call_kwargs["primary_config_id"] == "model-id-5678"


# ============================================================
# 3. image_polish 缺失 → 兜底 chat
# ============================================================

@pytest.mark.asyncio
async def test_polish_falls_back_to_chat_when_no_image_polish_model(
    mock_model_svc, mock_fallback_svc
):
    """image_polish 类别无默认 → 查 chat 类别"""
    chat_model = _make_model(category="chat", model_name="gpt-4o", model_id="chat-model-id")
    # 第一次（image_polish）返回 None，第二次（chat）返回 chat_model
    mock_model_svc.get_default_model.side_effect = [None, chat_model]
    mock_fallback_svc.generate_with_fallback.return_value = "chat-fallback polish"

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "chat-fallback polish"
    assert mock_model_svc.get_default_model.call_count == 2
    mock_model_svc.get_default_model.assert_any_call(category="image_polish")
    mock_model_svc.get_default_model.assert_any_call(category="chat")
    # fallback 用 chat model id
    call_kwargs = mock_fallback_svc.generate_with_fallback.call_args.kwargs
    assert call_kwargs["primary_config_id"] == "chat-model-id"


# ============================================================
# 4. 两个类别都无默认 → 原 prompt + warning
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_no_model_found(
    mock_model_svc, mock_fallback_svc, caplog
):
    """image_polish + chat 均无默认 → 返回原 prompt，记 warning"""
    mock_model_svc.get_default_model.side_effect = [None, None]

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_fallback_svc.generate_with_fallback.assert_not_called()
    # 验证 warning 日志
    assert any("无可用默认模型" in rec.message for rec in caplog.records)


# ============================================================
# 5. fallback 抛异常 → 原 prompt + warning
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_fallback_fails(
    mock_model_svc, mock_fallback_svc, caplog
):
    """LLMFallbackService 抛异常 → 不冒泡，返回原 prompt + warning"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_fallback_svc.generate_with_fallback.side_effect = RuntimeError("LLM service down")

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    assert any("润色失败" in rec.message for rec in caplog.records)


# ============================================================
# 6. fallback 返回 None / 空字符串 → 原 prompt
# ============================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("empty_value", [None, ""])
async def test_polish_returns_original_when_fallback_returns_empty(
    mock_model_svc, mock_fallback_svc, empty_value, caplog
):
    """LLM 返回 None 或空字符串 → 返回原 prompt + warning"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_fallback_svc.generate_with_fallback.return_value = empty_value

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    assert any("LLM 返回空结果" in rec.message for rec in caplog.records)


# ============================================================
# 7. provider 配置不完整 → 原 prompt
# ============================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing_field,provider_kwargs",
    [
        ("provider=None", {}),  # 特殊处理：model.provider = None
        ("api_key_encrypted", {"api_key_encrypted": "", "base_url": "https://api.example.com"}),
        ("base_url", {"api_key_encrypted": "encrypted", "base_url": ""}),
    ],
)
async def test_polish_returns_original_when_provider_config_incomplete(
    mock_model_svc,
    mock_fallback_svc,
    missing_field,
    provider_kwargs,
    caplog,
):
    """provider 字段缺失 → 返回原 prompt + warning，不调 LLM"""
    if missing_field == "provider=None":
        model = _make_model(provider=None)
    else:
        provider = _make_provider(**provider_kwargs)
        model = _make_model(provider=provider)

    mock_model_svc.get_default_model.return_value = model

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_fallback_svc.generate_with_fallback.assert_not_called()
    assert any("返回原提示词" in rec.message for rec in caplog.records)


# ============================================================
# 8. system prompt 包含 operation 和 model_name
# ============================================================

@pytest.mark.asyncio
async def test_polish_system_prompt_includes_operation_and_model(
    mock_model_svc, mock_fallback_svc
):
    """验证构造的 system_msg 包含 target_operation 和 model.model_name"""
    model = _make_model(model_name="dall-e-3-xl")
    mock_model_svc.get_default_model.return_value = model
    mock_fallback_svc.generate_with_fallback.return_value = "polished"

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)
    await polisher.polish(
        "一只可爱的猫咪", user_id="user-1", target_operation="img2img"
    )

    # 提取传给 generate_with_fallback 的 context
    call_kwargs = mock_fallback_svc.generate_with_fallback.call_args.kwargs
    context = call_kwargs["context"]
    assert len(context) == 1
    system_msg = context[0]["content"]

    # system_msg 必须包含：operation、model_name、原始 prompt
    assert "img2img" in system_msg
    assert "dall-e-3-xl" in system_msg
    assert "一只可爱的猫咪" in system_msg
    assert "图像生成提示词优化专家" in system_msg

    # 同时验证 prompt 和 primary_config_id 正确传递
    assert call_kwargs["prompt"] == "一只可爱的猫咪"
    assert call_kwargs["primary_config_id"] == "model-id-5678"


# ============================================================
# 9. model 缺 model_name → 原 prompt
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_model_missing_model_name(
    mock_model_svc, mock_fallback_svc, caplog
):
    """model.model_name 为空 → 返回原 prompt + warning"""
    model = _make_model(model_name="")
    mock_model_svc.get_default_model.return_value = model

    polisher = _build_polisher(mock_model_svc, mock_fallback_svc)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_fallback_svc.generate_with_fallback.assert_not_called()
    assert any("model_name" in rec.message for rec in caplog.records)
