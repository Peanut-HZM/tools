"""
验证 Message.llm_config_id 列已解除对 llm_configs 表的 FK 约束。

背景（Task 1.5.2 Critical fix）：
v1 起消费者改读 llm_models 表，chat_stream.py 现在写入 LLMModel.id 到
Message.llm_config_id；若该列仍声明 ForeignKey("llm_configs.id")，
commit 时会触发 IntegrityError。

本测试文件验证 ORM 层面 FK 已移除，Message 实例可自由持有任意 UUID
（模拟 LLMModel.id），不会触发 FK 验证。
"""
import os
import sys
import uuid
import pytest
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import INET

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@compiles(INET, "sqlite")
def _compile_inet_for_sqlite(element, compiler, **kw):
    return "VARCHAR(45)"


from app.models.base import Base
from app.models.message import Message
from app.models.conversation import Conversation


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_conversation(session):
    """创建一条最小可用的 Conversation（Message 必须有 conversation_id）"""
    conv = Conversation(
        id=uuid.uuid4(),
        user_id="test-user-1",  # Conversation.user_id 为 String(64)，非 UUID
        title="test conv",
        current_stage="init",
        version=1,
    )
    session.add(conv)
    session.commit()
    return conv


def test_message_llm_config_id_accepts_arbitrary_uuid(db_session):
    """
    Message.llm_config_id 可写入任意 UUID（模拟 LLMModel.id），
    不会触发 FK IntegrityError。
    """
    conv = _make_conversation(db_session)

    # 故意使用一个「不存在」于任何表的 UUID，模拟 LLMModel.id
    fake_llm_model_id = uuid.uuid4()

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        sender_type="agent",
        content="hello from agent",
        llm_config_id=fake_llm_model_id,
        llm_model_name="gpt-4o",
    )
    db_session.add(msg)
    # 如果 FK 仍存在，这里会抛 IntegrityError
    db_session.commit()

    loaded = db_session.query(Message).filter_by(id=msg.id).one()
    assert loaded.llm_config_id == fake_llm_model_id
    assert loaded.llm_model_name == "gpt-4o"


def test_message_schema_has_no_fk_on_llm_config_id():
    """
    静态检查：Message 表 DDL 中 llm_config_id 列不应存在 FK 约束。
    通过 SQLAlchemy inspect 验证元数据层面 FK 已移除。
    """
    fk_targets = [
        fk.column.table.name
        for fk in Message.__table__.c.llm_config_id.foreign_keys
    ]
    assert "llm_configs" not in fk_targets, (
        f"Message.llm_config_id 不应再指向 llm_configs，实际 FK 目标：{fk_targets}"
    )


def test_message_llm_config_id_nullable(db_session):
    """llm_config_id 允许为 NULL（用户消息不需要记录模型）"""
    conv = _make_conversation(db_session)

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        sender_type="user",
        content="user message",
        llm_config_id=None,
    )
    db_session.add(msg)
    db_session.commit()

    loaded = db_session.query(Message).filter_by(id=msg.id).one()
    assert loaded.llm_config_id is None
