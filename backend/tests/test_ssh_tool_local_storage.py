"""SSH 工具本地存储改造测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


class TestCreateLocalSSHConfig:
    def test_writes_encrypted_secret_to_local_db(self, local_env):
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService
        from sqlalchemy import text

        result = SSHToolService.create_config(
            "u-ssh",
            CreateSSHRequest(
                alias="local-ssh",
                host="10.0.0.1",
                port=22,
                username="root",
                password="ssh-secret",
            ),
            StorageLocation.LOCAL,
        )

        assert result.storage_location == "local"

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, password_encrypted FROM ssh_configs WHERE id = :i"
            ), {"i": result.id}).first()

        assert row[0] == "LOCAL"
        assert "ssh-secret" not in row[1]
        assert LocalEncryption.decrypt(row[1]) == "ssh-secret"

    def test_private_key_is_encrypted(self, local_env):
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService
        from sqlalchemy import text

        fake_key = "-----BEGIN OPENSSH PRIVATE KEY-----\nFAKE\n-----END OPENSSH PRIVATE KEY-----"
        result = SSHToolService.create_config(
            "u-ssh",
            CreateSSHRequest(
                alias="key-ssh",
                host="10.0.0.2",
                port=22,
                username="root",
                private_key=fake_key,
            ),
            StorageLocation.LOCAL,
        )

        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT private_key_encrypted FROM ssh_configs WHERE id = :i"
            ), {"i": result.id}).first()[0]

        assert "BEGIN OPENSSH" not in cipher
        assert LocalEncryption.decrypt(cipher) == fake_key
