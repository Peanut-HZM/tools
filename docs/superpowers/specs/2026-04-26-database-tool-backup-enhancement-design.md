---
author: Claude Code
created_at: 2026-04-26
purpose: 设计数据库管理工具备份与表结构浏览增强功能，支持全数据库类型备份、服务端文件存储、左侧树表详情展开
---

# 数据库管理工具增强设计文档

## 1. 概述

增强现有数据库管理工具，新增以下能力：

1. **数据库/表备份** — 支持备份表结构、数据或两者，导出为 SQL 文件，支持全部数据库类型（MySQL/PostgreSQL/SQLite/Oracle/SQLServer/MariaDB）
2. **服务端文件存储** — 备份文件保存到服务器，返回下载链接
3. **左侧树表结构详情** — 展开表节点显示字段、索引、外键详情
4. **备份管理** — 查看历史备份记录、下载、删除

## 2. 现状分析

### 2.1 已有能力

| 能力 | 状态 | 位置 |
|------|------|------|
| 备份接口 | 已有（仅 MySQL） | `backend/app/services/database_tool_service.py:2291` |
| 备份模型 | 已有 | `backend/app/models/database_tool_models.py:280-306` |
| 表 Schema 获取 | 已有 | `GET /databases/{id}/tables/{table}/schema` |
| 恢复接口 | 已有 | `POST /configs/{id}/restore` |
| 左侧树结构 | 已有（连接→数据库→Tables/Views） | `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` |
| DDL 查看 | 已有（单表/全库） | `DDLDialog.tsx` + `getDatabaseDDL` |

### 2.2 缺失能力

- 前端无备份操作 UI
- 备份仅支持 MySQL/MariaDB（PostgreSQL、SQLite 等未实现）
- 备份只支持"结构+数据"，缺少"仅结构"和"仅数据"模式
- 备份文件通过 URL 返回但无对应的下载路由（`/backups/{backup_id}/download` 不存在）
- 左侧树只显示表名，无字段、索引、外键详情展开
- 无备份历史记录管理

## 3. 架构设计

### 3.1 整体流程

```
用户操作 → 前端 BackupDialog
               │
               │ POST /configs/{id}/backup
               │ {database_name, backup_mode, tables, include_drop, include_if_not_exists}
               ▼
         后端 DatabaseToolService.backup_database()
               │
               ├─ 根据 db_type 选择生成器
               │   ├─ MySQL/MariaDB → SHOW CREATE TABLE + SELECT *
               │   ├─ PostgreSQL → information_schema + COPY/INSERT
               │   ├─ SQLite → sqlite_master + SELECT *
               │   ├─ SQLServer → sys.tables + SELECT *
               │   └─ Oracle → user_tables + SELECT *
               │
               ├─ 生成 SQL 内容（字符串）
               │
               ├─ 保存到服务器文件 (backups/{user_id}/{timestamp}.sql)
               │
               ├─ 记录备份元数据到本地 SQLite (backups.db)
               │
               └─ 返回 {backup_id, file_name, file_size, download_url, tables_count}
                      │
                      ▼
               前端显示备份成功 + 下载链接
```

### 3.2 文件存储设计

```
backend/
├── backups/                    # 备份文件存储目录
│   ├── {user_id}/              # 按用户隔离
│   │   ├── 20260426_143000_mydb_structure_and_data.sql
│   │   └── 20260426_143500_mydb_structure_only.sql
│   └── ...
└── backups.db                  # SQLite 元数据数据库
```

### 3.3 备份元数据表 (SQLite)

```sql
CREATE TABLE IF NOT EXISTS backup_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    config_id TEXT NOT NULL,
    database_name TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    backup_mode TEXT NOT NULL,  -- 'structure_and_data', 'structure_only', 'data_only'
    tables_count INTEGER NOT NULL,
    tables_list TEXT,           -- JSON 数组
    status TEXT DEFAULT 'success',  -- 'success', 'failed', 'deleted'
    error_message TEXT,
    created_at TEXT NOT NULL,
    downloaded_count INTEGER DEFAULT 0
);

CREATE INDEX idx_backup_user ON backup_records(user_id, created_at DESC);
```

## 4. 接口设计

### 4.1 备份接口（增强）

**`POST /configs/{id}/backup`**

请求体增强：
```python
class BackupDatabaseRequest(BaseModel):
    database_name: str
    backup_format: str = Field("sql", description="备份格式：sql")
    backup_mode: str = Field("structure_and_data", description="备份模式")
    # structure_and_data | structure_only | data_only
    tables: Optional[List[str]] = None
    include_drop: bool = Field(False, description="是否包含 DROP TABLE")
    include_if_not_exists: bool = Field(True, description="是否包含 IF NOT EXISTS")
```

