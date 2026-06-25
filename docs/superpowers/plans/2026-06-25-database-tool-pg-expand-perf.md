# PostgreSQL 连接展开性能优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 PostgreSQL 连接展开下级节点的耗时从 2.4~5.5s 降到 < 300ms，通过懒加载分层（连接→只列库名，库→懒加载 schema）+ 5 分钟 TTL 缓存 + 并行查询实现。

**Architecture:** 后端 `get_databases_list` 瘦身为只查 `pg_database` 返回库名（不再遍历每库查 schema）；schema 改由已有的 `get_schemas_list` 在展开具体库时懒加载；新增 `get_all_schemas` 用线程池并行查询供搜索场景使用；列库/列 schema 结果复用文件内已有的 `StructureCache`（5 分钟 TTL 实例）。前端 `PostgresDatabaseNode` 改为展开库时才请求 schema，并处理返回格式变更与旧缓存失效。

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / pytest（后端），React 18 + TypeScript / Vite（前端）。后端服务进程以 `--reload` 运行，保存即热加载。

---

## 关键现状（实现前必读）

1. **缓存类已存在**：`backend/app/services/database_tool_service.py:60` 已有线程安全 TTL 缓存类 `StructureCache`，提供 `get/set/invalidate/invalidate_prefix`。文件顶部已 `import time`、`import threading`。已有全局实例 `_STRUCTURE_CACHE = StructureCache(ttl=3600, maxsize=100)`（第 102 行）。**不要新建缓存工具文件**，复用此类即可。
2. **慢代码位置**：`get_databases_list` 的 PG 无 `database_name` 分支在 `database_tool_service.py:1144-1186`，串行遍历每个库建连查 schema。
3. **schema 懒加载接口已存在**：`get_schemas_list`（`database_tool_service.py:1200-1244`）+ 路由 `GET /database-tool/databases/{id}/schemas?database_name=`（`routes/database_tool.py:197-209`），单库查询，快。
4. **前端已有分层组件**：`ConnectionList.tsx` 的 `PostgresDatabaseNode`（第 1444-1513 行）当前接收 `schemaNames` props 直接渲染（不请求）。PG 无 database_name 时父级在第 600-636 行把 `db:schema` 扁平列表 `split(':')` 分组后喂给它。
5. **前端缓存**：`getDatabasesList`（`databaseToolApi.ts:133-158`）已有 IndexedDB 缓存 + in-flight 去重；`getSchemasList`（第 160-172 行）有 IndexedDB 缓存但**无 in-flight 去重、无 skipCache**。`dbCache.ts` 的 `CACHE_CONFIG` 无 `schemas` 项，已自动回落到 5 分钟默认 TTL。
6. **返回格式破坏性变更**：`getDatabasesList` 对 PG 的返回从 `["db:schema",...]` 改为 `["db",...]`，前后端必须同时上线，且需让旧 IndexedDB 缓存失效。

---

## File Structure

**后端：**
- `backend/app/services/database_tool_service.py`
  - 新增全局实例 `_LIST_CACHE`（5 分钟 TTL），用于库名/ schema 列表缓存。
  - 改造 `get_databases_list(user_id, config_id, skip_cache=False)`：PG 无 database_name 分支只查 `pg_database`，加缓存。
  - 改造 `get_schemas_list(user_id, config_id, database_name=None, skip_cache=False)`：加缓存。
  - 新增 `get_all_schemas(user_id, config_id, skip_cache=False) -> Dict[str, List[str]]`：线程池并行查各库 schema。
- `backend/app/routes/database_tool.py`
  - `get_databases_list` / `get_schemas_list` 路由加 `skip_cache` Query 参数透传。
  - 新增路由 `GET /database-tool/databases/{id}/all-schemas`。
- `backend/tests/test_database_tool_service.py`
  - 新增列库不遍历 schema、缓存命中、并行全量、缓存失效的单测。

**前端：**
- `frontend/src/api/databaseToolApi.ts`
  - `getDatabasesList(id, skipCache=false)`：加 skipCache。
  - `getSchemasList(id, databaseName, skipCache=false)`：加 in-flight 去重 + skipCache。
  - 新增 `getAllSchemas(id, skipCache=false): Promise<Record<string,string[]>>`。
  - 提升 DBCache 版本或变更 databases cacheKey，使旧 `db:schema` 缓存失效。
- `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`
  - PG 无 database_name 渲染：不再 `split(':')`，直接用库名列表渲染 `PostgresDatabaseNode`。
  - `PostgresDatabaseNode`：展开库时懒加载 schema（带 loading/错误态）。
  - 搜索场景：调 `getAllSchemas` 并行取全量后分组渲染。
