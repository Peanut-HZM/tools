## Why

当前后台管理页面的样式较为简陋，与首页的现代化设计风格不一致。AdminLayout 使用简单的 slate 色背景，卡片组件缺少视觉层次感和精致的交互效果。需要统一整体设计语言，提升用户体验和视觉一致性。

## What Changes

- **优化 AdminLayout 布局**：改进侧边栏导航样式，增加渐变背景和图标，提升视觉吸引力
- **重构 Dashboard 组件**：使用与首页一致的卡片样式，增加渐变色和动画效果
- **优化课程管理页面**：改进表格、表单、按钮等组件的样式，增加过渡动画
- **统一设计语言**：使用首页的 `bg-slate-800`、`border-slate-700`、`cyan` 主题色系
- **增强交互反馈**：添加 hover 效果、过渡动画、加载状态优化

## Capabilities

### New Capabilities

- `admin-ui-components`: 后台管理 UI 组件库，包括优化后的卡片、表格、表单、按钮等通用组件
- `admin-theme-system`: 后台主题系统，定义统一的颜色、间距、圆角等设计 Token

### Modified Capabilities

- `admin-layout`: 优化 AdminLayout 的布局和样式，包括侧边栏和主内容区域
- `admin-dashboard`: 重构 Dashboard 组件，使用新的 UI 组件

## Impact

- **前端组件**：修改 AdminLayout、Dashboard、CourseManagement 等多个组件的样式
- **样式系统**：新增或更新 Tailwind 配置中的设计 Token
- **用户体验**：不影响现有业务功能，仅优化视觉呈现和交互体验
- **兼容性**：保持现有 API 和数据流不变，仅改变 UI 表现层
