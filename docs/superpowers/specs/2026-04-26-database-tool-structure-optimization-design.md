---
author: Peanut
created_at: 2026-04-26
purpose: 解决 structure 接口 20+ 秒慢查询的优化方案（修订版）
---

# 数据库工具 Structure 接口性能优化设计文档（修订版）

## 1. 问题概述

上一轮优化后，数据库列表加载已走 IndexedDB 缓存（4.59s），但 `structure` 接口仍然是瓶颈：

从 Chrome DevTools Network 面板观察到：
- `GET /api/database-tool/databases/{id}/structure?database_name=tools` 耗时 **20.67s**
- 相同接口被调用 **3 次**，各耗时 20-24s
- 总加载时间 = 20s+（并行但都被拖慢）

### 根因分析

1. **前端重复请求** — [SQLExecutor.tsx](frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx) 两个 useEffect 依赖完全相同 `[currentConfig?.id, currentDatabase]`，同时触发 `getDatabaseStructure`。即使 IndexedDB 缓存已实现，但**并发请求无法命中**（第一个请求尚未返回写入缓存，第二个已出发）
2. **前端无 In-flight 去重** — API 层没有对相同 URL 的并发请求做 Promise 共享
3. **后端无缓存** — 每次请求都直查 `information_schema.TABLES` 和 `information_schema.VIEWS`，无服务端缓存
4. **SQL 查询未优化** — 两张信息表分开查询（2 次 round-trip），且 `information_schema` 在表多的数据库中本身较慢
5. **无后端 DDL 感知的缓存失效** — 即使加了服务端缓存，如果 SQL Executor 执行了 DDL，缓存不会失效

## 2. 优化目标

- 消除重复请求：3 个 → **1 个**（前端去重）
- 首次 `structure` 请求时间：**视数据库规模而定**，目标是消除不必要的开销
- 后续 `structure` 请求（缓存命中）：**< 500ms**
- DDL 操作后缓存正确失效

## 3. 架构设计

### 3.1 前端请求去重（In-flight Dedup + 组件层优化）

#### 3.1.1 API 层 In-flight Dedup

修改文件：[frontend/src/api/databaseToolApi.ts](frontend/src/api/databaseToolApi.ts)

新增一个 **In-flight Promise 共享层**，对相同 cacheKey 的并发请求共享同一个 Promise：

```typescript
// 模块级 in-flight 请求追踪
const pendingStructureRequests = new Map<string, Promise<DatabaseStructure>>();

export async function getDatabaseStructure(id: string, databaseName: string): Promise<DatabaseStructure> {
  const cacheKey = `structure:${id}:${databaseName}`;

  // 1. 查 IndexedDB 缓存
  const cached = await DBCache.get<DatabaseStructure>(cacheKey);
  if (cached) return cached;

  // 2. 检查是否已有相同请求在飞行中
  if (pendingStructureRequests.has(cacheKey)) {
    return pendingStructureRequests.get(cacheKey)!;
  }

  // 3. 发起请求并注册到 in-flight 追踪
  const requestPromise = (async () => {
    try {
      const response = await fetch(
        `${BASE_URL}/databases/${id}/structure?database_name=${encodeURIComponent(databaseName)}`,
        { headers: getAuthHeaders() }
      );
      const data = await handleResponse<DatabaseStructure>(response);
      await DBCache.set(cacheKey, data, 'structure');
      return data;
    } finally {
      pendingStructureRequests.delete(cacheKey);
    }
  })();

  pendingStructureRequests.set(cacheKey, requestPromise);
  return requestPromise;
}
```

**注意**：
1. 失败时 Promise 会 reject，所有共享者都会收到错误。这在并发场景下是合理行为（后端确实挂了），不需要额外的重试逻辑。
2. In-flight dedup 不仅解决 SQLExecutor.tsx 的重复请求，也覆盖 ConnectionList.tsx 中的 `fetchStructure` 调用（当两者同时挂载时）。

#### 3.1.2 组件层去重

修改文件：[frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx](frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx)

合并两个依赖相同的 useEffect。当前有两个 useEffect 都依赖 `[currentConfig?.id, currentDatabase]`，各自独立调用 `getDatabaseStructure`。合并后只调用一次。

### 3.2 后端缓存（标准库实现，无新依赖）

修改文件：[backend/app/services/database_tool_service.py](backend/app/services/database_tool_service.py)

**不使用 cachetools**（避免新依赖），改用 `time` + `dict` 实现 TTL 缓存：

