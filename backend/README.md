# Backend API

工具箱后端服务，基于 FastAPI 构建。

## 前置要求

- Python 3.10+

## 快速开始

### 1. 创建虚拟环境

建议使用 Python 虚拟环境来隔离项目依赖，避免与其他 Python 项目冲突。

**Windows:**
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

**macOS/Linux:**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

激活成功后，命令行前面会显示 `(venv)` 标识。

### 2. 安装依赖

```bash
pip install -r requirements.txt
pip install --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt
```

### 3. 运行服务

```bash
uvicorn app.main:app --reload --port 19092
```

服务将在 http://localhost:19092 启动。

### 4. 退出虚拟环境

完成开发后，可以退出虚拟环境：

```bash
deactivate
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:19092/docs
- ReDoc: http://localhost:19092/redoc

## API 端点

### 工具 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/tools` | 获取所有工具 |
| GET | `/api/tools/search?q={query}` | 搜索工具 |
| GET | `/api/tools/category/{category}` | 按分类获取工具 |

### 认证 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/logout` | 用户登出 |
| GET | `/api/auth/me` | 获取当前用户信息 |
| GET | `/api/auth/verify` | 验证令牌有效性 |

### Markdown 编辑器 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/markdown-editor/files/root` | 获取用户根目录 |
| GET | `/api/markdown-editor/files/tree` | 获取目录树 |
| GET | `/api/markdown-editor/files/read` | 读取文件内容 |
| POST | `/api/markdown-editor/files/save` | 保存文件 |
| POST | `/api/markdown-editor/files/create` | 创建文件 |
| DELETE | `/api/markdown-editor/files/delete` | 删除文件 |
| POST | `/api/markdown-editor/files/rename` | 重命名文件 |
| POST | `/api/markdown-editor/files/directory/create` | 创建目录 |
| DELETE | `/api/markdown-editor/files/directory/delete` | 删除目录 |
| GET | `/api/markdown-editor/config` | 获取用户配置 |
| POST | `/api/markdown-editor/config` | 保存用户配置 |
| GET | `/api/markdown-editor/search/files` | 搜索文件名 |
| GET | `/api/markdown-editor/search/content` | 搜索文件内容 |

## 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | JWT 签名密钥（生产环境必须修改） |
| `JWT_EXPIRE_MINUTES` | `1440` | JWT 令牌过期时间（分钟） |

## 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/ -v
```

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── models/              # Pydantic 数据模型
│   ├── routes/              # API 路由
│   ├── services/            # 业务逻辑服务
│   ├── middleware/          # 中间件
│   ├── utils/               # 工具函数
│   └── data/                # 静态数据
├── tests/                   # 测试文件
├── requirements.txt         # Python 依赖
├── desktop_app.py           # 桌面应用入口
├── desktop_config.py        # 桌面模式配置
├── desktop.spec             # PyInstaller 打包规格
├── build_desktop.py         # 一键构建脚本
├── requirements-desktop.txt # 桌面打包额外依赖
├── assets/                  # 应用图标等资源
└── README.md               # 本文件
```

## 桌面应用

本项目可以打包为 Windows 和 macOS 桌面应用。

### 开发模式

```bash
# 1. 启动前端（另一个终端）
cd ../frontend && npm run dev

# 2. 启动桌面应用（开发模式，前端连接 Vite 热重载服务器）
DESKTOP_DEV=1 python desktop_app.py
```

桌面窗口会使用 pywebview 内嵌浏览器展示前端，开发模式下支持 F12 打开开发者工具。

### 构建桌面应用

```bash
python build_desktop.py [--dev] [--clean] [--skip-frontend]
```

产物输出到 `dist/ToolBox.app`（macOS）或 `dist/ToolBox/ToolBox.exe`（Windows）。

### 外部依赖

桌面应用需要以下外部服务配置（通过 `.env` 文件）：
- PostgreSQL 数据库（或默认 SQLite）
- Redis（Token Usage 缓存）
- 阿里云 OSS（文件存储）
- LLM API Key（OpenAI/Anthropic）
