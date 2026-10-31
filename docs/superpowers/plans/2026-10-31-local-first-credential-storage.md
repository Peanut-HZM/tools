# 凭据本地化存储 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让数据库/K8s/SSH/Redis 四个工具的连接配置可逐条选择保存在本机 SQLite（凭据不离开本机）或服务器 PostgreSQL，并支持两者之间安全迁移。

**Architecture:** 新增 `backend/app/storage/` 抽象层，用 SQLAlchemy Core 统一本地 SQLite 与远程 PostgreSQL 的配置读写；每条配置带 `storage_location` 列标记归属；本地库用独立文件密钥加密，服务器库沿用现有 `EncryptionUtils`。Service 层的配置 CRUD 改为委托 Repository，业务逻辑（连接测试、SQL 执行、资源查询）不变。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy 2.0 Core / SQLite 3.50 / Fernet (cryptography) / pytest / React 18 + TypeScript + Vitest

**设计文档:** `docs/superpowers/specs/2026-10-31-local-first-credential-storage-design.md`
**审查台账:** `docs/reviews/2026-10-31-local-first-credential-storage-review.md`

## Global Constraints

- **所有对话和代码注释使用中文**
- **禁止 Mock 与兜底**：真实问题必须如实暴露，禁止掩盖（尤其禁止解密失败时返回假明文）
- **禁止批量脚本修改代码**：所有代码修改必须逐个文件手动进行
- **SQL 可重复执行且不影响现有数据**：加列逻辑必须幂等
- **禁止 `git pull`（不带 `--rebase`）/ 禁止 `git merge` 更新本地分支**
- **提交只显式 `git add` 自己任务的文件，禁止 `git add .`**
- **用户目录访问必须使用真实家目录**：`config.py` 在非桌面模式下把 `HOME` 覆盖为 `backend/data/cache`，读用户家目录必须用 `REAL_HOME`（`backend/app/config/config.py:21`）
- **单测验收最小化**：只跑与本次变更直接相关的测试，不全量跑测
- **不得修改 `cross_share`（设备传传）任何代码**
- **本地 SQLite 路径**：`~/.toolbox/toolbox.db`（基于 `REAL_HOME` 推导）
- **本地加密密钥路径**：`~/.toolbox/encryption.key`
- **本地库默认 `storage_location` 值**：`'LOCAL'`；**服务器库默认值**：`'SERVER'`
- **`storage_location` 不得写在 SQLAlchemy `Column` 的 `default=` 上**（本地/远程共用同一份 Table 定义，默认值必须由 Repository 注入）

---

## File Structure

### 后端新建

| 文件 | 职责 |
|---|---|
| `backend/app/storage/__init__.py` | 包导出：`StorageLocation`、`get_repository`、`get_local_db_path` |
| `backend/app/storage/locator.py` | `StorageLocation` 枚举；`get_repository(location, tool)` 路由；`server_available()` 判定 |
| `backend/app/storage/paths.py` | 本地数据目录/库文件/密钥文件路径推导（基于 `REAL_HOME`） |
| `backend/app/storage/crypto.py` | `LocalEncryption`：本机文件密钥加密器（独立于服务器 `EncryptionUtils`） |
| `backend/app/storage/ddl.py` | `column_exists(conn, table, column)` / `ensure_column(...)` 双方言幂等加列 |
| `backend/app/storage/local_db.py` | 延迟创建的 SQLite engine + 幂等建表（5 张主表 + 4 张关联表） |
| `backend/app/storage/remote_db.py` | 远程 PG engine 适配（复用现有 `app.config.database`） |
| `backend/app/storage/repository.py` | SQLAlchemy Core `Table` 定义 + `LocalConfigRepository` / `RemoteConfigRepository` |
| `backend/app/storage/migration.py` | 迁移服务：解密 → 重加密 → 先写后删 |
| `backend/app/routes/storage.py` | `GET /api/storage/status` + 迁移接口（单条/批量） |

### 后端修改

| 文件 | 改动 |
|---|---|
| `backend/app/db/init_db_tool.sql` | `db_configs` 加 `storage_location` 列 |
| `backend/app/services/database_tool_service.py` | 配置 CRUD 走 Repository |
| `backend/app/services/k8s_tool_service.py` | 同上 + `_ensure_table` 幂等加列 |
| `backend/app/services/ssh_tool_service.py` | 同上 |
| `backend/app/services/redis_tool_service.py` | 同上 |
| `backend/app/models/database_tool_models.py` | 请求/响应模型加 `storage_location` |
| `backend/app/models/k8s_tool_models.py` | 同上 |
| `backend/app/models/ssh_tool_models.py` | 同上 |
| `backend/app/models/redis_tool_models.py` | 同上 |
| `backend/app/main.py` | 注册 `storage` 路由 |

### 前端新建

| 文件 | 职责 |
|---|---|
| `frontend/src/types/storage.ts` | `StorageLocation` 类型、`StorageStatus`、`MigrateResult` |
| `frontend/src/api/storageApi.ts` | `getStorageStatus()` / `migrateConfig()` / `migrateAllConfigs()` |
| `frontend/src/components/Common/StorageLocationSelector.tsx` | 存储位置选择器（默认本机；服务器不可用时隐藏上传选项） |
| `frontend/src/components/Common/StorageNoticeBar.tsx` | 无服务器提示条 |
| `frontend/src/components/Common/StorageLocationBadge.tsx` | 🔒本机 / ☁️服务器 徽章 |

### 前端修改

| 文件 | 改动 |
|---|---|
| `frontend/src/types/databaseTool.ts` | `DatabaseConfig` / `CreateDatabaseRequest` 加 `storage_location` |
| `frontend/src/components/Tools/K8sTool/types.ts` | 同上 |
| `frontend/src/api/databaseToolApi.ts` | 创建/更新请求带 `storage_location` |
| `frontend/src/api/k8sToolApi.ts` | 同上 |
| `frontend/src/api/sshToolApi.ts` | 同上 |
| `frontend/src/api/redisToolApi.ts` | 同上 |
| `frontend/src/components/Tools/DatabaseTool/components/CreateDatabaseDialog.tsx` | 接入选择器 |
| `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` | 徽章 + 迁移按钮 |
| `frontend/src/components/Tools/K8sTool/ConnectionModal.tsx` | 接入选择器 |
| `frontend/src/components/Tools/K8sTool/ConnectionList.tsx` | 徽章 + 迁移按钮 |

---

## 任务总览

| # | 任务 | 产出 |
|---|---|---|
| 1 | 存储路径与本地加密 | `paths.py` + `crypto.py` |
| 2 | 双方言幂等 DDL 辅助 | `ddl.py` |
| 3 | 本地 SQLite 引擎与建表 | `local_db.py` |
| 4 | StorageLocation 枚举与路由 | `locator.py` |
| 5 | Repository 实现 | `repository.py` |
| 6 | 服务器侧表结构加列 | 4 张表 |
| 7 | 数据库工具改造 | `database_tool_service.py` |
| 8 | K8s 工具改造 | `k8s_tool_service.py` |
| 9 | SSH 工具改造 | `ssh_tool_service.py` |
| 10 | Redis 工具改造 | `redis_tool_service.py` |
| 11 | 迁移服务与接口 | `migration.py` + `routes/storage.py` |
| 12 | 前端类型与 API | `types/storage.ts` + `api/storageApi.ts` |
| 13 | 前端通用组件 | 选择器 / 徽章 / 提示条 |
| 14 | 数据库工具前端接入 | 弹窗 + 列表 |
| 15 | K8s 工具前端接入 | 弹窗 + 列表 |
| 16 | SSH / Redis 前端接入 | 弹窗 + 列表 |
| 17 | 端到端验收 | 浏览器全流程 + 安全验证 |

---

（后续任务见下方各节）

---

## Task 1: 存储路径与本地加密

**Files:**
- Create: `backend/app/storage/paths.py`
- Create: `backend/app/storage/crypto.py`
- Create: `backend/app/storage/__init__.py`
- Test: `backend/tests/test_local_paths_crypto.py`

**Interfaces:**
- Consumes: `app.config.config.REAL_HOME`（真实家目录字符串）
- Produces:
  - `get_local_data_dir() -> Path` — `~/.toolbox` 目录（不存在则创建）
  - `get_local_db_path() -> Path` — `~/.toolbox/toolbox.db`
  - `get_local_key_path() -> Path` — `~/.toolbox/encryption.key`
  - `LocalEncryption.encrypt(plain_text: str) -> str`
  - `LocalEncryption.decrypt(encrypted_text: str) -> str`
  - `LocalEncryption.reset_cipher_suite() -> None`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_local_paths_crypto.py`：

```python
"""本地存储路径与本地加密器测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.paths import (
    get_local_data_dir,
    get_local_db_path,
    get_local_key_path,
)
from app.storage.crypto import LocalEncryption


class TestLocalPaths:
    def test_data_dir_under_real_home(self, monkeypatch, tmp_path):
        """本地目录必须基于真实家目录，而不是被覆盖的 HOME"""
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        # 模拟 config.py 的 HOME 覆盖（假家目录）
        monkeypatch.setenv("HOME", "/fake/cache/dir")

        data_dir = get_local_data_dir()

        assert data_dir == tmp_path / ".toolbox"
        assert data_dir.exists()

    def test_db_and_key_paths(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))

        assert get_local_db_path() == tmp_path / ".toolbox" / "toolbox.db"
        assert get_local_key_path() == tmp_path / ".toolbox" / "encryption.key"


class TestLocalEncryption:
    def test_encrypt_decrypt_roundtrip(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()

        plain = "my-secret-password"
        cipher = LocalEncryption.encrypt(plain)

        assert cipher != plain
        assert LocalEncryption.decrypt(cipher) == plain

    def test_key_file_created(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()

        LocalEncryption.encrypt("x")

        assert get_local_key_path().exists()
        assert get_local_key_path().stat().st_size > 0

    def test_empty_string_returns_empty(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()

        assert LocalEncryption.encrypt("") == ""
        assert LocalEncryption.decrypt("") == ""

    def test_decrypt_with_wrong_key_raises(self, monkeypatch, tmp_path):
        """密钥不匹配时必须抛异常，禁止返回假明文"""
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        LocalEncryption.reset_cipher_suite()
        cipher = LocalEncryption.encrypt("secret")

        # 换一把密钥
        get_local_key_path().write_text("0" * 64, encoding="utf-8")
        LocalEncryption.reset_cipher_suite()

        with pytest.raises(Exception):
            LocalEncryption.decrypt(cipher)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_local_paths_crypto.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage'`

- [ ] **Step 3: 实现 paths.py**

创建 `backend/app/storage/paths.py`：

```python
"""
本地存储路径推导

关键约束：config.py 在非桌面模式下把 HOME 覆盖为 backend/data/cache
（见 app/config/config.py:39），进程内 HOME 是"假家目录"。
本地数据目录必须基于 REAL_HOME 推导（app/config/config.py:21）。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 本地数据目录名（放在真实家目录下）
LOCAL_DIR_NAME = ".toolbox"
LOCAL_DB_NAME = "toolbox.db"
LOCAL_KEY_NAME = "encryption.key"


def _real_home() -> Path:
    """获取真实家目录。

    必须用 REAL_HOME，不能用 Path.home() / os.path.expanduser("~")，
    因为 config.py 已把 HOME 环境变量覆盖为缓存目录。
    """
    from app.config.config import REAL_HOME

    return Path(REAL_HOME)


def get_local_data_dir() -> Path:
    """获取（并创建）本地数据目录 ~/.toolbox/"""
    data_dir = _real_home() / LOCAL_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_local_db_path() -> Path:
    """获取本地 SQLite 文件路径 ~/.toolbox/toolbox.db"""
    return get_local_data_dir() / LOCAL_DB_NAME


def get_local_key_path() -> Path:
    """获取本地加密密钥文件路径 ~/.toolbox/encryption.key"""
    return get_local_data_dir() / LOCAL_KEY_NAME
```

- [ ] **Step 4: 实现 crypto.py**

创建 `backend/app/storage/crypto.py`：

```python
"""
本地文件密钥加密器

与服务器 EncryptionUtils 完全分离：
- 服务器 EncryptionUtils 的密钥存在数据库 system_settings 表
- 本地 LocalEncryption 的密钥存在本机 ~/.toolbox/encryption.key

两把密钥物理隔离，密文即便被复制到另一端也无法解密。
算法同为 Fernet，便于理解与迁移。
"""
import base64
import hashlib
import logging
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.storage.paths import get_local_key_path

logger = logging.getLogger(__name__)


class LocalEncryption:
    """本地文件密钥加密器（密钥不出本机）"""

    _cipher_suite = None

    @classmethod
    def _read_or_create_key(cls) -> str:
        """读取本机密钥；不存在则生成并原子写入"""
        key_path = get_local_key_path()

        if key_path.exists():
            key = key_path.read_text(encoding="utf-8").strip()
            if key:
                return key

        key = secrets.token_hex(32)
        cls._write_key_atomic(key_path, key)
        logger.info("已生成本地加密密钥：%s", key_path)
        return key

    @staticmethod
    def _write_key_atomic(path: Path, key: str) -> None:
        """原子写入密钥文件。

        Windows 上 os.rename() 对已存在的目标文件会抛 FileExistsError
        （POSIX 是静默覆盖），故需按 os.name 分支处理。
        """
        tmp = path.with_suffix(".tmp")
        tmp.write_text(key, encoding="utf-8")

        if os.name == "nt" and path.exists():
            path.unlink()

        os.rename(tmp, path)
        try:
            path.chmod(0o600)  # POSIX 收紧权限；Windows 上为 no-op
        except OSError:
            pass

    @classmethod
    def _get_cipher_suite(cls):
        if cls._cipher_suite is None:
            key = cls._read_or_create_key()
            try:
                cls._cipher_suite = Fernet(key)
            except ValueError:
                # 非标准 Fernet key 时用 SHA-256 派生（与服务器 EncryptionUtils 同策略）
                digest = hashlib.sha256(key.encode("utf-8")).digest()
                cls._cipher_suite = Fernet(base64.urlsafe_b64encode(digest))
        return cls._cipher_suite

    @classmethod
    def reset_cipher_suite(cls) -> None:
        """重置密钥缓存（密钥变更或测试隔离时调用）"""
        cls._cipher_suite = None

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        """加密字符串"""
        if not plain_text:
            return ""
        cipher_suite = cls._get_cipher_suite()
        return cipher_suite.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """解密字符串。密钥不匹配时抛 InvalidToken —— 禁止返回假明文。"""
        if not encrypted_text:
            return ""
        cipher_suite = cls._get_cipher_suite()
        try:
            return cipher_suite.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            logger.error("本地密文解密失败（密钥不匹配或数据损坏）")
            raise ValueError(
                "本地加密密钥不可用，请检查 ~/.toolbox/encryption.key"
            ) from exc
```

- [ ] **Step 5: 实现 __init__.py**

创建 `backend/app/storage/__init__.py`：

```python
"""本地优先凭据存储抽象层"""

from app.storage.crypto import LocalEncryption
from app.storage.paths import (
    get_local_data_dir,
    get_local_db_path,
    get_local_key_path,
)

__all__ = [
    "LocalEncryption",
    "get_local_data_dir",
    "get_local_db_path",
    "get_local_key_path",
]
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_local_paths_crypto.py -v`
Expected: PASS — 7 passed

- [ ] **Step 7: 提交**

```bash
git add backend/app/storage/paths.py backend/app/storage/crypto.py backend/app/storage/__init__.py backend/tests/test_local_paths_crypto.py
git commit -m "feat(storage): 本地存储路径推导与本机文件密钥加密器"
```

---

## Task 2: 双方言幂等 DDL 辅助

**Files:**
- Create: `backend/app/storage/ddl.py`
- Test: `backend/tests/test_storage_ddl.py`

**Interfaces:**
- Consumes: `sqlalchemy.engine.Connection`（同时支持 PG / SQLite）
- Produces:
  - `column_exists(conn, table: str, column: str) -> bool`
  - `ensure_column(conn, table: str, column: str, ddl: str) -> bool` — 返回 True 表示实际执行了加列

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_storage_ddl.py`：

```python
"""双方言幂等 DDL 辅助测试"""
import os
import sys
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.ddl import column_exists, ensure_column


@pytest.fixture
def sqlite_conn():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE t_demo (id VARCHAR(64) PRIMARY KEY)"))
        conn.commit()
        yield conn
        conn.close()


class TestColumnExists:
    def test_existing_column(self, sqlite_conn):
        assert column_exists(sqlite_conn, "t_demo", "id") is True

    def test_missing_column(self, sqlite_conn):
        assert column_exists(sqlite_conn, "t_demo", "storage_location") is False

    def test_missing_table(self, sqlite_conn):
        assert column_exists(sqlite_conn, "t_absent", "id") is False


class TestEnsureColumn:
    def test_adds_column_when_missing(self, sqlite_conn):
        added = ensure_column(
            sqlite_conn,
            "t_demo",
            "storage_location",
            "storage_location VARCHAR(16) NOT NULL DEFAULT 'LOCAL'",
        )

        assert added is True
        assert column_exists(sqlite_conn, "t_demo", "storage_location") is True

    def test_is_idempotent(self, sqlite_conn):
        """重复执行不报错、不重复加列"""
        ddl = "storage_location VARCHAR(16) NOT NULL DEFAULT 'LOCAL'"

        assert ensure_column(sqlite_conn, "t_demo", "storage_location", ddl) is True
        assert ensure_column(sqlite_conn, "t_demo", "storage_location", ddl) is False
        assert ensure_column(sqlite_conn, "t_demo", "storage_location", ddl) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_storage_ddl.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage.ddl'`

- [ ] **Step 3: 实现 ddl.py**

创建 `backend/app/storage/ddl.py`：

