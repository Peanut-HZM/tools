"""Redis 工具本地存储改造测试"""
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


class TestCreateLocalRedisConfig:
    def test_writes_encrypted_password_to_local_db(self, local_env):
        from app.models.redis_tool_models import CreateRedisRequest
        from app.services.redis_tool_service import RedisToolService
        from sqlalchemy import text

        result = RedisToolService.create_config(
            "u-redis",
            CreateRedisRequest(
                alias="local-redis",
                host="127.0.0.1",
                port=6379,
                username="default",
                password="redis-secret",
                db=0,
            ),
            StorageLocation.LOCAL,
        )

        assert result.storage_location == "local"

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, password_encrypted FROM redis_configs WHERE id = :i"
            ), {"i": result.id}).first()

        assert row[0] == "LOCAL"
        assert "redis-secret" not in row[1]
        assert LocalEncryption.decrypt(row[1]) == "redis-secret"
