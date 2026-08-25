"""
Task 23 — 自研路径 quota + history 测试

覆盖 chat_generate_dispatch_with_quota 的关键路径：
  ✓ image_urls 非空 → record_usage + 写 history（含 backend 字段）
  ✓ image_urls 为空 → rollback（不写 history）
  ✓ 异常 → rollback（不写 history）
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.image_gen.base import BackendResult, IImageGenerationBackend
from app.services.image_gen.backends import BackendRegistry
from app.services.image_generation_service import ImageGenService


# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------

@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def reset_registry():
    """每个用例清空 BackendRegistry，避免串数据"""
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


# ------------------------------------------------------------
# Stub 后端
# ------------------------------------------------------------

class _StubBackendWithImages(IImageGenerationBackend):
    """返回含 image_urls 的结果 → 触发 commit"""

    async def run(self, ctx):
        return BackendResult(
            image_urls=["https://oss/1.png"],
            answer_text="done",
            conversation_id="cid",
            model_used="m",
            backend="selfdev",
        )


class _StubBackendWithoutImages(IImageGenerationBackend):
    """返回空 image_urls → 触发 release"""

    async def run(self, ctx):
        return BackendResult(
            image_urls=[],
            answer_text="no images",
            conversation_id="cid2",
            model_used="m",
            backend="selfdev",
        )


class _StubBackendRaises(IImageGenerationBackend):
    """抛异常 → 触发 release"""

    async def run(self, ctx):
        raise RuntimeError("boom")


# ------------------------------------------------------------
# 辅助：构造 ImageGenService（依赖均为 mock）
# ------------------------------------------------------------

def _make_svc(db_session, quota=None, history=None):
    quota = quota or MagicMock()
    history = history or MagicMock()
    return ImageGenService(
        db=db_session,
        dify_client=MagicMock(),
        quota_svc=quota,
        oss_svc=MagicMock(),
        history_svc=history,
        degradation_svc=MagicMock(),
    ), quota, history


# ------------------------------------------------------------
# 用例
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_quota_commit_on_image_urls(db_session):
    """image_urls 非空 → commit + 写 history（含 backend 字段）"""
    BackendRegistry.register("selfdev", _StubBackendWithImages())

    svc, quota, history = _make_svc(db_session)
    quota.check_and_reserve = MagicMock(return_value="res-1")
    quota.record_usage = MagicMock()
    quota.rollback = MagicMock()
    history.create_record = MagicMock(return_value=MagicMock(id="h1"))

    await svc.chat_generate_dispatch_with_quota(
        backend="selfdev",
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        mask_image=None,
        size="1024x1024",
        n=1,
    )

    quota.check_and_reserve.assert_called_once()
    quota.record_usage.assert_called_once()
    quota.rollback.assert_not_called()
    history.create_record.assert_called_once()
    # history record 应带 backend 字段
    call_kwargs = history.create_record.call_args[1]
    assert call_kwargs["backend"] == "selfdev"


@pytest.mark.asyncio
async def test_quota_release_on_empty_image_urls(db_session):
    """image_urls 为空 → release，不 commit，不写 history"""
    BackendRegistry.register("selfdev", _StubBackendWithoutImages())

    svc, quota, history = _make_svc(db_session)
    quota.check_and_reserve = MagicMock(return_value="res-2")
    quota.record_usage = MagicMock()
    quota.rollback = MagicMock()
    history.create_record = MagicMock()

    await svc.chat_generate_dispatch_with_quota(
        backend="selfdev",
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        mask_image=None,
        size="1024x1024",
        n=1,
    )

    quota.check_and_reserve.assert_called_once()
    quota.record_usage.assert_not_called()
    quota.rollback.assert_called_once()
    history.create_record.assert_not_called()


@pytest.mark.asyncio
async def test_quota_release_on_exception(db_session):
    """后端抛异常 → release，不 commit，不写 history"""
    BackendRegistry.register("selfdev", _StubBackendRaises())

    svc, quota, history = _make_svc(db_session)
    quota.check_and_reserve = MagicMock(return_value="res-3")
    quota.record_usage = MagicMock()
    quota.rollback = MagicMock()
    history.create_record = MagicMock()

    with pytest.raises(RuntimeError, match="boom"):
        await svc.chat_generate_dispatch_with_quota(
            backend="selfdev",
            user_id=uuid.uuid4(),
            operation="text2img",
            query="a cat",
            conversation_id=None,
            reference_image=None,
            mask_image=None,
            size="1024x1024",
            n=1,
        )

    quota.check_and_reserve.assert_called_once()
    quota.record_usage.assert_not_called()
    quota.rollback.assert_called_once()
    history.create_record.assert_not_called()
