# backend/tests/test_admin_llm_quota_api.py
"""管理员 LLM 配额 API 集成测试"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.llm_quota_models import LLMUserQuota
from app.routes import admin_llm_quota


@pytest.fixture
def client():
    return TestClient(app)


def _mock_admin():
    admin = MagicMock()
    admin.user_id = "admin-id"
    admin.role = "admin"
    return admin


def _grant_count_payload():
    return {"quota_mode": "count", "daily_limit": 10, "monthly_limit": 300, "notes": "test"}


def test_list_users_requires_admin(client):
    """无 auth 请求管理员接口 → 401"""
    r = client.get("/api/admin/llm-quota/users")
    assert r.status_code == 401


def test_grant_count_creates(client):
    """mock service 后，grant 接口返回正确结构"""
    # FastAPI Depends 在路由注册时已捕获依赖引用，必须通过 dependency_overrides 替换
    mock_svc_instance = MagicMock()
    mock_svc_instance.grant.return_value = MagicMock(
        user_id="u1", quota_mode="count",
        daily_limit=10, daily_used=0, daily_remaining=10,
        monthly_limit=300, monthly_used=0, monthly_remaining=300,
        token_period=None, token_limit=None, token_used=0, token_remaining=0,
        valid_from=None, valid_until=None, is_valid=True,
        granted_by="admin", notes="x",
    )

    def _override_admin():
        return _mock_admin()

    def _override_db():
        return MagicMock()

    try:
        app.dependency_overrides[admin_llm_quota.get_admin_user] = _override_admin
        app.dependency_overrides[admin_llm_quota.get_db] = _override_db
        with patch.object(admin_llm_quota, "LLMQuotaService", return_value=mock_svc_instance):
            r = client.post(
                "/api/admin/llm-quota/users/u1/grant",
                json=_grant_count_payload(),
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["quota_mode"] == "count"
