# 凭据本地化存储设计（Local-First Credential Storage）

**日期**：2026-10-31
**状态**：待评审
**范围**：数据库管理工具、K8s 控制台、SSH 管理、Redis 管理

---

## 1. 背景与目标

### 1.1 问题

当前 4 个凭据类工具的配置（数据库连接、K8s kubeconfig、SSH 连接、Redis 连接）**全部存放在服务端 PostgreSQL**：

| 工具 | 表 | 敏感列 |
|---|---|---|
| 数据库管理 | `db_configs` | `password_encrypted` |
| K8s 控制台 | `k8s_connections` | `auth_data_encrypted`、`ca_cert_encrypted` |
| SSH 管理 | `ssh_configs` | `password_encrypted`、`private_key_encrypted`、`passphrase_encrypted` |
| Redis 管理 | `redis_configs` | `password_encrypted` |

即使密码经过 Fernet 加密，凭据的**密文仍会离开本机**（服务端持有加密密钥，可随时解密）。这与「敏感数据不上传、不离开本机」的安全预期不符。

### 1.2 目标

1. 用户可将凭据类配置保存在**本机 SQLite**，物理上不离开本机
2. 用户可**自行选择**存本地还是存服务器（逐条配置粒度）
3. 无远程服务器时，自动降级为本地存储并给出友好提示
4. 跨设备功能（设备传传 / cross_share）**保持现状**，仍走服务器 + OSS
5. 配置可**迁移**（本地 ↔ 服务器），迁移时用目标端密钥重加密

### 1.3 非目标

- 不改变任何工具的业务功能（连接测试、SQL 执行、Pod 查询等行为不变）
- 不改动 `cross_share`（设备传传）任何代码
- 不实现配置的多机同步（同步需要服务器中转，与「不上传」目标冲突）

---

## 2. 关键约束（实测结论）

### 2.1 现有 SQL 无法直接跑 SQLite

本项目存储层使用 **psycopg2 原生 SQL**，实测以下写法在 SQLite 3.50 下全部失败：

| 写法 | SQLite 结果 | 出现位置 |
|---|---|---|
| `%s` 占位符 | `OperationalError: near "%": syntax error` | **全项目通用** |
| `ILIKE` | `OperationalError: near "ILIKE": syntax error` | `database_tool_service.py:2023` |
| `NOW()` | `OperationalError: no such function: NOW` | `database_tool_service.py:180` |
| `ADD COLUMN IF NOT EXISTS` | `OperationalError: near "EXISTS": syntax error` | `k8s_tool_service.py:72` |

兼容的写法：`FALSE` 字面量、`BOOLEAN DEFAULT FALSE`。

**决策**：采用 SQLAlchemy Core 统一层（用户已选定），重写 4 个工具的配置 CRUD 查询，用 SQLAlchemy 的方言抽象消除 PG/SQLite 差异。

### 2.2 加密密钥当前存在数据库中

`EncryptionUtils._get_db_encryption_key()` 从 `system_settings` 表读取密钥，读不到才回退 `.env`。这意味着密钥跟随数据库走——本地模式下必须独立出来。

### 2.3 HOME 被覆盖

`backend/app/config/config.py:39` 在非桌面模式下执行 `os.environ["HOME"] = str(CACHE_DIR)`，进程内 `HOME` 是**假家目录**。本地数据目录必须基于 `REAL_HOME`（`config.py:21`）推导。

### 2.4 两种部署模式并存

- 桌面模式：`DESKTOP_MODE=1`（`backend/desktop_config.py`），PyInstaller 打包，数据目录随程序
- 服务器模式：当前 `backend/.env` 指向远程 PostgreSQL

设计需在两种模式下都可用。

---

## 3. 总体架构

```
┌────────────────────────────────────────────────────────────┐
│  前端（4 个工具的连接列表 / 新建 / 编辑弹窗）                │
│  存储位置选择器：● 本机保存   ○ 上传到服务器                 │
└───────────────────────┬────────────────────────────────────┘
                        │ REST
┌───────────────────────▼────────────────────────────────────┐
│  路由层 routes/{database,k8s,ssh,redis}_tool.py            │
│  （基本不变，仅注入 storage_location 参数）                  │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│  Service 层（database_tool_service 等）                     │
│  业务逻辑不变，配置读写改为委托 Repository                  │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│  ★ storage 层（新增）                                       │
│  locator.py    存储位置枚举 + 路由                          │
│  crypto.py     本地文件密钥加密器                           │
│  local_db.py   本地 SQLite engine + 幂等建表               │
│  remote_db.py  远程 PG engine                               │
│  repository.py Repository 接口 + 两套实现                   │
└───────────────┬──────────────────────────┬─────────────────┘
                │                          │
                ▼                          ▼
   ┌────────────────────┐    ┌──────────────────────────┐
   │ 本地 SQLite         │    │ 远程 PostgreSQL           │
   │ ~/.toolbox/         │    │ (用户自己配置的服务器)     │
   │   toolbox.db        │    │                           │
   │   encryption.key    │    │                           │
   └────────────────────┘    └──────────────────────────┘
      凭据永不离开本机            用户主动选择才上传
```

### 3.1 存储位置模型

新增枚举：

```python
class StorageLocation(str, Enum):
    LOCAL = "local"    # 本机 SQLite
    SERVER = "server"  # 远程 PostgreSQL
```

**两边同构**：本地 SQLite 与远程 PG 使用**相同的表结构和相同的列**，均新增 `storage_location` 列。

