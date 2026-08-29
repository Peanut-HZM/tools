"""Checkpoint REST API 测试

Phase 3-Plan-1D / Task 4

测试覆盖：
- GET  /api/v1/harness/conversations/{id}/branches
- POST /api/v1/harness/conversations/{id}/branches
- POST /api/v1/harness/conversations/{id}/branches/{branch_id}/merge
- POST /api/v1/harness/conversations/{id}/checkpoints/{cp_id}/rollback
- 401 / 403 未鉴权拒绝
- §6.3 租户隔离 — user A 访问 user B 的 conversation 应 404

说明：
- mock_db 为 MagicMock（避免 SQLite in-memory 与 TestClient 跨线程冲突）。
  Brief 字面定义 ``mock_db`` 本身没有具体类型；用 MagicMock 与现有 harness 测试风格一致。
- 部分 brief 字面在路径中使用的 ``conv-1`` / ``branch-1`` / ``cp-1`` 不是合法 UUID，
  本实现改用真实 UUID；这是为了让 FastAPI 路径参数校验通过（已在 task-4-report 记录）。
- 通过 fixture 检测自动覆盖 get_db / get_current_user 依赖；测试
  ``test_unauthenticated_request_rejected`` 不使用 auth_headers / mock_db，因此不触发覆盖，
  走真实 JWT 校验路径。
- §6.3 租户隔离测试使用真实 SQLite in-memory session（``real_db`` fixture），
  创建 user B 的 Conversation 行，验证 user A 的请求被拒绝。
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.harness_models import Branch, SessionCheckpoint


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()      # 当前登录用户（user A）
USER_B_ID = uuid.uuid4()    # 另一个用户（user B）
CONV_ID = uuid.uuid4()      # user A 拥有的 conversation（happy path）
CONV_B_ID = uuid.uuid4()    # user B 拥有的 conversation（隔离测试用）
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


@pytest.fixture
def real_db():
    """真实 SQLite in-memory session — 用于 §6.3 租户隔离测试。

    该 fixture 完整建表（含 Conversation / Branch / SessionCheckpoint），
    模拟 user B 创建一条 Conversation 行后验证 user A 的请求被拒绝。
    """
    # 复用 conftest 的 SQLite JSONB/UUID 降级编译器
    from sqlalchemy.dialects.postgresql import JSONB, UUID
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_for_sqlite(element, compiler, **kw):
        return "JSON"

    @compiles(UUID, "sqlite")
    def _compile_uuid_for_sqlite(element, compiler, **kw):
        return "CHAR(32)"

    from app.models.harness_models import Branch, SessionCheckpoint  # noqa: F401
    from app.models.base import Base

    # StaticPool + check_same_thread=False 让 SQLite session 可跨线程
    # （TestClient 在另一线程运行请求）
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def apply_dep_overrides(request):
    """根据测试请求的 fixtures 决定是否覆盖 get_db / get_current_user。

    - 测试同时声明了 mock_db / real_db + auth_headers → 覆盖 get_db 为 mock/real、覆盖 get_current_user 为 stub
    - 测试只声明 client（如 unauth 测试）→ 不覆盖，触发真实 JWT 校验 → 401
    """
    if "mock_db" in request.fixturenames:
        db = request.getfixturevalue("mock_db")
        app.dependency_overrides[get_db] = lambda: db
    elif "real_db" in request.fixturenames:
        db = request.getfixturevalue("real_db")
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


def _make_mock_conv(conv_id=None, user_id=None):
    """构造 ORM-like Conversation mock"""
    conv = MagicMock()
    conv.id = conv_id or CONV_ID
    conv.user_id = user_id or str(USER_ID)
    return conv


def _make_mock_branch(
    branch_id=None, conv_id=None, name="主线",
    parent_branch_id=None, head_checkpoint_id=None,
    is_archived=False, closed_at=None,
):
    """构造 ORM-like Branch mock，datetime 字段已转 ISO str"""
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
    """构造 ORM-like SessionCheckpoint mock，datetime 字段已转 ISO str"""
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


def _setup_mock_db_for_happy_path(mock_db):
    """配置 mock_db：db.query(Conversation).filter().first() → mock_conv，其他查询链可继续工作。

    通过 side_effect 根据 model 类分派 query 行为，避免一个 chain 配置覆盖另一个。
    """
    mock_conv = _make_mock_conv()
    mock_branch = _make_mock_branch()

    def query_side_effect(model):
        q = MagicMock()
        if model is Conversation:
            q.filter.return_value.first.return_value = mock_conv
        elif model is Branch:
            q.filter.return_value.order_by.return_value.all.return_value = [mock_branch]
            q.filter.return_value.first.return_value = mock_branch
        else:
            # SessionCheckpoint 或其他
            q.filter.return_value.first.return_value = None
            q.filter.return_value.all.return_value = []
            q.filter.return_value.order_by.return_value.all.return_value = []
        return q

    mock_db.query.side_effect = query_side_effect
    return mock_conv, mock_branch


# ---------------------------------------------------------------------------
# Tests — Happy path (existing 5 tests + adjustments)
# ---------------------------------------------------------------------------


def test_list_branches_endpoint(client, auth_headers, mock_db):
    """GET /branches 应返回分支列表"""
    _setup_mock_db_for_happy_path(mock_db)

    response = client.get(
        f"/api/v1/harness/conversations/{CONV_ID}/branches",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["name"] == "主线"


def test_create_branch_endpoint(client, auth_headers, mock_db):
    """POST /branches 应创建新分支"""
    _setup_mock_db_for_happy_path(mock_db)
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
    _setup_mock_db_for_happy_path(mock_db)
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
    _setup_mock_db_for_happy_path(mock_db)
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


# ---------------------------------------------------------------------------
# §6.3 租户隔离测试 — 使用真实 DB 验证 ownership check 真生效
# ---------------------------------------------------------------------------


def test_tenant_isolation_other_user_conv_returns_404(client, auth_headers, real_db):
    """user A 访问 user B 的 conversation 应返回 404（不泄漏存在性）

    使用真实 SQLite in-memory session（real_db）创建 user B 的 Conversation 行，
    验证 ownership check 真生效（不是 mock 链返回的假值）。
    """
    # 在 DB 中创建 user B 拥有的 conversation（user A 在 JWT 中）
    user_b_conv = Conversation(
        id=CONV_B_ID,
        user_id=str(USER_B_ID),  # 不同于当前 user A
        title="User B 的私密会话",
    )
    real_db.add(user_b_conv)
    real_db.commit()

    # current_user stub 是 user A（来自 apply_dep_overrides）
    # 但路径参数 CONV_B_ID 属于 user B → 应被 _check_tenant 拒绝
    response = client.get(
        f"/api/v1/harness/conversations/{CONV_B_ID}/branches",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_tenant_isolation_write_checkpoint_other_user_returns_404(client, auth_headers, real_db):
    """user A 对 user B 的 conversation 调用 POST /checkpoints 应返回 404"""
    user_b_conv = Conversation(
        id=CONV_B_ID,
        user_id=str(USER_B_ID),
        title="User B 的私密会话",
    )
    real_db.add(user_b_conv)
    real_db.commit()

    # messages: List[dict] 被 FastAPI 视为 body 字段（非 query）
    response = client.post(
        f"/api/v1/harness/conversations/{CONV_B_ID}/checkpoints"
        f"?step_index=1&phase=after_user_message",
        json={"messages": [{"id": str(uuid.uuid4()), "content": "hi"}]},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_tenant_isolation_own_conv_passes(client, auth_headers, real_db):
    """user A 访问自己的 conversation 应正常通过（200）"""
    own_conv = Conversation(
        id=CONV_ID,
        user_id=str(USER_ID),  # 匹配当前 user A
        title="我自己的会话",
    )
    real_db.add(own_conv)
    real_db.commit()

    response = client.get(
        f"/api/v1/harness/conversations/{CONV_ID}/branches",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []  # 无分支


def test_list_checkpoints_idor_other_conv_branch_rejected(client, auth_headers, real_db):
    """IDOR 防护：user A 的 conv 不能读取 user B 的 branch 的 checkpoints

    场景：
    - user A 拥有 conv-A（通过 _check_tenant 校验）
    - user A 尝试访问 branch-B（属于 conv-B，user B 拥有）
    - 应返回 404（branch 不属于 conv-A）

    这是 HIGH 安全 finding 的回归测试 — 防止通过 list_checkpoints 端点
    跨租户读取其他用户的 checkpoint 数据。
    """
    # user A 拥有 conv-A
    user_a_conv = Conversation(
        id=CONV_ID,
        user_id=str(USER_ID),
        title="user A 的会话",
    )
    # user B 拥有 conv-B，包含 branch-B
    user_b_conv = Conversation(
        id=CONV_B_ID,
        user_id=str(USER_B_ID),
        title="user B 的私密会话",
    )
    user_b_branch = Branch(
        id=BRANCH_ID,
        conversation_id=CONV_B_ID,  # branch 属于 conv-B
        name="user B 的私密分支",
        is_archived=False,
    )
    real_db.add_all([user_a_conv, user_b_conv, user_b_branch])
    real_db.commit()

    # user A 请求访问 conv-A 下的 branch-B（实际属于 conv-B）
    response = client.get(
        f"/api/v1/harness/conversations/{CONV_ID}/branches/{BRANCH_ID}/checkpoints",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "分支不存在" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Resource cap 测试 — 防 messages / scratch_state 过大
# ---------------------------------------------------------------------------


def test_write_checkpoint_manual_messages_cap_rejects(client, auth_headers, mock_db):
    """messages 数量 > MAX_MESSAGES_PER_CHECKPOINT (200) 应 400"""
    _setup_mock_db_for_happy_path(mock_db)
    # 201 个 message 触发 cap
    big_messages = [{"id": str(uuid.uuid4()), "content": "x"} for _ in range(201)]

    # messages: List[dict] 被 FastAPI 视为 body 字段（非 query）
    response = client.post(
        f"/api/v1/harness/conversations/{CONV_ID}/checkpoints"
        f"?step_index=1&phase=after_user_message",
        json={"messages": big_messages},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "messages 数量超限" in response.json()["detail"]