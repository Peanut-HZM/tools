# 工具箱 - 聚合类工具网站

一站式实用工具集合，提升工作效率，简化日常任务。从文本处理到格式转换，从计算辅助到设计工具，应有尽有。

![ Logo](https://img.shields.io/badge/工具箱-2563eb?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.2+-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.3+-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)

## 📖 项目简介

本项目是一个现代化的工具聚合网站，采用前后端分离架构，提供丰富的在线工具服务。项目完全基于设计原型实现，确保100%还原设计稿的视觉效果和交互体验。

## ✨ 功能特性

- 🎨 **深色主题设计** - 优雅的深色UI，减少视觉疲劳
- 🔍 **智能搜索** - 实时搜索工具，支持防抖优化
- 🏷️ **分类筛选** - 6大工具分类，快速定位所需工具
- 📱 **响应式布局** - 完美适配桌面、平板和移动设备
- ⚡ **高性能** - 基于Vite构建，快速加载和热更新
- 🛡️ **隐私保护** - 本地处理，数据不上传
- 🎯 **交互友好** - 流畅的动画效果和即时反馈
- 📝 **Markdown编辑器** - 功能完整的Markdown编辑器，支持实时预览
- 🔐 **用户认证** - JWT认证系统，支持用户注册和登录
- 👤 **用户隔离** - 每个用户拥有独立的文件存储空间

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js 16+
- npm 或 yarn

### 一键启动

**推荐使用 dev_services.py 管理服务（最简单）：**

```bash
# 启动前后端服务
python dev_services.py

# 查看服务状态
python dev_services.py status

# 重启服务
python dev_services.py restart

# 停止服务
python dev_services.py stop

# 查看实时日志
python dev_services.py logs backend
python dev_services.py logs frontend
```

**传统方式（手动启动）：**

1. **启动后端**

> **注意**: Windows 环境下如遇 `uvicorn: command not found` 错误，请使用 `python -m uvicorn` 代替 `uvicorn`。

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
- **数据验证**: Pydantic
- **服务器**: Uvicorn
- **API文档**: Swagger UI / ReDoc

### 前端
- **框架**: React 18+
- **语言**: TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS 3+
- **图标**: Font Awesome 6.4.0
- **字体**: Google Fonts (Pacifico)

## 📁 项目结构

```
tool-aggregation-website/
├── .kiro/specs/              # 需求、设计和任务文档
├── backend/                  # Python后端服务
│   ├── app/
│   │   ├── main.py          # FastAPI应用入口
│   │   ├── models.py        # 数据模型
│   │   ├── routes/          # API路由
│   │   └── data/            # 静态数据
│   └── requirements.txt     # Python依赖
├── frontend/                 # React前端应用
│   ├── src/
│   │   ├── components/      # React组件
│   │   ├── hooks/           # 自定义Hooks
│   │   ├── services/        # API服务
│   │   ├── types/           # TypeScript类型
│   │   └── App.tsx          # 主应用组件
│   └── package.json         # Node依赖
├── design/                   # 设计原型文件
├── README.md                 # 项目说明（本文件）
├── QUICKSTART.md            # 快速启动指南
├── DEPLOYMENT.md            # 部署指南
└── PROJECT_STRUCTURE.md     # 详细项目结构说明
```

查看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 了解完整的项目结构说明。

## 📚 文档

- [快速启动指南](QUICKSTART.md) - 如何快速运行项目
- [部署指南](DEPLOYMENT.md) - 生产环境部署方法
- [项目结构说明](PROJECT_STRUCTURE.md) - 详细的代码结构说明
- [需求文档](.kiro/specs/tool-aggregation-website/requirements.md) - 完整的功能需求
- [设计文档](.kiro/specs/tool-aggregation-website/design.md) - 技术设计方案
- [任务列表](.kiro/specs/tool-aggregation-website/tasks.md) - 开发任务清单

## 🎯 核心功能

### 工具展示
- 8个精选工具卡片
- 悬停动画效果
- 评分和使用统计
- 点击跳转功能

### Markdown编辑器 (新增)
- 📁 文件树管理 - 浏览、创建、删除、重命名文件和目录
- ✏️ Markdown编辑 - 支持语法高亮和快捷键
- 👁️ 实时预览 - 编辑/预览/分屏三种模式
- 🔍 全文搜索 - 支持文件名和内容搜索
- ⚙️ 配置管理 - 主题、字体、自动保存等可配置
- 🌐 国际化 - 支持中文和英文界面
- 💾 自动保存 - 可配置的自动保存间隔

### 用户认证系统 (新增)
- 用户注册和登录
- JWT令牌认证
- 会话持久化
- 路由保护

### 搜索和筛选
- 实时搜索（300ms防抖）
- 6大分类筛选
- 搜索结果高亮
- 无结果友好提示

### 响应式设计
- 移动端：1列布局
- 平板：2列布局
- 笔记本：3列布局
- 桌面：4列布局

## 🔌 API端点

### 工具API

#### 获取所有工具
```
GET /api/tools
```

#### 搜索工具
```
GET /api/tools/search?q={query}
```

#### 按分类获取工具
```
GET /api/tools/category/{category}
```

### 认证API

#### 用户注册
```
POST /api/auth/register
Body: { "username": "string", "email": "string", "password": "string" }
```

#### 用户登录
```
POST /api/auth/login
Body: { "username": "string", "password": "string" }
```

#### 获取当前用户
```
GET /api/auth/me
Headers: Authorization: Bearer {token}
```

### Markdown编辑器API

#### 获取目录树
```
GET /api/markdown-editor/files/tree
Headers: Authorization: Bearer {token}
```

#### 读取文件
```
GET /api/markdown-editor/files/read?path={path}
Headers: Authorization: Bearer {token}
```

#### 保存文件
```
POST /api/markdown-editor/files/save
Headers: Authorization: Bearer {token}
Body: { "path": "string", "content": "string" }
```

#### 搜索文件
```
GET /api/markdown-editor/search/files?keyword={keyword}
Headers: Authorization: Bearer {token}
```

#### 获取/保存配置
```
GET /api/markdown-editor/config
POST /api/markdown-editor/config
Headers: Authorization: Bearer {token}
```

访问 http://localhost:19092/docs 查看完整的API文档。

## 🎨 设计规范

### 颜色主题
- **Primary**: #2563eb (蓝色)
- **Secondary**: #34d399 (绿色)
- **Background**: #0f172a (深蓝灰)
- **Card**: #1e293b (浅蓝灰)
- **Border**: #334155 (边框灰)

### 圆角规范
- **按钮**: 4px
- **卡片**: 12px
- **输入框**: 8px

### 间距规范
- **容器内边距**: 24px (px-6)
- **卡片间距**: 24px (gap-6)
- **组件间距**: 64px (mb-16)

## 🧪 测试

### 功能测试清单
- [ ] 页面正常加载，显示所有工具卡片
- [ ] 分类标签切换正常
- [ ] 搜索功能正常
- [ ] 工具卡片悬停效果正常
- [ ] 点击交互正常
- [ ] 响应式布局正常

### 运行测试
```bash
# 后端测试（待实现）
cd backend
pytest

# 前端测试（待实现）
cd frontend
npm test
```

## 📦 部署

查看 [DEPLOYMENT.md](DEPLOYMENT.md) 获取详细的部署指南。

### 推荐部署平台

**后端:**
- Railway
- Heroku
- AWS EC2
- Google Cloud Run

**前端:**
- Vercel (推荐)
- Netlify
- Cloudflare Pages

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

## 📄 许可证

© 2024 . All rights reserved.

## 👥 开发团队

 Team

---

**注意**: 本项目基于设计原型 `design/页面 36.html` 实现，确保100%还原设计稿的所有细节。