```python
"""
双方言幂等 DDL 辅助

背景：PostgreSQL 支持 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，
但 SQLite 不支持（实测 `ALTER TABLE t ADD COLUMN IF NOT EXISTS b INT`
报 `near "EXISTS": syntax error`）。故统一用「先探测、再加列」的方式，
两端通用且可重复执行。
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


def _is_postgres(conn) -> bool:
    """判断连接方言"""
    dialect = getattr(conn, "dialect", None)
    if dialect is not None:
        return dialect.name == "postgresql"
    return False


def column_exists(conn, table: str, column: str) -> bool:
    """判断列是否存在（PostgreSQL / SQLite 双方言）

    Args:
        conn: SQLAlchemy Connection
        table: 表名
        column: 列名

    Returns:
        列存在返回 True；表不存在也返回 False
    """
    if _is_postgres(conn):
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c LIMIT 1"
            ),
            {"t": table, "c": column},
        ).first()
        return row is not None

    # SQLite：PRAGMA table_info 返回 (cid, name, type, notnull, dflt_value, pk)
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def ensure_column(conn, table: str, column: str, ddl: str) -> bool:
    """幂等加列：列已存在则跳过。

    Args:
        conn: SQLAlchemy Connection
        table: 表名
        column: 列名
        ddl: ADD COLUMN 子句（不含表名与 ADD COLUMN 关键字），如
             "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'"

    Returns:
        True = 本次实际执行了加列；False = 列已存在，未执行
    """
    if column_exists(conn, table, column):
        return False

    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    conn.commit()
    logger.info("已为表 %s 添加列 %s", table, column)
    return True
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_storage_ddl.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/storage/ddl.py backend/tests/test_storage_ddl.py
git commit -m "feat(storage): 双方言幂等加列辅助（PG/SQLite 通用）"
```

---

## Task 3: 本地 SQLite 引擎与建表

**Files:**
- Create: `backend/app/storage/local_db.py`
- Test: `backend/tests/test_local_db.py`

**Interfaces:**
- Consumes: `app.storage.paths.get_local_db_path`
- Produces:
  - `get_local_engine() -> Engine` — 延迟创建并缓存的本地 SQLite engine
  - `reset_local_engine() -> None` — 清缓存（测试用）
  - `init_local_tables(engine=None) -> None` — 幂等建表（5 张主表 + 4 张关联表）
  - `get_local_session()` — 上下文管理器风格的 session 工厂

**设计要点:**
- **延迟创建**：不在应用启动时建，避免服务器部署下每个用户都生成空库文件，也避免只读磁盘导致启动失败
- **建表用 SQLAlchemy `metadata.create_all`**：SQLite 与 PG 方言差异由 SQLAlchemy 处理
- **关联表必须建**：`sql_execution_history` 有外键依赖 `db_configs`，漏建会导致本地执行历史写入失败
- **SQLite 外键默认关闭**：删除配置时需显式清理关联历史（见 Task 5 Repository 的 delete）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_local_db.py`：

```python
"""本地 SQLite 引擎与建表测试"""
import os
import sys
import pytest
from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import local_db


@pytest.fixture
def local_engine(monkeypatch, tmp_path):
    """指向临时目录的本地 engine"""
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    local_db.reset_local_engine()

    engine = local_db.get_local_engine()
    yield engine

    local_db.reset_local_engine()


class TestLocalEngine:
    def test_engine_created_lazily(self, monkeypatch, tmp_path):
        from app.config import config as config_module

        monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
        local_db.reset_local_engine()

        engine = local_db.get_local_engine()

        assert engine is not None
        db_file = tmp_path / ".toolbox" / "toolbox.db"
        assert db_file.exists()

    def test_engine_is_cached(self, local_engine):
        assert local_db.get_local_engine() is local_engine


class TestLocalTables:
    def test_all_tables_created(self, local_engine):
        local_db.init_local_tables(local_engine)
        inspector = inspect(local_engine)
        tables = set(inspector.get_table_names())

        expected = {
            "db_configs",
            "k8s_connections",
            "ssh_configs",
            "redis_configs",
            "sql_execution_history",
            "db_scan_history",
            "table_schema_cache",
            "user_display_preferences",
            "users",
        }
        assert expected.issubset(tables)

    def test_storage_location_column_present(self, local_engine):
        local_db.init_local_tables(local_engine)
        inspector = inspect(local_engine)

        for table in ("db_configs", "k8s_connections", "ssh_configs", "redis_configs"):
            cols = {c["name"] for c in inspector.get_columns(table)}
            assert "storage_location" in cols, f"{table} 缺少 storage_location 列"

    def test_init_is_idempotent(self, local_engine):
        """重复建表不报错"""
        local_db.init_local_tables(local_engine)
        local_db.init_local_tables(local_engine)
        local_db.init_local_tables(local_engine)

        inspector = inspect(local_engine)
        assert "db_configs" in inspector.get_table_names()

    def test_default_storage_location_is_local(self, local_engine):
        """本地库新行默认标记为 LOCAL"""
        local_db.init_local_tables(local_engine)

        with local_engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO db_configs "
                "(id, user_id, alias, db_type, host, port, username, "
                " password_encrypted, storage_location) "
                "VALUES ('i1', 'u1', 'a', 'mysql', 'h', 3306, 'root', 'x', 'LOCAL')"
            ))
            row = conn.execute(text(
                "SELECT storage_location FROM db_configs WHERE id = 'i1'"
            )).first()

        assert row[0] == "LOCAL"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_local_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage.local_db'`

- [ ] **Step 3: 实现 local_db.py**

创建 `backend/app/storage/local_db.py`：

```python
"""
本地 SQLite 引擎与建表

关键约束：
1. 延迟创建 —— 不在应用启动时建库。服务器部署下绝大多数用户只用远程存储，
   不该为每人生成空 SQLite 文件；也避免只读磁盘导致整个应用启动失败。
2. 失败不降级 —— 本地库创建失败时抛明确异常，禁止降级到内存库
   （内存库会让用户以为配置已保存，重启即丢失）。
3. 关联表必须建 —— sql_execution_history 等表有外键依赖 db_configs，
   漏建会导致本地执行历史写入失败。
"""
import logging
from contextlib import contextmanager

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine

from app.storage.paths import get_local_db_path

logger = logging.getLogger(__name__)

metadata = MetaData()

# ============ 5 张主表（4 个工具的配置 + users） ============

users = Table(
    "users", metadata,
    Column("user_id", String(64), primary_key=True),
    Column("username", String(50), nullable=False),
    Column("email", String(100)),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(20), default="user"),
    Column("created_at", DateTime, server_default=func.now()),
)

db_configs = Table(
    "db_configs", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("alias", String(32), nullable=False),
    Column("db_type", String(20), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False),
    Column("database_name", String(255)),
    Column("username", String(100), nullable=False),
    Column("password_encrypted", Text, nullable=False),
    Column("environment", String(20)),
    Column("group_name", String(50)),
    Column("charset", String(50)),
    Column("connect_timeout", Integer, default=10),
    Column("max_pool_size", Integer, default=10),
    Column("ssl_mode", String(20)),
    Column("ssl_cert_path", Text),
    Column("extra_config", Text),
    Column("is_active", Boolean, default=True),
    Column("last_connected_at", DateTime),
    # 注意：不设 default —— 本地/远程共用同一份 Table 定义，
    # 默认值必须由 Repository 按实例绑定的位置注入（见 repository.py）
    Column("storage_location", String(16), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("deleted", Boolean, default=False),
)

k8s_connections = Table(
    "k8s_connections", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("name", String(128), nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("cluster_name", String(255), nullable=False),
    Column("context_name", String(255), nullable=False),
    Column("server", String(512), nullable=False),
    Column("auth_type", String(32), nullable=False),
    Column("auth_data_encrypted", Text),
    Column("ca_cert_encrypted", Text),
    Column("namespace_filter", Text, default="[]"),
    Column("is_metrics_available", Boolean, default=False),
    Column("last_test_at", DateTime),
    Column("last_test_error", Text),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("sort_order", Integer, default=0),
    Column("deleted", Boolean, default=False),
    Column("storage_location", String(16), nullable=False),
)

ssh_configs = Table(
    "ssh_configs", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("alias", String(64), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False, default=22),
    Column("username", String(128), nullable=False),
    Column("password_encrypted", Text),
    Column("private_key_encrypted", Text),
    Column("passphrase_encrypted", Text),
    Column("group_name", String(64)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("deleted", Boolean, default=False),
    Column("storage_location", String(16), nullable=False),
)

redis_configs = Table(
    "redis_configs", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("alias", String(64), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False),
    Column("username", String(128)),
    Column("password_encrypted", Text),
    Column("db", Integer, default=0),
    Column("group_name", String(64)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    Column("deleted", Boolean, default=False),
    Column("storage_location", String(16), nullable=False),
)

# ============ 4 张关联表 ============

sql_execution_history = Table(
    "sql_execution_history", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("db_config_id", String(64), nullable=False),
    Column("sql_statement", Text, nullable=False),
    Column("sql_type", String(20)),
    Column("execution_status", String(20), nullable=False),
    Column("affected_rows", Integer),
    Column("execution_time_ms", Integer),
    Column("error_message", Text),
    Column("result_data", Text),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

db_scan_history = Table(
    "db_scan_history", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("db_config_id", String(64), nullable=False),
    Column("scan_result", Text),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

table_schema_cache = Table(
    "table_schema_cache", metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("db_config_id", String(64), nullable=False),
    Column("schema_data", Text, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
)

user_display_preferences = Table(
    "user_display_preferences", metadata,
    Column("user_id", String(64), primary_key=True),
    Column("visible_connections", Text),
    Column("visible_databases", Text),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
)

# ============ 引擎管理 ============

_engine: Engine | None = None


def get_local_engine() -> Engine:
    """获取（延迟创建并缓存）本地 SQLite engine。

    失败时抛明确异常，禁止降级到内存库。
    """
    global _engine

    if _engine is not None:
        return _engine

    db_path = get_local_db_path()
    try:
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            pool_reset_on_return="rollback",
        )
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        raise RuntimeError(f"本地存储不可用：{db_path} —— {exc}") from exc

    _engine = engine
    logger.info("本地 SQLite 引擎已创建：%s", db_path)
    return engine


def reset_local_engine() -> None:
    """清空引擎缓存（测试隔离用）"""
    global _engine

    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_local_tables(engine: Engine | None = None) -> None:
    """幂等建表（可重复执行）"""
    target = engine or get_local_engine()
    metadata.create_all(bind=target)
    logger.info("本地 SQLite 表结构已就绪")


@contextmanager
def get_local_session():
    """本地库会话上下文管理器"""
    from sqlalchemy.orm import sessionmaker

    engine = get_local_engine()
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_local_db.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/storage/local_db.py backend/tests/test_local_db.py
git commit -m "feat(storage): 本地 SQLite 延迟引擎与幂等建表"
```

---

## Task 4: StorageLocation 枚举与仓库路由

**Files:**
- Create: `backend/app/storage/locator.py`
- Modify: `backend/app/storage/__init__.py`
- Test: `backend/tests/test_storage_locator.py`

**Interfaces:**
- Consumes: `app.config.config.settings.DATABASE_URL`
- Produces:
  - `StorageLocation` 枚举（`LOCAL` / `SERVER`）+ `StorageLocation.from_value(value)`
  - `server_available() -> tuple[bool, str]` — 返回 (是否可用, 原因)
  - `get_repository(location, tool)` / `get_local_repo(tool)` / `get_remote_repo(tool)`

**判定规则（重要）:**
- `DATABASE_URL` 以 `sqlite://` 开头 → 远程服务器**不可用**（桌面模式默认如此）
- `DATABASE_URL` 以 `postgresql://` 开头但连接探测失败 → 不可用（附原因）
- 连接正常 → 可用

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_storage_locator.py`：

```python
"""存储位置枚举与服务器可用性判定测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.locator import StorageLocation, server_available


class TestStorageLocation:
    def test_enum_values(self):
        assert StorageLocation.LOCAL.value == "local"
        assert StorageLocation.SERVER.value == "server"

    def test_from_value(self):
        assert StorageLocation.from_value("local") is StorageLocation.LOCAL
        assert StorageLocation.from_value("SERVER") is StorageLocation.SERVER
        assert StorageLocation.from_value(StorageLocation.LOCAL) is StorageLocation.LOCAL

    def test_from_value_rejects_unknown(self):
        """非法值必须抛异常，禁止静默兜底"""
        with pytest.raises(ValueError):
            StorageLocation.from_value("nowhere")


class TestServerAvailable:
    def test_sqlite_url_means_unavailable(self, monkeypatch):
        """sqlite:// 开头 → 无远程服务器"""
        from app.config import config as config_module

        monkeypatch.setattr(
            config_module.settings, "DATABASE_URL", "sqlite:///./data/x.db"
        )

        available, reason = server_available()

        assert available is False
        assert reason  # 必须有原因说明

    def test_empty_url_means_unavailable(self, monkeypatch):
        from app.config import config as config_module

        monkeypatch.setattr(config_module.settings, "DATABASE_URL", "")

        available, reason = server_available()

        assert available is False
        assert reason

    def test_postgres_unreachable_means_unavailable(self, monkeypatch):
        """PG 地址不可达 → 不可用，且给出原因"""
        from app.config import config as config_module

        monkeypatch.setattr(
            config_module.settings,
            "DATABASE_URL",
            "postgresql://u:p@127.0.0.1:59999/nonexistent",
        )

        available, reason = server_available()

        assert available is False
        assert reason  # 必须有原因，不能是空串
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_storage_locator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage.locator'`

- [ ] **Step 3: 实现 locator.py**

创建 `backend/app/storage/locator.py`：

```python
"""
存储位置枚举与仓库路由

注意：本地凭据库（~/.toolbox/toolbox.db）与主应用库（settings.DATABASE_URL）
是两个不同的库。远程服务器存储指主应用库 —— 当 DATABASE_URL 指向 PG 且可达时，
配置可存主应用库；不可达或为 sqlite 时，只能存本地专用库。
"""
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class StorageLocation(str, Enum):
    """配置存储位置"""

    LOCAL = "local"    # 本机 SQLite（~/.toolbox/toolbox.db）
    SERVER = "server"  # 服务器 PostgreSQL（主应用库）

    @classmethod
    def from_value(cls, value) -> "StorageLocation":
        """从字符串解析存储位置；非法值抛异常（不做静默兜底）"""
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"未知存储位置：{value}")


def server_available() -> tuple[bool, str]:
    """判定远程服务器是否可用。

    Returns:
        (是否可用, 原因说明)。不可用时原因非空，可直接展示给用户。
    """
    from app.config.config import settings

    url = (settings.DATABASE_URL or "").strip()

    if not url:
        return False, "未配置数据库地址（DATABASE_URL 为空），无法使用服务器存储"

    if url.startswith("sqlite://"):
        return False, "当前为 SQLite 部署模式（无远程服务器），凭据将仅保存在本机"

    if not url.startswith("postgresql://"):
        return False, f"不支持的数据库类型：{url.split('://')[0]}"

    try:
        from app.config.database import get_pooled_db_connection, release_db_connection

        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            release_db_connection(conn)
    except Exception as exc:
        logger.warning("远程服务器不可达：%s", exc)
        return False, f"远程服务器不可达：{exc}"

    return True, ""


def get_repository(location: StorageLocation, tool: str):
    """按存储位置返回对应仓库实现。

    Args:
        location: 存储位置
        tool: 工具标识（'database' / 'k8s' / 'ssh' / 'redis'）
    """
    from app.storage.repository import get_repository as _get_repository

    return _get_repository(location, tool)


def get_local_repo(tool: str):
    """获取本地仓库"""
    return get_repository(StorageLocation.LOCAL, tool)


def get_remote_repo(tool: str):
    """获取远程仓库"""
    return get_repository(StorageLocation.SERVER, tool)
```

- [ ] **Step 4: 更新 __init__.py**

编辑 `backend/app/storage/__init__.py`，把内容替换为：

```python
"""本地优先凭据存储抽象层"""

from app.storage.crypto import LocalEncryption
from app.storage.locator import (
    StorageLocation,
    get_local_repo,
    get_remote_repo,
    get_repository,
    server_available,
)
from app.storage.paths import (
    get_local_data_dir,
    get_local_db_path,
    get_local_key_path,
)

__all__ = [
    "LocalEncryption",
    "StorageLocation",
    "get_local_data_dir",
    "get_local_db_path",
    "get_local_key_path",
    "get_local_repo",
    "get_remote_repo",
    "get_repository",
    "server_available",
]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_storage_locator.py -v`
Expected: PASS — 6 passed

- [ ] **Step 6: 提交**

```bash
git add backend/app/storage/locator.py backend/app/storage/__init__.py backend/tests/test_storage_locator.py
git commit -m "feat(storage): StorageLocation 枚举与仓库路由、服务器可用性判定"
```

---

## Task 5: Repository 实现（核心）

**Files:**
- Create: `backend/app/storage/repository.py`
- Create: `backend/app/storage/remote_db.py`
- Test: `backend/tests/test_config_repository.py`

**Interfaces:**
- Consumes: `app.storage.local_db`（Table 定义）、`app.storage.crypto.LocalEncryption`、`app.utils.encryption.EncryptionUtils`、`app.storage.locator.StorageLocation`
- Produces:
  - `ConfigRepository` 基类，方法签名（本地/远程行为一致）：
    - `list(user_id: str) -> list[dict]`
    - `get(config_id: str, user_id: str) -> dict | None`
    - `find_by_alias(user_id: str, alias: str) -> dict | None`
    - `create(user_id: str, data: dict, storage_location: StorageLocation) -> dict`
    - `update(config_id: str, user_id: str, data: dict, storage_location: StorageLocation) -> dict | None`
    - `delete(config_id: str, user_id: str) -> bool`
    - `get_with_secret(config_id: str, user_id: str) -> dict | None`
    - `list_all_locations(user_id: str) -> list[dict]`
  - `get_repository(location: StorageLocation, tool: str) -> ConfigRepository`
  - `TOOL_TABLES` 映射：`{"database": "db_configs", "k8s": "k8s_connections", "ssh": "ssh_configs", "redis": "redis_configs"}`

**安全要点:**
- **位置绑定校验**：`_assert_location()` —— 传入位置与实例绑定位置不符即抛错。这是「LOCAL 数据不可能写进远程库」的类型层保障
- **`storage_location` 由 Repository 注入**：不能写在 Column 的 `default=` 上（本地/远程共用同一份 Table 定义）
- **删除时清理关联历史**：SQLite 外键默认关闭，本地删配置需手动删 `sql_execution_history` / `db_scan_history` / `table_schema_cache`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_config_repository.py`：

```python
"""Repository 实现测试（含跨库隔离安全断言）"""
import os
import sys
import uuid
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine
from app.storage.locator import StorageLocation
from app.storage.repository import get_repository
from app.storage.crypto import LocalEncryption