- `frontend/src/utils/dbCache.ts`
  - `DB_VERSION` 自增或在 `CACHE_CONFIG` 明确加 `schemas` 项（5 分钟）。

---

## Task 1: 后端新增 5 分钟列表缓存实例

**Files:**
- Modify: `backend/app/services/database_tool_service.py:102`

- [ ] **Step 1: 在已有 `_STRUCTURE_CACHE` 定义下方新增列表缓存实例**

定位 `database_tool_service.py:102` 的这一行：

```python
# 全局实例：1 小时 TTL，最多 100 条
_STRUCTURE_CACHE = StructureCache(ttl=3600, maxsize=100)
```

在其下方新增：

```python
# 库名/Schema 列表缓存：5 分钟 TTL（schema 变动不频繁，靠右键刷新与写操作失效兜底）
_LIST_CACHE = StructureCache(ttl=300, maxsize=200)
```

- [ ] **Step 2: 语法检查**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m py_compile app/services/database_tool_service.py && echo OK`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/database_tool_service.py
git commit -m "feat: 新增数据库列表 5 分钟 TTL 缓存实例"
```

---

## Task 2: 后端列库瘦身 + 缓存（核心提速）

**Files:**
- Modify: `backend/app/services/database_tool_service.py:1100-1198`
- Test: `backend/tests/test_database_tool_service.py`

- [ ] **Step 1: 写失败测试——验证 PG 列库只查 pg_database、不遍历各库**

在 `backend/tests/test_database_tool_service.py` 末尾追加：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py::test_pg_get_databases_list_only_queries_pg_database -v`
Expected: FAIL（当前实现遍历各库并执行 `information_schema.schemata`，断言不通过；或 `get_databases_list` 不接受 `skip_cache` 参数报 TypeError）

- [ ] **Step 3: 改造 `get_databases_list` 方法签名与缓存逻辑**

定位 `database_tool_service.py:1100-1104`：

```python
    @staticmethod
    def get_databases_list(user_id: str, config_id: str) -> List[str]:
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
```

替换为（加 `skip_cache` 参数 + 缓存读取）：

```python
    @staticmethod
    def get_databases_list(user_id: str, config_id: str, skip_cache: bool = False) -> List[str]:
        cache_key = f"databases:{config_id}"
        if not skip_cache:
            cached = _LIST_CACHE.get(cache_key)
            if cached is not None:
                return cached

        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
```

- [ ] **Step 4: 用一条 pg_database 查询替换 PG 遍历各库逻辑**

定位 `database_tool_service.py:1144-1186`（PG 无 database_name 的 `else` 分支，从 `# 查询所有非模板数据库` 注释开始，到 `fallback_engine.dispose()` 结束）。整段替换为：

```python
                    else:
                        # 只列库名：连 postgres 系统库查 pg_database，不再遍历各库查 schema。
                        # Schema 改由 get_schemas_list 在展开具体数据库时懒加载。
                        fallback_config = config_dict.copy()
                        fallback_config["database_name"] = "postgres"
                        temp_key = f"{config_id}:_temp_postgres_fallback"
                        fallback_engine = DBConnectionManager.get_engine(
                            temp_key, fallback_config
                        )
                        try:
                            with fallback_engine.connect() as fallback_conn:
                                db_result = fallback_conn.execute(
                                    text(
                                        "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
                                    )
                                )
                                databases = [row[0] for row in db_result]
                        finally:
                            fallback_engine.dispose()
```

- [ ] **Step 5: 在 return 前写入缓存**

定位方法结尾 `database_tool_service.py:1198`：

```python
        return sorted(databases)
```

替换为：

```python
        result = sorted(databases)
        _LIST_CACHE.set(cache_key, result)
        return result
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py::test_pg_get_databases_list_only_queries_pg_database -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/database_tool_service.py backend/tests/test_database_tool_service.py
git commit -m "feat: PG 列库瘦身为只查 pg_database 并加 5 分钟缓存"
```

---

## Task 3: 后端列库路由透传 skip_cache

**Files:**
- Modify: `backend/app/routes/database_tool.py:183-194`

- [ ] **Step 1: 给 get_databases_list 路由加 skip_cache 参数**

定位 `routes/database_tool.py:183-194`：

