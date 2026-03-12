# 课程学习页面章节切换修复设计

> **日期：** 2026-03-12
> **状态：** 已批准
> **问题：** 学习页面左侧点击其他章节时无法正确切换，始终显示进入时的章节

## 问题分析

### 问题描述

在用户端课程学习页面（`/courses/:slug/learn?chapterId=16`），左侧有课程章节列表。用户点击其他章节时，无法正确切换到对应的章节内容，始终显示点击"开始学习"按钮进入时的章节。

### 根本原因

**`handleSelectChapter` 函数只更新 React 状态，没有同步更新 URL 参数**

```typescript
// 问题代码
const handleSelectChapter = (chapter: CourseChapter) => {
  setCurrentChapter(chapter);           // ✅ 更新状态
  setShowContent('content');
  updateChapterProgress(chapter.id, 'in_progress');
  // ❌ 没有更新 URL 参数
};
```

### 问题链路

1. 用户点击"开始学习"进入页面 → URL: `?chapterId=16`
2. `useEffect` 加载课程，设置 `currentChapter` 为第 1 章
3. 用户点击左侧第 2 章 → `handleSelectChapter` 更新 `currentChapter`
4. 但 URL 参数仍是 `?chapterId=16`
5. 页面重新渲染时，第二个 `useEffect` 监听到 `location.search` 没变
6. 由于 `currentChapter?.id !== chapter.id` 条件判断，状态不会更新
7. 用户看到的始终是第 1 章内容

### 影响范围

- 用户无法在学习页面内切换章节
- 无法分享特定章节的链接
- 刷新页面后丢失当前选择

---

## 修复方案

### 方案对比

| 方案 | 核心思路 | 优点 | 缺点 |
|------|----------|------|------|
| **A: URL 参数同步（推荐）** | `handleSelectChapter` 同时更新 URL | ✅ URL 可分享<br>✅ 刷新保持状态<br>✅ 前进/后退正常 | 需修改 URL |
| **B: 纯状态管理** | 完全移除 URL 依赖 | 简单直接 | ❌ 刷新丢失状态<br>❌ URL 不可分享 |
| **C: 移除 useEffect** | 不再监听 URL 变化 | 改动小 | ❌ URL 与状态不同步 |

### 选择：方案 A - URL 参数同步

**理由：**
1. URL 可分享，用户可以发送特定章节链接
2. 刷新页面后保持当前章节
3. 浏览器前进/后退按钮正常工作
4. 改动最小，只需修改一个函数

---

## 设计详情

### 修改 1：handleSelectChapter 函数

**文件：** `frontend/src/pages/CourseLearnPage.tsx`
**位置：** 第 117-121 行

```typescript
// ===== 修改前 =====
const handleSelectChapter = (chapter: CourseChapter) => {
  setCurrentChapter(chapter);
  setShowContent('content');
  updateChapterProgress(chapter.id, 'in_progress');
};

// ===== 修改后 =====
const handleSelectChapter = (chapter: CourseChapter) => {
  setCurrentChapter(chapter);
  setShowContent('content');
  updateChapterProgress(chapter.id, 'in_progress');
  // 同步更新 URL 参数
  navigate(`/courses/${slug}/learn?chapterId=${chapter.id}`, { replace: true });
};
```

**关键点：**
- 使用 `{ replace: true }` 避免在浏览器历史中创建大量条目
- URL 参数更新后，`location.search` 变化
- 第二个 `useEffect` 会触发，但由于 `currentChapter?.id !== chapter.id` 条件，不会重复设置状态

---

## 验证标准

### 功能验证

- [ ] 点击左侧第 1 章，显示第 1 章内容
- [ ] 点击左侧第 2 章，显示第 2 章内容
- [ ] 点击左侧第 3 章，显示第 3 章内容
- [ ] 以此类推，所有章节都能正确切换

### URL 验证

- [ ] URL 参数 `chapterId` 随选择变化
- [ ] 刷新页面后仍停留在当前章节
- [ ] 可以直接通过 URL 访问特定章节
- [ ] 浏览器前进/后退按钮正常工作

### 视觉验证

- [ ] 当前章节高亮正确（边框颜色）
- [ ] 章节内容正确显示
- [ ] 没有报错或警告

---

## 相关文件

| 文件 | 修改类型 |
|------|----------|
| `frontend/src/pages/CourseLearnPage.tsx` | 修改 `handleSelectChapter` 函数 |

---

## 后续任务

修复完成后，需要在浏览器中验证：
1. 从课程详情页点击"开始学习"进入
2. 点击左侧不同章节，验证内容切换
3. 刷新页面，验证状态保持
