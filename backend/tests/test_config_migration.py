"""配置迁移服务测试（重加密 + 先写后删 + 失败处理）"""
import os
import sys
import uuid
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine
from app.storage.migration import migrate_config


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    # 屏蔽测试套件间的 DATABASE_URL 泄漏：默认认为服务器可用，
    # 各用例按需再覆盖 migration.server_available
    from app.storage import migration as migration_module

    monkeypatch.setattr(migration_module, "server_available", lambda: (True, ""))
    # 不触碰远程引擎全局单例：app.models.base.engine 一旦创建就会缓存连接池，
    # 污染后续针对 server_available 的用例。默认让 SERVER 侧探测直接报不可达，
    # 需要服务器侧仓储的用例会自行 monkeypatch migration.get_repository。
    original_get_repository = migration_module.get_repository

    def _local_only_get_repository(location, tool):
        from app.storage.locator import StorageLocation as _Loc

        if location is _Loc.SERVER:
            raise RuntimeError("测试环境不连接远程库")
        return original_get_repository(location, tool)

    monkeypatch.setattr(
        migration_module, "get_repository", _local_only_get_repository
    )
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


def _seed_local_config(user_id="u-mig", alias="mig-db"):
    """在本地库插入一条配置，返回 (config_id, cipher)"""
    config_id = str(uuid.uuid4())
    cipher = LocalEncryption.encrypt("migrate-secret")

    with get_local_engine().begin() as conn:
        conn.execute(text(
            "INSERT INTO db_configs "
            "(id, user_id, alias, db_type, host, port, username, password_encrypted, "
            " storage_location, deleted, created_at, updated_at) "
            "VALUES (:i, :u, :a, 'mysql', 'h', 3306, 'root', :c, 'LOCAL', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"i": config_id, "u": user_id, "a": alias, "c": cipher})

    return config_id, cipher


class TestMigrateConfig:
    def test_source_not_found_raises(self, local_env):
        with pytest.raises(ValueError, match="不存在"):
            migrate_config("u-mig", "database", str(uuid.uuid4()), StorageLocation.SERVER)

    def test_migrate_requires_target_available(self, local_env, monkeypatch):
        """目标服务器不可用时必须拒绝迁移"""
        from app.storage import migration as migration_module

        config_id, _cipher = _seed_local_config()

        monkeypatch.setattr(
            migration_module, "server_available", lambda: (False, "未配置远程服务器")
        )

        with pytest.raises(ValueError, match="未配置远程服务器"):
            migrate_config("u-mig", "database", config_id, StorageLocation.SERVER)

    def test_migrate_to_local_reencrypts(self, local_env, monkeypatch):
        """从服务器搬到本地：密文必须用本地密钥重加密"""
        from app.storage import migration as migration_module
        from app.storage.repository import RemoteConfigRepository

        config_id, _ = _seed_local_config()

        # 伪造一条服务器侧配置（用另一把密钥加密）
        fake_cipher = "server-side-cipher"

        class FakeRemoteRepo(RemoteConfigRepository):
            def get(self, cid, uid):
                if cid != config_id:
                    return None
                return {
                    "id": config_id,
                    "user_id": uid,
                    "alias": "mig-db",
                    "db_type": "mysql",
                    "host": "h",
                    "port": 3306,
                    "username": "root",
                    "password_encrypted": fake_cipher,
                    "storage_location": "SERVER",
                    "deleted": False,
                }

            def get_with_secret(self, cid, uid):
                row = self.get(cid, uid)
                if row is None:
                    return None
                row["password_decrypted"] = "migrate-secret"
                return row

            def create(self, user_id, data, storage_location):
                with get_local_engine().begin() as conn:
                    conn.execute(text(
                        "INSERT INTO db_configs "
                        "(id, user_id, alias, db_type, host, port, username, "
                        " password_encrypted, storage_location, created_at, updated_at) "
                        "VALUES (:i, :u, :a, 'mysql', 'h', 3306, 'root', :c, 'LOCAL', "
                        " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ), {
                        "i": data["id"], "u": user_id, "a": data["alias"],
                        "c": data.get("password_encrypted"),
                    })
                return data

            def delete(self, cid, uid):
                return False  # 模拟源端删除失败 → 中间态

        original_get_repository = migration_module.get_repository

        monkeypatch.setattr(
            migration_module, "get_repository",
            lambda location, tool: FakeRemoteRepo(tool)
            if location is StorageLocation.SERVER
            else original_get_repository(location, tool),
        )
        monkeypatch.setattr(migration_module, "server_available", lambda: (True, ""))

        result = migrate_config(
            "u-mig", "database", config_id, StorageLocation.LOCAL
        )

        assert result["success"] is True
        assert result["storage_location"] == "local"

        # 目标端密文必须能用本地密钥解开
        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT password_encrypted FROM db_configs WHERE id = :i"
            ), {"i": config_id}).first()[0]

        assert LocalEncryption.decrypt(cipher) == "migrate-secret"


class TestMigrateOrdering:
    def test_target_written_before_source_deleted(self, local_env, monkeypatch):
        """执行顺序验证：目标端写入发生在源端删除之前"""
        from app.storage import migration as migration_module

        config_id, _ = _seed_local_config()
        call_order: list[str] = []

        class FakeSourceRepo:
            """伪造源端（SERVER 侧）仓储：只记录 delete"""

            def get(self, cid, uid):
                return {
                    "id": cid, "user_id": uid, "alias": "mig-db",
                    "db_type": "mysql", "host": "h", "port": 3306,
                    "username": "root", "password_encrypted": "c",
                    "storage_location": "SERVER", "deleted": False,
                }

            def get_with_secret(self, cid, uid):
                row = self.get(cid, uid)
                row["password_decrypted"] = "s"
                return row

            def find_by_alias(self, uid, alias):
                return None

            def create(self, user_id, data, storage_location):
                raise AssertionError("源端仓储不应被写入")

            def delete(self, cid, uid):
                call_order.append("delete_source")
                return True

        # 目标端（LOCAL）用真实仓储，但包装 create 以记录写入时序
        from app.storage.repository import LocalConfigRepository

        class RecordingLocalRepo(LocalConfigRepository):
            def create(self, user_id, data, storage_location):
                call_order.append("write_target")
                return super().create(user_id, data, storage_location)

        original_get_repository = migration_module.get_repository

        def fake_get_repository(location, tool):
            if location is StorageLocation.SERVER:
                return FakeSourceRepo()
            return RecordingLocalRepo(tool)

        monkeypatch.setattr(migration_module, "get_repository", fake_get_repository)
        monkeypatch.setattr(migration_module, "server_available", lambda: (True, ""))

        migrate_config("u-mig", "database", config_id, StorageLocation.LOCAL)

        assert call_order == ["write_target", "delete_source"]
