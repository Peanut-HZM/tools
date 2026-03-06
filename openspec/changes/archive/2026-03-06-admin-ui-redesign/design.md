## Context

**背景：**
- 当前后台管理页面使用简单的 slate 色系，缺少视觉层次和精致感
- 首页使用了现代化的卡片设计、渐变效果和动画过渡
- 课程管理页面功能已实现，但 UI 样式需要优化以匹配整体设计语言
- 用户期望后台管理页面也有与首页一致的专业外观

**当前状态：**
- AdminLayout：简单的 slate-900 背景，基础款侧边栏导航
- Dashboard：基础卡片和表格，缺少视觉吸引力
- CourseManagement：功能完整但样式简陋

**约束：**
- 不能改变现有业务逻辑和数据流
- 保持 React 组件结构不变，仅优化样式
- 使用现有的 Tailwind CSS 和已安装的依赖
- 保持响应式设计

## Goals / Non-Goals

**Goals:**
- 统一后台管理与首页的视觉设计语言
- 优化侧边栏导航，增加渐变背景和图标
- 改进 Dashboard 卡片，使用首页风格的 tool-card 样式
- 优化课程管理页面的表格、表单、按钮样式
- 增加 hover 效果、过渡动画，提升交互体验
- 保持深色主题的一致性

**Non-Goals:**
- 不改变现有业务功能和 API 调用
- 不重构组件架构
- 不添加新的功能特性
- 不改变路由和导航结构

## Decisions

### 1. 设计系统选择

**决策：** 使用首页已有的设计模式，包括 `bg-slate-800` 卡片、`border-slate-700` 边框、`cyan-500` 主题色

**理由：**
- 保持整个应用的设计一致性
- 用户已经熟悉首页的交互模式
- 减少学习成本

**替代方案考虑：**
- 方案 A：使用 shadcn/ui 组件库
  - 缺点：需要额外安装依赖，增加复杂度
- 方案 B：创建全新的设计系统
  - 缺点：与首页风格不统一，增加维护成本

### 2. 侧边栏优化

**决策：** 保留左侧导航布局，增加渐变背景、图标、hover 动画

**样式规范：**
- 背景：`bg-gradient-to-br from-slate-800 to-slate-900`
- 激活项：`bg-cyan-500/20 text-cyan-400 border border-cyan-500/30`
- 普通项：`text-slate-300 hover:bg-slate-700 hover:text-white`

### 3. 卡片组件优化

**决策：** 参考首页 ToolCard 样式，增加渐变、阴影、动画效果

**样式规范：**
- 基础：`bg-slate-800 rounded-xl p-6 border border-slate-700`
- Hover：`hover:border-cyan-500/50 transition-all`
- 标题：`text-lg font-semibold text-white`
- 描述：`text-slate-400 text-sm`

### 4. 表格样式优化

**决策：** 使用现代化表格设计，增加表头背景、hover 效果

**样式规范：**
- 表头：`bg-slate-700/50 text-slate-300`
- 行：`hover:bg-slate-700/30 transition-colors`
- 单元格：`px-4 py-3 text-slate-300`

## Risks / Trade-offs

### 风险 1：样式覆盖导致功能异常

**风险描述：** 修改组件样式时可能意外影响功能逻辑

**缓解措施：**
- 仅修改 className，不改变组件结构
- 保持现有事件处理逻辑
- 测试关键交互功能

### 风险 2：响应式布局问题

**风险描述：** 新样式可能在不同屏幕尺寸下显示异常

**缓解措施：**
- 保持现有的响应式类名
- 在多种设备尺寸下测试
- 使用 Tailwind 的响应式工具类

### 风险 3：性能影响

**风险描述：** 过多动画和渐变可能影响性能

**缓解措施：**
- 使用 CSS transition 而非 JavaScript 动画
- 限制同时播放的动画数量
- 使用 will-change 优化性能

## Migration Plan

### 部署步骤：
1. 修改 AdminLayout 组件样式
2. 优化 Dashboard 组件卡片样式
3. 更新 CourseManagement 及其子组件样式
4. 测试所有后台管理页面

### 回滚策略：
- Git 回滚样式修改的 commits
- 不影响后端 API 和数据结构
- 可快速恢复到原有样式

## Open Questions

1. 是否需要添加浅色主题切换功能？
2. 是否需要为不同角色用户定制不同的 UI？
3. 是否需要添加更多的数据可视化图表？
