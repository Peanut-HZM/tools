"""记忆管理 API 测试

Phase 3 Plan-1B / Task 6
- GET    /api/v1/harness/agents/{agent_id}/memories
- DELETE /api/v1/harness/agents/{agent_id}/memories/{key}
- POST   /api/v1/harness/agents/{agent_id}/memories/search
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_db
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_agent_id():
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def override_user():
    """默认覆盖 get_current_user：模拟已认证用户"""
    app.dependency_overrides[get_current_user] = lambda: {
        "role": "user",
        "id": "11111111-1111-1111-1111-111111111111",
        "username": "test-user",
    }
    yield
    app.dependency_overrides.clear()


def _override_db(mock_db):
    def _fake():
        yield mock_db

    app.dependency_overrides[get_db] = _fake


def test_list_memories_authenticated(client, test_agent_id):
    """认证用户可以列出记忆"""
    mock_db = MagicMock()

    with patch("app.services.harness.memory_service.MemoryService") as mock_svc_cls:
        from app.services.harness.memory_service import MemoryEntry
        instance = mock_svc_cls.return_value
        instance.list_all = AsyncMock(return_value=[
            MemoryEntry(
                key="k1", value={"text": "hello"}, importance=0.8,
                access_count=3, summary="greeting", has_embedding=True,
            ),
        ])
        _override_db(mock_db)

        resp = client.get(f"/api/v1/harness/agents/{test_agent_id}/memories")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["records"][0]["key"] == "k1"
        assert data["records"][0]["value"] == {"text": "hello"}
        assert data["records"][0]["importance"] == 0.8
        assert data["records"][0]["access_count"] == 3
        assert data["records"][0]["summary"] == "greeting"
        assert data["records"][0]["has_embedding"] is True


def test_delete_memory_authenticated(client, test_agent_id):
    """认证用户可以删除记忆"""
    mock_db = MagicMock()

    with patch("app.services.harness.memory_service.MemoryService") as mock_svc_cls:
        instance = mock_svc_cls.return_value
        instance.delete = AsyncMock(return_value=True)
        _override_db(mock_db)

        resp = client.delete(f"/api/v1/harness/agents/{test_agent_id}/memories/k1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["key"] == "k1"
        instance.delete.assert_awaited_once()


def test_delete_memory_not_found(client, test_agent_id):
    """删除不存在的记忆返回 404"""
    mock_db = MagicMock()

    with patch("app.services.harness.memory_service.MemoryService") as mock_svc_cls:
        instance = mock_svc_cls.return_value
        instance.delete = AsyncMock(return_value=False)
        _override_db(mock_db)

        resp = client.delete(f"/api/v1/harness/agents/{test_agent_id}/memories/missing")

        assert resp.status_code == 404


def test_search_memories(client, test_agent_id):
    """向量检索 API 返回结果"""
    mock_db = MagicMock()

    with patch("app.services.harness.memory_service.MemoryService") as mock_svc_cls:
        from app.services.harness.memory_service import MemoryEntry
        instance = mock_svc_cls.return_value
        instance.search = AsyncMock(return_value=[
            MemoryEntry(
                key="k1", value={"text": "hello world"},
                score=0.92, importance=0.8,
            ),
            MemoryEntry(
                key="k2", value={"text": "world peace"},
                score=0.81, importance=0.6,
            ),
        ])
        _override_db(mock_db)

        resp = client.post(
            f"/api/v1/harness/agents/{test_agent_id}/memories/search",
            json={"query": "hello", "top_k": 5},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["records"][0]["key"] == "k1"
        assert data["records"][0]["score"] == 0.92
        # score 应被 round 到 4 位小数
        assert isinstance(data["records"][0]["score"], float)


def test_list_memories_unauthenticated(client, test_agent_id):
    """未认证返回 401"""
    # 移除默认的 dependency override
    app.dependency_overrides.clear()

    resp = client.get(f"/api/v1/harness/agents/{test_agent_id}/memories")
    assert resp.status_code == 401