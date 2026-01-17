# Design Document

## Overview

本设计文档描述了将 markdown-editor 项目的前后端功能完整迁移到 tool-aggregation-website 的 backend 和 frontend 中的技术实现方案。迁移后的 markdown-editor 将作为一个工具集成到工具聚合网站中，用户可以通过首页的工具卡片进入使用。迁移过程需要将 Vue.js 前端转换为 React，保持所有功能完整，并集成用户认证系统。

## Architecture

### 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     Browser                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │        React Frontend (Port 3000)                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │  │
│  │  │  Components │  │   Stores    │  │  Routes  │  │  │
│  │  │  (React)    │  │  (Zustand)  │  │  (React  │  │  │
│  │  │             │  │             │  │  Router) │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/REST API + JWT
                          ▼
┌─────────────────────────────────────────────────────────┐
│        Python Backend (FastAPI, Port 8000)              │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  API Routes  │  │   Models    │  │   Services   │  │
│  │  (Markdown   │  │  (Pydantic)  │  │  (File,      │  │
│  │   Editor)    │  │             │  │   Config,    │  │
│  │              │  │             │  │   Search,    │  │
│  │              │  │             │  │   Auth)      │  │
│  └───────────────┘  └─────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              File System (User Isolated)                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  /users/{user_id}/markdown-files/                │  │
│  │    ├── documents/                                 │  │
│  │    ├── notes/                                     │  │
│  │    └── .markdown-editor/config.json               │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

**Frontend:**
- React 18+ with TypeScript
- React Router v6+ (路由管理)
- Zustand (状态管理，替代Pinia)
- Monaco Editor (代码编辑器)
- markdown-it (Markdown解析)
- highlight.js (代码高亮)
- KaTeX (数学公式渲染)
- Mermaid (流程图渲染)
- DOMPurify (XSS防护)
- Tailwind CSS (样式框架)
- Vite (构建工具)

**Backend:**
- Python 3.10+
- FastAPI
- Pydantic (数据验证)
- python-jose (JWT认证)
- passlib (密码加密)
- aiofiles (异步文件操作)
- CORS middleware

## Components and Interfaces

### Frontend组件结构

```
src/
├── components/
│   ├── MarkdownEditor/
│   │   ├── MarkdownEditor.tsx          # 主容器组件
│   │   ├── FileTree/
│   │   │   └── FileTree.tsx            # 文件树组件
│   │   ├── Editor/
│   │   │   └── Editor.tsx              # Monaco编辑器组件
│   │   ├── Preview/
│   │   │   └── Preview.tsx             # Markdown预览组件
│   │   ├── SearchDialog/
│   │   │   └── SearchDialog.tsx        # 搜索对话框组件
│   │   ├── SettingsDialog/
│   │   │   └── SettingsDialog.tsx      # 设置对话框组件
│   │   └── StatusBar/
│   │       └── StatusBar.tsx           # 状态栏组件
│   └── Auth/
│       ├── LoginForm.tsx               # 登录表单组件
│       ├── RegisterForm.tsx            # 注册表单组件
│       └── AuthGuard.tsx                # 认证守卫组件
├── stores/
│   ├── authStore.ts                    # 认证状态管理
│   ├── fileStore.ts                    # 文件状态管理
│   ├── editorStore.ts                  # 编辑器状态管理
│   └── configStore.ts                  # 配置状态管理
├── hooks/
│   ├── useAutoSave.ts                  # 自动保存Hook
│   ├── useFileTree.ts                  # 文件树Hook
│   └── useMarkdownPreview.ts           # Markdown预览Hook
├── api/
│   ├── markdownEditorApi.ts            # Markdown编辑器API
│   └── authApi.ts                      # 认证API
├── types/
│   └── markdownEditor.ts                # TypeScript类型定义
└── routes/
    └── MarkdownEditorRoute.tsx         # 路由组件
```

### 组件接口定义

#### MarkdownEditor Component

```typescript
interface MarkdownEditorProps {
  // 主容器组件，无需外部Props
}
```

#### FileTree Component

```typescript
interface FileTreeProps {
  rootPath: string;
  onFileSelect: (path: string) => void;
  currentFilePath?: string;
}
```

#### Editor Component

```typescript
interface EditorProps {
  content: string;
  config: EditorConfig;
  onChange: (content: string) => void;
  onSave: () => void;
}
```

#### Preview Component

```typescript
interface PreviewProps {
  content: string;
  theme?: 'light' | 'dark';
  showHeader?: boolean;
  onTocUpdate?: (toc: TocItem[]) => void;
}
```

#### SearchDialog Component

```typescript
interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
  onFileSelect: (path: string) => void;
}
```

#### SettingsDialog Component

```typescript
interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}
```