```python
import time
from threading import Lock

class StructureCache:
    """线程安全的 TTL 缓存，无需外部依赖"""
    def __init__(self, ttl: int = 600, maxsize: int = 100):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl
        self._maxsize = maxsize
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._timestamps[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            # LRU 淘汰
            if len(self._cache) >= self._maxsize and key not in self._cache:
                oldest_key = min(self._timestamps, key=self._timestamps.get)
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
                del self._timestamps[k]

# 全局实例：10 分钟 TTL，最多 100 条
_STRUCTURE_CACHE = StructureCache(ttl=600, maxsize=100)
```

**多 Worker 场景说明**：每个 Uvicorn worker 进程有独立的缓存实例。这会导致：
- 同一请求可能被不同 worker 查询多次（缓存不共享）
- 这是可接受的 trade-off：引入 Redis 跨进程缓存会增加复杂度和运维成本，而 structure 数据变更频率极低（用户很少执行 DDL）

#### 3.2.1 缓存查询逻辑

```python
@staticmethod
def get_database_structure(user_id: str, config_id: str, database_name: str) -> Dict[str, List[Dict[str, Any]]]:
    cache_key = f"{config_id}:{database_name}"

    # 查缓存
    cached = _STRUCTURE_CACHE.get(cache_key)
    if cached:
        return cached

    # ... 原有查询逻辑（见 3.3）...

    # 写缓存
    result = {"tables": tables_data, "views": views_data}
    _STRUCTURE_CACHE.set(cache_key, result)
    return result
```

#### 3.2.2 后端缓存失效机制

修改文件：[backend/app/routes/database_tool.py](backend/app/routes/database_tool.py)

在所有 DDL 操作的路由中，调用成功后清除缓存：

```python
from app.services.database_tool_service import _STRUCTURE_CACHE

# 示例：drop_table_instance 路由
@router.delete("/databases/{id}/tables/{table}")
async def drop_table(id: str, table: str, database_name: str = Query(...)):
    result = DatabaseToolService.drop_table_instance(user_id, id, table, database_name)
    # 清除缓存
    cache_key = f"{id}:{database_name}"
    _STRUCTURE_CACHE.invalidate(cache_key)
    return result
```

需加缓存失效的路由：
- `POST /databases/{id}/databases` — create database → 清除 `databases:{id}` + 前端层已有失效
- `DELETE /databases/{id}/databases/{name}` — drop database → 清除 `structure:{id}:{name}`
- `DELETE /databases/{id}/tables/{table}` — drop table → 清除 `structure:{id}:{database_name}`
- `POST /databases/{id}/tables/{table}/truncate` — truncate table → 清除 `structure:{id}:{database_name}`
- `POST /databases/{id}/tables/modify` — alter table → 清除 `structure:{id}:{database_name}`
- `DELETE /databases/{id}/all-tables` — delete all tables → 清除 `structure:{id}:{database_name}`
- `POST /databases/{id}/truncate-all-tables` — truncate all → 清除 `structure:{id}:{database_name}`
- `PUT /databases/{id}` — update config → 清除 `structure:{id}:*`（使用 `invalidate_prefix`）
- `DELETE /databases/{id}` — delete config → 清除 `structure:{id}:*`

**SQL Executor 执行 DDL 的场景**：当用户通过 SQL Console 执行 `CREATE TABLE` / `DROP TABLE` 等 DDL 时，无法自动检测并失效缓存。这是已知限制，用户需手动刷新连接树来获取最新结构。可以通过在 SQL 执行结果中检测 DDL 关键字来做启发式失效，但这增加了复杂度和误判风险，暂不纳入本轮优化。

### 3.4 SQL 查询优化（MySQL 专属）

修改文件：[backend/app/services/database_tool_service.py](backend/app/services/database_tool_service.py)

**仅适用于 MySQL/MariaDB**。将两次 `information_schema` 查询合并为一次 UNION ALL：

```python
if db_type == DatabaseType.MYSQL or db_type == DatabaseType.MARIADB:
    with engine.connect() as conn:
        sql = text("""
            SELECT TABLE_NAME, TABLE_COMMENT, 'table' AS obj_type
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = :schema AND TABLE_TYPE = 'BASE TABLE'
            UNION ALL
            SELECT TABLE_NAME, NULL, 'view' AS obj_type
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = :schema
            ORDER BY TABLE_NAME
        """)
        result = conn.execute(sql, {"schema": database_name})

        tables_data = []
        views_data = []
        for row in result:
            entry = {"name": row[0], "comment": row[1]}
            if row[2] == 'table':
                tables_data.append(entry)
            else:
                views_data.append(entry)
else:
    # 非 MySQL 数据库保持原有逻辑（SQLAlchemy inspector）
    # ... 保持不变 ...
```

**效果**：减少一次 round-trip。UNION ALL 不重复扫描，性能优于两次独立查询。

