# 后台管理侧边栏固定优化设计

> 日期：2026-03-12
> 状态：已批准

## 问题描述

后台管理页面内容滚动时，左侧菜单栏没有固定，导致用户体验不佳。

## 设计方案

### 使用 `sticky` 定位固定侧边栏

**修改文件：** `frontend/src/components/Admin/AdminLayout.tsx`

**修改内容：**

在侧边栏 `aside` 标签上添加以下 className：

```tsx
// 修改前
<aside className="w-64 flex-shrink-0">

// 修改后
<aside className="w-64 flex-shrink-0 sticky top-8 self-start max-h-[calc(100vh-4rem)]">
```

**属性说明：**
- `sticky top-8`：粘性定位，距离顶部 8px（与容器 py-8 配合）
- `self-start`：在 flex 容器中从顶部开始对齐
- `max-h-[calc(100vh-4rem)]`：最大高度为视口高度减去上下边距

**同时修改侧边栏内部容器：**

```tsx
// 修改前
<div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-4 border border-slate-700/50 h-full shadow-xl">

// 修改后
<div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-4 border border-slate-700/50 shadow-xl">
```

移除 `h-full`，让侧边栏高度自适应内容。

## 影响范围

| 文件 | 修改类型 | 影响 |
|------|---------|------|
| AdminLayout.tsx | 样式优化 | 所有后台管理页面侧边栏 |

## 验证标准

- [ ] 侧边栏在页面滚动时保持固定位置
- [ ] 侧边栏菜单项可以正常点击
- [ ] 主内容区域滚动不受影响
- [ ] 页面布局无异常
