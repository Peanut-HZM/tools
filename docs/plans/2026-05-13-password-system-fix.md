# 密码系统排查与修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 消除密码系统重复代码、修复硬编码密钥安全隐患、增强可观测性以排查跨设备登录问题

**Architecture:** 保持现有 bcrypt + PostgreSQL 架构不变，仅优化配置层和审计层。实施顺序 C→B→A：先统一代码入口减少风险面，再修复密钥配置，最后添加审计日志和诊断接口。

**Tech Stack:** Python 3.10+, FastAPI, Pydantic Settings, bcrypt/passlib, PostgreSQL, SQLAlchemy

---

## Task 1: 从 jwt.py 中移除未使用的密码函数

**Files:**
- Modify: `backend/app/utils/jwt.py:15-17`（移除 pwd_context 导入和定义）
- Modify: `backend/app/utils/jwt.py:78-102`（移除 hash_password 和 verify_password）

**Step 1: 确认无外部引用**

Run:
```bash
cd backend
grep -rn "from app.utils.jwt import.*hash_password\|from app.utils.jwt import.*verify_password\|jwt\.hash_password\|jwt\.verify_password" app --include="*.py" | grep -v __pycache__
```
Expected: 无输出（确认没有任何地方引用 jwt.py 中的这两个函数）

**Step 2: 修改 jwt.py**

移除 `pwd_context` 定义（第15-16行）和 `hash_password`/`verify_password` 函数（第78-102行）：

```python
# 删除第15-17行:
# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 删除第78-102行:
def hash_password(password: str) -> str:
    ...

def verify_password(plain_password: str, hashed_password: str) -> bool:
    ...
```

同时移除顶部未使用的导入 `from passlib.context import CryptContext`。

修改后 jwt.py 只保留 JWT 相关函数：create_access_token, verify_token, get_user_from_token。

**Step 3: 语法检查**

Run: `python -m py_compile app/utils/jwt.py`
Expected: 无输出（通过编译）

**Step 4: Commit**

```bash
git add backend/app/utils/jwt.py
git commit -m "refactor: 从 jwt.py 中移除未使用的密码函数，统一由 auth_service 处理"
```

---

## Task 2: 将 auth_service 的密码函数设为模块级工具函数

**Files:**
- Create: `backend/app/utils/password_utils.py`（扩展已有文件）

**Step 1: 查看现有 password_utils.py**

Run: `cat backend/app/utils/password_utils.py`

**Step 2: 在 password_utils.py 中添加密码哈希/验证函数**

```python
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希（截断至72字节）"""
    truncated = password[:72]
    return _pwd_context.hash(truncated)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配 bcrypt 哈希"""
    truncated = plain_password[:72]
    return _pwd_context.verify(truncated, hashed_password)
```

**Step 3: 修改 auth_service.py 使用新的模块级函数**

Modify: `backend/app/services/auth_service.py:32-33`

将：
```python
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```
改为导入：
```python
from app.utils.password_utils import hash_password, verify_password
```

然后修改 `auth_service.py` 中的方法：
- `_hash_password` 改为调用 `hash_password(password)`
- `_verify_password` 改为调用 `verify_password(plain_password, hashed_password)`
- `hash_password` 公共方法改为调用 `hash_password(password)`
- `verify_password` 公共方法改为调用 `verify_password(plain_password, hashed_password)`

**Step 4: 语法检查**

Run:
```bash
cd backend
python -m py_compile app/utils/password_utils.py
python -m py_compile app/services/auth_service.py
```
Expected: 无输出

**Step 5: Commit**

```bash
git add backend/app/utils/password_utils.py backend/app/services/auth_service.py
git commit -m "refactor: 将密码哈希/验证统一提取到 password_utils 模块"
```

---

## Task 3: 运行后端验证 C 部分无回归

**Files:**
- Test: 启动后端验证

**Step 1: 启动后端服务**

Run:
```bash
cd /Users/huazhongmin/IdeaProjects/tools
source backend/venv/bin/activate
python dev-services.py status
```

如果后端未运行：
```bash
python dev-services.py start
sleep 15
python dev-services.py status
```

Expected: Backend 后端状态为"运行中"

**Step 2: 用浏览器验证登录功能正常**

访问 http://localhost:5178，尝试用现有账号登录。
Expected: 登录成功，无 Console 错误。

**Step 3: Commit（如有其他未提交的 C 部分改动）**

---

## Task 4: 修改 config.py 移除硬编码密钥默认值

