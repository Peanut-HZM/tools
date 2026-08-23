"""ConversationRepository 测试

使用 SQLite 内存 DB，每个用例一个干净 session。
验证 save / load / load_by_id 三个方法，包括：
- 新建对话
- 多消息落盘
- 同 conversation_id 重复 save → update 而非 insert
- load_by_id 的用户隔离：同 conversation_id 不同 user_id 返回空
- user_id 兼容 UUID 和 str 两种入参
"""

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_gen_conversation import ImageGenSelfDevConversation
from app.services.image_gen.conversation_repo import ConversationRepository


# SQLite 无 JSONB，降级为 JSON（与 test_image_gen_conversation_model.py 同模式）
@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
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


# user_id 使用 str(uuid.uuid4())，与模型 String(64) 列一致
@pytest.mark.asyncio
async def test_save_new_conversation(db_session):
    """save 新对话后 load 可读到消息"""
    repo = ConversationRepository(db=db_session)
    user_id = str(uuid.uuid4())
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=user_id,
        conversation_id=cid,
        operation="text2img",
        messages=[{"role": "user", "content": "hello"}],
    )

    loaded = await repo.load(cid)
    assert loaded[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_load_returns_messages(db_session):
    """多条消息按顺序落盘"""
    repo = ConversationRepository(db=db_session)
    user_id = str(uuid.uuid4())
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=user_id,
        conversation_id=cid,
        operation="text2img",
        messages=[
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ],
    )

    loaded = await repo.load(cid)
    assert len(loaded) == 2


@pytest.mark.asyncio
async def test_save_updates_existing(db_session):
    """同一 conversation_id 重复 save → update，不 insert"""
    repo = ConversationRepository(db=db_session)
    user_id = str(uuid.uuid4())
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=user_id,
        conversation_id=cid,
        operation="text2img",
        messages=[{"role": "user", "content": "a"}],
    )
    await repo.save(
        user_id=user_id,
        conversation_id=cid,
        operation="text2img",
        messages=[
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ],
    )

    loaded = await repo.load(cid)
    assert len(loaded) == 2


@pytest.mark.asyncio
async def test_load_by_id_user_isolation(db_session):
    """load_by_id 强制 user_id 匹配；不匹配返回空"""
    repo = ConversationRepository(db=db_session)
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=user_a,
        conversation_id=cid,
        operation="text2img",
        messages=[{"role": "user", "content": "secret"}],
    )

    # 正确的 user_id → 能读到
    assert len(await repo.load_by_id(cid, user_a)) == 1
    # 错误的 user_id → 返回空（隔离）
    assert await repo.load_by_id(cid, user_b) == []


@pytest.mark.asyncio
async def test_load_by_id_accepts_uuid(db_session):
    """load_by_id 支持传入 uuid.UUID 对象（自动转 str）"""
    repo = ConversationRepository(db=db_session)
    # 注意：模型 user_id 列为 String(64)，存储时 _to_str_user_id 会把 UUID 转 str
    uid = uuid.uuid4()
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=uid,  # UUID 对象
        conversation_id=cid,
        operation="text2img",
        messages=[{"role": "user", "content": "x"}],
    )

    # 用同 UUID 对象查询 → 能读到
    loaded = await repo.load_by_id(cid, uid)
    assert len(loaded) == 1
    # 用 str(uid) 查询 → 也能读到（因为入库时已转 str）
    loaded2 = await repo.load_by_id(cid, str(uid))
    assert len(loaded2) == 1


@pytest.mark.asyncio
async def test_load_nonexistent_returns_empty(db_session):
    """不存在的 conversation_id 返回空列表"""
    repo = ConversationRepository(db=db_session)
    assert await repo.load("nonexistent") == []
    assert await repo.load_by_id("nonexistent", str(uuid.uuid4())) == []