- 本地库的表只有 `storage_location='LOCAL'` 的行
- 服务器库的表只有 `storage_location='SERVER'` 的行
- 该列作为**双保险**：即使某个写操作漏了路由判断，目标库里的行也能被过滤掉，不会交叉污染

### 3.2 安全不变量

> `storage_location='LOCAL'` 的配置，其敏感字段在物理上不可能出现在远程 PostgreSQL 中。

保障方式（四重）：

1. **Repository 实例绑定存储位置**：`LocalConfigRepository` 只接受 `storage_location='LOCAL'`，`RemoteConfigRepository` 只接受 `'SERVER'`，传入不匹配即抛错（见 5.1）。这是**类型层面**的保障，不是运行时分支。
2. **写入路径隔离**：Service 层按用户选择 `get_repository(location)` 拿到对应实例，LOCAL 的写操作永远不会拿到远程 engine。
3. **列级归属标记**：两张库都有 `storage_location` 列，且**每个 Repository 只读写自己那一侧的行**——本地库查询恒带 `WHERE storage_location='LOCAL'`，远程库恒带 `WHERE storage_location='SERVER'`。
4. **密钥隔离**：本地库用本机文件密钥加密，远程库用服务器 `system_settings` 密钥加密，两把密钥物理隔离，无法互相解密——即便密文被复制到另一端也无法解密。

> ⚠️ 关键澄清：**「只过滤本侧」不等于「防止跨库读取」**。真正的保障来自 1、2、4 三层：写操作受 Repository 绑定约束（不可能写错地方），密钥隔离（密文搬过去也解不开）。第 3 层的 `storage_location` 过滤是**兜底**（防止历史脏数据或人工 SQL 造成的越界行出现在错误列表中），不是主要保障。

### 3.3 无远程服务器的降级

后端暴露 `GET /api/storage/status`：

```json
{
  "server_available": false,
  "server_reason": "DATABASE_URL 未配置为 PostgreSQL 或连接不可达",
  "local_path": "C:\\Users\\xxx\\.toolbox\\toolbox.db"
}
```

判定规则：
- `DATABASE_URL` 以 `sqlite://` 开头 → `server_available=False`
- 以 `postgresql://` 开头但连接探测失败 → `server_available=False`（附原因）
- 连接正常 → `server_available=True`

前端行为：
- `server_available=false` → **隐藏**「上传到服务器」选项，顶部显示友好提示条
- 新建配置默认 `storage_location='LOCAL'`
- 已有 SERVER 配置仍可查看/编辑（服务端数据依然在），但迁移到本地需用户手动触发

### 3.4 与主应用数据库的关系（重要区分）

本设计的「本地 SQLite」是**专用的本地凭据库**（`~/.toolbox/toolbox.db`），**不是**主应用数据库 `settings.DATABASE_URL`（当前指向远程 PG `39.107.229.30`）。

因此在**服务器部署**下，现状是「主应用在远程 PG + 另有本地 SQLite 存凭据」的**双库并存**：

| 库 | 内容 | 是否本设计范围 |
|---|---|---|
| 主应用库（`settings.DATABASE_URL`） | 用户、Token 用量、课程、设备传传消息等 | ❌ 不动 |
| 本地凭据库（`~/.toolbox/toolbox.db`） | 4 个工具的配置 + 关联历史 | ✅ 本设计 |

**「远程服务器存储」指的是主应用库**——当 `DATABASE_URL` 指向 PG 且可达时，用户可以把配置存到主应用库（与现状行为一致）；不可达或为 sqlite 时，只能存本地。

> ⚠️ **桌面模式的特殊情况**：`desktop_config.py` 加载的 `.env` 默认 `DATABASE_URL=sqlite:///./data/tools.db`（见 `backend/.env.example:12`），即桌面版主应用库本身就是 SQLite。此时：
> - `server_available=False`（符合预期：桌面版本就没有远程服务器）
> - 但主应用库是 SQLite，**不能直接当「远程服务器库」用**——它的 SQL 方言与本地专用库不同
> - 故判定规则细化：`DATABASE_URL` 为 sqlite 时，主应用库**既不是**本地专用库**也不是**远程服务器库，`server_available=False`，所有凭据只能存本地专用库

这一区分必须在实现中明确，避免把主应用库误当作远程存储目标。

---

## 4. 本地存储实现

### 4.1 目录与文件

```
~/.toolbox/                     ← 基于 REAL_HOME 推导
├── toolbox.db                  ← 本地 SQLite
├── encryption.key              ← 本地加密密钥（0600 权限）
└── logs/                        （可选）
```

权限：
- Unix/macOS：`chmod 600`（文件）/ `chmod 700`（目录）
- Windows：继承用户目录 ACL（Windows 无 POSIX 权限位，依赖 NTFS ACL + 目录位于用户 profile 下）

密钥生成：首次使用时 `secrets.token_hex(32)` 生成并原子写入（先写临时文件再 rename，避免半写文件）。

### 4.2 本地加密器

与服务器 `EncryptionUtils` **完全分离**（不能复用——服务器密钥在数据库里）：

```python
class LocalEncryption:
    """本地文件密钥加密器。密钥来自 ~/.toolbox/encryption.key，不入库、不上传。"""
    @classmethod
    def encrypt(cls, plain_text: str) -> str: ...
    @classmethod
    def decrypt(cls, encrypted_text: str) -> str: ...
```

使用同样的 Fernet 算法（便于理解与迁移），但密钥来源不同：
- 服务器 `EncryptionUtils`：密钥来自 `system_settings` 表
- 本地 `LocalEncryption`：密钥来自本机文件

