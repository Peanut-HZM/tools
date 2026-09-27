"""
app_secrets（key-in-DB 主密钥存储）单元测试

覆盖范围：
  ✓ 环境变量逃生舱 TOOLBOX_APP_SECRET_HEX（测试/离线场景）
  ✓ 独立 SQLite 库上首次访问自动建表 + 生成密钥
  ✓ 二次读取返回同一密钥（幂等）
  ✓ 不同 key_id 相互独立
  ✓ 环境变量逃生舱非法值报错
  ✓ encrypt_api_key / decrypt_api_key 往返 + v1 前缀
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine

from app.core.app_secrets import (
    ENV_OVERRIDE,
    clear_secret_cache,
    get_or_create_secret,
)
from app.core.security import decrypt_api_key, encrypt_api_key


@pytest.fixture
def sqlite_engine():
    """每用例独立 SQLite 内存库，并清空进程内密钥缓存"""
    clear_secret_cache()
    engine = create_engine("sqlite://")
    yield engine
    clear_secret_cache()


class TestEnvOverride:
    def setup_method(self):
        clear_secret_cache()

    def teardown_method(self):
        os.environ.pop(ENV_OVERRIDE, None)
        clear_secret_cache()

    def test_override_returns_deterministic_key(self):
        os.environ[ENV_OVERRIDE] = "cd" * 32
        key1 = get_or_create_secret("llm_master_key")
        key2 = get_or_create_secret("llm_master_key")
        assert key1 == bytes.fromhex("cd" * 32)
        assert key1 == key2

    def test_override_rejects_non_hex(self):
        os.environ[ENV_OVERRIDE] = "not-hex-value"
        with pytest.raises(ValueError):
            get_or_create_secret("llm_master_key")

    def test_override_rejects_wrong_length(self):
        os.environ[ENV_OVERRIDE] = "ab" * 16  # 16 字节，不是 32
        with pytest.raises(ValueError):
            get_or_create_secret("llm_master_key")


class TestKeyInDb:
    def test_first_access_creates_and_persists(self, sqlite_engine):
        key1 = get_or_create_secret("llm_master_key", engine=sqlite_engine)
        assert len(key1) == 32
        # 二次读取（同一 engine）返回同一把密钥
        key2 = get_or_create_secret("llm_master_key", engine=sqlite_engine)
        assert key1 == key2

    def test_different_key_ids_independent(self, sqlite_engine):
        key_a = get_or_create_secret("llm_master_key", engine=sqlite_engine)
        key_b = get_or_create_secret("openclaw_master_key", engine=sqlite_engine)
        assert key_a != key_b

    def test_persisted_in_db(self, sqlite_engine):
        """密钥确实写入数据库，且库中值与返回值一致"""
        from sqlalchemy import text

        key = get_or_create_secret("llm_master_key", engine=sqlite_engine)
        with sqlite_engine.connect() as conn:
            row = conn.execute(
                text("SELECT secret_value FROM app_secrets WHERE key_id = 'llm_master_key'")
            ).scalar()
        assert row is not None
        assert bytes.fromhex(row) == key


class TestEncryptDecryptRoundTrip:
    def test_round_trip_with_v1_prefix(self):
        plaintext = "sk-test-1234567890abcdef"
        encrypted = encrypt_api_key(plaintext)
        assert encrypted.startswith("v1:")
        assert decrypt_api_key(encrypted) == plaintext

    def test_round_trip_unicode(self):
        plaintext = "密钥内容-🎉-abc123"
        assert decrypt_api_key(encrypt_api_key(plaintext)) == plaintext

    def test_ciphertext_not_reversible_without_key(self):
        """密文不含明文特征"""
        encrypted = encrypt_api_key("sk-very-secret-value")
        assert "very-secret" not in encrypted

    def test_unique_ciphertext_per_call(self):
        """AES-GCM 随机 IV：同一明文两次加密密文不同"""
        assert encrypt_api_key("same") != encrypt_api_key("same")

    def test_decrypt_garbage_raises(self):
        """伪造/损坏密文必须报错（InvalidTag），不得静默返回"""
        with pytest.raises(Exception):
            decrypt_api_key("v1:" + uuid.uuid4().hex)