### Backend API接口

#### 认证API

**POST /api/auth/register**
用户注册

**Request:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "user_id": "string",
  "username": "string",
  "token": "string"
}
```

**POST /api/auth/login**
用户登录

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "user_id": "string",
  "username": "string",
  "token": "string"
}
```

**POST /api/auth/logout**
用户登出

**GET /api/auth/me**
获取当前用户信息

**Response:**
```json
{
  "user_id": "string",
  "username": "string",
  "email": "string"
}
```

#### Markdown编辑器API

**GET /api/markdown-editor/files/root**
获取用户根目录路径

**Response:**
```json
{
  "path": "string",
  "exists": boolean
}
```

**POST /api/markdown-editor/files/root**
设置用户根目录路径

**Request:**
```json
{
  "path": "string"
}
```

**GET /api/markdown-editor/files/tree**
获取目录树结构

**Parameters:**
- root: string (可选，相对路径)

**Response:**
```json
{
  "name": "string",
  "type": "file" | "directory",
  "path": "string",
  "children": [...]
}
```

**GET /api/markdown-editor/files/read**
读取文件内容

**Parameters:**
- path: string (相对路径)

**Response:**
```json
{
  "path": "string",
  "content": "string",
  "modified_time": "string"
}
```

**POST /api/markdown-editor/files/save**
保存文件内容

**Request:**
```json
{
  "path": "string",
  "content": "string"
}
```

**POST /api/markdown-editor/files/create**
创建新文件

**Request:**
```json
{
  "path": "string",
  "content": "string"
}
```

**DELETE /api/markdown-editor/files/delete**
删除文件

**Parameters:**
- path: string

**POST /api/markdown-editor/files/rename**
重命名文件

**Request:**
```json
{
  "old_path": "string",
  "new_path": "string"
}
```

**POST /api/markdown-editor/files/directory/create**
创建目录

**Parameters:**
- path: string

**DELETE /api/markdown-editor/files/directory/delete**
删除目录

**Parameters:**
- path: string
- recursive: boolean

**GET /api/markdown-editor/config**
获取用户配置

**Response:**
```json
{
  "theme": "light" | "dark",
  "fontSize": number,
  "autoSaveInterval": number,
  "previewTheme": "string",
  "showLineNumbers": boolean,
  "tabSize": number,
  "useSpaces": boolean,
  "language": "zh-CN" | "en-US"
}
```

**POST /api/markdown-editor/config**
保存用户配置

**Request:**
```json
{
  "theme": "light" | "dark",
  "fontSize": number,
  "autoSaveInterval": number,
  "previewTheme": "string",
  "showLineNumbers": boolean,
  "tabSize": number,
  "useSpaces": boolean,
  "language": "zh-CN" | "en-US"
}
```

**GET /api/markdown-editor/search/files**
搜索文件

**Parameters:**
- keyword: string

**Response:**
```json
[
  {
    "path": "string",
    "name": "string"
  }
]
```

**GET /api/markdown-editor/search/content**
搜索内容

**Parameters:**
- keyword: string
- regex: boolean
- case_sensitive: boolean

**Response:**
```json
[
  {
    "path": "string",
    "name": "string",
    "matches": [
      {
        "line": number,
        "content": "string"
      }
    ]
  }
]
```

## Data Models

### 认证模型

```typescript
interface User {
  user_id: string;
  username: string;
  email: string;
  created_at: string;
}

interface LoginRequest {
  username: string;
  password: string;
}

interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

interface AuthResponse {
  user_id: string;
  username: string;
  token: string;
}
```

### 文件模型

```typescript
interface FileNode {
  name: string;
  type: 'file' | 'directory';
  path: string;
  children?: FileNode[];
}

interface FileContent {
  path: string;
  content: string;
  modified_time: string;
}

interface SaveRequest {
  path: string;
  content: string;
}

interface CreateRequest {
  path: string;
  content?: string;
}

interface RenameRequest {
  old_path: string;
  new_path: string;
}
```

### 配置模型

```typescript
interface EditorConfig {
  theme: 'light' | 'dark';
  fontSize: number;
  autoSaveInterval: number;
  previewTheme: string;
  showLineNumbers: boolean;
  tabSize: number;
  useSpaces: boolean;
  language: 'zh-CN' | 'en-US';
}
```

### 搜索模型

```typescript
interface FileSearchResult {
  path: string;
  name: string;
}

interface ContentSearchResult {
  path: string;
  name: string;
  matches: Array<{
    line: number;
    content: string;
  }>;
}
```

## Authentication and Authorization

### JWT认证流程

1. 用户注册/登录后，后端生成JWT令牌
2. 前端将JWT令牌存储在localStorage中
3. 前端在API请求的Authorization header中携带JWT令牌
4. 后端验证JWT令牌的有效性和用户身份
5. 后端基于用户ID进行文件操作隔离