**密钥文件生成（原子写入，跨平台）**：

```python
def _write_key_atomic(path: Path, key: str) -> None:
    """原子写入密钥文件。Windows 上 os.rename 不能覆盖已存在文件，需先删除目标。"""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(key, encoding="utf-8")
    if os.name == "nt" and path.exists():
        path.unlink()          # Windows: rename 不能覆盖已存在目标
    os.rename(tmp, path)       # POSIX: rename 本身即原子覆盖
    path.chmod(0o600)          # POSIX 收紧权限；Windows 上为 no-op
```

> ⚠️ Windows 差异：`os.rename()` 在 Windows 上对**已存在的目标文件**会抛 `FileExistsError`（POSIX 是静默覆盖）。故需按 `os.name` 分支处理。`path.chmod(0o600)` 在 Windows 上不生效（Windows 无 POSIX 权限位），依赖用户 profile 目录的 NTFS ACL 保护。

### 4.3 本地引擎创建时机

**延迟创建（lazy），不在应用启动时建**：本地 SQLite engine 在**首次需要访问本地库时**才创建并建表。

理由：
- 服务器模式下，绝大多数用户只用远程存储，不该为每人都在启动时创建一个空 SQLite 文件
- 避免本地磁盘不可写（如只读部署目录）导致整个应用启动失败
- 本地库创建失败时，只影响本地存储路径，远程存储功能仍可用

失败行为：
- 首次访问本地库失败 → 抛明确异常（「本地存储不可用：{原因}」），**不静默降级到内存库**（内存库会导致用户以为配置已保存，重启即丢失）

### 4.3 本地库建表

**DDL 来源不统一**（实测确认），本地库建表必须按各自来源分别对齐：

| 表 | 服务器侧 DDL 来源 | 本地库处理 |
|---|---|---|
| `db_configs` | `backend/app/db/init_db_tool.sql:12`（**SQL 文件**，非代码） | 需同步修改该 SQL 文件 |
| `redis_configs` | `backend/app/services/redis_tool_service.py:34`（代码内 `_ensure_table`） | 复刻代码内 DDL |
| `ssh_configs` | `backend/app/services/ssh_tool_service.py:38`（代码内 `_ensure_table`） | 复刻代码内 DDL |
| `k8s_connections` | `backend/app/services/k8s_tool_service.py:38`（代码内 `_ensure_table`） | 复刻代码内 DDL |

本地 `db_configs` DDL（SQLite 兼容版，对齐 `init_db_tool.sql`）：

```sql
CREATE TABLE IF NOT EXISTS db_configs (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    alias VARCHAR(32) NOT NULL,
    db_type VARCHAR(20) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    database_name VARCHAR(255),
    username VARCHAR(100) NOT NULL,
    password_encrypted TEXT NOT NULL,
    environment VARCHAR(20),
    group_name VARCHAR(50),
    charset VARCHAR(50),
    connect_timeout INT DEFAULT 10,
    max_pool_size INT DEFAULT 10,
    ssl_mode VARCHAR(20),
    ssl_cert_path TEXT,
    extra_config TEXT,                          -- PG 是 JSON，SQLite 用 TEXT
    is_active BOOLEAN DEFAULT TRUE,
    last_connected_at TIMESTAMP,
    storage_location VARCHAR(16) NOT NULL DEFAULT 'LOCAL',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);
```

差异处理（相对 PG）：

| PG 写法 | SQLite 处理 | 依据 |
|---|---|---|
| `%s` 占位符 | 由 SQLAlchemy Core 自动转方言（PG `%s` / SQLite `?`） | 实测 `%s` 直接语法错误 |
| `NOW()` | `CURRENT_TIMESTAMP`（SQLite 原生支持） | 实测 `NOW()` 无此函数 |
| `ILIKE` | SQLAlchemy `.ilike()` 自动降级为 `LIKE` | 实测 `ILIKE` 语法错误 |
| `ADD COLUMN IF NOT EXISTS` | 先 `PRAGMA table_info` 探测再 `ALTER TABLE ADD COLUMN` | 实测语法错误 |
| `JSON` 列类型 | 声明为 `TEXT` | **实测 SQLite 对 `JSON` 声明类型有 TEXT 亲和性**，JSON 字符串原样存储不损坏；仍统一用 TEXT 更清晰 |
| `SERIAL` / `UUID` | `VARCHAR` / `TEXT` | SQLite 无自增/UUID 类型 |

> SQLite 的 `JSON` 亲和性实测结论：声明 `x JSON` 时 `typeof(x)` 返回 `text`，`{"a": 1}` 原样保留，未被数值化。故 PG 的 `JSON` 列在本地库用 `TEXT` 声明是安全的。

其余三张表按各自 `_ensure_table` 的 DDL 复刻，同样加 `storage_location` 列。

### 4.3.1 关联表必须同步建（否则本地执行历史无法落库）

`db_configs` 有 4 张关联表，其中 `sql_execution_history` 对 `db_configs` 有**外键依赖**（`FOREIGN KEY (db_config_id) REFERENCES db_configs(id) ON DELETE CASCADE`）。本地库必须一并建这些表，否则数据库工具的「执行历史」功能在本地模式下会写入失败。

| 表 | 外键依赖 | 缺失后果 |
|---|---|---|
| `sql_execution_history` | `db_config_id → db_configs.id` | **执行历史写入失败**（外键目标不存在） |
| `db_scan_history` | `db_config_id → db_configs.id` | 扫描历史写入失败 |
| `table_schema_cache` | `db_config_id → db_configs.id` | 表结构缓存失效（退化为每次实时查询，不致命） |
| `user_display_preferences` | `user_id → users.user_id` | 显示偏好无法保存 |

