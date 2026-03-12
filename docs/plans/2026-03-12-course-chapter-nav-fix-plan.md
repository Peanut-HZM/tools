# 课程章节跳转修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复课程详情页点击章节跳转错误，实现正确跳转到所选章节

**Architecture:**
- 使用 URL 参数传递章节 ID
- CourseDetailPage 跳转时传递 chapterId
- CourseLearnPage 从 URL 读取 chapterId 并加载对应章节

**Tech Stack:** React, TypeScript, react-router-dom

---

## Task 1: 创建测试文件

**Files:**
- Create: `tests/test_course_chapter_navigation.test.tsx`

### 步骤 1: 创建测试文件

```tsx
// tests/test_course_chapter_navigation.test.tsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CourseDetailPage from '../frontend/src/pages/CourseDetailPage';
import CourseLearnPage from '../frontend/src/pages/CourseLearnPage';
import * as coursePlatform from '../frontend/src/services/coursePlatform';

// Mock API 调用
vi.mock('../frontend/src/services/coursePlatform', () => ({
  getCourseDetail: vi.fn(),
  getCourseReviews: vi.fn(),
  submitReview: vi.fn(),
  enrollCourse: vi.fn(),
  getMyCourses: vi.fn(),
}));

const mockCourse = {
  id: 4,
  slug: 'openspec-vibecoding',
  title: 'OpenSpec VibeCoding 实践指南',
  description: '课程描述',
  cover_image: null,
  category: null,
  statistics: {
    view_count: 100,
    enroll_count: 50,
    like_count: 20,
    bookmark_count: 10,
    review_count: 5,
    avg_rating: 4.5,
  },
  chapters: [
    { id: 1, slug: 'chapter-1', title: '第一章', order: 1, content: '内容 1', chapter_type: 'story', video_url: null, is_locked: false, duration_minutes: 30 },
    { id: 2, slug: 'chapter-2', title: '第二章', order: 2, content: '内容 2', chapter_type: 'story', video_url: null, is_locked: false, duration_minutes: 30 },
    { id: 3, slug: 'chapter-3', title: '第三章', order: 3, content: '内容 3', chapter_type: 'story', video_url: null, is_locked: false, duration_minutes: 30 },
  ],
};

describe('课程章节跳转', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (coursePlatform.getCourseDetail as any).mockResolvedValue(mockCourse);
    (coursePlatform.getCourseReviews as any).mockResolvedValue([]);
    (coursePlatform.getMyCourses as any).mockResolvedValue({ courses: [] });
  });

  it('CourseDetailPage - 点击不同章节应跳转到对应 chapterId', async () => {
    render(
      <MemoryRouter initialEntries={['/courses/openspec-vibecoding']}>
        <Routes>
          <Route path="/courses/:slug" element={<CourseDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('第一章')).toBeInTheDocument();
    });

    // 获取所有"开始学习"按钮
    const startButtons = screen.getAllByText('开始学习');

    // 点击第一章的按钮，应该跳转到 chapterId=1
    fireEvent.click(startButtons[0]);
    // 验证跳转 URL（通过 mock navigate 或检查 window.location）

    // 点击第二章的按钮，应该跳转到 chapterId=2
    fireEvent.click(startButtons[1]);

    // 点击第三章的按钮，应该跳转到 chapterId=3
    fireEvent.click(startButtons[2]);
  });

  it('CourseLearnPage - 应能从 URL 读取 chapterId 并加载对应章节', async () => {
    render(
      <MemoryRouter initialEntries={['/courses/openspec-vibecoding/learn?chapterId=2']}>
        <Routes>
          <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('第二章')).toBeInTheDocument();
    });
  });

  it('CourseLearnPage - 没有 chapterId 时应默认加载第一章', async () => {
    render(
      <MemoryRouter initialEntries={['/courses/openspec-vibecoding/learn']}>
        <Routes>
          <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('第一章')).toBeInTheDocument();
    });
  });

  it('CourseLearnPage - chapterId 无效时应默认加载第一章', async () => {
    render(
      <MemoryRouter initialEntries={['/courses/openspec-vibecoding/learn?chapterId=999']}>
        <Routes>
          <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('第一章')).toBeInTheDocument();
    });
  });
});
```

