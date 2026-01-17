# Design Document

## Overview

本设计文档描述了一个聚合类工具网站的完整技术实现方案。该网站采用前后端分离架构，使用Python（FastAPI）作为后端，React + TypeScript作为前端，Tailwind CSS作为样式框架。设计目标是百分百还原设计原型的所有视觉元素、布局结构和交互功能。

## Architecture

### 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     Browser                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │           React Frontend (Port 3000)              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │  │
│  │  │  Components │  │   Hooks     │  │  Styles  │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/REST API
                          ▼
┌─────────────────────────────────────────────────────────┐
│           Python Backend (FastAPI, Port 8000)           │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   API Routes  │  │   Models    │  │   Services   │  │
│  └───────────────┘  └─────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

**Frontend:**
- React 18+ with TypeScript
- Tailwind CSS 3+
- Font Awesome 6.4.0
- Google Fonts (Pacifico)
- Vite (构建工具)

**Backend:**
- Python 3.10+
- FastAPI
- Pydantic (数据验证)
- CORS middleware

## Components and Interfaces

### Frontend组件结构

```
src/
├── components/
│   ├── Header/
│   │   ├── Header.tsx
│   │   ├── Navigation.tsx
│   │   ├── SearchBar.tsx
│   │   └── LoginButton.tsx
│   ├── Hero/
│   │   ├── Hero.tsx
│   │   ├── CategoryTabs.tsx
│   │   └── ToolGrid.tsx
│   ├── ToolCard/
│   │   └── ToolCard.tsx
│   ├── Features/
│   │   ├── Features.tsx
│   │   └── FeatureItem.tsx
│   ├── Statistics/
│   │   └── Statistics.tsx
│   ├── Recommendations/
│   │   ├── Recommendations.tsx
│   │   └── RecommendationCard.tsx
│   └── Footer/
│       └── Footer.tsx
├── hooks/
│   ├── useCategory.ts
│   └── useSearch.ts
├── types/
│   └── index.ts
├── App.tsx
└── main.tsx
```

### 组件接口定义

#### ToolCard Component

```typescript
interface ToolCardProps {
  id: string;
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  rating: number;
  usageCount: string;
  onClick: () => void;
}
```

#### CategoryTabs Component

```typescript
interface CategoryTabsProps {
  categories: string[];
  activeCategory: string;
  onCategoryChange: (category: string) => void;
}
```

#### SearchBar Component

```typescript
interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
}
```

### Backend API接口

#### GET /api/tools
获取所有工具列表

**Response:**
```json
{
  "tools": [
    {
      "id": "text-processing",
      "icon": "fa-font",
      "iconColor": "bg-blue-500",
      "title": "文本处理",
      "description": "支持文本格式化、大小写转换、去除空格等操作",
      "rating": 4.8,
      "usageCount": "1.2K",
      "category": "文本工具"
    }
  ]
}
```

#### GET /api/tools/search?q={query}
搜索工具

**Parameters:**
- q: 搜索关键词

**Response:**
```json
{
  "tools": [...],
  "count": 5
}
```

#### GET /api/tools/category/{category}
按分类获取工具

**Parameters:**
- category: 分类名称

**Response:**
```json
{
  "tools": [...],
  "category": "文本工具"
}
```

## Data Models

### Tool Model

```typescript
interface Tool {
  id: string;
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  rating: number;
  usageCount: string;
  category: string;
}
```

### Category Model

```typescript
type Category = 
  | "全部工具"
  | "文本工具"
  | "转换工具"
  | "计算工具"
  | "设计工具"
  | "实用工具";
```

### Feature Model

```typescript
interface Feature {
  icon: string;
  iconColor: string;
  title: string;
  description: string;
}
```

### Statistic Model

```typescript
interface Statistic {
  value: string;
  label: string;
}
```

### Recommendation Model

```typescript
interface Recommendation {
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  action: string;
}
```

## Correctness Properties

*属性是关于系统应该如何行为的形式化陈述，这些属性在所有有效执行中都应该成立。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### Property 1: 分类筛选互斥性
*For any* 分类标签集合，当用户点击某个分类标签时，只有该标签应该处于激活状态，其他所有标签都应该处于非激活状态
**Validates: Requirements 4.3, 4.4**

### Property 2: 工具卡片悬停效果一致性
*For any* 工具卡片，当鼠标悬停时，应该同时应用向上平移4px的动画和primary色边框，移开鼠标后应该恢复原状
**Validates: Requirements 3.2, 3.3**

### Property 3: 搜索框焦点状态
*For any* 搜索输入框，当获得焦点时应该显示primary色外发光效果，失去焦点时应该移除该效果
**Validates: Requirements 5.3**

### Property 4: 响应式布局列数
*For any* 屏幕宽度，工具卡片网格的列数应该符合以下规则：<768px为1列，768-1024px为2列，1024-1280px为3列，>1280px为4列
**Validates: Requirements 12.1, 12.2, 12.3, 12.4**

