from datetime import datetime
from app.services import database_tool_service


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def cursor(self):
        return FakeCursor(self._rows)

    def close(self):
        self.closed = True


def test_get_all_configs_without_password(monkeypatch):
    rows = [{
        "id": "1",
        "user_id": "u1",
        "alias": "db1",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database_name": "test",
        "username": "root",
        "password_encrypted": "encrypted",
        "environment": "dev",
        "group_name": None,
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "max_pool_size": 10,
        "ssl_mode": None,
        "ssl_cert_path": None,
        "extra_config": None,
        "is_active": True,
        "last_connected_at": None,
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 2)
    }]

    monkeypatch.setattr(database_tool_service, "get_db_connection", lambda: FakeConn(rows))
    monkeypatch.setattr(database_tool_service.EncryptionUtils, "decrypt", lambda value: "plain")

    configs = database_tool_service.DatabaseToolService.get_all_configs("u1")

    assert configs[0].password is None


def test_get_all_configs_with_password(monkeypatch):
    rows = [{
        "id": "1",
        "user_id": "u1",
        "alias": "db1",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database_name": "test",
        "username": "root",
        "password_encrypted": "encrypted",
        "environment": "dev",
        "group_name": None,
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "max_pool_size": 10,
        "ssl_mode": None,
        "ssl_cert_path": None,
        "extra_config": None,
        "is_active": True,
        "last_connected_at": None,
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 2)
    }]

    monkeypatch.setattr(database_tool_service, "get_db_connection", lambda: FakeConn(rows))
    monkeypatch.setattr(database_tool_service.EncryptionUtils, "decrypt", lambda value: "plain")

    configs = database_tool_service.DatabaseToolService.get_all_configs("u1", include_password=True)

    assert configs[0].password == "plain"
