# 课程后台管理迁移计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将后台管理从 `openspec_course` 表迁移到 `course_platform` 表，统一数据源，解决用户端看到旧数据的问题。

**Architecture:**
1. 修改后台管理前端 API 服务，从 `/api/openspec-course` 改为 `/api/admin/courses`
2. 更新后台管理导入导出功能，使用 `course_platform` 模型
3. 迁移 `openspec_course_chapters` 数据到 `course_chapters`
4. 移除不再使用的 `openspec_course` 相关代码

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript

---

## 现状分析

### 问题原因

- **后台管理**: 使用 `/api/openspec-course` 接口，操作 `openspec_course_chapters` 表
- **用户端**: 使用 `/api/courses` 接口，读取 `course_chapters` 表
- **结果**: 后台更新的数据用户端看不到

### 目标架构

- **统一数据源**: `courses` / `course_chapters` / `course_quizzes` / `course_quiz_questions` / `course_quiz_options` / `course_resources`
- **后台管理**: 使用 `/api/admin/courses` 接口
- **用户端**: 继续使用 `/api/courses` 接口（无需修改）

---

## 数据模型对比

### openspec_course 模型 (要被移除)

| 表名 | 字段 | 说明 |
|------|------|------|
| `openspec_course_chapters` | id, slug, title, order, content, chapter_type, video_url, is_locked, required_quiz_id | 章节表 (无 course_id) |
| `openspec_course_quizzes` | id, chapter_id, title, passing_score | 测验表 |
| `openspec_course_quiz_questions` | id, quiz_id, question_text, question_type, correct_answer, explanation, order | 题目表 |
| `openspec_course_quiz_options` | id, question_id, option_text, option_index | 选项表 |
| `openspec_course_resources` | id, chapter_id, resource_type, title, content, extra_data | 资源表 |

### course_platform 模型 (保留)

| 表名 | 字段 | 说明 |
|------|------|------|
| `courses` | id, slug, title, description, cover_image, category_id, status | 课程主表 |
| `course_chapters` | id, course_id, slug, title, order, content, chapter_type, video_url, is_locked, duration_minutes | 章节表 (有 course_id) |
| `course_quizzes` | id, chapter_id, title, passing_score | 测验表 |
| `course_quiz_questions` | id, quiz_id, question_text, question_type, correct_answer, explanation, order | 题目表 |
| `course_quiz_options` | id, question_id, option_text, option_index | 选项表 |
| `course_resources` | id, chapter_id, resource_type, title, content, extra_data | 资源表 |

### 关键差异

1. `course_chapters` 有 `course_id` 字段，`openspec_course_chapters` 没有
2. `course_chapters` 有 `duration_minutes` 字段
3. Schema 字段基本一致，可以直接迁移

---

## 迁移步骤

### Task 1: 数据迁移脚本

**Files:**
- Create: `backend/scripts/migrate_openspec_to_platform.py`

**Step 1: 创建迁移脚本**