```python
@router.get("/databases/{id}/databases", response_model=List[str])
async def get_databases_list(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """List databases for a connection"""
    try:
        return DatabaseToolService.get_databases_list(user_id, id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

替换为：

```python
@router.get("/databases/{id}/databases", response_model=List[str])
async def get_databases_list(
    id: str = PathParam(..., description="Configuration ID"),
    skip_cache: bool = Query(False, description="跳过缓存强制刷新"),
    user_id: str = Depends(get_current_user_id),
):
    """List databases for a connection"""
    try:
        return DatabaseToolService.get_databases_list(user_id, id, skip_cache=skip_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: 语法检查**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m py_compile app/routes/database_tool.py && echo OK`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/database_tool.py
git commit -m "feat: 列库路由支持 skip_cache 强制刷新"
```

---

## Task 4: 后端列 schema 加缓存 + skip_cache

**Files:**
- Modify: `backend/app/services/database_tool_service.py:1200-1244`
- Test: `backend/tests/test_database_tool_service.py`

- [ ] **Step 1: 写失败测试——验证列 schema 命中缓存不重复查库**

在 `backend/tests/test_database_tool_service.py` 末尾追加：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py::test_pg_get_schemas_list_uses_cache -v`
Expected: FAIL（当前无缓存，`connect_count["n"] == 2`）

- [ ] **Step 3: 改造 get_schemas_list 方法签名 + 缓存读取**

定位 `database_tool_service.py:1200-1205`：

```python
    @staticmethod
    def get_schemas_list(user_id: str, config_id: str, database_name: Optional[str] = None) -> List[str]:
        """获取指定数据库下的 schema 列表（PostgreSQL）"""
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
```

替换为：

```python
    @staticmethod
    def get_schemas_list(
        user_id: str, config_id: str, database_name: Optional[str] = None,
        skip_cache: bool = False,
    ) -> List[str]:
        """获取指定数据库下的 schema 列表（PostgreSQL）"""
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            raise ValueError("Configuration not found")
```

- [ ] **Step 4: 在确定 target_db 后插入缓存读取**

定位 `database_tool_service.py:1217-1220`：

```python
        # 确定目标数据库名：优先使用参数，其次使用配置中的 database_name
        target_db = database_name or config_row.get("database_name")
        if not target_db:
            raise ValueError("database_name is required for PostgreSQL schema listing")
```

替换为：

```python
        # 确定目标数据库名：优先使用参数，其次使用配置中的 database_name
        target_db = database_name or config_row.get("database_name")
        if not target_db:
            raise ValueError("database_name is required for PostgreSQL schema listing")

        cache_key = f"schemas:{config_id}:{target_db}"
        if not skip_cache:
            cached = _LIST_CACHE.get(cache_key)
            if cached is not None:
                return cached
```

- [ ] **Step 5: 写入缓存后返回**

定位 `database_tool_service.py:1236-1244`：

```python
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
                )
                schemas = [row[0] for row in result]
            return schemas
        finally:
            engine.dispose()
