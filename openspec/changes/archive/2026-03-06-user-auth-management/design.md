# CrossShare 认证与 CRUD 功能增强 - 详细设计

## 架构设计

### 系统架构

```
前端 (React) ←→ JWT Token ←→ 后端 (FastAPI) ←→ SQLite
```

### 认证流程

1. 用户注册/登录 → 后端验证 → 签发 JWT Token
2. 前端存储 token (localStorage)
3. 后续请求携带 token (Authorization: Bearer <token>)
4. 后端验证 token → 解析用户 ID → 处理请求

## 数据模型

### User 表（新增）

```python
class User(Base):
    id: str  # primary key
    username: str  # unique
    email: str  # unique
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 现有表（无需修改）

- Device、CrossMessage、CrossFile、CrossShareConfig 都已有 user_id 字段

## API 设计

### 认证 API

- POST `/api/auth/register` - 用户注册
- POST `/api/auth/login` - 用户登录
- GET `/api/auth/me` - 获取当前用户
- POST `/api/auth/refresh` - 刷新 token

### 消息 API

- PUT `/api/cross-share/messages/{id}` - 编辑消息
- DELETE `/api/cross-share/messages/{id}` - 删除消息

### 文件 API

- PUT `/api/cross-share/files/{id}` - 更新文件信息
- DELETE `/api/cross-share/files/{id}` - 删除文件

## 前端组件

### 新增组件

- LoginForm - 登录表单
- RegisterForm - 注册表单
- AuthContext - 认证上下文
- ProtectedRoute - 路由保护

### 修改组件

- MessagePanel - 添加编辑、删除功能
- FilePanel - 添加重命名、删除功能
- CrossShareMain - 添加用户信息显示、退出登录

## 安全设计

- 密码使用 bcrypt 哈希
- JWT 使用 HS256 签名，有效期 7 天
- 所有 API 通过 user_id 过滤确保资源隔离
- CORS 限制、输入验证、防 SQL 注入
