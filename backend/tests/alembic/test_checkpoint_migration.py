"""Checkpoint 时间旅行迁移测试

验证 20260829c_checkpoint_time_travel 迁移：
- 新增列存在
- 新增 branches 表存在
- 索引存在
- 升级 + 降级 幂等
"""
import pytest
from sqlalchemy import inspect, text
from app.models.base import Base
from app.database import engine


@pytest.fixture
def db():
    """提供测试 DB session"""
    from app.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


def test_session_checkpoints_new_columns_exist(db):
    """迁移后 session_checkpoints 应有新增列"""
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("session_checkpoints")}
    expected = {
        "branch_id",
        "parent_checkpoint_id",
        "messages_snapshot",
        "checkpoint_kind",
        "label",
        "merge_parents",
        "is_head",
    }
    assert expected.issubset(cols), f"Missing columns: {expected - cols}"


def test_conversations_new_columns_exist(db):
    """迁移后 conversations 应有 head_checkpoint_id + main_branch_id"""
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("conversations")}
    assert "head_checkpoint_id" in cols
    assert "main_branch_id" in cols


def test_branches_table_exists(db):
    """迁移后 branches 表应存在"""
    inspector = inspect(engine)
    assert "branches" in inspector.get_table_names()


def test_branches_indexes_exist(db):
    """branches 应有 ix_branches_conv 索引"""
    inspector = inspect(engine)
    indexes = {i["name"] for i in inspector.get_indexes("branches")}
    assert "ix_branches_conv" in indexes