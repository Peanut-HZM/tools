## 1. 后端认证基础

- [ ] 1.1 创建 User 模型 (`backend/app/models/user.py`)
- [ ] 1.2 创建用户相关的 Schema (`backend/app/schemas/user.py`, `backend/app/schemas/auth.py`)
- [ ] 1.3 实现 JWT 工具函数 (`backend/app/utils/jwt.py`)
- [ ] 1.4 添加 JWT 配置到 config.py
- [ ] 1.5 实现认证 API 路由 (`backend/app/routes/auth.py`)
- [ ] 1.6 实现 `get_current_user_id` 依赖注入
- [ ] 1.7 注册 auth 路由到 main.py

## 2. 消息和文件 CRUD

- [ ] 2.1 实现消息编辑 API (`PUT /messages/{id}`)
- [ ] 2.2 实现消息删除 API (`DELETE /messages/{id}`)
- [ ] 2.3 实现文件更新 API (`PUT /files/{id}`)
- [ ] 2.4 验证文件删除 API 是否已存在并正常工作
- [ ] 2.5 在服务层添加权限验证逻辑

## 3. 前端认证

- [ ] 3.1 创建 AuthContext (`src/contexts/AuthContext.tsx`)
- [ ] 3.2 创建 authStore (`src/stores/authStore.ts`)
- [ ] 3.3 实现 LoginForm 组件
- [ ] 3.4 实现 RegisterForm 组件
- [ ] 3.5 实现 ProtectedRoute 组件
- [ ] 3.6 实现 token 管理和自动刷新
- [ ] 3.7 集成认证到 API 调用 (axios interceptor)

## 4. 前端 CRUD UI

- [ ] 4.1 MessagePanel 添加编辑消息功能
- [ ] 4.2 MessagePanel 添加删除消息功能
- [ ] 4.3 FilePanel 添加重命名文件功能
- [ ] 4.4 FilePanel 添加删除文件功能
- [ ] 4.5 CrossShareMain 添加用户信息显示
- [ ] 4.6 CrossShareMain 添加退出登录功能

## 5. 测试和清理

- [ ] 5.1 编写后端 JWT 工具函数单元测试
- [ ] 5.2 编写认证 API 集成测试
- [ ] 5.3 测试消息 CRUD 功能
- [ ] 5.4 测试文件 CRUD 功能
- [ ] 5.5 测试前端认证流程
- [ ] 5.6 清理调试代码和日志
- [ ] 5.7 更新文档和 README