```python
#!/usr/bin/env python3
"""
将 openspec_course 数据迁移到 course_platform

1. 检查 courses 表中是否存在 'openspec-vibecoding-practice' 课程
2. 如果存在，将 openspec_course_chapters 数据迁移到 course_chapters
3. 迁移测验、题目、选项、资源数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.openspec_course import (
    OpenSpecCourseChapter,
    OpenSpecCourseQuiz,
    OpenSpecCourseQuizQuestion,
    OpenSpecCourseQuizOption,
    OpenSpecCourseResource,
)
from app.models.course_platform import (
    Course,
    CourseChapter,
    CourseQuiz,
    CourseQuizQuestion,
    CourseQuizOption,
    CourseResource,
)

DATABASE_URL = "sqlite:///./backend/app.db"  # 根据实际配置调整

def migrate():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 1. 查找或创建课程
        course = db.query(Course).filter_by(slug="openspec-vibecoding-practice").first()
        if not course:
            print("创建课程...")
            course = Course(
                slug="openspec-vibecoding-practice",
                title="OpenSpec VibeCoding 实践指南",
                description="掌握 AI 编程的核心技能，从 Rules 配置到 Skill 系统，提升开发效率",
                status="published",
            )
            db.add(course)
            db.flush()
            print(f"创建课程 ID={course.id}")
        else:
            print(f"找到现有课程 ID={course.id}")

        # 2. 迁移章节数据
        print("迁移章节数据...")
        openspec_chapters = db.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()

        for os_chapter in openspec_chapters:
            # 检查是否已存在
            existing = db.query(CourseChapter).filter_by(slug=os_chapter.slug).first()
            if existing:
                # 更新现有章节
                existing.title = os_chapter.title
                existing.content = os_chapter.content
                existing.order = os_chapter.order
                existing.chapter_type = os_chapter.chapter_type
                existing.video_url = os_chapter.video_url
                existing.is_locked = os_chapter.is_locked
                print(f"  更新章节 {os_chapter.slug}")
            else:
                # 创建新章节
                chapter = CourseChapter(
                    course_id=course.id,
                    slug=os_chapter.slug,
                    title=os_chapter.title,
                    order=os_chapter.order,
                    content=os_chapter.content,
                    chapter_type=os_chapter.chapter_type,
                    video_url=os_chapter.video_url,
                    is_locked=os_chapter.is_locked,
                    duration_minutes=10,  # 默认值
                )
                db.add(chapter)
                db.flush()
                print(f"  创建章节 {os_chapter.slug} ID={chapter.id}")

        # 3. 迁移测验数据
        print("迁移测验数据...")
        openspec_quizzes = db.query(OpenSpecCourseQuiz).all()

        for os_quiz in openspec_quizzes:
            os_chapter = db.query(OpenSpecCourseChapter).filter_by(id=os_quiz.chapter_id).first()
            if not os_chapter:
                print(f"  跳过测验 {os_quiz.id}，章节不存在")
                continue

            # 找到对应的 course_chapter
            course_chapter = db.query(CourseChapter).filter_by(slug=os_chapter.slug).first()
            if not course_chapter:
                print(f"  跳过测验 {os_quiz.id}，course_chapter 不存在")
                continue

            # 检查是否已存在
            existing = db.query(CourseQuiz).filter_by(slug=os_quiz.title.replace(" ", "-").lower()).first()
            if existing:
                # 更新
                existing.title = os_quiz.title
                existing.passing_score = os_quiz.passing_score
                existing.chapter_id = course_chapter.id
                print(f"  更新测验 {os_quiz.title}")
            else:
                # 创建
                quiz = CourseQuiz(
                    chapter_id=course_chapter.id,
                    slug=os_quiz.title.replace(" ", "-").lower(),
                    title=os_quiz.title,
                    passing_score=os_quiz.passing_score,
                )
                db.add(quiz)
                db.flush()
                print(f"  创建测验 {os_quiz.title} ID={quiz.id}")

        # 4. 迁移测验题目
        print("迁移测验题目...")
        openspec_questions = db.query(OpenSpecCourseQuizQuestion).all()

        for os_question in openspec_questions:
            os_quiz = db.query(OpenSpecCourseQuiz).filter_by(id=os_question.quiz_id).first()
            if not os_quiz:
                continue

            # 找到对应的 course_quiz
            course_quiz = db.query(CourseQuiz).filter_by(slug=os_quiz.title.replace(" ", "-").lower()).first()
            if not course_quiz:
                continue

            # 创建题目
            question = CourseQuizQuestion(
                quiz_id=course_quiz.id,
                question_text=os_question.question_text,
                question_type=os_question.question_type,
                correct_answer=os_question.correct_answer,
                explanation=os_question.explanation,
                order=os_question.order,
            )
            db.add(question)
            db.flush()

            # 迁移选项
            os_options = db.query(OpenSpecCourseQuizOption).filter_by(question_id=os_question.id).all()
            for os_option in os_options:
                option = CourseQuizOption(
                    question_id=question.id,
                    option_text=os_option.option_text,
                    option_index=os_option.option_index,
                )
                db.add(option)

        # 5. 迁移资源数据
        print("迁移资源数据...")
        openspec_resources = db.query(OpenSpecCourseResource).all()

        for os_resource in openspec_resources:
            os_chapter = db.query(OpenSpecCourseChapter).filter_by(id=os_resource.chapter_id).first()
            if not os_chapter:
                continue

            course_chapter = db.query(CourseChapter).filter_by(slug=os_chapter.slug).first()
            if not course_chapter:
                continue

            resource = CourseResource(
                chapter_id=course_chapter.id,
                resource_type=os_resource.resource_type,
                title=os_resource.title,
                content=os_resource.content,
                extra_data=os_resource.extra_data,
            )
            db.add(resource)

        # 6. 提交
        db.commit()
        print("✓ 迁移完成!")

    except Exception as e:
        db.rollback()
        print(f"✗ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0

if __name__ == "__main__":
    exit(migrate())
```

