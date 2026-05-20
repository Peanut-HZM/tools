# PostgreSQL SQL 执行器 Schema 支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 PostgreSQL 的 SQL 执行器增加 Schema 下拉框，用户选择 schema 后执行自由 SQL 时自动为未指定 schema 的表名拼接 schema 前缀，不影响其他数据库类型。

**Architecture:** 前端 SQLExecutor 增加 Schema 下拉框并在执行时传递 `schema_name`；后端 `execute_sql` 接收 `schema_name` 并在 PostgreSQL 场景下调用 AST 解析器自动注入 schema 前缀到表名；新增后端 `/databases/{id}/schemas` 端点用于获取指定数据库下的 schema 列表。

**Tech Stack:** Python FastAPI, sqlparse (AST 解析), React TypeScript, Pydantic

---

### Task 1: 后端新增 `/databases/{id}/schemas` 端点

**Files:**
- Modify: `backend/app/services/database_tool_service.py` — 新增 `get_schemas_list` 方法
- Modify: `backend/app/routes/database_tool.py` — 新增 GET `/databases/{id}/schemas` 路由

- [ ] **Step 1: 在 `database_tool_service.py` 中添加 `get_schemas_list` 方法**

在 `get_databases_list` 方法之后（约第 1161 行后），添加新方法：

```python
@staticmethod
def get_schemas_list(user_id: str, config_id: str, database_name: Optional[str] = None) -> List[str]:
    """获取指定数据库下的 schema 列表（PostgreSQL）"""
    config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
    if not config_row:
        raise ValueError("Configuration not found")

    db_type = config_row["db_type"]
    if db_type != DatabaseType.POSTGRESQL:
        # 其他数据库不支持 schema 列表，返回空
        return []

    try:
        password = EncryptionUtils.decrypt(config_row["password_encrypted"])
    except Exception:
        raise ValueError("Failed to decrypt password")

    # 确定目标数据库名：优先使用参数，其次使用配置中的 database_name
    target_db = database_name or config_row.get("database_name")
    if not target_db:
        raise ValueError("database_name is required for PostgreSQL schema listing")

    config_dict = {
        "db_type": config_row["db_type"],
        "host": config_row["host"],
        "port": config_row["port"],
        "database_name": target_db,
        "username": config_row["username"],
        "password": password,
        "charset": config_row["charset"],
        "max_pool_size": config_row["max_pool_size"],
    }

    temp_key = f"{config_id}:_temp_schemas_{target_db}"
    engine = DBConnectionManager.get_engine(temp_key, config_dict)

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

- [ ] **Step 2: 在 `database_tool.py` 中添加路由**

在 `get_databases_list` 路由之后（约第 188 行后），添加：

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

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile app/services/database_tool_service.py && python -m py_compile app/routes/database_tool.py`
Expected: 无输出（语法正确）

- [ ] **Step 4: 重启后端服务验证端点**

重启后端服务，访问 `http://localhost:8000/docs` 确认新端点出现在 Swagger UI 中。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/database_tool_service.py backend/app/routes/database_tool.py
git commit -m "feat: 新增 PostgreSQL schema 列表查询端点"
```

---

### Task 2: 后端新增 SQL Schema 注入器

**Files:**
- Create: `backend/app/utils/sql_schema_injector.py`

- [ ] **Step 1: 创建测试文件并编写测试用例**

创建测试文件 `backend/tests/test_sql_schema_injector.py`（如果 tests 目录不存在则创建）：

```python
import pytest
from app.utils.sql_schema_injector import inject_schema_name


