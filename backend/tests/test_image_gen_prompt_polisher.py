"""
Task 8.1 / Task 14 — ImageGenPromptPolisher 单元测试

Task 14 起润色器迁移到 OrderedLLMGateway，本文件改为 mock 网关，
行为覆盖与迁移前保持一致：

  1. test_polish_returns_optimized_prompt — 成功路径返回润色后内容
  2. test_polish_uses_image_polish_category_first — 优先选 image_polish 类别
  3. test_polish_falls_back_to_chat_when_no_image_polish_model — 兜底 chat 类别
  4. test_polish_returns_original_when_no_model_found — 两类都无 → 原 prompt + warning
  5. test_polish_returns_original_when_gateway_fails — 网关抛异常 → 原 prompt + warning
  6. test_polish_returns_original_when_gateway_returns_empty — 返回 None/"" → 原 prompt
  7. test_polish_returns_original_when_provider_config_incomplete — provider 字段缺失 → 原 prompt
  8. test_polish_system_prompt_includes_operation_and_model — 验证 system_msg 包含 operation 和 model_name
  9. test_polish_returns_original_when_model_missing_model_name — model 缺 model_name → 原 prompt
  10. test_polish_cross_category_fallback_on_all_unavailable — image_polish 链全失败 → 降级 chat
  11. test_polish_accepts_generation_result — 兼容 GenerationResult（.content）返回形态
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
from app.services.llm.exceptions import AllModelsUnavailableError


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
def mock_gateway():
    """模拟 OrderedLLMGateway"""
    gw = AsyncMock()
    gw.generate = AsyncMock()
    return gw


def _build_polisher(mock_model_svc, mock_gateway) -> ImageGenPromptPolisher:
    """构建 ImageGenPromptPolisher，注入 mock 依赖"""
    # 直接构造，绕过 __init__ 中的真实 LLMModelService 实例化
    polisher = ImageGenPromptPolisher.__new__(ImageGenPromptPolisher)
    polisher._db = MagicMock()
    polisher._model_svc = mock_model_svc
    polisher._gateway = mock_gateway
    return polisher


# ============================================================
# 1. 成功路径：返回润色后的 prompt
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_optimized_prompt(mock_model_svc, mock_gateway):
    """正常路径：image_polish 模型存在 → 调用网关 → 返回润色后的内容"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = (
        "a majestic cat sitting on a windowsill, golden hour lighting"
    )

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("一只可爱的猫", user_id="user-1")

    assert result == "a majestic cat sitting on a windowsill, golden hour lighting"
    mock_model_svc.get_default_model.assert_called_once_with(category="image_polish")
    mock_gateway.generate.assert_called_once()


# ============================================================
# 2. 优先选 image_polish 类别
# ============================================================

@pytest.mark.asyncio
async def test_polish_uses_image_polish_category_first(mock_model_svc, mock_gateway):
    """image_polish 存在时，不调用 chat 类别"""
    polish_model = _make_model(category="image_polish", model_name="dalle-3")
    mock_model_svc.get_default_model.return_value = polish_model
    mock_gateway.generate.return_value = "polished prompt"

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "polished prompt"
    # 只调用一次 get_default_model（image_polish 命中，不查 chat）
    mock_model_svc.get_default_model.assert_called_once_with(category="image_polish")
    # 验证网关走 image_polish 分类
    call_kwargs = mock_gateway.generate.call_args.kwargs
    assert call_kwargs["category"] == "image_polish"


# ============================================================
# 3. image_polish 缺失 → 兜底 chat
# ============================================================

@pytest.mark.asyncio
async def test_polish_falls_back_to_chat_when_no_image_polish_model(
    mock_model_svc, mock_gateway
):
    """image_polish 类别无默认 → 查 chat 类别"""
    chat_model = _make_model(category="chat", model_name="gpt-4o", model_id="chat-model-id")
    # 第一次（image_polish）返回 None，第二次（chat）返回 chat_model
    mock_model_svc.get_default_model.side_effect = [None, chat_model]
    mock_gateway.generate.return_value = "chat-fallback polish"

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "chat-fallback polish"
    assert mock_model_svc.get_default_model.call_count == 2
    mock_model_svc.get_default_model.assert_any_call(category="image_polish")
    mock_model_svc.get_default_model.assert_any_call(category="chat")
    # 网关走 chat 分类
    call_kwargs = mock_gateway.generate.call_args.kwargs
    assert call_kwargs["category"] == "chat"


# ============================================================
# 4. 两个类别都无默认 → 原 prompt + warning
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_no_model_found(
    mock_model_svc, mock_gateway, caplog
):
    """image_polish + chat 均无默认 → 返回原 prompt，记 warning"""
    mock_model_svc.get_default_model.side_effect = [None, None]

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_gateway.generate.assert_not_called()
    # 验证 warning 日志
    assert any("无可用默认模型" in rec.message for rec in caplog.records)


