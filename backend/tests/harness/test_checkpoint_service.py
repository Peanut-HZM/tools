"""CheckpointService 单元测试"""
import pytest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session as DBSession

from app.services.harness.checkpoint_service import CheckpointService


@pytest.fixture
def mock_db():
    return MagicMock(spec=DBSession)


@pytest.fixture
def service(mock_db):
    return CheckpointService(mock_db)


def _make_conversation(conv_id=None):
    c = MagicMock()
    c.id = conv_id or uuid.uuid4()
    return c


def _make_messages(n=3):
    msgs = []
    for i in range(n):
        m = MagicMock()
        m.id = uuid.uuid4()
        m.sender_type = "user" if i % 2 == 0 else "agent"
        m.role = "user" if i % 2 == 0 else "assistant"
        m.content = f"msg-{i}"
        m.message_type = "text"
        m.sent_at = MagicMock()
        m.sent_at.isoformat.return_value = f"2026-01-01T00:00:{i:02d}"
        m.tool_calls = None
        m.tool_call_id = None
        m.tool_name = None
        m.attachments = []
        m.prompt_tokens = 10
        m.completion_tokens = 20
        m.total_tokens = 30
        msgs.append(m)
    return msgs


def test_write_checkpoint_creates_record(service, mock_db):
    """write_checkpoint 应创建 SessionCheckpoint 行"""
    conv = _make_conversation()
    branch_id = uuid.uuid4()
    msgs = _make_messages(2)

    # 让 SessionCheckpoint 构造后被 mock add
    cp_instance = MagicMock()
    cp_instance.id = uuid.uuid4()
    with patch("app.services.harness.checkpoint_service.SessionCheckpoint") as mock_cp_cls:
        mock_cp_cls.return_value = cp_instance
        result = service.write_checkpoint(
            conversation_id=conv.id,
            step_index=5,
            phase="after_user_message",
            messages=msgs,
            scratch_state={"k": "v"},
            branch_id=branch_id,
        )

    # 验证 cp 被 add + commit
    mock_db.add.assert_called_once_with(cp_instance)
    mock_db.commit.assert_called_once()
    assert result is cp_instance


def test_write_checkpoint_serializes_messages(service, mock_db):
    """write_checkpoint 应把 Message ORM 序列化为 dict"""
    conv = _make_conversation()
    branch_id = uuid.uuid4()
    msgs = _make_messages(1)

    with patch("app.services.harness.checkpoint_service.SessionCheckpoint") as mock_cp_cls:
        cp_instance = MagicMock()
        mock_cp_cls.return_value = cp_instance
        service.write_checkpoint(
            conversation_id=conv.id,
            step_index=1,
            phase="before_tool",
            messages=msgs,
            scratch_state={},
            branch_id=branch_id,
        )

    # 检查 SessionCheckpoint 构造时的 messages_snapshot 参数
    call_kwargs = mock_cp_cls.call_args.kwargs
    snapshot = call_kwargs["messages_snapshot"]
    assert len(snapshot) == 1
    assert snapshot[0]["content"] == "msg-0"
    assert snapshot[0]["sender_type"] == "user"


def test_write_checkpoint_sets_parent(service, mock_db):
    """write_checkpoint 接受 parent_checkpoint_id 参数"""
    conv = _make_conversation()
    branch_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    with patch("app.services.harness.checkpoint_service.SessionCheckpoint") as mock_cp_cls:
        cp_instance = MagicMock()
        mock_cp_cls.return_value = cp_instance
        service.write_checkpoint(
            conversation_id=conv.id,
            step_index=1,
            phase="after_tool",
            messages=[],
            scratch_state={},
            branch_id=branch_id,
            parent_checkpoint_id=parent_id,
        )

    assert mock_cp_cls.call_args.kwargs["parent_checkpoint_id"] == parent_id


def test_rollback_updates_head(service, mock_db):
    """rollback 应更新 conversation.head_checkpoint_id + 旧 checkpoint is_head=False"""
    conv = _make_conversation()
    target_cp = MagicMock()
    target_cp.id = uuid.uuid4()
    target_cp.is_head = False
    target_cp.conversation_id = conv.id

    mock_db.query.return_value.filter.return_value.first.return_value = target_cp
    mock_db.query.return_value.filter.return_value.all.return_value = []  # 中间 checkpoint 列表为空

    # 需要让 service 拿到 conversation
    mock_db.query.return_value.filter.return_value.first.side_effect = [conv, target_cp]

    result = service.rollback(conversation_id=conv.id, target_checkpoint_id=target_cp.id)

    # 返回 (target, detached_count) tuple
    target, detached_n = result
    assert target is target_cp
    assert detached_n == 0  # 无旧 head

    # 验证 conversation.head_checkpoint_id 被设置
    assert conv.head_checkpoint_id == target_cp.id
    # 验证 target is_head 变为 True
    assert target_cp.is_head is True
    # 验证 commit
    mock_db.commit.assert_called_once()
