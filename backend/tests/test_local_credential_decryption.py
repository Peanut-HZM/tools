"""本地存储配置的凭据解密回归测试。

回归背景：配置迁移到本地后，K8s 连接全部报 500（"Failed to fetch"），
数据库的 /databases/{id}/decrypt-password 也报 500。

根因：解密时无条件使用服务器密钥 EncryptionUtils，
而本地库密文用本机密钥 LocalEncryption 加密 —— 两把密钥物理隔离，
用错密钥抛 InvalidToken。

本测试覆盖四个工具在 LOCAL 存储下的解密路径：
- database: /databases/{id}/decrypt-password 路由 + _decrypt_for
- k8s:      build_client 构造
- ssh:      _get_connection_secrets
- redis:    _get_config_with_password
"""
import asyncio
import json
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


UID = "u-local"


class TestDatabaseLocalDecryption:
    """数据库本地存储的解密路径"""

    def _create(self):
        from app.models.database_tool_models import CreateDatabaseRequest, DatabaseType
        from app.services.database_tool_service import DatabaseToolService

        req = CreateDatabaseRequest(
            alias="local-db",
            db_type=DatabaseType.POSTGRESQL,
            host="127.0.0.1",
            port=5432,
            database_name="postgres",
            username="u",
            password="secret-pw",
            storage_location="local",
        )
        return DatabaseToolService.create_config(UID, req, StorageLocation.LOCAL)

    def test_decrypt_for_uses_local_key(self, local_env):
        """_decrypt_for 对 LOCAL 行用本机密钥解密"""
        from app.services.database_tool_service import DatabaseToolService
        from app.storage.repository import get_repository

        created = self._create()
        repo = get_repository(StorageLocation.LOCAL, "database")
        row = repo.get(created.id, UID)

        assert row["storage_location"] == "LOCAL"
        assert DatabaseToolService._decrypt_for(row) == "secret-pw"

    def test_get_config_with_password_returns_plaintext(self, local_env):
        """_get_config_with_password 返回 password_decrypted 明文"""
        from app.services.database_tool_service import DatabaseToolService

        created = self._create()
        row = DatabaseToolService._get_config_with_password(created.id, UID)

        assert row["password_decrypted"] == "secret-pw"

    def test_decrypt_password_route_works_for_local_config(self, local_env):
        """POST /databases/{id}/decrypt-password 对本地配置必须 200。

        回归点：该路由曾无条件用服务器密钥 EncryptionUtils.decrypt 硬解，
        本地密文必然 InvalidToken → 500。
        """
        from fastapi.testclient import TestClient

        from app.main import app

        created = self._create()
        client = TestClient(app)
        token = self._make_token(UID)

        response = client.post(
            f"/api/database-tool/databases/{created.id}/decrypt-password",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["password"] == "secret-pw"

    @staticmethod
    def _make_token(user_id: str) -> str:
        from app.services.auth_service import get_auth_service

        return get_auth_service().create_token(user_id, "local-tester")


class TestK8sLocalDecryption:
    """K8s 本地存储的解密路径"""

    def test_build_client_does_not_raise_invalid_token(self, local_env, monkeypatch):
        """build_client 构造本地配置时不得抛 InvalidToken"""
        import kubernetes_asyncio.client as k8s_client

        from app.models.k8s_tool_models import CreateK8sManualRequest
        from app.services.k8s_client_factory import build_client
        from app.services.k8s_tool_service import K8sToolService

        created = K8sToolService.create_config(
            UID,
            CreateK8sManualRequest(
                name="local-cluster",
                server="https://k8s.local:6443",
                auth_type="bearer_token",
                token="my-k8s-token",
            ),
            StorageLocation.LOCAL,
        )
        config = K8sToolService.get_config_by_id(UID, created.id)

        class _FakeApiClient:
            def __init__(self, configuration=None):
                self.configuration = configuration

            async def close(self):
                pass

        monkeypatch.setattr(k8s_client, "ApiClient", _FakeApiClient)
        for api in ("CoreV1Api", "AppsV1Api", "BatchV1Api", "CustomObjectsApi"):
            monkeypatch.setattr(k8s_client, api, lambda *a, **k: object(), raising=False)

        async def _run():
            async with build_client(config) as bundle:
                assert bundle is not None

        asyncio.run(_run())


class TestSshLocalDecryption:
    """SSH 本地存储的解密路径"""

    def test_connection_secrets_use_local_key(self, local_env):
        """_get_connection_secrets 对本地配置返回明文密码"""
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService

        created = SSHToolService.create_config(
            UID,
            CreateSSHRequest(
                alias="local-ssh",
                host="127.0.0.1",
                port=22,
                username="u",
                password="ssh-pw",
                storage_location="local",
            ),
            StorageLocation.LOCAL,
        )

        config = SSHToolService._get_config_record(created.id, UID)
        password, private_key, passphrase = SSHToolService._get_connection_secrets(config)

        assert password == "ssh-pw"
        assert private_key is None
        assert passphrase is None


class TestRedisLocalDecryption:
    """Redis 本地存储的解密路径"""

    def test_config_with_password_returns_plaintext(self, local_env):
        """_get_config_with_password 对本地配置返回明文密码"""
        from app.models.redis_tool_models import CreateRedisRequest
        from app.services.redis_tool_service import RedisToolService

        created = RedisToolService.create_config(
            UID,
            CreateRedisRequest(
                alias="local-redis",
                host="127.0.0.1",
                port=6379,
                username="",
                password="redis-pw",
                storage_location="local",
            ),
            StorageLocation.LOCAL,
        )

        row = RedisToolService._get_config_with_password(created.id, UID)

        assert row["password_decrypted"] == "redis-pw"


class TestServerKeyPathUnaffected:
    """服务器侧配置仍走服务器密钥，本次修复不得破坏"""

    def test_decrypt_sensitive_uses_server_key(self, monkeypatch):
        from app.services.k8s_client_factory import _decrypt_sensitive

        seen = {}

        class _FakeEncryption:
            @staticmethod
            def decrypt(cipher):
                seen["cipher"] = cipher
                return "server-plain"

        monkeypatch.setattr(
            "app.services.k8s_client_factory.EncryptionUtils", _FakeEncryption
        )

        config = {
            "storage_location": "SERVER",
            "auth_data_encrypted": "server-side-cipher",
        }

        assert _decrypt_sensitive(config, "auth_data_encrypted") == "server-plain"
        assert seen["cipher"] == "server-side-cipher"
