"""
Task 6.1 — 图像生成用户 API 路由测试

测试策略：
  - 创建独立的 FastAPI app，仅挂载 image_generation router
  - 通过 app.dependency_overrides 替换所有 Depends 工厂
  - get_db 替换为 SQLite 内存 DB session
  - get_current_user 替换为返回固定 fake user
  - get_image_gen_service / get_history_service / get_quota_service 替换为 MagicMock

覆盖 16 个用例：
  1. test_generate_requires_auth                  — 无 JWT → 401
  2. test_generate_invalid_operation             — operation=foo → 422
  3. test_generate_invalid_size                   — size=9999x9999 → 422
  4. test_generate_text2img_success               — 成功路径
  5. test_generate_img2img_with_reference         — 带 reference_image
  6. test_generate_quota_exceeded_returns_429     — 配额超限
  7. test_generate_dify_error_returns_502         — Dify 失败
  8. test_get_quota_me_returns_quota_info         — 配额查询
  9. test_get_history_list                        — 历史列表
 10. test_get_history_detail_updates_last_accessed — 访问时间刷新
 11. test_get_history_not_found_returns_404       — 记录不存在
 12. test_delete_history_calls_soft_delete        — 软删除
 13. test_get_result_refresh_url                  — 签名 URL 刷新 + 访问时间
 14. test_polish_prompt_placeholder_returns_original — 占位返回
 15. test_generate_invalid_edit_type              — upload_edit 校验 edit_type
 16. test_generate_invalid_n                      — n 范围校验
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保 backend 在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.exceptions import DifyError, QuotaExceeded, ServiceDegraded  # noqa: E712
from app.models.base import Base  # noqa: E712
from app.models.image_generation_models import ImageGenHistory  # noqa: E712
from app.services.image_gen_history_service import ImageGenHistoryService  # noqa: E712
from app.services.llm_quota_service import LLMQuotaService, QuotaInfo  # noqa: E712
from app.services.image_generation_service import GenerationResult  # noqa: E712
from app.services.image_generation_service import ImageGenService  # noqa: E712


# ============================================================
# 测试 fixture
# ============================================================

@pytest.fixture
def fake_user():
    """模拟 get_current_user 返回值"""
    return {"id": "user-1", "username": "alice", "role": "user"}


@pytest.fixture
def db_session():
    """每个测试一个干净的 SQLite 内存 DB（用于 history 端点的 detail/delete/result 真查询）"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_history_svc():
    """模拟 ImageGenHistoryService（默认 mock 所有方法）"""
    svc = MagicMock(spec=ImageGenHistoryService)
    svc.list_records = MagicMock(return_value=[])
    svc.get_record = MagicMock(return_value=None)
    svc.soft_delete = MagicMock(return_value=True)
    svc.update_last_accessed = MagicMock()
    svc.get_result_url = MagicMock(return_value="")
    return svc


@pytest.fixture
def mock_quota_svc():
    """模拟 LLMQuotaService"""
    svc = MagicMock(spec=LLMQuotaService)
    svc.get_user_quota = MagicMock(return_value=None)
    return svc


@pytest.fixture
def mock_image_gen_svc():
    """模拟 ImageGenService"""
    svc = MagicMock(spec=ImageGenService)
    svc.generate = AsyncMock()
    return svc


@pytest.fixture
def client(db_session, fake_user, mock_history_svc, mock_quota_svc, mock_image_gen_svc):
    """
    构建 TestClient，覆盖全部 Depends 工厂：
      - get_db → 内存 SQLite session
      - get_current_user → fake_user
      - get_history_service → mock_history_svc
      - get_quota_service → mock_quota_svc
      - get_image_gen_service → mock_image_gen_svc
    """
    from app.routes import image_generation as img_gen_module

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return fake_user

    app.dependency_overrides[img_gen_module.get_db] = override_get_db
    app.dependency_overrides[img_gen_module.get_current_user] = override_get_current_user
    app.dependency_overrides[img_gen_module.get_history_service] = lambda: mock_history_svc
    app.dependency_overrides[img_gen_module.get_quota_service] = lambda: mock_quota_svc
    app.dependency_overrides[img_gen_module.get_image_gen_service] = lambda: mock_image_gen_svc

    # Auth bypass（None credentials）：永远通过
    from app.api.dependencies import get_current_user as real_get_current_user
    app.dependency_overrides[real_get_current_user] = override_get_current_user

    return TestClient(app)