### Property 5: 颜色主题一致性
*For any* 页面元素，所有使用primary色的地方应该使用 #2563eb，所有使用slate-900的地方应该使用 #0f172a
**Validates: Requirements 2.1, 2.2**

### Property 6: 工具卡片数据完整性
*For any* 工具卡片，必须包含图标、标题、描述、评分和使用次数这5个必需字段
**Validates: Requirements 3.4**

### Property 7: 导航链接悬停效果
*For any* 导航链接，悬停时文字颜色应该从slate-300变为白色，移开后应该恢复为slate-300
**Validates: Requirements 6.2**

### Property 8: 按钮圆角一致性
*For any* 按钮元素，应该应用4px的圆角值
**Validates: Requirements 2.5**

## Error Handling

### Frontend错误处理

1. **API请求失败**
   - 显示用户友好的错误提示
   - 提供重试机制
   - 记录错误日志到控制台

2. **组件渲染错误**
   - 使用Error Boundary捕获组件错误
   - 显示降级UI
   - 防止整个应用崩溃

3. **搜索无结果**
   - 显示"未找到相关工具"提示
   - 提供搜索建议
   - 显示热门工具作为替代

### Backend错误处理

1. **无效请求参数**
   - 返回400状态码
   - 提供详细的错误信息
   - 使用Pydantic进行参数验证

2. **资源未找到**
   - 返回404状态码
   - 提供友好的错误消息

3. **服务器内部错误**
   - 返回500状态码
   - 记录详细错误日志
   - 不暴露敏感信息给客户端

## Testing Strategy

### 单元测试

**Frontend单元测试 (Jest + React Testing Library):**
- 测试每个组件的渲染输出
- 测试用户交互事件（点击、悬停、输入）
- 测试条件渲染逻辑
- 测试自定义Hooks的状态管理

**Backend单元测试 (pytest):**
- 测试API端点的响应格式
- 测试数据验证逻辑
- 测试错误处理机制
- 测试CORS配置

### 属性测试

使用fast-check（Frontend）和Hypothesis（Backend）进行属性测试，每个测试至少运行100次迭代。

**Frontend属性测试:**
- 测试分类筛选的互斥性（Property 1）
- 测试响应式布局的列数计算（Property 4）
- 测试颜色主题的一致性（Property 5）

**Backend属性测试:**
- 测试工具数据的完整性（Property 6）
- 测试搜索结果的正确性
- 测试分类筛选的准确性

### 集成测试

- 测试Frontend与Backend的API交互
- 测试完整的用户流程（搜索、筛选、点击）
- 测试跨浏览器兼容性

### 视觉回归测试

- 使用Playwright进行截图对比
- 确保视觉效果与设计原型100%一致
- 测试不同屏幕尺寸下的布局

## Implementation Notes

### 样式实现要点

1. **Tailwind配置**
   - 扩展默认主题，添加primary和secondary颜色
   - 自定义圆角值，确保按钮使用4px圆角
   - 配置容器最大宽度和内边距

2. **字体加载**
   - 使用Google Fonts CDN加载Pacifico字体
   - 为logo元素应用font-['Pacifico']类

3. **图标系统**
   - 使用Font Awesome CDN
   - 为每个工具卡片使用不同颜色的图标背景
   - 图标颜色：蓝(blue-500)、绿(green-500)、紫(purple-500)、橙(orange-500)、红(red-500)、青(teal-500)、靛(indigo-500)、粉(pink-500)

### 交互实现要点

1. **分类筛选**
   - 使用useState管理当前激活的分类
   - 点击时更新状态并触发工具列表过滤
   - 使用CSS类切换实现视觉反馈

2. **搜索功能**
   - 使用防抖(debounce)优化搜索性能
   - 实时过滤工具列表
   - 支持按标题和描述搜索

3. **工具卡片点击**
   - 使用alert显示工具名称（原型行为）
   - 后续可扩展为路由跳转

### 性能优化

1. **代码分割**
   - 使用React.lazy进行组件懒加载
   - 按路由分割代码包

2. **图片优化**
   - 使用SVG图标减少HTTP请求
   - 懒加载非首屏图片

3. **缓存策略**
   - 缓存API响应数据
   - 使用React.memo优化组件渲染

### 部署配置

1. **Frontend部署**
   - 构建生产版本：`npm run build`
   - 部署到静态托管服务（Vercel/Netlify）
   - 配置环境变量指向Backend API

2. **Backend部署**
   - 使用uvicorn运行FastAPI应用
   - 配置CORS允许Frontend域名
   - 部署到云服务（AWS/Heroku/Railway）

## File Structure

### 完整项目结构

```
tool-aggregation-website/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── tools.py
│   │   └── data/
│   │       └── tools_data.py
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header/
│   │   │   ├── Hero/
│   │   │   ├── ToolCard/
│   │   │   ├── Features/
│   │   │   ├── Statistics/
│   │   │   ├── Recommendations/
│   │   │   └── Footer/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── README.md
└── README.md
```
