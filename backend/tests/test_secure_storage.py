"""
统一安全存储（app.utils.secure_storage）单元测试

覆盖范围：
  ✓ encrypt_text / decrypt_text 往返一致
  ✓ 密文带 enc:v1: 前缀，且 is_encrypted 可判定
  ✓ 历史明文数据（原样返回，不报错）
  ✓ 空值 / None 处理
  ✓ 密文损坏时抛 SecureStorageError（不静默返回原文）
  ✓ 不同明文产生不同密文（随机 IV）
"""

import os

import pytest

from app.core.app_secrets import ENV_OVERRIDE, clear_secret_cache
from app.utils.secure_storage import (
    CIPHER_PREFIX,
    SecureStorageError,
    decrypt_text,
    encrypt_text,
    is_encrypted,
)


@pytest.fixture(autouse=True)
def fixed_master_key():
    """用逃生舱环境变量提供固定主密钥，避免测试依赖数据库"""
    clear_secret_cache()
    os.environ[ENV_OVERRIDE] = "ab" * 32
    yield
    os.environ.pop(ENV_OVERRIDE, None)
    clear_secret_cache()


class TestRoundTrip:
    def test_round_trip(self):
        plain = "hello-敏感内容-2026"
        cipher = encrypt_text(plain)
        assert cipher != plain
        assert decrypt_text(cipher) == plain

    def test_cipher_has_prefix(self):
        cipher = encrypt_text("x")
        assert cipher.startswith(CIPHER_PREFIX)
        assert is_encrypted(cipher) is True

    def test_plain_is_not_encrypted(self):
        assert is_encrypted("plain text") is False
        assert is_encrypted("") is False
        assert is_encrypted(None) is False

    def test_random_iv_produces_different_cipher(self):
        assert encrypt_text("same") != encrypt_text("same")

    def test_unicode_round_trip(self):
        plain = "中文内容 with emoji 🎉 and 换行\n第二行"
        assert decrypt_text(encrypt_text(plain)) == plain


class TestLegacyPlaintext:
    """历史明文数据（加密功能上线前写入）必须原样返回"""

    def test_legacy_plaintext_returned_as_is(self):
        assert decrypt_text("legacy-plain-value") == "legacy-plain-value"

    def test_legacy_plaintext_not_marked_encrypted(self):
        assert is_encrypted("legacy-plain-value") is False


class TestEdgeCases:
    def test_empty_string(self):
        assert encrypt_text("") == ""
        assert decrypt_text("") == ""

    def test_none(self):
        assert encrypt_text(None) is None
        assert decrypt_text(None) is None


class TestErrorHandling:
    """损坏密文必须真实报错，不能静默返回原文"""

    def test_corrupted_cipher_raises(self):
        with pytest.raises(SecureStorageError):
            decrypt_text(CIPHER_PREFIX + "Z" * 60)

    def test_invalid_base64_raises(self):
        with pytest.raises(SecureStorageError):
            decrypt_text(CIPHER_PREFIX + "!!!not-base64!!!")

    def test_error_message_is_actionable(self):
        with pytest.raises(SecureStorageError) as exc:
            decrypt_text(CIPHER_PREFIX + "Z" * 60)
        assert "重新" in str(exc.value)
