# PostgreSQL 连接展开性能优化设计（方案 C）

- 日期：2026-06-25
- 状态：待评审
- 关联页面：`http://localhost:5178/tools/database-tool`

## 一、问题与根因

在数据库工具页面点击 **PostgreSQL 连接** 展开下级节点时非常慢。实测（测试账号，12 个连接）：

| 连接类型 | 展开耗时 | 返回 |
|---|---|---|
| PostgreSQL（未指定 database_name）| 2.2s ~ 5.5s | `数据库:schema` 扁平列表（10~29 项）|
| MySQL | ~0.05s | 秒回 |

连续 3 次请求同一 PG 连接均稳定 2.4s，说明**后端无缓存**。

### 根因

后端 `DatabaseToolService.get_databases_list`（`backend/app/services/database_tool_service.py:1144-1186`）在 PG 连接未指定 `database_name` 时：

1. 先连 `postgres` 系统库，查 `pg_database` 得到所有数据库名；
2. **串行遍历每个数据库**，对每个库**新建独立 engine + 建立新连接**，逐个查 `information_schema.schemata`；
3. 把结果拼成 `["db:schema", ...]` 扁平列表返回。

库/ schema 越多，串行跨网络建连次数越多，累加成秒级延迟。MySQL 仅一条 `SHOW DATABASES` 故快。

### 关键现状（决定改动量）

- 前端 `ConnectionList.tsx` 已存在 `PostgresDatabaseNode` 组件，把后端的 `db:schema` 扁平列表在前端按库分组渲染成"数据库 → schema"层级；展开某个库只是本地展开已有 schema（不再请求）。
- schema 懒加载接口 `get_schemas_list` / `GET /database-tool/databases/{id}/schemas?database_name=` **已存在**（单库查询、快），但当前这条展开路径未使用它。
- 前端 `getDatabasesList` / `getSchemasList` 已带 IndexedDB 缓存 + in-flight 去重。

因此方案 C 的改动是**把已有但未串联的能力接起来**，而非新建。

## 二、目标

1. 点击 PG 连接展开 → 仅列库名，耗时降到 < 300ms。
2. 点击某个数据库展开 → 懒加载该库 schema，带缓存。
3. 后端对列库 / 列 schema 结果加 5 分钟 TTL 缓存，避免重复连库。
4. 搜索（跨库搜 schema）仍可用：用并行查询替代串行。
5. 右键"刷新"可强制跳过缓存重查。

## 三、架构与数据流

### 修复后数据流

```
点连接   → GET /databases/{id}/databases            → 只返回库名列表 ["db1","db2",...]  (~50ms, 带缓存)
点某个库 → GET /databases/{id}/schemas?database_name=X → 返回该库 schema ["public",...]   (~100ms, 带缓存)
点 schema→ GET /databases/{id}/structure?...          → 返回表/视图（已有，不改）
搜索     → GET /databases/{id}/all-schemas（新增/并行）→ 跨库 schema，线程池并行 + 缓存
```

### 返回格式变更（破坏性，需前后端同步）

`GET /database-tool/databases/{id}/databases`（PG 无 database_name 时）：

- 旧：`["mydb:public", "mydb:app", "other:public", ...]`
- 新：`["mydb", "other", ...]`（与 MySQL 行为一致）

## 四、后端改动

文件：`backend/app/services/database_tool_service.py`、`backend/app/routes/database_tool.py`，新增 `backend/app/utils/ttl_cache.py`。

### 1. 轻量 TTL 缓存工具（新增 `app/utils/ttl_cache.py`）

项目无 `cachetools` 依赖，避免引入新包。实现一个进程内、线程安全的 TTL 缓存：

- `TTLCache(ttl_seconds: int)`，内部 `dict[key] -> (value, expire_at)` + `threading.Lock`。
- 方法：`get(key)`（过期返回 None 并清除）、`set(key, value)`、`invalidate(key)`、`invalidate_prefix(prefix)`（按连接维度清理）。
- 默认 TTL **300 秒（5 分钟）**，从常量配置。

### 2. `get_databases_list` 瘦身

PG 无 `database_name` 分支：**只查 `pg_database`** 返回库名列表（一条查询），删除"遍历每库查 schema"逻辑。MySQL/SQLServer/SQLite 分支不变。

