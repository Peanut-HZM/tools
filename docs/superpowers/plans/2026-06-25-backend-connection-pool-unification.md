# 后端连接池统一实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `auth_service.py` 等使用直连数据库连接的服务改为使用连接池，解决连接池耗尽导致的保存卡住问题。

**Architecture:** 保持现有数据库操作逻辑不变，仅将 `get_db_connection()` 替换为 `get_pooled_db_connection()`，将 `conn.close()` 替换为 `release_db_connection(conn)`，确保连接正确归还。

**Tech Stack:** Python, FastAPI, SQLAlchemy, psycopg2

---

## 阶段 1：改造 `auth_service.py`（核心文件）

### Task 1: 列出 `auth_service.py` 中所有数据库连接点

**Files:**
- Read: `backend/app/services/auth_service.py`

- [ ] **Step 1: 搜索所有连接点**

运行命令：

```bash
grep -n "get_db_connection()\|conn.close()" backend/app/services/auth_service.py
```

Expected output: 列出所有需要改造的行号。

- [ ] **Step 2: 记录需要改造的方法**

将输出保存到 `.superpowers/sdd/auth_service_db_methods.md`，格式：

```markdown
- `_log_audit`: line 58, 72
- `_get_user_by_username`: line 76
- `_get_user_by_id`: line 232
- ...
```

- [ ] **Step 3: 提交准备文档**

```bash
git add .superpowers/sdd/auth_service_db_methods.md
git commit -m "docs: 记录 auth_service.py 中需要改造的数据库连接点"
```

---

### Task 2: 改造 `_log_audit`、`_get_user_by_username`、`_get_user_by_id`

**Files:**
- Modify: `backend/app/services/auth_service.py`

- [ ] **Step 1: 修改 import**

将第 19 行：

```python
from app.config.database import get_db_connection
```

改为：

```python
from app.config.database import get_pooled_db_connection, release_db_connection
```

- [ ] **Step 2: 修改 `_log_audit`（约第 52-72 行）**

改造前：

```python
    def _log_audit(self, user_id: str, action_type: str, success: bool,
                   error_message: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   device_info: Optional[str] = None,
                   actor_user_id: Optional[str] = None) -> None:
        """记录密码审计日志"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO password_audit_logs
                       (id, user_id, action_type, success, error_message, ip_address, device_info, actor_user_id, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), user_id, action_type, success,
                     error_message, ip_address, device_info, actor_user_id, datetime.utcnow())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
        finally:
            conn.close()
```

改造后：

```python
    def _log_audit(self, user_id: str, action_type: str, success: bool,
                   error_message: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   device_info: Optional[str] = None,
                   actor_user_id: Optional[str] = None) -> None:
        """记录密码审计日志"""
        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO password_audit_logs
                       (id, user_id, action_type, success, error_message, ip_address, device_info, actor_user_id, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), user_id, action_type, success,
                     error_message, ip_address, device_info, actor_user_id, datetime.utcnow())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
        finally:
            release_db_connection(conn)
```

- [ ] **Step 3: 修改 `_get_user_by_username`（约第 74-90 行）**

改造前：

```python
    def _get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    return UserInDB(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        hashed_password=row['password_hash'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
        finally:
            conn.close()
```

改造后：

```python
    def _get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    return UserInDB(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        hashed_password=row['password_hash'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
        finally:
            release_db_connection(conn)
```

- [ ] **Step 4: 修改 `_get_user_by_id`（约第 230-254 行）**

改造前：

```python
    def _get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return UserInDB(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        hashed_password=row['password_hash'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            conn.close()
```

改造后：

```python
    def _get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return UserInDB(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        hashed_password=row['password_hash'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            release_db_connection(conn)
```

- [ ] **Step 5: 运行语法检查**

```bash
cd backend
python -m py_compile app/services/auth_service.py
```

Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/auth_service.py
git commit -m "refactor: auth_service 审计日志和查询方法使用连接池

- _log_audit, _get_user_by_username, _get_user_by_id 改为连接池"
```

---

### Task 3: 改造 `_create_user`、`_update_user`、`_change_password`

**Files:**
- Modify: `backend/app/services/auth_service.py`

- [ ] **Step 1: 修改 `_create_user`（约第 120-160 行）**

查找并改造该函数中的 `get_db_connection()` 和 `conn.close()`。

- [ ] **Step 2: 修改 `_update_user`（约第 180-220 行）**

查找并改造该函数中的 `get_db_connection()` 和 `conn.close()`。

- [ ] **Step 3: 修改 `_change_password`（约第 640-688 行）**

改造前最后部分：

```python
        finally:
            conn.close()
```

改造后：

```python
        finally:
            release_db_connection(conn)