**Files:**
- Modify: `backend/app/config/config.py:48-53`

**Step 1: 修改配置类**

将：
```python
    # Security
    JWT_SECRET_KEY: str = "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4="
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 天
    DB_ENCRYPTION_KEY: str = (
        "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4="  # Default key for dev
    )
```

改为：
```python
    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 天
    DB_ENCRYPTION_KEY: str
```

**Step 2: 语法检查**

Run: `cd backend && python -m py_compile app/config/config.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/config/config.py
git commit -m "security: 移除 JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 的硬编码默认值"
```

---

## Task 5: 更新 .env 文件添加密钥配置

**Files:**
- Modify: `backend/.env`

**Step 1: 查看现有 .env 内容**

Run: `cat backend/.env`

**Step 2: 追加密钥配置**

在 `backend/.env` 末尾追加：

```bash
# 安全密钥配置（生产环境请使用随机生成的强密钥）
# 生成命令: python backend/scripts/generate_keys.py
JWT_SECRET_KEY=VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4=
DB_ENCRYPTION_KEY=VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4=
```

注意：这里暂时保留原有值以确保现有部署不中断，但密钥已从代码中移出到配置文件。

**Step 3: 验证配置读取**

Run:
```bash
cd backend
source venv/bin/activate
python -c "from app.config.config import settings; print('JWT:', settings.JWT_SECRET_KEY[:10] + '...'); print('DB:', settings.DB_ENCRYPTION_KEY[:10] + '...')"
```
Expected: 输出密钥前10字符，无异常

**Step 4: Commit**

```bash
git add backend/.env
git commit -m "chore: 在 .env 中添加 JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 配置"
```

---

## Task 6: 创建密钥生成脚本

**Files:**
- Create: `backend/scripts/generate_keys.py`

**Step 1: 创建脚本目录和文件**

```bash
mkdir -p backend/scripts
```

```python
"""
生成安全的随机密钥脚本

Usage:
    python scripts/generate_keys.py

输出可直接复制到 .env 文件中
"""
import secrets
import base64


def generate_key(length: int = 32) -> str:
    """生成 URL-safe 的随机密钥"""
    return secrets.token_urlsafe(length)


def main():
    jwt_key = generate_key(32)
    db_key = generate_key(32)

    print("# 将以下内容复制到 backend/.env 文件中")
    print("# 注意：修改密钥后，已颁发的 JWT Token 将失效，用户需要重新登录")
    print()
    print(f"JWT_SECRET_KEY={jwt_key}")
    print(f"DB_ENCRYPTION_KEY={db_key}")


if __name__ == "__main__":
    main()
```

**Step 2: 验证脚本运行**

Run:
```bash
cd backend
source venv/bin/activate
python scripts/generate_keys.py
```
Expected: 输出两行密钥配置，格式正确

**Step 3: Commit**

```bash
git add backend/scripts/generate_keys.py
git commit -m "feat: 添加密钥生成脚本 generate_keys.py"
```

---

## Task 7: 在 main.py 启动时添加密钥安全校验

**Files:**
- Modify: `backend/app/main.py:98-148`（lifespan 函数中）

**Step 1: 在 lifespan 启动逻辑中添加校验**

在 `backend/app/main.py` lifespan 函数中，在 `logger.info("Starting application...")` 之后添加：

```python
    # 密钥安全校验
    try:
        _check_security_settings()
    except Exception as e:
        logger.warning(f"安全校验未通过: {e}")

    ...


def _check_security_settings():
    """检查安全密钥配置是否合规"""
    from app.config.config import settings

    # 已知的硬编码默认值（需要替换）
    DEFAULT_KEYS = [
        "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4=",
    ]

    if settings.JWT_SECRET_KEY in DEFAULT_KEYS:
        logger.warning("JWT_SECRET_KEY 使用了默认硬编码值，生产环境请务必更换！运行: python scripts/generate_keys.py")

    if settings.DB_ENCRYPTION_KEY in DEFAULT_KEYS:
        logger.warning("DB_ENCRYPTION_KEY 使用了默认硬编码值，生产环境请务必更换！")

    if settings.JWT_SECRET_KEY == settings.DB_ENCRYPTION_KEY:
        logger.warning("JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 相同，建议配置为不同的密钥")

    if len(settings.JWT_SECRET_KEY) < 32:
        logger.warning("JWT_SECRET_KEY 长度不足 32 字符，建议更换为更长的随机密钥")

    if len(settings.DB_ENCRYPTION_KEY) < 32:
        logger.warning("DB_ENCRYPTION_KEY 长度不足 32 字符，建议更换为更长的随机密钥")
```