class TestInjectSchemaName:
    """测试 SQL schema 注入功能"""

    SCHEMA = "inventory"

    def test_simple_select_from(self):
        sql = "SELECT * FROM users"
        result = inject_schema_name(sql, self.SCHEMA)
        assert result == 'SELECT * FROM "inventory"."users"'

    def test_select_with_schema_already_specified(self):
        sql = "SELECT * FROM public.users"
        result = inject_schema_name(sql, self.SCHEMA)
        assert result == "SELECT * FROM public.users"

    def test_select_with_quoted_schema(self):
        sql = 'SELECT * FROM "public"."users"'
        result = inject_schema_name(sql, self.SCHEMA)
        assert result == sql

    def test_select_with_join(self):
        sql = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        result = inject_schema_name(sql, self.SCHEMA)
        assert '"inventory"."users"' in result
        assert '"inventory"."orders"' in result

    def test_select_with_left_join(self):
        sql = "SELECT * FROM users u LEFT JOIN orders o ON u.id = o.user_id"
        result = inject_schema_name(sql, self.SCHEMA)
        assert '"inventory"."users"' in result
        assert '"inventory"."orders"' in result

    def test_subquery(self):
        sql = "SELECT * FROM (SELECT id FROM orders) t"
        result = inject_schema_name(sql, self.SCHEMA)
        assert '"inventory"."orders"' in result
        # 子查询别名 t 不应被注入
        assert '"inventory"."t"' not in result

    def test_cte(self):
        sql = "WITH x AS (SELECT * FROM users) SELECT * FROM x"
        result = inject_schema_name(sql, self.SCHEMA)
        assert '"inventory"."users"' in result
        # CTE 别名 x 不应被注入
        assert '"inventory"."x"' not in result

    def test_insert_into(self):
        sql = "INSERT INTO users (name, email) VALUES ('test', 'test@example.com')"
        result = inject_schema_name(sql, self.SCHEMA)
        assert result == 'INSERT INTO "inventory"."users" (name, email) VALUES (\'test\', \'test@example.com\')'

    def test_update_table(self):
        sql = "UPDATE users SET name = 'new' WHERE id = 1"
        result = inject_schema_name(sql, self.SCHEMA)
        assert result == 'UPDATE "inventory"."users" SET name = \'new\' WHERE id = 1'

    def test_delete_from(self):
        sql = "DELETE FROM users WHERE id = 1"
        result = inject_schema_name(sql, self.SCHEMA)
        assert result == 'DELETE FROM "inventory"."users" WHERE id = 1'

    def test_multiple_statements(self):
        sql = "SELECT * FROM users; INSERT INTO logs (msg) VALUES ('done')"
        result = inject_schema_name(sql, self.SCHEMA)
        assert '"inventory"."users"' in result
        assert '"inventory"."logs"' in result

    def test_function_call_not_injected(self):
        sql = "SELECT * FROM generate_series(1, 10)"
        result = inject_schema_name(sql, self.SCHEMA)
        # generate_series 是函数调用，紧跟在 FROM 后面但在 ( 之前，
        # 我们的实现应该只注入标识符后跟空格或逗号的情况
        # 这里 generate_series 后面紧跟 (，应跳过
        assert '"inventory"."generate_series"' not in result

    def test_non_select_statement(self):
        sql = "DROP TABLE users"
        result = inject_schema_name(sql, self.SCHEMA)
        # DROP TABLE 也需要处理
        assert '"inventory"."users"' in result

    def test_non_postgresql_sql_passthrough(self):
        """非 PostgreSQL 不调用注入（由调用方保证）"""
        # 此函数本身不知道数据库类型，调用方只在 postgresql 时调用
        pass
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m pytest tests/test_sql_schema_injector.py -v`
Expected: 大部分测试 FAIL（函数未实现）

- [ ] **Step 3: 实现 `sql_schema_injector.py`**

```python
"""
SQL Schema 注入器

基于 sqlparse AST 解析 SQL，为 PostgreSQL 中未指定 schema 的表名自动注入 schema 前缀。
仅处理已知的 SQL 关键字后的表名：FROM, JOIN 系列, UPDATE, INTO, ALTER TABLE, TRUNCATE TABLE, DROP TABLE。
"""

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Parenthesis, Function
from sqlparse.tokens import Keyword, DML, Punctuation


