---
name: postgresql-schema-support
description: 为 PostgreSQL 数据库工具增加多 schema 支持，包括 UI 浏览和 SQL 操作，不影响其他数据库类型
metadata:
  type: design
---

# PostgreSQL 多 Schema 支持设计文档

## 问题描述

当前数据库工具不支持 PostgreSQL 的 schema 层级浏览和操作。用户连接 PostgreSQL 后，只能看到 database 级别的表（默认 public schema），无法查看和操作其他 schema 下的表。同时需要不影响 MySQL、SQLite 等其他数据库的正常使用。

## 需求

1. **UI 浏览**：在左侧导航树中，PostgreSQL 连接支持展开到 schema 层级，查看所有 schema 下的表和视图
2. **SQL 操作**：支持跨 schema 查询（使用 `schema.table` 语法）
3. **包含所有 schema**：包括系统 schema（pg_catalog、information_schema 等）和用户自定义 schema
4. **不影响其他数据库**：MySQL/MariaDB/SQLite/SQLServer/Oracle 保持原有行为

## 方案选择

采用**方案 2 - 复用现有 API，参数扩展**：不新增 API 端点，通过修改现有函数的行为来支持 schema 层级。

## 架构设计

### 树形结构

**PostgreSQL（新增）**：
```
Connection → Database → Schema → Tables/Views
```
当连接配置指定了 database_name 时：
```
Connection → Database:Schema → Tables/Views
```

**其他数据库（不变）**：
```
Connection → Database → Tables/Views
```

## 后端改动

### 1. 修改 `get_databases_list` 函数

**文件**：`backend/app/services/database_tool_service.py:1029`

**逻辑**：
- 当 `db_type == POSTGRESQL` 且配置中**没有**指定 `database_name` 时：
  - 查询所有非模板数据库（`SELECT datname FROM pg_database WHERE datistemplate = false`）
  - 对每个数据库，查询其下的所有 schema（`SELECT schema_name FROM information_schema.schemata`）
  - 返回 `["database:schema", ...]` 格式的列表
- 当 `db_type == POSTGRESQL` 且配置中**已**指定 `database_name` 时：
  - 连接指定数据库，查询所有 schema
  - 返回 `["schema1", "schema2", ...]` 格式的列表
- 对于非 PostgreSQL 数据库，保持原有逻辑不变

### 2. 修改 `get_database_structure` 函数

**文件**：`backend/app/services/database_tool_service.py:1080`

**改动**：
- API 端点 `/databases/{id}/structure` 增加可选的 `schema_name` query 参数
- 当 `db_type == POSTGRESQL` 且提供了 `schema_name` 时：
  - 使用 `information_schema.tables WHERE table_schema = :schema` 查询表和视图
  - 使用 `information_schema.tables` 获取表注释
- 非 PostgreSQL 数据库，保持原有逻辑

### 3. 修改 `generate_ddl` 函数

**文件**：`backend/app/services/database_tool_service.py:107`

**改动**：
- 支持 `schema_name` 参数，生成 DDL 时包含 schema 限定
- PostgreSQL DDL 生成使用 `pg_tables` 或 `pg_class` 查询，限定 schema

### 4. 其他函数适配

以下函数需要接受可选的 `schema_name` 参数：
- `get_table_schema` (line 1186)
- `query_table_data` (line 441)
- `get_table_detail` (line 646)
- `get_table_row_count` (line 662)
- `modify_table_structure` (line 166)
- `drop_table_instance` (line 341)
- `truncate_table_instance` (line 360)
- `search_tables` (line 1583)
- `table_preview` (line 522)
- `auto_complete` (line 541)
- `backup_database` (line 557)

**改动方式**：在函数签名中增加 `schema_name: Optional[str] = None` 参数，PostgreSQL 类型数据库在使用时将 schema_name 加入 SQL 查询的 WHERE 条件或表名前缀。

## 前端改动

### 1. 修改 `ConnectionList.tsx`

**文件**：`frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`

**改动**：
- 在 `ConnectionNode` 组件中，根据 `db_type` 判断是否需要增加 Schema 层级
- PostgreSQL 类型连接展开后，显示 schema 列表而非直接的 database 列表
- 新增 `SchemaNode` 组件，复用 `DatabaseStructureNode` 的样式和交互

### 2. 新增 `SchemaNode` 组件

**新文件**：`frontend/src/components/Tools/DatabaseTool/components/SchemaNode.tsx`

**功能**：
- 显示 schema 名称和图标
- 展开后显示该 schema 下的 Tables 和 Views 文件夹
- 支持右键菜单（SQL Console、刷新等）
- 与 `DatabaseStructureNode` 保持一致的交互体验

### 3. 修改 API 调用

**文件**：`frontend/src/api/databaseToolApi.ts`

**改动**：
- `getDatabaseStructure` 函数增加可选的 `schemaName` 参数
- 所有涉及表操作的 API 调用增加 `schema_name` 参数（如果需要）

### 4. 修改 SQL 执行联动

- 当用户从 schema 下的表打开数据时，SQL 中使用 `schema.table` 格式
- 自动补全功能需要包含 schema 信息

## 数据流

```
用户点击 PostgreSQL 连接
  → 调用 getDatabasesList → 返回 ["database:schema", ...] 或 ["schema1", ...]
  → 前端根据 db_type 渲染 Schema 节点
  → 用户点击 Schema 节点
  → 调用 getDatabaseStructure(configId, databaseName, schemaName)
  → 返回该 schema 下的表和视图
  → 用户点击表
  → 打开 TableDataViewer，使用 schema.table 格式查询
```

## 测试计划

1. 验证 PostgreSQL 连接能看到所有 schema
2. 验证展开 schema 能看到正确的表和视图
3. 验证点击表能正确打开数据查看器
4. 验证 SQL 执行支持 `schema.table` 语法
5. 验证 MySQL/SQLite 等其他数据库行为不变
6. 验证 DDL 生成包含 schema 信息
7. 验证备份恢复功能对 schema 的支持

## 风险点

1. **性能**：查询所有数据库的所有 schema 可能较慢，需要评估
2. **权限**：某些 schema 可能用户没有访问权限，需要优雅处理
3. **连接配置变更**：如果用户的连接配置从指定 database_name 变为不指定，需要清除前端缓存
