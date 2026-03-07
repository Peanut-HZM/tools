# UI Consistency Spec

## Requirement

CrossShare 页面的 UI 样式必须与主系统保持一致，不得使用独立的主题和颜色。

## Design Tokens

### Colors

使用 Tailwind CSS 默认的 slate 色系：

| 用途 | 颜色类 | 说明 |
|------|--------|------|
| 主背景 | `bg-slate-50` | 页面整体背景 |
| 卡片背景 | `bg-white` | 卡片、面板背景 |
| 主文字 | `text-slate-900` | 标题、主要内容 |
| 次要文字 | `text-slate-500` | 描述、提示 |
| 边框 | `border-slate-200` | 卡片边框、分隔线 |
| 强调色 | `bg-blue-500` / `bg-indigo-500` | 按钮、高亮 |

### Layout

| 用途 | 类名 | 说明 |
|------|------|------|
| 页面容器 | `min-h-screen flex flex-col` | 自适应高度 |
| 主内容区 | `flex-1` | 占满剩余空间 |
| 卡片容器 | `bg-white rounded-lg shadow-md` | 统一卡片样式 |
| Header 固定 | `sticky top-0 z-50` | 固定定位 |

## Components

### CrossShareMain

- 移除：用户头像、用户名、退出按钮
- 移除：紫色渐变背景
- 使用：`bg-slate-50 min-h-screen`

### Header (Layout)

- 添加：`sticky top-0 z-50`
- 保持：现有用户信息展示和退出功能

## Behavior

- 页面滚动时 Header 保持可见
- 内容区域自适应高度，无明显底部空白
- 所有子组件（消息、文件、设备面板）样式一致
