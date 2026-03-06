# CrossShare 认证与 CRUD 功能增强设计文档

**日期**: 2026-03-06
**状态**: 已批准
**变更类型**: 功能增强

---

## 1. 概述

### 1.1 背景

CrossShare 设备传传工具目前存在以下问题：
- 用户认证机制不完善（仅有简化的 header 传递 user_id）
- 消息和文件只能查看，无法修改和删除
- 缺乏完善的权限验证机制

### 1.2 目标

- 实现完整的 JWT 用户认证系统
- 为消息和文件添加完整的 CRUD 功能
- 确保用户只能访问和管理自己的资源
- 提供友好的前端操作界面

### 1.3 使用场景

小团队内部使用的跨设备消息和文件同步工具。

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (React + TypeScript)                 │
├─────────────────────────────────────────────────────────────────┤
│  登录/注册页面  │  CrossShare 主页面  │  消息/文件管理组件       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + JWT Token
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        后端 (FastAPI + Python)                   │
├─────────────────────────────────────────────────────────────────┤
│  认证中间件 (JWT 验证)  │  权限验证装饰器                         │
├─────────────────────────────────────────────────────────────────┤
│  设备管理 API  │  消息管理 API  │  文件管理 API  │  配置管理 API  │
│  (增删改查)    │  (增删改查)    │  (增删改查)    │  (增删改查)    │
├─────────────────────────────────────────────────────────────────┤
│                        服务层 (CrossShareService)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据库 (SQLite)                           │
├─────────────────────────────────────────────────────────────────┤
│  users  │  devices  │  messages  │  files  │  configs           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

- **前端**: React 18, TypeScript, Zustand, Tailwind CSS
- **后端**: FastAPI, Python 3.10+, SQLAlchemy, Pydantic
- **认证**: JWT (HS256 算法)
- **密码加密**: bcrypt

---

## 3. 数据模型

### 3.1 新增 User 模型

```python
class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 3.2 现有模型（无需修改）

现有模型均已有 `user_id` 字段，通过外键或逻辑关联与 User 模型关联：

- `Device.user_id` → User.id
- `CrossMessage.user_id` → User.id
- `CrossFile.user_id` → User.id
- `CrossShareConfig.user_id` → User.id

### 3.3 JWT 配置

```python
# config.py
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 天
```

---

## 4. API 设计

### 4.1 认证 API（新增）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 否 |
| POST | `/api/auth/login` | 用户登录 | 否 |
| POST | `/api/auth/logout` | 用户登出 | 否 |
| GET | `/api/auth/me` | 获取当前用户 | 是 |
| POST | `/api/auth/refresh` | 刷新 token | 是 |
| POST | `/api/auth/change-password` | 修改密码 | 是 |

### 4.2 消息 API（增强）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/cross-share/messages` | 获取消息列表 | 是 |
| POST | `/api/cross-share/messages` | 发送消息 | 是 |
| PUT | `/api/cross-share/messages/{id}` | 编辑消息 | 是 |
| DELETE | `/api/cross-share/messages/{id}` | 删除消息 | 是 |
| PATCH | `/api/cross-share/messages/{id}/read` | 标记已读/未读 | 是 |

### 4.3 文件 API（增强）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/cross-share/files` | 获取文件列表 | 是 |
| POST | `/api/cross-share/files/upload` | 上传文件 | 是 |
| PUT | `/api/cross-share/files/{id}` | 更新文件信息 | 是 |
| DELETE | `/api/cross-share/files/{id}` | 删除文件 | 是 |
| POST | `/api/cross-share/files/{id}/download` | 获取下载链接 | 是 |

---

## 5. 前端设计

### 5.1 新增组件

| 组件名 | 路径 | 功能 |
|--------|------|------|
| `LoginForm` | `src/components/Auth/LoginForm.tsx` | 登录表单 |
| `RegisterForm` | `src/components/Auth/RegisterForm.tsx` | 注册表单 |
| `AuthProvider` | `src/contexts/AuthContext.tsx` | 认证上下文 |
| `ProtectedRoute` | `src/components/Auth/ProtectedRoute.tsx` | 路由保护 |

### 5.2 现有组件增强

| 组件名 | 新增功能 |
|--------|----------|
| `MessagePanel` | 编辑、删除、标记已读/未读 |
| `FilePanel` | 重命名、删除、查看详情 |
| `CrossShareMain` | 用户信息显示、退出登录 |

