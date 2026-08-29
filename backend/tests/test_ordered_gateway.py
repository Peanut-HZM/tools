"""OrderedLLMGateway 测试

覆盖范围：
  ✓ priority ASC 排序
  ✓ 第一个模型成功直接返回
  ✓ RecoverableFailure 跳过，用下一个
  ✓ UnrecoverableFailure 立即抛出
  ✓ 全部 RecoverableFailure → AllModelsUnavailableError
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.base import Base  # noqa: E402
from app.services.llm.exceptions import (  # noqa: E402
    AllModelsUnavailableError,
    RecoverableFailure,
    UnrecoverableFailure,
)
from app.services.llm.ordered_gateway import OrderedLLMGateway  # noqa: E402


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ============================================================
# Helpers
# ============================================================


def _make_model(model_id, priority):
    m = MagicMock()
    m.id = model_id
    m.priority = priority
    m.category = "chat"
    m.is_active = True
    m.request_params = "{}"
    m.model_name = "test-model"
    m.provider = MagicMock()
    m.provider.provider_type = "openai"
    m.provider.base_url = "https://api.openai.com/v1"
    m.provider.api_key_encrypted = "dummy"
    m.provider.is_active = True
    return m


# ============================================================
# Tests
# ============================================================


@pytest.mark.asyncio
async def test_priority_ordering(db_session):
    """按 priority ASC 迭代"""
    models = [_make_model("m1", 50), _make_model("m2", 10), _make_model("m3", 100)]

    gw = OrderedLLMGateway(db=db_session)
    ordered = gw._ordered(models)
    assert [m.id for m in ordered] == ["m2", "m1", "m3"]


@pytest.mark.asyncio
async def test_first_success_wins(db_session):
    """第一个模型成功就返回"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.get_provider") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        mock_adapter = AsyncMock()
        mock_adapter.generate = AsyncMock(return_value="hello")
        mock_factory.return_value = mock_adapter

        gw = OrderedLLMGateway(db=db_session)
        result = await gw.generate(
            category="chat", messages=[{"role": "user", "content": "x"}]
        )
        assert result == "hello"
        # 只调用了一次 factory（第一个就成功了）
        assert mock_factory.call_count == 1


@pytest.mark.asyncio
async def test_recoverable_skips_to_next(db_session):
    """第一个 RecoverableFailure，跳过，用第二个"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    async def fail_first(messages, **kw):
        raise RecoverableFailure("rate limit")

    async def ok_second(messages, **kw):
        return "from m2"

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.get_provider") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        adapter1 = AsyncMock()
        adapter1.generate = fail_first
        adapter2 = AsyncMock()
        adapter2.generate = ok_second
        mock_factory.side_effect = [adapter1, adapter2]

        gw = OrderedLLMGateway(db=db_session)
        result = await gw.generate(
            category="chat", messages=[{"role": "user", "content": "x"}]
        )
        assert result == "from m2"
        assert mock_factory.call_count == 2


@pytest.mark.asyncio
async def test_unrecoverable_raises_immediately(db_session):
    """UnrecoverableFailure 立即抛出，不试下一个"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    async def fail_first(messages, **kw):
        raise UnrecoverableFailure("invalid api key")

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.get_provider") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        adapter = AsyncMock()
        adapter.generate = fail_first
        mock_factory.return_value = adapter

        gw = OrderedLLMGateway(db=db_session)
        with pytest.raises(UnrecoverableFailure):
            await gw.generate(
                category="chat", messages=[{"role": "user", "content": "x"}]
            )
        # 只调用了一次（Unrecoverable 不继续）
        assert mock_factory.call_count == 1


@pytest.mark.asyncio
async def test_all_fail_raises_all_unavailable(db_session):
    """全部 RecoverableFailure → AllModelsUnavailableError"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    async def fail_all(messages, **kw):
        raise RecoverableFailure("rate limit")

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.get_provider") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        adapter = AsyncMock()
        adapter.generate = fail_all
        mock_factory.return_value = adapter

        gw = OrderedLLMGateway(db=db_session)
        with pytest.raises(AllModelsUnavailableError) as exc_info:
            await gw.generate(
                category="chat", messages=[{"role": "user", "content": "x"}]
            )
        # failures 记录了两个模型
        assert len(exc_info.value.failures) == 2


@pytest.mark.asyncio
async def test_empty_models_raises(db_session):
    """category 下无模型 → AllModelsUnavailableError"""
    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=[]):
        gw = OrderedLLMGateway(db=db_session)
        with pytest.raises(AllModelsUnavailableError):
            await gw.generate(category="chat")


@pytest.mark.asyncio
async def test_image_gen_category_raises_unrecoverable(db_session):
    """image_gen 分类不再通过本网关，直接抛 UnrecoverableFailure"""
    from app.services.llm.exceptions import UnrecoverableFailure

    models = [_make_model("img1", 10)]

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.get_provider") as mock_text_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        gw = OrderedLLMGateway(db=db_session)
        with pytest.raises(UnrecoverableFailure):
            await gw.generate(
                category="image_gen", prompt="a cute cat"
            )
        mock_text_factory.assert_not_called()
