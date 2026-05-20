# PostgreSQL 多 Schema 支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 PostgreSQL 数据库工具增加多 schema 层级浏览和操作支持，同时不影响 MySQL/SQLite 等其他数据库类型的正常处理。

**Architecture:** 复用现有 `get_databases_list` API，让 PostgreSQL 返回 `database:schema` 格式的组合字符串；前端根据 `db_type` 判断并在 PostgreSQL 连接的 database 节点和 tables 之间渲染 Schema 节点层级。所有数据库操作函数新增可选 `schema_name` 参数，PostgreSQL 类型根据 schema 过滤查询。

**Tech Stack:** Python FastAPI, SQLAlchemy, React TypeScript, IndexedDB Cache

---

## 文件概览

### 新建文件
- `frontend/src/components/Tools/DatabaseTool/components/SchemaNode.tsx` — Schema 节点组件，复用 DatabaseStructureNode 的样式和交互模式

### 修改文件（后端）
- `backend/app/routes/database_tool.py:179-201` — 修改 `get_databases_list` 和 `get_database_structure` 路由，增加 `schema_name` 参数
- `backend/app/services/database_tool_service.py:1029-1158` — 修改核心服务方法，支持 schema 层级
- `backend/app/models/database_tool_models.py` — 可选：增加 schema 相关模型字段（如需要）

### 修改文件（前端）
- `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` — 核心改动，增加 SchemaNode 渲染逻辑
- `frontend/src/api/databaseToolApi.ts` — API 调用增加 schema_name 参数
- `frontend/src/types/databaseTool.ts` — DisplayPreferences 增加 visible_schemas 字段

---

### Task 1: 后端 — 修改 `get_databases_list` 支持 PostgreSQL Schema 列表

**Files:**
- Modify: `backend/app/services/database_tool_service.py:1029-1077`

- [ ] **Step 1: 修改 `get_databases_list` 函数，为 PostgreSQL 返回 schema 组合**

当前代码（line 1059-1065）PostgreSQL 只返回 database 列表。需要改为：

```python
# 修改 backend/app/services/database_tool_service.py:1029-1077 中的 PostgreSQL 分支

# 替换原有的:
# elif db_type == DatabaseType.POSTGRESQL:
#     result = conn.execute(
#         text(
#             "SELECT datname FROM pg_database WHERE datistemplate = false"
#         )
#     )
#     databases = [row[0] for row in result]

# 改为:
elif db_type == DatabaseType.POSTGRESQL:
    # 如果配置中指定了 database_name，则返回该数据库下的 schema 列表
    # 否则返回所有数据库的所有 schema（格式: "database:schema"）
    target_db = config_row.get("database_name")
    if target_db:
        # 连接指定数据库，查询所有 schema
        result = conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
            )
        )
        databases = [row[0] for row in result]
    else:
        # 查询所有非模板数据库
        db_result = conn.execute(
            text("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
        )
        db_names = [row[0] for row in db_result]
        # 对每个数据库查询其 schema
        for db_name in db_names:
            try:
                # 临时连接到该数据库查询 schema
                schema_config = config_dict.copy()
                schema_config["database_name"] = db_name
                temp_key = f"{config_id}:_temp_{db_name}"
                temp_engine = DBConnectionManager.get_engine(temp_key, schema_config)
                with temp_engine.connect() as db_conn:
                    schema_result = db_conn.execute(
                        text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
                    )
                    for schema_row in schema_result:
                        databases.append(f"{db_name}:{schema_row[0]}")
                temp_engine.dispose()
            except Exception as e:
                logger.warning(f"Failed to get schemas for {db_name}: {e}")
```

- [ ] **Step 2: 验证后端改动语法正确**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m py_compile app/services/database_tool_service.py`
Expected: 无输出（编译成功）

### Task 2: 后端 — 修改 `get_database_structure` 支持 schema_name 参数

**Files:**
- Modify: `backend/app/services/database_tool_service.py:1080-1158`
- Modify: `backend/app/routes/database_tool.py:191-201`

- [ ] **Step 1: 修改路由增加 `schema_name` query 参数**

```python
# 修改 backend/app/routes/database_tool.py:191-201

