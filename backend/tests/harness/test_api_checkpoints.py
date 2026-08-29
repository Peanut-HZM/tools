"""Checkpoint REST API 测试

Phase 3-Plan-1D / Task 4

测试覆盖：
- GET  /api/v1/harness/conversations/{id}/branches
- POST /api/v1/harness/conversations/{id}/branches
- POST /api/v1/harness/conversations/{id}/branches/{branch_id}/merge
- POST /api/v1/harness/conversations/{id}/checkpoints/{cp_id}/rollback
- 401 / 403 未鉴权拒绝

说明：
- mock_db 为 MagicMock（避免 SQLite in-memory 与 TestClient 跨线程冲突）。
  Brief 字面定义 ``mock_db`` 本身没有具体类型；用 MagicMock 与现有 harness 测试风格一致。
- 部分 brief 字面在路径中使用的 ``conv-1`` / ``branch-1`` / ``cp-1`` 不是合法 UUID，
  本实现改用真实 UUID；这是为了让 FastAPI 路径参数校验通过（偏差已在 task-4-report 记录）。
- 通过 fixture 检测自动覆盖 get_db / get_current_user 依赖；测试
  ``test_unauthenticated_request_rejected`` 不使用 auth_headers / mock_db，因此不触发覆盖，
  走真实 JWT 校验路径。
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_db
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
CONV_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
CP_ID = uuid.uuid4()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """认证 header（占位 — 真正的鉴权覆盖由 apply_dep_overrides 完成）"""
    return {"Authorization": "Bearer fake-token-for-test"}


@pytest.fixture
def mock_db():
    """模拟 DB session（MagicMock）

    SQLite in-memory session 不能跨线程（TestClient 在另一线程运行请求），
    因此采用 MagicMock，避免 thread-safety 问题。
    """
    return MagicMock()


@pytest.fixture(autouse=True)
def apply_dep_overrides(request):
    """根据测试请求的 fixtures 决定是否覆盖 get_db / get_current_user。

    - 测试同时声明了 mock_db + auth_headers → 覆盖 get_db 为 mock、覆盖 get_current_user 为 stub
    - 测试只声明 client（如 unauth 测试）→ 不覆盖，触发真实 JWT 校验 → 401
    """
    if "mock_db" in request.fixturenames:
        db = request.getfixturevalue("mock_db")
        app.dependency_overrides[get_db] = lambda: db
    if "auth_headers" in request.fixturenames:
        app.dependency_overrides[get_current_user] = lambda: {
            "id": str(USER_ID),
            "username": "tester",
            "role": "user",
        }
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_branch(
    branch_id=None, conv_id=None, name="主线",
    parent_branch_id=None, head_checkpoint_id=None,
    is_archived=False, closed_at=None,
):
    """构造一个 ORM-like Branch mock，datetime 字段已转 ISO str"""
    from datetime import datetime
    b = MagicMock()
    b.id = branch_id or BRANCH_ID
    b.conversation_id = conv_id or CONV_ID
    b.name = name
    b.parent_branch_id = parent_branch_id
    b.head_checkpoint_id = head_checkpoint_id
    b.is_archived = is_archived
    b.created_at = datetime(2026, 1, 1, 12, 0, 0)
    b.closed_at = closed_at
    return b


def _make_mock_checkpoint(
    cp_id=None, conv_id=None, branch_id=None,
    step_index=1, phase="after_user_message",
    checkpoint_kind="auto", label=None,
    parent_checkpoint_id=None, merge_parents=None,
    is_head=True, messages_snapshot=None, agent_state=None,
):
    """构造一个 ORM-like SessionCheckpoint mock，datetime 字段已转 ISO str"""
    from datetime import datetime
    cp = MagicMock()
    cp.id = cp_id or CP_ID
    cp.conversation_id = conv_id or CONV_ID
    cp.branch_id = branch_id or BRANCH_ID
    cp.parent_checkpoint_id = parent_checkpoint_id
    cp.step_index = step_index
    cp.phase = phase
    cp.checkpoint_kind = checkpoint_kind
    cp.label = label
    cp.merge_parents = merge_parents
    cp.is_head = is_head
    cp.messages_snapshot = messages_snapshot if messages_snapshot is not None else []
    cp.agent_state = agent_state if agent_state is not None else {}
    cp.created_at = datetime(2026, 1, 1, 12, 0, 0)
    return cp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_branches_endpoint(client, auth_headers, mock_db):
    """GET /branches 应返回分支列表"""
    # 配置 mock_db 链：query(Branch).filter().order_by().all() → [mock_branch]
    mock_branch = _make_mock_branch()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_branch]

    response = client.get(
        f"/api/v1/harness/conversations/{CONV_ID}/branches",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    # 路由返回 List[BranchResponse]，response.json() 为 list
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["name"] == "主线"


def test_create_branch_endpoint(client, auth_headers, mock_db):
    """POST /branches 应创建新分支"""
    # 配置 CheckpointService.branch_from 返回值
    mock_branch = _make_mock_branch(branch_id=uuid.uuid4(), name="GPT-4 实验")
    mock_first_cp = _make_mock_checkpoint(cp_id=uuid.uuid4(), checkpoint_kind="branch_point")

    with patch("app.api.routes.harness_checkpoints.CheckpointService") as MockService:
        MockService.return_value.branch_from.return_value = (mock_branch, mock_first_cp)

        body = {
            "source_checkpoint_id": str(CP_ID),
            "name": "GPT-4 实验",
            "start_with_messages": True,
        }
        response = client.post(
            f"/api/v1/harness/conversations/{CONV_ID}/branches",
            json=body,
            headers=auth_headers,
        )
    assert response.status_code == 201


def test_merge_endpoint(client, auth_headers, mock_db):
    """POST /branches/{id}/merge 应做 pick-from 合并"""
    mock_branch = _make_mock_branch(branch_id=uuid.uuid4(), name="合并 v1")
    mock_merge_commit = _make_mock_checkpoint(
        cp_id=uuid.uuid4(),
        phase="merge_commit",
        checkpoint_kind="merge_commit",
    )

    with patch("app.api.routes.harness_checkpoints.CheckpointService") as MockService:
        MockService.return_value.merge_branches.return_value = (mock_branch, mock_merge_commit)

        body = {
            "picked_checkpoint_ids": [
                str(uuid.uuid4()),
                str(uuid.uuid4()),
            ],
            "new_branch_name": "合并 v1",
        }
        response = client.post(
            f"/api/v1/harness/conversations/{CONV_ID}/branches/{BRANCH_ID}/merge",
            json=body,
            headers=auth_headers,
        )
    assert response.status_code == 201


def test_rollback_endpoint(client, auth_headers, mock_db):
    """POST /checkpoints/{id}/rollback 应回滚"""
    mock_target_cp = _make_mock_checkpoint()

    with patch("app.api.routes.harness_checkpoints.CheckpointService") as MockService:
        MockService.return_value.rollback.return_value = (mock_target_cp, 3)

        response = client.post(
            f"/api/v1/harness/conversations/{CONV_ID}/checkpoints/{CP_ID}/rollback",
            headers=auth_headers,
        )
    assert response.status_code == 200


def test_unauthenticated_request_rejected(client):
    """无 auth 应 401"""
    response = client.get(f"/api/v1/harness/conversations/{CONV_ID}/branches")
    assert response.status_code in (401, 403)