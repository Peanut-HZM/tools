"""
Task 7.1 — 图像生成管理 API 测试

依赖：
  - FastAPI TestClient
  - mock ImageGenQuotaService / DifyConfigService / DifyClient
  - 注入临时 in-memory SQLite session 给 stat 聚合查询

覆盖范围（>=18 个用例）：
  鉴权 (1)
    1. test_get_users_requires_admin

  配额管理 (5)
    2. test_list_users_pagination
    3. test_grant_quota_creates_record
    4. test_grant_quota_validity_range_invalid
    5. test_grant_quota_extra_field_rejected
    6. test_revoke_quota_deletes_record
    7. test_reset_counters_zeroes_used
    8. test_get_user_quota_returns_info
    9. test_get_user_quota_404_if_missing

  Dify 配置 (3)
    10. test_get_dify_config_masks_api_key
    11. test_update_dify_config_partial_update
    12. test_update_dify_config_with_unknown_field
    13. test_test_connection_returns_sanitized_message

  降级 (2)
    14. test_get_degradation_returns_503_if_service_not_wired
    15. test_reset_degradation_returns_503_if_service_not_wired

  保留 (3)
    16. test_get_retention_returns_503_if_service_not_wired
    17. test_update_retention_returns_503_if_service_not_wired
    18. test_trigger_retention_returns_503_if_service_not_wired

  统计 (3)
    19. test_stats_returns_aggregated_data
    20. test_stats_days_parameter_validated
    21. test_stats_success_rate_calculation
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 把 backend 加入 path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.base import Base
from app.models import image_generation_models  # noqa: F401 - 触发表注册
from app.models.image_generation_models import ImageGenHistory
from app.services.image_gen_quota_service import QuotaInfo


# ============================================================
# Fixtures
# ============================================================

# 使用 SQLite 内存数据库 + StaticPool，所有连接共享同一份内存库
TEST_SQLITE_URL = "sqlite:///:memory:"
_engine = create_engine(
    TEST_SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="function")
def db_session():
    """每次测试新建表 + 新 session"""
    Base.metadata.create_all(bind=_engine)
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()
        # 清表（下一个测试重建）
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def admin_user():
    """模拟管理员 UserResponse"""
    return MagicMock(
        user_id="admin-001",
        username="admin",
        email="admin@test.com",
        role="admin",
    )


@pytest.fixture
def normal_user():
    """模拟普通用户 UserResponse"""
    return MagicMock(
        user_id="user-001",
        username="alice",
        email="alice@test.com",
        role="user",
    )


# ============================================================
# Mock 服务
# ============================================================

def _make_quota(
    user_id: str = "user-001",
    daily_limit: int = 50,
    daily_used: int = 5,
    monthly_limit: int = 1000,
    monthly_used: int = 100,
    valid_from=None,
    valid_until=None,
    granted_by: str = "admin-001",
    notes: str = None,
    is_valid: bool = True,
) -> QuotaInfo:
    return QuotaInfo(
        user_id=user_id,
        daily_limit=daily_limit,
        daily_used=daily_used,
        daily_remaining=max(0, daily_limit - daily_used),
        monthly_limit=monthly_limit,
        monthly_used=monthly_used,
        monthly_remaining=max(0, monthly_limit - monthly_used),
        valid_from=valid_from,
        valid_until=valid_until,
        is_valid=is_valid,
        granted_by=granted_by,
        notes=notes,
    )


@pytest.fixture
def mock_quota_svc():
    """可配置的 mock ImageGenQuotaService"""
    svc = MagicMock()
    svc.list_users.return_value = []
    svc.count_users.return_value = 0
    svc.get_user_quota.return_value = None
    svc.grant.return_value = _make_quota()
    svc.revoke.return_value = None
    svc.reset_counters.return_value = None
    return svc


@pytest.fixture
def mock_dify_config_svc():
    """可配置的 mock DifyConfigService"""

    cfg_view = {
        "api_url": "https://dify.test.com/v1",
        "is_api_key_set": True,
        "workflow_text2img": "wf-text2img-001",
        "workflow_img2img": "wf-img2img-002",
        "workflow_inpaint": "wf-inpaint-003",
        "workflow_upload_edit": "wf-upload-edit-004",
        "default_timeout": 60.0,
    }

    svc = MagicMock()
    svc.get_config_view.return_value = cfg_view
    svc.update_config.return_value = None
    return svc


@pytest.fixture
def mock_dify_client():
    """可配置的 mock DifyClient"""
    client = MagicMock()
    client.test_connection = AsyncMock(return_value=(True, "连接成功"))
    return client


# ============================================================
# app + 依赖覆盖
# ============================================================

@pytest.fixture
def app(mock_quota_svc, mock_dify_config_svc, mock_dify_client, db_session, admin_user):
    """
    构造独立的 FastAPI app（避免污染项目全局 app）

    依赖覆盖：
      - get_admin_user → 返回固定 admin_user
      - get_image_gen_quota_service → mock_quota_svc
      - get_dify_config_service → mock_dify_config_svc
      - get_dify_client → mock_dify_client
      - get_db → 临时 SQLite session
    """
    from app.routes import admin_image_generation as aig

    app = FastAPI()
    app.include_router(aig.router)

    def _override_admin():
        return admin_user

    def _override_quota():
        return mock_quota_svc

    def _override_config():
        return mock_dify_config_svc

    def _override_client():
        return mock_dify_client

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[aig.get_admin_user] = _override_admin
    app.dependency_overrides[aig.get_image_gen_quota_service] = _override_quota
    app.dependency_overrides[aig.get_dify_config_service] = _override_config
    app.dependency_overrides[aig.get_dify_client] = _override_client
    app.dependency_overrides[aig.get_db] = _override_db

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def app_with_normal_user(mock_quota_svc, mock_dify_config_svc, mock_dify_client, db_session, normal_user):
    """用普通用户 token 构造 app（用于鉴权失败测试）"""
    from app.routes import admin_image_generation as aig

    app = FastAPI()
    app.include_router(aig.router)

    def _override_user():
        return normal_user

    def _override_quota():
        return mock_quota_svc

    def _override_config():
        return mock_dify_config_svc

    def _override_client():
        return mock_dify_client

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    # 让 get_admin_user 实际执行（基于 current_user.role）
    # 但我们直接 mock get_admin_user 总是抛 403
    def _override_admin():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Permission denied: Admin access required")

    app.dependency_overrides[aig.get_admin_user] = _override_admin
    app.dependency_overrides[aig.get_image_gen_quota_service] = _override_quota
    app.dependency_overrides[aig.get_dify_config_service] = _override_config
    app.dependency_overrides[aig.get_dify_client] = _override_client
    app.dependency_overrides[aig.get_db] = _override_db

    return app


@pytest.fixture
def client_not_admin(app_with_normal_user):
    return TestClient(app_with_normal_user)


# ============================================================
# 辅助：写入测试历史
# ============================================================

def _insert_history(
    db_session,
    *,
    user_id: str = "user-001",
    status: str = "success",
    model_used: str = "doubao_seedream",
    days_ago: int = 1,
) -> None:
    """往测试库插入一条历史"""
    from app.models.image_generation_models import ImageGenHistory
    import uuid

    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    record = ImageGenHistory(
        id=str(uuid.uuid4()),
        user_id=user_id,
        operation="text2img",
        prompt="test prompt",
        result_oss_key=f"image-gen/result/{uuid.uuid4()}.png",
        model_used=model_used,
        status=status,
        duration_ms=1000,
        created_at=created_at,
    )
    db_session.add(record)
    db_session.commit()


# ============================================================
# 1. 鉴权 (1)
# ============================================================

class TestAuth:
    def test_get_users_requires_admin(self, client_not_admin):
        """普通用户 token 访问 → 403"""
        resp = client_not_admin.get("/api/admin/image-generation/users")
        assert resp.status_code == 403
        body = resp.json()
        # detail 字段可能是字符串或 dict
        assert "Permission denied" in str(body.get("detail", "")) or \
               "Admin" in str(body.get("detail", ""))


# ============================================================
# 2. 配额管理 (5)
# ============================================================

class TestQuotaManagement:

    def test_list_users_pagination(self, client, mock_quota_svc):
        """分页 + 搜索参数正确传递给 service"""
        mock_quota_svc.list_users.return_value = [_make_quota(), _make_quota(user_id="user-002")]
        mock_quota_svc.count_users.return_value = 2

        resp = client.get(
            "/api/admin/image-generation/users",
            params={"skip": 10, "limit": 20, "search": "alice"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["skip"] == 10
        assert body["limit"] == 20
        assert len(body["items"]) == 2
        # 验证参数透传
        mock_quota_svc.list_users.assert_called_once_with(skip=10, limit=20, search="alice")
        mock_quota_svc.count_users.assert_called_once_with(search="alice")

    def test_grant_quota_creates_record(self, client, mock_quota_svc):
        """grant 成功 → 返回 QuotaInfo dict"""
        mock_quota_svc.grant.return_value = _make_quota(daily_limit=100, monthly_limit=3000)

        payload = {
            "daily_limit": 100,
            "monthly_limit": 3000,
            "notes": "测试分配",
        }
        resp = client.post(
            "/api/admin/image-generation/users/user-001/grant",
            json=payload,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == "user-001"
        assert body["daily_limit"] == 100
        # 验证参数传递
        mock_quota_svc.grant.assert_called_once()
        call_kwargs = mock_quota_svc.grant.call_args.kwargs
        assert call_kwargs["user_id"] == "user-001"
        assert call_kwargs["daily_limit"] == 100
        assert call_kwargs["monthly_limit"] == 3000
        assert call_kwargs["granted_by"] == "admin-001"
        assert call_kwargs["notes"] == "测试分配"

    def test_grant_quota_validity_range_invalid(self, client):
        """valid_from >= valid_until → 422"""
        later = datetime.now(timezone.utc) + timedelta(days=10)
        earlier = datetime.now(timezone.utc)
        payload = {
            "daily_limit": 10,
            "monthly_limit": 100,
            "valid_from": later.isoformat(),
            "valid_until": earlier.isoformat(),
        }
        resp = client.post(
            "/api/admin/image-generation/users/user-001/grant",
            json=payload,
        )
        assert resp.status_code == 422

    def test_grant_quota_extra_field_rejected(self, client):
        """未知字段被 extra="forbid" 拦截 → 422"""
        payload = {
            "daily_limit": 10,
            "monthly_limit": 100,
            "is_admin": True,  # 不允许的字段
        }
        resp = client.post(
            "/api/admin/image-generation/users/user-001/grant",
            json=payload,
        )
        assert resp.status_code == 422

    def test_revoke_quota_deletes_record(self, client, mock_quota_svc):
        """DELETE 调用 service.revoke"""
        resp = client.delete("/api/admin/image-generation/users/user-001/quota")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["user_id"] == "user-001"
        mock_quota_svc.revoke.assert_called_once_with("user-001")

    def test_reset_counters_zeroes_used(self, client, mock_quota_svc):
        """POST /reset 调用 service.reset_counters"""
        resp = client.post("/api/admin/image-generation/users/user-001/reset")
        assert resp.status_code == 200
        mock_quota_svc.reset_counters.assert_called_once_with("user-001")

    def test_get_user_quota_returns_info(self, client, mock_quota_svc):
        """存在配额 → 返回 dict"""
        mock_quota_svc.get_user_quota.return_value = _make_quota()
        resp = client.get("/api/admin/image-generation/quota/user-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == "user-001"
        mock_quota_svc.get_user_quota.assert_called_once_with("user-001")

    def test_get_user_quota_404_if_missing(self, client, mock_quota_svc):
        """无配额记录 → 404"""
        mock_quota_svc.get_user_quota.return_value = None
        resp = client.get("/api/admin/image-generation/quota/no-such-user")
        assert resp.status_code == 404


# ============================================================
# 3. Dify 配置 (4)
# ============================================================

class TestDifyConfig:

    def test_get_dify_config_masks_api_key(self, client, mock_dify_config_svc):
        """config 视图不应包含明文 api_key"""
        resp = client.get("/api/admin/image-generation/config")
        assert resp.status_code == 200
        body = resp.json()
        # 明文 key 不应出现
        assert "app_api_key" not in body
        # 只暴露 is_api_key_set 标志
        assert "is_api_key_set" in body
        assert body["is_api_key_set"] is True
        mock_dify_config_svc.get_config_view.assert_called_once()

    def test_update_dify_config_partial_update(self, client, mock_dify_config_svc):
        """部分字段更新 → 仅更新传入字段"""
        payload = {
            "api_url": "https://new-dify.test.com/v1",
            "timeout_seconds": 120,
        }
        resp = client.put("/api/admin/image-generation/config", json=payload)
        assert resp.status_code == 200
        mock_dify_config_svc.update_config.assert_called_once()
        call_kwargs = mock_dify_config_svc.update_config.call_args.kwargs
        partial = call_kwargs["partial"]
        # 字段名映射到 service key
        assert "api_url" in partial
        assert partial["api_url"] == "https://new-dify.test.com/v1"
        assert "default_timeout" in partial
        assert partial["default_timeout"] == 120
        # workflow id 没传，不应出现在 update 中
        assert "workflow_text2img" not in partial
        assert call_kwargs["updated_by"] == "admin-001"

    def test_update_dify_config_with_unknown_field(self, client):
        """未知字段 → 422（extra="forbid"）"""
        payload = {
            "api_url": "https://dify.test.com/v1",
            "secret_backdoor": True,  # 不允许
        }
        resp = client.put("/api/admin/image-generation/config", json=payload)
        assert resp.status_code == 422

    def test_test_connection_returns_sanitized_message(self, client, mock_dify_client):
        """Dify 抛带 stack trace 的异常 → message 中不能暴露 IP / key / 文件路径"""
        # 模拟一次连接失败，message 里塞 stack trace + IP + 文件路径 + Bearer token
        raw_msg = (
            "Traceback (most recent call last):\n"
            "  File \"/app/internal/secrets.py\", line 42\n"
            "ConnectionError: Could not connect to 192.168.1.100:8080\n"
            "Authorization: Bearer app-secret-key-DO-NOT-LEAK\n"
        )
        mock_dify_client.test_connection = AsyncMock(return_value=(False, raw_msg))

        resp = client.post("/api/admin/image-generation/config/test")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        sanitized = body["message"]

        # 关键断言：不能泄露敏感信息
        assert "192.168.1.100" not in sanitized
        assert "app-secret-key-DO-NOT-LEAK" not in sanitized
        assert "/app/internal/secrets.py" not in sanitized
        assert "Traceback" not in sanitized
        assert "Bearer" not in sanitized
        # 应该是友好提示
        assert sanitized.startswith("connection failed:")


# ============================================================
# 4. 降级管理 (2) — Phase 9 占位
# ============================================================

class TestDegradation:

    def test_get_degradation_returns_503_if_service_not_wired(self, client):
        """degradation_svc=None → 503"""
        resp = client.get("/api/admin/image-generation/degradation")
        assert resp.status_code == 503
        body = resp.json()
        assert "service_not_enabled" in str(body.get("detail", ""))

    def test_update_degradation_returns_503_if_service_not_wired(self, client):
        """degradation_svc=None → 503"""
        resp = client.put(
            "/api/admin/image-generation/degradation",
            json={"enabled": True, "failure_threshold": 5},
        )
        assert resp.status_code == 503

    def test_reset_degradation_returns_503_if_service_not_wired(self, client):
        """degradation_svc=None → 503"""
        resp = client.post("/api/admin/image-generation/degradation/reset")
        assert resp.status_code == 503


# ============================================================
# 5. 保留策略 (3) — Phase 10 占位
# ============================================================

class TestRetention:

    def test_get_retention_returns_503_if_service_not_wired(self, client):
        resp = client.get("/api/admin/image-generation/retention")
        assert resp.status_code == 503
        body = resp.json()
        assert "service_not_enabled" in str(body.get("detail", ""))

    def test_update_retention_returns_503_if_service_not_wired(self, client):
        resp = client.put(
            "/api/admin/image-generation/retention",
            json={"mode": "delete_after_n_days", "n_days": 60},
        )
        assert resp.status_code == 503

    def test_trigger_retention_returns_503_if_service_not_wired(self, client):
        resp = client.post("/api/admin/image-generation/retention/trigger")
        assert resp.status_code == 503


# ============================================================
# 6. 统计 (3)
# ============================================================

class TestStats:

    def test_stats_returns_aggregated_data(self, client, db_session):
        """聚合查询：插入多条历史，验证返回字段"""
        # 插入 6 条历史：5 success + 1 failed + 1 cancelled
        # 注意：cancelled 和 failed 都计入 failed_calls
        for _ in range(5):
            _insert_history(db_session, status="success", model_used="doubao_seedream")
        _insert_history(db_session, status="failed", model_used="qwen_image")
        # cancelled 不计入 default 窗口太久远，加上确保聚合正确
        # 这里都放最近 1 天内

        resp = client.get("/api/admin/image-generation/stats?days=7")
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 7
        assert body["total_calls"] == 6
        assert body["success_calls"] == 5
        assert body["failed_calls"] == 1
        # 模型分布
        models = {row["model"]: row["count"] for row in body["model_distribution"]}
        assert models.get("doubao_seedream") == 5
        assert models.get("qwen_image") == 1
        # 日调用
        assert len(body["daily_calls"]) >= 1

    def test_stats_days_parameter_validated(self, client):
        """days 越界 → 422"""
        resp = client.get("/api/admin/image-generation/stats?days=0")
        assert resp.status_code == 422
        resp = client.get("/api/admin/image-generation/stats?days=100")
        assert resp.status_code == 422
        # 边界合法值
        resp = client.get("/api/admin/image-generation/stats?days=1")
        assert resp.status_code == 200
        resp = client.get("/api/admin/image-generation/stats?days=90")
        assert resp.status_code == 200

    def test_stats_success_rate_calculation(self, client, db_session):
        """写 5 成功 + 2 失败 → success_rate ≈ 0.714"""
        for _ in range(5):
            _insert_history(db_session, status="success")
        for _ in range(2):
            _insert_history(db_session, status="failed")

        resp = client.get("/api/admin/image-generation/stats?days=7")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 7
        assert body["success_calls"] == 5
        assert body["failed_calls"] == 2
        # 5/7 ≈ 0.7143
        assert abs(body["success_rate"] - 5 / 7) < 0.01

    def test_stats_empty_returns_zero(self, client, db_session):
        """无历史 → 全 0"""
        resp = client.get("/api/admin/image-generation/stats?days=7")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 0
        assert body["success_calls"] == 0
        assert body["failed_calls"] == 0
        assert body["success_rate"] == 0
        assert body["model_distribution"] == []
        assert body["daily_calls"] == []