@pytest.fixture
def local_repo(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    engine = get_local_engine()
    init_local_tables(engine)

    repo = get_repository(StorageLocation.LOCAL, "database")
    yield repo

    reset_local_engine()


@pytest.fixture
def sample_data():
    return {
        "id": str(uuid.uuid4()),
        "user_id": "u-test",
        "alias": "test-db",
        "db_type": "mysql",
        "host": "127.0.0.1",
        "port": 3306,
        "username": "root",
        "password_encrypted": LocalEncryption.encrypt("s3cret"),
        "environment": "dev",
        "group_name": None,
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "max_pool_size": 10,
        "ssl_mode": None,
        "ssl_cert_path": None,
        "extra_config": None,
        "is_active": True,
    }


class TestLocalRepository:
    def test_create_and_get(self, local_repo, sample_data):
        created = local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        assert created["id"] == sample_data["id"]

        fetched = local_repo.get(sample_data["id"], "u-test")
        assert fetched is not None
        assert fetched["alias"] == "test-db"

    def test_create_injects_local_storage_location(self, local_repo, sample_data):
        """本地创建的记录必须标记为 LOCAL"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location FROM db_configs WHERE id = :i"
            ), {"i": sample_data["id"]}).first()

        assert row[0] == "LOCAL"

    def test_create_rejects_wrong_location(self, local_repo, sample_data):
        """本地仓储拒绝写入 SERVER 位置 —— 越界写入的第一道闸门"""
        with pytest.raises(ValueError, match="存储位置不匹配"):
            local_repo.create("u-test", sample_data, StorageLocation.SERVER)

    def test_list_filters_by_user(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        assert len(local_repo.list("u-test")) == 1
        assert len(local_repo.list("other-user")) == 0

    def test_find_by_alias(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        found = local_repo.find_by_alias("u-test", "test-db")
        assert found is not None
        assert found["id"] == sample_data["id"]

        assert local_repo.find_by_alias("u-test", "no-such") is None

    def test_update(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        updated = local_repo.update(
            sample_data["id"], "u-test", {"alias": "renamed"}, StorageLocation.LOCAL
        )

        assert updated["alias"] == "renamed"

    def test_delete_removes_row(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        assert local_repo.delete(sample_data["id"], "u-test") is True
        assert local_repo.get(sample_data["id"], "u-test") is None

    def test_delete_cleans_related_history(self, local_repo, sample_data):
        """SQLite 外键默认关闭，必须显式清理关联历史"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        with get_local_engine().begin() as conn:
            conn.execute(text(
                "INSERT INTO sql_execution_history "
                "(id, user_id, db_config_id, sql_statement, execution_status) "
                "VALUES ('h1', 'u-test', :cid, 'SELECT 1', 'success')"
            ), {"cid": sample_data["id"]})

        local_repo.delete(sample_data["id"], "u-test")

        with get_local_engine().begin() as conn:
            remaining = conn.execute(text(
                "SELECT COUNT(*) FROM sql_execution_history WHERE db_config_id = :cid"
            ), {"cid": sample_data["id"]}).scalar()

        assert remaining == 0

    def test_get_with_secret_decrypts(self, local_repo, sample_data):
        """get_with_secret 解出明文；普通 get 不含明文"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        plain = local_repo.get(sample_data["id"], "u-test")
        assert plain.get("password_decrypted") is None

        with_secret = local_repo.get_with_secret(sample_data["id"], "u-test")
        assert with_secret["password_decrypted"] == "s3cret"

    def test_update_rejects_wrong_location(self, local_repo, sample_data):
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        with pytest.raises(ValueError, match="存储位置不匹配"):
            local_repo.update(
                sample_data["id"], "u-test", {"alias": "x"}, StorageLocation.SERVER
            )


class TestCrossStoreIsolation:
    """跨库隔离断言 —— 本设计的安全回归底线"""

    def test_local_config_not_in_remote_db(self, local_repo, sample_data):
        """本地创建的配置，绝不能出现在远程 PG 的 db_configs 表"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        from app.config.database import get_pooled_db_connection, release_db_connection

        try:
            conn = get_pooled_db_connection()
        except Exception:
            pytest.skip("远程数据库不可达，跳过跨库断言")

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM db_configs WHERE id = %s", (sample_data["id"],)
                )
                count = cur.fetchone()["count"]
        except Exception:
            pytest.skip("远程库无 db_configs 表，跳过")
        finally:
            release_db_connection(conn)

        assert count == 0

    def test_local_secret_not_decryptable_by_server_key(self, local_repo, sample_data):
        """本地密文用服务器密钥解不开"""
        local_repo.create("u-test", sample_data, StorageLocation.LOCAL)

        from app.utils.encryption import EncryptionUtils

        with pytest.raises(Exception):
            EncryptionUtils.decrypt(sample_data["password_encrypted"])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_config_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage.repository'`

- [ ] **Step 3: 实现 remote_db.py**

创建 `backend/app/storage/remote_db.py`：

```python
"""
远程 PostgreSQL 引擎适配

复用现有的 app.config.database 连接池（app/models/base.py 的 SQLAlchemy engine），
不新建连接池 —— 项目连接预算已统一收敛为一套。
"""
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def get_remote_engine() -> Engine:
    """获取远程 PG 的 SQLAlchemy engine（复用全局单例）"""
    from app.models.base import engine

    return engine


def remote_connection():
    """获取远程库的 SQLAlchemy 连接上下文管理器"""
    return get_remote_engine().begin()


def ensure_remote_column(table: str, column: str, ddl: str) -> bool:
    """幂等为远程表加列（可重复执行）"""
    from app.storage.ddl import ensure_column

    with get_remote_engine().begin() as conn:
        return ensure_column(conn, table, column, ddl)
```

- [ ] **Step 4: 实现 repository.py**

创建 `backend/app/storage/repository.py`：

```python
"""
配置仓储 —— 本地 SQLite 与远程 PostgreSQL 的统一读写层

安全不变量：storage_location='LOCAL' 的配置，其敏感字段在物理上不可能
出现在远程 PostgreSQL 中。保障来自四重：
1. Repository 实例绑定存储位置，_assert_location 拒绝越界写入
2. 写入路径隔离 —— 写操作必须拿到对应位置的 Repository 实例
3. 每个 Repository 只读写自己那一侧的行（storage_location 过滤兜底）
4. 密钥隔离 —— 本地库用本机文件密钥，远程库用服务器密钥，密文互不可解
"""
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import delete as sa_delete, insert, select, update as sa_update

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import (
    db_configs,
    db_scan_history,
    get_local_engine,
    init_local_tables,
    k8s_connections,
    redis_configs,
    sql_execution_history,
    ssh_configs,
    table_schema_cache,
)

logger = logging.getLogger(__name__)

# 工具标识 → 表名
TOOL_TABLES: dict[str, str] = {
    "database": "db_configs",
    "k8s": "k8s_connections",
    "ssh": "ssh_configs",
    "redis": "redis_configs",
}

# 工具标识 → Table 对象
TOOL_TABLE_OBJECTS = {
    "database": db_configs,
    "k8s": k8s_connections,
    "ssh": ssh_configs,
    "redis": redis_configs,
}

# 需要在删除配置时一并清理的关联表（SQLite 外键默认关闭）
RELATED_HISTORY_TABLES = {
    "database": ["sql_execution_history", "db_scan_history", "table_schema_cache"],
    "k8s": [],
    "ssh": [],
    "redis": [],
}

# 各工具的敏感列（迁移时需重加密）
SENSITIVE_COLUMNS: dict[str, list[str]] = {
    "database": ["password_encrypted"],
    "k8s": ["auth_data_encrypted", "ca_cert_encrypted"],
    "ssh": ["password_encrypted", "private_key_encrypted", "passphrase_encrypted"],
    "redis": ["password_encrypted"],
}


class ConfigRepository:
    """配置仓储基类。

    子类只需提供 `_engine()`、`_encrypt()`、`_decrypt()` 三个钩子。
    """

    location: StorageLocation = StorageLocation.SERVER

    def __init__(self, tool: str):
        if tool not in TOOL_TABLES:
            raise ValueError(f"未知工具：{tool}")
        self.tool = tool
        self.table_name = TOOL_TABLES[tool]
        self.table = TOOL_TABLE_OBJECTS[tool]

    # ============ 子类钩子 ============

    def _engine(self):
        raise NotImplementedError

    def _encrypt(self, plain: str) -> str:
        raise NotImplementedError

    def _decrypt(self, cipher: str) -> str:
        raise NotImplementedError

    def _now(self) -> datetime:
        return datetime.now()

    # ============ 安全闸门 ============

    def _assert_location(self, storage_location: StorageLocation) -> None:
        """校验传入的存储位置与本实例绑定位置一致。

        这是「LOCAL 数据不可能写进远程库」的类型层保障。
        """
        if storage_location is not self.location:
            raise ValueError(
                f"存储位置不匹配：{self.location.value} 仓储不接受 "
                f"{storage_location.value}"
            )

    # ============ 读 ============

    def list(self, user_id: str) -> list[dict]:
        """列出用户的全部配置（不含明文凭据）"""
        stmt = select(self.table).where(
            self.table.c.user_id == user_id,
            self.table.c.deleted.is_(False),
            self.table.c.storage_location == self.location.value,
        )
        with self._engine().begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def get(self, config_id: str, user_id: str) -> dict | None:
        """获取单条配置（不含明文凭据）"""
        stmt = select(self.table).where(
            self.table.c.id == config_id,
            self.table.c.user_id == user_id,
            self.table.c.deleted.is_(False),
            self.table.c.storage_location == self.location.value,
        )
        with self._engine().begin() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row) if row else None

    def find_by_alias(self, user_id: str, alias: str) -> dict | None:
        """按别名查找（用于跨库唯一性检查）"""
        stmt = select(self.table).where(
            self.table.c.user_id == user_id,
            self.table.c.alias == alias,
            self.table.c.deleted.is_(False),
            self.table.c.storage_location == self.location.value,
        )
        with self._engine().begin() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row) if row else None

    def get_with_secret(self, config_id: str, user_id: str) -> dict | None:
        """获取配置并解密敏感列（仅连接测试/实际连接时使用）。

        安全约束：
        - 不修改 self.get() 返回的字典（get/list 的返回值不含明文）
        - 解密后的明文放在独立的 result 字典里，调用方用完即丢弃
        """
        row = self.get(config_id, user_id)
        if row is None:
            return None

        # 拷贝一份新的字典，避免把明文写回 get/list 的缓存值
        result = dict(row)

        for column in SENSITIVE_COLUMNS.get(self.tool, []):
            cipher = row.get(column)
            if not cipher:
                result[f"{column.removesuffix('_encrypted')}_decrypted"] = None
                continue
            try:
                result[f"{column.removesuffix('_encrypted')}_decrypted"] = self._decrypt(cipher)
            except Exception as exc:
                logger.error("解密 %s 的 %s 失败：%s", config_id, column, exc)
                raise

        return result

    def list_all_locations(self, user_id: str) -> list[dict]:
        """列出用户在本侧的全部配置（跨位置视图用）"""
        return self.list(user_id)

    # ============ 写 ============

    def create(self, user_id: str, data: dict, storage_location: StorageLocation) -> dict:
        """创建配置。

        storage_location 必须与实例绑定位置一致，否则抛错。
        """
        self._assert_location(storage_location)

        payload = dict(data)
        payload["user_id"] = user_id
        # 位置标记由 Repository 注入 —— 不能依赖 Column 的 default
        payload["storage_location"] = self.location.value
        payload.setdefault("created_at", self._now())
        payload.setdefault("updated_at", self._now())

        stmt = insert(self.table).values(**payload)
        with self._engine().begin() as conn:
            conn.execute(stmt)

        created = self.get(payload["id"], user_id)
        if created is None:
            raise RuntimeError("配置创建后无法读回")
        return created

    def update(
        self, config_id: str, user_id: str, data: dict, storage_location: StorageLocation
    ) -> dict | None:
        """更新配置"""
        self._assert_location(storage_location)

        existing = self.get(config_id, user_id)
        if existing is None:
            return None

        payload = dict(data)
        payload.pop("id", None)
        payload.pop("user_id", None)
        payload["updated_at"] = self._now()

        stmt = (
            sa_update(self.table)
            .where(
                self.table.c.id == config_id,
                self.table.c.user_id == user_id,
                self.table.c.storage_location == self.location.value,
            )
            .values(**payload)
        )
        with self._engine().begin() as conn:
            conn.execute(stmt)

        return self.get(config_id, user_id)

    def delete(self, config_id: str, user_id: str) -> bool:
        """删除配置（并清理关联历史）"""
        existing = self.get(config_id, user_id)
        if existing is None:
            return False

        with self._engine().begin() as conn:
            conn.execute(
                sa_delete(self.table).where(
                    self.table.c.id == config_id,
                    self.table.c.user_id == user_id,
                    self.table.c.storage_location == self.location.value,
                )
            )
            # SQLite 外键默认关闭，需显式清理关联历史
            for related in RELATED_HISTORY_TABLES.get(self.tool, []):
                related_table = {
                    "sql_execution_history": sql_execution_history,
                    "db_scan_history": db_scan_history,
                    "table_schema_cache": table_schema_cache,
                }.get(related)
                if related_table is None:
                    continue
                conn.execute(
                    sa_delete(related_table).where(
                        related_table.c.db_config_id == config_id
                    )
                )

        return True


class LocalConfigRepository(ConfigRepository):
    """本地 SQLite 仓储"""

    location = StorageLocation.LOCAL

    def _engine(self):
        engine = get_local_engine()
        init_local_tables(engine)
        return engine

    def _encrypt(self, plain: str) -> str:
        return LocalEncryption.encrypt(plain)

    def _decrypt(self, cipher: str) -> str:
        return LocalEncryption.decrypt(cipher)


class RemoteConfigRepository(ConfigRepository):
    """远程 PostgreSQL 仓储"""

    location = StorageLocation.SERVER

    def _engine(self):
        from app.storage.remote_db import get_remote_engine

        return get_remote_engine()

    def _encrypt(self, plain: str) -> str:
        from app.utils.encryption import EncryptionUtils

        return EncryptionUtils.encrypt(plain)

    def _decrypt(self, cipher: str) -> str:
        from app.utils.encryption import EncryptionUtils

        return EncryptionUtils.decrypt(cipher)


def get_repository(location: StorageLocation, tool: str) -> ConfigRepository:
    """按存储位置返回对应仓库实现"""
    location = StorageLocation.from_value(location)

    if location is StorageLocation.LOCAL:
        return LocalConfigRepository(tool)
    return RemoteConfigRepository(tool)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_config_repository.py -v`
Expected: PASS — 14 passed（跨库断言若远程库不可达会 skip）

- [ ] **Step 6: 提交**

```bash
git add backend/app/storage/repository.py backend/app/storage/remote_db.py backend/tests/test_config_repository.py
git commit -m "feat(storage): 配置 Repository 统一层（本地 SQLite + 远程 PG）"
```

---

## Task 6: 服务器侧表结构加列

**Files:**
- Modify: `backend/app/db/init_db_tool.sql`（`db_configs` 表定义）
- Modify: `backend/app/services/k8s_tool_service.py`（`_ensure_table`）
- Modify: `backend/app/services/ssh_tool_service.py`（`_ensure_table`）
- Modify: `backend/app/services/redis_tool_service.py`（`_ensure_table`）
- Create: `backend/scripts/migrate_storage_location.sql`
- Test: `backend/tests/test_storage_location_migration.py`

**Interfaces:**
- Consumes: `app.storage.ddl.ensure_column`
- Produces: 4 张表都有 `storage_location` 列（服务器侧默认 `'SERVER'`）

**关键约束:**
- **DDL 有两个来源**：`db_configs` 在 SQL 文件里，另外 3 张在 Service 的 `_ensure_table()` 里 —— 漏改一处则该工具本地模式无法建表
- **加列必须幂等**：用 `ensure_column`（探测式），**不能用** `ADD COLUMN IF NOT EXISTS`（SQLite 不支持）
- **现有行默认 `'SERVER'`**：保持历史行为不变

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_storage_location_migration.py`：

```python
"""服务器侧 storage_location 列迁移测试（幂等性验证）"""
import os
import sys
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.ddl import column_exists, ensure_column


DDL = "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'"


@pytest.fixture
def pg_like_conn():
    """模拟服务器侧的表（SQLite 用于验证探测式加列的幂等逻辑）"""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE db_configs (id VARCHAR(64) PRIMARY KEY)"))
        conn.commit()
        yield conn
        conn.close()


class TestEnsureColumnIdempotency:
    def test_repeated_calls_are_safe(self, pg_like_conn):
        """重复执行不报错，且只加一次"""
        results = [ensure_column(pg_like_conn, "db_configs", "storage_location", DDL) for _ in range(3)]

        assert results == [True, False, False]
        assert column_exists(pg_like_conn, "db_configs", "storage_location") is True

    def test_existing_rows_get_server_default(self, pg_like_conn):
        """加列后既有行的默认值为 SERVER"""
        with pg_like_conn.begin() as conn:
            conn.execute(text("INSERT INTO db_configs (id) VALUES ('x1')"))

        ensure_column(pg_like_conn, "db_configs", "storage_location", DDL)

        with pg_like_conn.begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location FROM db_configs WHERE id = 'x1'"
            )).first()

        assert row[0] == "SERVER"