```

- [ ] **Step 4: 运行语法检查**

```bash
cd backend
python -m py_compile app/services/auth_service.py
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/auth_service.py
git commit -m "refactor: auth_service 用户 CRUD 方法使用连接池"
```

---

### Task 4: 改造 `auth_service.py` 剩余方法

**Files:**
- Modify: `backend/app/services/auth_service.py`

- [ ] **Step 1: 使用 sed 批量替换剩余连接点**

运行命令查找剩余位置：

```bash
grep -n "get_db_connection()\|conn.close()" backend/app/services/auth_service.py
```

- [ ] **Step 2: 逐个修改剩余方法**

包括：
- `update_user_role`
- `delete_user`
- 其他数据库操作方法

所有模式：
- `conn = get_db_connection()` → `conn = get_pooled_db_connection()`
- `conn.close()` → `release_db_connection(conn)`

- [ ] **Step 3: 确认无遗漏**

```bash
grep -n "get_db_connection()\|conn.close()" backend/app/services/auth_service.py
```

Expected: 无输出

- [ ] **Step 4: 运行语法检查**

```bash
cd backend
python -m py_compile app/services/auth_service.py
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/auth_service.py
git commit -m "refactor: auth_service 剩余方法全部使用连接池"
```

---

## 阶段 2：改造 `http_client_service.py`

### Task 5: 改造 `http_client_service.py`

**Files:**
- Modify: `backend/app/services/http_client_service.py`

- [ ] **Step 1: 修改 import**

将：

```python
from app.config.database import get_db_connection
```

改为：

```python
from app.config.database import get_pooled_db_connection, release_db_connection
```

- [ ] **Step 2: 批量替换**

- 所有 `conn = get_db_connection()` → `conn = get_pooled_db_connection()`
- 所有 `conn.close()` → `release_db_connection(conn)`

- [ ] **Step 3: 确认无遗漏**

```bash
grep -n "get_db_connection()\|conn.close()" backend/app/services/http_client_service.py
```

Expected: 无输出

- [ ] **Step 4: 运行语法检查**

```bash
cd backend
python -m py_compile app/services/http_client_service.py
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/http_client_service.py
git commit -m "refactor: http_client_service 使用连接池"
```

---

## 阶段 3：检查并改造其他文件

### Task 6: 全局搜索并评估剩余连接点

**Files:**
- Search: `backend/app/` 下所有 `.py` 文件

- [ ] **Step 1: 搜索剩余连接点**

```bash
grep -rn "get_db_connection()" backend/app/ --include="*.py"
```

- [ ] **Step 2: 分类处理**

对于每个结果，判断：
- 如果该文件是业务服务代码 → 改造为连接池
- 如果是测试代码、脚本、一次性工具 → 保持原样
- 如果是初始化代码（如创建表）→ 可以使用连接池或保持原样

- [ ] **Step 3: 改造判定为需要改造的文件**

逐个文件修改，每个文件独立提交。

---

## 阶段 4：验证

### Task 7: 后端重启和基础验证

**Files:**
- All modified backend files

- [ ] **Step 1: 重启后端服务**

```bash
python dev-services.py restart backend
```

Expected: 服务正常启动

- [ ] **Step 2: 测试登录接口**

```bash
curl -X POST http://127.0.0.1:19092/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"peanut","password":"Peanut2817*#"}'
```

Expected: 返回 token

- [ ] **Step 3: 测试保存显示设置**

```bash
TOKEN="your_token_here"
curl -X PUT http://127.0.0.1:19092/api/database-tool/preferences \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"visible_connections": null, "visible_databases": {}}'
```

Expected: 响应时间 < 1s，返回保存结果

- [ ] **Step 4: 检查后端日志**

```bash
tail -50 logs/backend.log | grep -i "QueuePool limit\|TimeoutError"
```

Expected: 无 `QueuePool limit` 或 `TimeoutError` 错误

- [ ] **Step 5: 提交**

```bash
git commit --allow-empty -m "chore: 后端连接池改造完成，验证通过"
```

---

### Task 8: 浏览器验证

**Files:**
- frontend/src/components/Tools/DatabaseTool/components/DisplaySettingsDialog.tsx

- [ ] **Step 1: 启动前端**

```bash
python dev-services.py restart frontend
```

或者：

```bash
cd frontend
npm run dev
```

- [ ] **Step 2: 浏览器操作**

1. 打开 `http://localhost:5178`
2. 登录账号
3. 进入数据库工具
4. 打开显示设置
5. 勾选/取消部分连接
6. 点击保存
7. 观察"保存中..."是否在 1s 内消失

- [ ] **Step 3: 检查 Console 和 Network**

- Console 无错误
- `/preferences` PUT 请求响应时间 < 1s
- 无 pending 请求

- [ ] **Step 4: 提交验证结果**

```bash
git commit --allow-empty -m "verify: 浏览器验证显示设置保存正常"
```

---

## 验证清单

完成所有 Task 后，确认以下事项：

- [ ] `auth_service.py` 中无 `get_db_connection()` 和 `conn.close()`
- [ ] `http_client_service.py` 中无 `get_db_connection()` 和 `conn.close()`
- [ ] 其他需要改造的文件已完成
- [ ] 后端服务正常启动
- [ ] 登录接口正常
- [ ] 保存显示设置响应时间 < 1s
- [ ] 浏览器 Console 无错误
- [ ] 后端日志无 `QueuePool limit` 错误

---

## 回滚方案

如果出现问题：

1. 查看 git log 找到改造前的提交
2. 执行 `git revert` 回退相关提交
3. 临时增加 PostgreSQL `max_connections` 作为应急方案
4. 重启后端服务

---

## 注意事项

1. **连接释放必须配对**：每个 `get_pooled_db_connection()` 必须有对应的 `release_db_connection()`
2. **事务边界**：确保每个请求完成后提交或回滚事务
3. **异常处理**：异常时也要释放连接
4. **不要改造测试代码**：测试文件中的 `get_db_connection()` 保持原样
