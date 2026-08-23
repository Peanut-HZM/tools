"""
Task 1.5.3 — LLMProviderService 单元测试

使用 SQLite 内存 DB，每个用例一个干净 session。
覆盖范围：
  ✓ 创建 / 查询 / 列表 / 更新 / 删除
  ✓ api_key 加密存储 + reveal 解密
  ✓ api_key_suffix 自动记录
  ✓ api_key_hash 存储（SHA-256 32 字节）
  ✓ get_by_api_key 幂等检索
  ✓ exists_by_api_key 去重查询
  ✓ create_provider 重复 api_key 抛 ValueError
  ✓ set_active 启用 / 禁用
  ✓ delete_provider 有子记录时拒绝
  ✓ list_providers active_only 过滤
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

# 确保 backend 目录在 sys.path（兼容 IDE / pytest 两种启动方式）
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.llm_provider_service import LLMProviderService, _hash_api_key


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ============================================================
# 创建 & 列表
# ============================================================

class TestCreateAndListProvider:
    def test_create_and_list_provider(self, db_session):
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="OpenAI",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-xxx",
        )
        assert p.id is not None
        assert svc.list_providers()[0].name == "OpenAI"

    def test_api_key_is_encrypted_in_db(self, db_session):
        """api_key_encrypted 存的是密文，不是明文"""
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-secret-key",
        )
        # 数据库字段不应包含明文
        assert "sk-secret-key" not in p.api_key_encrypted
        # suffix 应为末 4 位
        assert p.api_key_suffix == "-key"

    def test_reveal_api_key_returns_plaintext(self, db_session):
        """reveal_api_key 能正确解出明文"""
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-secret-key",
        )
        assert svc.reveal_api_key(str(p.id)) == "sk-secret-key"

    def test_list_providers_active_only(self, db_session):
        svc = LLMProviderService(db_session)
        svc.create_provider(
            name="active", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-a",
        )
        svc.create_provider(
            name="inactive", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-b", is_active=False,
        )
        all_list = svc.list_providers()
        active_list = svc.list_providers(active_only=True)
        assert len(all_list) == 2
        assert len(active_list) == 1
        assert active_list[0].name == "active"

    def test_create_provider_stores_hash(self, db_session):
        """创建后 api_key_hash 是 32 字节 SHA-256"""
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-test-key",
        )
        assert p.api_key_hash is not None
        assert isinstance(p.api_key_hash, bytes)
        assert len(p.api_key_hash) == 32
        # 与直接计算 SHA-256 一致
        assert p.api_key_hash == _hash_api_key("sk-test-key")

    def test_get_by_api_key_finds_existing(self, db_session):
        """明文 key 通过 hash 检索能找到"""
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-find-me",
        )
        found = svc.get_by_api_key("sk-find-me")
        assert found is not None
        assert found.id == p.id

    def test_get_by_api_key_returns_none_for_missing(self, db_session):
        """不存在的 key 返回 None"""
        svc = LLMProviderService(db_session)
        svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-exists",
        )
        assert svc.get_by_api_key("sk-does-not-exist") is None

    def test_exists_by_api_key_true_and_false(self, db_session):
        svc = LLMProviderService(db_session)
        svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-dup",
        )
        assert svc.exists_by_api_key("sk-dup") is True
        assert svc.exists_by_api_key("sk-other") is False

    def test_create_provider_duplicate_api_key_raises(self, db_session):
        """重复 api_key 创建应抛 ValueError"""
        svc = LLMProviderService(db_session)
        svc.create_provider(
            name="first", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-same-key",
        )
        with pytest.raises(ValueError, match="already exists"):
            svc.create_provider(
                name="second", provider_type="openai",
                base_url="https://api.example.com/v1", api_key="sk-same-key",
            )


# ============================================================
# 更新
# ============================================================

class TestUpdateProvider:
    def test_update_name(self, db_session):
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="old", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-old",
        )
        updated = svc.update_provider(str(p.id), name="new")
        assert updated.name == "new"

    def test_update_api_key_rotates_encrypted_and_suffix(self, db_session):
        """更新 api_key 时，加密字段和 suffix 应同步刷新"""
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-old-key",
        )
        updated = svc.update_provider(str(p.id), api_key="sk-new-password")
        # suffix 应为新 key 末 4 位
        assert updated.api_key_suffix == "word"
        # reveal 应返回新明文
        assert svc.reveal_api_key(str(p.id)) == "sk-new-password"

    def test_set_active(self, db_session):
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-x",
        )
        assert p.is_active is True
        svc.set_active(str(p.id), False)
        refreshed = svc.get_provider(str(p.id))
        assert refreshed.is_active is False

    def test_update_nonexistent_returns_none(self, db_session):
        svc = LLMProviderService(db_session)
        result = svc.update_provider(str(uuid.uuid4()), name="ghost")
        assert result is None


# ============================================================
# 删除
# ============================================================

class TestDeleteProvider:
    def test_delete_provider_no_children(self, db_session):
        svc = LLMProviderService(db_session)
        p = svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-x",
        )
        assert svc.delete_provider(str(p.id)) is True
        assert svc.get_provider(str(p.id)) is None

    def test_delete_provider_with_linked_models_fails(self, db_session):
        """有模型关联时不允许删除"""
        p_svc = LLMProviderService(db_session)
        m_svc = _import_model_service()
        p = p_svc.create_provider(
            name="X", provider_type="openai",
            base_url="https://api.example.com/v1", api_key="sk-x",
        )
        m_svc(db_session).create_model(
            name="gpt-4o", model_name="gpt-4o", provider_id=p.id, category="chat",
        )
        with pytest.raises(ValueError, match="存在关联模型"):
            p_svc.delete_provider(str(p.id))

    def test_delete_nonexistent_returns_false(self, db_session):
        svc = LLMProviderService(db_session)
        assert svc.delete_provider(str(uuid.uuid4())) is False


# ============================================================
# 辅助
# ============================================================

def _import_model_service():
    """延迟返回 LLMModelService 类（避免顶层循环导入）"""
    from app.services.llm_model_service import LLMModelService
    return LLMModelService
