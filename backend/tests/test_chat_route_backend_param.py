"""
Task 24 — /chat 路由 backend 参数测试

覆盖场景：
  1. test_chat_backend_selfdev                — backend=selfdev → 200 + resp.backend=selfdev
  2. test_chat_backend_dify                   — backend=dify    → 200 + resp.backend=dify
  3. test_chat_backend_default_selfdev        — 不传 backend → 默认 selfdev
  4. test_chat_backend_unconfigured_returns_503 — 注册表为空 → 503

注：项目 conftest.py 中暂无 `client` / `auth_headers` fixture，
本文件内自行构造（参考 tests/test_chat_route.py 的最小 TestClient 模式）。
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保 backend 目录在 sys.path（防止直接 pytest tests/... 时找不到 app）
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.base import Base
from app.services.image_gen.base import BackendResult, IImageGenerationBackend
from app.services.image_gen.backends import BackendRegistry
from app.services.image_generation_service import ImageGenService


# ============================================================
# Stub 后端
# ============================================================

class _StubBackend(IImageGenerationBackend):
    """用 name 标识自身，便于断言"""

    def __init__(self, name: str):
        self._name = name

    async def run(self, ctx):
        return BackendResult(
            image_urls=["https://oss/1.png"],
            answer_text=f"from {self._name}",
            conversation_id="cid",
            model_used="m",
            backend=self._name,
        )


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def reset_registry():
    """每个用例前后清空 BackendRegistry，避免串数据"""
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_quota():
    """mock quota_svc — reserve/commit/release 全部 no-op"""
    mock = MagicMock()
    mock.check_and_reserve = MagicMock()
    mock.commit = MagicMock()
    mock.release = MagicMock()
    return mock


@pytest.fixture
def mock_history():
    """mock history_svc — create_record 返回带 id 的 MagicMock"""
    mock = MagicMock()
    mock.create_record = MagicMock(return_value=MagicMock(id="h1"))
    return mock


@pytest.fixture
def fake_user():
    """模拟 get_current_user 返回值（id 不是合法 UUID，触发 route 内 uuid5 兜底）"""
    return {"id": "u1", "username": "test", "role": "user"}


@pytest.fixture
def client(db_session, mock_quota, mock_history, fake_user):
    """
    构建轻量 TestClient，覆盖依赖：
      - get_current_user → fake_user
      - get_image_gen_service → 真实 ImageGenService（依赖全 mock）

    使用独立的 FastAPI 子应用而非 app.main.app，避免 lifespan 副作用（监控、
    scheduler、数据库建表等）。
    """
    from app.api.dependencies import get_current_user as real_get_current_user
    from app.routes import image_generation as img_gen_module

    # 用真实 ImageGenService，所有依赖 mock；BackendRegistry 中的 stub 会被实际调用
    svc = ImageGenService(
        db=db_session,
        dify_client=MagicMock(),
        quota_svc=mock_quota,
        oss_svc=MagicMock(),
        history_svc=mock_history,
        degradation_svc=MagicMock(),
        prompt_polisher=MagicMock(),
    )

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")

    app.dependency_overrides[img_gen_module.get_current_user] = lambda: fake_user
    app.dependency_overrides[img_gen_module.get_image_gen_service] = lambda: svc
    # 真正引入 app.routes.image_generation 后也覆盖 app.api.dependencies 中同名引用
    app.dependency_overrides[real_get_current_user] = lambda: fake_user

    return TestClient(app)


@pytest.fixture
def auth_headers():
    """
    测试用 auth headers。

    注：route 内 get_current_user 已被 dependency_overrides 绕过为返回 fake_user，
    实际 JWT 不会校验；这里保留以便用例语义清晰。
    """
    return {"Authorization": "Bearer fake-token-for-test"}


# ============================================================
# 用例
# ============================================================

def test_chat_backend_selfdev(client, auth_headers):
    """backend=selfdev → 200 + resp.backend=selfdev"""
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))
    BackendRegistry.register("dify", _StubBackend("dify"))

    resp = client.post(
        "/api/image-generation/chat",
        data={"backend": "selfdev", "operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["backend"] == "selfdev"


def test_chat_backend_dify(client, auth_headers):
    """backend=dify → 200 + resp.backend=dify"""
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))
    BackendRegistry.register("dify", _StubBackend("dify"))

    resp = client.post(
        "/api/image-generation/chat",
        data={"backend": "dify", "operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["backend"] == "dify"


def test_chat_backend_default_selfdev(client, auth_headers):
    """不传 backend → 默认 selfdev"""
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))
    BackendRegistry.register("dify", _StubBackend("dify"))

    resp = client.post(
        "/api/image-generation/chat",
        data={"operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["backend"] == "selfdev"


def test_chat_backend_unconfigured_returns_503(client, auth_headers):
    """注册表为空 → 503（BackendNotConfiguredError → HTTP 503）"""
    # autouse reset_registry 已清空；此处不注册任何 backend
    resp = client.post(
        "/api/image-generation/chat",
        data={"backend": "selfdev", "operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 503, resp.text
