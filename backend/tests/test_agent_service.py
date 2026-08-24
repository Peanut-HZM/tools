"""
Task 14 — agent_service 迁移 OrderedLLMGateway 单元测试

覆盖范围：
  1. test_default_path_uses_gateway_chat_category — 默认路径走网关（chat 分类），返回 .content
  2. test_default_path_messages_include_system_history_user — 消息结构：system + history + user
  3. test_default_path_no_models_returns_config_message — chat 分类无模型 → 「尚未配置」提示
  4. test_default_path_all_models_failed_returns_unavailable — 全部失败 → 「暂时不可用」提示
  5. test_default_path_gateway_unexpected_error — 未知异常 → 「暂时不可用」提示（不冒泡）
  6. test_specified_model_called_directly — 显式 llm_config_id → 直接调用该模型（不走网关）
  7. test_specified_model_not_found_falls_back_to_gateway — 指定模型不存在 → 降级走网关
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.agent_service import generate_agent_response
from app.services.llm.base import GenerationResult
from app.services.llm.exceptions import AllModelsUnavailableError

MODULE = "app.services.agent_service"


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_msg_service():
    """模拟 MessageService：返回一段历史对话"""
    with patch(f"{MODULE}.MessageService") as cls:
        instance = MagicMock()
        instance.build_context.return_value = [
            {"role": "user", "content": "历史问题"},
            {"role": "assistant", "content": "历史回答"},
        ]
        cls.return_value = instance
        yield instance


@pytest.fixture
def mock_gateway_cls():
    """模拟 OrderedLLMGateway 类，返回可控实例"""
    with patch(f"{MODULE}.OrderedLLMGateway") as cls:
        instance = MagicMock()
        instance.generate = AsyncMock()
        cls.return_value = instance
        yield cls


def _gen_result(content: str) -> GenerationResult:
    """构造 GenerationResult"""
    return GenerationResult(
        content=content,
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        model="test-model",
    )


def _make_specified_model(model_name: str = "gpt-4o"):
    """构造显式指定的 mock LLMModel（含 provider）"""
    provider = SimpleNamespace(
        provider_type="openai",
        base_url="https://api.example.com/v1",
        api_key_encrypted="encrypted-key",
    )
    return SimpleNamespace(
        id="specified-model-id",
        name="Specified Model",
        model_name=model_name,
        provider=provider,
        request_params=json.dumps({"temperature": 0.3}),
    )


def _db_with_specified_model(model):
    """构造 db mock：query().options().filter().first() 返回指定模型"""
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.first.return_value = model
    return db


# ============================================================
# 1. 默认路径：走网关（chat 分类）
# ============================================================

@pytest.mark.asyncio
async def test_default_path_uses_gateway_chat_category(mock_msg_service, mock_gateway_cls):
    """未指定模型 → OrderedLLMGateway.generate(category='chat')，返回 .content"""
    gateway = mock_gateway_cls.return_value
    gateway.generate.return_value = _gen_result("你好，我是产品经理助手")

    result = await generate_agent_response(
        db=MagicMock(), conversation_id="conv-1", user_message="你好"
    )

    assert result == "你好，我是产品经理助手"
    mock_gateway_cls.assert_called_once()
    gateway.generate.assert_called_once()
    assert gateway.generate.call_args.kwargs["category"] == "text"


# ============================================================
# 2. 消息结构：system + history + user
# ============================================================

@pytest.mark.asyncio
async def test_default_path_messages_include_system_history_user(
    mock_msg_service, mock_gateway_cls
):
    """传给网关的 messages = 系统提示 + 历史对话 + 当前用户消息"""
    gateway = mock_gateway_cls.return_value
    gateway.generate.return_value = _gen_result("ok")

    await generate_agent_response(
        db=MagicMock(), conversation_id="conv-1", user_message="帮我写 PRD"
    )

    messages = gateway.generate.call_args.kwargs["messages"]
    assert messages[0].role == "system"
    assert "产品经理助手" in messages[0].content
    assert messages[1].role == "user"
    assert messages[1].content == "历史问题"
    assert messages[2].role == "assistant"
    assert messages[2].content == "历史回答"
    assert messages[-1].role == "user"
    assert messages[-1].content == "帮我写 PRD"
    # 历史按最近 10 条构建
    mock_msg_service.build_context.assert_called_once_with("conv-1", max_messages=10)


# ============================================================
# 3. 无模型：尚未配置提示
# ============================================================

@pytest.mark.asyncio
async def test_default_path_no_models_returns_config_message(
    mock_msg_service, mock_gateway_cls
):
    """chat 分类下无任何模型（failures 为空）→ 返回「尚未配置」提示"""
    gateway = mock_gateway_cls.return_value
    gateway.generate.side_effect = AllModelsUnavailableError([])

    result = await generate_agent_response(
        db=MagicMock(), conversation_id="conv-1", user_message="你好"
    )

    assert result == "抱歉，系统尚未配置 AI 模型，请联系管理员配置。"


# ============================================================
# 4. 全部模型失败：暂时不可用提示
# ============================================================

@pytest.mark.asyncio
async def test_default_path_all_models_failed_returns_unavailable(
    mock_msg_service, mock_gateway_cls
):
    """有模型但全部失败（failures 非空）→ 返回「暂时不可用」提示"""
    gateway = mock_gateway_cls.return_value
    gateway.generate.side_effect = AllModelsUnavailableError([("m1", "down")])

    result = await generate_agent_response(
        db=MagicMock(), conversation_id="conv-1", user_message="你好"
    )

    assert "AI 服务暂时不可用" in result


# ============================================================
# 5. 未知异常：友好提示，不冒泡
# ============================================================

@pytest.mark.asyncio
async def test_default_path_gateway_unexpected_error(mock_msg_service, mock_gateway_cls):
    """网关抛出未知异常 → 返回友好提示，不向上冒泡"""
    gateway = mock_gateway_cls.return_value
    gateway.generate.side_effect = RuntimeError("boom")

    result = await generate_agent_response(
        db=MagicMock(), conversation_id="conv-1", user_message="你好"
    )

    assert "AI 服务暂时不可用" in result
    assert "boom" in result


# ============================================================
# 6. 显式指定模型：直接调用，不走网关
# ============================================================

@pytest.mark.asyncio
async def test_specified_model_called_directly(mock_msg_service):
    """指定 llm_config_id 且模型存在 → 直接调用该模型，不实例化网关"""
    model = _make_specified_model()
    db = _db_with_specified_model(model)

    fake_adapter = MagicMock()
    fake_adapter.generate = AsyncMock(return_value=_gen_result("direct-ok"))

    with patch(f"{MODULE}.get_provider", return_value=fake_adapter) as mock_gp, \
         patch(f"{MODULE}.decrypt_api_key", return_value="sk-plain") as mock_dk, \
         patch(f"{MODULE}.OrderedLLMGateway") as mock_gw_cls:
        result = await generate_agent_response(
            db=db,
            conversation_id="conv-1",
            user_message="你好",
            llm_config_id="specified-model-id",
        )

    assert result == "direct-ok"
    # api_key 解密 + provider 构造参数正确
    mock_dk.assert_called_once_with("encrypted-key")
    call_kwargs = mock_gp.call_args.kwargs
    assert call_kwargs["provider_type"] == "openai"
    assert call_kwargs["base_url"] == "https://api.example.com/v1"
    assert call_kwargs["model"] == "gpt-4o"
    # request_params 被解析并展开
    assert call_kwargs["temperature"] == 0.3
    # 网关未被使用
    mock_gw_cls.assert_not_called()


# ============================================================
# 7. 指定模型不存在：降级走网关
# ============================================================

@pytest.mark.asyncio
async def test_specified_model_not_found_falls_back_to_gateway(
    mock_msg_service, mock_gateway_cls
):
    """指定模型查不到 → 降级到 OrderedLLMGateway(chat)"""
    db = _db_with_specified_model(None)  # first() 返回 None
    gateway = mock_gateway_cls.return_value
    gateway.generate.return_value = _gen_result("gateway-ok")

    result = await generate_agent_response(
        db=db,
        conversation_id="conv-1",
        user_message="你好",
        llm_config_id="missing-model-id",
    )

    assert result == "gateway-ok"
    gateway.generate.assert_called_once()
    assert gateway.generate.call_args.kwargs["category"] == "text"
