"""双方言幂等 DDL 辅助测试"""
import os
import sys
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.ddl import column_exists, ensure_column


@pytest.fixture
def sqlite_conn():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE t_demo (id VARCHAR(64) PRIMARY KEY)"))
        conn.commit()
        yield conn
        conn.close()


class TestColumnExists:
    def test_existing_column(self, sqlite_conn):
        assert column_exists(sqlite_conn, "t_demo", "id") is True

    def test_missing_column(self, sqlite_conn):
        assert column_exists(sqlite_conn, "t_demo", "storage_location") is False

    def test_missing_table(self, sqlite_conn):
        assert column_exists(sqlite_conn, "t_absent", "id") is False


class TestEnsureColumn:
    def test_adds_column_when_missing(self, sqlite_conn):
        added = ensure_column(
            sqlite_conn,
            "t_demo",
            "storage_location",
            "storage_location VARCHAR(16) NOT NULL DEFAULT 'LOCAL'",
        )

        assert added is True
        assert column_exists(sqlite_conn, "t_demo", "storage_location") is True

    def test_is_idempotent(self, sqlite_conn):
        """重复执行不报错、不重复加列"""
        ddl = "storage_location VARCHAR(16) NOT NULL DEFAULT 'LOCAL'"

        assert ensure_column(sqlite_conn, "t_demo", "storage_location", ddl) is True
        assert ensure_column(sqlite_conn, "t_demo", "storage_location", ddl) is False
        assert ensure_column(sqlite_conn, "t_demo", "storage_location", ddl) is False