- 结果进 TTL 缓存，key=`databases:{config_id}`。
- 加可选 `skip_cache: bool` 透传，支持强制刷新。

### 3. `get_schemas_list` 接入缓存

已存在，补充：结果进 TTL 缓存，key=`schemas:{config_id}:{database_name}`，同样支持 `skip_cache`。

### 4. 搜索用并行全量接口（新增）

新增 `get_all_schemas(user_id, config_id, skip_cache=False) -> dict[str, list[str]]`：

- 查 `pg_database` 得库名，用 `ThreadPoolExecutor`（限制并发，如 max_workers=5）**并行**查各库 schema。
- 返回 `{db: [schema...]}`，进缓存 key=`all_schemas:{config_id}`。
- 路由：`GET /database-tool/databases/{id}/all-schemas`。
- 仅搜索场景调用，非默认展开路径。

### 5. 缓存失效

写操作（建库/删库、改 schema/表结构等已有端点）成功后，调用 `invalidate_prefix(f"...:{config_id}")` 清理该连接相关缓存。右键刷新端点透传 `skip_cache=True`。

## 五、前端改动

文件：`frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`、`frontend/src/api/databaseToolApi.ts`。

### 1. PG 无 database_name 的渲染（约 600-636 行）

不再 `split(':')` 分组。`getDatabasesList` 现在直接返回库名数组，遍历渲染 `PostgresDatabaseNode`，`schemaNames` 改为**懒加载**（初始不传或传空）。

### 2. `PostgresDatabaseNode` 改为懒加载 schema（约 1458-1513 行）

- 展开某个库时（`setIsExpanded(true)` 且未加载），调 `api.getSchemasList(configId, dbName)` 拉该库 schema，存本地 state，再渲染 `SchemaNode`。
- 复用现有 `getSchemasList` 的 IndexedDB 缓存 + in-flight 去重。
- 加 loading 态与错误处理（toast + console.error）。

### 3. 搜索场景

搜索激活时，连接节点改为调用 `getAllSchemas(configId)`（新增 API 封装，命中 `/all-schemas`）一次性并行取全量，再按库分组喂给 `PostgresDatabaseNode`，保持现有"搜索自动展开匹配项"行为。

### 4. API 封装（`databaseToolApi.ts`）

- `getDatabasesList` 返回类型不变（`string[]`），语义从"db:schema"变为"db 名"。
- 新增 `getAllSchemas(id): Promise<Record<string,string[]>>`，带 IndexedDB 缓存 + in-flight 去重，key=`all_schemas:{id}`。

## 六、错误处理

- 后端列库/列 schema 失败：保持现有"抛异常 → 路由转 500/400"，前端 toast 提示并 `console.error`，不静默吞错。
- 密码解密失败（实测部分 MySQL 连接出现 `InvalidToken`）：维持现有报错文案，不在本次范围内修复。
- 并行查询中单库失败：记 `logger.warning`，跳过该库，不影响其他库（沿用现有 `try/except` 容错）。

## 七、测试计划

### 后端单测
- `get_databases_list`（PG 无 database_name）只执行一次 `pg_database` 查询，不再遍历各库（mock engine 校验调用次数）。
- `TTLCache`：命中、过期、`invalidate_prefix` 行为。
- `get_all_schemas`：并行返回结构正确，单库异常被隔离。

### 浏览器实测（强制要求）
1. 登录后打开 `/tools/database-tool`。
2. 展开 PG 连接 `6f051a47`（原 5.5s）→ 耗时 < 300ms，列出库名。
3. 展开某个库 → 懒加载 schema，正常渲染。
4. 展开 schema → 表/视图正常。
5. 搜索一个 schema 名 → 跨库匹配仍能展开命中。
6. 右键刷新 → 强制重查生效。
7. Console 无报错；MySQL 连接行为不回归。

## 八、风险

- **交互变更**：PG 连接展开后，原来一次性铺开所有 schema；现在多一层"数据库"节点（已与用户确认接受）。这是行业惯例（Navicat/DBeaver）且是提速根本。
- **返回格式破坏性变更**：`getDatabasesList` 的 PG 语义改变，前后端必须同时上线；前端旧 IndexedDB 缓存中的 `db:schema` 数据需失效（提升缓存版本号或变更 cacheKey 命名）。
- **缓存陈旧**：5 分钟内库/schema 变动不可见，靠右键刷新与写操作失效兜底。
