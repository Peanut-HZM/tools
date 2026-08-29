"""checkpoint 快照回填脚本测试"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session as DBSession


@pytest.fixture
def mock_db():
    db = MagicMock(spec=DBSession)
    return db


def test_backfill_no_pending_checkpoints(mock_db):
    """无待回填 checkpoint 应直接返回 0"""
    from scripts.backfill_checkpoint_snapshots import backfill_checkpoint_snapshots

    # mock 无 pending
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    filled = backfill_checkpoint_snapshots(mock_db, batch_size=10)
    assert filled == 0


def test_backfill_writes_messages_snapshot(mock_db):
    """回填应查询 messages 并写入 messages_snapshot"""
    from scripts.backfill_checkpoint_snapshots import backfill_checkpoint_snapshots

    # mock 1 个 pending checkpoint
    mock_db.query.return_value.filter.return_value.count.return_value = 1
    mock_checkpoint = MagicMock()
    mock_checkpoint.id = "cp-1"
    mock_checkpoint.conversation_id = "conv-1"
    mock_checkpoint.created_at = MagicMock()

    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_checkpoint]

    # mock messages 查询结果
    mock_msg = MagicMock()
    mock_msg.id = "msg-1"
    mock_msg.content = "hello"
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_msg]

    # 把第二、三次 query 区分开（第一次 count, 第二次 pending, 第三次 messages）
    call_count = {"n": 0}

    def fake_query(model):
        call_count["n"] += 1
        q = MagicMock()
        if call_count["n"] == 1:  # count
            q.filter.return_value.count.return_value = 1
        elif call_count["n"] == 2:  # pending list
            q.filter.return_value.limit.return_value.all.return_value = [mock_checkpoint]
        elif call_count["n"] == 3:  # messages
            q.filter.return_value.order_by.return_value.all.return_value = [mock_msg]
        else:  # 后续轮次：pending 为空以终止 while 循环
            q.filter.return_value.limit.return_value.all.return_value = []
        return q

    mock_db.query.side_effect = fake_query

    filled = backfill_checkpoint_snapshots(mock_db, batch_size=10)
    assert filled == 1
    # 验证 messages_snapshot 被设置且包含 id + content
    assert mock_checkpoint.messages_snapshot
    snapshot_msg = mock_checkpoint.messages_snapshot[0]
    assert snapshot_msg["id"] == "msg-1"
    assert snapshot_msg["content"] == "hello"


def test_backfill_is_idempotent(mock_db):
    """回填完成后再次调用应返回 0（无 pending）"""
    from scripts.backfill_checkpoint_snapshots import backfill_checkpoint_snapshots

    mock_db.query.return_value.filter.return_value.count.return_value = 0
    filled = backfill_checkpoint_snapshots(mock_db, batch_size=10)
    assert filled == 0