# 需要注入 schema 的关键字集合
TABLE_KEYWORDS = {
    "FROM",
    "JOIN",
    "INNER JOIN",
    "LEFT JOIN",
    "RIGHT JOIN",
    "OUTER JOIN",
    "LEFT OUTER JOIN",
    "RIGHT OUTER JOIN",
    "FULL JOIN",
    "FULL OUTER JOIN",
    "CROSS JOIN",
    "NATURAL JOIN",
    "INTO",
    "UPDATE",
}

# 特殊复合关键字
COMPOUND_KEYWORDS = {"ALTER TABLE", "TRUNCATE TABLE", "DROP TABLE"}


def _is_schema_qualified(name: str) -> bool:
    """判断表名是否已包含 schema 前缀"""
    # 去除引号后检查是否包含 .
    clean = name.strip().strip('"').strip("'")
    return "." in clean


def _is_function_call(token) -> bool:
    """判断是否为函数调用（表名后紧跟括号）"""
    if hasattr(token, 'ttype') and token.ttype is Punctuation and token.value == '(':
        return True
    return False


def _inject_into_token(token_str: str, schema_name: str) -> str:
    """给单个 token 字符串注入 schema 前缀"""
    stripped = token_str.strip()
    if not stripped:
        return token_str
    if _is_schema_qualified(stripped):
        return token_str
    # 跳过 SQL 关键字（避免把 UPDATE/SELECT 等当作表名）
    upper = stripped.upper()
    sql_keywords = {
        "SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "AND", "OR",
        "NOT", "NULL", "AS", "ON", "IN", "IS", "LIKE", "BETWEEN", "ORDER",
        "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT",
        "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END", "WITH", "RECURSIVE",
        "VALUES", "INTO", "SET", "RETURNING", "TRUE", "FALSE", "DEFAULT",
        "CREATE", "ALTER", "DROP", "TRUNCATE", "TABLE", "INDEX", "VIEW",
        "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT", "UNIQUE",
        "CHECK", "NOT NULL",
    }
    if upper in sql_keywords:
        return token_str
    return f'"{schema_name}".{stripped}'


def inject_schema_name(sql: str, schema_name: str) -> str:
    """
    为 SQL 中未指定 schema 的表名注入 schema 前缀。

    处理的关键字: FROM, JOIN 系列, UPDATE (语句开头), INTO (INSERT INTO 后),
                 ALTER TABLE, TRUNCATE TABLE, DROP TABLE

    Args:
        sql: 原始 SQL 语句（单条语句，不含分号分隔的多条语句）
        schema_name: 要注入的 schema 名称

    Returns:
        注入 schema 前缀后的 SQL 语句
    """
    if not schema_name:
        return sql

    parsed = sqlparse.parse(sql)
    if not parsed:
        return sql

    result_tokens = []

    for statement in parsed:
        if not str(statement).strip():
            continue

        modified = _process_statement(statement, schema_name)
        result_tokens.append(str(modified))

    return " ".join(result_tokens) if result_tokens else sql