@pytest.fixture
def auth_headers(fake_user):
    """提供已认证的假请求头（实际上用 dependency_overrides 已绕过 JWT）"""
    return {"Authorization": "Bearer fake-token-for-test"}


# ============================================================
# 工具：生成一张 fake 历史 ORM 对象
# ============================================================

def _make_history_record(
    user_id: str = "user-1",
    operation: str = "text2img",
    history_id: str = "hist-1",
) -> ImageGenHistory:
    """构造一个 ImageGenHistory ORM 记录（不 flush）"""
    rec = ImageGenHistory(
        id=history_id,
        user_id=user_id,
        operation=operation,
        prompt="a cat",
        params={"size": "1024x1024", "n": 1},
        result_oss_key="image-gen/result/abc.png",
        model_used="doubao_seedream",
        status="success",
        duration_ms=1200,
        is_deleted=False,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    return rec


# ============================================================
# 1. 鉴权
# ============================================================

def test_generate_requires_auth():
    """无 JWT 时 generate 应返回 401"""
    from app.routes import image_generation as img_gen_module

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")
    # 不覆盖 get_current_user —— 让真实 JWT 校验失败
    test_client = TestClient(app)
    resp = test_client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat"},
    )
    assert resp.status_code == 401, resp.text


def test_polish_prompt_requires_auth():
    """polish-prompt 同样需要鉴权"""
    from app.routes import image_generation as img_gen_module

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")
    test_client = TestClient(app)
    resp = test_client.post(
        "/api/image-generation/polish-prompt",
        data={"prompt": "a cat"},
    )
    assert resp.status_code == 401


# ============================================================
# 2. 参数校验（422）
# ============================================================

def test_generate_invalid_operation(client):
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "foo", "prompt": "a cat"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    # FastAPI 返回 Pydantic 校验错误；我们的路由额外检查时才会返回 detail["error"] == "invalid_operation"
    # 这里只是 form 字段校验
    assert "detail" in body


def test_generate_invalid_size(client):
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat", "size": "9999x9999"},
    )
    # 我们的路由会在 operation 校验通过后立刻校验 size，返回 detail 含 invalid_size
    assert resp.status_code == 422, resp.text
    # detail 可能是 HTTPException detail
    detail = resp.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("error") == "invalid_size"


def test_generate_invalid_edit_type(client):
    """upload_edit 缺少 edit_type → 422"""
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "upload_edit", "prompt": "a cat"},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("error") == "invalid_edit_type"


def test_generate_invalid_n(client):
    """n 超过 MAX_N_IMAGES → 422"""
    from app.utils.image_gen_constants import MAX_N_IMAGES

    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat", "n": str(MAX_N_IMAGES + 1)},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("error") == "invalid_n"


# ============================================================
# 3. 成功路径
# ============================================================

def test_generate_text2img_success(client, mock_image_gen_svc):
    mock_image_gen_svc.generate = AsyncMock(
        return_value=GenerationResult(
            history_id="hist-1",
            image_urls=["https://oss.example.com/result.png"],
            model_used="doubao_seedream",
            duration_ms=1234,
            operation="text2img",
            prompt="a cat",
        )
    )

    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["history_id"] == "hist-1"
    assert body["image_urls"] == ["https://oss.example.com/result.png"]
    assert body["model_used"] == "doubao_seedream"
    assert body["duration_ms"] == 1234
    assert body["operation"] == "text2img"
    assert body["prompt"] == "a cat"
    # 验证 service.generate 被以正确参数调用
    mock_image_gen_svc.generate.assert_awaited_once()
    kwargs = mock_image_gen_svc.generate.await_args.kwargs
    assert kwargs["user_id"] == "user-1"
    assert kwargs["operation"] == "text2img"
    assert kwargs["prompt"] == "a cat"