**Step 2: 执行迁移脚本**

```bash
cd backend
python scripts/migrate_openspec_to_platform.py
```

**预期输出:**
```
找到现有课程 ID=X
迁移章节数据...
  更新章节 intro-vibe-coding
  更新章节 ai-problems
  ...
迁移测验数据...
  更新测验 VibeCoding 入门测验
...
✓ 迁移完成!
```

**Step 3: 验证迁移结果**

```bash
sqlite3 backend/app.db "SELECT id, slug, title, course_id FROM course_chapters ORDER BY order;"
```

---

### Task 2: 更新后台管理 API 服务

**Files:**
- Modify: `frontend/src/services/openspecCourseAdmin.ts` → 删除或重命名
- Create: `frontend/src/services/courseAdmin.ts`

**Step 1: 创建新的课程管理服务**

```typescript
/**
 * 课程管理 API 服务（使用 course_platform 模型）
 */
import axios from 'axios';

const API_BASE_URL = '/api/admin/courses';

export interface Course {
  id: number;
  slug: string;
  title: string;
  description: string;
  cover_image?: string | null;
  status: string;
  category_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface CourseChapter {
  id: number;
  course_id: number;
  slug: string;
  title: string;
  order: number;
  content: string;
  chapter_type: string;
  video_url?: string | null;
  is_locked: boolean;
  duration_minutes: number;
  created_at: string;
  updated_at: string;
}

// ============ 课程管理 API ============

/**
 * 获取所有课程（管理后台）
 */
export const getCourses = async (params?: {
  page?: number;
  limit?: number;
  status?: string;
}): Promise<{ courses: Course[]; total: number; page: number; limit: number }> => {
  const response = await axios.get(API_BASE_URL, { params });
  return response.data;
};

/**
 * 获取课程详情（管理后台）
 */
export const getCourse = async (courseId: number): Promise<Course> => {
  const response = await axios.get(`${API_BASE_URL}/${courseId}`);
  return response.data;
};

/**
 * 创建课程
 */
export const createCourse = async (data: Partial<Course>): Promise<Course> => {
  const response = await axios.post(API_BASE_URL, data);
  return response.data;
};

/**
 * 更新课程
 */
export const updateCourse = async (courseId: number, data: Partial<Course>): Promise<Course> => {
  const response = await axios.put(`${API_BASE_URL}/${courseId}`, data);
  return response.data;
};

/**
 * 删除课程
 */
export const deleteCourse = async (courseId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/${courseId}`);
};

// ============ 章节管理 API ============

/**
 * 获取课程的所有章节
 */
export const getCourseChapters = async (courseId: number): Promise<CourseChapter[]> => {
  const response = await axios.get(`${API_BASE_URL}/${courseId}/chapters`);
  return response.data;
};

/**
 * 创建章节
 */
export const createChapter = async (courseId: number, data: Partial<CourseChapter>): Promise<CourseChapter> => {
  const response = await axios.post(`${API_BASE_URL}/${courseId}/chapters`, data);
  return response.data;
};

/**
 * 更新章节
 */
export const updateChapter = async (courseId: number, chapterId: number, data: Partial<CourseChapter>): Promise<CourseChapter> => {
  const response = await axios.put(`${API_BASE_URL}/${courseId}/chapters/${chapterId}`, data);
  return response.data;
};

/**
 * 删除章节
 */
