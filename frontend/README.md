# 工具箱 - 前端应用

基于React + TypeScript + Tailwind CSS构建的现代化工具聚合网站前端。

## 技术栈

- React 18+
- TypeScript
- Tailwind CSS 3+
- Vite
- Font Awesome 6.4.0
- Google Fonts (Pacifico)

## 安装依赖

```bash
npm install
```

## 开发环境运行

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

## 生产构建

```bash
npm run build
```

构建产物将生成在 `dist` 目录

## 预览生产构建

```bash
npm run preview
```

## 项目结构

```
src/
├── components/          # React组件
│   ├── Header/         # 头部导航组件
│   ├── Hero/           # 主要内容区域
│   ├── ToolCard/       # 工具卡片组件
│   ├── Features/       # 特色功能组件
│   ├── Statistics/     # 统计数据组件
│   ├── Recommendations/# 推荐工具组件
│   └── Footer/         # 页脚组件
├── hooks/              # 自定义Hooks
├── services/           # API服务
├── types/              # TypeScript类型定义
├── App.tsx             # 主应用组件
├── main.tsx            # 应用入口
└── index.css           # 全局样式
```

## 功能特性

- ✅ 响应式设计，支持多种屏幕尺寸
- ✅ 深色主题UI
- ✅ 工具搜索功能（带防抖）
- ✅ 分类筛选功能
- ✅ 工具卡片悬停效果
- ✅ 与后端API集成
- ✅ 错误处理和加载状态

## 环境变量

如需修改API地址，请编辑 `src/services/api.ts` 中的 `API_BASE_URL`

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)
