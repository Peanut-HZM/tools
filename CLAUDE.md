# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 快速开始

### 使用 dev_services.py 管理服务（推荐）

```bash
# 启动前后端服务
python dev_services.py

# 其他子命令
python dev_services.py status      # 查看服务状态
python dev_services.py restart     # 重启前后端服务
python dev_services.py stop        # 停止前后端服务
python dev_services.py kill all    # 强制终止所有服务
python dev_services.py logs backend  # 查看后端实时日志
python dev_services.py logs frontend # 查看前端实时日志
```

访问 http://localhost:5178

### 手动启动（仅调试时）

```bash
# 后端 (端口 19092)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 19092

# 前端 (端口 5178)
cd frontend
npm install
npm run dev
```

## 技术栈

- **后端**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic, Uvicorn
- **前端**: React 18, TypeScript, Vite, Tailwind CSS, Zustand
- **数据库**: PostgreSQL (通过 SQLAlchemy)
- **存储**: 阿里云 OSS (oss2 SDK)

## 常用命令

```bash
# 前端
cd frontend
npm run dev       # 开发服务器 (热重载)
npm run build     # 生产构建
npm run test      # 运行测试
npm run preview   # 预览生产构建

# 后端
cd backend
uvicorn app.main:app --reload --port 19092  # 开发服务器 (热重载)
python -m py_compile app/main.py            # 语法检查
ruff check .                                # 代码规范检查
```

## 项目结构

```
tools/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/routes/          # API 路由 (v1 版本)
│   │   ├── routes/              # 工具路由
│   │   ├── models/              # 数据模型
│   │   ├── schemas/             # Pydantic 模式
│   │   ├── services/            # 业务逻辑层
│   │   ├── config/              # 配置管理
│   │   └── utils/               # 工具函数
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件
│   │   ├── hooks/               # 自定义 Hooks
│   │   ├── services/            # API 服务层
│   │   ├── stores/              # Zustand 状态管理
│   │   ├── types/               # TypeScript 类型
│   │   └── App.tsx
│   └── package.json
├── specs/                       # 需求规格文档
└── docs/                        # 项目文档
```

## 核心模块

### 后端路由
- `/api/v1` - Product Manager Agent (LLM 配置、对话、PRD 生成)
- `/api` - 工具集合 (OCR、ASR、数据库、Redis、SSH、Markdown 编辑器等)
- `/api/auth` - 用户认证 (JWT)

### 前端主要组件
- `components/Tools/` - 各工具页面实现
- `components/Admin/` - 管理后台
- `services/` - 后端 API 封装

## 开发规范

**重要**: 本项目有严格的开发规范，详见 [AGENTS.md](AGENTS.md)，核心要求：

1. **语言**: 所有对话和代码注释使用中文
2. **热重载**: 优先使用热重载，非必要不重启服务
3. **最小变更**: 只修改必要的代码，不改动已正常的业务逻辑
4. **编译验证**: 修改后必须验证能正常编译
5. **日志**: 后端关键代码必须包含日志记录

## 配置

- 后端配置：`backend/app/config/config.py` (从环境变量或 `.env` 读取)
- 前端配置：`frontend/.env` (VITE_ 开头的环境变量)
- CORS 默认允许 `http://localhost:5178`

## API 文档

启动后端后访问：
- Swagger UI: http://localhost:19092/docs
- ReDoc: http://localhost:19092/redoc