def _process_statement(statement, schema_name: str) -> str:
    """处理单条 SQL 语句"""
    tokens = list(statement.flatten())
    if not tokens:
        return str(statement)

    i = 0
    result_parts = []

    while i < len(tokens):
        token = tokens[i]
        token_str = str(token).strip()
        token_upper = token_str.upper()

        # 跳过空白
        if not token_str:
            i += 1
            continue

        # 检查是否为复合关键字（ALTER TABLE, TRUNCATE TABLE, DROP TABLE）
        if i + 1 < len(tokens):
            next_str = str(tokens[i + 1]).strip().upper()
            compound = f"{token_upper} {next_str}"
            if compound in COMPOUND_KEYWORDS:
                result_parts.append(token_str)
                result_parts.append(str(tokens[i + 1]).strip())
                i += 2
                # 跳过后续的空白
                while i < len(tokens) and not str(tokens[i]).strip():
                    i += 1
                # 下一个 token 是表名
                if i < len(tokens):
                    table_token = str(tokens[i]).strip()
                    if not _is_schema_qualified(table_token):
                        table_token = f'"{schema_name}".{table_token}'
                    result_parts.append(table_token)
                    i += 1
                continue

        # 检查是否为表关键字
        is_table_keyword = False

        if token_upper in TABLE_KEYWORDS:
            is_table_keyword = True
        elif token_upper == "JOIN":
            is_table_keyword = True

        if is_table_keyword:
            result_parts.append(token_str)
            i += 1
            # 跳过空白
            while i < len(tokens) and not str(tokens[i]).strip():
                i += 1
            # 下一个非空白 token 是表名
            if i < len(tokens):
                table_token = str(tokens[i]).strip()
                # 如果是括号开头，说明是子查询或函数，跳过
                if table_token.startswith("("):
                    result_parts.append(table_token)
                    i += 1
                    continue
                if not _is_schema_qualified(table_token):
                    # 检查后面是否有括号（函数调用）
                    next_i = i + 1
                    while next_i < len(tokens) and not str(tokens[next_i]).strip():
                        next_i += 1
                    if next_i < len(tokens) and str(tokens[next_i]).strip() == '(':
                        # 函数调用，不注入
                        result_parts.append(table_token)
                    else:
                        table_token = f'"{schema_name}".{table_token}'
                        result_parts.append(table_token)
                    i += 1
                else:
                    result_parts.append(table_token)
                    i += 1
            continue

        # 处理 UPDATE 语句开头的表名（UPDATE 后面直接跟表名，不需要 TABLE 关键字）
        if token_upper == "UPDATE" and i == 0:
            result_parts.append(token_str)
            i += 1
            # 跳过空白
            while i < len(tokens) and not str(tokens[i]).strip():
                i += 1
            if i < len(tokens):
                table_token = str(tokens[i]).strip()
                if not _is_schema_qualified(table_token):
                    table_token = f'"{schema_name}".{table_token}'
                result_parts.append(table_token)
                i += 1
            continue

        # 默认情况：保留原始 token
        result_parts.append(token_str)
        i += 1

    return " ".join(result_parts)


def process_sql_with_schema_injection(sql: str, schema_name: str) -> str:
    """
    处理可能包含多条语句的 SQL，为每条语句注入 schema 前缀。

    Args:
        sql: 可能包含多条语句的 SQL（以分号分隔）
        schema_name: 要注入的 schema 名称

    Returns:
        注入后的 SQL
    """
    if not schema_name:
        return sql

    statements = sqlparse.split(sql)
    processed = []

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        processed.append(inject_schema_name(stmt, schema_name))

    return "; ".join(processed)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m pytest tests/test_sql_schema_injector.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/sql_schema_injector.py backend/tests/test_sql_schema_injector.py
git commit -m "feat: 新增 SQL schema 注入器（基于 sqlparse AST 解析）"
```

---

### Task 3: 后端 `execute_sql` 集成 schema 注入

**Files:**
- Modify: `backend/app/models/database_tool_models.py:89-97` — `SQLExecutionRequest` 增加 `schema_name`
- Modify: `backend/app/services/database_tool_service.py:911-973` — `execute_sql` 方法集成 schema 注入

- [ ] **Step 1: 更新 `SQLExecutionRequest` Pydantic 模型**

在 `backend/app/models/database_tool_models.py` 第 89-97 行，添加 `schema_name` 字段：

```python
class SQLExecutionRequest(BaseModel):
    db_config_id: str
    sql: str
    params: Optional[Dict[str, Any]] = None
    database_name: Optional[str] = None  # Override database name
    schema_name: Optional[str] = None  # Schema name for PostgreSQL
    page: Optional[int] = Field(None, ge=1, description="Page number for pagination")
    page_size: Optional[int] = Field(
        None, ge=1, le=1000, description="Page size for pagination"
    )