**`users` 表**：本地库也需要（`db_configs.user_id` 的外键目标）。本地库的 `users` 表**只建结构、不插数据**——本机用户以 `user_id` 字符串标识，`FOREIGN KEY` 约束在 SQLite 默认**关闭**（`PRAGMA foreign_keys` 默认 OFF），因此不会因本地无对应 user 行而插入失败。

> ⚠️ SQLite 的外键默认不启用。这意味着本地库不会有外键级联删除——删除配置时需**显式**清理关联的历史记录（服务端 PG 有 `ON DELETE CASCADE` 自动清理）。实现时本地 Repository 的 `delete` 需手动删除 `sql_execution_history` / `db_scan_history` / `table_schema_cache` 中该 `db_config_id` 的行。

`db_scan_history` / `table_schema_cache` / `user_display_preferences` 的 DDL 见 `backend/app/db/init_db_tool.sql:42-136`，PG 的 `JSON` 列在本地用 `TEXT`（实测 SQLite 对 `JSON` 声明类型有 TEXT 亲和性，JSON 字符串原样存储不损坏）。

### 4.4 表结构迁移（服务器侧）

远程 PG 需要给 4 张表加 `storage_location` 列，**幂等且可重复执行**：

```sql
ALTER TABLE db_configs ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';
```

现有行的默认值为 `'SERVER'`——保持现有行为不变（历史数据仍在服务器），这是安全的向后兼容。

> 注：`ADD COLUMN IF NOT EXISTS` 在 PG 9.6+ 支持，项目当前 PG 版本满足。

**DDL 分两处维护**（因来源不统一，见 4.3）：

| 表 | 迁移语句位置 |
|---|---|
| `db_configs` | `backend/app/db/init_db_tool.sql`（表定义处补列）**+** 独立迁移脚本 |
| `redis_configs` / `ssh_configs` / `k8s_connections` | 各 Service 的 `_ensure_table()` 内补列 |

**加列实现必须分方言**（PG 与 SQLite 都不通用的写法）：封装为 `storage/ddl.py` 的辅助函数。

```python
# backend/app/storage/ddl.py
def column_exists(conn, table: str, column: str) -> bool:
    """判断列是否存在（PG / SQLite 双方言）。"""
    dialect = conn.dialect.name if hasattr(conn, "dialect") else _detect(conn)
    if dialect == "postgresql":
        row = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c LIMIT 1"
        ), {"t": table, "c": column}).first()
    else:  # sqlite
        cols = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        row = next((r for r in cols if r[1] == column), None)
    return row is not None


def ensure_column(conn, table: str, column: str, ddl: str) -> None:
    """幂等加列：已存在则跳过。"""
    if column_exists(conn, table, column):
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
```

> ⚠️ 不得使用 `ADD COLUMN IF NOT EXISTS`——PG 9.6+ 支持但 **SQLite 不支持**（实测语法错误）。统一走 `column_exists` 探测式写法，两端通用且可重复执行。

**回滚 SQL**（加列可回滚；数据迁移不可逆，需人工介入）：

```sql
-- 回滚：删除 storage_location 列（PG）
ALTER TABLE db_configs DROP COLUMN IF EXISTS storage_location;
ALTER TABLE redis_configs DROP COLUMN IF EXISTS storage_location;
ALTER TABLE ssh_configs DROP COLUMN IF EXISTS storage_location;
ALTER TABLE k8s_connections DROP COLUMN IF EXISTS storage_location;
```

> ⚠️ **回滚前必须先处理数据**：若已有 `storage_location='LOCAL'` 的行存在于服务器库（正常流程下不会发生，因 LOCAL 行只写本地库），回滚会丢失归属标记。回滚脚本执行前应先校验：
> ```sql
> SELECT COUNT(*) FROM db_configs WHERE storage_location <> 'SERVER';
> ```
> 期望结果为 0；非 0 则中止回滚，先人工处理。

**幂等性要求**：加列逻辑必须可重复执行且不报错——这是项目「SQL 可重复执行且不影响现有数据」规则的硬性要求。

---

## 5. Repository 统一层

### 5.1 接口

```python
class ConfigRepository(Protocol):
    """配置仓储接口。本地 SQLite 与远程 PostgreSQL 两套实现行为一致。"""

    def list(self, user_id: str) -> list[dict]: ...
    def get(self, config_id: str, user_id: str) -> dict | None: ...
    def create(self, user_id: str, data: dict, storage_location: StorageLocation) -> dict: ...
    def update(self, config_id: str, user_id: str, data: dict,
               storage_location: StorageLocation) -> dict | None: ...
    def delete(self, config_id: str, user_id: str) -> bool: ...
    def get_with_secret(self, config_id: str, user_id: str) -> dict | None: ...
    def list_all_locations(self, user_id: str) -> list[dict]:
        """跨本地+服务器列出（用于迁移与统一视图）"""
```

**`storage_location` 契约约定**（关键）：

