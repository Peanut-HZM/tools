"""
Task 1.5.3 — LLMModelService 单元测试

使用 SQLite 内存 DB，每个用例一个干净 session。
覆盖范围：
  ✓ 创建 / 查询 / 列表（按 provider / 按 category / active_only）
  ✓ 更新 / 删除
  ✓ set_default（全局）—— 唯一性约束
  ✓ set_default（分类）—— 同 category 唯一性约束
  ✓ create_model 时 is_default=True 自动清理其他 default
  ✓ get_default_model 按 category / 全局
"""

import sys
import uuid
import pytest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.core.security import encrypt_api_key

BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.llm_provider_service import LLMProviderService
from app.services.llm_model_service import LLMModelService


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_provider(session, *, name="p1", provider_type="openai", key_suffix="1234"):
    svc = LLMProviderService(session)
    return svc.create_provider(
        name=name, provider_type=provider_type,
        base_url="https://api.example.com/v1", api_key=f"sk-{key_suffix}",
    )


# ============================================================
# 创建 & 查询
# ============================================================

class TestCreateAndGetModel:
    def test_create_and_get_model(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m = svc.create_model(
            name="gpt-4o", model_name="gpt-4o",
            provider_id=p.id, category="chat",
        )
        assert m.id is not None
        found = svc.get_model(str(m.id))
        assert found.name == "gpt-4o"
        assert found.category == "chat"

    def test_list_models_by_category(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        svc.create_model(name="c1", model_name="c1", provider_id=p.id, category="chat")
        svc.create_model(name="c2", model_name="c2", provider_id=p.id, category="chat")
        svc.create_model(name="i1", model_name="i1", provider_id=p.id, category="image")
        assert len(svc.list_models(category="chat")) == 2
        assert len(svc.list_models(category="image")) == 1

    def test_list_models_by_provider(self, db_session):
        p1 = _seed_provider(db_session, name="p1", key_suffix="aaa")
        p2 = _seed_provider(db_session, name="p2", key_suffix="bbb")
        svc = LLMModelService(db_session)
        svc.create_model(name="m1", model_name="m1", provider_id=p1.id, category="chat")
        svc.create_model(name="m2", model_name="m2", provider_id=p2.id, category="chat")
        assert len(svc.list_by_provider(str(p1.id))) == 1
        assert len(svc.list_by_category("chat")) == 2

    def test_list_models_active_only(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        svc.create_model(name="active", model_name="active", provider_id=p.id, category="chat")
        svc.create_model(name="inactive", model_name="inactive", provider_id=p.id, category="chat", is_active=False)
        assert len(svc.list_models(active_only=True)) == 1
        assert len(svc.list_models()) == 2


# ============================================================
# 默认模型（全局 & 分类）
# ============================================================

class TestDefaultModel:
    def test_get_default_model_global(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        svc.create_model(name="normal", model_name="normal", provider_id=p.id, category="chat")
        m = svc.create_model(
            name="default", model_name="default", provider_id=p.id,
            category="chat", is_default=True,
        )
        found = svc.get_default_model()
        assert found is not None
        assert found.id == m.id

    def test_get_default_model_by_category(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m = svc.create_model(
            name="polish", model_name="qwen-turbo", provider_id=p.id,
            category="image_polish", is_default_for_category=True,
        )
        found = svc.get_default_model("image_polish")
        assert found is not None
        assert found.id == m.id

    def test_set_default_uniqueness(self, db_session):
        """设置某个 model 为全局 default 时，其他记录的 is_default 应被清为 False"""
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m1 = svc.create_model(
            name="old-default", model_name="old-default",
            provider_id=p.id, category="chat", is_default=True,
        )
        m2 = svc.create_model(
            name="new-default", model_name="new-default",
            provider_id=p.id, category="chat",
        )
        # m1 此时是全局 default
        assert svc.get_default_model().id == m1.id

        # 切换 default 到 m2
        svc.set_default(str(m2.id))
        # m2 现在是全局 default
        assert svc.get_default_model().id == m2.id
        # m1 已不是 default
        db_session.refresh(m1)
        assert m1.is_default is False

    def test_set_default_for_category_uniqueness(self, db_session):
        """设置分类 default 时，同 category 其他记录应被清为 False"""
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m1 = svc.create_model(
            name="old-cat-default", model_name="old-cat-default",
            provider_id=p.id, category="image_polish",
            is_default_for_category=True,
        )
        m2 = svc.create_model(
            name="new-cat-default", model_name="new-cat-default",
            provider_id=p.id, category="image_polish",
        )
        # m1 是 image_polish 分类 default
        assert svc.get_default_model("image_polish").id == m1.id

        # 切换分类 default 到 m2
        svc.set_default(str(m2.id), category="image_polish")
        assert svc.get_default_model("image_polish").id == m2.id
        db_session.refresh(m1)
        assert m1.is_default_for_category is False

    def test_create_model_with_is_default_clears_others(self, db_session):
        """create_model 时传入 is_default=True，应自动清掉其他 default"""
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m1 = svc.create_model(
            name="first-default", model_name="first-default",
            provider_id=p.id, category="chat", is_default=True,
        )
        m2 = svc.create_model(
            name="second-default", model_name="second-default",
            provider_id=p.id, category="chat", is_default=True,
        )
        # 应只有一个全局 default
        db_session.refresh(m1)
        assert m1.is_default is False
        assert m2.is_default is True

    def test_set_default_nonexistent_returns_false(self, db_session):
        svc = LLMModelService(db_session)
        assert svc.set_default(str(uuid.uuid4())) is False

    def test_get_default_model_none_when_empty(self, db_session):
        svc = LLMModelService(db_session)
        assert svc.get_default_model() is None
        assert svc.get_default_model("chat") is None


# ============================================================
# 更新 & 删除
# ============================================================

class TestUpdateAndDeleteModel:
    def test_update_model_name(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m = svc.create_model(name="old", model_name="old", provider_id=p.id, category="chat")
        updated = svc.update_model(str(m.id), name="new")
        assert updated.name == "new"

    def test_delete_model(self, db_session):
        p = _seed_provider(db_session)
        svc = LLMModelService(db_session)
        m = svc.create_model(name="x", model_name="x", provider_id=p.id, category="chat")
        assert svc.delete_model(str(m.id)) is True
        assert svc.get_model(str(m.id)) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        svc = LLMModelService(db_session)
        assert svc.delete_model(str(uuid.uuid4())) is False

    def test_update_nonexistent_returns_none(self, db_session):
        svc = LLMModelService(db_session)
        assert svc.update_model(str(uuid.uuid4()), name="ghost") is None