@router.get("/databases/{id}/structure", response_model=Dict[str, List[Dict[str, Any]]])
async def get_database_structure(
    id: str = PathParam(..., description="Configuration ID"),
    database_name: str = Query(..., description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL only)"),
    user_id: str = Depends(get_current_user_id),
):
    """Get structure (tables, views) for a specific database/schema"""
    try:
        return DatabaseToolService.get_database_structure(user_id, id, database_name, schema_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: 修改 `get_database_structure` 方法签名和 PostgreSQL 查询逻辑**

```python
# 修改 backend/app/services/database_tool_service.py:1080-1158

@staticmethod
def get_database_structure(
    user_id: str, config_id: str, database_name: str, schema_name: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    # 如果 database_name 包含 "database:schema" 格式，解析它
    actual_db_name = database_name
    actual_schema_name = schema_name
    if ":" in database_name:
        parts = database_name.split(":", 1)
        actual_db_name = parts[0]
        actual_schema_name = parts[1]

    cache_key = f"{config_id}:{actual_db_name}:{actual_schema_name}"

    # 1. 查后端缓存
    cached = _STRUCTURE_CACHE.get(cache_key)
    if cached:
        return cached

    config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
    if not config_row:
        raise ValueError("Configuration not found")

    try:
        password = EncryptionUtils.decrypt(config_row["password_encrypted"])
    except Exception:
        raise ValueError("Failed to decrypt password")

    config_dict = {
        "db_type": config_row["db_type"],
        "host": config_row["host"],
        "port": config_row["port"],
        "database_name": actual_db_name,
        "username": config_row["username"],
        "password": password,
        "charset": config_row["charset"],
    }

    temp_config_id = f"{config_id}:{actual_db_name}"

    try:
        engine = DBConnectionManager.get_engine(temp_config_id, config_dict)
        db_type = config_row["db_type"]

        tables_data = []
        views_data = []

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
                result = conn.execute(sql, {"schema": actual_db_name})
                for row in result:
                    entry = {"name": row[0], "comment": row[1]}
                    if row[2] == 'table':
                        tables_data.append(entry)
                    else:
                        views_data.append(entry)

        elif db_type == DatabaseType.POSTGRESQL:
            pg_schema = actual_schema_name or "public"
            with engine.connect() as conn:
                # 查询表（包含注释）
                sql_tables = text("""
                    SELECT c.relname AS table_name, 
                           obj_description(c.oid, 'pg_class') AS table_comment
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relkind = 'r'  -- regular table
                    AND n.nspname = :schema
                    ORDER BY c.relname
                """)
                result = conn.execute(sql_tables, {"schema": pg_schema})
                for row in result:
                    tables_data.append({"name": row[0], "comment": row[1]})

                # 查询视图
                sql_views = text("""
                    SELECT c.relname AS view_name
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relkind = 'v'  -- view
                    AND n.nspname = :schema
                    ORDER BY c.relname
                """)
                result = conn.execute(sql_views, {"schema": pg_schema})
                for row in result:
                    views_data.append({"name": row[0], "comment": None})

        else:
            # 其他数据库类型保持原有逻辑
            inspector = inspect(engine)
            for name in inspector.get_table_names():
                try:
                    comment = inspector.get_table_comment(name).get("text")
                except:
                    comment = None
                tables_data.append({"name": name, "comment": comment})

            for name in inspector.get_view_names():
                views_data.append({"name": name, "comment": None})

        result = {"tables": tables_data, "views": views_data}
        _STRUCTURE_CACHE.set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Failed to get database structure: {e}")
        raise e
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m py_compile app/services/database_tool_service.py && python -m py_compile app/routes/database_tool.py`
Expected: 无输出

- [ ] **Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/services/database_tool_service.py backend/app/routes/database_tool.py
git commit -m "feat: 后端支持 PostgreSQL schema 层级查询

- get_databases_list 为 PostgreSQL 返回 database:schema 格式列表
- get_database_structure 支持 schema_name 参数，PostgreSQL 使用 pg_class 查询
- 路由增加可选 schema_name query 参数
- 其他数据库类型保持原有逻辑不变"
```

### Task 3: 前端 — 更新 API 层和类型定义

**Files:**
- Modify: `frontend/src/api/databaseToolApi.ts:133-144` — `getDatabasesList` 增加返回类型说明注释
- Modify: `frontend/src/api/databaseToolApi.ts:194-222` — `getDatabaseStructure` 增加 `schemaName` 参数
- Modify: `frontend/src/types/databaseTool.ts:269-276` — `DisplayPreferences` 增加 `visible_schemas` 字段

- [ ] **Step 1: 修改 `getDatabaseStructure` API 函数增加 schemaName 参数**

```typescript
// 修改 frontend/src/api/databaseToolApi.ts:194-222

export async function getDatabaseStructure(id: string, databaseName: string, schemaName?: string): Promise<DatabaseStructure> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const cacheKey = `structure:${id}:${databaseName}${schemaName ? ':' + schemaName : ''}`;

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
      const response = await fetch(`${BASE_URL}/databases/${id}/structure?database_name=${encodeURIComponent(databaseName)}${schemaParam}`, {
        headers: getAuthHeaders()
      });
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

- [ ] **Step 2: 更新类型定义**

```typescript
// 修改 frontend/src/types/databaseTool.ts:269-276

export interface DisplayPreferences {
  visible_connections: string[] | null;
  visible_databases: Record<string, string[]>;
  visible_schemas?: Record<string, string[]>; // configId -> schema[] 过滤（PostgreSQL）
  updated_at?: string;
}
```

- [ ] **Step 3: 更新 invalidate 逻辑 — 结构缓存 key 变更**

在 `updateDatabase` 函数中（line 97-101），缓存清除需要兼容新的 key 格式：

```typescript
// 修改 frontend/src/api/databaseToolApi.ts:97-101 中的 invalidatePrefix
// 原: await DBCache.invalidatePrefix(`structure:${id}`);
// 改为（不需要改，因为 prefix 匹配仍然有效）:
await DBCache.invalidatePrefix(`structure:${id}`);
```

实际上不需要修改，因为 `structure:${id}:` 前缀仍然能匹配所有子 key。

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 可能有类型错误（后续任务会修复），但 databaseToolApi.ts 和 databaseTool.ts 本身不应有错误

- [ ] **Step 5: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/api/databaseToolApi.ts frontend/src/types/databaseTool.ts
git commit -m "feat: 前端 API 层增加 schema_name 参数支持

- getDatabaseStructure 增加可选 schemaName 参数
- DisplayPreferences 增加 visible_schemas 字段
- 缓存 key 兼容 schema 层级"
```

### Task 4: 前端 — 新增 SchemaNode 组件

**Files:**
- Create: `frontend/src/components/Tools/DatabaseTool/components/SchemaNode.tsx`

- [ ] **Step 1: 创建 SchemaNode 组件**

```tsx
// Create frontend/src/components/Tools/DatabaseTool/components/SchemaNode.tsx

import React, { useState, useEffect } from 'react';
import { DatabaseStructure, TableItem } from '../../../../types/databaseTool';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseTool';

interface SchemaNodeProps {
  configId: string;
  dbName: string;
  schemaName: string;
  onSelectTable: (tableName: string) => void;
  onSelectSchema: () => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string, schemaName?: string) => void;
  searchTerm: string;
  activeSchemaName?: string;
}

