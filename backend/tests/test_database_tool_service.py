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


def _make_config_row(**overrides):
    """构造一条 db_configs 字典行（模拟 Repository.list 返回）"""
    row = {
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
        "updated_at": datetime(2024, 1, 2),
        "storage_location": "SERVER",
    }
    row.update(overrides)
    return row


def _fake_repo_class(rows):
    """构造一个以 rows 为 list 返回值的假仓储类"""
    class _FakeRepo:
        def list(self, user_id):
            return rows

    return _FakeRepo


def test_get_all_configs_without_password(monkeypatch):
    from app.storage import repository as repo_module
    from app.storage.locator import StorageLocation

    rows = [_make_config_row()]

    monkeypatch.setattr(
        repo_module, "get_repository",
        lambda location, tool: _fake_repo_class(rows)()
        if location is StorageLocation.LOCAL else _fake_repo_class([])(),
    )

    configs = database_tool_service.DatabaseToolService.get_all_configs("u1")

    assert configs[0].password is None
    assert configs[0].storage_location == "server"


def test_get_all_configs_with_password(monkeypatch):
    from app.storage import repository as repo_module
    from app.storage.locator import StorageLocation

    rows = [_make_config_row()]

    monkeypatch.setattr(
        repo_module, "get_repository",
        lambda location, tool: _fake_repo_class(rows)()
        if location is StorageLocation.LOCAL else _fake_repo_class([])(),
    )
    # 服务器侧行走 _decrypt_password 多密钥路径
    monkeypatch.setattr(
        database_tool_service.DatabaseToolService, "_decrypt_password",
        staticmethod(lambda enc, cid="": ("plain", None)),
    )

    configs = database_tool_service.DatabaseToolService.get_all_configs(
        "u1", include_password=True
    )

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


def test_execute_sql_ddl_invalidates_structure_cache(monkeypatch):
    """DDL 执行成功后必须失效该连接的服务端结构缓存，界面才能立即看到表结构变更。"""
    from app.models.database_tool_models import SQLExecutionRequest, SQLExecutionResult
    from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE, _LIST_CACHE

    invalidated_structure = []
    invalidated_list = []
    monkeypatch.setattr(_STRUCTURE_CACHE, "invalidate_prefix", lambda prefix: invalidated_structure.append(prefix))
    monkeypatch.setattr(_LIST_CACHE, "invalidate_prefix", lambda prefix: invalidated_list.append(prefix))

    monkeypatch.setattr(
        DatabaseToolService, "_get_config_with_password",
        staticmethod(lambda uid, cid: {"db_type": "mysql", "host": "h", "port": 3306, "database_name": "db", "username": "u", "password_encrypted": "enc", "charset": "utf8mb4", "max_pool_size": 5}),
    )
    monkeypatch.setattr(
        DatabaseToolService, "_decrypt_password",
        staticmethod(lambda enc, cid: ("pw", None)),
    )
    from app.utils.sql_executor import SQLExecutor
    monkeypatch.setattr(
        SQLExecutor, "execute",
        staticmethod(lambda cid, cfg, sql, params: SQLExecutionResult(success=True, sql_type="DML/DDL", affected_rows=0, execution_time_ms=1)),
    )
    monkeypatch.setattr(DatabaseToolService, "_save_history", staticmethod(lambda uid, req, res: None))

    request = SQLExecutionRequest(db_config_id="cfg-1", sql="CREATE TABLE t1 (id INT)", database_name="db")
    result = DatabaseToolService.execute_sql("u1", request)

    assert result.success is True
    assert invalidated_structure == ["cfg-1"]  # 普通表级 DDL：只失效结构缓存


def test_execute_sql_create_database_invalidates_list_cache(monkeypatch):
    """CREATE DATABASE 执行成功后除结构缓存外，还必须失效库列表/Schema 列表缓存。"""
    from app.models.database_tool_models import SQLExecutionRequest, SQLExecutionResult
    from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE, _LIST_CACHE

    invalidated_structure = []
    invalidated_list = []
    monkeypatch.setattr(_STRUCTURE_CACHE, "invalidate_prefix", lambda prefix: invalidated_structure.append(prefix))
    monkeypatch.setattr(_LIST_CACHE, "invalidate_prefix", lambda prefix: invalidated_list.append(prefix))

    monkeypatch.setattr(
        DatabaseToolService, "_get_config_with_password",
        staticmethod(lambda uid, cid: {"db_type": "mysql", "host": "h", "port": 3306, "database_name": "db", "username": "u", "password_encrypted": "enc", "charset": "utf8mb4", "max_pool_size": 5}),
    )
    monkeypatch.setattr(
        DatabaseToolService, "_decrypt_password",
        staticmethod(lambda enc, cid: ("pw", None)),
    )
    from app.utils.sql_executor import SQLExecutor
    monkeypatch.setattr(
        SQLExecutor, "execute",
        staticmethod(lambda cid, cfg, sql, params: SQLExecutionResult(success=True, sql_type="DML/DDL", affected_rows=1, execution_time_ms=1)),
    )
    monkeypatch.setattr(DatabaseToolService, "_save_history", staticmethod(lambda uid, req, res: None))

    request = SQLExecutionRequest(db_config_id="cfg-1", sql="CREATE DATABASE new_db", database_name=None)
    DatabaseToolService.execute_sql("u1", request)

    assert invalidated_structure == ["cfg-1"]
    assert f"databases:cfg-1" in invalidated_list
    assert f"schemas:cfg-1" in invalidated_list
    assert f"all_schemas:cfg-1" in invalidated_list