```

替换为：

```python
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
                )
                schemas = [row[0] for row in result]
            _LIST_CACHE.set(cache_key, schemas)
            return schemas
        finally:
            engine.dispose()
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py::test_pg_get_schemas_list_uses_cache -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/database_tool_service.py backend/tests/test_database_tool_service.py
git commit -m "feat: 列 schema 加 5 分钟缓存与 skip_cache"
```

---

## Task 5: 后端新增并行全量 schema 查询（搜索用）

**Files:**
- Modify: `backend/app/services/database_tool_service.py`（在 `get_schemas_list` 方法后新增方法 + 文件顶部加 import）
- Test: `backend/tests/test_database_tool_service.py`

- [ ] **Step 1: 文件顶部新增 ThreadPoolExecutor import**

定位 `database_tool_service.py:5`（`import threading` 行），在其下方新增：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

- [ ] **Step 2: 写失败测试——验证并行全量返回 {db: [schema]} 且单库异常被隔离**

在 `backend/tests/test_database_tool_service.py` 末尾追加：

```python
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
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py::test_pg_get_all_schemas_parallel_and_isolates_errors -v`
Expected: FAIL with "AttributeError: ... has no attribute 'get_all_schemas'"

- [ ] **Step 4: 在 get_schemas_list 方法后新增 get_all_schemas**

定位 `get_schemas_list` 方法结尾（`engine.dispose()` 那一段之后、`get_database_structure` 方法之前），插入新方法：

```python
    @staticmethod
    def get_all_schemas(
        user_id: str, config_id: str, skip_cache: bool = False
    ) -> Dict[str, List[str]]:
        """并行查询某 PG 连接下所有库的 schema，供搜索场景使用。

        返回 {database_name: [schema, ...]}。单库查询失败被隔离，记 warning 后跳过。
        """
        cache_key = f"all_schemas:{config_id}"
        if not skip_cache:
            cached = _LIST_CACHE.get(cache_key)
            if cached is not None:
                return cached

        db_names = DatabaseToolService.get_databases_list(
            user_id, config_id, skip_cache=skip_cache
        )

        result: Dict[str, List[str]] = {}

        def _fetch_one(db_name: str):
            return db_name, DatabaseToolService.get_schemas_list(
                user_id, config_id, db_name, skip_cache=skip_cache
            )

        # 限制并发，避免短时占用过多数据库连接
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_fetch_one, db): db for db in db_names}
            for future in as_completed(futures):
                db = futures[future]
                try:
                    name, schemas = future.result()
                    result[name] = schemas
                except Exception as exc:
                    logger.warning(f"Failed to get schemas for {db}: {exc}")

        _LIST_CACHE.set(cache_key, result)
        return result
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py::test_pg_get_all_schemas_parallel_and_isolates_errors -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/database_tool_service.py backend/tests/test_database_tool_service.py
git commit -m "feat: 新增并行全量 schema 查询 get_all_schemas"
```

---

## Task 6: 后端 schemas 路由 skip_cache + all-schemas 路由 + 写操作失效

**Files:**
- Modify: `backend/app/routes/database_tool.py:48`（import）
- Modify: `backend/app/routes/database_tool.py:197-209`（schemas 路由）
- Modify: `backend/app/routes/database_tool.py:183-194`（databases 路由后新增 all-schemas）
- Modify: `backend/app/routes/database_tool.py:341-360`（建/删库失效列表缓存）

- [ ] **Step 1: import 加上 _LIST_CACHE**

定位 `routes/database_tool.py:48`：

```python
from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE
```

替换为：

```python
from app.services.database_tool_service import DatabaseToolService, _STRUCTURE_CACHE, _LIST_CACHE
```

- [ ] **Step 2: get_schemas_list 路由加 skip_cache**

定位 `routes/database_tool.py:197-209`：

```python
@router.get("/databases/{id}/schemas", response_model=List[str])
async def get_schemas_list(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: Optional[str] = Query(None, description="Database Name (PostgreSQL)"),
    user_id: str = Depends(get_current_user_id),
):
    """List schemas for a specific database (PostgreSQL)"""
    try:
        return DatabaseToolService.get_schemas_list(user_id, id, database_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

替换为：

```python
@router.get("/databases/{id}/schemas", response_model=List[str])
async def get_schemas_list(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: Optional[str] = Query(None, description="Database Name (PostgreSQL)"),
    skip_cache: bool = Query(False, description="跳过缓存强制刷新"),
    user_id: str = Depends(get_current_user_id),
):
    """List schemas for a specific database (PostgreSQL)"""
    try:
        return DatabaseToolService.get_schemas_list(
            user_id, id, database_name, skip_cache=skip_cache
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 新增 all-schemas 路由**

在上面 schemas 路由之后（`routes/database_tool.py:209` 之后、`get_database_structure` 路由 `@router.get("/databases/{id}/structure"...` 之前）插入：

```python
@router.get("/databases/{id}/all-schemas", response_model=Dict[str, List[str]])
async def get_all_schemas(
    id: str = PathParam(..., description="Configuration ID"),
    skip_cache: bool = Query(False, description="跳过缓存强制刷新"),
    user_id: str = Depends(get_current_user_id),
):
    """并行返回某 PG 连接下所有库的 schema（搜索用）"""
    try:
        return DatabaseToolService.get_all_schemas(user_id, id, skip_cache=skip_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: 建库成功后失效列表缓存**

定位 `routes/database_tool.py:341-344`：

```python
        result = DatabaseToolService.create_database_instance(user_id, id, name, charset)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{name}")
        return result
```

替换为：

```python
        result = DatabaseToolService.create_database_instance(user_id, id, name, charset)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{name}")
            _LIST_CACHE.invalidate_prefix(f"databases:{id}")
            _LIST_CACHE.invalidate_prefix(f"all_schemas:{id}")
        return result
```

- [ ] **Step 5: 删库成功后失效列表缓存**

定位 `routes/database_tool.py:357-360`：

```python
        result = DatabaseToolService.drop_database_instance(user_id, id, name)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{name}")
        return result
```

替换为：

```python
        result = DatabaseToolService.drop_database_instance(user_id, id, name)
        if result:
            _STRUCTURE_CACHE.invalidate(f"{id}:{name}")
            _LIST_CACHE.invalidate_prefix(f"databases:{id}")
            _LIST_CACHE.invalidate_prefix(f"schemas:{id}:{name}")
            _LIST_CACHE.invalidate_prefix(f"all_schemas:{id}")
        return result
```

- [ ] **Step 6: 语法检查**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m py_compile app/routes/database_tool.py && echo OK`
Expected: 输出 `OK`

- [ ] **Step 7: 运行后端全部相关测试**

Run: `cd backend && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pytest tests/test_database_tool_service.py -v`
Expected: 全部 PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/routes/database_tool.py
git commit -m "feat: schemas/all-schemas 路由支持缓存与并行，写操作失效列表缓存"
```

---

## Task 7: 前端 API 层——库名缓存版本升级 + schema 去重/skipCache + getAllSchemas

**Files:**
- Modify: `frontend/src/api/databaseToolApi.ts:133-172`、第 221-225 行附近（pending Map 声明）

**说明**：返回格式从 `db:schema` 变为 `db`，必须让旧 IndexedDB 缓存失效。`DB_VERSION` 自增不会清空已有数据（升级回调仅在 store 缺失时建 store），因此改用**变更 cacheKey**（加 `v2` 版本前缀）使旧缓存自然失效。

- [ ] **Step 1: getDatabasesList 加 skipCache + 升级 cacheKey 版本**

定位 `databaseToolApi.ts:133-158`：

```typescript
export async function getDatabasesList(id: string): Promise<string[]> {
  const cacheKey = `databases:${id}`;
  const cached = await DBCache.get<string[]>(cacheKey);
  if (cached) return cached;

  // In-flight 去重：同一连接的并发请求共享 Promise，避免重复请求
  if (pendingDatabasesRequests.has(id)) {
    return pendingDatabasesRequests.get(id)!;
  }

  const requestPromise = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/databases/${id}/databases`, {
        headers: getAuthHeaders()
      });
      const data = await handleResponse<string[]>(response);
      await DBCache.set(cacheKey, data, 'databases');
      return data;
    } finally {
      pendingDatabasesRequests.delete(id);
    }
  })();

  pendingDatabasesRequests.set(id, requestPromise);
  return requestPromise;
}
```

替换为：

```typescript
export async function getDatabasesList(id: string, skipCache = false): Promise<string[]> {
  // v2：返回格式从 "db:schema" 变为 "db"，提升 cacheKey 版本使旧缓存失效
  const cacheKey = `databases:v2:${id}`;
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    const cached = await DBCache.get<string[]>(cacheKey);
    if (cached) return cached;
  }

  // In-flight 去重：同一连接的并发请求共享 Promise，避免重复请求
  if (pendingDatabasesRequests.has(id)) {
    return pendingDatabasesRequests.get(id)!;
  }

  const requestPromise = (async () => {
    try {
      const query = skipCache ? '?skip_cache=true' : '';
      const response = await fetch(`${BASE_URL}/databases/${id}/databases${query}`, {
        headers: getAuthHeaders()
      });
      const data = await handleResponse<string[]>(response);
      await DBCache.set(cacheKey, data, 'databases');
      return data;
    } finally {
      pendingDatabasesRequests.delete(id);
    }
  })();

  pendingDatabasesRequests.set(id, requestPromise);
  return requestPromise;
}
```

- [ ] **Step 2: getSchemasList 加 in-flight 去重 + skipCache**

定位 `databaseToolApi.ts:160-172`：

```typescript
export async function getSchemasList(id: string, databaseName: string): Promise<string[]> {
  const cacheKey = `schemas:${id}:${databaseName}`;
  const cached = await DBCache.get<string[]>(cacheKey);
  if (cached) return cached;

  const response = await fetch(
    `${BASE_URL}/databases/${id}/schemas?database_name=${encodeURIComponent(databaseName)}`,
    { headers: getAuthHeaders() }
  );
  const data = await handleResponse<string[]>(response);
  await DBCache.set(cacheKey, data, 'schemas');
  return data;
}
```

替换为：

```typescript
export async function getSchemasList(
  id: string, databaseName: string, skipCache = false
): Promise<string[]> {
  const cacheKey = `schemas:${id}:${databaseName}`;
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    const cached = await DBCache.get<string[]>(cacheKey);
    if (cached) return cached;
  }

  const pendingKey = `${id}:${databaseName}`;
  if (pendingSchemasRequests.has(pendingKey)) {
    return pendingSchemasRequests.get(pendingKey)!;
  }

  const requestPromise = (async () => {
    try {
      const skipParam = skipCache ? '&skip_cache=true' : '';
      const response = await fetch(
        `${BASE_URL}/databases/${id}/schemas?database_name=${encodeURIComponent(databaseName)}${skipParam}`,
        { headers: getAuthHeaders() }
      );
      const data = await handleResponse<string[]>(response);
      await DBCache.set(cacheKey, data, 'schemas');
      return data;
    } finally {
      pendingSchemasRequests.delete(pendingKey);
    }
  })();

  pendingSchemasRequests.set(pendingKey, requestPromise);
  return requestPromise;
}

