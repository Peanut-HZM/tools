# 课程学习页面章节跳转修复设计

> **日期：** 2026-03-12
> **状态：** 已批准
> **问题：** 用户端课程详情页点击任意章节"开始学习"都进入第一章

## 问题分析

### 问题描述

在用户端首页，通过技术分析卡片进入课程中心，再通过立即学习进入课程详情页面，通过章节列表点击任意章节开始学习，进入的都是第一章，而不是所选章节。

### 根本原因

1. **CourseDetailPage.tsx (第 175 行)**：所有章节的"开始学习"按钮都跳转到 `/courses/${slug}/learn`，没有传递章节 ID 参数

```tsx
// 问题代码
onClick={() => navigate(`/courses/${slug}/learn`)}
```

2. **CourseLearnPage.tsx (第 56-59 行)**：默认选择第一个章节，没有从 URL 读取章节 ID 参数的逻辑

```tsx
// 问题代码
if (data.chapters.length > 0) {
  setCurrentChapter(data.chapters[0]);
}
```

### 影响范围

- 用户无法直接跳转到指定章节
- 所有用户都只能从第一章开始学习
- 无法分享特定章节的链接

---

## 修复方案

### 方案对比

| 方案 | URL 格式 | 改动范围 | 优缺点 |
|------|----------|----------|--------|
| **A: URL 参数（推荐）** | `/courses/:slug/learn?chapterId=123` | 修改 2 个文件 | ✅ URL 可分享、改动小<br>❌ 参数在 query 中 |
| **B: URL 路径** | `/courses/:slug/learn/:chapterId` | 修改 3 个文件 | ✅ RESTful 风格<br>❌ 需修改路由配置 |
| **C: state 传递** | 同 A，用 state 传递 | 修改 2 个文件 | ❌ 刷新后丢失、URL 不可分享 |

### 选择：方案 A - URL 参数传递章节 ID

**理由：**
1. 改动最小，只需修改两个文件
2. 不需要改动路由配置
3. URL 可分享，符合 Web 标准
4. 支持直接访问特定章节

---

## 设计详情

### 修改 1：CourseDetailPage.tsx

**文件：** `frontend/src/pages/CourseDetailPage.tsx`
**位置：** 第 175 行

```tsx
// ===== 修改前 =====
<button
  onClick={() => navigate(`/courses/${slug}/learn`)}
  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm transition-colors"
>
  开始学习
</button>

// ===== 修改后 =====
<button
  onClick={() => navigate(`/courses/${slug}/learn?chapterId=${chapter.id}`)}
  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm transition-colors"
>
  开始学习
</button>
```

### 修改 2：CourseLearnPage.tsx

**文件：** `frontend/src/pages/CourseLearnPage.tsx`
**位置：** 第 43-65 行（`loadCourse` 函数）

```tsx
// ===== 修改前 =====
const loadCourse = async () => {
  if (!slug) return;
  setLoading(true);
  try {
    const data = await getCourseDetail(slug);
    setCourse(data);
    // 初始化章节进度
    const progress = data.chapters.map((ch) => ({
      chapter_id: ch.id,
      status: 'not_started' as const,
    }));
    setChapterProgress(progress);

    // 默认选择第一个章节
    if (data.chapters.length > 0) {
      setCurrentChapter(data.chapters[0]);
    }
  } catch (error) {
    console.error('加载课程失败:', error);
  } finally {
    setLoading(false);
  }
};

// ===== 修改后 =====
const loadCourse = async () => {
  if (!slug) return;
  setLoading(true);
  try {
    const data = await getCourseDetail(slug);
    setCourse(data);

    // 初始化章节进度
    const progress = data.chapters.map((ch) => ({
      chapter_id: ch.id,
      status: 'not_started' as const,
    }));
    setChapterProgress(progress);

    // 从 URL 参数获取章节 ID
    const urlParams = new URLSearchParams(window.location.search);
    const chapterIdParam = urlParams.get('chapterId');

    if (chapterIdParam) {
      // 找到对应章节
      const chapter = data.chapters.find((ch) => ch.id.toString() === chapterIdParam);
      if (chapter) {
        setCurrentChapter(chapter);
      } else {
        // 章节不存在，使用第一章
        setCurrentChapter(data.chapters[0]);
      }
    } else if (data.chapters.length > 0) {
      // 没有参数，默认选择第一个章节
      setCurrentChapter(data.chapters[0]);
    }
  } catch (error) {
    console.error('加载课程失败:', error);
  } finally {
    setLoading(false);
  }
};
```

---

## 验证标准

### 功能验证

- [ ] 点击第 1 章"开始学习"进入第 1 章
- [ ] 点击第 2 章"开始学习"进入第 2 章
- [ ] 点击第 3 章"开始学习"进入第 3 章
- [ ] 以此类推，所有章节都能正确跳转

### URL 验证

- [ ] URL 包含 `chapterId` 参数
- [ ] 刷新页面后仍停留在当前章节
- [ ] 可以直接通过 URL 访问特定章节

### 兼容性验证

- [ ] 没有 chapterId 参数时默认进入第一章
- [ ] chapterId 无效时默认进入第一章
- [ ] 课程章节为空时不报错

---

## 相关文件

| 文件 | 修改类型 |
|------|----------|
| `frontend/src/pages/CourseDetailPage.tsx` | 修改跳转逻辑 |
| `frontend/src/pages/CourseLearnPage.tsx` | 添加 URL 参数解析 |

---

## 后续任务

修复完成后，继续执行 `docs/plans/2026-03-12-course-quiz-redesign-plan.md` 中的测验重新设计任务。
