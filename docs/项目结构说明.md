# 项目结构说明

## 完整目录结构

```
tool-aggregation-website/
├── .kiro/
│   └── specs/
│       └── tool-aggregation-website/
│           ├── requirements.md      # 需求文档
│           ├── design.md           # 设计文档
│           └── tasks.md            # 任务列表
├── backend/                        # Python后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI应用入口
│   │   ├── models.py              # Pydantic数据模型
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── tools.py           # 工具API路由
│   │   └── data/
│   │       ├── __init__.py
│   │       └── tools_data.py      # 工具静态数据
│   ├── requirements.txt           # Python依赖
│   └── README.md                  # 后端说明文档
├── frontend/                       # React前端
│   ├── public/
│   │   └── index.html             # HTML模板
│   ├── src/
│   │   ├── components/            # React组件
│   │   │   ├── Header/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Navigation.tsx
│   │   │   │   ├── SearchBar.tsx
│   │   │   │   └── LoginButton.tsx
│   │   │   ├── Hero/
│   │   │   │   ├── Hero.tsx
│   │   │   │   ├── CategoryTabs.tsx
│   │   │   │   └── ToolGrid.tsx
│   │   │   ├── ToolCard/
│   │   │   │   └── ToolCard.tsx
│   │   │   ├── Features/
│   │   │   │   ├── Features.tsx
│   │   │   │   └── FeatureItem.tsx
│   │   │   ├── Statistics/
│   │   │   │   └── Statistics.tsx
│   │   │   ├── Recommendations/
│   │   │   │   ├── Recommendations.tsx
│   │   │   │   └── RecommendationCard.tsx
│   │   │   └── Footer/
│   │   │       └── Footer.tsx
│   │   ├── hooks/                 # 自定义Hooks
│   │   │   ├── useCategory.ts
│   │   │   └── useSearch.ts
│   │   ├── services/              # API服务
│   │   │   └── api.ts
│   │   ├── types/                 # TypeScript类型
│   │   │   └── index.ts
│   │   ├── App.tsx                # 主应用组件
│   │   ├── main.tsx               # 应用入口
│   │   └── index.css              # 全局样式
│   ├── index.html                 # HTML入口
│   ├── package.json               # 依赖配置
│   ├── tsconfig.json              # TypeScript配置
│   ├── vite.config.ts             # Vite配置
│   ├── tailwind.config.js         # Tailwind配置
│   ├── postcss.config.js          # PostCSS配置
│   └── README.md                  # 前端说明文档
├── design/                         # 设计原型
│   └── 页面 36.html               # 原始设计文件
├── README.md                       # 项目总览
├── QUICKSTART.md                   # 快速启动指南
├── DEPLOYMENT.md                   # 部署指南
└── PROJECT_STRUCTURE.md            # 本文件
```

## 核心文件说明

### 后端核心文件

| 文件 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI应用入口，配置CORS和路由 |
| `backend/app/models.py` | Pydantic数据模型定义 |
| `backend/app/routes/tools.py` | 工具相关API端点 |
| `backend/app/data/tools_data.py` | 8个工具的静态数据 |

### 前端核心文件

| 文件 | 说明 |
|------|------|
| `frontend/src/App.tsx` | 主应用组件，管理全局状态和API调用 |
| `frontend/src/main.tsx` | React应用入口 |
| `frontend/src/index.css` | 全局样式和Tailwind配置 |
| `frontend/src/types/index.ts` | TypeScript类型定义 |

### 组件说明

| 组件 | 功能 |
|------|------|
| `Header` | 顶部导航栏，包含logo、导航菜单、搜索框和登录按钮 |
| `Hero` | 主要内容区域，包含标题、分类标签和工具网格 |
| `CategoryTabs` | 分类筛选标签 |
| `ToolGrid` | 工具卡片网格布局 |
| `ToolCard` | 单个工具卡片 |
| `Features` | 特色功能展示区域 |
| `Statistics` | 使用统计数据展示 |
| `Recommendations` | 热门推荐工具 |
| `Footer` | 页脚信息 |

### Hooks说明

| Hook | 功能 |
|------|------|
| `useCategory` | 管理分类筛选状态 |
| `useSearch` | 管理搜索功能和防抖 |

### API服务

| 函数 | 功能 |
|------|------|
| `fetchTools()` | 获取所有工具 |
| `searchTools(query)` | 搜索工具 |
| `fetchToolsByCategory(category)` | 按分类获取工具 |

## 数据流

```
用户交互
    ↓
React组件 (App.tsx)
    ↓
自定义Hooks (useCategory, useSearch)
    ↓
API服务 (api.ts)
    ↓
后端API (FastAPI)
    ↓
数据模型 (tools_data.py)
    ↓
返回数据
    ↓
更新UI
```

## 样式系统

- **框架**: Tailwind CSS 3+
- **主题色**: 
  - Primary: #2563eb (蓝色)
  - Secondary: #34d399 (绿色)
- **背景色**: 
  - 主背景: #0f172a (slate-900)
  - 卡片背景: #1e293b (slate-800)
- **字体**: 
  - Logo: Pacifico (Google Fonts)
  - 正文: 系统默认字体
- **图标**: Font Awesome 6.4.0

## 技术栈总结

### 后端
- Python 3.10+
- FastAPI
- Pydantic
- Uvicorn

### 前端
- React 18+
- TypeScript
- Vite
- Tailwind CSS
- Font Awesome
- Google Fonts

## 开发工作流

1. **需求阶段**: 编写 `requirements.md`
2. **设计阶段**: 编写 `design.md`
3. **任务规划**: 编写 `tasks.md`
4. **后端开发**: 实现API和数据模型
5. **前端开发**: 实现React组件和样式
6. **集成测试**: 前后端联调
7. **部署**: 按照 `DEPLOYMENT.md` 部署

## 扩展建议

### 后端扩展
- 添加数据库支持（PostgreSQL/MongoDB）
- 实现用户认证系统
- 添加工具使用统计
- 实现工具收藏功能

### 前端扩展
- 添加用户登录/注册页面
- 实现工具详情页
- 添加工具评论功能
- 实现深色/浅色主题切换
- 添加国际化支持

### 功能扩展
- 实现实际的工具功能（文本处理、格式转换等）
- 添加工具使用历史记录
- 实现工具推荐算法
- 添加用户个性化设置
