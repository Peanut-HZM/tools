## Why

CrossShare 设备传传页面存在以下 UI/UX 问题，与主系统风格不一致：

1. **重复展示用户信息**：页面 header 已显示登录用户信息和退出按钮，CrossShare 页面内部又重复展示，造成冗余
2. **主题样式突兀**：CrossShare 使用了紫色渐变背景 (`from-indigo-900 via-purple-900 to-slate-900`)，与首页的简洁浅色主题风格差异巨大
3. **Header 不固定**：页面滚动时 header 随之消失，不符合现代 UI 习惯
4. **底部空白区域**：卡片页面底部有明显的空白区域，页面布局不自适应

这些问题导致用户体验割裂，视觉风格不统一。

## What Changes

- **移除重复的用户信息展示**：CrossShare 页面不再显示用户头像、用户名、退出按钮，使用主 Layout 的 header
- **统一主题样式**：移除紫色渐变背景，使用与首页一致的浅色/白色背景主题
- **固定 Header 位置**：修改主 Layout 的 header 为 `fixed` 或 `sticky` 定位
- **消除底部空白**：优化页面布局，使用 `flex-1` 和 `min-h-screen` 实现自适应
- **保持业务功能不变**：仅调整 UI 样式，不影响 CrossShare 的消息、文件、设备管理功能

## Capabilities

### New Capabilities

无 - 此变更是 UI/UX 优化，不引入新能力

### Modified Capabilities

无 - 仅调整实现细节，不改变接口规范或行为要求

## Impact

- **前端组件**:
  - `frontend/src/components/Tools/CrossShare/CrossShareMain.tsx` - 移除重复用户信息、修改背景样式
  - `frontend/src/components/Layout/Layout.tsx` - 修改 header 为固定定位（如果需要）
  - `frontend/src/components/Tools/CrossShare/*.tsx` - 确保子组件样式一致
- **样式系统**: 使用 Tailwind CSS 统一样式，与首页保持一致
- **无后端影响**: 纯前端 UI 调整