export async function getAllSchemas(
  id: string, skipCache = false
): Promise<Record<string, string[]>> {
  const cacheKey = `all_schemas:${id}`;
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    const cached = await DBCache.get<Record<string, string[]>>(cacheKey);
    if (cached) return cached;
  }

  if (pendingAllSchemasRequests.has(id)) {
    return pendingAllSchemasRequests.get(id)!;
  }

  const requestPromise = (async () => {
    try {
      const query = skipCache ? '?skip_cache=true' : '';
      const response = await fetch(`${BASE_URL}/databases/${id}/all-schemas${query}`, {
        headers: getAuthHeaders()
      });
      const data = await handleResponse<Record<string, string[]>>(response);
      await DBCache.set(cacheKey, data, 'databases');
      return data;
    } finally {
      pendingAllSchemasRequests.delete(id);
    }
  })();

  pendingAllSchemasRequests.set(id, requestPromise);
  return requestPromise;
}
```

- [ ] **Step 3: 新增 pending Map 声明**

定位 `databaseToolApi.ts:223`：

```typescript
const pendingDatabasesRequests = new Map<string, Promise<string[]>>();
```

在其下方新增：

```typescript
const pendingSchemasRequests = new Map<string, Promise<string[]>>();
const pendingAllSchemasRequests = new Map<string, Promise<Record<string, string[]>>>();
```

- [ ] **Step 4: 前端类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无与 `databaseToolApi.ts` 相关的报错（已有的无关报错忽略）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/databaseToolApi.ts
git commit -m "feat: 前端库名缓存升级v2，schema 加去重/skipCache，新增 getAllSchemas"
```

