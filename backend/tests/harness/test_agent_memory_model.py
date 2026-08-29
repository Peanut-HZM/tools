"""AgentMemoryLongTerm ORM 模型测试

TDD: 验证 AgentMemoryLongTerm 模型可实例化、字段默认值正确、唯一约束生效、
updated_at 自动刷新。
"""
import time
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

# 触发 Base.metadata 注册（conftest 的 test_db fixture 通过
# Base.metadata.create_all 建表，必须先 import 模型类）
from app.models.agent_memory import AgentMemoryLongTerm


# === 测试用常量（避免 magic uuid） ===
AGENT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_A = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_B = uuid.UUID("33333333-3333-3333-3333-333333333333")


def test_create_basic_record(test_db):
    """能创建一条带完整字段的记录并读回"""
    record = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_A,
        key="favorite_color",
        value={"color": "blue", "shade": "navy"},
        summary="用户最喜欢蓝色",
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)

    assert record.id is not None
    assert isinstance(record.id, uuid.UUID)
    assert record.agent_id == AGENT_ID
    assert record.user_id == USER_A
    assert record.key == "favorite_color"
    assert record.value == {"color": "blue", "shade": "navy"}
    assert record.summary == "用户最喜欢蓝色"
    assert record.created_at is not None
    assert record.updated_at is not None


def test_unique_constraint_same_triple(test_db):
    """重复的 (agent_id, user_id, key) 触发 IntegrityError"""
    record1 = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_A,
        key="pref_lang",
        value={"lang": "zh"},
    )
    test_db.add(record1)
    test_db.commit()

    record2 = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_A,
        key="pref_lang",
        value={"lang": "en"},
    )
    test_db.add(record2)

    with pytest.raises(IntegrityError):
        test_db.commit()

    # 回滚事务，避免污染后续测试
    test_db.rollback()


def test_same_key_allowed_for_different_users(test_db):
    """相同 (agent_id, key) 但不同 user_id 应允许共存"""
    record1 = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_A,
        key="nickname",
        value={"nick": "小蓝"},
    )
    record2 = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_B,
        key="nickname",
        value={"nick": "小红"},
    )
    test_db.add_all([record1, record2])
    test_db.commit()

    rows = (
        test_db.query(AgentMemoryLongTerm)
        .filter(AgentMemoryLongTerm.key == "nickname")
        .all()
    )
    assert len(rows) == 2
    user_values = {str(r.user_id): r.value["nick"] for r in rows}
    assert user_values[str(USER_A)] == "小蓝"
    assert user_values[str(USER_B)] == "小红"


def test_value_default_empty_jsonb(test_db):
    """不显式传 value 时默认空 dict {}"""
    record = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_A,
        key="empty_test",
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)

    assert record.value == {}


def test_updated_at_auto_refresh_on_update(test_db):
    """更新行时 updated_at 自动刷新"""
    record = AgentMemoryLongTerm(
        agent_id=AGENT_ID,
        user_id=USER_A,
        key="counter",
        value={"n": 0},
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)

    original_updated_at = record.updated_at
    # SQLite 时间戳精度为秒，等待 1 秒以上确保差异可观察
    time.sleep(1.05)

    record.value = {"n": 1}
    test_db.commit()
    test_db.refresh(record)

    assert record.updated_at > original_updated_at, (
        f"updated_at 应自动刷新，原值={original_updated_at} 新值={record.updated_at}"
    )