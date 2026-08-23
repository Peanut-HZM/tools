"""
Task 1.5.2 — 验证 3 个消费方（llm_fallback / agent_service / chat_stream）
从 LLMConfig 迁移到 LLMModel + LLMProvider 的行为正确性。

覆盖范围（明确）：
  ✓ _parse_request_params 辅助函数：Text → dict 的所有分支
  ✓ LLMFallbackService._get_available_models：活跃过滤 + 默认优先 + 主模型置顶
  ✓ agent_service._get_default_model：返回 is_default + is_active 的模型
  ✓ chat_stream._get_default_model：同上（两个模块各自定义）
  ✓ 完整 fallback 路径端到端：decrypt_api_key + get_provider 调用（用 mock 验证参数传递）
  ✓ LLMProvider.is_active=False 时，关联的 LLMModel 应被过滤掉（双重 is_active）

未覆盖（诚实声明）：
  ✗ chat_stream 的 generate_stream 完整 SSE 路径（需要大量 FastAPI + provider mock，留作后续）
  ✗ agent_service.generate_agent_response 完整路径（同上）
  这两条路径通过 py_compile + 服务启动已验证无导入错误。
"""
import os
import sys
import json
import uuid
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import INET

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@compiles(INET, "sqlite")
def _compile_inet_for_sqlite(element, compiler, **kw):
    return "VARCHAR(45)"


from app.models.base import Base
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.core.security import encrypt_api_key

# 待测模块
from app.services.llm_fallback import (
    LLMFallbackService,
    _parse_request_params as fb_parse,
)
from app.services.agent_service import (
    _get_default_model as agent_get_default,
    _parse_request_params as as_parse,
)
from app.api.routes.chat_stream import (
    _get_default_model as cs_get_default,
    _parse_request_params as cs_parse,
)


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_provider(session, *, provider_type="openai", is_active=True, key_suffix="1234"):
    """创建并持久化一个 LLMProvider，返回实例"""
    provider = LLMProvider(
        id=uuid.uuid4(),
        name=f"test-{provider_type}-{key_suffix}",
        provider_type=provider_type,
        base_url="https://api.example.com/v1",
        api_key_encrypted=encrypt_api_key(f"sk-test-{key_suffix}"),
        api_key_suffix=key_suffix,
        is_active=is_active,
    )
    session.add(provider)
    session.commit()
    session.refresh(provider)
    return provider