---

## Task 8: 前端组件——PG 渲染改为懒加载 schema + 搜索走 getAllSchemas

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx:600-636`（PG 渲染分支）
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx:1444-1513`（PostgresDatabaseNode）

**背景**：现在 `databases` 数组对 PG 也只含库名（不再是 `db:schema`）。父级不再需要 `split(':')` 分组；`PostgresDatabaseNode` 改为展开库时懒加载 schema。搜索时需要 schema 名参与匹配，故在搜索激活时预取 `getAllSchemas` 并作为初始 `schemaNames` 传入。

- [ ] **Step 1: 在 ConnectionItem 组件内新增搜索期全量 schema 状态**

定位 `ConnectionList.tsx:261-262`：

```typescript
  // Search results from backend: { database: table_list }
  const [searchResults, setSearchResults] = useState<Record<string, string[]>>({});
  const [searching, setSearching] = useState(false);
```

在其下方新增：

```typescript
  // 搜索期：PG 各库 schema 全量（供 schema 名匹配），key=db, value=schema[]
  const [allSchemas, setAllSchemas] = useState<Record<string, string[]>>({});
```

- [ ] **Step 2: 搜索激活时为 PG 预取全量 schema**

定位 `ConnectionList.tsx:300-302`（搜索 useEffect 的开头）：

```typescript
  useEffect(() => {
      let active = true;
      const search = async () => {
```

在 `const search = async () => {` 之后、`if (!searchTerm ...` 之前插入预取（保持原有逻辑不动，仅追加）：

```typescript
          // PG：搜索时并行预取所有库 schema，供 schema 名匹配
          if (searchTerm && searchTerm.length >= 2 && config.db_type === 'postgresql' && !config.database_name) {
              api.getAllSchemas(config.id)
                  .then(s => { if (active) setAllSchemas(s); })
                  .catch(() => {});
          }
```

- [ ] **Step 3: 替换 PG 无 database_name 的渲染块（去掉 split 分组，懒加载）**

定位 `ConnectionList.tsx:600-636`（从 `// 未指定 database_name，databases 是 "database:schema" 格式` 注释到该 IIFE 的 `})()` 结束）。整段替换为：

```typescript
                // 未指定 database_name：databases 是库名列表，schema 懒加载
                filteredDatabases.map(dbName => (
                  <PostgresDatabaseNode
                    key={dbName}
                    configId={config.id}
                    dbName={dbName}
                    initialSchemaNames={allSchemas[dbName]}
                    onSelectTable={onSelectTable}
                    onSelectDatabase={onSelectDatabase}
                    onOpenSqlConsole={onOpenSqlConsole}
                    onOpenBackup={(d, tables) => onOpenBackup(config.id, d, tables)}
                    onOpenBackupHistory={(d) => onOpenBackupHistory(config.id, d)}
                    searchTerm={searchTerm}
                    activeDatabaseName={activeDatabaseName}
                    activeSchemaName={activeSchemaName}
                  />
                ))
```

- [ ] **Step 4: 改造 PostgresDatabaseNode props 接口（schemaNames 改为 initialSchemaNames 可选）**

定位 `ConnectionList.tsx:1444-1456`：

```typescript
interface PostgresDatabaseNodeProps {
  configId: string;
  dbName: string;
  schemaNames: string[];
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => void;
  onSelectDatabase: (configId: string, dbName: string, schemaName?: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string, schemaName?: string) => void;
  onOpenBackup: (dbName: string, tables?: string[]) => void;
  onOpenBackupHistory: (dbName: string) => void;
  searchTerm: string;
  activeDatabaseName?: string;
  activeSchemaName?: string;
}
```