const SchemaNode: React.FC<SchemaNodeProps> = ({ configId, dbName, schemaName, onSelectTable, onSelectSchema, onOpenSqlConsole, searchTerm, activeSchemaName }) => {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [structure, setStructure] = useState<DatabaseStructure | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStructure = async () => {
    setLoading(true);
    try {
      const data = await api.getDatabaseStructure(configId, dbName, schemaName);
      setStructure(data);
      return data;
    } catch (err) {
      console.error("Failed to load schema structure", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (searchTerm && !structure && !loading) {
      fetchStructure().then(() => setIsExpanded(true));
    }
  }, [searchTerm]);

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectSchema();

    const nextState = !isExpanded;
    setIsExpanded(nextState);

    if (nextState && !structure) {
      await fetchStructure();
    }
  };

  const handleTableClick = (table: string) => {
    onSelectSchema();
    onSelectTable(table);
  };

  const isActive = activeSchemaName === schemaName;

  return (
    <div className="text-sm">
      <div
        className={`flex items-center space-x-2 py-1 px-2 rounded cursor-pointer ${
          isActive ? 'bg-blue-600/20 text-blue-300' : 'text-slate-300 hover:bg-slate-700/50'
        }`}
        onClick={handleToggle}
      >
        <span className="w-4 h-4 flex items-center justify-center">
          {loading ? (
            <i className="fas fa-spinner fa-spin text-[10px]"></i>
          ) : (
            <i className={`fas fa-chevron-right text-[10px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}></i>
          )}
        </span>
        <i className="fas fa-folder text-cyan-500/80 text-xs"></i>
        <span className="truncate">{schemaName}</span>
      </div>

      {isExpanded && structure && (
        <div className="ml-4 pl-2 border-l border-slate-700 mt-1 space-y-1">
          {/* Tables */}
          {structure.tables.length > 0 && (
            <div className="py-1 px-2">
              <div className="flex items-center space-x-2 text-slate-400 text-xs">
                <i className="fas fa-table text-blue-400"></i>
                <span>Tables</span>
                <span className="text-[10px] bg-slate-700 px-1 rounded-full">{structure.tables.length}</span>
              </div>
              <div className="ml-4 mt-1 space-y-0.5">
                {structure.tables.map((table: TableItem) => (
                  <div
                    key={table.name}
                    className="flex items-center space-x-2 py-0.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300 text-xs"
                    onClick={() => handleTableClick(table.name)}
                    title={table.comment || undefined}
                  >
                    <i className="fas fa-table text-slate-500 text-[10px]"></i>
                    <span className="truncate">{table.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Views */}
          {structure.views.length > 0 && (
            <div className="py-1 px-2">
              <div className="flex items-center space-x-2 text-slate-400 text-xs">
                <i className="fas fa-eye text-purple-400"></i>
                <span>Views</span>
                <span className="text-[10px] bg-slate-700 px-1 rounded-full">{structure.views.length}</span>
              </div>
              <div className="ml-4 mt-1 space-y-0.5">
                {structure.views.map((view: TableItem) => (
                  <div
                    key={view.name}
                    className="flex items-center space-x-2 py-0.5 px-2 hover:bg-slate-700/50 rounded cursor-pointer text-slate-300 text-xs"
                    onClick={() => handleTableClick(view.name)}
                  >
                    <i className="fas fa-eye text-slate-500 text-[10px]"></i>
                    <span className="truncate">{view.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {structure.tables.length === 0 && structure.views.length === 0 && (
            <div className="text-xs text-slate-500 py-1 px-2 italic">No tables or views in this schema</div>
          )}
        </div>
      )}
    </div>
  );
};

export default SchemaNode;
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep SchemaNode`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/components/SchemaNode.tsx
git commit -m "feat: 新增 SchemaNode 组件用于 PostgreSQL schema 层级展示

- 支持展开/收起 schema 节点
- 显示 schema 下的 Tables 和 Views 列表
- 与 DatabaseStructureNode 保持一致的视觉风格
- 支持搜索高亮和活跃状态标识"
```

### Task 5: 前端 — 修改 ConnectionList 集成 Schema 层级

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` — 核心集成

这是最大的改动。需要在 `ConnectionNode` 中判断 PostgreSQL 类型，并在 database 节点下渲染 SchemaNode。

- [ ] **Step 1: 在 ConnectionNode 中增加 PostgreSQL schema 解析逻辑**

在 `ConnectionNode` 组件中（约 line 244-627），修改 `databases` 状态的使用逻辑。

首先在 `fetchDatabases` 之后，对 PostgreSQL 类型做特殊处理：

```tsx
// 在 ConnectionNode 组件中，约 line 340-353，修改 fetchDatabases:

const fetchDatabases = async () => {
  setLoading(true);
  try {
    const dbs = await api.getDatabasesList(config.id);
    
    // PostgreSQL 特殊处理：解析 "database:schema" 格式
    let processedDbs = dbs;
    if (config.db_type === 'postgresql' && !config.database_name) {
      // 未指定 database_name 时，返回的是 "database:schema" 格式
      // 保持原样，在渲染时解析
      processedDbs = dbs;
    } else if (config.db_type === 'postgresql' && config.database_name) {
      // 已指定 database_name 时，返回的是 schema 列表
      processedDbs = dbs;
    }
    
    setDatabases(processedDbs);
    setLoaded(true);
    return processedDbs;
  } catch (err) {
    console.error("Failed to load databases", err);
    return [];
  } finally {
    setLoading(false);
  }
};
```

- [ ] **Step 2: 修改数据库列表渲染，PostgreSQL 显示 Schema 层级**

在 `ConnectionNode` 的渲染部分（约 line 553-599），修改数据库列表渲染：

找到这段代码：
```tsx
{filteredDatabases.map(db => (
  <DatabaseStructureNode
    key={db}
    configId={config.id}
    dbName={db}
    ...
  />
))}
```

替换为（PostgreSQL 使用 SchemaNode，其他数据库使用 DatabaseStructureNode）：

```tsx
{config.db_type === 'postgresql' ? (
  // PostgreSQL: 渲染 Schema 层级
  filteredDatabases.map(db => {
    // 解析 "database:schema" 格式
    const parts = db.includes(':') ? db.split(':', 1) : [config.database_name || db, db];
    const pgDbName = parts[0];
    const schemaName = parts[1] || 'public';

    return (
      <SchemaNode
        key={db}
        configId={config.id}
        dbName={pgDbName}
        schemaName={schemaName}
        onSelectTable={(table) => onSelectTable(config.id, pgDbName, table)}
        onSelectSchema={() => onSelectDatabase(config.id, pgDbName)}
        onOpenSqlConsole={onOpenSqlConsole}
        searchTerm={searchTerm}
        activeSchemaName={activeDatabaseName}
      />
    );
  })
) : (
  // 其他数据库: 保持原有逻辑
  filteredDatabases.map(db => (
    <DatabaseStructureNode
      key={db}
      configId={config.id}
      dbName={db}
      onSelectTable={(table) => onSelectTable(config.id, db, table)}
      onSelectDatabase={() => onSelectDatabase(config.id, db)}
      onRefreshDatabases={fetchDatabases}
      onOpenSqlConsole={onOpenSqlConsole}
      onOpenBackup={(dbName, tables) => onOpenBackup(config.id, dbName, tables)}
      onOpenBackupHistory={(dbName) => onOpenBackupHistory(config.id, dbName)}
      searchTerm={searchTerm}
      activeDatabaseName={activeDatabaseName}
    />
  ))
)}
```

- [ ] **Step 3: 添加 SchemaNode import**

在文件顶部 import 中添加：

```typescript
import SchemaNode from './SchemaNode';
```

放在其他组件 import 之后：

```typescript
import DatabaseFilterDialog from './DatabaseFilterDialog';
// ... 其他 import
import SchemaNode from './SchemaNode';
```

- [ ] **Step 4: 修改 `ConnectionNodeProps` 接口**

`DatabaseStructureNode` 的 `onOpenSqlConsole` 可能需要传递 schemaName。但为了最小改动，我们先不修改签名，让 SQL 执行时用户在 SQL 中使用 `schema.table` 格式即可。

不需要修改 props 接口。

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 可能有一些既有警告，但不应该有新的错误

- [ ] **Step 6: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx
git commit -m "feat: ConnectionList 集成 PostgreSQL Schema 层级

- PostgreSQL 连接下，database 节点之间渲染 Schema 层级
- 解析 getDatabasesList 返回的 database:schema 格式
- 其他数据库类型保持原有树形结构不变
- SchemaNode 复用 DatabaseStructureNode 的交互模式"
```

### Task 6: 后端 — 修改核心操作函数支持 schema_name 参数

需要修改以下后端服务方法，为 PostgreSQL 类型增加 schema_name 支持：
- `get_table_schema` (line 1186)
- `get_table_detail` (line 2836)
- `get_table_row_count` (line 2946)
- `query_table_data` (line 1252)
- `table_preview` (line 2110)
- `search_tables` (line 1553)
- `auto_complete` (line 2213)

每个方法的改动模式相同：增加 `schema_name: Optional[str] = None` 参数，PostgreSQL 类型在 SQL 查询中使用 `schema.table` 格式。

**Files:**
- Modify: `backend/app/services/database_tool_service.py` — 多个方法
- Modify: `backend/app/routes/database_tool.py` — 对应路由增加参数

- [ ] **Step 1: 修改 `get_table_schema` 方法**

```python
# 修改 backend/app/services/database_tool_service.py:1186

@staticmethod
def get_table_schema(
    user_id: str,
    config_id: str,
    table_name: str,
    database_name: Optional[str] = None,
    schema_name: Optional[str] = None,
) -> TableSchema:
```

在方法内部，获取 engine 后，PostgreSQL 类型需要使用 schema_name 进行查询过滤。找到获取 columns、indexes、foreign_keys 的部分，PostgreSQL 需要加上 schema 限定。

在 inspector 调用处，SQLAlchemy 的 inspector 对 PostgreSQL 会自动处理 schema，但需要在连接时指定 `options` 或使用 `schema` 参数。对于 `get_columns`、`get_indexes` 等方法，SQLAlchemy inspector 默认查询当前连接数据库的 `public` schema。我们需要通过 SQL 查询替代 inspector 调用来支持自定义 schema。

实际上，SQLAlchemy 的 `inspect(engine).get_columns(table_name)` 对 PostgreSQL 默认使用 `public` schema。要支持其他 schema，最简单的方式是在表名中使用 schema 限定（如 `"auth"."users"`），SQLAlchemy 会正确解析。

因此改动为：对 PostgreSQL，在表名前加 schema 限定：

```python
# 在 get_table_schema 方法中，engine 获取后：
qualified_table_name = table_name
if db_type == DatabaseType.POSTGRESQL and schema_name:
    qualified_table_name = f'"{schema_name}"."{table_name}"'

# 然后使用 qualified_table_name 替换所有 inspector 调用中的 table_name
inspector = inspect(engine)
existing_columns = inspector.get_columns(qualified_table_name)
# ... 等等
```

- [ ] **Step 2: 修改路由传递 schema_name**

```python
# 修改 backend/app/routes/database_tool.py:425-438

@router.get("/databases/{id}/tables/{table}/schema", response_model=TableSchema)
async def get_table_schema(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    database_name: Optional[str] = Query(None, description="Database Name"),
    schema_name: Optional[str] = Query(None, description="Schema Name (PostgreSQL only)"),
    user_id: str = Depends(get_current_user_id),
):
    """Get table schema structure"""
    try:
        return DatabaseToolService.get_table_schema(user_id, id, table, database_name, schema_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 同样模式修改其他方法**

对以下方法应用相同的改动模式（增加 `schema_name` 参数 + PostgreSQL 限定查询）：

```python
# get_table_detail 增加 schema_name: Optional[str] = None
# get_table_row_count 增加 schema_name: Optional[str] = None  
# table_preview 的 TablePreviewRequest 模型增加 schema_name 字段
# query_table_data 的 request body 解析增加 schema_name
# search_tables 的 PostgreSQL 分支增加 schema 过滤
# auto_complete 的 PostgreSQL 分支增加 schema 列表
```

每个方法的具体改动：
1. 函数签名增加 `schema_name: Optional[str] = None`
2. 对 PostgreSQL，使用 `f'"{schema_name}"."{table_name}"'` 作为限定表名
3. 路由端点增加 `schema_name: Optional[str] = Query(None)` 参数

- [ ] **Step 4: 修改 `TablePreviewRequest` 模型**

```python
# 修改 backend/app/models/database_tool_models.py:239-245

class TablePreviewRequest(BaseModel):
    database_name: str
    table_name: str
    schema_name: Optional[str] = None  # PostgreSQL schema 支持
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=1000)
    order_by: Optional[str] = None
    filter_conditions: Optional[Dict[str, Any]] = None
```

- [ ] **Step 5: 修改 `auto_complete` 的 PostgreSQL 查询**

```python
# 修改 auto_complete 中 PostgreSQL 部分（line 2289-2297）

elif db_type == DatabaseType.POSTGRESQL:
    # 获取所有 schema 的表
    schema_filter = ""
    if request.schema_name:  # 需要在 AutoCompleteRequest 中增加此字段
        schema_filter = f"AND schemaname = '{request.schema_name}'"
    else:
        # 默认包含 public 和常见用户 schema
        schema_filter = "AND schemaname NOT IN ('pg_catalog', 'information_schema')"
    
    result = conn.execute(
        text(f"""
            SELECT tablename, ''
            FROM pg_tables
            WHERE 1=1 {schema_filter}
            LIMIT 100
        """)
    )
```

需要在 `AutoCompleteRequest` 模型中增加 `schema_name` 字段：

```python
# 修改 backend/app/models/database_tool_models.py:260-263

class AutoCompleteRequest(BaseModel):
    query: str
    database_name: Optional[str] = None
    schema_name: Optional[str] = None  # PostgreSQL schema 支持
    position: int = Field(0, description="光标位置")
```

- [ ] **Step 6: 验证编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m py_compile app/services/database_tool_service.py && python -m py_compile app/routes/database_tool.py && python -m py_compile app/models/database_tool_models.py`
Expected: 无输出

- [ ] **Step 7: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/services/database_tool_service.py backend/app/routes/database_tool.py backend/app/models/database_tool_models.py
git commit -m "feat: 后端核心操作函数增加 schema_name 支持

- get_table_schema, get_table_detail, get_table_row_count 增加 schema_name 参数
- table_preview, auto_complete, search_tables 支持 PostgreSQL schema 过滤
- TablePreviewRequest 和 AutoCompleteRequest 模型增加 schema_name 字段
- PostgreSQL 使用 schema.table 限定格式进行查询
- 其他数据库类型不受影响"
```

### Task 7: 前端 — 更新 TableDataViewer 和 SQL 执行支持 schema

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx` — 传递 schema_name
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx` — handleSelectTable 传递 schemaName
- Modify: `frontend/src/api/databaseToolApi.ts` — queryTableData 等函数支持 schema_name

- [ ] **Step 1: 修改 DatabaseTool.tsx 的 handleSelectTable**

```tsx
// 修改 frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx:62-78

const handleSelectTable = (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => {
  const tabId = `table-${configId}-${databaseName || ''}-${schemaName || ''}-${tableName}`;
  
  const existingTab = tabs.find(t => t.id === tabId);
  if (existingTab) {
    setActiveTabId(tabId);
  } else {
    const newTab: Tab = {
      id: tabId,
      type: 'table',
      title: tableName,
      data: { configId, databaseName, tableName, schemaName }
    };
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
  }
};
```

同时修改 Tab 接口：

```tsx
// 修改 Tab 接口的 data 类型
data?: {
  configId: string;
  databaseName?: string;
  tableName: string;
  schemaName?: string;  // 新增
};
```

- [ ] **Step 2: 修改 TableDataViewer 组件接收和使用 schemaName**

```tsx
// 修改 TableDataViewer 组件的 props 和使用
interface TableDataViewerProps {
  configId: string;
  databaseName?: string;
  tableName: string;
  schemaName?: string;  // 新增
}

// 在调用 API 时使用 schemaName
const data = await api.queryTableData(configId, tableName, {
  database_name: databaseName,
  schema_name: schemaName,
  page: currentPage,
  page_size: pageSize,
});
```

- [ ] **Step 3: 修改 DatabaseTool.tsx 中 TableDataViewer 的渲染**

```tsx
// 修改 DatabaseTool.tsx:233-239

tab.data && (
  <TableDataViewer 
    configId={tab.data.configId}
    databaseName={tab.data.databaseName}
    tableName={tab.data.tableName}
    schemaName={tab.data.schemaName}
  />
)
```

- [ ] **Step 4: 修改 API 层传递 schema_name**

```typescript
// 修改 frontend/src/api/databaseToolApi.ts:271-288

export async function queryTableData(
  id: string, 
  table: string, 
  params: { 
    database_name?: string;
    schema_name?: string;  // 新增
    where?: string; 
    order_by?: string; 
    page?: number; 
    page_size?: number 
  }
): Promise<SQLExecutionResult> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${table}/data`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(params)
  });
  return handleResponse<SQLExecutionResult>(response);
}
```

- [ ] **Step 5: 修改 getTableDetail 和 getTableRowCount API 传递 schema_name**

```typescript
// 修改 frontend/src/api/databaseToolApi.ts:401-411

export async function getTableDetail(
  id: string,
  table: string,
  databaseName: string,
  schemaName?: string  // 新增
): Promise<TableDetailResponse> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/detail?database_name=${encodeURIComponent(databaseName)}${schemaParam}`,
    { headers: getAuthHeaders() }
  );
  return handleResponse<TableDetailResponse>(response);
}

// 修改 getTableRowCount
export async function getTableRowCount(
  id: string,
  table: string,
  databaseName: string,
  schemaName?: string  // 新增
): Promise<{ table_name: string; row_count: number }> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/row-count?database_name=${encodeURIComponent(databaseName)}${schemaParam}`,
    { headers: getAuthHeaders() }
  );
  return handleResponse<{ table_name: string; row_count: number }>(response);
}
```

- [ ] **Step 6: 修改 dropTableInstance 和 truncateTableInstance 传递 schema_name**

```typescript
// 修改 frontend/src/api/databaseToolApi.ts:170-189

export async function dropTableInstance(id: string, table: string, databaseName: string, schemaName?: string): Promise<boolean> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}?database_name=${encodeURIComponent(databaseName)}${schemaParam}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}${schemaName ? ':' + schemaName : ''}`);
  return result;
}

export async function truncateTableInstance(id: string, table: string, databaseName: string, schemaName?: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/truncate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName, schema_name: schemaName })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}${schemaName ? ':' + schemaName : ''}`);
  return result;
}
```

- [ ] **Step 7: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无新错误

- [ ] **Step 8: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx frontend/src/api/databaseToolApi.ts
git commit -m "feat: 前端 TableDataViewer 和 API 层传递 schema_name

- handleSelectTable 支持 schemaName 参数
- TableDataViewer 组件接受并传递 schemaName
- queryTableData, getTableDetail, getTableRowCount 增加 schema_name 参数
- dropTableInstance, truncateTableInstance 支持 schema 层级缓存失效"
```

