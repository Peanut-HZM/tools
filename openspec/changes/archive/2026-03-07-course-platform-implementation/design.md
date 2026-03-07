# 课程设计文档

**变更:** course-platform-implementation
**创建日期:** 2026-03-07
**状态:** 草稿

---

## 1. 架构设计

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│  前端 (React + TypeScript)                                   │
├─────────────────────────────────────────────────────────────┤
│  /courses              课程列表页                            │
│  /courses/:slug        课程详情页                            │
│  /courses/:slug/learn  课程学习页                            │
│  /my-courses           我的课程                              │
│  /admin/course         后台课程管理                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  后端 (FastAPI + SQLAlchemy)                                 │
├─────────────────────────────────────────────────────────────┤
│  /api/courses            课程公开 API                        │
│  /api/my-courses         用户课程 API                        │
│  /api/admin/courses      后台管理 API                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ ORM
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  数据库 (MySQL/PostgreSQL)                                   │
├─────────────────────────────────────────────────────────────┤
│  courses, course_categories, course_chapters, ...           │
│  course_enrollments, course_progress, ...                   │
│  course_statistics, course_reviews, ...                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 组件设计

### 2.1 前端组件树

```
App
├── Layout
│   ├── Header
│   └── Footer
├── CoursesPage
│   ├── PageHeader
│   ├── FilterSidebar
│   └── CourseGrid
│       └── CourseCard
├── CourseDetailPage
│   ├── CourseBanner
│   ├── CourseTabs
│   │   ├── CourseIntro
│   │   ├── CourseChapters
│   │   ├── CourseReviews
│   │   └── CourseInstructor
│   └── EnrollmentBar
├── CourseLearnPage (复用扩展现有 OpenSpecCourse)
│   ├── ChapterNavigation
│   ├── ChapterContent
│   ├── QuizView
│   └── ProgressBar
├── MyCoursesPage
│   └── CourseList
└── AdminLayout
    └── CourseManagement
        ├── CourseList
        ├── CourseEditor
        │   └── RichTextEditor (TipTap)
        ├── ChapterManager
        ├── QuizManager
        └── ResourceManager
```

---

## 3. UI/UX 设计

### 3.1 课程卡片设计

```
┌─────────────────────────────────┐
│  [封面图 16:9]                   │
│  ┌─────────────────────────────┐│
│  │  📖 OpenSpec VibeCoding      ││
│  │  从 AI 小白到 Spec 高手         ││
│  │  ⭐⭐⭐⭐⭐ 4.9 (2.3k)        ││
│  │  👨‍🏫 华中敏                   ││
│  │  ─────────────────────────  ││
│  │  ❤️ 12.5k  👁 89.2k  📚 12   ││
│  │  [立即学习 →]                ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

**样式规范:**
- 与首页工具卡片保持一致
- 深色主题：slate-900 背景
- 渐变卡片：紫色/蓝色主题
- 悬停效果：scale-105 + shadow

### 3.2 颜色方案

```css
/* 主色调 - 与现有系统一致 */
--primary: #06b6d4;  /* cyan-500 */
--secondary: #3b82f6; /* blue-500 */
--accent: #a855f7; /* purple-500 */

/* 背景色 */
--bg-primary: #0f172a; /* slate-900 */
--bg-secondary: #1e293b; /* slate-800 */
--bg-card: rgba(30, 41, 59, 0.5);

/* 文字色 */
--text-primary: #f8fafc; /* slate-50 */
--text-secondary: #94a3b8; /* slate-400 */
```

---

## 4. 技术选型

### 4.1 前端依赖

```json
{
  "@tiptap/react": "^2.0.0",
  "@tiptap/starter-kit": "^2.0.0",
  "@tiptap/extension-code-block-lowlight": "^2.0.0",
  "highlight.js": "^11.0.0",
  "react-dropzone": "^14.0.0",
  "react-markdown": "^9.0.0",
  "rehype-highlight": "^7.0.0"
}
```

### 4.2 后端依赖

```txt
# 现有依赖，无需新增
fastapi
sqlalchemy
pydantic
```

---

## 5. 文件结构

### 5.1 后端

```
backend/
├── app/
│   ├── models/
│   │   ├── course_platform.py    # 新增
│   │   └── openspec_course.py    # 保留
│   ├── schemas/
│   │   ├── course_platform.py    # 新增
│   │   └── openspec_course.py    # 保留
│   ├── routes/
│   │   ├── course_platform.py    # 新增
│   │   └── openspec_course.py    # 保留
│   ├── services/
│   │   ├── course_platform_service.py    # 新增
│   │   ├── course_statistics_service.py  # 新增
│   │   └── openspec_course_service.py    # 保留
│   └── utils/
│       └── oss.py                  # 扩展现有
└── alembic/
    └── versions/
        └── xxxx_add_course_platform_tables.py  # 新增
```

### 5.2 前端

```
frontend/
├── src/
│   ├── pages/
│   │   ├── CoursesPage.tsx         # 新增
│   │   ├── CourseDetailPage.tsx    # 新增
│   │   └── MyCoursesPage.tsx       # 新增
│   ├── components/
│   │   ├── Courses/
│   │   │   ├── CourseCard.tsx
│   │   │   ├── FilterSidebar.tsx
│   │   │   └── CourseReviews.tsx
│   │   ├── Common/
│   │   │   ├── RichTextEditor.tsx  # 新增
│   │   │   └── OssUploader.tsx     # 新增
│   │   └── Admin/
│   │       └── CourseManagement/
│   │           ├── CourseList.tsx
│   │           ├── CourseEditor.tsx
│   │           └── ...
│   ├── services/
│   │   └── coursePlatform.ts       # 新增
│   └── stores/
│       └── courseStore.ts          # 新增
```

---

## 6. 验收标准

### 6.1 设计验收

- [ ] UI 设计与现有系统风格一致
- [ ] 响应式布局适配移动端
- [ ] 组件复用性良好
- [ ] 代码结构清晰

### 6.2 功能验收

- [ ] 所有页面能正常访问
- [ ] 所有 API 正常工作
- [ ] 数据迁移完整
- [ ] 无控制台错误

---

**审批:**
- [ ] 设计审批