**不设置 statement_timeout**：`SET SESSION statement_timeout` 只在 PostgreSQL 中有效，MySQL 不支持。且 20s 的慢查询主要来自 `information_schema` 本身的查询效率，不是网络或连接问题。保留默认的 `read_timeout=30s` 配置即可。

**pool_pre_ping 保持现状**：已验证 `pool_pre_ping=True` 的开销 < 1ms，远小于 20s 的主查询时间，不是瓶颈根因。移除它会导致 Error 2013 风险。

## 4. 缓存失效矩阵

| 操作 | 后端 TTLCache 清除 | 前端 IndexedDB 清除 |
|------|-------------------|-------------------|
| `CREATE DATABASE` | — | `databases:{config_id}` |
| `DROP DATABASE` | `structure:{config_id}:{db_name}` | `databases:{config_id}`, `structure:{config_id}:{db_name}` |
| `DROP TABLE` | `structure:{config_id}:{db_name}` | `structure:{config_id}:{db_name}` |
| `TRUNCATE TABLE` | `structure:{config_id}:{db_name}` | `structure:{config_id}:{db_name}` |
| `ALTER TABLE` | `structure:{config_id}:{db_name}` | `structure:{config_id}:{db_name}` |
| `DELETE ALL TABLES` | `structure:{config_id}:{db_name}` | `structure:{config_id}:{db_name}` |
| `TRUNCATE ALL TABLES` | `structure:{config_id}:{db_name}` | `structure:{config_id}:{db_name}` |
| `UPDATE config` | `structure:{config_id}:*` | `configs`, `databases:{config_id}`, `structure:{config_id}:*` |
| `DELETE config` | `structure:{config_id}:*` | `configs`, `databases:{config_id}`, `structure:{config_id}:*` |

## 5. 改动文件清单

| 文件 | 改动类型 | 描述 |
|------|---------|------|
| `frontend/src/api/databaseToolApi.ts` | 修改 | In-flight dedup（pendingStructureRequests Map） |
| `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx` | 修改 | 合并两个重复 useEffect |
| `backend/app/services/database_tool_service.py` | 修改 | StructureCache 类 + TTL 缓存 + MySQL UNION ALL |
| `backend/app/routes/database_tool.py` | 修改 | DDL 路由增加缓存失效调用 |

## 6. 验收标准

### 6.1 重复请求消除
1. 清除浏览器 IndexedDB 缓存（DevTools → Application → IndexedDB → 删除 dbToolCache）
2. 访问 `http://localhost:5178/tools/database-tool`
3. 打开 DevTools → Network 面板
4. 选择一个数据库连接，确认 `structure` 接口只出现 **1 次**（不是 3 次）

### 6.2 首次请求性能
1. 保持上一步环境（IndexedDB 缓存已清除）
2. 选择另一个数据库连接
3. 确认 `structure` 接口仍然只出现 **1 次**
4. 确认 `structure` 请求时间 < 20s（首次请求仍受 MySQL information_schema 查询速度限制，目标是消除前端重复请求造成的不必要开销）

### 6.3 缓存命中性能
1. 在 6.1 后不关闭页面，再次切换回同一个数据库连接
2. 确认 `structure` 接口 **0 次**（IndexedDB 缓存命中，不发请求）
3. 如果 IndexedDB 缓存未命中（如新选择的数据库），确认请求时间 < 500ms（后端 TTLCache 命中）

### 6.4 缓存失效正确性
1. 展开连接树，查看表列表（触发缓存写入）
2. 通过 SQL Console 执行 `DROP TABLE test_table` 或 `CREATE TABLE test_new_table (...)`
3. 点击连接树的刷新按钮
4. 确认：`DROP TABLE` 后该表不再出现在列表中；`CREATE TABLE` 后新表出现在列表中

### 6.5 无回归
1. 浏览器 Console 无报错
2. 验证功能清单：
   - [ ] 展开/折叠连接树正常
   - [ ] 查看表数据正常
   - [ ] SQL 查询执行正常
   - [ ] 编辑连接配置正常
   - [ ] DDL 操作（创建/删除表）正常返回
3. 验证多数据库类型：
   - [ ] MySQL/MariaDB 的 structure 查询正常返回（使用 UNION ALL 优化路径）
   - [ ] PostgreSQL 的 structure 查询正常返回（使用 inspector 回退路径）

## 7. 已知限制

1. **SQL Executor DDL 不会自动失效缓存** — 用户通过 SQL Console 执行 DDL 后，需手动刷新连接树
2. **多 Worker 缓存不共享** — 每个 worker 独立缓存，同一结构可能被查询多次
3. **首次加载仍受 MySQL information_schema 查询速度限制** — 如果数据库有数百/数千张表，首次查询仍需数秒