### 步骤 2: 运行测试验证失败

```bash
cd /Users/huazhongmin/IdeaProjects/tools
npm run test -- tests/test_course_chapter_navigation.test.tsx
```

预期：FAIL - CourseDetailPage 跳转不带 chapterId，CourseLearnPage 不读取 URL 参数

---

## Task 2: 修改 CourseDetailPage.tsx

**Files:**
- Modify: `frontend/src/pages/CourseDetailPage.tsx:175`

### 步骤 1: 修改跳转逻辑

```tsx
// frontend/src/pages/CourseDetailPage.tsx
// 第 174-179 行

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

### 步骤 2: 运行测试验证

```bash
npm run test -- tests/test_course_chapter_navigation.test.tsx
```

预期：部分 PASS - CourseDetailPage 测试通过，CourseLearnPage 测试仍失败

### 步骤 3: 提交

```bash
git add frontend/src/pages/CourseDetailPage.tsx
git commit -m "fix: CourseDetailPage 跳转时传递 chapterId 参数"
```

---

## Task 3: 修改 CourseLearnPage.tsx

**Files:**
- Modify: `frontend/src/pages/CourseLearnPage.tsx:43-65`

### 步骤 1: 添加 URL 参数解析逻辑

```tsx
// frontend/src/pages/CourseLearnPage.tsx
// 第 43-65 行（loadCourse 函数）

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

### 步骤 2: 运行测试验证通过

```bash
npm run test -- tests/test_course_chapter_navigation.test.tsx
```

预期：全部 PASS

### 步骤 3: 提交

```bash
git add frontend/src/pages/CourseLearnPage.tsx
git commit -m "fix: CourseLearnPage 从 URL 读取 chapterId 加载对应章节"
```

---

## Task 4: 浏览器验证

### 步骤 1: 启动服务

```bash
# 后端（端口 19092）
cd backend
uvicorn app.main:app --reload --port 19092 &

# 前端（端口 5178）
cd frontend
npm run dev &
```

### 步骤 2: 手动验证

1. 访问 `http://localhost:5178/courses`
2. 点击"立即学习"进入课程详情页
3. 点击第 1 章"开始学习"，验证 URL 为 `/courses/xxx/learn?chapterId=1`
4. 点击第 2 章"开始学习"，验证 URL 为 `/courses/xxx/learn?chapterId=2`
5. 点击第 3 章"开始学习"，验证 URL 为 `/courses/xxx/learn?chapterId=3`
6. 验证刷新页面后仍停留在当前章节
7. 验证直接访问带 chapterId 的 URL 能正确加载

### 步骤 3: 边界情况验证

1. 访问 `/courses/xxx/learn`（无 chapterId），验证默认加载第一章
2. 访问 `/courses/xxx/learn?chapterId=999`（无效 ID），验证默认加载第一章

---

## Task 5: 回滚方案

### 回滚脚本

```bash
# 回滚到修复前的版本
git revert HEAD~2..HEAD

# 或者重置到特定提交
git reset --hard <commit-hash-before-fix>
```

### 回滚验证

```bash
# 重启前端服务
cd frontend
npm run dev &

# 验证跳转功能回到原来状态（所有章节都跳转到第一章）
```

---

## 验收清单

### 代码质量
- [ ] 测试文件通过
- [ ] 没有 TypeScript 错误
- [ ] 代码格式符合规范

### 功能验证
- [ ] 点击第 1 章进入第 1 章
- [ ] 点击第 2 章进入第 2 章
- [ ] 点击第 3 章进入第 3 章
- [ ] 刷新页面保持当前章节
- [ ] 无参数时默认第一章
- [ ] 参数无效时默认第一章

### 浏览器 Console
- [ ] 无 JavaScript 错误
- [ ] 无警告信息

---

## 后续任务

修复完成后，继续执行 `docs/plans/2026-03-12-course-quiz-redesign-plan.md` 中的测验重新设计任务。
