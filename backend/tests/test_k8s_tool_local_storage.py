"""K8s 工具本地存储改造测试"""
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


class TestRequestModel:
    def test_storage_location_defaults_to_local(self):
        assert _make_request().storage_location == "local"


class TestCreateLocalK8sConfig:
    def test_writes_to_local_db(self, local_env):
        from app.services.k8s_tool_service import K8sToolService
        from sqlalchemy import text

        result = K8sToolService.create_config(
            "u-k8s", _make_request(), StorageLocation.LOCAL
        )

        assert result.storage_location == "local"
        assert result.has_auth_data is True

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, auth_data_encrypted FROM k8s_connections WHERE id = :i"
            ), {"i": result.id}).first()

        assert row[0] == "LOCAL"
        assert "my-k8s-token" not in row[1]  # 必须是密文

    def test_token_decrypts_with_local_key(self, local_env):
        import json

        from app.services.k8s_tool_service import K8sToolService
        from sqlalchemy import text

        result = K8sToolService.create_config(
            "u-k8s", _make_request(), StorageLocation.LOCAL
        )

        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT auth_data_encrypted FROM k8s_connections WHERE id = :i"
            ), {"i": result.id}).first()[0]

        assert json.loads(LocalEncryption.decrypt(cipher))["token"] == "my-k8s-token"