响应体增强：
```python
class BackupDatabaseResponse(BaseModel):
    backup_id: str
    file_name: str
    file_size: int
    download_url: str
    created_at: datetime
    tables_count: int
    backup_mode: str
    status: str  # 'success' | 'partial' | 'failed'
```

### 4.2 下载备份文件

**`GET /backups/{backup_id}/download`** — **新增**

返回：文件流（`application/sql`）

```python
@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str = PathParam(...),
    user_id: str = Depends(get_current_user_id),
):
    """下载备份文件"""
```

### 4.3 备份历史记录

**`GET /configs/{id}/backups`** — **新增**

```python
@router.get("/configs/{id}/backups", response_model=List[BackupRecordResponse])
async def list_backups(
    id: str = PathParam(...),
    database_name: Optional[str] = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    user_id: str = Depends(get_current_user_id),
):
    """获取备份历史列表"""
```

**`DELETE /backups/{backup_id}`** — **新增**

```python
@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str = PathParam(...),
    user_id: str = Depends(get_current_user_id),
):
    """删除备份文件"""
```

### 4.4 表详细结构

**`GET /databases/{id}/tables/{table}/detail`** — **新增**

复用现有 `get_table_schema` 逻辑，返回更详细的结构信息：

```python
class TableDetailResponse(BaseModel):
    table_name: str
    comment: Optional[str]
    columns: List[ColumnDetail]
    indexes: List[IndexDetail]
    foreign_keys: List[ForeignKeyDetail]
    row_count: Optional[int]

class ColumnDetail(BaseModel):
    name: str
    type: str
    length: Optional[str]
    nullable: bool
    default_value: Optional[str]
    comment: Optional[str]
    primary_key: bool
    auto_increment: bool
    ordinal_position: int

class IndexDetail(BaseModel):
    name: str
    unique: bool
    primary: bool
    columns: List[str]

class ForeignKeyDetail(BaseModel):
    name: str
    constrained_columns: List[str]
    referred_table: str
    referred_columns: List[str]
```

### 4.5 表行数统计

**`GET /databases/{id}/tables/{table}/row-count`** — **新增**

```python
@router.get("/databases/{id}/tables/{table}/row-count", response_model=Dict[str, int])
async def get_table_row_count(
    id: str = PathParam(...),
    table: str = PathParam(...),
    database_name: str = Query(...),
    user_id: str = Depends(get_current_user_id),
):
    """获取表行数"""
```

## 5. 前端设计

### 5.1 组件清单

| 组件 | 文件 | 功能 |
|------|------|------|
| `BackupDialog` | `components/Tools/DatabaseTool/components/BackupDialog.tsx` | 备份配置对话框 |
| `BackupHistoryDialog` | `components/Tools/DatabaseTool/components/BackupHistoryDialog.tsx` | 备份历史管理对话框 |
| `TableDetailPanel` | 集成到 `ConnectionList.tsx` | 左侧树表详情展开 |

### 5.2 BackupDialog 布局

```
┌──────────────────────────────────────────────────┐
│  📦 数据库备份                   [×]              │
├──────────────────────────────────────────────────┤
│                                                  │
│ 连接: [my-prod-db ▼]  数据库: [my_database ▼]    │
│                                                  │
│ ┌─ 选择要备份的表 ─────────────────────────────┐ │
│ │ ☑ 全选 (12 个表)                    [刷新]   │ │
│ │ ┌──────────────────────────────────────────┐ │ │
│ │ │ ☑ users            1,234 条    45.2 KB   │ │ │
│ │ │ ☑ orders           5,678 条   230.1 KB   │ │ │
│ │ │ ☑ products           890 条    78.5 KB   │ │ │
│ │ │ ☑ sessions         3,456 条    12.3 KB   │ │ │
│ │ │ ☑ logs           120,000 条     5.2 MB   │ │ │
│ │ │ ...                                      │ │ │
│ │ └──────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ┌─ 备份模式 ──────────────────────────────────┐ │
│ │ ◉ 结构 + 数据  (完整备份)                    │ │
│ │ ○ 仅结构      (CREATE TABLE / DDL)           │ │
│ │ ○ 仅数据      (INSERT INTO)                  │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ☑ 包含 DROP TABLE 语句                           │
│ ☑ 包含 IF NOT EXISTS                             │
│                                                  │
│ ┌─ 进度条 (备份中) ──────────────────────────┐  │
│ │ ████████████████░░░░░░░░  65%              │  │
│ │ 正在备份: logs (8/12)                      │  │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│                       [ 取消 ]  [ 📦 开始备份 ]   │
└──────────────────────────────────────────────────┘
```

