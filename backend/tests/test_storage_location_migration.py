"""服务器侧 storage_location 列迁移测试（幂等性验证）"""
import os
import sys
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.ddl import column_exists, ensure_column


DDL = "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'"


@pytest.fixture
def pg_like_conn():
    """模拟服务器侧的表（SQLite 用于验证探测式加列的幂等逻辑）"""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE db_configs (id VARCHAR(64) PRIMARY KEY)"))
        conn.commit()
        yield conn
        conn.close()


class TestEnsureColumnIdempotency:
    def test_repeated_calls_are_safe(self, pg_like_conn):
        """重复执行不报错，且只加一次"""
        results = [ensure_column(pg_like_conn, "db_configs", "storage_location", DDL) for _ in range(3)]

        assert results == [True, False, False]
        assert column_exists(pg_like_conn, "db_configs", "storage_location") is True

    def test_existing_rows_get_server_default(self, pg_like_conn):
        """加列后既有行的默认值为 SERVER"""
        # SQLAlchemy 2.x：begin() 返回事务对象，直接在连接上执行
        pg_like_conn.execute(text("INSERT INTO db_configs (id) VALUES ('x1')"))
        pg_like_conn.commit()

        ensure_column(pg_like_conn, "db_configs", "storage_location", DDL)

        row = pg_like_conn.execute(text(
            "SELECT storage_location FROM db_configs WHERE id = 'x1'"
        )).first()

        assert row[0] == "SERVER"


class TestSqlFileHasColumn:
    def test_init_sql_declares_storage_location(self):
        """init_db_tool.sql 的 db_configs 必须声明 storage_location 列"""
        sql_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "db", "init_db_tool.sql",
        )
        with open(sql_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 取 db_configs 表定义片段
        start = content.index("CREATE TABLE IF NOT EXISTS db_configs")
        end = content.index(";", start)
        block = content[start:end]

        assert "storage_location" in block, "db_configs 缺少 storage_location 列"
