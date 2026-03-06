## ADDED Requirements

### Requirement: 后台管理 UI 组件库

提供一套统一的后台管理 UI 组件，包括卡片、表格、表单、按钮等，具有现代化的视觉设计和交互效果。

#### Scenario: 卡片组件展示
- **WHEN** 用户在后台管理页面查看数据卡片
- **THEN** 卡片显示 `bg-slate-800` 背景、`border-slate-700` 边框、圆角 `rounded-xl`，hover 时边框变为 `cyan-500/50`

#### Scenario: 表格组件展示
- **WHEN** 用户查看数据表格
- **THEN** 表头显示 `bg-slate-700/50` 背景，行 hover 时显示 `bg-slate-700/30`，单元格间距 `px-4 py-3`

#### Scenario: 按钮组件交互
- **WHEN** 用户 hover 到按钮上
- **THEN** 按钮颜色渐变过渡，显示 `hover:bg-cyan-700` 效果，过渡时间 `transition-colors`

#### Scenario: 表单组件输入
- **WHEN** 用户聚焦到输入框
- **THEN** 输入框边框变为 `border-cyan-500`，显示 `focus:outline-none focus:border-cyan-500` 效果

### Requirement: 加载状态组件

提供统一的加载状态展示，包括骨架屏和加载动画。

#### Scenario: 页面加载
- **WHEN** 页面数据正在加载
- **THEN** 显示 "加载中..." 文字，使用 `text-slate-400` 颜色

#### Scenario: 按钮加载
- **WHEN** 表单提交中
- **THEN** 按钮显示 `disabled:bg-slate-600` 状态，文字变为 "保存中..."

### Requirement: 空状态组件

提供友好的空状态提示，引导用户进行操作。

#### Scenario: 列表为空
- **WHEN** 数据列表为空
- **THEN** 显示 "暂无数据" 提示，使用 `text-slate-500` 颜色，居中显示 `text-center py-16`

#### Scenario: 引导操作
- **WHEN** 用户可以添加新数据
- **THEN** 显示操作按钮，使用 `bg-cyan-600 hover:bg-cyan-700` 样式