### 5.3 BackupHistoryDialog 布局

```
┌──────────────────────────────────────────────────┐
│  📋 备份历史                     [×]              │
├──────────────────────────────────────────────────┤
│                                                  │
│ 筛选: [所有数据库 ▼]  [2026-04-01 ~ 2026-04-26]  │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ 文件名            │ 模式  │ 大小   │ 操作    │ │
│ ├──────────────────────────────────────────────┤ │
│ │ backup_mydb_...   │ 完整  │ 5.8 MB │ ↓ 🗑    │ │
│ │ 2026-04-26 14:30 │       │       │         │ │
│ ├──────────────────────────────────────────────┤ │
│ │ backup_mydb_...   │ 结构  │ 45 KB  │ ↓ 🗑    │ │
│ │ 2026-04-25 09:15 │       │       │         │ │
│ ├──────────────────────────────────────────────┤ │
│ │ ...                                          │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ 分页: < 1 2 3 >     共 45 条                     │
└──────────────────────────────────────────────────┘
```

### 5.4 左侧树表详情展开

**当前结构：**
```
├─ 🔗 my-prod-db [prod]
│  ├─ ▼ 🗄️ my_database
│  │  ├─ 📂 Tables (12)
│  │  │  ├─ 📄 users
│  │  │  ├─ 📄 orders
│  │  │  └─ ...
│  │  └─ 📂 Views (2)
```

**新增结构：**
```
├─ 🔗 my-prod-db [prod]
│  ├─ ▼ 🗄️ my_database
│  │  ├─ 📂 Tables (12)
│  │  │  ├─ ▼ 📄 users
│  │  │  │  ├─ 📋 字段 (6)
│  │  │  │  │  ├─ id         INT          PK AI
│  │  │  │  │  ├─ name       VARCHAR(255) NOT NULL
│  │  │  │  │  ├─ email      VARCHAR(255) UNIQUE
│  │  │  │  │  ├─ password   VARCHAR(255) NOT NULL
│  │  │  │  │  ├─ status     TINYINT      DEFAULT 1
│  │  │  │  │  └─ created_at DATETIME
│  │  │  │  ├─ 🔑 索引 (3)
│  │  │  │  │  ├─ PRIMARY    (id)
│  │  │  │  │  ├─ idx_email  UNIQUE (email)
│  │  │  │  │  └─ idx_status (status)
│  │  │  │  └─ 🔗 外键 (1)
│  │  │  │     └─ fk_role    → roles.id
│  │  │  ├─ 📄 orders
│  │  │  └─ ...
│  │  └─ 📂 Views (2)
```

**交互：** 点击表名展开后，自动请求 `GET /databases/{id}/tables/{table}/detail`，返回字段/索引/外键信息后渲染。

### 5.5 右键菜单新增项

**数据库节点右键：**
- 📦 备份数据库
- 📋 备份历史
- (已有项：新建数据库、刷新、删除数据库)

**Tables 文件夹右键：**
- 📦 备份所选表
- 📋 备份历史
- (已有项：新建表、生成全部 DDL、清空所有表、删除所有表)

**单个表节点右键：**
- 📦 备份此表
- (已有项：查看数据、查看结构、生成 DDL、修改结构、清空数据、删除表)

## 6. 数据流

### 6.1 备份数据流

```
BackupDialog
  │
  ├─ 1. 选择连接/数据库 → GET /databases/{id}/structure
  │                        获取表列表
  │
  ├─ 2. 用户勾选表、选择模式
  │
  ├─ 3. 点击"开始备份" → POST /configs/{id}/backup
  │                        {database_name, backup_mode, tables, include_drop, include_if_not_exists}
  │
  ├─ 4. 后端执行备份：
  │   ├─ a. 连接目标数据库
  │   ├─ b. 根据 db_type 调用对应生成器
  │   ├─ c. 生成 SQL 内容
  │   ├─ d. 写入文件到 backups/{user_id}/
  │   ├─ e. 记录元数据到 backups.db
  │   └─ f. 返回 backup_id, file_name, file_size, download_url
  │
  ├─ 5. 前端显示成功 + 下载按钮
  │
  └─ 6. 用户点击下载 → GET /backups/{backup_id}/download
                          → 返回文件流
```

### 6.2 表详情数据流

```
用户点击展开表节点
  │
  ├─ GET /databases/{id}/tables/{table}/detail?database_name=xxx
  │
  ├─ 后端：
  │   ├─ inspector.get_columns(table) → columns
  │   ├─ inspector.get_indexes(table) → indexes
  │   ├─ inspector.get_foreign_keys(table) → foreign_keys
  │   └─ 返回 TableDetailResponse
  │
  └─ 前端渲染：
      ├─ 字段列表（名称、类型、约束、注释）
      ├─ 索引列表（名称、类型、列）
      └─ 外键列表（名称、参照关系）
```