### 文件存储隔离

- 每个用户的文件存储在独立的目录：`/users/{user_id}/markdown-files/`
- 所有文件操作API都需要验证用户身份
- 路径验证确保用户无法访问其他用户的文件

## Error Handling

### Frontend错误处理

1. **认证错误**
   - 令牌过期：自动跳转到登录页面
   - 无效令牌：清除本地存储，跳转到登录页面
   - 登录失败：显示错误消息

2. **文件操作错误**
   - 文件不存在：显示404错误
   - 权限不足：显示403错误
   - 保存失败：显示错误消息，提供重试选项

3. **网络错误**
   - 连接失败：显示网络错误提示
   - 超时：提供重试机制

### Backend错误处理

1. **认证错误**
   - 返回401状态码
   - 提供详细的错误信息

2. **文件操作错误**
   - 路径遍历攻击：返回400错误
   - 文件不存在：返回404错误
   - 权限不足：返回403错误

3. **验证错误**
   - 使用Pydantic进行参数验证
   - 返回详细的验证错误信息

## Testing Strategy

### 单元测试

**Frontend单元测试 (Jest + React Testing Library):**
- 测试组件渲染
- 测试用户交互
- 测试状态管理
- 测试API调用

**Backend单元测试 (pytest):**
- 测试API端点
- 测试服务层逻辑
- 测试数据验证
- 测试错误处理

### 集成测试

- 测试前后端API交互
- 测试认证流程
- 测试文件操作流程
- 测试用户隔离

### 端到端测试

- 使用Playwright测试完整用户流程
- 测试登录、文件操作、编辑、预览等完整流程

## Implementation Notes

### Vue到React迁移要点

1. **组件转换**
   - Vue的`<template>`转换为React的JSX
   - Vue的`<script setup>`转换为React函数组件
   - Vue的`ref`和`reactive`转换为React的`useState`和`useRef`
   - Vue的`computed`转换为React的`useMemo`
   - Vue的`watch`转换为React的`useEffect`

2. **状态管理**
   - Pinia Store转换为Zustand Store
   - 保持相同的状态结构和API

3. **生命周期**
   - Vue的`onMounted`转换为React的`useEffect`
   - Vue的`onUnmounted`转换为React的`useEffect`清理函数

4. **路由**
   - Vue Router转换为React Router v6
   - 保持相同的路由结构

### 认证系统集成

1. **后端认证中间件**
   - 创建JWT认证中间件
   - 验证所有Markdown编辑器API请求的令牌
   - 提取用户ID并传递给服务层

2. **前端认证守卫**
   - 创建AuthGuard组件保护路由
   - 实现登录状态检查
   - 实现令牌刷新机制

### 文件存储隔离

1. **用户目录结构**
   ```
   /users/
     {user_id}/
       markdown-files/
         documents/
         notes/
         .markdown-editor/
           config.json
   ```

2. **路径验证**
   - 确保所有文件路径都在用户目录内
   - 防止路径遍历攻击（`../`等）

### 性能优化

1. **组件懒加载**
   - 使用React.lazy加载Markdown编辑器组件
   - 使用Suspense处理加载状态

2. **编辑器优化**
   - Monaco编辑器按需加载
   - 大文件使用虚拟滚动（如需要）

3. **自动保存优化**
   - 使用防抖（debounce）减少保存频率
   - 仅在内容变化时保存

## File Structure

### 完整项目结构

```
tool-aggregation-website/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py                    # 认证API路由
│   │   │   └── markdown_editor.py         # Markdown编辑器API路由
│   │   ├── models/
│   │   │   ├── auth_models.py             # 认证数据模型
│   │   │   ├── file_models.py             # 文件数据模型
│   │   │   ├── config_models.py           # 配置数据模型
│   │   │   └── search_models.py           # 搜索数据模型
│   │   ├── services/
│   │   │   ├── auth_service.py            # 认证服务
│   │   │   ├── file_service.py            # 文件服务
│   │   │   ├── config_service.py          # 配置服务
│   │   │   └── search_service.py          # 搜索服务
│   │   ├── middleware/
│   │   │   └── auth_middleware.py         # 认证中间件
│   │   └── utils/
│   │       └── path_utils.py              # 路径工具
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MarkdownEditor/            # Markdown编辑器组件
│   │   │   └── Auth/                      # 认证组件
│   │   ├── stores/                        # Zustand状态管理
│   │   ├── hooks/                         # React Hooks
│   │   ├── api/                           # API客户端
│   │   ├── types/                         # TypeScript类型
│   │   └── routes/                        # 路由配置
│   └── package.json
└── README.md
```