### 5.3 状态管理

```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
```

---

## 6. 安全设计

### 6.1 密码安全

- 使用 bcrypt 进行密码哈希
- 密码长度要求：8-128 位
- 不存储明文密码

### 6.2 JWT 安全

- 使用 HS256 算法签名
- Token 有效期 7 天
- 支持 token 刷新机制

### 6.3 权限验证

- 所有 API 通过 `get_current_user_id` 获取当前用户
- 服务层所有查询通过 `user_id` 过滤
- 删除/修改操作验证资源所有权

### 6.4 其他安全措施

- CORS 限制只允许受信任的域名
- 输入验证（长度、格式）
- 使用 SQLAlchemy ORM 防止 SQL 注入
- 前端对用户输入进行转义防止 XSS

---

## 7. 错误处理

| 错误码 | 场景 | 前端处理 |
|--------|------|----------|
| 401 | token 无效/过期 | 跳转登录页 |
| 403 | 无权访问资源 | 显示错误提示 |
| 404 | 资源不存在 | 显示错误提示 |
| 409 | 用户名/邮箱已存在 | 显示表单错误 |

---

## 8. 测试计划

| 测试类型 | 测试内容 |
|----------|----------|
| 单元测试 | JWT 工具函数、服务层逻辑 |
| 集成测试 | API 端点认证和权限验证 |
| E2E 测试 | 注册→登录→发送消息→编辑→删除 |

---

## 9. 实施任务

### 阶段 1: 后端认证基础
1. 创建 User 模型和数据库迁移
2. 实现 JWT 工具函数（签发、验证）
3. 实现认证 API（注册、登录、获取当前用户）
4. 实现 `get_current_user_id` 依赖注入

### 阶段 2: 消息和文件 CRUD
5. 实现消息编辑 API（PUT /messages/{id}）
6. 实现消息删除 API（DELETE /messages/{id}）
7. 实现文件更新 API（PUT /files/{id}）
8. 实现文件删除 API（确认已有）

### 阶段 3: 前端认证
9. 创建 AuthContext 和 authStore
10. 实现 LoginForm 和 RegisterForm 组件
11. 实现 ProtectedRoute 路由保护
12. 集成 token 管理到 API 调用

### 阶段 4: 前端 CRUD UI
13. MessagePanel 添加编辑、删除功能
14. FilePanel 添加重命名、删除功能
15. 添加用户信息显示和退出登录

### 阶段 5: 测试和清理
16. 编写单元测试
17. 端到端测试验证
18. 清理调试代码和日志

---

## 10. 变更文件列表

### 后端文件
- `backend/app/models/user.py` (新增)
- `backend/app/schemas/user.py` (新增)
- `backend/app/schemas/auth.py` (新增)
- `backend/app/utils/jwt.py` (新增)
- `backend/app/routes/auth.py` (新增)
- `backend/app/api/routes/cross_share.py` (修改)
- `backend/app/services/cross_share_service.py` (修改)
- `backend/app/config/config.py` (修改)
- `backend/app/main.py` (修改)

### 前端文件
- `frontend/src/contexts/AuthContext.tsx` (新增)
- `frontend/src/stores/authStore.ts` (新增)
- `frontend/src/components/Auth/LoginForm.tsx` (新增)
- `frontend/src/components/Auth/RegisterForm.tsx` (新增)
- `frontend/src/components/Auth/ProtectedRoute.tsx` (新增)
- `frontend/src/components/Tools/CrossShare/MessagePanel.tsx` (修改)
- `frontend/src/components/Tools/CrossShare/FilePanel.tsx` (修改)
- `frontend/src/components/Tools/CrossShare/CrossShareMain.tsx` (修改)
- `frontend/src/services/auth.ts` (新增)
- `frontend/src/services/crossShare.ts` (修改)

---

## 11. 验收标准

- [ ] 用户可以注册和登录
- [ ] 未登录用户无法访问 CrossShare 功能
- [ ] 用户只能查看和管理自己的消息和文件
- [ ] 消息可以编辑和删除
- [ ] 文件可以重命名和删除
- [ ] token 过期后自动刷新或跳转登录
- [ ] 所有 API 通过自动化测试

---

## 12. 参考资料

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/)
- [bcrypt 最佳实践](https://github.com/pyca/bcrypt/)
