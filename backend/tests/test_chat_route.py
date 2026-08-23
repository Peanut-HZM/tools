"""
Task 7 — /chat 端点测试

覆盖场景：
  1. test_chat_endpoint_returns_asking_status  — 追问时返回 status=asking
  2. test_chat_endpoint_returns_generated_status — 生成完成时返回 status=generated
  3. test_chat_endpoint_invalid_operation        — operation 非法 → 422
  4. test_chat_endpoint_requires_auth            — 无 JWT → 401
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 确保 backend 在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.dify_client import ChatRunResult  # noqa: E712
from app.services.image_generation_service import ImageGenService  # noqa: E712


# ============================================================
# 测试 fixture
# ============================================================

@pytest.fixture
def fake_user():
    """模拟 get_current_user 返回值"""
    return {"id": "u1", "username": "test", "role": "user"}


@pytest.fixture
def mock_image_gen_svc():
    """模拟 ImageGenService"""
    svc = MagicMock(spec=ImageGenService)
    svc.chat_generate = AsyncMock()
    return svc


@pytest.fixture
def client(fake_user, mock_image_gen_svc):
    """
    构建 TestClient，覆盖 Depends 工厂：
      - get_db → 使用默认依赖
      - get_current_user → fake_user
      - get_image_gen_service → mock_image_gen_svc
    """
    from app.routes import image_generation as img_gen_module

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")

    def override_get_current_user():
        return fake_user

    app.dependency_overrides[img_gen_module.get_current_user] = override_get_current_user
    app.dependency_overrides[img_gen_module.get_image_gen_service] = lambda: mock_image_gen_svc

    # Auth bypass
    from app.api.dependencies import get_current_user as real_get_current_user
    app.dependency_overrides[real_get_current_user] = override_get_current_user

    return TestClient(app)


# ============================================================
# 用例
# ============================================================

def test_chat_endpoint_returns_asking_status(client, mock_image_gen_svc):
    """追问时返回 status=asking"""
    fake_result = ChatRunResult(
        conversation_id="conv-1",
        answer="你想要什么风格？",
    )
    mock_image_gen_svc.chat_generate = AsyncMock(return_value=fake_result)

    resp = client.post(
        "/api/image-generation/chat",
        data={
            "operation": "text2img",
            "prompt": "一只猫",
            "size": "1024x1024",
            "n": "1",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "asking"
    assert body["conversation_id"] == "conv-1"
    assert body["answer"] == "你想要什么风格？"
    assert "image_urls" not in body or body["image_urls"] == []


def test_chat_endpoint_returns_generated_status(client, mock_image_gen_svc):
    """生成完成时返回 status=generated + image_urls + history_id"""
    fake_result = ChatRunResult(
        conversation_id="conv-1",
        answer="好的，<<GENERATE>> 已为您生成。",
        image_urls=["https://oss.example.com/result.png"],
        model_used="doubao_seedream",
        polish_prompt="A cute cat",
        history_id="hist-1",
    )
    mock_image_gen_svc.chat_generate = AsyncMock(return_value=fake_result)

    resp = client.post(
        "/api/image-generation/chat",
        data={
            "operation": "text2img",
            "prompt": "一只猫",
            "size": "1024x1024",
            "n": "1",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "generated"
    assert body["conversation_id"] == "conv-1"
    assert body["answer"] == "好的，<<GENERATE>> 已为您生成。"
    assert body["image_urls"] == ["https://oss.example.com/result.png"]
    assert body["history_id"] == "hist-1"


def test_chat_endpoint_invalid_operation(client):
    """operation 非法 → 422"""
    resp = client.post(
        "/api/image-generation/chat",
        data={"operation": "foo", "prompt": "一只猫"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    detail = body.get("detail")
    if isinstance(detail, dict):
        assert detail.get("error") == "invalid_operation"


def test_chat_endpoint_requires_auth():
    """无 JWT 时 chat 应返回 401"""
    from app.routes import image_generation as img_gen_module

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")
    # 不覆盖 get_current_user —— 让真实 JWT 校验失败
    test_client = TestClient(app)
    resp = test_client.post(
        "/api/image-generation/chat",
        data={"operation": "text2img", "prompt": "一只猫"},
    )
    assert resp.status_code == 401, resp.text