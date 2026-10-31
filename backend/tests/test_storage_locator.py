"""存储位置枚举与服务器可用性判定测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.locator import StorageLocation, server_available


class TestStorageLocation:
    def test_enum_values(self):
        assert StorageLocation.LOCAL.value == "local"
        assert StorageLocation.SERVER.value == "server"

    def test_from_value(self):
        assert StorageLocation.from_value("local") is StorageLocation.LOCAL
        assert StorageLocation.from_value("SERVER") is StorageLocation.SERVER
        assert StorageLocation.from_value(StorageLocation.LOCAL) is StorageLocation.LOCAL

    def test_from_value_rejects_unknown(self):
        """非法值必须抛异常，禁止静默兜底"""
        with pytest.raises(ValueError):
            StorageLocation.from_value("nowhere")


class TestServerAvailable:
    def test_sqlite_url_means_unavailable(self, monkeypatch):
        """sqlite:// 开头 → 无远程服务器"""
        from app.config import config as config_module

        monkeypatch.setattr(
            config_module.settings, "DATABASE_URL", "sqlite:///./data/x.db"
        )

        available, reason = server_available()

        assert available is False
        assert reason  # 必须有原因说明

    def test_empty_url_means_unavailable(self, monkeypatch):
        from app.config import config as config_module

        monkeypatch.setattr(config_module.settings, "DATABASE_URL", "")

        available, reason = server_available()

        assert available is False
        assert reason

    def test_postgres_unreachable_means_unavailable(self, monkeypatch):
        """PG 地址不可达 → 不可用，且给出原因"""
        from app.config import config as config_module

        monkeypatch.setattr(
            config_module.settings,
            "DATABASE_URL",
            "postgresql://u:p@127.0.0.1:59999/nonexistent",
        )

        # 连接池走 app.models.base.engine 全局单例（导入时已按真实 DATABASE_URL 建立），
        # monkeypatch settings.DATABASE_URL 不会重建它，故此处直接 mock 连接获取，
        # 模拟「PG 不可达」的真实故障路径。
        from app.config import database as database_module

        def _raise_unreachable():
            raise ConnectionError("could not connect to server")

        monkeypatch.setattr(
            database_module, "get_pooled_db_connection", _raise_unreachable
        )

        available, reason = server_available()

        assert available is False
        assert reason  # 必须有原因，不能是空串