替换为：

```typescript
interface PostgresDatabaseNodeProps {
  configId: string;
  dbName: string;
  initialSchemaNames?: string[];
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => void;
  onSelectDatabase: (configId: string, dbName: string, schemaName?: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string, schemaName?: string) => void;
  onOpenBackup: (dbName: string, tables?: string[]) => void;
  onOpenBackupHistory: (dbName: string) => void;
  searchTerm: string;
  activeDatabaseName?: string;
  activeSchemaName?: string;
}
```

- [ ] **Step 5: 改造 PostgresDatabaseNode 实现为懒加载**

定位 `ConnectionList.tsx:1458-1490`（从 `const PostgresDatabaseNode...` 到 `<span ...>{filteredSchemas.length}</span>` 所在 div 之前的逻辑部分）。把组件顶部到 `isActive` 定义替换为：

```typescript
const PostgresDatabaseNode: React.FC<PostgresDatabaseNodeProps> = ({
  configId, dbName, initialSchemaNames, onSelectTable, onSelectDatabase,
  onOpenSqlConsole, onOpenBackup, onOpenBackupHistory, searchTerm, activeDatabaseName, activeSchemaName
}) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [schemaNames, setSchemaNames] = useState<string[]>(initialSchemaNames ?? []);
  const [schemasLoaded, setSchemasLoaded] = useState<boolean>(!!initialSchemaNames);
  const [loadingSchemas, setLoadingSchemas] = useState(false);

  // 搜索态传入的全量 schema 到达后同步进来
  useEffect(() => {
    if (initialSchemaNames) {
      setSchemaNames(initialSchemaNames);
      setSchemasLoaded(true);
    }
  }, [initialSchemaNames]);

  const fetchSchemas = async (skipCache = false) => {
    setLoadingSchemas(true);
    try {
      const data = await api.getSchemasList(configId, dbName, skipCache);
      setSchemaNames(data);
      setSchemasLoaded(true);
    } catch (err) {
      console.error("Failed to load schemas", err);
      toast.error(t.database?.status?.loadFailed || '加载 Schema 失败');
    } finally {
      setLoadingSchemas(false);
    }
  };

  const handleToggle = () => {
    const next = !isExpanded;
    setIsExpanded(next);
    onSelectDatabase(configId, dbName);
    if (next && !schemasLoaded && !loadingSchemas) {
      fetchSchemas();
    }
  };

  const filteredSchemas = searchTerm
    ? schemaNames.filter(s => s.toLowerCase().includes(searchTerm.toLowerCase()))
    : schemaNames;

  if (searchTerm && schemasLoaded && filteredSchemas.length === 0) return null;

  const isActive = activeDatabaseName === dbName;
```

- [ ] **Step 6: 更新 PostgresDatabaseNode 的 JSX（onClick 用 handleToggle，加 loading 态）**

定位 `ConnectionList.tsx` 中 PostgresDatabaseNode 的渲染（`onClick={() => { setIsExpanded(!isExpanded); onSelectDatabase(configId, dbName); }}` 那段，约第 1479-1482 行）：

```typescript
        onClick={() => {
          setIsExpanded(!isExpanded);
          onSelectDatabase(configId, dbName);
        }}
```

替换为：

```typescript
        onClick={handleToggle}
```

然后定位计数徽标（约第 1489 行）：

```typescript
        <span className="text-[10px] bg-slate-700 px-1 rounded-full">{filteredSchemas.length}</span>
```

替换为（加载中显示 spinner）：

```typescript
        {loadingSchemas ? (
          <i className="fas fa-spinner fa-spin text-[10px] text-slate-400"></i>
        ) : (
          schemasLoaded && <span className="text-[10px] bg-slate-700 px-1 rounded-full">{filteredSchemas.length}</span>
        )}
```

- [ ] **Step 7: 前端类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "ConnectionList" | head -20`
Expected: 无 `ConnectionList.tsx` 相关报错

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx
git commit -m "feat: PG 数据库节点改为懒加载 schema，搜索走 getAllSchemas"
```

---

## Task 9: 端到端验证（后端计时 + 浏览器）

**Files:** 无（仅验证）

- [ ] **Step 1: 确认热加载已生效（后端 --reload）**

修改保存后等待 3-5 秒，确认 uvicorn 已重载。检查：

Run: `curl -s -m 8 -o /dev/null -w "根路径:%{http_code} %{time_total}s\n" http://localhost:19092/`
Expected: `根路径:200`，耗时 < 0.1s