class TestSqlFileHasColumn:
    def test_init_sql_declares_storage_location(self):
        """init_db_tool.sql 的 db_configs 必须声明 storage_location 列"""
        sql_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "db", "init_db_tool.sql",
        )
        with open(sql_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 取 db_configs 表定义片段
        start = content.index("CREATE TABLE IF NOT EXISTS db_configs")
        end = content.index(";", start)
        block = content[start:end]

        assert "storage_location" in block, "db_configs 缺少 storage_location 列"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_storage_location_migration.py -v`
Expected: FAIL — `init_db_tool.sql` 的 `db_configs` 缺少 `storage_location` 列

- [ ] **Step 3: 修改 init_db_tool.sql**

编辑 `backend/app/db/init_db_tool.sql`，在 `db_configs` 表定义中把：

```sql
    is_active BOOLEAN DEFAULT TRUE,                -- 是否激活
    last_connected_at TIMESTAMP,                   -- 最后连接时间
```

改为：

```sql
    is_active BOOLEAN DEFAULT TRUE,                -- 是否激活
    last_connected_at TIMESTAMP,                   -- 最后连接时间
    storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER',  -- 存储位置：LOCAL(本机)/SERVER(服务器)
```

- [ ] **Step 4: 修改三个 Service 的 _ensure_table**

编辑 `backend/app/services/k8s_tool_service.py`，在 `_ensure_table()` 的 `conn.commit()` 之前插入：

```python
            # 幂等加列：存储位置标记（LOCAL=本机 / SERVER=服务器）。
            # 注意：不能使用 ADD COLUMN IF NOT EXISTS —— SQLite 不支持该语法。
            from app.storage.remote_db import ensure_remote_column

            ensure_remote_column(
                "k8s_connections",
                "storage_location",
                "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'",
            )
```

编辑 `backend/app/services/ssh_tool_service.py`，在 `_ensure_table()` 的 `conn.commit()` 之前插入：

```python
            # 幂等加列：存储位置标记（LOCAL=本机 / SERVER=服务器）
            from app.storage.remote_db import ensure_remote_column

            ensure_remote_column(
                "ssh_configs",
                "storage_location",
                "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'",
            )
```

编辑 `backend/app/services/redis_tool_service.py`，在 `_ensure_table()` 的 `conn.commit()` 之前插入：

```python
            # 幂等加列：存储位置标记（LOCAL=本机 / SERVER=服务器）
            from app.storage.remote_db import ensure_remote_column

            ensure_remote_column(
                "redis_configs",
                "storage_location",
                "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'",
            )
```

> ⚠️ **为何用 `ensure_remote_column` 而不是直接调 `ensure_column`**：这三个 `_ensure_table()` 里的 `conn` 是 `_PooledRawConnection`（psycopg2 风格包装），而 `ensure_column` 期望 SQLAlchemy `Connection`。`ensure_remote_column` 内部用 SQLAlchemy engine 自行开启事务并调用 `ensure_column`，避免了连接类型不匹配。

- [ ] **Step 5: 创建独立迁移脚本**

创建 `backend/scripts/migrate_storage_location.sql`：

```sql
-- 为 4 张凭据配置表添加 storage_location 列（幂等，可重复执行）
-- 用法：psql "$DATABASE_URL" -f backend/scripts/migrate_storage_location.sql
--
-- 语义：storage_location ∈ {LOCAL, SERVER}
--   LOCAL  = 存本机 SQLite（~/.toolbox/toolbox.db）
--   SERVER = 存本服务器 PostgreSQL
-- 现有行统一标记为 SERVER，保持历史行为不变。
--
-- 注意：PostgreSQL 支持 ADD COLUMN IF NOT EXISTS（9.6+）；
--       SQLite 不支持，故应用层加列走 app/storage/ddl.py 的探测式写法。

ALTER TABLE db_configs
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

ALTER TABLE redis_configs
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

ALTER TABLE ssh_configs
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

ALTER TABLE k8s_connections
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER';

-- 校验：以下查询期望返回 0（非 0 说明存在异常归属行，需人工核查）
SELECT COUNT(*) AS unexpected_rows FROM db_configs WHERE storage_location <> 'SERVER';
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_storage_location_migration.py -v`
Expected: PASS — 3 passed

- [ ] **Step 7: 对生产库执行迁移**

先备份，再执行幂等脚本：

```bash
cd backend
python -c "from app.config.config import settings; print(settings.DATABASE_URL)"
```

确认 URL 是目标生产库后执行：

```bash
psql "<DATABASE_URL>" -f scripts/migrate_storage_location.sql
```

Expected: 4 条 `ALTER TABLE` 成功；最后的校验查询返回 `unexpected_rows = 0`

> 若未安装 psql，用 Python 执行（同样幂等）：
> ```bash
> cd backend
> python -c "
> from app.storage.remote_db import ensure_remote_column
> for t in ['db_configs', 'redis_configs', 'ssh_configs', 'k8s_connections']:
>     added = ensure_remote_column(t, 'storage_location', \"storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'\")
>     print(t, 'added' if added else 'exists')
> "
> ```

- [ ] **Step 8: 提交**

```bash
git add backend/app/db/init_db_tool.sql backend/app/services/k8s_tool_service.py backend/app/services/ssh_tool_service.py backend/app/services/redis_tool_service.py backend/scripts/migrate_storage_location.sql backend/tests/test_storage_location_migration.py
git commit -m "feat(storage): 服务器侧 4 张表加 storage_location 列（幂等迁移）"
```

---

## Task 7: 数据库工具改造（试点）

**Files:**
- Modify: `backend/app/services/database_tool_service.py`
- Modify: `backend/app/models/database_tool_models.py`
- Modify: `backend/app/routes/database_tool.py`
- Test: `backend/tests/test_database_tool_local_storage.py`

**Interfaces:**
- Consumes: `app.storage.repository.get_repository`、`app.storage.locator.StorageLocation`
- Produces:
  - `DatabaseToolService` 的配置 CRUD 方法新增 `storage_location: StorageLocation` 参数
  - `DatabaseConfigResponse` 新增 `storage_location: str` 字段
  - `CreateDatabaseRequest` / `UpdateDatabaseRequest` 新增 `storage_location: str = "local"`

**改造方法清单：**
| 方法 | 改动 |
|---|---|
| `get_all_configs` | 走 Repository，合并本地+服务器列表 |
| `get_config` | 按 storage_location 路由到对应 Repository |
| `_get_config_with_password` | 同上，走 `get_with_secret` |
| `create_config` | 按 storage_location 写入对应 Repository |
| `update_config` | 同上 |
| `delete_config` | 同上 |
| `_re_encrypt_password` | 走 Repository.update |

**关键点:**
- `get_all_configs` 需要**合并两侧列表**并按 `created_at` 倒序 —— 用户在一个界面看到全部配置
- 密码加密改用 Repository 的 `_encrypt`（本地用本地密钥，远程用服务器密钥）
- `_decrypt_password` 的多密钥回退逻辑保留（服务器侧历史兼容），但本地仓储走 `LocalEncryption`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_database_tool_local_storage.py`：

```python
"""数据库工具本地存储改造测试"""
import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_tool_models import (
    CreateDatabaseRequest,
    DatabaseType,
)
from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    engine = get_local_engine()
    init_local_tables(engine)

    yield

    reset_local_engine()


def _make_request(**overrides):
    payload = {
        "alias": "local-db",
        "db_type": DatabaseType.MYSQL,
        "host": "127.0.0.1",
        "port": 3306,
        "database_name": "app",
        "username": "root",
        "password": "p@ssw0rd",
    }
    payload.update(overrides)
    return CreateDatabaseRequest(**payload)


class TestRequestModel:
    def test_storage_location_defaults_to_local(self):
        """新配置默认存本机"""
        req = _make_request()
        assert req.storage_location == "local"

    def test_storage_location_accepts_server(self):
        req = _make_request(storage_location="server")
        assert req.storage_location == "server"


class TestCreateLocalConfig:
    def test_create_writes_to_local_db(self, local_env):
        from app.services.database_tool_service import DatabaseToolService

        req = _make_request()
        result = DatabaseToolService.create_config(
            "u-local", req, StorageLocation.LOCAL
        )

        assert result.storage_location == "local"

        # 直接查本地 SQLite，确认行存在且标记为 LOCAL
        from sqlalchemy import text

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, password_encrypted FROM db_configs WHERE id = :i"
            ), {"i": result.id}).first()

        assert row is not None
        assert row[0] == "LOCAL"
        # 密码是密文，不是明文
        assert row[1] != "p@ssw0rd"

    def test_local_password_decrypts_with_local_key(self, local_env):
        from app.services.database_tool_service import DatabaseToolService
        from sqlalchemy import text

        req = _make_request()
        result = DatabaseToolService.create_config(
            "u-local", req, StorageLocation.LOCAL
        )

        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT password_encrypted FROM db_configs WHERE id = :i"
            ), {"i": result.id}).first()[0]

        assert LocalEncryption.decrypt(cipher) == "p@ssw0rd"


class TestAliasUniquenessAcrossStores:
    def test_alias_conflict_with_other_store_rejected(self, local_env, monkeypatch):
        """本地已有同名 alias 时，服务器侧创建必须被拒绝"""
        from app.services.database_tool_service import DatabaseToolService
        from app.storage import repository as repo_module

        # 先在本地建一条
        DatabaseToolService.create_config(
            "u-x", _make_request(alias="dup"), StorageLocation.LOCAL
        )

        # 伪造「远程仓储查到了同名」的场景
        class FakeRemoteRepo:
            def find_by_alias(self, user_id, alias):
                return {"id": "remote-1", "alias": alias}

        original = repo_module.get_repository

        def fake_get_repository(location, tool):
            if location is StorageLocation.SERVER:
                return FakeRemoteRepo()
            return original(location, tool)

        monkeypatch.setattr(repo_module, "get_repository", fake_get_repository)

        with pytest.raises(ValueError, match="已存在"):
            DatabaseToolService.create_config(
                "u-x", _make_request(alias="dup"), StorageLocation.SERVER
            )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_database_tool_local_storage.py -v`
Expected: FAIL — `CreateDatabaseRequest` 无 `storage_location` 字段

- [ ] **Step 3: 修改 models**

编辑 `backend/app/models/database_tool_models.py`，在 `CreateDatabaseRequest` 中添加：

```python
class CreateDatabaseRequest(DatabaseConfigBase):
    password: str = Field(..., description="密码")
    storage_location: str = Field(
        "local", description="存储位置：local(本机)/server(服务器)"
    )
```

在 `UpdateDatabaseRequest` 中添加：

```python
    storage_location: Optional[str] = Field(
        None, description="存储位置：local(本机)/server(服务器)"
    )
```

在 `DatabaseConfigResponse` 中添加：

```python
    storage_location: str = Field(
        default="local", description="存储位置：local(本机)/server(服务器)"
    )
```

- [ ] **Step 4: 改造 Service 的配置 CRUD**

编辑 `backend/app/services/database_tool_service.py`。

**4.1 替换 `get_all_configs`** —— 把原方法体改为：

```python
    @staticmethod
    def get_all_configs(
        user_id: str, include_password: bool = False
    ) -> List[DatabaseConfigResponse]:
        """获取用户的全部连接配置（合并本地 + 服务器两侧，按创建时间倒排）"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        rows: list[dict] = []

        # 本地侧
        try:
            local_repo = get_repository(StorageLocation.LOCAL, "database")
            rows.extend(local_repo.list(user_id))
        except Exception as exc:
            logger.warning("读取本地数据库配置失败：%s", exc)

        # 服务器侧（不可用时跳过）
        available, _reason = server_available()
        if available:
            try:
                remote_repo = get_repository(StorageLocation.SERVER, "database")
                rows.extend(remote_repo.list(user_id))
            except Exception as exc:
                logger.warning("读取服务器数据库配置失败：%s", exc)

        rows.sort(key=lambda r: r.get("created_at") or datetime.min, reverse=True)

        configs = []
        for row in rows:
            password = None
            if include_password and row.get("password_encrypted"):
                try:
                    password = self._decrypt_for(row)
                except Exception:
                    password = None
            configs.append(DatabaseToolService._row_to_response(row, password))
        return configs
```

**4.2 新增 `_decrypt_for` 辅助方法**（按行的 storage_location 选密钥）：

```python
    @staticmethod
    def _decrypt_for(row: dict) -> str | None:
        """按行的存储位置选择对应密钥解密密码"""
        from app.storage.locator import StorageLocation

        cipher = row.get("password_encrypted")
        if not cipher:
            return None

        if row.get("storage_location") == StorageLocation.LOCAL.value:
            from app.storage.crypto import LocalEncryption

            return LocalEncryption.decrypt(cipher)

        password, _error = DatabaseToolService._decrypt_password(cipher, row.get("id", ""))
        return password
```

**4.3 新增 `_row_to_response` 辅助方法**：

```python
    @staticmethod
    def _row_to_response(row: dict, password: str | None = None) -> DatabaseConfigResponse:
        """把字典行转换为响应模型"""
        return DatabaseConfigResponse(
            id=row["id"],
            user_id=row["user_id"],
            alias=row["alias"],
            db_type=row["db_type"],
            host=row["host"],
            port=row["port"],
            database_name=row.get("database_name"),
            username=row["username"],
            environment=row.get("environment"),
            group_name=row.get("group_name"),
            charset=row.get("charset"),
            connect_timeout=row.get("connect_timeout"),
            max_pool_size=row.get("max_pool_size"),
            ssl_mode=row.get("ssl_mode"),
            ssl_cert_path=row.get("ssl_cert_path"),
            extra_config=row.get("extra_config"),
            is_active=row.get("is_active", True),
            last_connected_at=row.get("last_connected_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            password=password,
            storage_location=row.get("storage_location", "server"),
        )
```

**4.4 替换 `get_config`**：

```python
    @staticmethod
    def get_config(config_id: str, user_id: str) -> Optional[DatabaseConfigResponse]:
        """获取单条配置（自动定位其所在存储位置）"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "database")
            except Exception:
                continue
            row = repo.get(config_id, user_id)
            if row:
                return DatabaseToolService._row_to_response(row)

        return None
```

**4.5 替换 `_get_config_with_password`**：

```python
    @staticmethod
    def _get_config_with_password(
        config_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取配置（含解密后的密码）"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "database")
            except Exception:
                continue
            row = repo.get_with_secret(config_id, user_id)
            if row:
                return row

        return None
```

**4.6 替换 `create_config`**：

```python
    @staticmethod
    def create_config(
        user_id: str, request: CreateDatabaseRequest, storage_location: StorageLocation
    ) -> DatabaseConfigResponse:
        """创建连接配置（写入指定存储位置）"""
        from app.storage.repository import get_repository

        # 跨库别名唯一性检查（本地 + 服务器两侧都查）
        DatabaseToolService._assert_alias_unique(user_id, request.alias, exclude_config_id=None)

        config_id = str(uuid.uuid4())
        now = datetime.now()

        payload = {
            "id": config_id,
            "alias": request.alias,
            "db_type": request.db_type.value if hasattr(request.db_type, "value") else request.db_type,
            "host": request.host,
            "port": request.port,
            "database_name": request.database_name,
            "username": request.username,
            "environment": request.environment.value if hasattr(request.environment, "value") else request.environment,
            "group_name": request.group_name,
            "charset": request.charset,
            "connect_timeout": request.connect_timeout,
            "max_pool_size": request.max_pool_size,
            "ssl_mode": request.ssl_mode,
            "ssl_cert_path": request.ssl_cert_path,
            "extra_config": json.dumps(request.extra_config) if request.extra_config else None,
            "is_active": request.is_active,
            "created_at": now,
            "updated_at": now,
        }

        repo = get_repository(storage_location, "database")
        # 密码用目标仓储的密钥加密（本地用本地密钥，远程用服务器密钥）
        payload["password_encrypted"] = repo._encrypt(request.password)

        repo.create(user_id, payload, storage_location)

        created = repo.get(config_id, user_id)
        if created is None:
            raise RuntimeError("配置创建后无法读回")
        return DatabaseToolService._row_to_response(created)
```

**4.7 新增 `_assert_alias_unique`**：

```python
    @staticmethod
    def _assert_alias_unique(
        user_id: str, alias: str, exclude_config_id: str | None = None
    ) -> None:
        """别名唯一性 —— 必须跨本地与服务器两侧检查"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        locations = [StorageLocation.LOCAL]
        available, _ = server_available()
        if available:
            locations.append(StorageLocation.SERVER)

        for location in locations:
            try:
                repo = get_repository(location, "database")
                existing = repo.find_by_alias(user_id, alias)
            except Exception:
                continue
            if existing and existing.get("id") != exclude_config_id:
                raise ValueError(
                    f"别名 '{alias}' 已存在（存储位置：{location.value}）"
                )
```

**4.8 替换 `update_config`**：

```python
    @staticmethod
    def update_config(
        config_id: str,
        user_id: str,
        request: UpdateDatabaseRequest,
        storage_location: StorageLocation | None = None,
    ) -> Optional[DatabaseConfigResponse]:
        """更新连接配置"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        # 定位配置当前所在位置
        target_location = storage_location
        repo = None
        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                candidate = get_repository(location, "database")
            except Exception:
                continue
            if candidate.get(config_id, user_id):
                repo = candidate
                target_location = location
                break

        if repo is None or target_location is None:
            return None

        if request.alias is not None:
            DatabaseToolService._assert_alias_unique(
                user_id, request.alias, exclude_config_id=config_id
            )

        updates: dict[str, Any] = {}
        for field in (
            "alias", "host", "port", "database_name", "username",
            "environment", "group_name", "charset", "connect_timeout",
            "max_pool_size", "ssl_mode", "ssl_cert_path", "is_active",
        ):
            value = getattr(request, field, None)
            if value is not None:
                updates[field] = value.value if hasattr(value, "value") else value

        if request.extra_config is not None:
            updates["extra_config"] = json.dumps(request.extra_config)

        if request.password is not None:
            updates["password_encrypted"] = repo._encrypt(request.password)

        updated = repo.update(config_id, user_id, updates, target_location)
        if updated is None:
            return None
        return DatabaseToolService._row_to_response(updated)
```

**4.9 替换 `delete_config`**：

```python
    @staticmethod
    def delete_config(config_id: str, user_id: str) -> bool:
        """删除连接配置（两侧都尝试删，清理可能的重复残留）"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        deleted = False
        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "database")
            except Exception:
                continue
            try:
                if repo.delete(config_id, user_id):
                    deleted = True
            except Exception as exc:
                logger.warning("删除 %s 侧配置失败：%s", location.value, exc)

        return deleted
```

**4.10 替换 `_re_encrypt_password`**

`_decrypt_password` 的多密钥回退逻辑（第 119–171 行）会调用它做「旧密钥 → 新密钥」自动迁移。

⚠️ **注意**：该方法原本没有 `user_id` 参数，且调用点在 `_decrypt_password` 内部（该方法也没有 user_id）。改造方案：

- **本地侧**：本地密文用 `LocalEncryption` 解密，走的是 Repository 的 `get_with_secret`，**不经过** `_decrypt_password` 的多密钥回退路径 → 本地不需要 `_re_encrypt_password`
- **远程侧**：保留原逻辑不动（`_decrypt_password` 与 `_re_encrypt_password` 继续用 psycopg2），因为远程表结构与既有数据兼容

因此 **`_re_encrypt_password` 与 `_decrypt_password` 保持原样，不改**。仅在 `_get_config_with_password` 走 Repository 后，本地配置不再经过这两个方法。

**4.10.1 但 `_decrypt_password` 的其余调用点需改为按位置解密**

`_decrypt_password` 还有 3 处直接调用（行 1034、1227、1631：`execute_sql` / `query_table_data` / `get_table_schema` 等业务方法）。这些方法拿到的 `config_row` 来自 `_get_config_with_password`，此时**密码已在 Repository 层解密**（`password_decrypted` 字段）。

改造方式：把这 3 处改为优先使用 `config_row.get("password_decrypted")`，回退到 `_decrypt_password`（兼容远程旧数据）：

```python
        # 优先用 Repository 已解密的密码；远程旧数据回退到原多密钥路径
        password = config_row.get("password_decrypted")
        if password is None:
            password, error = DatabaseToolService._decrypt_password(
                config_row["password_encrypted"], config_row["id"]
            )
            if password is None:
                raise ValueError(error)
```

为避免 3 处重复，**新增统一辅助方法**：

```python
    @staticmethod
    def _resolve_password(config_row: dict) -> str:
        """从配置行解析明文密码（优先 Repository 已解密值，回退远程旧密钥路径）"""
        decrypted = config_row.get("password_decrypted")
        if decrypted:
            return decrypted

        cipher = config_row.get("password_encrypted")
        if not cipher:
            raise ValueError("数据库配置密码为空")

        password, error = DatabaseToolService._decrypt_password(cipher, config_row.get("id", ""))
        if password is None:
            raise ValueError(error or "密码解密失败，请编辑该连接重新保存密码")
        return password
```

然后把 3 处调用点统一改为：

```python
        password = DatabaseToolService._resolve_password(config_row)
```

- [ ] **Step 5: 修改路由层**

编辑 `backend/app/routes/database_tool.py`：

`create_database` 端点改为：

```python
@router.post("/databases", response_model=DatabaseConfigResponse)
async def create_database(
    request: CreateDatabaseRequest,
    user_id: str = Depends(get_current_user_id),
):
    """创建数据库连接配置"""
    from app.storage.locator import StorageLocation

    try:
        location = StorageLocation.from_value(request.storage_location)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return DatabaseToolService.create_config(user_id, request, location)
```

`update_database` 端点改为：

```python
@router.put("/databases/{id}", response_model=DatabaseConfigResponse)
async def update_database(
    id: str,
    request: UpdateDatabaseRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新数据库连接配置"""
    from app.storage.locator import StorageLocation

    location = None
    if request.storage_location:
        try:
            location = StorageLocation.from_value(request.storage_location)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    result = DatabaseToolService.update_config(id, user_id, request, location)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Database config not found: {id}")
    return result
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_database_tool_local_storage.py tests/test_config_repository.py -v`
Expected: PASS

- [ ] **Step 7: 跑数据库工具的既有单测（回归）**

Run: `cd backend && python -m pytest tests/ -k "database_tool or db_configs" -q`
Expected: PASS —— 既有行为未破坏

若既有测试因方法签名变化而失败，**必须同步更新测试**（新参数有默认值，保持向后兼容）。

- [ ] **Step 8: 提交**

```bash
git add backend/app/services/database_tool_service.py backend/app/models/database_tool_models.py backend/app/routes/database_tool.py backend/tests/test_database_tool_local_storage.py
git commit -m "feat(database-tool): 连接配置支持本机/服务器双存储位置"
```

---

## Task 8: K8s 工具改造

**Files:**
- Modify: `backend/app/services/k8s_tool_service.py`
- Modify: `backend/app/models/k8s_tool_models.py`
- Modify: `backend/app/routes/k8s_tool.py`
- Test: `backend/tests/test_k8s_tool_local_storage.py`

**Interfaces:**
- Consumes: `app.storage.repository.get_repository`
- Produces: `K8sConfigResponse` 新增 `storage_location: str`；创建/更新请求新增 `storage_location: str = "local"`

**改造方法：** `get_configs`、`create_config`、`create_from_kubeconfig`、`update_config`、`update_config_auth`、`delete_config`、`get_config_by_id`、`update_sort_order`、`update_test_result`

**关键点：**
- K8s 用 `name` 而非 `alias`，**无唯一约束** → 不需要跨库别名检查
- `auth_data_encrypted`（token/cert/password 的 JSON）与 `ca_cert_encrypted` 两列都需重加密
- `create_from_kubeconfig` 批量创建时，每个 context 一条配置，全部落在同一存储位置

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_k8s_tool_local_storage.py`：

```python
"""K8s 工具本地存储改造测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.k8s_tool_models import CreateK8sManualRequest
from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


def _make_request(**overrides):
    payload = {
        "name": "local-cluster",
        "server": "https://k8s.local:6443",
        "auth_type": "bearer_token",
        "token": "my-k8s-token",
    }
    payload.update(overrides)
    return CreateK8sManualRequest(**payload)


class TestRequestModel:
    def test_storage_location_defaults_to_local(self):
        assert _make_request().storage_location == "local"


class TestCreateLocalK8sConfig:
    def test_writes_to_local_db(self, local_env):
        from app.services.k8s_tool_service import K8sToolService
        from sqlalchemy import text

        result = K8sToolService.create_config(
            "u-k8s", _make_request(), StorageLocation.LOCAL
        )

        assert result.storage_location == "local"
        assert result.has_auth_data is True

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, auth_data_encrypted FROM k8s_connections WHERE id = :i"
            ), {"i": result.id}).first()

        assert row[0] == "LOCAL"
        assert "my-k8s-token" not in row[1]  # 必须是密文

    def test_token_decrypts_with_local_key(self, local_env):
        import json

        from app.services.k8s_tool_service import K8sToolService
        from sqlalchemy import text

        result = K8sToolService.create_config(
            "u-k8s", _make_request(), StorageLocation.LOCAL
        )

        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT auth_data_encrypted FROM k8s_connections WHERE id = :i"
            ), {"i": result.id}).first()[0]

        assert json.loads(LocalEncryption.decrypt(cipher))["token"] == "my-k8s-token"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_k8s_tool_local_storage.py -v`
Expected: FAIL — `CreateK8sManualRequest` 无 `storage_location`

- [ ] **Step 3: 修改 models**

编辑 `backend/app/models/k8s_tool_models.py`：

在 `CreateK8sManualRequest` 中添加：

```python
    storage_location: str = Field(
        "local", description="存储位置：local(本机)/server(服务器)"
    )
```

在 `K8sConfigResponse` 中添加：

```python
    storage_location: str = Field(
        default="local", description="存储位置：local(本机)/server(服务器)"
    )
```

- [ ] **Step 4: 改造 Service**

编辑 `backend/app/services/k8s_tool_service.py`。

**4.1 `get_configs`** —— 合并两侧：

```python
    @staticmethod
    def get_configs(user_id: str) -> List[K8sConfigResponse]:
        """获取当前用户的所有连接配置（合并本地 + 服务器，脱敏）"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        rows: list[dict] = []

        try:
            rows.extend(
                get_repository(StorageLocation.LOCAL, "k8s").list(user_id)
            )
        except Exception as exc:
            logger.warning("读取本地 K8s 配置失败：%s", exc)

        available, _ = server_available()
        if available:
            try:
                rows.extend(
                    get_repository(StorageLocation.SERVER, "k8s").list(user_id)
                )
            except Exception as exc:
                logger.warning("读取服务器 K8s 配置失败：%s", exc)

        rows.sort(key=lambda r: (r.get("sort_order", 0), r.get("name", "")))
        return [K8sToolService._row_to_response(row) for row in rows]
```

**4.2 `_row_to_response`** —— 加 `storage_location` 字段：

```python
    @staticmethod
    def _row_to_response(row) -> K8sConfigResponse:
        data = dict(row)
        data.setdefault("storage_location", "server")
        data["namespace_filter"] = _parse_namespace_filter(data.get("namespace_filter"))
        data["has_auth_data"] = bool(data.get("auth_data_encrypted"))
        data["has_ca_cert"] = bool(data.get("ca_cert_encrypted"))
        return K8sConfigResponse(**data)
```

> ⚠️ 实施时保留原 `_row_to_response` 里已有的字段映射逻辑（`namespace_filter` 解析、`has_auth_data` 计算等），只在其基础上补 `storage_location`，不要整体重写。

**4.3 `create_config`** —— 改为走 Repository：

```python
    @staticmethod
    def create_config(
        user_id: str, request: CreateK8sManualRequest, storage_location: StorageLocation
    ) -> K8sConfigResponse:
        """手动创建单条连接配置（敏感字段按存储位置加密）"""
        from app.storage.repository import get_repository

        repo = get_repository(storage_location, "k8s")
        config_id = str(uuid.uuid4())
        now = datetime.now()

        auth_data = K8sToolService._build_auth_data(request)
        payload = {
            "id": config_id,
            "name": request.name,
            "source_type": "manual",
            "cluster_name": request.name,
            "context_name": request.name,
            "server": request.server,
            "auth_type": request.auth_type,
            "namespace_filter": json.dumps(request.namespace_filter),
            "created_at": now,
            "updated_at": now,
        }
        if auth_data:
            payload["auth_data_encrypted"] = repo._encrypt(json.dumps(auth_data))
        if request.ca_cert:
            payload["ca_cert_encrypted"] = repo._encrypt(request.ca_cert)

        repo.create(user_id, payload, storage_location)

        row = repo.get(config_id, user_id)
        if row is None:
            raise RuntimeError("K8s 配置创建后无法读回")
        return K8sToolService._row_to_response(row)
```

**4.4 `create_from_kubeconfig`** —— 增加 `storage_location` 参数并透传：

```python
    @staticmethod
    def create_from_kubeconfig(
        user_id: str,
        kubeconfig_text: str,
        namespace_filter: Optional[List[str]] = None,
        storage_location: StorageLocation = StorageLocation.LOCAL,
    ) -> List[K8sConfigResponse]:
        """从 kubeconfig 文本批量创建连接配置（每个 context 一条）"""
        parsed = parse_kubeconfig(kubeconfig_text)
        results = []
        for ctx in parsed.contexts:
            req = K8sToolService._parsed_context_to_manual_request(
                ctx, namespace_filter or []
            )
            results.append(
                K8sToolService.create_config(user_id, req, storage_location)
            )
        return results
```

**4.5 `update_config` / `update_config_auth` / `delete_config` / `get_config_by_id` / `update_sort_order` / `update_test_result`** —— 同样改为「先定位配置所在位置，再走对应 Repository」：

```python
    @staticmethod
    def _locate(user_id: str, config_id: str):
        """定位配置所在位置与仓储；找不到返回 (None, None)"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "k8s")
            except Exception:
                continue
            if repo.get(config_id, user_id):
                return repo, location
        return None, None
```

`update_config`：

```python
    @staticmethod
    def update_config(
        user_id: str, request: UpdateK8sRequest, storage_location: StorageLocation | None = None
    ) -> K8sConfigResponse:
        """更新连接配置（仅允许修改 name / namespace_filter）"""
        repo, location = K8sToolService._locate(user_id, request.id)
        if repo is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")
        if storage_location is not None and storage_location is not location:
            raise ValueError("不允许改变配置的存储位置（如需变更请使用迁移功能）")

        updates: dict = {"updated_at": datetime.now()}
        if request.name is not None:
            updates["name"] = request.name
        if request.namespace_filter is not None:
            updates["namespace_filter"] = json.dumps(request.namespace_filter)

        updated = repo.update(request.id, user_id, updates, location)
        if updated is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")
        return K8sToolService._row_to_response(updated)
```

`update_config_auth`（敏感列重加密用目标仓储的密钥）：

```python
    @staticmethod
    def update_config_auth(
        user_id: str, request: UpdateK8sAuthRequest, storage_location: StorageLocation | None = None
    ) -> K8sConfigResponse:
        """更新连接认证信息"""
        repo, location = K8sToolService._locate(user_id, request.id)
        if repo is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")
        if storage_location is not None and storage_location is not location:
            raise ValueError("不允许改变配置的存储位置（如需变更请使用迁移功能）")

        auth_data = K8sToolService._build_auth_data(request)
        updates: dict = {"updated_at": datetime.now()}

        if auth_data:
            updates["auth_data_encrypted"] = repo._encrypt(json.dumps(auth_data))
        if request.ca_cert is not None:
            updates["ca_cert_encrypted"] = repo._encrypt(request.ca_cert)

        updated = repo.update(request.id, user_id, updates, location)
        if updated is None:
            raise ValueError(f"K8s 配置不存在：{request.id}")
        return K8sToolService._row_to_response(updated)
```

> ⚠️ `update_config_auth` 原实现会先 `SELECT auth_type` 再判断要更新哪些字段。改造时保留该判断逻辑（`auth_type` 决定更新 token/cert 还是 username/password），只是把最终写入改为 `repo.update(...)`。

- [ ] **Step 5: 修改路由层**

编辑 `backend/app/routes/k8s_tool.py`：`upload_kubeconfig`、`paste_kubeconfig`、`create_manual`、`update_config`、`update_config_auth` 五个端点增加 `storage_location` 解析：

```python
    from app.storage.locator import StorageLocation

    try:
        location = StorageLocation.from_value(request.storage_location)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

并把 `location` 传给对应的 Service 方法。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_k8s_tool_local_storage.py -v`
Expected: PASS — 3 passed

- [ ] **Step 7: 跑 K8s 既有单测（回归）**

Run: `cd backend && python -m pytest tests/ -k "k8s" -q`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add backend/app/services/k8s_tool_service.py backend/app/models/k8s_tool_models.py backend/app/routes/k8s_tool.py backend/tests/test_k8s_tool_local_storage.py
git commit -m "feat(k8s-tool): 连接配置支持本机/服务器双存储位置"
```

---

## Task 9: SSH 工具改造

**Files:**
- Modify: `backend/app/services/ssh_tool_service.py`
- Modify: `backend/app/models/ssh_tool_models.py`
- Modify: `backend/app/routes/ssh_tool.py`
- Test: `backend/tests/test_ssh_tool_local_storage.py`

**Interfaces:**
- Consumes: `app.storage.repository.get_repository`
- Produces: `SSHConfigResponse` 新增 `storage_location: str`；请求模型新增 `storage_location: str = "local"`

**改造方法：** `get_configs`、`get_config`、`create_config`、`update_config`、`delete_config`、`_get_column_map`

**关键点：**
- SSH 有 3 个敏感列：`password_encrypted`、`private_key_encrypted`、`passphrase_encrypted`
- `_get_column_map` 兼容新旧列名（`pick("password_encrypted", "password")`）—— 改造后本地表统一用新列名，列映射逻辑可保留但只对远程侧有意义
- SSH 用 `alias` 且有唯一性检查 → **需要跨库别名检查**（同数据库工具）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_ssh_tool_local_storage.py`：

```python
"""SSH 工具本地存储改造测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


class TestCreateLocalSSHConfig:
    def test_writes_encrypted_secret_to_local_db(self, local_env):
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService
        from sqlalchemy import text

        result = SSHToolService.create_config(
            "u-ssh",
            CreateSSHRequest(
                alias="local-ssh",
                host="10.0.0.1",
                port=22,
                username="root",
                password="ssh-secret",
            ),
            StorageLocation.LOCAL,
        )

        assert result.storage_location == "local"

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, password_encrypted FROM ssh_configs WHERE id = :i"
            ), {"i": result.id}).first()

        assert row[0] == "LOCAL"
        assert "ssh-secret" not in row[1]
        assert LocalEncryption.decrypt(row[1]) == "ssh-secret"

    def test_private_key_is_encrypted(self, local_env):
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService
        from sqlalchemy import text

        fake_key = "-----BEGIN OPENSSH PRIVATE KEY-----\nFAKE\n-----END OPENSSH PRIVATE KEY-----"
        result = SSHToolService.create_config(
            "u-ssh",
            CreateSSHRequest(
                alias="key-ssh",
                host="10.0.0.2",
                port=22,
                username="root",
                private_key=fake_key,
            ),
            StorageLocation.LOCAL,
        )

        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT private_key_encrypted FROM ssh_configs WHERE id = :i"
            ), {"i": result.id}).first()[0]

        assert "BEGIN OPENSSH" not in cipher
        assert LocalEncryption.decrypt(cipher) == fake_key
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_ssh_tool_local_storage.py -v`
Expected: FAIL — `CreateSSHRequest` / `SSHConfigResponse` 无 `storage_location`，或 `create_config` 不接受第 3 个参数

- [ ] **Step 3: 修改 models**

编辑 `backend/app/models/ssh_tool_models.py`：
- `CreateSSHRequest` 增加 `storage_location: str = Field("local", ...)`
- `UpdateSSHRequest` 增加 `storage_location: Optional[str] = Field(None, ...)`
- `SSHConfigResponse` 增加 `storage_location: str = Field(default="local", ...)`

- [ ] **Step 4: 改造 Service**

编辑 `backend/app/services/ssh_tool_service.py`：

**4.1 `create_config`** —— 改为走 Repository：

```python
    @staticmethod
    def create_config(
        user_id: str, request: CreateSSHRequest, storage_location: StorageLocation
    ) -> SSHConfigResponse:
        """创建 SSH 连接配置（敏感字段按存储位置加密）"""
        from app.storage.repository import get_repository

        SSHToolService._assert_alias_unique(user_id, request.alias)

        repo = get_repository(storage_location, "ssh")
        config_id = str(uuid.uuid4())
        now = datetime.now()

        payload = {
            "id": config_id,
            "alias": request.alias,
            "host": request.host,
            "port": request.port,
            "username": request.username,
            "group_name": request.group_name,
            "is_active": request.is_active,
            "created_at": now,
            "updated_at": now,
        }
        if request.password:
            payload["password_encrypted"] = repo._encrypt(request.password)
        if request.private_key:
            payload["private_key_encrypted"] = repo._encrypt(request.private_key)
        if request.passphrase:
            payload["passphrase_encrypted"] = repo._encrypt(request.passphrase)

        repo.create(user_id, payload, storage_location)

        row = repo.get(config_id, user_id)
        if row is None:
            raise RuntimeError("SSH 配置创建后无法读回")
        return SSHToolService._row_to_response(row)