- `create` / `update` 的 `storage_location` 参数由**调用方**（Service 层）根据用户选择传入
- Repository 实例自身**绑定**一个存储位置（`LocalConfigRepository` 恒为 LOCAL，`RemoteConfigRepository` 恒为 SERVER）
- **一致性校验**（防越界写入，强制）：Repository 在 `create`/`update` 时校验传入的 `storage_location` 与自身绑定位置一致，不一致则抛错
  ```python
  def _assert_location(self, storage_location: StorageLocation) -> None:
      if storage_location is not self.location:
          raise ValueError(
              f"存储位置不匹配：{self.location} 仓储不接受 {storage_location}"
          )
  ```
  这样「LOCAL 的数据被写进远程库」在类型层面就不可能发生——写操作必须拿到 `LocalConfigRepository` 实例，而它只接受 `LOCAL`。

- **调用方与校验的分工**：Service 层负责**选择**正确的 Repository（`get_repository(location)`），Repository 负责**校验**传入值与自己绑定的一致性。两者是互补的：前者防「拿错仓储」，后者防「传错位置值」。

- `get_with_secret` 单独拆出，因为**只有连接测试/实际连接时**才需要解密出明文；列表接口只返回脱敏数据（与现状一致）。

### 5.2 实现方式

用 **SQLAlchemy Core**（非 ORM）——保持与现有手写 SQL 的形态接近，同时由 SQLAlchemy 处理方言差异：

```python
from sqlalchemy import Table, Column, MetaData, String, Integer, Boolean, Text, DateTime, select, insert, update, delete

# metadata 不绑定 engine —— 本地与远程是两套独立 engine，
# 建表由各自的 local_db / remote_db 模块显式调用 metadata.create_all(engine) 完成。
metadata = MetaData()

db_configs = Table(
    "db_configs", metadata,
    Column("id", String(64), primary_key=True),
    # 注意：不在 Column 上设 default —— 同一份 Table 定义被本地/远程两个实现共用，
    # 而两者的默认值不同（本地 'LOCAL' / 远程 'SERVER'）。
    # storage_location 的取值由 Repository 实例绑定位置统一注入（见 _assert_location）。
    Column("storage_location", String(16), nullable=False),
    # ...
)
```

> ⚠️ **`storage_location` 的默认值必须由 Repository 注入，不能写在 Column 上**：`Table` 定义被本地/远程两套实现共用，写死 `default="SERVER"` 会导致本地库新行被标成 SERVER（安全不变量破坏）；写死 `default="LOCAL"` 则会让远程库出现 LOCAL 行。正确做法是 Repository 在 insert 时显式传入自身绑定的位置值。

> ⚠️ **`metadata` 不绑定 engine**：`MetaData()` 无 engine 参数时不会自动建表。本地库与远程库各自在初始化时显式调用 `metadata.create_all(bind=local_engine)` / `metadata.create_all(bind=remote_engine)`——但**远程库的表已由既有 SQL/Service 建立**，故远程侧只需探测式加列（见 4.4），不调用 `create_all`（避免与既有表定义冲突）。

查询用 `select()` / `insert()` / `update()` / `delete()` 构造，参数绑定自动适配方言（PG 用 `%s`，SQLite 用 `?`，由 SQLAlchemy 处理）。

`ILIKE` 场景（`database_tool_service.py:2023` 的表名模糊搜索）改写为 SQLAlchemy 表达式：

```python
# 原来（PG only）
cursor.execute("... WHERE table_name ILIKE :keyword", {...})

# 改写后（跨方言）
stmt = select(t).where(t.c.table_name.ilike(f"%{keyword}%"))
```

SQLAlchemy 的 `.ilike()` 会自动在 SQLite 上降级为 `LIKE`（SQLite 的 LIKE 默认对 ASCII 大小写不敏感）。

### 5.3 路由

```python
def get_repository(storage_location: StorageLocation) -> ConfigRepository:
    """按存储位置返回对应实现。"""
    if storage_location is StorageLocation.LOCAL:
        return LocalConfigRepository(...)
    return RemoteConfigRepository(...)
```

### 5.5 别名唯一性的跨库处理

现状：`db_configs` 的别名唯一性检查是**单库内**的（`database_tool_service.py:725`）：

```sql
SELECT id FROM db_configs WHERE user_id = %s AND alias = %s AND deleted = FALSE
```

改造后配置可能分布在**两个库**里，若只查本侧，会出现「本地已有 `prod-db`、服务器也能建 `prod-db`」，用户看到两个同名连接，容易误操作。

**决策：别名唯一性按「用户 + 工具」维度跨库检查**。

```python
def _assert_alias_unique(user_id: str, alias: str, tool: str,
                         exclude_config_id: str | None = None) -> None:
    """检查别名唯一性 —— 必须跨本地与服务器两侧检查。"""
    for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
        repo = get_repository(location, tool)
        existing = repo.find_by_alias(user_id, alias)
        if existing and existing["id"] != exclude_config_id:
            raise ValueError(f"别名 '{alias}' 已存在（存储位置：{location.value}）")
```

**性能考量**：跨库检查意味着每次创建/改名都要查两次库。本地 SQLite 查询极快，远程 PG 是既有行为（原本就查一次），实际开销可接受。

**迁移时的别名冲突**：把配置从服务器搬到本地时，若本地已存在同名别名 → **迁移失败并提示**（不自动改名，避免用户困惑）。用户需先改名或删除本地同名配置。

> 注：SSH 工具的 `alias` 唯一性检查在 `ssh_tool_service.py` 中同理处理；K8s 用 `name` 字段（无唯一约束），Redis 用 `alias`（同理处理）。

### 5.6 改造范围

需要从 psycopg2 原生 SQL 改为 Repository 的方法（**仅配置 CRUD**，业务查询如 Pod 列表不动）：

