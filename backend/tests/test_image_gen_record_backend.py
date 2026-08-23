"""ImageGenHistory.backend 字段测试

使用 SQLite 内存 DB，每个用例一个干净 session（与 test_llm_model_priority.py 同模式）。

注：任务简报中的 `ImageGenRecord` 对应现有 `ImageGenHistory` 模型
（表 image_gen_history，自研/Dify 共用，见设计文档 2.2 节不变量 3）。
"""

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_generation_models import ImageGenHistory

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


def test_record_has_backend_default(db_session):
    """新建记录 backend 默认 'dify'"""
    record = ImageGenHistory(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        operation="text2img",
        prompt="a cat",
        status="success",
        result_oss_key="oss/result/a-cat.png",
    )
    db_session.add(record)
    db_session.flush()

    assert record.backend == "dify"


def test_record_backend_selfdev(db_session):
    """显式设置 selfdev 应持久化"""
    record = ImageGenHistory(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        operation="text2img",
        prompt="a cat",
        status="success",
        result_oss_key="oss/result/a-cat.png",
        backend="selfdev",
    )
    db_session.add(record)
    db_session.commit()

    fetched = db_session.query(ImageGenHistory).filter_by(prompt="a cat").first()
    assert fetched is not None
    assert fetched.backend == "selfdev"
