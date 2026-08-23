"""ImageGenSelfDevConversation 模型测试

使用 SQLite 内存 DB，每个用例一个干净 session（与 test_image_gen_record_backend.py 同模式）。
"""

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_gen_conversation import ImageGenSelfDevConversation


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
    """SQLite 无 JSONB 类型，降级为 JSON（与 conftest.py 的 INET 处理同模式）。

    仅影响 SQLite 测试库 DDL 编译，不触碰生产 PostgreSQL 模型。
    """
    return "JSON"

BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_conversation_creation(db_session):
    """能创建并落盘"""
    conv = ImageGenSelfDevConversation(
        user_id=uuid.uuid4(),
        conversation_id=str(uuid.uuid4()),
        operation="text2img",
        messages=[{"role": "user", "content": "hello"}],
    )
    db_session.add(conv)
    db_session.commit()

    fetched = db_session.query(ImageGenSelfDevConversation).filter_by(
        conversation_id=conv.conversation_id
    ).first()
    assert fetched is not None
    assert fetched.messages[0]["role"] == "user"


def test_conversation_unique(db_session):
    """conversation_id 唯一"""
    cid = str(uuid.uuid4())
    c1 = ImageGenSelfDevConversation(
        user_id=uuid.uuid4(),
        conversation_id=cid,
        operation="text2img",
        messages=[],
    )
    c2 = ImageGenSelfDevConversation(
        user_id=uuid.uuid4(),
        conversation_id=cid,
        operation="text2img",
        messages=[],
    )
    db_session.add(c1)
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