| Service | 需要改造的配置 CRUD 方法 |
|---|---|
| `database_tool_service.py` | `get_all_configs`、`get_config`、`_get_config_with_password`、`create_config`、`update_config`、`delete_config`、`_re_encrypt_password` |
| `k8s_tool_service.py` | `get_configs`、`create_config`、`create_from_kubeconfig`、`update_config`、`update_config_auth`、`delete_config`、`get_config_by_id`、`update_sort_order`、`update_test_result` |
| `ssh_tool_service.py` | `get_configs`、`get_config`、`create_config`、`update_config`、`delete_config`、`_get_column_map` |
| `redis_tool_service.py` | `get_configs`、`get_config`、`create_config`、`update_config`、`delete_config`、`_get_config_with_password` |

各 Service 另需改造：`_ensure_table()` 的建表/加列逻辑（分方言，见 4.4）。

> 业务逻辑方法（连接测试、SQL 执行、Redis 命令、K8s 资源查询）保持不变，仅把「取配置 + 解密」改为调用 `repository.get_with_secret()`。

---

## 6. 加密与迁移

### 6.1 迁移时的重加密

配置从服务器搬到本地（或反之）时，**必须重加密**，因为两端密钥不同：

```
服务器密文 --[服务器密钥解密]--> 明文 --[本地密钥加密]--> 本地密文
```

**迁移执行顺序（防重复记录）**：

必须**先写目标端、后删源端**，且写目标端与删源端之间要能识别「目标端已写入但源端删除失败」的中间态：

```
1. 读源行（含密文）
2. 用源端密钥解密敏感列 → 明文（仅内存，不落盘、不打日志）
3. 用目标端密钥加密 → 目标端密文
4. 目标端事务：删除同 id 旧行（若有）→ 插入新行 → COMMIT
5. 源端事务：删除源行 → COMMIT
6. 返回成功
```

**失败处理矩阵**：

| 失败点 | 状态 | 处理 |
|---|---|---|
| 第 2 步解密失败 | 源行完好，目标端未动 | 中止迁移，返回「凭据解密失败」，源行保留 |
| 第 4 步写入失败 | 源行完好，目标端已回滚 | 中止迁移，返回错误，源行保留 |
| 第 5 步删除源行失败 | **两端同时存在同 id 配置** | 见下方「重复记录处理」 |

**重复记录处理（中间态）**：第 5 步失败会导致同一 id 在两端都存在。此时：

- **列表查询**：每个 Repository 只查自己那一侧的 `storage_location`，因此两端记录**不会同时出现在列表里**（用户看到的是本地那条）
- **再次迁移**：用户再次触发「移到服务器」时，第 4 步会先删除目标端同 id 旧行再插入，实现**自愈**
- **兜底清理**：提供运维接口 `DELETE /api/{tool}/configs/{id}` 时，**同时删除两端同 id 记录**，避免残留

> 设计取舍：选择「先写后删」而非「先删后写」，因为先删后写在第 4 步失败时会**丢失配置**（不可接受）。先写后删的最坏情况是短暂重复，而重复可通过再次迁移自愈，且列表查询隔离保证用户无感。

**明文安全要求（强制）**：

- 迁移/加解密过程中的明文**只在内存变量与栈上**，不写磁盘、不进日志
- 异常堆栈不得包含凭据明文
- `logger` 调用不得传入敏感字段
- 前端响应体中，列表接口永不返回明文密码/token/私钥（与现状一致：仅 `has_auth_data` 之类的布尔标记）

---

## 7. 迁移接口设计

### 7.1 单条迁移

```
POST /api/{tool}/configs/{config_id}/migrate
Body: { "target": "local" | "server" }
Response: { "success": bool, "storage_location": str, "message": str }
```

行为：
- 校验目标库可用性（服务器不可用时，`target='server'` 返回 400 并给出友好原因）
- 找到源行 → 解密 → 重加密 → 写入目标 → 删除源行（顺序见 6.1）
- **幂等处理**：写入目标前先删除目标端同 id 旧行（避免主键冲突）。若删除目标旧行失败 → 中止迁移，返回错误，源行保留（不进入「两端重复」中间态）
- 若源端找不到该 id（可能已被迁移过、或已在中间态）：返回 404 并说明「该配置不在源端存储中，请检查目标端」

批量迁移对每条配置独立执行上述流程，**单条失败不中断整体**。

### 7.2 批量迁移

```
POST /api/{tool}/configs/migrate-all
Body: { "target": "local" | "server" }
Response: { "success": bool, "migrated": int, "failed": int, "errors": [...] }
```

行为：遍历该工具当前用户的全部配置，逐条迁移，**单条失败不中断整体**，失败项收集到 `errors` 返回。

> 幂等性：接口重复执行安全（每次执行都是「当前在源端的都搬走」）。

---

## 8. 前端设计

### 8.1 存储位置选择器

新建/编辑配置弹窗中增加一个二选一：

```
存储位置
┌─────────────────────────────────┐
│ ◉ 仅保存在本机                   │  ← 推荐
│   凭据不离开本机，更安全          │
├─────────────────────────────────┤
│ ○ 上传到服务器                   │
│   便于多设备访问                  │
└─────────────────────────────────┘
```

- 默认选中「仅保存在本机」
- `server_available=false` 时：隐藏「上传到服务器」整项，只显示本机选项 + 说明文字
- 提交时随表单带上 `storage_location`

### 8.2 连接列表

每条配置旁显示一个**位置徽章**：

| 徽章 | 含义 |
|---|---|
| 🔒 本机 | `storage_location='LOCAL'` |
| ☁️ 服务器 | `storage_location='SERVER'` |