**Step 2: 语法检查**

Run: `cd backend && python -m py_compile app/main.py`
Expected: 无输出

**Step 3: 重启后端并观察日志**

Run:
```bash
cd /Users/huazhongmin/IdeaProjects/tools
source backend/venv/bin/activate
python dev-services.py restart
sleep 15
tail -20 logs/dev-services.log
```
Expected: 日志中出现警告：`JWT_SECRET_KEY 使用了默认硬编码值...`

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: 启动时添加安全密钥合规校验"
```

---

## Task 8: 扩展密码审计日志表结构

**Files:**
- Modify: `backend/app/models/password_log_models.py`
- Create: `backend/app/db/migrate_password_audit.sql`

**Step 1: 修改模型文件**

将 `backend/app/models/password_log_models.py` 完整替换为：

```python
"""
密码审计日志模型
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import INET
from datetime import datetime
from app.models.base import Base


class PasswordAuditLog(Base):
    """密码审计日志表（记录登录、修改密码、重置密码等操作）"""
    __tablename__ = "password_audit_logs"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True)           # 操作用户 ID
    action_type = Column(String(20), nullable=False, default="login")   # 操作类型: login / change_password / admin_reset
    success = Column(Boolean, nullable=False, default=True)             # 是否成功
    error_message = Column(Text)                                         # 错误信息（失败时）
    ip_address = Column(INET)                                           # 请求 IP 地址
    device_info = Column(Text)                                           # 设备信息（User-Agent 等）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_audit_user_id', 'user_id'),
        Index('idx_audit_action_type', 'action_type'),
        Index('idx_audit_created_at', 'created_at'),
        Index('idx_audit_user_action', 'user_id', 'action_type'),
    )
```

**Step 2: 创建迁移 SQL**

```sql
-- 兼容已有 password_reset_logs 表的迁移脚本
-- 如果表已存在则重命名并添加新列，否则创建新表

DO $$
BEGIN
    -- 检查旧表是否存在
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'password_reset_logs') THEN
        -- 重命名旧表
        ALTER TABLE password_reset_logs RENAME TO password_audit_logs;

        -- 添加新列（如果不存在）
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS action_type VARCHAR(20) DEFAULT 'admin_reset';
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE;
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS error_message TEXT;
        ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS device_info TEXT;

        -- 重命名旧列以符合新语义
        ALTER TABLE password_audit_logs RENAME COLUMN reset_by_user_id TO actor_user_id;

        -- 创建新索引
        CREATE INDEX IF NOT EXISTS idx_audit_user_id ON password_audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_action_type ON password_audit_logs(action_type);
        CREATE INDEX IF NOT EXISTS idx_audit_created_at ON password_audit_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_user_action ON password_audit_logs(user_id, action_type);
    ELSE
        -- 创建新表
        CREATE TABLE password_audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            action_type VARCHAR(20) NOT NULL DEFAULT 'login',
            success BOOLEAN NOT NULL DEFAULT TRUE,
            error_message TEXT,
            ip_address INET,
            device_info TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor_user_id VARCHAR(36)
        );

        CREATE INDEX idx_audit_user_id ON password_audit_logs(user_id);
        CREATE INDEX idx_audit_action_type ON password_audit_logs(action_type);
        CREATE INDEX idx_audit_created_at ON password_audit_logs(created_at);
        CREATE INDEX idx_audit_user_action ON password_audit_logs(user_id, action_type);
    END IF;
END $$;
```

**Step 3: Commit**

```bash
git add backend/app/models/password_log_models.py backend/app/db/migrate_password_audit.sql
git commit -m "feat: 扩展密码审计日志模型，支持登录/修改密码/重置密码全记录"
```

---

## Task 9: 在 auth_service 中添加审计日志记录

**Files:**
- Modify: `backend/app/services/auth_service.py`

**Step 1: 在登录方法中添加审计日志**

在 `login()` 方法（第287行附近）中，修改返回前添加日志记录：

```python
    def login(self, login_data: UserLogin, ip_address: Optional[str] = None,
              device_info: Optional[str] = None) -> AuthResponse:
        # ... 原有逻辑不变 ...
        user = self._get_user_by_username(login_data.username)

        if not user:
            self._log_audit(
                user_id="", action_type="login", success=False,
                error_message="用户不存在", ip_address=ip_address, device_info=device_info
            )
            raise ValueError("Invalid username or password")

        if not verify_password(login_data.password, user.hashed_password):
            self._log_audit(
                user_id=user.user_id, action_type="login", success=False,
                error_message="密码不正确", ip_address=ip_address, device_info=device_info
            )
            raise ValueError("Invalid username or password")

        # 登录成功
        self._log_audit(
            user_id=user.user_id, action_type="login", success=True,
            ip_address=ip_address, device_info=device_info
        )

        # Generate token ...
```

注意：需要修改 login 方法签名，添加 `ip_address` 和 `device_info` 参数。这会影响到 `auth.py` 中的调用。

**Step 2: 在修改密码方法中添加审计日志**

在 `change_password()` 方法中，在成功和失败时都记录：

```python
    def change_password(self, user_id: str, old_password: str, new_password: str,
                        ip_address: Optional[str] = None,
                        device_info: Optional[str] = None) -> tuple[bool, str]:
        # ... 原有逻辑 ...
        # 验证旧密码失败
        if not verify_password(old_password, row['password_hash']):
            self._log_audit(
                user_id=user_id, action_type="change_password", success=False,
                error_message="当前密码不正确", ip_address=ip_address, device_info=device_info
            )
            return False, "当前密码不正确"

        # ... 更新密码 ...
        conn.commit()

        self._log_audit(
            user_id=user_id, action_type="change_password", success=True,
            ip_address=ip_address, device_info=device_info
        )
        return True, "密码修改成功"
```

**Step 3: 添加 _log_audit 辅助方法**

在 AuthService 类中添加：

```python
    def _log_audit(self, user_id: str, action_type: str, success: bool,
                   error_message: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   device_info: Optional[str] = None) -> None:
        """记录密码审计日志"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO password_audit_logs
                       (id, user_id, action_type, success, error_message, ip_address, device_info, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), user_id, action_type, success,
                     error_message, ip_address, device_info, datetime.utcnow())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
        finally:
            conn.close()
