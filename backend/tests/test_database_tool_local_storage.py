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


class TestDecryptForLocalRows:
    def test_get_all_configs_decrypts_local_password(self, local_env):
        """本地创建的配置，列表含密码时必须能解出正确明文（走本地密钥路径）"""
        from app.services.database_tool_service import DatabaseToolService

        created = DatabaseToolService.create_config(
            "u-dec", _make_request(alias="dec-check"), StorageLocation.LOCAL
        )

        configs = DatabaseToolService.get_all_configs("u-dec", include_password=True)

        target = [c for c in configs if c.id == created.id]
        assert len(target) == 1
        assert target[0].password == "p@ssw0rd"

    def test_get_config_decrypts_local_password(self, local_env):
        """单条查询含密码时同样走本地密钥"""
        from app.services.database_tool_service import DatabaseToolService

        created = DatabaseToolService.create_config(
            "u-dec2", _make_request(alias="dec-one"), StorageLocation.LOCAL
        )

        config = DatabaseToolService.get_config(created.id, "u-dec2", include_password=True)

        assert config is not None
        assert config.password == "p@ssw0rd"


class TestUpdateConfigLocation:
    def test_update_without_location_locates_local_row(self, local_env):
        """storage_location=None 时自动定位：本地建的行在本地被更新"""
        from app.services.database_tool_service import DatabaseToolService

        created = DatabaseToolService.create_config(
            "u-upd", _make_request(alias="upd-auto"), StorageLocation.LOCAL
        )

        from app.models.database_tool_models import UpdateDatabaseRequest

        req = UpdateDatabaseRequest(host="10.0.0.8")
        updated = DatabaseToolService.update_config(created.id, "u-upd", req)

        assert updated is not None
        assert updated.host == "10.0.0.8"
        assert updated.storage_location == "local"

        # 本地行确实被改
        from app.storage.repository import get_repository
        row = get_repository(StorageLocation.LOCAL, "database").get(created.id, "u-upd")
        assert row is not None
        assert row["host"] == "10.0.0.8"

    def test_update_with_explicit_server_only_touches_server(self, local_env, monkeypatch):
        """显式传 SERVER 时即使本地有同 id 行也只改服务器侧"""
        from app.models.database_tool_models import UpdateDatabaseRequest
        from app.services.database_tool_service import DatabaseToolService
        from app.storage import repository as repo_module

        created = DatabaseToolService.create_config(
            "u-upd2", _make_request(alias="upd-srv"), StorageLocation.LOCAL
        )

        server_rows = {
            created.id: {
                "id": created.id, "user_id": "u-upd2", "alias": "upd-srv",
                "db_type": "mysql", "host": "srv-old", "port": 3306,
                "username": "root", "storage_location": "SERVER",
                "created_at": created.created_at, "updated_at": created.updated_at,
            }
        }

        class FakeServerRepo:
            def get(self, config_id, user_id):
                return dict(server_rows[config_id]) if config_id in server_rows else None

            def update(self, config_id, user_id, data, storage_location):
                server_rows[config_id].update(data)
                return self.get(config_id, user_id)

        original = repo_module.get_repository

        def fake_get_repository(location, tool):
            if location is StorageLocation.SERVER:
                return FakeServerRepo()
            return original(location, tool)

        monkeypatch.setattr(repo_module, "get_repository", fake_get_repository)

        req = UpdateDatabaseRequest(host="srv-new")
        updated = DatabaseToolService.update_config(
            created.id, "u-upd2", req, StorageLocation.SERVER
        )

        # 只改了服务器侧
        assert updated is not None
        assert updated.host == "srv-new"
        assert updated.storage_location == "server"
        assert created.id in server_rows

        # 本地行未被触碰
        from sqlalchemy import text
        with get_local_engine().begin() as conn:
            host = conn.execute(text(
                "SELECT host FROM db_configs WHERE id = :i"
            ), {"i": created.id}).first()[0]
        assert host == "127.0.0.1"


class TestAliasCheckFailure:
    def test_local_repo_error_raises(self, local_env, monkeypatch):
        """本地仓储别名检查异常时必须抛错，不允许静默放行"""
        from app.services.database_tool_service import DatabaseToolService
        from app.storage import repository as repo_module

        class BrokenLocalRepo:
            def find_by_alias(self, user_id, alias):
                raise RuntimeError("local db broken")

        original = repo_module.get_repository

        def fake_get_repository(location, tool):
            if location is StorageLocation.LOCAL:
                return BrokenLocalRepo()
            return original(location, tool)

        monkeypatch.setattr(repo_module, "get_repository", fake_get_repository)

        with pytest.raises(ValueError, match="本地"):
            DatabaseToolService.create_config(
                "u-broken", _make_request(alias="no-check"), StorageLocation.LOCAL
            )


class TestAliasExcludeSelf:
    def test_exclude_config_id_allows_rename(self, local_env):
        """改名（alias 更新）时排除自身配置，不误报重复"""
        from app.models.database_tool_models import UpdateDatabaseRequest
        from app.services.database_tool_service import DatabaseToolService

        created = DatabaseToolService.create_config(
            "u-rename", _make_request(alias="old-name"), StorageLocation.LOCAL
        )

        req = UpdateDatabaseRequest(alias="new-name")
        updated = DatabaseToolService.update_config(created.id, "u-rename", req)

        assert updated is not None
        assert updated.alias == "new-name"


class TestInvalidStorageLocation:
    def test_invalid_value_rejected_at_service_layer(self):
        """非法 storage_location 在 Service 边界抛 ValueError"""
        from app.storage.locator import StorageLocation

        with pytest.raises(ValueError):
            StorageLocation.from_value("cloud")

    def test_invalid_value_rejected_in_route(self):
        """路由层非法 storage_location 返回 400"""
        from types import SimpleNamespace
        import asyncio
        from app.routes.database_tool import create_database
        from fastapi import HTTPException

        request = _make_request(storage_location="cloud")
        try:
            asyncio.run(create_database(request, user_id="u-route"))
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            pytest.fail("非法 storage_location 未被拒绝")