- [ ] **Step 2: 登录获取 token**

Run:
```bash
TOKEN=$(curl -s -m 10 -X POST http://localhost:19092/api/auth/login -H "Content-Type: application/json" -d '{"username":"peanut","password":"Peanut2817*#"}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('token') or d.get('access_token',''))")
echo "${#TOKEN}"
```
Expected: 输出 token 长度（约 212）

- [ ] **Step 3: 计时验证 PG 连接展开（原 5.5s 的连接 6f051a47）**

Run:
```bash
ID=$(curl -s -m 15 http://localhost:19092/api/database-tool/databases -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json;[print(x['id']) for x in json.load(sys.stdin) if x['id'].startswith('6f051a47')]")
curl -s -m 30 -o /tmp/r.json -w "列库耗时:%{time_total}s\n" "http://localhost:19092/api/database-tool/databases/$ID/databases?skip_cache=true" -H "Authorization: Bearer $TOKEN"
python3 -c "import json;d=json.load(open('/tmp/r.json'));print('返回类型: 库名列表' if d and ':' not in d[0] else '仍是 db:schema 格式（错误）', '项数:', len(d))"
```
Expected: `列库耗时 < 0.3s`；返回为库名列表（无冒号）

- [ ] **Step 4: 计时验证单库 schema 懒加载**

Run:
```bash
DB=$(python3 -c "import json;print(json.load(open('/tmp/r.json'))[0])")
curl -s -m 15 -o /dev/null -w "列schema耗时:%{time_total}s\n" "http://localhost:19092/api/database-tool/databases/$ID/schemas?database_name=$DB" -H "Authorization: Bearer $TOKEN"
curl -s -m 15 -o /dev/null -w "列schema(缓存)耗时:%{time_total}s\n" "http://localhost:19092/api/database-tool/databases/$ID/schemas?database_name=$DB" -H "Authorization: Bearer $TOKEN"
```
Expected: 首次 < 0.5s；第二次（缓存）< 0.05s

- [ ] **Step 5: 浏览器验证（全局强制要求）**

Run: `agent-browser open "http://localhost:5178/tools/database-tool"`，登录后：
- 展开 PG 连接 → 瞬时列出库名（不再卡 2-5s）
- 点开某个库 → 出现 spinner 后列出 schema
- 点开 schema → 表/视图正常
- 搜索一个 schema 名 → 跨库匹配能展开命中
- 右键连接「刷新」→ 强制重查生效
- Console 无报错
- MySQL 连接展开行为未回归

Expected: 全部满足；展开 PG 连接肉眼瞬时

- [ ] **Step 6: 清理临时文件**

Run: `rm -f /tmp/r.json /tmp/dbtoken.txt /tmp/dbresp.json`

---

## Self-Review（已执行）

**1. Spec coverage：**
- 列库瘦身 → Task 2 ✅
- schema 懒加载接口接入 → Task 4（缓存）+ Task 8（前端调用）✅
- 5 分钟 TTL 缓存 → Task 1（实例）+ Task 2/4（接入）✅
- 并行兜底（搜索）→ Task 5（后端）+ Task 8（前端 getAllSchemas）✅
- 返回格式破坏性变更 + 旧缓存失效 → Task 7（cacheKey v2）✅
- 前端分层懒加载渲染 → Task 8 ✅
- 右键刷新 skipCache → Task 3/6（路由）+ Task 7（API skipCache）✅
- 写操作失效缓存 → Task 6 ✅
- 测试（后端单测 + 浏览器）→ Task 2/4/5（单测）+ Task 9（端到端）✅

**2. Placeholder scan：** 无 TBD/TODO，每个代码步骤含完整代码。

**3. Type consistency：**
- 缓存实例统一 `_LIST_CACHE`；方法 `get_databases_list/get_schemas_list/get_all_schemas` 签名前后一致。
- 前端 `getDatabasesList(id, skipCache)`、`getSchemasList(id, db, skipCache)`、`getAllSchemas(id, skipCache)` 与组件调用一致。
- 组件 prop 从 `schemaNames` 改为 `initialSchemaNames`，接口与父级传参（Task 8 Step 3）、实现（Step 4/5）一致。
- pending Map：`pendingSchemasRequests`、`pendingAllSchemasRequests` 声明（Step 3）与使用（Step 2）一致。

**注意事项（执行者必读）：**
- 前端文案 `t.database?.status?.loadFailed` 若 i18n 无此键，toast 会显示中文兜底 `'加载 Schema 失败'`，无需新增 i18n 键即可工作；如需规范化可后续补键。
- 后端服务以 `--reload` 运行，改完等热加载；切勿手动重启（遵循项目 dev_services 规则，但本机当前直接 uvicorn --reload）。
