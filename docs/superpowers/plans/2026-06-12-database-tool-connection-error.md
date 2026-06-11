> **I'm using the writing-plans skill to create the implementation plan.**

---

# database-tool 连接稳定性修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 database-tool 页面长时间打开后出现的 `server closed the connection unexpectedly` 报错，并消除密码解密失败导致的 500 错误。

**Architecture:** 通过在后端自身连接池增加连接有效性检测、缩短目标数据库连接回收周期、统一密码解密错误处理三个层次，分别解决应用自身 DB 连接过期、目标 DB 连接过期、历史密码无法解密三类问题。

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy, psycopg2, psycopg2.pool

---

## File Map

| 文件 | 职责 | 本次修改 |
|------|------|----------|
| `backend/app/config/database.py` | 应用自身 PostgreSQL 连接池（psycopg2.pool） | 增加取连接时的有效性检测与重取逻辑 |
| `backend/app/utils/db_connection_manager.py` | 目标数据库 SQLAlchemy Engine 连接池 | 缩短 `pool_recycle`，修复 engine key 重复拼接 |
| `backend/app/services/database_tool_service.py` | database-tool 业务逻辑 | 新增密码解密 helper，关键接口使用 helper 降级 |
| `backend/app/routes/database_tool.py` | database-tool HTTP 路由 | 捕获解密异常，返回 400 友好提示 |

---

### Task 1: 后端自身连接池增加健康检查

**Files:**
- Modify: `backend/app/config/database.py:131-149`

**目标：** 当从 `psycopg2.pool.ThreadedConnectionPool` 取出的连接已被数据库服务端关闭时，自动关闭旧连接并重新获取新连接。

- [ ] **Step 1: 修改 `get_pooled_db_connection()`**

```python
def get_pooled_db_connection():
    """从连接池获取连接，若连接已失效则重取一次"""
    pool = get_connection_pool()
    conn = pool.getconn()

    # 连接已被服务端关闭时，回收并重新获取
    if getattr(conn, "closed", 0):
        try:
            pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = pool.getconn()

    return conn
```

替换原函数（第 131-134 行）：

```python
def get_pooled_db_connection():
    """从连接池获取连接"""
    pool = get_connection_pool()
    return pool.getconn()
```

- [ ] **Step 2: 让 `release_db_connection()` 更健壮**

```python
def release_db_connection(conn):
    """释放连接回池，失败时不影响业务"""
    if conn is None:
        return
    try:
        pool = get_connection_pool()
        pool.putconn(conn)
    except Exception as e:
        logger.warning(f"释放数据库连接回池失败: {e}")
        try:
            conn.close()
        except Exception:
            pass
```

替换原函数（第 146-149 行）：

```python
def release_db_connection(conn):
    """释放连接回池"""
    pool = get_connection_pool()
    pool.putconn(conn)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config/database.py
git commit -m "fix: 后端连接池增加失效连接检测与重取"
```

---

### Task 2: 缩短目标数据库连接回收周期并修复 engine key

**Files:**
- Modify: `backend/app/utils/db_connection_manager.py:110-133`, `backend/app/services/database_tool_service.py:129-130`

**目标：** 把 SQLAlchemy Engine 的 `pool_recycle` 从 1 小时改为 5 分钟，避免目标数据库空闲超时后复用失效连接；同时修复 `generate_ddl` 中 engine key 重复拼接的问题。

- [ ] **Step 1: 修改 `DBConnectionManager._create_engine()` 中的 `pool_recycle`**

将第 111 行：

```python
pool_recycle = 3600  # 1 小时回收连接，配合 pool_pre_ping 防止使用过期连接
```

改为：

```python
pool_recycle = 300  # 5 分钟回收连接，避免云数据库/本地 PG 空闲超时后复用失效连接
```

- [ ] **Step 2: 修复 `generate_ddl()` 中 engine key 的重复拼接**

将 `backend/app/services/database_tool_service.py` 第 129-130 行：

```python
engine_key = f"{config_id}:{database_name}"
engine = DBConnectionManager.get_engine(engine_key, config_dict)
```

改为：

```python
engine = DBConnectionManager.get_engine(config_id, config_dict)
```

> 原因：`DBConnectionManager.get_engine()` 内部会再次拼接 `config_id:database_name`，外部如果已经拼好传入，key 会变成 `config_id:db_name:db_name`，导致缓存 miss 并创建重复引擎。

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/db_connection_manager.py backend/app/services/database_tool_service.py
git commit -m "fix: 缩短目标 DB 连接回收周期并修复 engine key 重复拼接"
```

---

### Task 3: 新增密码解密 helper 并在关键接口降级

**Files:**
- Modify: `backend/app/services/database_tool_service.py:104-108`, `backend/app/services/database_tool_service.py:496-560`, `backend/app/services/database_tool_service.py:1086-1183`

**目标：** 避免单个数据库配置密码解密失败导致整个请求 500；对列表类接口跳过异常配置，对详情/操作类接口返回明确业务错误。

- [ ] **Step 1: 在 `DatabaseToolService` 类内新增解密 helper**

在 `class DatabaseToolService:` 定义之后（约第 105 行，即 `# --------------------------------------------------------------------------` 注释之前）插入：

