---
name: postgresql-sql-executor-schema-support
description: PostgreSQL SQL 执行器增加 Schema 下拉框和自动 schema 前缀拼接功能
metadata:
  type: project
---

# PostgreSQL SQL 执行器 Schema 支持设计

## 目标

为 PostgreSQL 数据库的 SQL 执行器增加 Schema 下拉框，用户选择 schema 后，执行自由 SQL 时自动为未指定 schema 的表名拼接 schema 前缀。不影响其他数据库类型。

## 架构

```
前端 SQLExecutor.tsx
  ├── 新增 schema prop + schema 下拉框
  ├── 选择 Database 时加载 schema 列表
  └── 执行 SQL 时传递 schema_name（仅 PostgreSQL）

后端 SQLExecutionRequest
  ├── 新增 schema_name 字段
  └── execute_sql 方法传递 schema_name

后端 sql_schema_injector.py（新模块）
  ├── 基于 sqlparse AST 解析 SQL
  ├── 识别 FROM/JOIN/UPDATE/INTO 等关键字后的表名
  ├── 判断表名是否已含 schema 前缀
  └── 为未含 schema 的表名注入 schema 前缀
```

## 前端改动

### SQLExecutor.tsx
1. **props 扩展**：增加 `schema: string` prop
2. **状态管理**：增加 `schemas: string[]` 和 `schemaLoading: boolean`
3. **Schema 下拉框**：放在 Database 下拉框后面，仅 PostgreSQL 连接时显示
4. **联动逻辑**：
   - 选择 Connection → 清空 schema
   - 选择 Database → 调用 API 获取 schema 列表
   - Schema 列表来源：后端已有的 `getDatabasesList` 接口（返回 `database:schema` 格式）或新增获取 schema 列表接口
5. **执行传递**：`executeSQL` 请求中增加 `schema_name` 字段（仅 PostgreSQL）

### SQLExecutionRequest 类型
- 增加 `schema_name?: string` 字段

### DatabaseTool.tsx
- SqlTabState 增加 `schemaName: string`
- 连接选择时传递 schema_name
- Tab title 更新：`config.schema.database` 格式

## 后端改动

### SQLExecutionRequest schema
- Pydantic 模型增加 `schema_name: Optional[str] = None`

### execute_sql 方法
- 接收 `schema_name` 参数
- 当 `db_type == postgresql` 且 `schema_name` 非空时，调用 schema 注入函数处理 SQL

### sql_schema_injector.py（新文件）
- `inject_schema_name(sql: str, schema_name: str) -> str`
- 使用 `sqlparse.parse()` 解析 SQL 为 AST
- 遍历 token 树，定位以下关键字后的第一个标识符：
  - `FROM`
  - `JOIN` / `LEFT JOIN` / `RIGHT JOIN` / `INNER JOIN` / `OUTER JOIN` / `CROSS JOIN` / `NATURAL JOIN`
  - `UPDATE`（语句开头的表名）
  - `INTO`（INSERT INTO 后的表名）
  - `ALTER TABLE`
  - `TRUNCATE TABLE`
- 检查标识符是否已包含 schema 前缀（形式为 `schema.table` 或 `"schema".table`）
- 若未包含，在标识符前插入 `"schema_name".` 前缀
- 处理多语句（sqlparse.split 后逐个处理再拼接）

## 数据流

```
用户选择 PostgreSQL 连接
  → 选择 Database（如 mydb）
  → 加载 schema 列表（如 public, inventory, auth）
  → 选择 Schema（如 inventory）
  → 输入 SQL: SELECT * FROM users
  → 后端接收 schema_name=inventory
  → SQL 被转换为: SELECT * FROM "inventory"."users"
  → 执行并返回结果
```

## 边界情况

- **用户已写 schema**：`SELECT * FROM public.users` → 不修改
- **用户已写带引号 schema**：`SELECT * FROM "public"."users"` → 不修改
- **子查询**：`SELECT * FROM (SELECT id FROM orders) t` → orders 也被注入
- **CTE**：`WITH x AS (SELECT * FROM users) SELECT * FROM x` → users 被注入，x 不注入
- **函数调用**：`SELECT * FROM generate_series(1, 10)` → 不注入（函数名识别）
- **多语句**：`SELECT * FROM a; INSERT INTO b VALUES (1)` → 两个表都注入
- **其他数据库类型**：不传递 schema_name，完全不受影响