export const deleteChapter = async (courseId: number, chapterId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/${courseId}/chapters/${chapterId}`);
};

/**
 * 批量更新章节顺序
 */
export const reorderChapters = async (courseId: number, chapterOrders: { id: number; order: number }[]): Promise<void> => {
  await axios.put(`${API_BASE_URL}/${courseId}/chapters/reorder`, chapterOrders);
};
```

**Step 2: 更新管理后台组件引用**

修改 `frontend/src/components/Admin/CourseManagement.tsx` 等组件，从引用 `openspecCourseAdmin` 改为引用新的 `courseAdmin` 服务。

**Step 3: 提交**

```bash
git add frontend/src/services/courseAdmin.ts
git commit -m "feat: 创建课程管理服务（使用 course_platform 模型）"
```

---

### Task 3: 更新导入导出服务

**Files:**
- Modify: `backend/app/services/course_import_export_service.py`
- Modify: `backend/app/routes/openspec_course.py`

**Step 1: 检查导入导出服务**

查看 `course_import_export_service.py` 是否已存在，如果存在则更新其使用 `course_platform` 模型。

**Step 2: 更新导入逻辑**

确保导入时将数据写入：
- `courses` 表
- `course_chapters` 表
- `course_quizzes` 表
- `course_quiz_questions` 表
- `course_quiz_options` 表
- `course_resources` 表

**Step 3: 更新导出逻辑**

确保导出时从上述表读取数据。

---

### Task 4: 移除 openspec_course 相关代码

**Files:**
- Delete: `backend/app/models/openspec_course.py`
- Delete: `backend/app/schemas/openspec_course.py`
- Delete: `backend/app/services/openspec_course_service.py`
- Delete: `backend/app/routes/openspec_course.py`
- Delete: `frontend/src/services/openspecCourseAdmin.ts`

**Step 1: 确认没有其他地方引用**

```bash
cd backend
grep -r "openspec_course" --include="*.py" .
grep -r "openspec-course" --include="*.py" .
```

**Step 2: 删除文件**

```bash
rm backend/app/models/openspec_course.py
rm backend/app/schemas/openspec_course.py
rm backend/app/services/openspec_course_service.py
rm backend/app/routes/openspec_course.py
rm frontend/src/services/openspecCourseAdmin.ts
```

**Step 3: 删除数据库表**

```sql
DROP TABLE IF EXISTS openspec_user_progress;
DROP TABLE IF EXISTS openspec_course_resources;
DROP TABLE IF EXISTS openspec_course_quiz_options;
DROP TABLE IF EXISTS openspec_course_quiz_questions;
DROP TABLE IF EXISTS openspec_course_quizzes;
DROP TABLE IF EXISTS openspec_course_chapters;
```

**Step 4: 提交**

```bash
git add -A
git commit -m "refactor: 移除不再使用的 openspec_course 相关代码"
```

---

## 验证步骤

### 1. 验证数据迁移

```bash
# 检查章节数
sqlite3 backend/app.db "SELECT COUNT(*) FROM course_chapters;"

# 检查测验数
sqlite3 backend/app.db "SELECT COUNT(*) FROM course_quizzes;"

# 检查题目数
sqlite3 backend/app.db "SELECT COUNT(*) FROM course_quiz_questions;"
```

### 2. 验证后台管理

1. 访问后台管理页面
2. 修改某个章节内容
3. 保存

### 3. 验证用户端

1. 访问用户端课程详情页
2. 确认显示的是最新数据
3. 检查章节内容是否正确

### 4. 验证导入导出

1. 导出课程数据
2. 清空数据
3. 导入数据
4. 验证数据完整性

---

## 回滚方案

如果迁移失败，执行以下命令回滚：

```bash
# 恢复数据库备份
cp backend/app.db.backup backend/app.db

# 或者删除迁移的数据
sqlite3 backend/app.db <<EOF
DELETE FROM course_resources WHERE chapter_id IN (SELECT id FROM course_chapters WHERE course_id = X);
DELETE FROM course_quiz_options WHERE question_id IN (SELECT id FROM course_quiz_questions WHERE quiz_id IN (SELECT id FROM course_quizzes WHERE chapter_id IN (SELECT id FROM course_chapters WHERE course_id = X)));
DELETE FROM course_quiz_questions WHERE quiz_id IN (SELECT id FROM course_quizzes WHERE chapter_id IN (SELECT id FROM course_chapters WHERE course_id = X));
DELETE FROM course_quizzes WHERE chapter_id IN (SELECT id FROM course_chapters WHERE course_id = X);
DELETE FROM course_chapters WHERE course_id = X;
DELETE FROM courses WHERE id = X;
EOF
```

---

## 完成标准

- [ ] 数据迁移完成（所有章节、测验、题目、资源）
- [ ] 后台管理使用 `course_platform` 模型
- [ ] 用户端显示最新数据
- [ ] 导入导出功能正常
- [ ] `openspec_course` 相关代码已移除
- [ ] 所有测试通过
