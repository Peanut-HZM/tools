## Context

**当前状态：**
1. CrossShare 页面使用独立的紫色渐变背景 (`from-indigo-900 via-purple-900 to-slate-900`)
2. 页面内部重复展示用户信息（头像、用户名、退出按钮）
3. Header 不是固定定位，滚动时消失
4. 页面底部有明显的空白区域
5. 整体风格与首页（白色/浅色简洁主题）差异巨大

**约束：**
- 不能破坏现有的 CrossShare 业务功能（消息、文件、设备管理）
- 需要保持响应式设计
- 使用 Tailwind CSS 统一样式

## Goals / Non-Goals

**Goals:**
- 移除 CrossShare 页面内重复的用户信息展示
- 统一主题样式，与首页保持一致（白色/浅色背景）
- 固定 Header 位置，滚动时保持可见
- 消除页面底部突兀的空白，实现自适应布局
- 整体视觉风格统一、和谐

**Non-Goals:**
- 不修改 CrossShare 的核心业务逻辑
- 不改变 API 调用和数据流
- 不添加新功能

## Decisions

### Decision 1: 移除 CrossShare 页面内的用户信息展示

**选择：** 完全移除 CrossShareMain.tsx 中的用户头像、用户名、退出按钮区域

**理由：**
1. 主 Layout 的 Header 已经提供了用户信息展示和退出功能
2. 避免重复，减少视觉噪音
3. 保持与系统其他工具页面的一致性

### Decision 2: 使用统一的浅色主题

**选择：** CrossShare 页面使用白色/浅灰色背景，与首页保持一致

**样式方案：**
- 背景：`bg-slate-50` 或 `bg-white`
- 卡片：`bg-white shadow-md rounded-lg`
- 文字：`text-slate-900` 主色，`text-slate-500` 次要色
- 强调色：使用系统主色调（如蓝色/紫色按钮）

**理由：**
1. 与首页风格统一，用户体验一致
2. 浅色主题更适合工具类页面
3. 减少视觉疲劳

### Decision 3: 固定 Header 定位

**选择：** 修改 Layout.tsx，Header 使用 `sticky top-0 z-50` 定位

**理由：**
1. 现代 UI 的标准做法
2. 用户随时可以访问搜索、导航、用户菜单
3. 不需要大幅修改现有结构

### Decision 4: 自适应页面布局

**选择：** 使用 `flex-1` 和 `min-h-screen` 确保页面内容自适应

**理由：**
1. 消除底部空白
2. 内容决定高度，不是固定高度
3. 响应式友好

## Risks / Trade-offs

**[Risk]** 样式修改可能影响现有功能
→ **Mitigation:** 逐步修改，每步验证功能正常

**[Risk]** Header 固定可能遮挡内容
→ **Mitigation:** 给 main 添加适当的 `pt-` padding

**[Trade-off]** 完全重写样式 vs 渐进式修改
→ 选择渐进式修改，降低风险，易于回滚

## Migration Plan

1. 修改 `CrossShareMain.tsx` - 移除用户信息展示、修改背景样式
2. 修改 `Layout.tsx` - Header 固定定位
3. 验证各子组件（MessagePanel, FilePanel, DevicePanel, SettingsPanel）样式一致
4. 测试滚动、响应式布局
5. 验证业务功能正常

无需后端修改，回滚只需 git revert

## Open Questions

无