### Task 8: 修改 ConnectionList 中的表操作传递 schema_name

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` — FolderNode 中的各种操作

- [ ] **Step 1: 修改 FolderNode 接受和传递 schemaName**

FolderNode 已经接受 `configId`, `dbName` 等 props。需要增加 `schemaName` prop：

```tsx
// 修改 FolderNodeProps 接口（约 line 973-988）
interface FolderNodeProps {
  // ... existing props
  schemaName?: string;  // 新增
  // ...
}
```

在 FolderNode 的所有 API 调用中传递 schemaName：
- `api.getTableDetail(configId, tableName, dbName, schemaName)`
- `api.getTableDDL(configId, tableName, dbName)` — DDL 暂不需要 schema
- `api.truncateTableInstance(configId, item.name, dbName, schemaName)`
- `api.dropTableInstance(configId, item.name, dbName, schemaName)`

- [ ] **Step 2: 修改 SchemaNode 中 Tables/Views 的 Folder 渲染**

在 SchemaNode 组件中，将 Tables 和 Views 渲染改为使用 ConnectionList 中已有的 FolderNode，或者复用其渲染逻辑。

实际上，SchemaNode 当前内联了 table/view 列表的渲染。为了保持一致性（右键菜单、DDL 对话框、修改结构对话框等），应该改为使用 FolderNode。

修改 SchemaNode，使其使用 FolderNode 组件：

```tsx
// 修改 SchemaNode.tsx，引入并使用 FolderNode
import FolderNode from './ConnectionList'; // 不行，FolderNode 不是 export