悬停提示说明该配置的凭据存放在哪里。

### 8.3 迁移操作

- 单条：配置行 hover 时出现「移到本机」/「移到服务器」图标按钮
- 批量：工具栏「全部移到本机」/「全部移到服务器」按钮，带确认弹窗

### 8.4 友好提示

`server_available=false` 时，在 4 个工具的连接列表顶部显示提示条：

```
ℹ️ 当前未配置远程服务器，所有凭据将仅保存在本机
   数据库文件：C:\Users\xxx\.toolbox\toolbox.db
   [查看存储设置]  [清空本地数据]
```

### 8.5 清空本地数据

提供管理入口（建议放在「存储设置」弹窗），行为定义：

| 项 | 行为 |
|---|---|
| 清空范围 | 本地 SQLite 中 4 个工具的**全部配置与关联历史**（`db_configs` / `k8s_connections` / `ssh_configs` / `redis_configs` / `sql_execution_history` / `db_scan_history` / `table_schema_cache` / `user_display_preferences`） |
| 是否保留密钥文件 | **保留** `encryption.key`。理由：密钥是「本机身份」，清空数据不应更换密钥——否则其他工具（若未来共享该密钥）的密文会全部失效 |
| 是否可撤销 | 不可撤销。需二次确认弹窗，明确列出被清除的记录数 |
| 失败处理 | 整个清空在**单个事务**内完成，任一步失败则整体回滚，不留半清状态 |

**与「迁移」的边界**：清空本地数据只影响本地库，**不触碰服务器库**。若用户有 SERVER 配置，清空本地后它们仍在服务器，可正常显示。

**密钥丢失的处理**：若 `encryption.key` 被删除而本地库还在，已存密文**永久无法解密**（Fernet 密钥不可恢复）。此时：
- 本地配置列表仍可显示元信息（别名、主机等非敏感字段），但连接测试会明确报错「本地加密密钥不可用，请检查 ~/.toolbox/encryption.key」
- 提供「重置本地库」操作：删除本地 SQLite 文件并重建（会丢失本地全部配置，需确认）
- **不提供任何假解密或兜底明文**（项目规则：禁止 Mock 与兜底）

---

## 9. 安全考量

| 威胁 | 缓解措施 |
|---|---|
| 凭据明文落盘 | 本地 SQLite 中敏感列一律为密文；本地密钥文件本身 0600 |
| 密钥随数据库走 | 本地密钥独立存文件，与 `system_settings`（服务器）完全隔离 |
| 迁移过程泄露明文 | 明文仅在内存；不写日志；异常不含凭据 |
| 误把 LOCAL 配置传到服务器 | 四重保障：Repository 位置绑定校验 + 写入路径隔离 + 查询过滤 + 密钥隔离（详见 3.2） |
| 本地库文件被他人读取 | 文件位于用户 profile 下；Unix/Mac 额外收紧目录权限 |
| 日志泄露 | 审计日志只记录 `config_id`/`alias`/`storage_location`，不记录任何敏感字段 |
| 前端拿到明文 | 列表接口只返回脱敏字段；仅连接测试等必要场景在服务端内部解密 |
| 密文被复制到另一端 | 两端密钥物理隔离，密文即便被复制也无法用对方密钥解密 |
| 两端出现同名配置 | 别名唯一性跨库检查（见 5.5），迁移撞名时明确失败不静默覆盖 |

---

## 10. 错误处理

| 场景 | 行为 |
|---|---|
| 无远程服务器时请求 `target='server'` | HTTP 400 + 友好文案「未配置远程服务器，无法上传」 |
| 本地库初始化失败 | **首次访问本地库时**抛明确异常（不静默降级到内存库，避免用户以为已保存） |
| 本地密钥文件损坏/丢失 | 已存密文无法解密 → 明确报错「本地加密密钥不可用，请检查 ~/.toolbox/encryption.key」；**不提供假解密** |
| 迁移中解密失败 | 中止该条迁移，保留源行，返回失败原因 |
| 批量迁移部分失败 | 成功项已迁移，失败项保留原地，`errors` 数组逐条说明 |
| 迁移时目标端已有同名配置 | 迁移失败并提示「目标端已存在同名配置，请先改名或删除」，**不自动改名、不静默覆盖** |
| 用户切换存储位置后配置失效 | 因重加密保证密文与目标库密钥匹配，不会出现此问题 |
| 本地磁盘不可写 | 本地库创建失败 → 明确报错；远程存储功能不受影响（本地库是延迟创建的） |

---

## 11. 测试策略

### 11.1 后端

| 测试 | 覆盖点 |
|---|---|
| `test_local_db.py` | 本地建表幂等（重复执行不报错）、表结构与 PG 同构 |
| `test_local_encryption.py` | 加解密往返、密钥文件生成与权限、缺失密钥行为 |
| `test_storage_locator.py` | `server_available` 判定（sqlite URL / PG 不可达 / PG 可达） |
| `test_config_repository.py` | Repository 在本地 SQLite 与远程 PG 上行为一致（同一套用例参数化） |
| `test_config_migration.py` | 单条迁移往返、重加密正确性、幂等、失败回滚、批量部分失败 |

**关键测试设计**：Repository 的一致性测试用**同一组用例**跑两个实现（pytest 参数化），确保本地/远程行为不漂移。

**跨库隔离断言（核心安全不变量，必须有）**：

