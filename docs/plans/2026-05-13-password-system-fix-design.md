# 密码系统排查与修复设计文档

**日期**: 2026-05-13
**背景**: 用户报告在不同设备启动服务后，修改密码，另一设备使用正确密码无法登录。同时排查发现多处安全隐患。

---

## 问题背景

用户反馈：
1. "用户的密码没有变过，为什么总是会登录不上"
2. "在不同设备启动之后，修改密码了，另一个设备上启动这个服务，使用正确的密码就无法登录了"

## 排查结论

经过代码审查，核心密码逻辑（bcrypt 哈希、验证、修改）本身无 Bug：
- 密码使用 `bcrypt` 哈希，不受密钥影响
- 数据库为共享的远程 PostgreSQL
- `UPDATE users SET password_hash` + `COMMIT` 逻辑正确

但发现以下严重安全隐患和可观测性缺失问题：

### 发现的安全隐患

1. **JWT_SECRET_KEY 硬编码** (`backend/app/config/config.py:48`)
   - 值: `"VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4="`
   - 风险: 任何获得代码的人都能伪造 JWT Token

2. **DB_ENCRYPTION_KEY 硬编码** (`backend/app/config/config.py:51`)
   - 值: 与 JWT 密钥相同
   - 风险: 工具密码加密失去意义，违反密钥分离原则

3. **密码验证代码重复**
   - `backend/app/utils/jwt.py:91-102` 和 `backend/app/services/auth_service.py:238-265` 都实现了 `verify_password`
   - 维护风险: 未来修改时可能遗漏一处

### 可观测性缺失

- 无密码修改审计日志（仅记录管理员重置）
- 登录失败无详细原因记录
- 无诊断接口验证密码系统健康状态

---

## 设计方案

### A. 增强可观测性

#### A1. 审计日志扩展

扩展现有 `password_reset_logs` 表为通用的 `password_audit_logs`：

```sql
-- 扩展现有表（兼容已有数据）
ALTER TABLE password_reset_logs RENAME TO password_audit_logs;
ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS action_type VARCHAR(20) DEFAULT 'admin_reset';
ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE;
ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE password_audit_logs ADD COLUMN IF NOT EXISTS device_info TEXT;
```

记录场景：
- `login` - 用户登录（成功/失败）
- `change_password` - 用户修改密码
- `admin_reset` - 管理员重置密码（已有）

#### A2. 诊断接口（管理员专用）

- `GET /api/admin/auth/diagnosis`
  - 返回: 数据库连接状态、bcrypt 验证测试、密钥配置状态（是否使用默认值）
- `GET /api/admin/users/{user_id}/login-history`
  - 返回: 最近 50 条登录/密码操作记录

### B. 修复硬编码密钥

#### B1. 配置层改动

`backend/app/config/config.py`：
- 移除 `JWT_SECRET_KEY` 和 `DB_ENCRYPTION_KEY` 的硬编码默认值
- 使用 `Field(...)` 标记为必填，或提供更安全的长随机默认值

`backend/.env`：
- 添加 `JWT_SECRET_KEY` 和 `DB_ENCRYPTION_KEY` 配置项

#### B2. 启动时安全校验

在 `backend/app/main.py` 启动时：
- 检查密钥是否为已知默认值，如果是则打印 **ERROR** 级别警告
- 检查密钥长度是否 >= 32 字符

#### B3. 密钥生成脚本

新增 `backend/scripts/generate_keys.py`：
```python
import secrets
jwt_key = secrets.token_urlsafe(32)
db_key = secrets.token_urlsafe(32)
print(f"JWT_SECRET_KEY={jwt_key}")
print(f"DB_ENCRYPTION_KEY={db_key}")
```

### C. 统一密码验证入口

#### C1. 移除重复代码

- `backend/app/utils/jwt.py`：移除 `hash_password` 和 `verify_password`，保留 JWT 相关函数
- 所有引用点统一使用 `auth_service.hash_password()` / `auth_service.verify_password()`

#### C2. 引用点迁移

需要修改的文件：
- `backend/app/routes/admin.py`（如有直接引用）
- `backend/app/api/dependencies.py`（如有直接引用）
- 其他使用了 `jwt.verify_password` 的地方

---

## 实施顺序

1. **C 优先**: 统一入口，消除重复，为后续改动减少风险面
2. **B 次之**: 修复安全配置，提供密钥生成工具
3. **A 最后**: 添加审计日志和诊断接口，用于排查和长期监控

---

## 验证标准

- [ ] `backend/.env` 中配置了独立的 `JWT_SECRET_KEY` 和 `DB_ENCRYPTION_KEY`
- [ ] 启动时不再出现硬编码密钥警告
- [ ] 密码修改后在审计日志中可查询到记录
- [ ] 管理员诊断接口可正常返回密码系统状态
- [ ] `jwt.py` 中无 `verify_password` / `hash_password` 函数，所有密码操作通过 `auth_service`
