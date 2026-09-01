# 工具箱 - 全栈工具聚合平台

一站式实用工具集合，涵盖 AI 对话、文件处理、开发工具、系统管理等多个领域。采用前后端分离架构，支持 Web 和小程序双端访问。

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?style=flat-square&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3+-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)

## 📖 项目简介

本项目是一个功能丰富的全栈工具聚合平台，提供 25+ 款实用工具，包括 AI 对话、图片/视频生成、OCR 文字识别、语音识别、数据库管理、SSH 终端、K8s 控制台等。支持文件存储（MinIO/阿里云 OSS）、用户认证、Token 用量统计等企业级功能。

## ✨ 功能特性

### 🤖 AI 与智能工具
- **AI 助手** - 多模型对话，支持上下文管理
- **图片生成** - 支持多种 AI 图片生成模型
- **视频生成** - AI 视频创作工具
- **产品经理 Agent** - LLM 驱动的产品需求文档生成

### 📝 文档与文件处理
- **Markdown 编辑器** - 文件树管理、实时预览、全文搜索
- **MarkItDown 转换** - 多格式文档转换
- **JSON 格式化** - JSON 美化与校验
- **图片下载器** - 批量图片下载

### 🔍 识别与转换
- **OCR 文字识别** - 图片文字提取
- **ASR 语音识别** - 语音转文字

### 💻 开发工具
- **HTTP API 客户端** - 接口调试与测试
- **数据库工具** - 在线 SQL 执行与数据管理
- **Redis 工具** - Redis 数据浏览与管理
- **SSH 终端** - 远程服务器连接
- **密钥生成器** - 随机密钥/令牌生成
- **K8s 控制台** - Kubernetes 集群管理

### 🌐 其他工具
- **日历** - 日程管理
- **系统监控** - 服务状态监控
- **Token 用量统计** - AI API 调用量追踪
- **学习分享平台** - 课程与知识分享
- **OpenClaw 聊天** - 网关对话服务
- **视频下载器** - 视频内容下载
- **交叉分享** - 文件跨平台分享

### 🎨 通用特性
- 🌓 **明暗主题** - 支持亮色/暗色模式切换
- 🔍 **智能搜索** - 实时搜索工具，支持防抖优化
- 🏷️ **分类筛选** - 多工具分类，快速定位
- 📱 **响应式布局** - 完美适配桌面、平板和移动设备
- 📱 **小程序支持** - Taro 跨端小程序
- 🔐 **用户认证** - JWT 认证系统
- 👤 **用户隔离** - 每个用户拥有独立的文件存储空间

## 🔧 配置（首次运行必读）

### 1. 复制配置文件

```bash
# 后端配置（必须）
cd backend
cp .env.example .env
# 编辑 .env，按需填入 JWT 密钥、数据库、存储等配置

# 前端配置（可选，开发环境使用默认值即可）
cd ../frontend
cp .env.example .env
```

### 2. 生成安全密钥（生产环境必须）

```bash
cd backend
python scripts/generate_keys.py
# 将生成的密钥填入 backend/.env 的 JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY
```

### 3. 启动服务

```bash
cd ..
python dev-services.py
```

> **提示**: 默认配置下服务可以启动，但未配置的存储服务（OSS/MinIO）、OCR、ASR 等功能将不可用。

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- PostgreSQL（可选，默认使用 SQLite）
- Redis（可选，用于 Token 用量缓存）

### 一键启动

**推荐使用 dev-services.py 管理服务（最简单）：**

```bash
# 启动前后端服务
python dev-services.py

# 查看服务状态
python dev-services.py status

# 重启服务
python dev-services.py restart

# 停止服务
python dev-services.py stop

# 查看实时日志
python dev-services.py logs backend
python dev-services.py logs frontend
```

**传统方式（手动启动）：**

1. **启动后端**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 19092
# Windows 备选方案: python -m uvicorn app.main:app --reload --port 19092
```

2. **启动前端**
```bash
cd frontend
npm install
npm run dev
```

3. **访问应用**
打开浏览器访问 http://localhost:5178

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI
- **语言**: Python 3.10+
- **ORM**: SQLAlchemy 2.0
- **数据验证**: Pydantic v2
- **服务器**: Uvicorn
- **数据库**: PostgreSQL / SQLite
- **缓存**: Redis
- **存储**: MinIO / 阿里云 OSS
- **API 文档**: Swagger UI / ReDoc

### 前端
- **框架**: React 18
- **语言**: TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **图标**: Font Awesome
- **HTTP 客户端**: Axios

### 小程序
- **框架**: Taro 4.x
- **语言**: TypeScript + React
- **样式**: Sass

## 📁 项目结构

```
tools/
├── backend/                    # Python 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── api/routes/        # API v1 路由
│   │   ├── routes/            # 工具路由（OCR、ASR、SSH、K8s 等）
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 模式
│   │   ├── services/          # 业务逻辑层
│   │   ├── config/            # 配置管理
│   │   └── utils/             # 工具函数
│   ├── scripts/               # 后端脚本（密钥生成等）
│   ├── tests/                 # 后端测试
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt       # Python 依赖
├── frontend/                   # React 前端应用
│   ├── src/
│   │   ├── components/        # React 组件
│   │   │   ├── Tools/         # 各工具页面实现
│   │   │   └── Admin/         # 管理后台
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── services/          # API 服务层
│   │   ├── stores/            # Zustand 状态管理
│   │   ├── types/             # TypeScript 类型
│   │   └── App.tsx            # 主应用组件
│   ├── scripts/               # 前端脚本
│   └── package.json           # Node 依赖
├── mini-program/               # Taro 小程序
│   ├── src/                   # 小程序源码
│   ├── config/                # 小程序配置
│   └── package.json           # 小程序依赖
├── scripts/                    # 部署与运维脚本
├── tests/                      # 集成测试
├── dev-services.py             # 服务管理脚本
├── deploy.py                   # 部署脚本
├── deploy.env.example          # 部署配置示例
├── README.md                   # 项目说明（本文件）
├── CLAUDE.md                   # Claude Code 配置
└── AGENTS.md                   # AI Agent 配置
```

## 📚 API 文档

启动后端服务后访问：
- Swagger UI: http://localhost:19092/docs
- ReDoc: http://localhost:19092/redoc

## 🧪 测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

## 📦 部署

### 环境要求

- 服务器：Linux / macOS / Windows
- 数据库：PostgreSQL 12+（推荐）或 SQLite
- 缓存：Redis 6+（可选）
- 存储：MinIO 或阿里云 OSS

### 部署步骤

1. 复制 `deploy.env.example` 为 `deploy.env`，配置服务器信息
2. 执行 `python deploy.py` 进行自动化部署
3. 或参考 `local_deploy.sh` 进行手动部署

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

## 📄 许可证

© 2024-2026. All rights reserved.