def test_generate_img2img_with_reference(client, mock_image_gen_svc):
    """带 reference_image 时应读取并传入 bytes"""
    mock_image_gen_svc.generate = AsyncMock(
        return_value=GenerationResult(
            history_id="hist-2",
            image_urls=["url1"],
            model_used="qwen_image",
            duration_ms=500,
            operation="img2img",
            prompt="p",
        )
    )

    # 1x1 PNG
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x05"
        b"\xfe\x02\xfe\xa6\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "img2img", "prompt": "p"},
        files={"reference_image": ("ref.png", tiny_png, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    kwargs = mock_image_gen_svc.generate.await_args.kwargs
    assert kwargs["reference_image_bytes"] == tiny_png
    assert kwargs["mask_bytes"] is None


# ============================================================
# 4. 错误映射（429 / 502）
# ============================================================

def test_generate_quota_exceeded_returns_429(client, mock_image_gen_svc):
    mock_image_gen_svc.generate = AsyncMock(side_effect=QuotaExceeded("daily_limit_exceeded"))
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat"},
    )
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert body["detail"]["error"] == "quota_exceeded"
    assert body["detail"]["reason"] == "daily_limit_exceeded"


def test_generate_dify_error_returns_502(client, mock_image_gen_svc):
    mock_image_gen_svc.generate = AsyncMock(side_effect=DifyError("workflow failed", kind="workflow_failed"))
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat"},
    )
    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body["detail"]["error"] == "dify_error"
    assert body["detail"]["kind"] == "workflow_failed"
    assert body["detail"]["message"] == "workflow failed"


def test_generate_service_degraded_returns_503(client, mock_image_gen_svc):
    mock_image_gen_svc.generate = AsyncMock(side_effect=ServiceDegraded())
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "text2img", "prompt": "a cat"},
    )
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["detail"]["error"] == "service_degraded"


# ============================================================
# 5. 配额查询
# ============================================================

def test_get_quota_me_returns_quota_info(client, mock_quota_svc):
    mock_quota_svc.get_user_quota = MagicMock(
        return_value=QuotaInfo(
            user_id="user-1",
            quota_mode="image_gen",
            daily_limit=20,
            daily_used=5,
            daily_remaining=15,
            monthly_limit=300,
            monthly_used=10,
            monthly_remaining=290,
            token_period=None,
            token_limit=None,
            token_used=0,
            token_remaining=0,
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            valid_until=None,
            is_valid=True,
            granted_by="admin",
            notes="default",
        )
    )
    resp = client.get("/api/image-generation/quota/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_id"] == "user-1"
    assert body["daily_limit"] == 20
    assert body["daily_remaining"] == 15
    assert body["is_valid"] is True
    assert body["valid_from"].startswith("2026-01-01")  # isoformat


def test_get_quota_me_not_found(client, mock_quota_svc):
    mock_quota_svc.get_user_quota = MagicMock(return_value=None)
    resp = client.get("/api/image-generation/quota/me")
    assert resp.status_code == 404


# ============================================================
# 6. 历史列表
# ============================================================

def test_get_history_list(client, mock_history_svc):
    mock_history_svc.list_records = MagicMock(return_value=[
        _make_history_record(history_id="h1"),
        _make_history_record(history_id="h2", operation="img2img"),
    ])
    resp = client.get("/api/image-generation/history?skip=0&limit=10")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["skip"] == 0
    assert body["limit"] == 10
    assert body["count"] == 2
    assert len(body["items"]) == 2
    mock_history_svc.list_records.assert_called_once_with(
        user_id="user-1", skip=0, limit=10, operation=None,
    )


def test_get_history_list_with_operation_filter(client, mock_history_svc):
    mock_history_svc.list_records = MagicMock(return_value=[])
    resp = client.get("/api/image-generation/history?operation=img2img")
    assert resp.status_code == 200
    mock_history_svc.list_records.assert_called_once_with(
        user_id="user-1", skip=0, limit=20, operation="img2img",
    )


# ============================================================
# 7. 历史详情 + last_accessed
# ============================================================

def test_get_history_detail_updates_last_accessed(client, mock_history_svc):
    rec = _make_history_record(history_id="h1")
    mock_history_svc.get_record = MagicMock(return_value=rec)
    resp = client.get("/api/image-generation/history/h1")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == "h1"
    mock_history_svc.update_last_accessed.assert_called_once_with(history_id="h1")


