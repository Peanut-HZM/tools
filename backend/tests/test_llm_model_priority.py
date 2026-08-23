"""LLMModel.priority 字段测试

使用 SQLite 内存 DB，每个用例一个干净 session（与 test_llm_model_service.py 同模式）。
"""

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider

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


def test_llm_model_has_priority_default(db_session):
    """新增 LLMModel 时 priority 默认 100"""
    provider = LLMProvider(
        id=uuid.uuid4(),
        name="test-provider",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="dummy",
        api_key_suffix="xyz0",
        api_key_hash=b"hash-xyz",
    )
    db_session.add(provider)
    db_session.flush()

    model = LLMModel(
        id=uuid.uuid4(),
        name="test-model",
        model_name="gpt-4",
        provider_id=provider.id,
        category="chat",
    )
    db_session.add(model)
    db_session.flush()

    assert model.priority == 100


def test_llm_model_priority_persisted(db_session):
    """显式设置 priority 后应持久化"""
    provider = LLMProvider(
        id=uuid.uuid4(),
        name="p",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="dummy",
        api_key_suffix="xyz0",
        api_key_hash=b"hash-abc",
    )
    db_session.add(provider)
    db_session.flush()

    model = LLMModel(
        id=uuid.uuid4(),
        name="m",
        model_name="gpt-4",
        provider_id=provider.id,
        category="chat",
        priority=10,
    )
    db_session.add(model)
    db_session.commit()

    fetched = db_session.query(LLMModel).filter_by(name="m").first()
    assert fetched is not None
    assert fetched.priority == 10