# ============================================================
# 5. 网关抛异常 → 原 prompt + warning
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_gateway_fails(
    mock_model_svc, mock_gateway, caplog
):
    """OrderedLLMGateway 抛异常 → 不冒泡，返回原 prompt + warning"""
    model = _make_model(category="chat")
    # 直接命中 chat 分类，避免 image_polish → chat 的二次重试干扰
    mock_model_svc.get_default_model.side_effect = [None, model]
    mock_gateway.generate.side_effect = RuntimeError("LLM service down")

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    assert any("润色失败" in rec.message for rec in caplog.records)


# ============================================================
# 6. 网关返回 None / 空字符串 → 原 prompt
# ============================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("empty_value", [None, ""])
async def test_polish_returns_original_when_gateway_returns_empty(
    mock_model_svc, mock_gateway, empty_value, caplog
):
    """LLM 返回 None 或空字符串 → 返回原 prompt + warning"""
    model = _make_model()
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = empty_value

    polisher = _build_polisher(mock_model_svc, mock_gateway)

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
    mock_gateway,
    missing_field,
    provider_kwargs,
    caplog,
):
    """provider 字段缺失 → 返回原 prompt + warning，不调网关"""
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
# 8. system prompt 包含 operation 和 model_name
# ============================================================

@pytest.mark.asyncio
async def test_polish_system_prompt_includes_operation_and_model(
    mock_model_svc, mock_gateway
):
    """验证构造的 system_msg 包含 target_operation 和 model.model_name"""
    model = _make_model(model_name="dall-e-3-xl")
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.return_value = "polished"

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    await polisher.polish(
        "一只可爱的猫咪", user_id="user-1", target_operation="img2img"
    )

    # 提取传给网关的 messages
    call_kwargs = mock_gateway.generate.call_args.kwargs
    messages = call_kwargs["messages"]
    assert len(messages) == 2
    system_msg = messages[0].content

    # system_msg 必须包含：operation、model_name、原始 prompt
    assert messages[0].role == "system"
    assert "img2img" in system_msg
    assert "dall-e-3-xl" in system_msg
    assert "一只可爱的猫咪" in system_msg
    assert "图像生成提示词优化专家" in system_msg

    # 同时验证 user 消息与分类正确传递
    assert messages[1].role == "user"
    assert messages[1].content == "一只可爱的猫咪"
    assert call_kwargs["category"] == "image_polish"


# ============================================================
# 9. model 缺 model_name → 原 prompt
# ============================================================

@pytest.mark.asyncio
async def test_polish_returns_original_when_model_missing_model_name(
    mock_model_svc, mock_gateway, caplog
):
    """model.model_name 为空 → 返回原 prompt + warning"""
    model = _make_model(model_name="")
    mock_model_svc.get_default_model.return_value = model

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    mock_gateway.generate.assert_not_called()
    assert any("model_name" in rec.message for rec in caplog.records)


# ============================================================
# 10. image_polish 兜底链整体不可用 → 降级 chat 分类
# ============================================================

@pytest.mark.asyncio
async def test_polish_cross_category_fallback_on_all_unavailable(
    mock_model_svc, mock_gateway
):
    """image_polish 链全部失败（AllModelsUnavailableError）→ 降级 chat 链重试"""
    model = _make_model(category="image_polish")
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.side_effect = [
        AllModelsUnavailableError([("m1", "down")]),
        "polished via chat",
    ]

    polisher = _build_polisher(mock_model_svc, mock_gateway)
    result = await polisher.polish("test", user_id="user-1")

    assert result == "polished via chat"
    assert mock_gateway.generate.call_count == 2
    assert mock_gateway.generate.call_args_list[0].kwargs["category"] == "image_polish"
    assert mock_gateway.generate.call_args_list[1].kwargs["category"] == "chat"


@pytest.mark.asyncio
async def test_polish_returns_original_when_both_categories_unavailable(
    mock_model_svc, mock_gateway, caplog
):
    """image_polish 与 chat 链均不可用 → 返回原 prompt + warning"""
    model = _make_model(category="image_polish")
    mock_model_svc.get_default_model.return_value = model
    mock_gateway.generate.side_effect = AllModelsUnavailableError([("m1", "down")])

    polisher = _build_polisher(mock_model_svc, mock_gateway)

    with caplog.at_level(logging.WARNING, logger="app.services.image_gen_prompt_polisher"):
        result = await polisher.polish("original prompt", user_id="user-1")

    assert result == "original prompt"
    assert any("润色失败" in rec.message for rec in caplog.records)


# ============================================================
# 11. 兼容 GenerationResult 返回形态
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