```

**Step 4: Commit**

```bash
git add backend/app/services/auth_service.py
git commit -m "feat: 在登录和密码修改流程中添加审计日志记录"
```

---

## Task 10: 修改 auth 路由传递 IP 和设备信息

**Files:**
- Modify: `backend/app/routes/auth.py`

**Step 1: 修改 login 路由**

将：
```python
@router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLogin):
    try:
        auth_service = get_auth_service()
        return auth_service.login(login_data)
```

改为：
```python
@router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLogin, request: Request):
    try:
        auth_service = get_auth_service()
        ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", request.client.host))
        device_info = request.headers.get("User-Agent", "")
        return auth_service.login(login_data, ip_address=ip_address, device_info=device_info)
```

**Step 2: 修改 change_password 路由**

类似地修改 `change_password` 路由，传递 `request` 获取 IP 和 User-Agent。

**Step 3: 语法检查**

Run: `cd backend && python -m py_compile app/routes/auth.py`
Expected: 无输出

**Step 4: Commit**

```bash
git add backend/app/routes/auth.py
git commit -m "feat: 登录/修改密码接口传递客户端 IP 和设备信息用于审计"
```

---

## Task 11: 添加管理员诊断接口

**Files:**
- Modify: `backend/app/routes/admin.py`

**Step 1: 在 admin.py 中添加诊断路由**

在 admin.py 末尾添加：

```python
from app.utils.password_utils import verify_password


@router.get("/auth/diagnosis")
async def auth_diagnosis(admin_user: UserResponse = Depends(get_admin_user)):
    """
    密码系统诊断接口（管理员专用）

    返回:
        - 数据库连接状态
        - bcrypt 验证测试
        - 密钥配置状态
    """
    from app.config.config import settings
    from app.config.database import test_connection

    result = {
        "database_connected": False,
        "bcrypt_test": False,
        "jwt_key_status": "unknown",
        "db_key_status": "unknown",
        "warnings": []
    }

    # 测试数据库连接
    try:
        result["database_connected"] = test_connection()
    except Exception as e:
        result["warnings"].append(f"数据库连接测试失败: {e}")

    # 测试 bcrypt 验证
    try:
        test_pwd = "test_password_123"
        from app.utils.password_utils import hash_password
        hashed = hash_password(test_pwd)
        result["bcrypt_test"] = verify_password(test_pwd, hashed)
    except Exception as e:
        result["warnings"].append(f"bcrypt 测试失败: {e}")

    # 密钥状态
    DEFAULT_KEYS = ["VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4="]

    if settings.JWT_SECRET_KEY in DEFAULT_KEYS:
        result["jwt_key_status"] = "default_hardcoded"
        result["warnings"].append("JWT_SECRET_KEY 使用了默认硬编码值")
    elif len(settings.JWT_SECRET_KEY) < 32:
        result["jwt_key_status"] = "too_short"
        result["warnings"].append("JWT_SECRET_KEY 长度不足")
    else:
        result["jwt_key_status"] = "ok"

    if settings.DB_ENCRYPTION_KEY in DEFAULT_KEYS:
        result["db_key_status"] = "default_hardcoded"
        result["warnings"].append("DB_ENCRYPTION_KEY 使用了默认硬编码值")
    elif len(settings.DB_ENCRYPTION_KEY) < 32:
        result["db_key_status"] = "too_short"
        result["warnings"].append("DB_ENCRYPTION_KEY 长度不足")
    else:
        result["db_key_status"] = "ok"

    if settings.JWT_SECRET_KEY == settings.DB_ENCRYPTION_KEY:
        result["warnings"].append("JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 相同")

    return result