## 7. 备份生成器实现

### 7.1 多数据库类型支持

每种数据库使用不同的 SQL 方言获取 DDL 和数据：

```python
class BackupGenerator(ABC):
    @abstractmethod
    def get_create_table_ddl(self, conn, table: str) -> str: ...
    
    @abstractmethod
    def get_insert_statements(self, conn, table: str) -> List[str]: ...


class MySQLBackupGenerator(BackupGenerator):
    # 使用 SHOW CREATE TABLE
    def get_create_table_ddl(self, conn, table):
        result = conn.execute(text(f"SHOW CREATE TABLE `{table}`"))
        return result.fetchone()[1]


class PostgreSQLBackupGenerator(BackupGenerator):
    # 使用 pg_catalog + information_schema 构建 DDL
    def get_create_table_ddl(self, conn, table):
        # 查询 pg_attribute, pg_type, pg_constraint 等
        ...


class SQLiteBackupGenerator(BackupGenerator):
    # 使用 sqlite_master
    def get_create_table_ddl(self, conn, table):
        result = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            {"name": table}
        ))
        return result.fetchone()[0]


class SQLServerBackupGenerator(BackupGenerator):
    # 使用 sys.tables + INFORMATION_SCHEMA
    ...


class OracleBackupGenerator(BackupGenerator):
    # 使用 user_tab_columns + user_constraints
    ...
```

### 7.2 备份模式实现

```python
def generate_backup_sql(
    conn, engine, db_type: str, tables: List[str],
    mode: str, include_drop: bool, include_if_not_exists: bool
) -> str:
    """
    mode: 'structure_and_data' | 'structure_only' | 'data_only'
    """
    statements = []
    generator = get_generator(db_type)
    
    for table in tables:
        if include_drop:
            statements.append(f"DROP TABLE IF EXISTS `{table}`;")
        
        if mode in ('structure_and_data', 'structure_only'):
            ddl = generator.get_create_table_ddl(conn, table)
            if include_if_not_exists:
                ddl = ddl.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
            statements.append(ddl + ";")
        
        if mode in ('structure_and_data', 'data_only'):
            inserts = generator.get_insert_statements(conn, table)
            statements.extend(inserts)
    
    return "\n\n".join(statements)
```

## 8. 文件变更清单

### 8.1 后端新增/修改文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/app/services/database_tool_service.py` | 修改 | 增强 `backup_database`，新增下载/历史/删除方法 |
| `backend/app/models/database_tool_models.py` | 修改 | 新增 `backup_mode` 字段、`BackupRecordResponse`、`TableDetailResponse` 等模型 |
| `backend/app/routes/database_tool.py` | 修改 | 新增下载、历史、删除、表详情、行计数路由 |
| `backend/app/services/backup_storage.py` | 新增 | 备份文件存储管理（文件 I/O + SQLite 元数据） |
| `backend/app/services/backup_generators.py` | 新增 | 多数据库类型备份生成器抽象层 |

### 8.2 前端新增/修改文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/components/Tools/DatabaseTool/components/BackupDialog.tsx` | 新增 | 备份配置对话框 |
| `frontend/src/components/Tools/DatabaseTool/components/BackupHistoryDialog.tsx` | 新增 | 备份历史管理对话框 |
| `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` | 修改 | 表节点展开详情、右键菜单新增备份项 |
| `frontend/src/api/databaseToolApi.ts` | 修改 | 新增备份相关 API 函数 |
| `frontend/src/types/databaseTool.ts` | 修改 | 新增备份相关类型定义 |
| `frontend/src/i18n/zh-CN.ts` | 修改 | 新增翻译文案 |

## 9. 测试策略

### 9.1 后端测试
- 单元测试：每种数据库类型的备份生成器
- 集成测试：完整备份→下载→恢复流程
- 边界测试：空表、大表、特殊字符数据

### 9.2 前端测试
- UI 测试：备份对话框各模式切换
- 交互测试：左侧树展开/收起表详情
- 错误处理：备份失败提示、网络错误重试

## 10. 验收标准

1. ✅ 支持 6 种数据库类型的完整备份（结构+数据/仅结构/仅数据）
2. ✅ 备份文件保存到服务端，支持下载和删除
3. ✅ 备份历史记录可按数据库筛选、分页浏览
4. ✅ 左侧树可展开显示表的字段、索引、外键详情
5. ✅ 右键菜单新增备份入口（数据库级/表级）
6. ✅ 备份过程中显示进度条
7. ✅ 用户隔离：只能看到自己的备份
8. ✅ 无浏览器控制台报错