| 测试 | 断言 |
|---|---|
| `test_local_config_not_in_server_db` | 写入一条 LOCAL 配置后，直接查询远程 PG 的 `db_configs` 表，**断言查不到该 id** |
| `test_server_config_not_in_local_db` | 写入一条 SERVER 配置后，直接查询本地 SQLite，**断言查不到该 id** |
| `test_local_secret_not_decryptable_by_server_key` | 本地密文用服务器密钥 `EncryptionUtils.decrypt` 解密，**断言抛异常** |
| `test_repository_rejects_wrong_location` | 用 `LocalConfigRepository.create(..., storage_location=SERVER)`，**断言抛错** |
| `test_migration_moves_row_exclusively` | 迁移后，源端查不到该 id、目标端能查到，且**两端不同时存在** |

> 这 5 条断言是本设计的**安全回归底线**。任何改动若导致其中一条失败，即视为破坏安全不变量，必须拒绝合并。

### 11.2 前端

| 测试文件 | 覆盖点 |
|---|---|
| `components/Tools/DatabaseTool/__tests__/StorageLocationSelector.test.tsx` | 默认选本机、服务器不可用时隐藏「上传到服务器」选项、提交时带 `storage_location` |
| `components/Tools/K8sTool/__tests__/StorageLocationSelector.test.tsx` | 同上（K8s 版） |
| `components/Tools/DatabaseTool/__tests__/ConnectionListBadge.test.tsx` | LOCAL/SERVER 徽章正确渲染 |
| `components/Tools/K8sTool/__tests__/ConnectionListBadge.test.tsx` | 同上（K8s 版） |
| `components/Tools/DatabaseTool/__tests__/MigrateButton.test.tsx` | 单条/批量迁移触发、确认弹窗、成功/失败提示 |
| `components/Common/__tests__/StorageNoticeBar.test.tsx` | 无服务器时显示提示条、含本地库路径 |

> 4 个工具的组件结构相似但**不共用**（各自有独立的连接列表实现），故测试按工具分文件编写；共享的存储位置选择器与提示条组件应抽到 `components/Common/` 并只写一份测试。

### 11.3 验收

按项目「功能完成浏览器强制验收规则」：真实浏览器走完
「新建配置（选本机）→ 保存 → 验证服务端 PG 中无此行 → 列表显示本机徽章 → 迁移到服务器 → 验证服务端 PG 出现该行且密文不同 → 迁移回本机」全流程，Console 无错误。

---

## 12. 实施顺序（建议）

| # | 步骤 | 涉及文件 | 产出 |
|---|---|---|---|
| 1 | 存储抽象层骨架 | `backend/app/storage/{__init__,locator,ddl}.py` | `StorageLocation` 枚举、`get_repository()` 路由、`column_exists()` 辅助 |
| 2 | 本地加密 | `backend/app/storage/crypto.py` | `LocalEncryption` + 密钥文件生成（含 Windows rename 分支） |
| 3 | 本地库 | `backend/app/storage/local_db.py` | 延迟创建的 SQLite engine + 5 张表幂等建表 + 4 张关联表 |
| 4 | Repository 实现 | `backend/app/storage/repository.py` | SQLAlchemy Core `Table` 定义 + 本地/远程两套实现 |
| 5 | **服务器侧表结构加列** | ⚠️ **两处来源**：<br>• `backend/app/db/init_db_tool.sql`（`db_configs`）<br>• `k8s_tool_service.py` / `ssh_tool_service.py` / `redis_tool_service.py` 各自的 `_ensure_table()` | 4 张表加 `storage_location` 列（探测式，幂等） |
| 6 | 改造数据库工具 | `database_tool_service.py` | 配置 CRUD 走 Repository，其余业务逻辑不变 |
| 7 | 改造 K8s 工具 | `k8s_tool_service.py` | 同上 |
| 8 | 改造 SSH 工具 | `ssh_tool_service.py` | 同上 |
| 9 | 改造 Redis 工具 | `redis_tool_service.py` | 同上 |
| 10 | 迁移接口 | `backend/app/routes/storage.py`（新）+ 各工具路由挂载 | 单条 + 批量迁移，含重加密 |
| 11 | 存储状态接口 | `GET /api/storage/status` | `server_available` / `server_reason` / `local_path` |
| 12 | 前端：存储位置选择器 | 4 个工具的新建/编辑弹窗 | 默认选本机、服务器不可用时隐藏选项 |
| 13 | 前端：徽章 + 迁移按钮 | 4 个工具的连接列表 | 🔒本机 / ☁️服务器 徽章、单条+批量迁移 |
| 14 | 前端：提示条 + 存储设置 | 连接列表顶部、设置弹窗 | 无服务器提示、清空本地数据入口 |
| 15 | 端到端验收 | — | 浏览器全流程 + 安全验证（服务端 PG 无 LOCAL 行） |

> ⚠️ 第 5 步涉及**两个不同的 DDL 来源**（1 个 SQL 文件 + 3 个 Service 代码），实施时须逐一核对，漏改会导致该工具在本地模式下无法建表。

> 步骤 6–9 建议**逐工具改造并逐个验收**，不要 4 个一起改——每步都可独立验证，减少回归定位成本。

---

## 13. 明确不做的事

- ❌ 不改动 `cross_share`（设备传传）任何代码
- ❌ 不实现本地配置的自动同步/多机同步
- ❌ 不改变任何工具的业务行为
- ❌ 不做「双库实时同步」——存储位置是互斥的，配置只存在于其中一侧
- ❌ 不把服务器密钥机制改成本地文件密钥（服务器侧保持现状，避免影响多实例部署）