```python
    @staticmethod
    def _decrypt_password(password_encrypted: str, config_id: str = "") -> tuple[str | None, str | None]:
        """
        解密数据库配置密码。
        返回 (password, error_message)。
        解密失败时返回 (None, 错误描述)，不会抛异常。
        """
        if not password_encrypted:
            return None, "数据库配置密码为空"
        try:
            password = EncryptionUtils.decrypt(password_encrypted)
            return password, None
        except Exception as e:
            msg = str(e) or "未知错误"
            logger.error(f"数据库配置 {config_id} 密码解密失败: {msg}")
            return None, f"密码解密失败: {msg}，请编辑该连接重新保存密码"
```

- [ ] **Step 2: 在 `get_all_configs()` 中跳过解密失败的配置**

修改 `backend/app/services/database_tool_service.py` 第 496-560 行附近的 `get_all_configs` 方法。

原代码：

```python
                for row in rows:
                    password = None
                    if include_password:
                        try:
                            password = EncryptionUtils.decrypt(
                                row["password_encrypted"]
                            )
                        except Exception:
                            password = None
```

改为：

```python
                for row in rows:
                    password = None
                    if include_password:
                        password, _ = DatabaseToolService._decrypt_password(
                            row["password_encrypted"], row["id"]
                        )
```

- [ ] **Step 3: 在 `get_databases_list()` 中使用 helper 并返回友好错误**

修改 `backend/app/services/database_tool_service.py` 第 1086-1183 行的 `get_databases_list` 方法。

原代码：

```python
        try:
            password = EncryptionUtils.decrypt(config_row["password_encrypted"])
        except Exception:
            raise ValueError("Failed to decrypt password")
```

改为：

```python
        password, error = DatabaseToolService._decrypt_password(
            config_row["password_encrypted"], config_id
        )
        if error:
            raise ValueError(error)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/database_tool_service.py
git commit -m "fix: 数据库配置密码解密失败时返回友好业务错误"
```

---

### Task 4: 路由层捕获解密异常并返回 400

**Files:**
- Modify: `backend/app/routes/database_tool.py:56-70`, `backend/app/routes/database_tool.py:179-189`

**目标：** 当 `get_all_configs` 或 `get_databases_list` 因密码解密失败抛 `ValueError` 时，路由层返回 400 而不是 500。

- [ ] **Step 1: 修改 `get_databases()` 路由**

原代码（第 56-70 行）：

```python
@router.get("/databases", response_model=List[DatabaseConfigResponse])
async def get_databases(
    include_password: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
    current_user=Depends(get_current_user),
):
    """Get all database configurations for the current user"""
    if include_password and getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=403, detail="Permission denied: Admin access required"
        )
    return DatabaseToolService.get_all_configs(
        user_id, include_password=include_password
    )
```

改为：

```python
@router.get("/databases", response_model=List[DatabaseConfigResponse])
async def get_databases(
    include_password: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
    current_user=Depends(get_current_user),
):
    """Get all database configurations for the current user"""
    if include_password and getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=403, detail="Permission denied: Admin access required"
        )
    try:
        return DatabaseToolService.get_all_configs(
            user_id, include_password=include_password
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: 修改 `get_databases_list()` 路由**

原代码（第 179-189 行）：

```python
@router.get("/databases/{id}/databases", response_model=List[str])
async def get_databases_list(
    id: str = PathParam(..., description="Configuration ID"),
    user_id: str = Depends(get_current_user_id),
):
    """List databases for a connection"""
    try:
        return DatabaseToolService.get_databases_list(user_id, id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

改为：

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

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/database_tool.py
git commit -m "fix: database-tool 路由层对密码解密失败返回 400"
```

---

### Task 5: 重启后端并浏览器验证

**Files:**
- 无新增或修改文件

- [ ] **Step 1: 重启后端**

```bash
python dev-services.py restart backend
```

观察终端输出，确认后端启动无报错。

- [ ] **Step 2: 浏览器访问 database-tool 页面**

使用浏览器打开：`http://localhost:5178/tools/database-tool`

- 登录测试账号（peanut / Peanut2817*#）。
- 展开多个数据库连接，确认无 500/连接关闭报错。
- 在 SQL Console 执行一条简单查询（如 `SELECT 1`），确认正常返回。

- [ ] **Step 3: 静置复现测试**

保持 database-tool 页面打开且不操作 30 分钟以上，然后再次：

- 展开/刷新某个连接
- 执行一次搜索或 SQL
- 确认不再出现 `server closed the connection unexpectedly`

- [ ] **Step 4: 检查后端日志**

查看 `logs/backend_后端.log`，确认：

- 无新增的 `Decryption failed` 导致的 500
- 无新增的 `server closed the connection unexpectedly` 异常堆栈

- [ ] **Step 5: Commit（如需要）**

如果验证过程中没有代码改动，无需额外 commit。

---

## Self-Review Checklist

- [x] **Spec coverage:** 设计文档中的三项改动（连接池健康检查、连接回收周期、密码解密降级）分别对应 Task 1/2/3/4。
- [x] **Placeholder scan:** 无 TBD/TODO/"实现 later"/"适当处理" 等占位描述；所有代码块均为可直接使用的示例。
- [x] **Type consistency:** `_decrypt_password` 返回 `tuple[str | None, str | None]`，与调用处 `password, error = ...` 一致；`get_pooled_db_connection` 返回值类型未变。
- [x] **File paths:** 所有文件路径均为项目中的绝对路径。
- [x] **Test/Verify:** Task 5 包含后端重启命令、浏览器操作步骤、日志检查点。

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-12-database-tool-connection-error.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