```

- [ ] **Step 2: 修改 `execute_sql` 方法**

在 `backend/app/services/database_tool_service.py` 第 911 行附近的 `execute_sql` 方法中，在获取 `config_row` 的 `db_type` 后（约第 931 行 config_dict 定义之后），添加 schema 注入逻辑：

找到第 944 行 `final_sql = request.sql` 附近，替换为：

```python
        final_sql = request.sql

        # PostgreSQL schema 注入：当指定了 schema_name 时，自动为未指定 schema 的表名添加前缀
        if config_row["db_type"] == DatabaseType.POSTGRESQL and request.schema_name:
            from app.utils.sql_schema_injector import process_sql_with_schema_injection
            final_sql = process_sql_with_schema_injection(request.sql, request.schema_name)

        # Only apply auto-pagination if it's a single SELECT statement
        import sqlparse

        statements = sqlparse.split(final_sql)
        statements = [s for s in statements if s.strip()]
```

同时修改第 958-964 行的 `statements[0]` 为 `statements[0]`（不变），但注意 `_apply_pagination` 的输入现在是处理过 schema 注入的 SQL。

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile app/services/database_tool_service.py && python -m py_compile app/models/database_tool_models.py`
Expected: 无输出（语法正确）

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/database_tool_models.py backend/app/services/database_tool_service.py
git commit -m "feat: execute_sql 集成 PostgreSQL schema 注入"
```

---

### Task 4: 前端类型和 API 层更新

**Files:**
- Modify: `frontend/src/types/databaseTool.ts:95-102` — `SQLExecutionRequest` 增加 `schema_name`
- Modify: `frontend/src/api/databaseToolApi.ts` — 新增 `getSchemasList` API 函数

- [ ] **Step 1: 更新 TypeScript `SQLExecutionRequest` 类型**

在 `frontend/src/types/databaseTool.ts` 第 95-102 行，添加 `schema_name`：

```typescript
export interface SQLExecutionRequest {
  db_config_id: string;
  sql: string;
  params?: Record<string, any>;
  database_name?: string;
  schema_name?: string;  // PostgreSQL schema override
  page?: number;
  page_size?: number;
}
```

- [ ] **Step 2: 添加 `getSchemasList` API 函数**

在 `frontend/src/api/databaseToolApi.ts` 中，`getDatabasesList` 函数之后（约第 143 行后），添加：

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

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 可能会有 SQLExecutor 相关的类型错误（因为 executeSQL 可能还没传 schema_name），但没有新的类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/databaseTool.ts frontend/src/api/databaseToolApi.ts
git commit -m "feat: 前端类型和 API 层增加 schema_name 支持"
```

---

### Task 5: 前端 SQLExecutor 增加 Schema 下拉框

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx` — SqlTabState 增加 schemaName

- [ ] **Step 1: 更新 DatabaseTool.tsx 的 Tab 状态**

在 `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx` 第 9-13 行，更新 `SqlTabState`：

```typescript
interface SqlTabState {
  configId: string;
  databaseName: string;
  schemaName: string;  // 新增
  sql: string;
}
```

更新 `handleConnectionSelect` 回调（约第 124-141 行），添加 `schemaName`：

```typescript
  const handleConnectionSelect = useCallback((configId: string, databaseName?: string, schemaName?: string) => {
    const activeTab = tabs.find(t => t.id === activeTabId);
    if (activeTab?.type === 'sql') {
      const db = databaseName || configs.find(c => c.id === configId)?.database_name || '';
      const schema = schemaName || '';
      const currentSql = activeTab.sqlState?.sql || '';
      setTabs(prev => prev.map(t => 
        t.id === activeTabId 
          ? { 
              ...t, 
              sqlState: { configId, databaseName: db, schemaName: schema, sql: currentSql },
              title: deriveTabTitle(configId, db, configs)
            }
          : t
      ));
    } else {
      handleOpenSqlConsole('', databaseName, configId);
    }
  }, [tabs, activeTabId, configs]);