// 更好的方式：将 FolderNode 抽取为独立文件
```

实际上，FolderNode 定义在 ConnectionList.tsx 文件中。为了复用，有两个选择：
1. 将 FolderNode 抽取为独立文件 `FolderNode.tsx`
2. 在 SchemaNode 中复制类似的渲染逻辑

选择方案 2（最小改动），在 SchemaNode 中复制必要的渲染逻辑。

- [ ] **Step 3: 修改 ConnectionNode 中的 onOpenSqlConsole 调用**

当从 PostgreSQL schema 下打开 SQL Console 时，SQL 编辑器应该自动使用 `schema.` 前缀。

实际上，跨 schema 查询是用户自己在 SQL 中写的（`SELECT * FROM schema1.table1 JOIN schema2.table2`），不需要自动添加前缀。但可以在 SQL Console 的注释或提示中告知用户当前所在的 schema。

此步骤不需要改动，保持现有行为。

- [ ] **Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx frontend/src/components/Tools/DatabaseTool/components/SchemaNode.tsx
git commit -m "feat: ConnectionList 表操作传递 schema_name 参数

- FolderNode 操作（DDL、truncate、drop、detail）传递 schemaName
- SchemaNode 中的表点击和右键操作支持 schema 上下文
- PostgreSQL schema 下的表操作使用正确的 schema.table 格式"
```

