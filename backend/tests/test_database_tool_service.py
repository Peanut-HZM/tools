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


def test_pg_get_databases_list_only_queries_pg_database(monkeypatch):
    """PG 无 database_name 时，列库只执行 pg_database 查询，不再遍历各库查 schema。"""
    from app.services.database_tool_service import DatabaseToolService, _LIST_CACHE
    import app.services.database_tool_service as svc

    _LIST_CACHE.invalidate(f"databases:cfg-pg")

    config_row = {
        "db_type": "postgresql", "host": "h", "port": 5432,
        "database_name": "", "username": "u", "password_encrypted": "enc",
        "charset": "utf8",
    }
    monkeypatch.setattr(
        DatabaseToolService, "_get_config_with_password",
        staticmethod(lambda cid, uid: config_row),
    )
    monkeypatch.setattr(
        DatabaseToolService, "_decrypt_password",
        staticmethod(lambda enc, cid="": ("pw", None)),
    )

    executed = []

    class FakeResult:
        def __init__(self, rows): self._rows = rows
        def __iter__(self): return iter(self._rows)

    class FakeConn:
        def execute(self, stmt):
            sql = str(stmt)
            executed.append(sql)
            return FakeResult([("db_a",), ("db_b",)])
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class FakeEngine:
        def connect(self): return FakeConn()
        def dispose(self): pass

    monkeypatch.setattr(
        svc.DBConnectionManager, "get_engine",
        staticmethod(lambda key, cfg: FakeEngine()),
    )

    result = DatabaseToolService.get_databases_list("u1", "cfg-pg", skip_cache=True)

    assert result == ["db_a", "db_b"]
    # 只应有一条 pg_database 查询，绝不能出现 information_schema.schemata 遍历
    assert any("pg_database" in s for s in executed)
    assert not any("information_schema.schemata" in s for s in executed)


def test_pg_get_schemas_list_uses_cache(monkeypatch):
    """第二次调用 get_schemas_list 命中缓存，不再连库查询。"""
    from app.services.database_tool_service import DatabaseToolService, _LIST_CACHE
    import app.services.database_tool_service as svc

    _LIST_CACHE.invalidate("schemas:cfg-pg:db_a")

    config_row = {
        "db_type": "postgresql", "host": "h", "port": 5432,
        "database_name": "", "username": "u", "password_encrypted": "enc",
        "charset": "utf8", "max_pool_size": 5,
    }
    monkeypatch.setattr(
        DatabaseToolService, "_get_config_with_password",
        staticmethod(lambda cid, uid: config_row),
    )
    monkeypatch.setattr(svc.EncryptionUtils, "decrypt", staticmethod(lambda v: "pw"))

    connect_count = {"n": 0}

    class FakeResult:
        def __iter__(self): return iter([("public",), ("app",)])

    class FakeConn:
        def execute(self, stmt): return FakeResult()
        def __enter__(self):
            connect_count["n"] += 1
            return self
        def __exit__(self, *a): return False

    class FakeEngine:
        def connect(self): return FakeConn()
        def dispose(self): pass

    monkeypatch.setattr(
        svc.DBConnectionManager, "get_engine",
        staticmethod(lambda key, cfg: FakeEngine()),
    )

    first = DatabaseToolService.get_schemas_list("u1", "cfg-pg", "db_a")
    second = DatabaseToolService.get_schemas_list("u1", "cfg-pg", "db_a")

    assert first == ["public", "app"]
    assert second == ["public", "app"]
    assert connect_count["n"] == 1  # 第二次命中缓存，未再连库


def test_pg_get_all_schemas_parallel_and_isolates_errors(monkeypatch):
    """并行查所有库 schema，单库失败不影响其他库。"""
    from app.services.database_tool_service import DatabaseToolService, _LIST_CACHE
    _LIST_CACHE.invalidate("all_schemas:cfg-pg")

    monkeypatch.setattr(
        DatabaseToolService, "get_databases_list",
        staticmethod(lambda uid, cid, skip_cache=False: ["db_a", "db_b", "db_bad"]),
    )

    def fake_get_schemas(uid, cid, database_name=None, skip_cache=False):
        if database_name == "db_bad":
            raise RuntimeError("boom")
        return ["public", database_name]

    monkeypatch.setattr(
        DatabaseToolService, "get_schemas_list",
        staticmethod(fake_get_schemas),
    )

    result = DatabaseToolService.get_all_schemas("u1", "cfg-pg", skip_cache=True)

    assert result["db_a"] == ["public", "db_a"]
    assert result["db_b"] == ["public", "db_b"]
    assert "db_bad" not in result  # 失败库被跳过