def _seed_model(
    session,
    provider,
    *,
    name="gpt-4o",
    model_name="gpt-4o",
    is_default=False,
    is_active=True,
    request_params=None,
):
    """创建并持久化一个 LLMModel，返回实例"""
    model = LLMModel(
        id=uuid.uuid4(),
        name=name,
        model_name=model_name,
        provider_id=provider.id,
        request_params=request_params,
        category="chat",
        is_default=is_default,
        is_default_for_category=False,
        is_active=is_active,
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


# ============================================================
# 1. _parse_request_params 全分支覆盖（3 个文件各自一份）
# ============================================================

@pytest.mark.parametrize("parse_fn", [fb_parse, as_parse, cs_parse], ids=["fallback", "agent", "chat_stream"])
class TestParseRequestParams:
    def test_none(self, parse_fn):
        assert parse_fn(None) == {}

    def test_dict_passthrough(self, parse_fn):
        d = {"temperature": 0.7, "max_tokens": 100}
        assert parse_fn(d) == d

    def test_valid_json_string(self, parse_fn):
        s = '{"temperature": 0.5}'
        assert parse_fn(s) == {"temperature": 0.5}

    def test_invalid_json_string(self, parse_fn):
        assert parse_fn("not-a-json") == {}

    def test_json_string_non_dict(self, parse_fn):
        # JSON 数组不是 dict，应返回 {}
        assert parse_fn("[1, 2, 3]") == {}

    def test_empty_string(self, parse_fn):
        assert parse_fn("") == {}

    def test_unknown_type(self, parse_fn):
        # 非预期类型（int）应返回 {}
        assert parse_fn(42) == {}


# ============================================================
# 2. _get_available_models 行为
# ============================================================

class TestGetAvailableModels:
    def test_returns_only_active_models(self, db_session):
        """is_active=False 的 model 不应返回"""
        provider = _seed_provider(db_session)
        active = _seed_model(db_session, provider, name="active", model_name="m-active", is_active=True)
        _seed_model(db_session, provider, name="inactive", model_name="m-inactive", is_active=False)

        svc = LLMFallbackService(db_session)
        result = svc._get_available_models()
        assert len(result) == 1
        assert result[0].id == active.id

    def test_filters_out_inactive_provider(self, db_session):
        """provider.is_active=False 时，其下 model 应被过滤（双重 is_active）"""
        provider = _seed_provider(db_session, is_active=False)
        _seed_model(db_session, provider, name="orphan", model_name="m-orphan", is_active=True)

        svc = LLMFallbackService(db_session)
        result = svc._get_available_models()
        assert result == []

    def test_default_model_first(self, db_session):
        """is_default=True 的模型应排在列表首位"""
        provider = _seed_provider(db_session)
        # 先创建非默认
        m_normal = _seed_model(db_session, provider, name="normal", model_name="m-normal", is_default=False)
        m_default = _seed_model(db_session, provider, name="default", model_name="m-default", is_default=True)

        svc = LLMFallbackService(db_session)
        result = svc._get_available_models()
        assert len(result) == 2
        assert result[0].id == m_default.id
        assert result[1].id == m_normal.id

    def test_primary_model_promoted_to_front(self, db_session):
        """指定的 primary_model_id 应被提升到首位（即使不是 default）"""
        provider = _seed_provider(db_session)
        m_default = _seed_model(db_session, provider, name="default", model_name="m-default", is_default=True)
        m_primary = _seed_model(db_session, provider, name="primary", model_name="m-primary", is_default=False)

        svc = LLMFallbackService(db_session)
        result = svc._get_available_models(primary_model_id=str(m_primary.id))
        assert result[0].id == m_primary.id
        assert result[1].id == m_default.id

    def test_unknown_primary_ignored(self, db_session):
        """不存在的 primary_model_id 应被忽略，返回正常排序的列表"""
        provider = _seed_provider(db_session)
        m = _seed_model(db_session, provider, name="m1", model_name="m1")

        svc = LLMFallbackService(db_session)
        result = svc._get_available_models(primary_model_id=str(uuid.uuid4()))
        assert len(result) == 1
        assert result[0].id == m.id

    def test_empty_table(self, db_session):
        """无数据时返回空列表"""
        svc = LLMFallbackService(db_session)
        assert svc._get_available_models() == []


# ============================================================
# 3. _get_default_model（agent_service / chat_stream 两份）
# ============================================================

class TestGetDefaultModel:
    @pytest.mark.parametrize("get_default", [agent_get_default, cs_get_default], ids=["agent", "chat_stream"])
    def test_returns_default_active_model(self, db_session, get_default):
        provider = _seed_provider(db_session)
        default = _seed_model(db_session, provider, name="default", model_name="m-default", is_default=True)
        _seed_model(db_session, provider, name="other", model_name="m-other", is_default=False)

        result = get_default(db_session)
        assert result is not None
        assert result.id == default.id

    @pytest.mark.parametrize("get_default", [agent_get_default, cs_get_default], ids=["agent", "chat_stream"])
    def test_ignores_inactive_default(self, db_session, get_default):
        """is_default=True 但 is_active=False 的 model 不应被选为默认"""
        provider = _seed_provider(db_session)
        _seed_model(db_session, provider, name="inactive-default", model_name="m-inactive-default",
                    is_default=True, is_active=False)

        result = get_default(db_session)
        assert result is None

    @pytest.mark.parametrize("get_default", [agent_get_default, cs_get_default], ids=["agent", "chat_stream"])
    def test_ignores_default_with_inactive_provider(self, db_session, get_default):
        """provider.is_active=False 时，即使 model.is_default=True 也不应返回"""
        provider = _seed_provider(db_session, is_active=False)
        _seed_model(db_session, provider, name="orphan-default", model_name="m-orphan", is_default=True)

        result = get_default(db_session)
        assert result is None

    @pytest.mark.parametrize("get_default", [agent_get_default, cs_get_default], ids=["agent", "chat_stream"])
    def test_no_default_set(self, db_session, get_default):
        """没有任何 default 时返回 None"""
        provider = _seed_provider(db_session)
        _seed_model(db_session, provider, name="m1", model_name="m1", is_default=False)

        result = get_default(db_session)
        assert result is None


# ============================================================
# 4. 端到端 fallback 路径（mock 真实 provider 调用）
# ============================================================

class TestFallbackEndToEnd:
    @pytest.mark.asyncio
    async def test_generate_with_fallback_decrypts_and_calls_provider(self, db_session):
        """
        验证 generate_with_fallback：
        - 正确解密 api_key
        - 以正确参数调用 get_provider
        - 调用 provider.generate 并返回结果
        """
        provider = _seed_provider(db_session, provider_type="openai", key_suffix="abcd")
        _seed_model(
            db_session, provider,
            name="test-model", model_name="gpt-4o-mini",
            is_default=True,
            request_params=json.dumps({"temperature": 0.3, "max_tokens": 100}),
        )

        svc = LLMFallbackService(db_session)

        # mock get_provider 返回假 adapter，避免真实网络调用
        fake_adapter = MagicMock()
        fake_adapter.generate = AsyncMock(return_value="hello from mock")

        with patch("app.services.llm_fallback.get_provider", return_value=fake_adapter) as mock_gp:
            result = await svc.generate_with_fallback(prompt="hi")

        assert result == "hello from mock"
        # 验证 get_provider 以正确参数被调用
        mock_gp.assert_called_once()
        call_kwargs = mock_gp.call_args.kwargs
        assert call_kwargs["provider_type"] == "openai"
        assert call_kwargs["base_url"] == "https://api.example.com/v1"
        assert call_kwargs["model"] == "gpt-4o-mini"
        # api_key 应被解密为明文
        assert call_kwargs["api_key"] == "sk-test-abcd"
        # request_params 应被解析并展开
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_with_fallback_raises_when_no_models(self, db_session):
        """空表时应抛出 ValueError"""
        svc = LLMFallbackService(db_session)
        with pytest.raises(ValueError, match="没有可用的 LLM 配置"):
            await svc.generate_with_fallback(prompt="hi")

    @pytest.mark.asyncio
    async def test_generate_with_fallback_retries_on_failure(self, db_session):
        """主模型失败时应尝试下一个（双重模型场景）"""
        provider = _seed_provider(db_session)
        m1 = _seed_model(db_session, provider, name="primary", model_name="m-primary", is_default=True)
        m2 = _seed_model(db_session, provider, name="fallback", model_name="m-fallback", is_default=False)

        svc = LLMFallbackService(db_session)

        fake_adapter = MagicMock()
        # 第一次调用抛异常，第二次成功
        fake_adapter.generate = AsyncMock(side_effect=[RuntimeError("boom"), "ok on retry"])

        with patch("app.services.llm_fallback.get_provider", return_value=fake_adapter):
            result = await svc.generate_with_fallback(prompt="hi")

        assert result == "ok on retry"
        assert fake_adapter.generate.call_count == 2