def test_execute_sql_select_does_not_invalidate_caches(monkeypatch):
    """SELECT 查询不应触发缓存失效。"""
    from app.models.database_tool_models import SQLExecutionRequest, SQLExecutionResult
    from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE, _LIST_CACHE

    invalidated_structure = []
    invalidated_list = []
    monkeypatch.setattr(_STRUCTURE_CACHE, "invalidate_prefix", lambda prefix: invalidated_structure.append(prefix))
    monkeypatch.setattr(_LIST_CACHE, "invalidate_prefix", lambda prefix: invalidated_list.append(prefix))

    monkeypatch.setattr(
        DatabaseToolService, "_get_config_with_password",
        staticmethod(lambda uid, cid: {"db_type": "mysql", "host": "h", "port": 3306, "database_name": "db", "username": "u", "password_encrypted": "enc", "charset": "utf8mb4", "max_pool_size": 5}),
    )
    monkeypatch.setattr(
        DatabaseToolService, "_decrypt_password",
        staticmethod(lambda enc, cid: ("pw", None)),
    )
    from app.utils.sql_executor import SQLExecutor
    monkeypatch.setattr(
        SQLExecutor, "execute",
        staticmethod(lambda cid, cfg, sql, params: SQLExecutionResult(success=True, sql_type="SELECT", affected_rows=0, execution_time_ms=1, columns=["id"], result_data=[])),
    )
    monkeypatch.setattr(DatabaseToolService, "_save_history", staticmethod(lambda uid, req, res: None))

    request = SQLExecutionRequest(db_config_id="cfg-1", sql="SELECT 1", database_name="db")
    result = DatabaseToolService.execute_sql("u1", request)

    assert result.success is True
    assert invalidated_structure == []
    assert invalidated_list == []


def test_get_database_structure_skip_cache_bypasses_backend_cache(monkeypatch):
    """skip_cache=True 时必须绕过后端结构缓存并回源实查，且不回写缓存。"""
    from types import SimpleNamespace
    from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE

    cache_hits = {"get": 0, "set": 0}
    real_get = _STRUCTURE_CACHE.get
    real_set = _STRUCTURE_CACHE.set

    def fake_get(key):
        cache_hits["get"] += 1
        return {"tables": [{"name": "stale_table", "comment": None}], "views": []}

    def fake_set(key, value):
        cache_hits["set"] += 1

    monkeypatch.setattr(_STRUCTURE_CACHE, "get", fake_get)
    monkeypatch.setattr(_STRUCTURE_CACHE, "set", fake_set)

    monkeypatch.setattr(
        DatabaseToolService, "_get_config_with_password",
        staticmethod(lambda uid, cid: {"db_type": "mysql", "host": "h", "port": 3306, "database_name": "db", "username": "u", "password_encrypted": "enc", "charset": "utf8mb4"}),
    )
    from app.utils.encryption import EncryptionUtils
    monkeypatch.setattr(EncryptionUtils, "decrypt", staticmethod(lambda enc: "pw"))

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows
        def __iter__(self):
            return iter(self._rows)

    class FakeConn:
        def __init__(self):
            self.call = 0
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def execute(self, sql, params=None):
            self.call += 1
            # 第一条为表查询，第二条为视图查询
            return FakeResult([("fresh_table", None, "table")] if self.call == 1 else [])

    from app.utils.db_connection_manager import DBConnectionManager
    monkeypatch.setattr(DBConnectionManager, "get_engine", staticmethod(lambda cid, cfg: object.__new__(object)))

    import app.services.database_tool_service as svc_mod
    # engine.connect() 需要 context manager：包装 SQLAlchemy text 的执行路径
    from sqlalchemy import create_engine as _unused  # noqa: F401

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(DBConnectionManager, "get_engine", staticmethod(lambda cid, cfg: FakeEngine()))

    # skip_cache=True：缓存中的 stale_table 不应被返回
    result = DatabaseToolService.get_database_structure("u1", "cfg-1", "mydb", None, skip_cache=True)
    assert result == {"tables": [{"name": "fresh_table", "comment": None}], "views": []}
    assert cache_hits["get"] == 0  # skip_cache 不读缓存
    assert cache_hits["set"] == 0  # skip_cache 不回写缓存