```

更新 `handleSqlStateChange` 回调（约第 144-154 行），处理 `schemaName`：

```typescript
  const handleSqlStateChange = useCallback((tabId: string, state: { configId: string; database: string; schema?: string; sql: string }) => {
    setTabs(prev => prev.map(t => 
      t.id === tabId 
        ? { 
            ...t, 
            sqlState: { configId: state.configId, databaseName: state.database, schemaName: state.schema || '', sql: state.sql },
            title: deriveTabTitle(state.configId, state.database, configs)
          }
        : t
    ));
  }, [configs]);
```

更新 SQLExecutor 组件的渲染（约第 226-231 行），传递 schema prop：

```typescript
                <SQLExecutor
                  configId={tab.sqlState?.configId || ''}
                  database={tab.sqlState?.databaseName || ''}
                  schema={tab.sqlState?.schemaName || ''}
                  sql={tab.sqlState?.sql || ''}
                  onStateChange={(state) => handleSqlStateChange(tab.id, state)}
                />
```

- [ ] **Step 2: 更新 SQLExecutor.tsx props 接口**

在 `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx` 第 10-15 行，更新接口：

```typescript
interface SQLExecutorProps {
  configId: string;
  database: string;
  schema: string;  // 新增
  sql: string;
  onStateChange: (state: { configId: string; database: string; schema?: string; sql: string }) => void;
}
```

在组件函数签名中添加 `schema` prop：

```typescript
const SQLExecutor: React.FC<SQLExecutorProps> = ({ 
  configId, 
  database,
  schema,
  sql,
  onStateChange
}) => {
```

- [ ] **Step 3: 添加 schema 状态和加载逻辑**

在现有状态声明（第 34-40 行）之后，添加：

```typescript
  const [schemas, setSchemas] = useState<string[]>([]);
  const [schemaLoading, setSchemaLoading] = useState(false);
```

- [ ] **Step 4: 修改 useEffect 加载 schema 列表**

修改第 42-79 行的 useEffect，增加 PostgreSQL schema 加载逻辑：

```typescript
  useEffect(() => {
    const fetchAll = async () => {
      if (!currentConfig) {
        setDatabases([]);
        setTables([]);
        setSchemas([]);
        return;
      }

      setDbLoading(true);
      try {
        const targetDb = currentDatabase || currentConfig.database_name;
        const isPostgres = currentConfig.db_type === 'postgresql';

        // 获取数据库列表（或 PostgreSQL 的 database:schema 列表）
        const dbsPromise = api.getDatabasesList(currentConfig.id);

        // PostgreSQL: 如果指定了 database，加载其下的 schema 列表
        let schemasPromise: Promise<string[]> = Promise.resolve([]);
        if (isPostgres && targetDb) {
          schemasPromise = api.getSchemasList(currentConfig.id, targetDb).catch(() => []);
        }

        const structurePromise = targetDb
          ? api.getDatabaseStructure(currentConfig.id, targetDb).catch(() => null)
          : Promise.resolve(null);

        const [dbs, structure, schemasResult] = await Promise.allSettled([
          dbsPromise,
          structurePromise,
          schemasPromise,
        ]);

        if (dbs.status === 'fulfilled') {
          setDatabases(dbs.value);
        } else {
          setDatabases([]);
        }

        if (structure.status === 'fulfilled' && structure.value) {
          setTables([
            ...structure.value.tables.map(t => t.name),
            ...structure.value.views.map(v => v.name)
          ]);
        } else {
          setTables([]);
        }

        if (schemasPromise && schemasResult.status === 'fulfilled') {
          setSchemas(schemasResult.value);
        } else {
          setSchemas([]);
        }
      } catch (err) {
        console.error("Failed to load databases", err);
        setDatabases([]);
        setSchemas([]);
      } finally {
        setDbLoading(false);
      }
    };

    fetchAll();
  }, [currentConfig?.id, currentDatabase]);
```

- [ ] **Step 5: 添加 handleSchemaChange 回调**

在 `handleDatabaseChange` 回调（约第 126-132 行）之后，添加：

```typescript
  const handleSchemaChange = useCallback((newSchema: string) => {
    onStateChange({
      configId,
      database,
      schema: newSchema,
      sql
    });
  }, [configId, database, sql, onStateChange]);
```

- [ ] **Step 6: 添加 Schema 下拉框到 UI**

在 Database 下拉框之后（约第 180 行 `</div>` 之后，`</div>` 关闭之前），添加 Schema 下拉框：

```tsx
        {currentConfig && currentConfig.db_type === 'postgresql' && schemas.length > 0 && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-slate-400">Schema:</label>
            <div className="relative">
              <select 
                className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-blue-500 min-w-[150px] appearance-none pr-8"
                value={schema || ''}
                onChange={(e) => handleSchemaChange(e.target.value)}
                disabled={schemaLoading}
              >
                <option value="">Default (public)</option>
                {schemas.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              {schemaLoading && (
                <div className="absolute right-2 top-1.5 pointer-events-none">
                  <i className="fas fa-spinner fa-spin text-xs text-slate-400"></i>
                </div>
              )}
            </div>
          </div>
        )}
```

- [ ] **Step 7: 修改 executeSQL 调用传递 schema_name**

修改第 96-102 行的 `handleExecute` 中的 API 调用：

```typescript
      const res = await api.executeSQL({
        db_config_id: configId,
        sql: sql,
        database_name: currentDatabase || undefined,
        schema_name: (currentConfig?.db_type === 'postgresql' && schema) ? schema : undefined,
        page: targetPage,
        page_size: pageSize
      });
```

- [ ] **Step 8: 修改 handleConfigChange 清空 schema**

修改第 117-124 行的 `handleConfigChange`：

```typescript
  const handleConfigChange = useCallback((newConfigId: string) => {
    const newConfig = configs.find(c => c.id === newConfigId);
    onStateChange({
      configId: newConfigId,
      database: newConfig?.database_name || '',
      schema: '',  // 清空 schema
      sql
    });
  }, [configs, sql, onStateChange]);
```

- [ ] **Step 9: 修改 handleDatabaseChange 清空 schema**

修改第 126-132 行的 `handleDatabaseChange`：

```typescript
  const handleDatabaseChange = useCallback((newDatabase: string) => {
    onStateChange({
      configId,
      database: newDatabase,
      schema: '',  // 切换数据库时清空 schema
      sql
    });
  }, [configId, sql, onStateChange]);
```

- [ ] **Step 10: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无错误

- [ ] **Step 11: 前端热重载验证**

观察前端热重载是否成功，如无自动重载则重启前端。访问 `http://localhost:5178/tools/database-tool`，选择 PostgreSQL 连接，确认：
- Schema 下拉框出现（选择 Database 后加载）
- 执行 SQL 时 schema_name 被传递

- [ ] **Step 12: Commit**

```bash
git add frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx
git commit -m "feat: SQLExecutor 增加 Schema 下拉框和联动逻辑"
```

---

### Task 6: 端到端验证

**验证步骤：**

1. 启动前后端服务
2. 访问 `http://localhost:5178/tools/database-tool`
3. 左侧选择 PostgreSQL 连接
4. 选择一个 Database → 确认 Schema 下拉框出现并加载 schema 列表
5. 选择一个非 public 的 Schema（如 `inventory`）
6. 在 SQL 编辑器中输入 `SELECT * FROM some_table`（不写 schema）
7. 执行 SQL → 确认查询成功，实际执行的 SQL 为 `SELECT * FROM "inventory"."some_table"`
8. 输入 `SELECT * FROM public.other_table`（已写 schema）
9. 执行 SQL → 确认查询成功，SQL 未被修改
10. 切换到 MySQL 连接 → 确认没有 Schema 下拉框，功能不受影响
