# 后台管理页面布局优化设计

> 日期：2026-03-12
> 状态：已批准

## 问题描述

当前后台管理页面使用 `container mx-auto px-6` 的居中布局，在宽屏显示器下左右两侧有大量空白区域，页面空间利用率低。

## 优化目标

- 充分利用页面空间，减少不必要的留白
- 保持现有设计风格和主题
- **仅影响后台管理页面**，用户端和工具页不受影响

## 设计方案

### 1. AdminLayout.tsx - 全局布局调整

**位置：** `/frontend/src/components/Admin/AdminLayout.tsx`

**修改内容：**
- 移除 `container mx-auto px-6` 容器限制
- 改为 `flex-1 w-full` 全屏布局
- 主内容区移除 `min-h-[600px]` 固定高度限制
- 保持侧边栏宽度 w-64 不变

### 2. CourseManagement.tsx - 课程列表页

**位置：** `/frontend/src/components/Admin/CourseManagement.tsx`

**修改内容：**
- 课程卡片网格从 `grid-cols-3` 扩展为响应式布局
- 新增 `xl:grid-cols-4` 和 `2xl:grid-cols-5`
- 在宽屏下显示更多列，充分利用空间

### 3. CourseDetail.tsx - 课程详情页

**位置：** `/frontend/src/components/Admin/CourseDetail.tsx`

**修改内容：**
- 减少垂直间距：`mb-8` → `mb-4`，`mb-6` → `mb-4`
- 移除不必要的水平间距 `px-2`
- 让 Header、课程信息卡片和 Tabs 更紧凑

## 影响范围

| 文件 | 修改类型 | 影响 |
|------|---------|------|
| AdminLayout.tsx | 布局结构 | 所有后台管理页面 |
| CourseManagement.tsx | 网格列数 | 课程列表页 |
| CourseDetail.tsx | 间距优化 | 课程详情页 |

## 验证标准

- [ ] 后台管理页面左右两侧无明显空白
- [ ] 课程列表在宽屏下显示更多卡片
- [ ] 课程详情页内容更紧凑
- [ ] 用户端页面不受影响
- [ ] 工具页面不受影响
