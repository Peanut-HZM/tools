"""Repository 实现测试（含跨库隔离安全断言）"""
import os
import sys
import uuid
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine
from app.storage.locator import StorageLocation
from app.storage.repository import get_repository
from app.storage.crypto import LocalEncryption


@pytest.fixture
def local_repo(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    engine = get_local_engine()
    init_local_tables(engine)

    repo = get_repository(StorageLocation.LOCAL, "database")
    yield repo

    reset_local_engine()


@pytest.fixture
def sample_data():
    return {
        "id": str(uuid.uuid4()),
        "user_id": "u-test",
        "alias": "test-db",
        "db_type": "mysql",
        "host": "127.0.0.1",
        "port": 3306,
        "username": "root",
        "password_encrypted": LocalEncryption.encrypt("s3cret"),
        "environment": "dev",
        "group_name": None,
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "max_pool_size": 10,
        "ssl_mode": None,
        "ssl_cert_path": None,
        "extra_config": None,
        "is_active": True,
    }


class TestLocalRepository:
    def test_create_and_get(self, local_repo, sample_data):
        created = local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        assert created["id"] == sample_data["id"]

        fetched = local_repo.get(sample_data["id"], "u-test")
        assert fetched is not None
        assert fetched["alias"] == "test-db"

    def test_create_injects_local_storage_location(self, local_repo, sample_data):
        """本地创建的记录必须标记为 LOCAL"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location FROM db_configs WHERE id = :i"
            ), {"i": sample_data["id"]}).first()

        assert row[0] == "LOCAL"

    def test_create_rejects_wrong_location(self, local_repo, sample_data):
        """本地仓储拒绝写入 SERVER 位置 —— 越界写入的第一道闸门"""
        with pytest.raises(ValueError, match="存储位置不匹配"):
            local_repo.create("u-test", sample_data, StorageLocation.SERVER)

    def test_list_filters_by_user(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        assert len(local_repo.list("u-test")) == 1
        assert len(local_repo.list("other-user")) == 0

    def test_find_by_alias(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        found = local_repo.find_by_alias("u-test", "test-db")
        assert found is not None
        assert found["id"] == sample_data["id"]

        assert local_repo.find_by_alias("u-test", "no-such") is None

    def test_update(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        updated = local_repo.update(
            sample_data["id"], "u-test", {"alias": "renamed"}, StorageLocation.LOCAL
        )

        assert updated["alias"] == "renamed"

    def test_delete_removes_row(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        assert local_repo.delete(sample_data["id"], "u-test") is True
        assert local_repo.get(sample_data["id"], "u-test") is None

    def test_delete_cleans_related_history(self, local_repo, sample_data):
        """SQLite 外键默认关闭，必须显式清理关联历史"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        with get_local_engine().begin() as conn:
            conn.execute(text(
                "INSERT INTO sql_execution_history "
                "(id, user_id, db_config_id, sql_statement, execution_status) "
                "VALUES ('h1', 'u-test', :cid, 'SELECT 1', 'success')"
            ), {"cid": sample_data["id"]})

        local_repo.delete(sample_data["id"], "u-test")

        with get_local_engine().begin() as conn:
            remaining = conn.execute(text(
                "SELECT COUNT(*) FROM sql_execution_history WHERE db_config_id = :cid"
            ), {"cid": sample_data["id"]}).scalar()

        assert remaining == 0

    def test_get_with_secret_decrypts(self, local_repo, sample_data):
        """get_with_secret 解出明文；普通 get 不含明文"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        plain = local_repo.get(sample_data["id"], "u-test")
        assert plain.get("password_decrypted") is None

        with_secret = local_repo.get_with_secret(sample_data["id"], "u-test")
        assert with_secret["password_decrypted"] == "s3cret"

    def test_update_rejects_wrong_location(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        with pytest.raises(ValueError, match="存储位置不匹配"):
            local_repo.update(
                sample_data["id"], "u-test", {"alias": "x"}, StorageLocation.SERVER
            )


class TestCrossStoreIsolation:
    """跨库隔离断言 —— 本设计的安全回归底线"""

    def test_local_config_not_in_remote_db(self, local_repo, sample_data):
        """本地创建的配置，绝不能出现在远程 PG 的 db_configs 表"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        from app.config.database import get_pooled_db_connection, release_db_connection

        try:
            conn = get_pooled_db_connection()
        except Exception:
            pytest.skip("远程数据库不可达，跳过跨库断言")

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM db_configs WHERE id = %s", (sample_data["id"],)
                )
                count = cur.fetchone()["count"]
        except Exception:
            pytest.skip("远程库无 db_configs 表，跳过")
        finally:
            release_db_connection(conn)

        assert count == 0

    def test_local_secret_not_decryptable_by_server_key(self, local_repo, sample_data):
        """本地密文用服务器密钥解不开"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        from app.utils.encryption import EncryptionUtils

        with pytest.raises(Exception):
            EncryptionUtils.decrypt(sample_data["password_encrypted"])