```

**4.2 新增 `_locate` 与 `_assert_alias_unique`**：

```python
    @staticmethod
    def _locate(user_id: str, config_id: str):
        """定位配置所在位置与仓储；找不到返回 (None, None)"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "ssh")
            except Exception:
                continue
            if repo.get(config_id, user_id):
                return repo, location
        return None, None

    @staticmethod
    def _assert_alias_unique(user_id: str, alias: str, exclude_config_id: str | None = None) -> None:
        """别名唯一性 —— 跨本地与服务器两侧检查"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        locations = [StorageLocation.LOCAL]
        available, _ = server_available()
        if available:
            locations.append(StorageLocation.SERVER)

        for location in locations:
            try:
                repo = get_repository(location, "ssh")
                existing = repo.find_by_alias(user_id, alias)
            except Exception:
                continue
            if existing and existing.get("id") != exclude_config_id:
                raise ValueError(f"别名 '{alias}' 已存在（存储位置：{location.value}）")
```

**4.3 `get_configs` / `get_config` / `update_config` / `delete_config`** —— 与 K8s 工具同模式：合并两侧列表、按 `_locate` 定位后走 Repository。

**4.4 `_get_column_map`** —— 保留原实现（远程侧新旧列名兼容），但本地仓储直接用标准列名，不走列映射。

- [ ] **Step 5: 修改路由层**

编辑 `backend/app/routes/ssh_tool.py`：创建/更新端点解析 `storage_location` 并透传。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_ssh_tool_local_storage.py -v`
Expected: PASS — 2 passed

