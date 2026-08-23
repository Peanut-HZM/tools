"""ImageGenService 通过 BackendRegistry 分发"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.image_gen.backends import BackendRegistry
from app.services.image_gen.base import BackendResult, IImageGenerationBackend
from app.services.image_generation_service import ImageGenService


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class _StubBackend(IImageGenerationBackend):
    def __init__(self, backend_name):
        self._name = backend_name

    async def run(self, ctx):
        return BackendResult(
            image_urls=["https://oss/1.png"],
            answer_text=f"from {self._name}",
            conversation_id="cid",
            model_used="m",
            backend=self._name,
        )


@pytest.fixture(autouse=True)
def reset_registry():
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


@pytest.mark.asyncio
async def test_dispatch_by_backend_param(db_session):
    """backend 参数决定走哪个 backend"""
    BackendRegistry.register("dify", _StubBackend("dify"))
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))

    svc = ImageGenService(
        db=db_session,
        dify_client=MagicMock(),
        quota_svc=MagicMock(),
        oss_svc=MagicMock(),
        history_svc=MagicMock(),
        degradation_svc=MagicMock(),
    )

    result_dify = await svc.chat_generate_dispatch(
        backend="dify",
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        mask_image=None,
        size="1024x1024",
        n=1,
    )
    assert result_dify.backend == "dify"

    result_selfdev = await svc.chat_generate_dispatch(
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
    assert result_selfdev.backend == "selfdev"