def test_get_history_not_found_returns_404(client, mock_history_svc):
    mock_history_svc.get_record = MagicMock(return_value=None)
    # 跨用户记录也用 None 模拟：mock db 查询也返回 None
    from app.models.image_generation_models import ImageGenHistory

    fake_db = MagicMock()
    fake_chain = MagicMock()
    fake_chain.filter.return_value.first.return_value = None
    fake_db.query.return_value = fake_chain
    mock_history_svc.db = fake_db

    resp = client.get("/api/image-generation/history/missing-id")
    assert resp.status_code == 404


def test_get_history_forbidden_for_other_user(client, mock_history_svc):
    """其他用户的记录 → 403"""
    mock_history_svc.get_record = MagicMock(return_value=None)
    other_user_record = _make_history_record(user_id="user-99", history_id="h1")
    from app.models.image_generation_models import ImageGenHistory

    fake_db = MagicMock()
    fake_chain = MagicMock()
    fake_chain.filter.return_value.first.return_value = other_user_record
    fake_db.query.return_value = fake_chain
    mock_history_svc.db = fake_db

    resp = client.get("/api/image-generation/history/h1")
    assert resp.status_code == 403


# ============================================================
# 8. 软删除
# ============================================================

def test_delete_history_calls_soft_delete(client, mock_history_svc):
    mock_history_svc.soft_delete = MagicMock(return_value=True)
    resp = client.delete("/api/image-generation/history/h1")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["history_id"] == "h1"
    mock_history_svc.soft_delete.assert_called_once_with(
        user_id="user-1", history_id="h1",
    )


def test_delete_history_not_found_returns_404(client, mock_history_svc):
    mock_history_svc.soft_delete = MagicMock(return_value=False)
    fake_db = MagicMock()
    fake_chain = MagicMock()
    fake_chain.filter.return_value.first.return_value = None
    fake_db.query.return_value = fake_chain
    mock_history_svc.db = fake_db

    resp = client.delete("/api/image-generation/history/missing")
    assert resp.status_code == 404


# ============================================================
# 9. 结果 URL 刷新
# ============================================================

def test_get_result_refresh_url(client, mock_history_svc):
    rec = _make_history_record(history_id="h1")
    rec.result_oss_key = "image-gen/result/abc.png"
    mock_history_svc.get_record = MagicMock(return_value=rec)
    mock_history_svc.get_result_url = MagicMock(return_value="https://signed-url.example.com/abc.png?Expires=...&Signature=...")

    resp = client.get("/api/image-generation/result/h1")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["history_id"] == "h1"
    assert body["status"] == "success"
    assert body["result_url"].startswith("https://signed-url.example.com/")
    # 验证 last_accessed 被刷新
    mock_history_svc.update_last_accessed.assert_called_once_with(history_id="h1")


def test_get_result_not_found_returns_404(client, mock_history_svc):
    mock_history_svc.get_record = MagicMock(return_value=None)
    fake_db = MagicMock()
    fake_chain = MagicMock()
    fake_chain.filter.return_value.first.return_value = None
    fake_db.query.return_value = fake_chain
    mock_history_svc.db = fake_db

    resp = client.get("/api/image-generation/result/missing")
    assert resp.status_code == 404


# ============================================================
# 10. 提示词润色（占位）
# ============================================================

def test_polish_prompt_placeholder_returns_original(client):
    resp = client.post(
        "/api/image-generation/polish-prompt",
        data={"prompt": "a cat", "operation": "text2img"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["polished_prompt"] == "a cat"
    assert body["was_polished"] is False


# ============================================================
# 11. 上传非图像文件 → 422
# ============================================================

def test_generate_invalid_file_type(client):
    """上传 text/plain 文件到 reference_image → 422"""
    resp = client.post(
        "/api/image-generation/generate",
        data={"operation": "img2img", "prompt": "p"},
        files={"reference_image": ("ref.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    detail = body.get("detail")
    if isinstance(detail, dict):
        assert detail.get("error") == "invalid_file_type"