- [ ] **Step 7: 跑 SSH 既有单测（回归）**

Run: `cd backend && python -m pytest tests/ -k "ssh" -q`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add backend/app/services/ssh_tool_service.py backend/app/models/ssh_tool_models.py backend/app/routes/ssh_tool.py backend/tests/test_ssh_tool_local_storage.py
git commit -m "feat(ssh-tool): 连接配置支持本机/服务器双存储位置"
```

---

## Task 10: Redis 工具改造

**Files:**
- Modify: `backend/app/services/redis_tool_service.py`
- Modify: `backend/app/models/redis_tool_models.py`
- Modify: `backend/app/routes/redis_tool.py`
- Test: `backend/tests/test_redis_tool_local_storage.py`

**Interfaces:**
- Consumes: `app.storage.repository.get_repository`
- Produces: `RedisConfigResponse` 新增 `storage_location: str`；请求模型新增 `storage_location: str = "local"`

**改造方法：** `get_all_configs`、`get_config`、`create_config`、`update_config`、`delete_config`、`_get_config_with_password`

**关键点：**
- Redis 用 `alias` 且有唯一性检查 → **需要跨库别名检查**
- `redis_script_templates`（脚本模板）**不是凭据**，保持现状存服务器侧，不做本地化
- `_get_column_map` 的新旧列名兼容逻辑保留给远程侧

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_redis_tool_local_storage.py`：

```python
"""Redis 工具本地存储改造测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


class TestCreateLocalRedisConfig:
    def test_writes_encrypted_password_to_local_db(self, local_env):
        from app.models.redis_tool_models import CreateRedisRequest
        from app.services.redis_tool_service import RedisToolService
        from sqlalchemy import text

        result = RedisToolService.create_config(
            "u-redis",
            CreateRedisRequest(
                alias="local-redis",
                host="127.0.0.1",
                port=6379,
                username="default",
                password="redis-secret",
                db=0,
            ),
            StorageLocation.LOCAL,
        )

        assert result.storage_location == "local"

        with get_local_engine().begin() as conn:
            row = conn.execute(text(
                "SELECT storage_location, password_encrypted FROM redis_configs WHERE id = :i"
            ), {"i": result.id}).first()

        assert row[0] == "LOCAL"
        assert "redis-secret" not in row[1]
        assert LocalEncryption.decrypt(row[1]) == "redis-secret"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_redis_tool_local_storage.py -v`
Expected: FAIL — 模型无 `storage_location` 或方法签名不匹配

- [ ] **Step 3: 修改 models**

编辑 `backend/app/models/redis_tool_models.py`：
- `CreateRedisRequest` 增加 `storage_location: str = Field("local", ...)`
- `UpdateRedisRequest` 增加 `storage_location: Optional[str] = Field(None, ...)`
- `RedisConfigResponse` 增加 `storage_location: str = Field(default="local", ...)`

- [ ] **Step 4: 改造 Service**

编辑 `backend/app/services/redis_tool_service.py`，与 SSH 工具同模式：
- `create_config` 走 Repository（密码用 `repo._encrypt`）
- `get_all_configs` 合并两侧
- `get_config` / `update_config` / `delete_config` 按 `_locate` 定位
- `_get_config_with_password` 走 `repo.get_with_secret`
- 新增 `_locate` 与 `_assert_alias_unique`

**注意**：`redis_script_templates` 的相关方法（`get_script_templates` 等）**保持现状**，仍用 `get_pooled_db_connection` 写服务器库。

- [ ] **Step 5: 修改路由层**

编辑 `backend/app/routes/redis_tool.py`：创建/更新端点解析 `storage_location` 并透传。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_redis_tool_local_storage.py -v`
Expected: PASS — 1 passed

- [ ] **Step 7: 跑 Redis 既有单测（回归）**

Run: `cd backend && python -m pytest tests/ -k "redis" -q`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add backend/app/services/redis_tool_service.py backend/app/models/redis_tool_models.py backend/app/routes/redis_tool.py backend/tests/test_redis_tool_local_storage.py
git commit -m "feat(redis-tool): 连接配置支持本机/服务器双存储位置"
```

---

## Task 11: 迁移服务与接口

**Files:**
- Create: `backend/app/storage/migration.py`
- Create: `backend/app/routes/storage.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_config_migration.py`

**Interfaces:**
- Consumes: `app.storage.repository.get_repository`、`app.storage.locator.StorageLocation`、`app.storage.locator.server_available`
- Produces:
  - `migrate_config(user_id: str, tool: str, config_id: str, target: StorageLocation) -> dict`
  - `migrate_all(user_id: str, tool: str, target: StorageLocation) -> dict`
  - `GET /api/storage/status` → `{ server_available, server_reason, local_path }`
  - `POST /api/storage/{tool}/configs/{config_id}/migrate` → `{ success, storage_location, message }`
  - `POST /api/storage/{tool}/configs/migrate-all` → `{ success, migrated, failed, errors }`

**安全要点（必读）:**
- **迁移顺序：先写目标端，后删源端** —— 先删后写在写失败时会**丢失配置**（不可接受）
- **重加密**：用源端密钥解密 → 用目标端密钥加密。两端密钥不同，密文不可直接拷贝
- **明文只在内存**：不落盘、不进日志
- **别名冲突**：目标端已有同名 alias → 迁移失败并提示，不自动改名、不静默覆盖
- **批量迁移单条失败不中断整体**

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_config_migration.py`：

```python
"""配置迁移服务测试（重加密 + 先写后删 + 失败处理）"""
import os
import sys
import uuid
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine
from app.storage.migration import migrate_config


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


