"""K8s 本地存储配置的凭据解密回归测试。

回归背景：配置迁移到本地后，K8s 连接全部报 500（前端显示 "Failed to fetch"）。

根因：build_client 无条件用服务器密钥 EncryptionUtils 解密，
而本地库密文用本机密钥 LocalEncryption 加密 —— 两把密钥物理隔离，
用错密钥抛 InvalidToken。

本测试覆盖：
1. 本地配置能用本机密钥解密出明文（不抛 InvalidToken）
2. build_client 走本地配置时不再抛 InvalidToken
3. 服务器侧配置仍用服务器密钥解密（不因本次修复被破坏）
"""
import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.k8s_tool_models import CreateK8sManualRequest
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


def _make_request(**overrides):
    payload = {
        "name": "local-cluster",
        "server": "https://k8s.local:6443",
        "auth_type": "bearer_token",
        "token": "my-k8s-token",
    }
    payload.update(overrides)
    return CreateK8sManualRequest(**payload)


class TestLocalCredentialDecryption:
    """本地配置必须能用本机密钥解密"""

    def test_get_config_by_id_returns_plaintext(self, local_env):
        """get_config_by_id 必须返回明文（用 get_with_secret，而不是 get）"""
        from app.services.k8s_tool_service import K8sToolService

        created = K8sToolService.create_config(
            "u-k8s", _make_request(), StorageLocation.LOCAL
        )

        config = K8sToolService.get_config_by_id("u-k8s", created.id)

        assert config is not None
        assert "auth_data_decrypted" in config
        assert json.loads(config["auth_data_decrypted"])["token"] == "my-k8s-token"

    def test_build_client_does_not_raise_invalid_token(self, local_env, monkeypatch):
        """build_client 构造本地配置时不得抛 InvalidToken。

        构造真实客户端需要连集群，这里只验证解密阶段不失败：
        把 ApiClient 的创建替换掉，解密通过即视为成功。
        """
        import kubernetes_asyncio.client as k8s_client

        from app.services.k8s_client_factory import build_client
        from app.services.k8s_tool_service import K8sToolService

        created = K8sToolService.create_config(
            "u-k8s", _make_request(), StorageLocation.LOCAL
        )
        config = K8sToolService.get_config_by_id("u-k8s", created.id)

        class _FakeApiClient:
            def __init__(self, configuration=None):
                self.configuration = configuration

            async def close(self):
                pass

        monkeypatch.setattr(k8s_client, "ApiClient", _FakeApiClient)
        monkeypatch.setattr(
            k8s_client, "CoreV1Api", lambda *a, **k: object(), raising=False
        )
        monkeypatch.setattr(
            k8s_client, "AppsV1Api", lambda *a, **k: object(), raising=False
        )
        monkeypatch.setattr(
            k8s_client, "BatchV1Api", lambda *a, **k: object(), raising=False
        )
        monkeypatch.setattr(
            k8s_client, "CustomObjectsApi", lambda *a, **k: object(), raising=False
        )

        async def _run():
            async with build_client(config) as bundle:
                assert bundle is not None

        # 不抛异常即为通过 —— 修复前这里会抛 InvalidToken
        asyncio.run(_run())

    def test_decrypt_sensitive_uses_local_key(self, local_env):
        """_decrypt_sensitive 对 LOCAL 配置使用本机密钥"""
        from app.services.k8s_client_factory import _decrypt_sensitive

        cipher = LocalEncryption.encrypt("plain-secret")
        config = {
            "storage_location": "LOCAL",
            "auth_data_encrypted": cipher,
        }

        assert _decrypt_sensitive(config, "auth_data_encrypted") == "plain-secret"

    def test_decrypt_sensitive_prefers_decrypted_field(self, local_env):
        """已有 *_decrypted 明文时直接使用（不重复解密）"""
        from app.services.k8s_client_factory import _decrypt_sensitive

        config = {
            "storage_location": "LOCAL",
            "auth_data_encrypted": "garbage-not-decryptable",
            "auth_data_decrypted": "already-plain",
        }

        assert _decrypt_sensitive(config, "auth_data_encrypted") == "already-plain"


class TestServerCredentialDecryptionUnaffected:
    """服务器侧配置仍走服务器密钥，本次修复不得破坏"""

    def test_decrypt_sensitive_uses_server_key_for_server_location(self, monkeypatch):
        from app.services.k8s_client_factory import _decrypt_sensitive

        encrypted = "server-side-cipher"
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
            "auth_data_encrypted": encrypted,
        }

        assert _decrypt_sensitive(config, "auth_data_encrypted") == "server-plain"
        assert seen["cipher"] == encrypted
