"""本地 SQLite 引擎与建表测试"""
import os
import sys
import pytest
from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import local_db


@pytest.fixture
def local_engine(monkeypatch, tmp_path):
    """指向临时目录的本地 engine"""
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    local_db.reset_local_engine()

    engine = local_db.get_local_engine()
    yield engine

    local_db.reset_local_engine()


class TestLocalEngine:
    def test_engine_created_lazily(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        local_db.reset_local_engine()

        engine = local_db.get_local_engine()

        assert engine is not None
        db_file = tmp_path / ".toolbox" / "toolbox.db"
        assert db_file.exists()

        # 防止模块级缓存泄漏指向已废弃的 tmp_path
        local_db.reset_local_engine()

    def test_engine_is_cached(self, local_engine):
        assert local_db.get_local_engine() is local_engine


class TestLocalTables:
    def test_all_tables_created(self, local_engine):
        local_db.init_local_tables(local_engine)
        inspector = inspect(local_engine)
        tables = set(inspector.get_table_names())

        expected = {
            "db_configs",
            "k8s_connections",
            "ssh_configs",
            "redis_configs",
            "sql_execution_history",
            "db_scan_history",
            "table_schema_cache",
            "user_display_preferences",
            "users",
        }
        assert expected.issubset(tables)

    def test_storage_location_column_present(self, local_engine):
        local_db.init_local_tables(local_engine)
        inspector = inspect(local_engine)

        for table in ("db_configs", "k8s_connections", "ssh_configs", "redis_configs"):
            cols = {c["name"] for c in inspector.get_columns(table)}
            assert "storage_location" in cols, f"{table} 缺少 storage_location 列"

    def test_init_is_idempotent(self, local_engine):
        """重复建表不报错"""
        local_db.init_local_tables(local_engine)
        local_db.init_local_tables(local_engine)
        local_db.init_local_tables(local_engine)

        inspector = inspect(local_engine)
        assert "db_configs" in inspector.get_table_names()

    def test_default_storage_location_is_local(self, local_engine):
        """本地库新行默认标记为 LOCAL"""
        local_db.init_local_tables(local_engine)

        with local_engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO db_configs "
                "(id, user_id, alias, db_type, host, port, username, "
                " password_encrypted, storage_location) "
                "VALUES ('i1', 'u1', 'a', 'mysql', 'h', 3306, 'root', 'x', 'LOCAL')"
            ))
            row = conn.execute(text(
                "SELECT storage_location FROM db_configs WHERE id = 'i1'"
            )).first()

        assert row[0] == "LOCAL"