def _seed_local_config(user_id="u-mig", alias="mig-db"):
    """在本地库插入一条配置，返回 (config_id, cipher)"""
    config_id = str(uuid.uuid4())
    cipher = LocalEncryption.encrypt("migrate-secret")

    with get_local_engine().begin() as conn:
        conn.execute(text(
            "INSERT INTO db_configs "
            "(id, user_id, alias, db_type, host, port, username, password_encrypted, "
            " storage_location, created_at, updated_at) "
            "VALUES (:i, :u, :a, 'mysql', 'h', 3306, 'root', :c, 'LOCAL', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"i": config_id, "u": user_id, "a": alias, "c": cipher})

    return config_id, cipher


class TestMigrateConfig:
    def test_source_not_found_raises(self, local_env):
        with pytest.raises(ValueError, match="不存在"):
            migrate_config("u-mig", "database", str(uuid.uuid4()), StorageLocation.SERVER)

    def test_migrate_requires_target_available(self, local_env, monkeypatch):
        """目标服务器不可用时必须拒绝迁移"""
        from app.storage import migration as migration_module

        config_id, _cipher = _seed_local_config()

        monkeypatch.setattr(
            migration_module, "server_available", lambda: (False, "未配置远程服务器")
        )

        with pytest.raises(ValueError, match="未配置远程服务器"):
            migrate_config("u-mig", "database", config_id, StorageLocation.SERVER)

    def test_migrate_to_local_reencrypts(self, local_env, monkeypatch):
        """从服务器搬到本地：密文必须用本地密钥重加密"""
        from app.storage import migration as migration_module
        from app.storage.repository import RemoteConfigRepository

        config_id, _ = _seed_local_config()

        # 伪造一条服务器侧配置（用另一把密钥加密）
        fake_cipher = "server-side-cipher"

        class FakeRemoteRepo(RemoteConfigRepository):
            def get(self, cid, uid):
                if cid != config_id:
                    return None
                return {
                    "id": config_id,
                    "user_id": uid,
                    "alias": "mig-db",
                    "db_type": "mysql",
                    "host": "h",
                    "port": 3306,
                    "username": "root",
                    "password_encrypted": fake_cipher,
                    "storage_location": "SERVER",
                    "deleted": False,
                }

            def get_with_secret(self, cid, uid):
                row = self.get(cid, uid)
                if row is None:
                    return None
                row["password_decrypted"] = "migrate-secret"
                return row

            def create(self, user_id, data, storage_location):
                with get_local_engine().begin() as conn:
                    conn.execute(text(
                        "INSERT INTO db_configs "
                        "(id, user_id, alias, db_type, host, port, username, "
                        " password_encrypted, storage_location, created_at, updated_at) "
                        "VALUES (:i, :u, :a, 'mysql', 'h', 3306, 'root', :c, 'LOCAL', "
                        " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ), {
                        "i": data["id"], "u": user_id, "a": data["alias"],
                        "c": data.get("password_encrypted"),
                    })
                return data

            def delete(self, cid, uid):
                return False  # 模拟源端删除失败 → 中间态

        monkeypatch.setattr(
            migration_module, "get_repository",
            lambda location, tool: FakeRemoteRepo(tool)
            if location is StorageLocation.SERVER
            else migration_module.get_repository(location, tool),
        )
        monkeypatch.setattr(migration_module, "server_available", lambda: (True, ""))

        result = migrate_config(
            "u-mig", "database", config_id, StorageLocation.LOCAL
        )

        assert result["success"] is True
        assert result["storage_location"] == "local"

        # 目标端密文必须能用本地密钥解开
        with get_local_engine().begin() as conn:
            cipher = conn.execute(text(
                "SELECT password_encrypted FROM db_configs WHERE id = :i"
            ), {"i": config_id}).first()[0]

        assert LocalEncryption.decrypt(cipher) == "migrate-secret"


class TestMigrateOrdering:
    def test_target_written_before_source_deleted(self, local_env, monkeypatch):
        """执行顺序验证：目标端写入发生在源端删除之前"""
        from app.storage import migration as migration_module

        config_id, _ = _seed_local_config()
        call_order: list[str] = []

        class FakeRemoteRepo:
            def get(self, cid, uid):
                return {
                    "id": cid, "user_id": uid, "alias": "mig-db",
                    "db_type": "mysql", "host": "h", "port": 3306,
                    "username": "root", "password_encrypted": "c",
                    "storage_location": "SERVER", "deleted": False,
                }

            def get_with_secret(self, cid, uid):
                row = self.get(cid, uid)
                row["password_decrypted"] = "s"
                return row

            def create(self, user_id, data, storage_location):
                call_order.append("write_target")
                return data

            def delete(self, cid, uid):
                call_order.append("delete_source")
                return True

        original_get_repository = migration_module.get_repository

        def fake_get_repository(location, tool):
            if location is StorageLocation.SERVER:
                return FakeRemoteRepo()
            return original_get_repository(location, tool)

        monkeypatch.setattr(migration_module, "get_repository", fake_get_repository)
        monkeypatch.setattr(migration_module, "server_available", lambda: (True, ""))

        migrate_config("u-mig", "database", config_id, StorageLocation.LOCAL)

        assert call_order == ["write_target", "delete_source"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_config_migration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage.migration'`

- [ ] **Step 3: 实现 migration.py**

创建 `backend/app/storage/migration.py`：

```python
"""
配置迁移服务 —— 本地 ↔ 服务器

安全约束：
1. 执行顺序为「先写目标端、后删源端」。先删后写在写失败时会丢失配置（不可接受）；
   先写后删的最坏情况是短暂重复，可通过再次迁移自愈。
2. 迁移必须重加密：源端密钥与目标端密钥不同，密文不可直接拷贝。
3. 明文只在内存，不落盘、不进日志。
4. 目标端已有同名配置时迁移失败，不自动改名、不静默覆盖。
"""
import logging

from app.storage.locator import StorageLocation, server_available
from app.storage.repository import (
    SENSITIVE_COLUMNS,
    TOOL_TABLES,
    get_repository,
)

logger = logging.getLogger(__name__)


def _decrypt_sensitive(tool: str, row: dict, location: StorageLocation) -> dict:
    """用源端密钥解密敏感列，返回明文字典（仅在内存）"""
    from app.storage.crypto import LocalEncryption
    from app.utils.encryption import EncryptionUtils

    plain: dict = {}
    for column in SENSITIVE_COLUMNS.get(tool, []):
        cipher = row.get(column)
        if not cipher:
            plain[column] = None
            continue

        if location is StorageLocation.LOCAL:
            plain[column] = LocalEncryption.decrypt(cipher)
        else:
            plain[column] = EncryptionUtils.decrypt(cipher)

    return plain


def _encrypt_sensitive(tool: str, plain: dict, location: StorageLocation) -> dict:
    """用目标端密钥加密敏感列"""
    from app.storage.crypto import LocalEncryption
    from app.utils.encryption import EncryptionUtils

    cipher: dict = {}
    for column, value in plain.items():
        if not value:
            cipher[column] = None
            continue

        if location is StorageLocation.LOCAL:
            cipher[column] = LocalEncryption.encrypt(value)
        else:
            cipher[column] = EncryptionUtils.encrypt(value)

    return cipher


def migrate_config(
    user_id: str, tool: str, config_id: str, target: StorageLocation
) -> dict:
    """迁移单条配置到目标存储位置。

    Returns:
        { "success": bool, "storage_location": str, "message": str }

    Raises:
        ValueError: 配置不存在 / 目标不可用 / 别名冲突 / 解密失败
    """
    if tool not in TOOL_TABLES:
        raise ValueError(f"未知工具：{tool}")

    target = StorageLocation.from_value(target)

    if target is StorageLocation.SERVER:
        available, reason = server_available()
        if not available:
            raise ValueError(reason or "未配置远程服务器，无法上传")

    # 1. 定位源端（配置在哪一侧就从哪一侧迁出）
    #    若本地仓储初始化失败，跳过本地直接找服务器侧，不能因一边不可达而阻断定位
    source_repo = None
    source_location = None
    locate_errors: list[str] = []

    for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
        try:
            repo = get_repository(location, tool)
            if repo.get(config_id, user_id):
                source_repo = repo
                source_location = location
                break
        except Exception as exc:
            locate_errors.append(f"{location.value}：{exc}")
            logger.warning("定位源端时 %s 侧不可用：%s", location.value, exc)

    if source_repo is None or source_location is None:
        raise ValueError(f"配置不存在：{config_id}。定位失败：{locate_errors}")

    if source_location is target:
        return {
            "success": True,
            "storage_location": target.value,
            "message": "配置已在目标存储位置，无需迁移",
        }

    # 2. 解密（源端密钥）→ 明文（仅内存）
    source_row = source_repo.get_with_secret(config_id, user_id)
    if source_row is None:
        raise ValueError(f"配置不存在：{config_id}")

    plain = {}
    for column in SENSITIVE_COLUMNS.get(tool, []):
        key = f"{column.removesuffix('_encrypted')}_decrypted"
        plain[column] = source_row.get(key)

    # 3. 目标端别名冲突检查
    target_repo = get_repository(target, tool)
    alias_field = "name" if tool == "k8s" else "alias"
    alias = source_row.get(alias_field)
    if alias:
        existing = target_repo.find_by_alias(user_id, alias)
        if existing and existing.get("id") != config_id:
            raise ValueError(
                f"目标端已存在同名配置「{alias}」，请先改名或删除后再迁移"
            )

    # 4. 重加密（目标端密钥）
    cipher = _encrypt_sensitive(tool, plain, target)

    # 5. 先写目标端（先删同 id 旧行，避免主键冲突）
    #    只取目标端 Table 中真实存在的列 —— 源端行可能包含额外的派生字段
    #    （如 _decrypted 后缀），直接拷贝会导致 insert 失败。
    #    target_repo.table.c 是 SQLAlchemy ColumnCollection，其键即合法列名。
    valid_columns = set(target_repo.table.c.keys())
    payload = {
        key: value
        for key, value in source_row.items()
        if key in valid_columns and key != "storage_location"
    }
    payload.update(cipher)
    payload["storage_location"] = target.value

    target_repo.create(user_id, payload, target)

    # 6. 后删源端
    try:
        source_repo.delete(config_id, user_id)
    except Exception as exc:
        logger.warning("迁移后删除源端失败（两端暂时重复）：%s", exc)
        return {
            "success": True,
            "storage_location": target.value,
            "message": (
                "已迁移到目标位置，但源端记录清理失败（两端暂时重复，"
                "再次迁移可自动修复）"
            ),
        }

    return {
        "success": True,
        "storage_location": target.value,
        "message": "迁移成功",
    }


def migrate_all(user_id: str, tool: str, target: StorageLocation) -> dict:
    """批量迁移该用户的全部配置到目标存储位置。

    单条失败不中断整体，失败项收集到 errors 返回。
    """
    if tool not in TOOL_TABLES:
        raise ValueError(f"未知工具：{tool}")

    target = StorageLocation.from_value(target)

    if target is StorageLocation.SERVER:
        available, reason = server_available()
        if not available:
            raise ValueError(reason or "未配置远程服务器，无法上传")

    # 收集源端（与目标相反的一侧）的全部配置
    source_location = (
        StorageLocation.SERVER if target is StorageLocation.LOCAL else StorageLocation.LOCAL
    )
    source_repo = get_repository(source_location, tool)
    rows = source_repo.list(user_id)

    migrated = 0
    errors: list[dict] = []

    for row in rows:
        config_id = row.get("id")
        try:
            migrate_config(user_id, tool, config_id, target)
            migrated += 1
        except Exception as exc:
            logger.warning("批量迁移配置 %s 失败：%s", config_id, exc)
            errors.append({"config_id": config_id, "message": str(exc)})

    return {
        "success": len(errors) == 0,
        "migrated": migrated,
        "failed": len(errors),
        "errors": errors,
    }
```

- [ ] **Step 4: 实现 routes/storage.py**

创建 `backend/app/routes/storage.py`：

```python
"""
存储位置与配置迁移接口

- GET  /api/storage/status                      存储状态（服务器是否可用）
- POST /api/storage/{tool}/configs/{id}/migrate  迁移单条配置
- POST /api/storage/{tool}/configs/migrate-all   批量迁移
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth_middleware import get_current_user_id
from app.storage.locator import StorageLocation, server_available
from app.storage.migration import migrate_all, migrate_config
from app.storage.paths import get_local_db_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/storage", tags=["storage"])


class StorageStatusResponse(BaseModel):
    server_available: bool
    server_reason: str
    local_path: str


class MigrateRequest(BaseModel):
    target: str = Field(..., description="目标存储位置：local / server")


class MigrateResponse(BaseModel):
    success: bool
    storage_location: str
    message: str


class MigrateAllResponse(BaseModel):
    success: bool
    migrated: int
    failed: int
    errors: list = Field(default_factory=list)


@router.get("/status", response_model=StorageStatusResponse)
async def get_status():
    """获取存储状态：远程服务器是否可用 + 本地库路径"""
    available, reason = server_available()
    return StorageStatusResponse(
        server_available=available,
        server_reason=reason,
        local_path=str(get_local_db_path()),
    )


@router.post("/{tool}/configs/{config_id}/migrate", response_model=MigrateResponse)
async def migrate_one(
    tool: str,
    config_id: str,
    request: MigrateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """迁移单条配置到目标存储位置"""
    try:
        target = StorageLocation.from_value(request.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        return migrate_config(user_id, tool, config_id, target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("迁移配置 %s 失败：%s", config_id, exc)
        raise HTTPException(status_code=500, detail=f"迁移失败：{exc}")


@router.post("/{tool}/configs/migrate-all", response_model=MigrateAllResponse)
async def migrate_everything(
    tool: str,
    request: MigrateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """批量迁移该用户的全部配置到目标存储位置"""
    try:
        target = StorageLocation.from_value(request.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        return migrate_all(user_id, tool, target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("批量迁移失败：%s", exc)
        raise HTTPException(status_code=500, detail=f"批量迁移失败：{exc}")
```

- [ ] **Step 5: 注册路由**

编辑 `backend/app/main.py`：
1. 在 import 区添加 `storage,`
2. 在 `app.include_router(...)` 区添加：

```python
app.include_router(storage.router)
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_config_migration.py -v`
Expected: PASS — 4 passed

- [ ] **Step 7: 提交**

```bash
git add backend/app/storage/migration.py backend/app/routes/storage.py backend/app/main.py backend/tests/test_config_migration.py
git commit -m "feat(storage): 配置迁移服务与接口（重加密 + 先写后删）"
```

---

## Task 12: 前端类型与 API

**Files:**
- Create: `frontend/src/types/storage.ts`
- Create: `frontend/src/api/storageApi.ts`
- Test: `frontend/src/api/__tests__/storageApi.test.ts`

**Interfaces:**
- Consumes: `authedFetch`、`getAuthHeaders`（`frontend/src/api/http.ts`）
- Produces:
  - `type StorageLocation = 'local' | 'server'`
  - `interface StorageStatus { server_available: boolean; server_reason: string; local_path: string }`
  - `interface MigrateResult { success: boolean; storage_location: string; message: string }`
  - `interface MigrateAllResult { success: boolean; migrated: number; failed: number; errors: Array<{ config_id: string; message: string }> }`
  - `getStorageStatus(): Promise<StorageStatus>`
  - `migrateConfig(tool: string, configId: string, target: StorageLocation): Promise<MigrateResult>`
  - `migrateAllConfigs(tool: string, target: StorageLocation): Promise<MigrateAllResult>`

**工具标识映射**（前后端一致）：`database` / `k8s` / `ssh` / `redis`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/api/__tests__/storageApi.test.ts`：

```typescript
/**
 * storageApi 测试
 *
 * 覆盖：状态查询、单条迁移、批量迁移的 URL 与参数正确性
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getStorageStatus, migrateConfig, migrateAllConfigs } from '../storageApi';

const mockFetch = vi.fn();

vi.mock('../http', () => ({
  authedFetch: (...args: unknown[]) => mockFetch(...args),
}));

vi.mock('../authApi', () => ({
  getAuthHeaders: () => ({ Authorization: 'Bearer test-token' }),
  getAuthToken: () => 'test-token',
}));

describe('storageApi', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('getStorageStatus 请求 /api/storage/status', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        server_available: false,
        server_reason: '未配置远程服务器',
        local_path: 'C:/Users/x/.toolbox/toolbox.db',
      }),
    });

    const status = await getStorageStatus();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/storage/status'),
      expect.anything()
    );
    expect(status.server_available).toBe(false);
    expect(status.local_path).toContain('.toolbox');
  });

  it('migrateConfig 发送正确的 URL 与 body', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        storage_location: 'local',
        message: '迁移成功',
      }),
    });

    const result = await migrateConfig('database', 'cfg-1', 'local');

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/storage/database/configs/cfg-1/migrate');
    expect(JSON.parse(options.body)).toEqual({ target: 'local' });
    expect(result.success).toBe(true);
  });

  it('migrateAllConfigs 请求 migrate-all 端点', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        migrated: 3,
        failed: 0,
        errors: [],
      }),
    });

    const result = await migrateAllConfigs('k8s', 'server');

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/storage/k8s/configs/migrate-all');
    expect(JSON.parse(options.body)).toEqual({ target: 'server' });
    expect(result.migrated).toBe(3);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/api/__tests__/storageApi.test.ts`
Expected: FAIL — `Cannot find module '../storageApi'`

- [ ] **Step 3: 实现 types/storage.ts**

创建 `frontend/src/types/storage.ts`：

```typescript
/**
 * 存储位置相关类型
 */

/** 配置存储位置：local=本机 SQLite / server=服务器 PostgreSQL */
export type StorageLocation = 'local' | 'server';

/** 存储状态 */
export interface StorageStatus {
  /** 远程服务器是否可用 */
  server_available: boolean;
  /** 不可用原因（可直接展示给用户） */
  server_reason: string;
  /** 本地 SQLite 文件路径 */
  local_path: string;
}

/** 单条迁移结果 */
export interface MigrateResult {
  success: boolean;
  storage_location: StorageLocation;
  message: string;
}

/** 批量迁移结果 */
export interface MigrateAllResult {
  success: boolean;
  migrated: number;
  failed: number;
  errors: Array<{ config_id: string; message: string }>;
}

/** 工具标识（与后端 TOOL_TABLES 对应） */
export type StorageTool = 'database' | 'k8s' | 'ssh' | 'redis';
```

- [ ] **Step 4: 实现 api/storageApi.ts**

创建 `frontend/src/api/storageApi.ts`：

```typescript
/**
 * 存储位置与配置迁移 API 客户端
 */
import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';
import type {
  MigrateAllResult,
  MigrateResult,
  StorageLocation,
  StorageStatus,
  StorageTool,
} from '../types/storage';

const STORAGE_API_URL = `${API_BASE_URL}/storage`;

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...(getAuthHeaders() as Record<string, string>),
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const response = await authedFetch(url, { ...options, headers });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    const detail = (error as { detail?: unknown }).detail;
    let message = 'Unknown error';
    if (Array.isArray(detail)) {
      message = detail
        .map((e: { msg?: string }) => e.msg || JSON.stringify(e))
        .join('; ');
    } else if (typeof detail === 'string') {
      message = detail;
    } else if (detail) {
      message = JSON.stringify(detail);
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

/** 获取存储状态：远程服务器是否可用 + 本地库路径 */
export async function getStorageStatus(): Promise<StorageStatus> {
  return request<StorageStatus>(`${STORAGE_API_URL}/status`, { method: 'GET' });
}

/** 迁移单条配置到目标存储位置 */
export async function migrateConfig(
  tool: StorageTool,
  configId: string,
  target: StorageLocation,
): Promise<MigrateResult> {
  return request<MigrateResult>(
    `${STORAGE_API_URL}/${tool}/configs/${encodeURIComponent(configId)}/migrate`,
    {
      method: 'POST',
      body: JSON.stringify({ target }),
    },
  );
}

/** 批量迁移该用户的全部配置到目标存储位置 */
export async function migrateAllConfigs(
  tool: StorageTool,
  target: StorageLocation,
): Promise<MigrateAllResult> {
  return request<MigrateAllResult>(`${STORAGE_API_URL}/${tool}/configs/migrate-all`, {
    method: 'POST',
    body: JSON.stringify({ target }),
  });
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/api/__tests__/storageApi.test.ts`
Expected: PASS — 3 passed

- [ ] **Step 6: 提交**

```bash
git add frontend/src/types/storage.ts frontend/src/api/storageApi.ts frontend/src/api/__tests__/storageApi.test.ts
git commit -m "feat(storage): 前端存储类型与迁移 API 客户端"
```

---

## Task 13: 前端通用组件

**Files:**
- Create: `frontend/src/components/Common/StorageLocationSelector.tsx`
- Create: `frontend/src/components/Common/StorageLocationBadge.tsx`
- Create: `frontend/src/components/Common/StorageNoticeBar.tsx`
- Create: `frontend/src/components/Common/__tests__/StorageLocationSelector.test.tsx`
- Create: `frontend/src/components/Common/__tests__/StorageLocationBadge.test.tsx`

**Interfaces:**
- Consumes: `types/storage.ts` 的 `StorageLocation`
- Produces:
  - `<StorageLocationSelector value={StorageLocation} onChange={(v) => void} serverAvailable={boolean} />`
  - `<StorageLocationBadge location={StorageLocation} />`
  - `<StorageNoticeBar serverAvailable={boolean} localPath={string} onClearLocalData={() => void} />`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/components/Common/__tests__/StorageLocationSelector.test.tsx`：

```typescript
/**
 * StorageLocationSelector 测试
 *
 * 覆盖：默认选中本机、服务器不可用时隐藏上传选项、切换时触发回调
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StorageLocationSelector from '../StorageLocationSelector';

describe('StorageLocationSelector', () => {
  it('默认选中「仅保存在本机」', () => {
    render(<StorageLocationSelector value="local" onChange={vi.fn()} serverAvailable />);

    const localOption = screen.getByRole('radio', { name: /仅保存在本机/ });
    expect(localOption).toBeTruthy();
    expect((localOption as HTMLInputElement).checked).toBe(true);
  });

  it('服务器可用时展示两个选项', () => {
    render(<StorageLocationSelector value="local" onChange={vi.fn()} serverAvailable />);

    expect(screen.getByRole('radio', { name: /仅保存在本机/ })).toBeTruthy();
    expect(screen.getByRole('radio', { name: /上传到服务器/ })).toBeTruthy();
  });

  it('服务器不可用时隐藏「上传到服务器」选项', () => {
    render(
      <StorageLocationSelector value="local" onChange={vi.fn()} serverAvailable={false} />,
    );

    expect(screen.getByRole('radio', { name: /仅保存在本机/ })).toBeTruthy();
    expect(screen.queryByRole('radio', { name: /上传到服务器/ })).toBeNull();
  });

  it('选择「上传到服务器」时触发 onChange', () => {
    const onChange = vi.fn();
    render(<StorageLocationSelector value="local" onChange={onChange} serverAvailable />);

    fireEvent.click(screen.getByRole('radio', { name: /上传到服务器/ }));

    expect(onChange).toHaveBeenCalledWith('server');
  });
});
```

创建 `frontend/src/components/Common/__tests__/StorageLocationBadge.test.tsx`：

```typescript
/**
 * StorageLocationBadge 测试
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StorageLocationBadge from '../StorageLocationBadge';

describe('StorageLocationBadge', () => {
  it('local 显示「本机」', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });

  it('server 显示「服务器」', () => {
    render(<StorageLocationBadge location="server" />);
    expect(screen.getByText(/服务器/)).toBeTruthy();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/Common/__tests__/StorageLocationSelector.test.tsx src/components/Common/__tests__/StorageLocationBadge.test.tsx`
Expected: FAIL — `Cannot find module '../StorageLocationSelector'`

- [ ] **Step 3: 实现 StorageLocationSelector.tsx**

创建 `frontend/src/components/Common/StorageLocationSelector.tsx`：

```tsx
/**
 * StorageLocationSelector - 存储位置选择器
 *
 * 默认选中「仅保存在本机」；远程服务器不可用时隐藏「上传到服务器」选项。
 */
import React from 'react';
import type { StorageLocation } from '../../types/storage';

interface StorageLocationSelectorProps {
  value: StorageLocation;
  onChange: (value: StorageLocation) => void;
  /** 远程服务器是否可用；false 时隐藏上传选项 */
  serverAvailable: boolean;
}

const StorageLocationSelector: React.FC<StorageLocationSelectorProps> = ({
  value,
  onChange,
  serverAvailable,
}) => {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-ink">存储位置</label>

      <div className="space-y-2">
        <label className="flex items-start gap-2 p-2 border border-border rounded cursor-pointer hover:border-accent-cyan">
          <input
            type="radio"
            name="storage-location"
            value="local"
            checked={value === 'local'}
            onChange={() => onChange('local')}
            className="mt-1"
          />
          <span>
            <span className="block text-sm text-ink">仅保存在本机</span>
            <span className="block text-xs text-ink-faint">
              凭据不离开本机，更安全
            </span>
          </span>
        </label>

        {serverAvailable && (
          <label className="flex items-start gap-2 p-2 border border-border rounded cursor-pointer hover:border-accent-cyan">
            <input
              type="radio"
              name="storage-location"
              value="server"
              checked={value === 'server'}
              onChange={() => onChange('server')}
              className="mt-1"
            />
            <span>
              <span className="block text-sm text-ink">上传到服务器</span>
              <span className="block text-xs text-ink-faint">
                便于多设备访问，密文将离开本机
              </span>
            </span>
          </label>
        )}
      </div>

      {!serverAvailable && (
        <p className="text-xs text-ink-faint">
          当前未配置远程服务器，所有凭据将仅保存在本机。
        </p>
      )}
    </div>
  );
};

export default StorageLocationSelector;
```

- [ ] **Step 4: 实现 StorageLocationBadge.tsx**

创建 `frontend/src/components/Common/StorageLocationBadge.tsx`：

```tsx
/**
 * StorageLocationBadge - 存储位置徽章
 *
 * 🔒 本机 / ☁️ 服务器
 */
import React from 'react';
import type { StorageLocation } from '../../types/storage';

interface StorageLocationBadgeProps {
  location: StorageLocation;
}

const StorageLocationBadge: React.FC<StorageLocationBadgeProps> = ({ location }) => {
  const isLocal = location === 'local';

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${
        isLocal
          ? 'border-accent-cyan/50 text-accent-cyan'
          : 'border-border text-ink-faint'
      }`}
      title={isLocal ? '凭据仅保存在本机，不会上传' : '凭据已上传到服务器'}
    >
      {isLocal ? '🔒' : '☁️'} {isLocal ? '本机' : '服务器'}
    </span>
  );
};

export default StorageLocationBadge;
```

- [ ] **Step 5: 实现 StorageNoticeBar.tsx**

创建 `frontend/src/components/Common/StorageNoticeBar.tsx`：

```tsx
/**
 * StorageNoticeBar - 无远程服务器时的提示条
 */
import React from 'react';

interface StorageNoticeBarProps {
  serverAvailable: boolean;
  localPath: string;
  /** 清空本地数据回调（可选） */
  onClearLocalData?: () => void;
}

const StorageNoticeBar: React.FC<StorageNoticeBarProps> = ({
  serverAvailable,
  localPath,
  onClearLocalData,
}) => {
  if (serverAvailable) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded border border-accent-info/50 bg-accent-info/10 text-xs text-ink-muted">
      <span>ℹ️</span>
      <span className="flex-1">
        当前未配置远程服务器，所有凭据将仅保存在本机
        {localPath && <span className="ml-1 text-ink-faint">（{localPath}）</span>}
      </span>
      {onClearLocalData && (
        <button
          onClick={onClearLocalData}
          className="px-2 py-1 rounded border border-border hover:border-accent-danger text-ink-faint hover:text-accent-danger"
        >
          清空本地数据
        </button>
      )}
    </div>
  );
};

export default StorageNoticeBar;
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Common/__tests__/StorageLocationSelector.test.tsx src/components/Common/__tests__/StorageLocationBadge.test.tsx`
Expected: PASS — 6 passed

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/Common/StorageLocationSelector.tsx frontend/src/components/Common/StorageLocationBadge.tsx frontend/src/components/Common/StorageNoticeBar.tsx frontend/src/components/Common/__tests__/StorageLocationSelector.test.tsx frontend/src/components/Common/__tests__/StorageLocationBadge.test.tsx
git commit -m "feat(storage): 前端存储位置选择器/徽章/提示条组件"
```

---

## Task 14: 数据库工具前端接入

**Files:**
- Modify: `frontend/src/types/databaseTool.ts`
- Modify: `frontend/src/api/databaseToolApi.ts`
- Modify: `frontend/src/components/Tools/DatabaseTool/components/CreateDatabaseDialog.tsx`
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`
- Test: `frontend/src/components/Tools/DatabaseTool/__tests__/StorageLocation.test.tsx`

**Interfaces:**
- Consumes: `StorageLocationSelector`、`StorageLocationBadge`、`StorageNoticeBar`、`getStorageStatus`、`migrateConfig`
- Produces: `DatabaseConfig.storage_location: StorageLocation`；`CreateDatabaseRequest.storage_location?: StorageLocation`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/components/Tools/DatabaseTool/__tests__/StorageLocation.test.tsx`：

```tsx
/**
 * 数据库工具存储位置接入测试
 *
 * 覆盖：创建请求带上 storage_location、列表渲染本机徽章
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StorageLocationBadge from '../../../Common/StorageLocationBadge';

vi.mock('../../../../api/storageApi', () => ({
  getStorageStatus: vi.fn().mockResolvedValue({
    server_available: true,
    server_reason: '',
    local_path: 'C:/Users/x/.toolbox/toolbox.db',
  }),
  migrateConfig: vi.fn(),
  migrateAllConfigs: vi.fn(),
}));

describe('数据库工具存储位置', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('StorageLocationBadge 渲染本机徽章', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });

  it('DatabaseConfig 类型含 storage_location（编译期保障）', () => {
    const config = {
      id: 'c1',
      user_id: 'u1',
      alias: 'a',
      db_type: 'mysql' as any,
      host: 'h',
      port: 3306,
      username: 'root',
      is_active: true,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
      storage_location: 'local' as const,
    };
    expect(config.storage_location).toBe('local');
  });
});
```

- [ ] **Step 2: 运行测试确认通过/失败确认**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/__tests__/StorageLocation.test.tsx`
Expected: PASS（组件已存在）+ 类型检查在 Step 3 后生效

- [ ] **Step 3: 修改类型**

编辑 `frontend/src/types/databaseTool.ts`：

在 `DatabaseConfig` 中添加：

```typescript
  /** 存储位置：local=本机 / server=服务器 */
  storage_location: StorageLocation;
```

在 `CreateDatabaseRequest` 中添加：

```typescript
  /** 存储位置：local=本机 / server=服务器（默认本机） */
  storage_location?: StorageLocation;
```

在文件顶部添加 import：

```typescript
import type { StorageLocation } from '../storage';
```

- [ ] **Step 4: 修改 API 层**

编辑 `frontend/src/api/databaseToolApi.ts`：`createDatabase` 与 `updateDatabase` 的请求体带上 `storage_location`（若调用方未传则默认 `'local'`）。

- [ ] **Step 5: 接入 CreateDatabaseDialog**

编辑 `frontend/src/components/Tools/DatabaseTool/components/CreateDatabaseDialog.tsx`：

1. 引入组件与状态：

```tsx
import StorageLocationSelector from '../../../Common/StorageLocationSelector';
import { getStorageStatus } from '../../../../api/storageApi';
import type { StorageLocation } from '../../../../types/storage';
```

2. 在组件内增加状态：

```tsx
  const [storageLocation, setStorageLocation] = useState<StorageLocation>('local');
  const [serverAvailable, setServerAvailable] = useState(false);
```

3. 挂载时查询服务器可用性：

```tsx
  useEffect(() => {
    let cancelled = false;
    getStorageStatus()
      .then((status) => {
        if (!cancelled) setServerAvailable(status.server_available);
      })
      .catch(() => {
        if (!cancelled) setServerAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
```

4. 在表单中加入选择器（放在「密码」字段之后、「创建」按钮之前）：

```tsx
      <StorageLocationSelector
        value={storageLocation}
        onChange={setStorageLocation}
        serverAvailable={serverAvailable}
      />
```

5. 提交时带上 `storage_location`：

```tsx
      await createDatabase({
        ...formData,
        storage_location: storageLocation,
      } as CreateDatabaseRequest);
```

- [ ] **Step 6: 接入 ConnectionList（徽章 + 迁移按钮）**

编辑 `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`：

1. 引入 `StorageLocationBadge` 与 `migrateConfig`
2. 在每个连接项旁渲染徽章：

```tsx
<StorageLocationBadge location={(config.storage_location ?? 'server') as StorageLocation} />
```

3. 添加「移到本机 / 移到服务器」按钮（仅当目标侧可用时显示）：

```tsx
const target: StorageLocation = config.storage_location === 'local' ? 'server' : 'local';
const canMigrate = target === 'local' || serverAvailable;
```

点击后：

```tsx
const handleMigrate = async (configId: string, target: StorageLocation) => {
  if (!window.confirm('确定要迁移该连接配置吗？迁移时会用目标端的密钥重新加密凭据。')) {
    return;
  }
  try {
    const result = await migrateConfig('database', configId, target);
    if (result.success) {
      showToast(result.message || '迁移成功', 'success');
      onRefresh?.();
    } else {
      showToast(result.message || '迁移失败', 'error');
    }
  } catch (e) {
    showToast(e instanceof Error ? e.message : '迁移失败', 'error');
  }
};
```

- [ ] **Step 7: 运行测试与类型检查**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/`
Expected: PASS

Run: `cd frontend && npx tsc --noEmit 2>&1 | Select-String "DatabaseTool|storage"`
Expected: 无新增错误

- [ ] **Step 8: 提交**

```bash
git add frontend/src/types/databaseTool.ts frontend/src/api/databaseToolApi.ts frontend/src/components/Tools/DatabaseTool/components/CreateDatabaseDialog.tsx frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx frontend/src/components/Tools/DatabaseTool/__tests__/StorageLocation.test.tsx
git commit -m "feat(database-tool): 前端接入存储位置选择与迁移"
```

---

## Task 15: K8s 工具前端接入

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/types.ts`
- Modify: `frontend/src/api/k8sToolApi.ts`
- Modify: `frontend/src/components/Tools/K8sTool/ConnectionModal.tsx`
- Modify: `frontend/src/components/Tools/K8sTool/ConnectionList.tsx`
- Test: `frontend/src/components/Tools/K8sTool/__tests__/StorageLocation.test.tsx`

**Interfaces:**
- Consumes: 同 Task 14 的组件与 API（`migrateConfig` 的 tool 参数传 `'k8s'`）
- Produces: `K8sConnection.storage_location: StorageLocation`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/components/Tools/K8sTool/__tests__/StorageLocation.test.tsx`：

```tsx
/**
 * K8s 工具存储位置接入测试
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StorageLocationBadge from '../../../Common/StorageLocationBadge';

describe('K8s 工具存储位置', () => {
  it('渲染服务器徽章', () => {
    render(<StorageLocationBadge location="server" />);
    expect(screen.getByText(/服务器/)).toBeTruthy();
  });

  it('K8sConnection 类型含 storage_location（编译期保障）', () => {
    const conn = {
      id: 'k1',
      user_id: 'u1',
      name: 'cluster',
      source_type: 'manual',
      cluster_name: 'c',
      context_name: 'ctx',
      server: 'https://k8s',
      auth_type: 'bearer_token',
      has_auth_data: true,
      has_ca_cert: false,
      namespace_filter: [],
      is_metrics_available: false,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
      storage_location: 'local' as const,
    };
    expect(conn.storage_location).toBe('local');
  });
});
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/K8sTool/__tests__/StorageLocation.test.tsx`
Expected: PASS

- [ ] **Step 3: 修改类型与 API**

编辑 `frontend/src/components/Tools/K8sTool/types.ts`：在 `K8sConnection` 加 `storage_location: StorageLocation`，在 `CreateK8sManualRequest` 加 `storage_location?: StorageLocation`，并在文件顶部 import `StorageLocation` 类型。

编辑 `frontend/src/api/k8sToolApi.ts`：创建/更新请求带上 `storage_location`。

- [ ] **Step 4: 接入 ConnectionModal 与 ConnectionList**

与 Task 14 相同模式：`ConnectionModal` 加选择器（默认 `'local'`，服务器不可用时隐藏上传选项），`ConnectionList` 加徽章与迁移按钮（`migrateConfig('k8s', ...)`）。

- [ ] **Step 5: 运行测试与类型检查**

Run: `cd frontend && npx vitest run src/components/Tools/K8sTool/`
Expected: PASS

Run: `cd frontend && npx tsc --noEmit 2>&1 | Select-String "K8sTool"`
Expected: 无新增错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/Tools/K8sTool/types.ts frontend/src/api/k8sToolApi.ts frontend/src/components/Tools/K8sTool/ConnectionModal.tsx frontend/src/components/Tools/K8sTool/ConnectionList.tsx frontend/src/components/Tools/K8sTool/__tests__/StorageLocation.test.tsx
git commit -m "feat(k8s-tool): 前端接入存储位置选择与迁移"
```

---

## Task 16: SSH / Redis 前端接入

**Files:**
- Modify: `frontend/src/types/sshTool.ts`（若存在，否则在 `frontend/src/api/sshToolApi.ts` 内定义）
- Modify: `frontend/src/api/sshToolApi.ts`
- Modify: `frontend/src/api/redisToolApi.ts`
- Modify: `frontend/src/components/Tools/SSHTool/`（连接编辑弹窗）
- Modify: `frontend/src/components/Tools/RedisTool/`（连接编辑弹窗）
- Test: `frontend/src/components/Tools/SSHTool/__tests__/StorageLocation.test.tsx`

**Interfaces:**
- Consumes: 同 Task 14（`migrateConfig` 的 tool 参数传 `'ssh'` / `'redis'`）
- Produces: SSH / Redis 连接类型含 `storage_location: StorageLocation`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/components/Tools/SSHTool/__tests__/StorageLocation.test.tsx`：

```tsx
/**
 * SSH 工具存储位置接入测试
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StorageLocationBadge from '../../../Common/StorageLocationBadge';

describe('SSH 工具存储位置', () => {
  it('渲染本机徽章', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });
});
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/__tests__/StorageLocation.test.tsx`
Expected: PASS

- [ ] **Step 3: 确认实际文件路径**

Run: `ls frontend/src/components/Tools/ | grep -i -E "ssh|redis"`

按实际路径修改连接编辑弹窗组件（加入选择器）与连接列表组件（加入徽章 + 迁移按钮）。

- [ ] **Step 4: 修改类型与 API**

在 SSH / Redis 的连接类型与创建请求中加 `storage_location`，API 层带上该字段。

- [ ] **Step 5: 运行测试与类型检查**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/ src/components/Tools/RedisTool/`
Expected: PASS

Run: `cd frontend && npx tsc --noEmit 2>&1 | Select-String "SSH|Redis"`
Expected: 无新增错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/types/ frontend/src/api/sshToolApi.ts frontend/src/api/redisToolApi.ts frontend/src/components/Tools/SSHTool/ frontend/src/components/Tools/RedisTool/
git commit -m "feat(ssh-tool,redis-tool): 前端接入存储位置选择与迁移"
```

---

## Task 17: 端到端验收

**Files:** 无代码改动（仅验收）；若发现问题按对应任务修复

**验收场景（按项目「功能完成浏览器强制验收规则」逐条对照）：**

| # | 场景 | 期望 |
|---|---|---|
| 1 | 数据库工具 → 新建连接 → 选「仅保存在本机」→ 保存 | 成功；列表显示 🔒本机 徽章 |
| 2 | 直接查服务器 PG 的 `db_configs` 表 | **查不到该配置 id**（安全不变量） |
| 3 | 直接查本地 `~/.toolbox/toolbox.db` 的 `db_configs` | 能查到，且 `storage_location='LOCAL'` |
| 4 | 本地配置 → 点「移到服务器」 | 成功；徽章变 ☁️服务器；服务器 PG 能查到该 id |
| 5 | 服务器 PG 里的密文 vs 原本地密文 | **不同**（证明重加密生效） |
| 6 | 服务器 PG 里的密文用本地密钥解密 | **解不开**（抛异常） |
| 7 | 迁移回本机 | 成功；徽章变 🔒本机；服务器 PG 查不到该 id |
| 8 | K8s 工具新建连接（选本机）→ 连通性测试 | 认证信息能正常解密并连接 |
| 9 | SSH 工具新建连接（选本机）→ 连接测试 | 同上 |
| 10 | Redis 工具新建连接（选本机）→ 连接测试 | 同上 |
| 11 | 后端启动时 `DATABASE_URL=sqlite://...` | 4 个工具列表顶部显示「未配置远程服务器」提示条；新建弹窗**无**「上传到服务器」选项 |
| 12 | 批量迁移（全部移到本机） | 成功；`migrated` 计数正确 |
| 13 | 浏览器 Console | 无错误 |
| 14 | 现有功能回归：数据库工具执行 SQL、K8s 查 Pod、SSH 列目录、Redis 读 key | 全部正常 |

- [ ] **Step 1: 确认服务运行**

```bash
cd D:\CodeProjects\tools
python dev-services.py status
```

- [ ] **Step 2: 浏览器验收场景 1–7（数据库工具）**

用内置浏览器打开 `http://localhost:5178`，登录后进入「文件管理」外的「数据库管理工具」页，逐条走完场景 1–7。

- [ ] **Step 3: 用 Python 直接验证数据库状态（场景 2/3/5/6）**

```bash
cd D:\CodeProjects\tools\backend
python -c "
import sqlite3, os
from app.config.config import REAL_HOME
from app.storage.crypto import LocalEncryption

db = os.path.join(REAL_HOME, '.toolbox', 'toolbox.db')
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT id, alias, storage_location, password_encrypted FROM db_configs').fetchall()
print('本地库记录数:', len(rows))
for r in rows:
    print(dict(r))
"
```

期望：`storage_location` 全部为 `LOCAL`。

- [ ] **Step 4: 验证服务端 PG 无 LOCAL 行（场景 2/7）**

```bash
cd D:\CodeProjects\tools\backend
python -c "
from app.config.database import get_pooled_db_connection, release_db_connection
conn = get_pooled_db_connection()
with conn.cursor() as cur:
    cur.execute('SELECT COUNT(*) AS n FROM db_configs WHERE storage_location = %s', ('LOCAL',))
    print('服务端 LOCAL 行数（期望 0）:', cur.fetchone()['n'])
    cur.execute('SELECT id, alias, storage_location FROM db_configs ORDER BY created_at DESC LIMIT 5')
    for r in cur.fetchall():
        print(dict(r))
release_db_connection(conn)
"
```

期望：`LOCAL 行数 = 0`

- [ ] **Step 5: 验证密文不可跨端解密（场景 5/6）**

```bash
cd D:\CodeProjects\tools\backend
python -c "
import sqlite3, os
from app.config.config import REAL_HOME
from app.storage.crypto import LocalEncryption
from app.utils.encryption import EncryptionUtils

db = os.path.join(REAL_HOME, '.toolbox', 'toolbox.db')
conn = sqlite3.connect(db)
row = conn.execute('SELECT password_encrypted FROM db_configs LIMIT 1').fetchone()
if not row:
    print('本地库无记录，跳过')
else:
    cipher = row[0]
    print('本地密钥可解:', LocalEncryption.decrypt(cipher)[:3] + '***')
    try:
        EncryptionUtils.decrypt(cipher)
        print('!! 服务器密钥竟然解开了本地密文 —— 安全不变量被破坏')
    except Exception as e:
        print('服务器密钥解不开本地密文（符合预期）:', type(e).__name__)
"
```

期望：第二段输出「服务器密钥解不开本地密文（符合预期）」

- [ ] **Step 6: 验收场景 11（无远程服务器降级）**

临时把 `backend/.env` 的 `DATABASE_URL` 改为 `sqlite:///./data/tools.db`，重启后端，验证 4 个工具的提示条与选择器；验收完**改回原值并重启**。

```bash
# 改完后务必还原：
# DATABASE_URL=postgresql://<原值>
```

- [ ] **Step 7: 验收场景 13/14（Console 无错 + 功能回归）**

浏览器 Console 无错误；数据库工具执行一条 `SELECT 1`、K8s 查 Pod 列表、SSH 列目录、Redis 读一个 key，全部正常。

- [ ] **Step 8: 跑本次变更的全部相关单测**

```bash
cd D:\CodeProjects\tools\backend
python -m pytest tests/test_local_paths_crypto.py tests/test_storage_ddl.py tests/test_local_db.py tests/test_storage_locator.py tests/test_config_repository.py tests/test_storage_location_migration.py tests/test_database_tool_local_storage.py tests/test_k8s_tool_local_storage.py tests/test_ssh_tool_local_storage.py tests/test_redis_tool_local_storage.py tests/test_config_migration.py -q
```

```bash
cd D:\CodeProjects\tools\frontend
npx vitest run src/utils/__tests__ src/api/__tests__/storageApi.test.ts src/components/Common/__tests__ src/components/Tools/DatabaseTool src/components/Tools/K8sTool src/components/Tools/SSHTool
```

- [ ] **Step 9: 提交（若验收中修复了问题）**

```bash
git add <本次修复的文件>
git commit -m "fix(storage): 端到端验收问题修复"
```

---

## 附录：实现要点速查

### 存储位置判定链路

```
用户选择 storage_location
        ↓
Service.get_repository(location, tool)
        ↓
LocalConfigRepository（绑定 LOCAL，只接受 LOCAL）
   或
RemoteConfigRepository（绑定 SERVER，只接受 SERVER）
        ↓
写入 storage_location 列 + 用该侧的密钥加密敏感列
```

### 迁移链路

```
源端行（含密文）
   ↓ 用源端密钥解密 → 明文（仅内存）
   ↓ 用目标端密钥加密 → 目标端密文
   ↓ 目标端事务：删同 id 旧行 → 插入 → COMMIT
   ↓ 源端事务：删除源行 → COMMIT
```

### 不可违反的 5 条

1. `storage_location` 不得写在 `Column(default=...)` 上
2. 加列必须用 `ensure_column` 探测式，不得用 `ADD COLUMN IF NOT EXISTS`
3. 本地库与本地密钥必须基于 `REAL_HOME`，不得用 `Path.home()`
4. 解密失败必须抛异常，禁止返回假明文
5. 迁移必须先写目标端后删源端