@router.get("/users/{user_id}/login-history")
async def user_login_history(
    user_id: str,
    limit: int = 50,
    admin_user: UserResponse = Depends(get_admin_user)
):
    """
    查询用户登录/密码操作历史（管理员专用）

    Args:
        user_id: 用户 ID
        limit: 返回记录数量（默认50条）
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT action_type, success, error_message, ip_address,
                          device_info, created_at
                   FROM password_audit_logs
                   WHERE user_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return {
                "user_id": user_id,
                "total": len(rows),
                "records": [
                    {
                        "action_type": r["action_type"],
                        "success": r["success"],
                        "error_message": r["error_message"],
                        "ip_address": str(r["ip_address"]) if r["ip_address"] else None,
                        "device_info": r["device_info"],
                        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    }
                    for r in rows
                ]
            }
    finally:
        conn.close()
```

**Step 2: 语法检查**

Run: `cd backend && python -m py_compile app/routes/admin.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add backend/app/routes/admin.py
git commit -m "feat: 添加管理员密码系统诊断接口和登录历史查询接口"
```

---

## Task 12: 执行数据库迁移并验证端到端

**Files:**
- Test: 数据库迁移 + 接口验证

**Step 1: 执行数据库迁移**

Run:
```bash
cd backend
source venv/bin/activate
psql "$DATABASE_URL" -f app/db/migrate_password_audit.sql
# 或（替换为实际用户名/主机）：
# psql "postgresql://<user>:<password>@<host>:5432/tools" -f app/db/migrate_password_audit.sql
```

Expected: 成功执行，无报错

**Step 2: 重启后端服务**

Run:
```bash
cd /Users/huazhongmin/IdeaProjects/tools
source backend/venv/bin/activate
python dev-services.py restart
sleep 20
python dev-services.py status
```

Expected: Backend 后端和 Toolbox 前端都运行中

**Step 3: 浏览器验证**

1. 访问 http://localhost:5178，正常登录
2. 进入个人中心修改密码
3. 用新密码重新登录，确认正常
4. 检查后端日志是否有安全警告

Expected: 所有操作正常，Console 无报错

**Step 4: 验证诊断接口**

登录管理员账号，访问：
```
GET http://127.0.0.1:8000/api/admin/auth/diagnosis
```

Expected: 返回 JSON，包含 `database_connected: true`, `bcrypt_test: true`, `warnings` 中包含默认密钥警告

**Step 5: Commit（如有未提交的验证修复）**

---

## 实施完成后验证清单

- [ ] C 部分: `jwt.py` 中无 `hash_password`/`verify_password`，所有密码操作通过 `password_utils`
- [ ] B 部分: `config.py` 中无硬编码密钥默认值，`.env` 中包含密钥配置
- [ ] B 部分: 启动日志中出现安全密钥警告（提示更换默认密钥）
- [ ] B 部分: `scripts/generate_keys.py` 可正常运行并生成随机密钥
- [ ] A 部分: 数据库中 `password_audit_logs` 表存在且有新列
- [ ] A 部分: 登录/修改密码后在审计日志表中有记录
- [ ] A 部分: 管理员诊断接口 `/api/admin/auth/diagnosis` 可正常访问
- [ ] A 部分: 用户登录历史接口 `/api/admin/users/{user_id}/login-history` 可正常访问
- [ ] 端到端: 浏览器中登录、修改密码、重新登录流程正常
