# -*- coding: utf-8 -*-
"""数据库工具本地存储改造测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_tool_models import (
    CreateDatabaseRequest,
    DatabaseType,
)
from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    engine = get_local_engine()
    init_local_tables(engine)

    yield

    reset_local_engine()


def _make_request(**overrides):
    payload = {
        "alias": "local-db",
        "db_type": DatabaseType.MYSQL,
        "host": "127.0.0.1",
        "port": 3306,
        "database_name": "app",
        "username": "root",
        "password": "p@ssw0rd",
    }
    payload.update(overrides)
    return CreateDatabaseRequest(**payload)


class TestRequestModel:
    def test_storage_location_defaults_to_local(self):
        """新配置默认存本机"""
        req = _make_request()
        assert req.storage_location == "local"

    def test_storage_location_accepts_server(self):
        req = _make_request(storage_location="server")
        assert req.storage_location == "server"


class TestCreateLocalConfig:
    def test_create_writes_to_local_db(self, local_env):
        from app.services.database_tool_service import DatabaseToolService

        req = _make_request()
        result = DatabaseToolService.create_config(
            "u-local", req, StorageLocation.LOCAL
        )

        assert result.storage_location == "local"

        # 直接查本地 SQLite，确认行存在且标记为 LOCAL
        from sqlalchemy import text

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, password_encrypted FROM db_configs WHERE id = :i"
            ), {"i": result.id}).first()

        assert row is not None
        assert row[0] == "LOCAL"
        # 密码是密文，不是明文
        assert row[1] != "p@ssw0rd"

    def test_local_password_decrypts_with_local_key(self, local_env):
        from app.services.database_tool_service import DatabaseToolService
        from sqlalchemy import text

        req = _make_request()
        result = DatabaseToolService.create_config(
            "u-local", req, StorageLocation.LOCAL
        )

        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT password_encrypted FROM db_configs WHERE id = :i"
            ), {"i": result.id}).first()[0]

        assert LocalEncryption.decrypt(cipher) == "p@ssw0rd"


class TestAliasUniquenessAcrossStores:
    def test_alias_conflict_with_other_store_rejected(self, local_env, monkeypatch):
        """本地已有同名 alias 时，服务器侧创建必须被拒绝"""
        from app.services.database_tool_service import DatabaseToolService
        from app.storage import repository as repo_module

        # 先在本地建一条
        DatabaseToolService.create_config(
            "u-x", _make_request(alias="dup"), StorageLocation.LOCAL
        )

        # 伪造「远程仓储查到了同名」的场景
        class FakeRemoteRepo:
            def find_by_alias(self, user_id, alias):
                return {"id": "remote-1", "alias": alias}

        original = repo_module.get_repository

        def fake_get_repository(location, tool):
            if location is StorageLocation.SERVER:
                return FakeRemoteRepo()
            return original(location, tool)

        monkeypatch.setattr(repo_module, "get_repository", fake_get_repository)

        with pytest.raises(ValueError, match="已存在"):
            DatabaseToolService.create_config(
                "u-x", _make_request(alias="dup"), StorageLocation.SERVER
            )