### Task 9: 修改显示偏好支持 schema 级别过滤

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` — SchemaNode 的显示偏好
- Modify: `frontend/src/components/Tools/DatabaseTool/components/DisplaySettingsDialog.tsx` — 增加 schema 过滤选项

- [ ] **Step 1: 修改 SchemaNode 支持显示偏好过滤**

类似于 `DatabaseStructureNode` 使用 `displayPreferences.visible_databases`，`SchemaNode` 应该支持 `displayPreferences.visible_schemas`。

由于 schema 是 PostgreSQL 特有的，我们先实现基本功能，显示偏好作为后续优化。

此步标记为 TODO，不在本次实现范围内。

- [ ] **Step 2: 提交（如果有改动）**

如果没有实质性改动，跳过此任务。

### Task 10: 端到端验证

- [ ] **Step 1: 启动后端服务**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && uvicorn app.main:app --reload --port 19092`
Expected: 后端启动成功，访问 http://localhost:19092/docs 可以看到 API 文档

- [ ] **Step 2: 启动前端服务**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npm run dev`
Expected: 前端启动成功，访问 http://localhost:5178

- [ ] **Step 3: 验证 PostgreSQL Schema 层级**

1. 在数据库工具中添加/选择一个 PostgreSQL 连接
2. 展开连接，确认能看到 database 列表
3. 展开 database，确认能看到 schema 列表（public、pg_catalog 等）
4. 展开 schema，确认能看到 Tables 和 Views 文件夹
5. 点击表名，确认能正确打开数据查看器
6. 打开 SQL Console，执行 `SELECT * FROM public.some_table LIMIT 10`，确认能正确执行

- [ ] **Step 4: 验证其他数据库不受影响**

1. 选择一个 MySQL 连接
2. 展开连接，确认能看到 database 列表
3. 展开 database，确认直接看到 Tables 和 Views（没有 schema 层级）
4. 点击表名，确认功能正常

- [ ] **Step 5: 浏览器 Console 检查**

打开浏览器开发者工具，确认 Console 中没有错误。

---

## 风险点

1. **性能**：当 PostgreSQL 有很多数据库和 schema 时，`get_databases_list` 会建立多个临时连接查询 schema。可能导致连接加载变慢。**缓解措施**：连接复用、超时处理、错误容忍（单个数据库 schema 查询失败不影响整体）。

2. **权限**：用户可能对某些 schema 没有访问权限。**缓解措施**：单个 schema 查询失败时记录 warning 并跳过，不阻断整个列表。

3. **Schema 缓存**：后端 `StructureCache` 的 key 从 `config_id:database_name` 变为 `config_id:database_name:schema_name`。需要确保缓存失效逻辑正确。
