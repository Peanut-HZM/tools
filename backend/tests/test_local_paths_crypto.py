"""本地存储路径与本地加密器测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.paths import (
    get_local_data_dir,
    get_local_db_path,
    get_local_key_path,
)
from app.storage.crypto import LocalEncryption


class TestLocalPaths:
    def test_data_dir_under_real_home(self, monkeypatch, tmp_path):
        """本地目录必须基于真实家目录，而不是被覆盖的 HOME"""
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        # 模拟 config.py 的 HOME 覆盖（假家目录）
        monkeypatch.setenv("HOME", "/fake/cache/dir")

        data_dir = get_local_data_dir()

        assert data_dir == tmp_path / ".toolbox"
        assert data_dir.exists()

    def test_db_and_key_paths(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))

        assert get_local_db_path() == tmp_path / ".toolbox" / "toolbox.db"
        assert get_local_key_path() == tmp_path / ".toolbox" / "encryption.key"


class TestLocalEncryption:
    def test_encrypt_decrypt_roundtrip(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()

        plain = "my-secret-password"
        cipher = LocalEncryption.encrypt(plain)

        assert cipher != plain
        assert LocalEncryption.decrypt(cipher) == plain

    def test_key_file_created(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()

        LocalEncryption.encrypt("x")

        assert get_local_key_path().exists()
        assert get_local_key_path().stat().st_size > 0

    def test_empty_string_returns_empty(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()

        assert LocalEncryption.encrypt("") == ""
        assert LocalEncryption.decrypt("") == ""

    def test_decrypt_with_wrong_key_raises(self, monkeypatch, tmp_path):
        """密钥不匹配时必须抛异常，禁止返回假明文"""
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()
        cipher = LocalEncryption.encrypt("secret")

        # 换一把密钥
        get_local_key_path().write_text("0" * 64, encoding="utf-8")
        LocalEncryption.reset_cipher_suite()

        with pytest.raises(Exception):
            LocalEncryption.decrypt(cipher)
