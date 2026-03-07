# 课程学习平台设计文档

**创建日期:** 2026-03-07
**状态:** 已批准
**类型:** 新功能 - 完整平台化

---

## 1. 项目概述

### 1.1 项目背景

当前系统已有 OpenSpec VibeCoding 课程的单课程实现（5 个章节、测验、资源），但缺乏：
- 多课程管理能力
- 课程统计和互动功能
- 统一的课程学习入口
- 完善的后台课程管理

### 1.2 项目目标

打造一个完整的课程学习平台，支持：
- ✅ 多课程管理和展示
- ✅ 课程统计（点赞、观看、收藏等真实数据）
- ✅ 用户学习进度追踪
- ✅ 课程评价系统
- ✅ 完善的后台管理（富文本编辑、OSS 上传）
- ✅ 保留现有 OpenSpec VibeCoding 课程内容

### 1.3 设计决策记录

| 决策点 | 选项 | 选择 |
|--------|------|------|
| 课程列表位置 | 独立页面 / 工具分类 / 特殊工具 | 独立页面 `/courses` |
| 卡片样式 | 工具卡片风格 / 教育指标 / 进度显示 | 工具卡片风格 |
| 后台管理范围 | 单课程 / 多课程 / 多课程 + 元数据 | 多课程 + 元数据 |
| 编辑器 | 简单 Markdown / 富文本 +OSS / Markdown+ 资源库 | 富文本 + OSS 上传 |
| 数据处理 | 保持不变 / 重新设计后导入 | 重新设计后导入 |
| 平台化程度 | 渐进式 / 快速 MVP / 完整平台 | 完整平台化 |
| 富文本编辑器 | react-markdown / TipTap / Quill | TipTap |
| 后台入口 | 扩展现有 / 新建 | 扩展现有 `/admin/course` |

---

## 2. 数据库设计

### 2.1 ER 图

```
┌──────────────────┐       ┌──────────────────┐
│   courses        │       │ course_categories│
├──────────────────┤       ├──────────────────┤
│ id (PK)          │◄──────│ id (PK)          │
│ title            │       │ name             │
│ slug             │       │ slug             │
│ description      │       │ parent_id (FK)   │
│ cover_image      │       │ sort_order       │
│ category_id (FK) │       │ icon             │
│ instructor_id    │       └──────────────────┘
│ price            │
│ status           │       ┌──────────────────┐
│ created_at       │       │ course_chapters  │
│ updated_at       │       ├──────────────────┤
└──────────────────┘       │ id (PK)          │
         │                 │ course_id (FK)   │
         │                 │ slug             │
         │                 │ title            │
         ▼                 │ order            │
┌──────────────────┐       │ content          │
│course_statistics │       │ chapter_type     │
├──────────────────┤       │ video_url        │
│ id (PK)          │       │ is_locked        │
│ course_id (UK)   │       │ duration_minutes │
│ view_count       │       │ created_at       │
│ enroll_count     │       │ updated_at       │
│ like_count       │       └──────────────────┘
│ bookmark_count   │
│ review_count     │       ┌──────────────────┐
│ avg_rating       │       │ course_quizzes   │
│ completed_count  │       ├──────────────────┤
│ updated_at       │       │ id (PK)          │
└──────────────────┘       │ chapter_id (FK)  │
                           │ title            │
┌──────────────────┐       │ passing_score    │
│course_enrollments│       │ questions (JSON) │
├──────────────────┤       └──────────────────┘
│ id (PK)          │
│ user_id          │       ┌──────────────────┐
│ course_id (FK)   │       │course_resources  │
│ enrolled_at      │       ├──────────────────┤
│ completed_at     │       │ id (PK)          │
│ status           │       │ chapter_id (FK)  │
│ progress_percent │       │ resource_type    │
└──────────────────┘       │ title            │
                           │ content          │
┌──────────────────┐       │ file_url         │
│course_progress   │       │ file_size        │
├──────────────────┤       └──────────────────┘
│ id (PK)          │
│ user_id          │       ┌──────────────────┐
│ chapter_id (FK)  │       │course_reviews    │
│ status           │       ├──────────────────┤
│ quiz_score       │       │ id (PK)          │
│ quiz_passed      │       │ user_id          │
│ video_progress   │       │ course_id (FK)   │
│ last_accessed_at │       │ rating           │
└──────────────────┘       │ comment          │
                           │ created_at       │
┌──────────────────┐       └──────────────────┘
│course_interactions│
├──────────────────┤
│ id (PK)          │
│ user_id          │
│ course_id (FK)   │
│ interaction_type │
│ created_at       │
└──────────────────┘
```

### 2.2 表结构详情

#### 2.2.1 courses - 课程主表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 课程 ID |
| title | VARCHAR(200) | NOT NULL | 课程标题 |
| slug | VARCHAR(100) | UNIQUE, NOT NULL | 课程标识符（用于 URL） |
| description | TEXT | NOT NULL | 课程描述 |
| cover_image | VARCHAR(500) | NULL | 封面图 URL |
| category_id | BIGINT | FOREIGN KEY | 分类 ID |
| instructor_id | BIGINT | NULL | 讲师 ID（预留） |
| price | DECIMAL(10,2) | DEFAULT 0 | 价格（0=免费） |
| status | VARCHAR(20) | DEFAULT 'draft' | draft/published/archived |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 2.2.2 course_categories - 课程分类表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 分类 ID |
| name | VARCHAR(100) | NOT NULL | 分类名称 |
| slug | VARCHAR(50) | UNIQUE, NOT NULL | 分类标识符 |
| parent_id | BIGINT | NULL, SELF FK | 父分类 ID |
| sort_order | INT | DEFAULT 0 | 排序 |
| icon | VARCHAR(50) | NULL | 图标类名 |

#### 2.2.3 course_chapters - 课程章节表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 章节 ID |
| course_id | BIGINT | FOREIGN KEY, NOT NULL | 课程 ID |
| slug | VARCHAR(100) | NOT NULL | 章节标识符 |
| title | VARCHAR(200) | NOT NULL | 章节标题 |
| order | INT | DEFAULT 0 | 章节顺序 |
| content | TEXT | NOT NULL | 章节内容（Markdown） |
| chapter_type | VARCHAR(50) | DEFAULT 'story' | story/lesson/quiz-only/code/video |
| video_url | VARCHAR(500) | NULL | 视频链接 |
| is_locked | BOOLEAN | DEFAULT FALSE | 是否锁定 |
| duration_minutes | INT | DEFAULT 0 | 预计学习时长（分钟） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 2.2.4 course_quizzes - 课程测验表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 测验 ID |
| chapter_id | BIGINT | FOREIGN KEY, NOT NULL | 章节 ID |
| title | VARCHAR(200) | NOT NULL | 测验标题 |
| passing_score | INT | DEFAULT 60 | 及格分数（0-100） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 2.2.5 course_quiz_questions - 测验题目表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 题目 ID |
| quiz_id | BIGINT | FOREIGN KEY, NOT NULL | 测验 ID |
| question_text | TEXT | NOT NULL | 题目内容 |
| question_type | VARCHAR(20) | DEFAULT 'single' | single/multiple |
| correct_answer | VARCHAR(100) | NOT NULL | 正确答案（逗号分隔） |
| explanation | TEXT | NULL | 答案解析 |
| order | INT | DEFAULT 0 | 题目顺序 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### 2.2.6 course_quiz_options - 测验选项表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 选项 ID |
| question_id | BIGINT | FOREIGN KEY, NOT NULL | 题目 ID |
| option_text | TEXT | NOT NULL | 选项内容 |
| option_index | INT | NOT NULL | 选项索引（0=A, 1=B...） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### 2.2.7 course_resources - 课程资源表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 资源 ID |
| chapter_id | BIGINT | FOREIGN KEY, NOT NULL | 章节 ID |
| resource_type | VARCHAR(50) | NOT NULL | code/contrast/video/template/image |
| title | VARCHAR(200) | NOT NULL | 资源标题 |
| content | TEXT | NOT NULL | 资源内容 |
| file_url | VARCHAR(500) | NULL | 文件 URL（OSS） |
| file_size | BIGINT | NULL | 文件大小（字节） |
| extra_data | TEXT | NULL | 额外元数据（JSON） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 2.2.8 course_enrollments - 用户课程关联表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 关联 ID |
| user_id | VARCHAR(64) | NOT NULL, INDEX | 用户 ID |
| course_id | BIGINT | FOREIGN KEY, NOT NULL | 课程 ID |
| enrolled_at | TIMESTAMP | DEFAULT NOW() | 报名时间 |
| completed_at | TIMESTAMP | NULL | 完成时间 |
| status | VARCHAR(20) | DEFAULT 'active' | active/completed |
| progress_percent | FLOAT | DEFAULT 0 | 进度百分比（0-100） |

UNIQUE KEY: (user_id, course_id)

#### 2.2.9 course_progress - 学习进度表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 进度 ID |
| user_id | VARCHAR(64) | NOT NULL | 用户 ID |
| chapter_id | BIGINT | FOREIGN KEY, NOT NULL | 章节 ID |
| status | VARCHAR(20) | DEFAULT 'not_started' | not_started/in_progress/completed |
| quiz_score | FLOAT | NULL | 测验分数（0-100） |
| quiz_passed | BOOLEAN | DEFAULT FALSE | 测验是否通过 |
| video_progress | INT | DEFAULT 0 | 视频进度（秒） |
| last_accessed_at | TIMESTAMP | DEFAULT NOW() | 最后访问时间 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

UNIQUE KEY: (user_id, chapter_id)

#### 2.2.10 course_interactions - 课程互动表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 互动 ID |
| user_id | VARCHAR(64) | NOT NULL | 用户 ID |
| course_id | BIGINT | FOREIGN KEY, NOT NULL | 课程 ID |
| interaction_type | VARCHAR(20) | NOT NULL | like/view/bookmark/favorite |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

INDEX: (course_id, interaction_type), (user_id, course_id)

#### 2.2.11 course_reviews - 课程评价表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 评价 ID |
| user_id | VARCHAR(64) | NOT NULL | 用户 ID |
| course_id | BIGINT | FOREIGN KEY, NOT NULL | 课程 ID |
| rating | INT | NOT NULL | 评分（1-5） |
| comment | TEXT | NULL | 评论内容 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

INDEX: (course_id), (user_id)

#### 2.2.12 course_statistics - 课程统计表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PRIMARY KEY, AUTO INCREMENT | 统计 ID |
| course_id | BIGINT | UNIQUE, NOT NULL | 课程 ID（唯一） |
| view_count | BIGINT | DEFAULT 0 | 浏览次数 |
| enroll_count | BIGINT | DEFAULT 0 | 报名人数 |
| like_count | BIGINT | DEFAULT 0 | 点赞数 |
| bookmark_count | BIGINT | DEFAULT 0 | 收藏数 |
| review_count | BIGINT | DEFAULT 0 | 评价数 |
| avg_rating | FLOAT | DEFAULT 0 | 平均评分 |
| completed_count | BIGINT | DEFAULT 0 | 完成人数 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

---

## 3. API 设计

### 3.1 课程公开 API

#### GET /api/courses - 获取课程列表

```
Query Parameters:
  - category: string (可选) - 分类筛选
  - search: string (可选) - 搜索关键词
  - sort: string (可选) - 排序：hot/new/rated
  - page: int (可选) - 页码，默认 1
  - limit: int (可选) - 每页数量，默认 12

Response:
{
  "courses": [...],
  "total": 100,
  "page": 1,
  "limit": 12
}
```

#### GET /api/courses/:slug - 获取课程详情

```
Response:
{
  "id": 1,
  "slug": "openspec-vibecoding",
  "title": "OpenSpec VibeCoding 课程",
  "description": "...",
  "cover_image": "...",
  "category": {...},
  "statistics": {
    "view_count": 89200,
    "like_count": 12500,
    "enroll_count": 45000,
    "avg_rating": 4.9
  },
  "chapters": [
    {
      "id": 11,
      "title": "第一章：最初的我 - 谨慎使用 AI 😰",
      "order": 1,
      "chapter_type": "story",
      "duration_minutes": 15
    }
  ],
  "instructor": {...}
}
```

#### POST /api/courses/:id/enroll - 报名课程

```
Request: {} (空 body)
Response: {
  "success": true,
  "enrollment": {...}
}
```

#### POST /api/courses/:id/like - 点赞课程

```
Response: {
  "success": true,
  "liked": true,
  "like_count": 12501
}
```

#### POST /api/courses/:id/bookmark - 收藏课程

```
Response: {
  "success": true,
  "bookmarked": true,
  "bookmark_count": 3201
}
```

#### GET /api/courses/:id/reviews - 获取课程评价

```
Query Parameters:
  - page: int (可选)
  - limit: int (可选)

Response:
{
  "reviews": [...],
  "total": 2300,
  "avg_rating": 4.9
}
```

#### POST /api/courses/:id/reviews - 提交课程评价

```
Request:
{
  "rating": 5,
  "comment": "非常好的课程！"
}
```

### 3.2 用户课程 API

#### GET /api/my-courses - 我的课程

```
Response:
{
  "courses": [
    {
      "course": {...},
      "enrollment": {
        "progress_percent": 40,
        "status": "active",
        "completed_chapters": 2,
        "total_chapters": 5
      }
    }
  ]
}
```

### 3.3 后台管理 API

#### POST /api/admin/courses - 创建课程

#### PUT /api/admin/courses/:id - 更新课程

#### DELETE /api/admin/courses/:id - 删除课程

#### GET /api/admin/courses - 课程列表（管理端）

#### POST /api/admin/courses/:id/publish - 发布课程

#### POST /api/admin/courses/:id/chapters/reorder - 重新排序章节

---

## 4. 页面设计

### 4.1 页面结构图

```
前端页面                          后台管理页面
─────────────────────────────────────────────────
/                               /admin
├── /courses                    ├── /admin/courses
│   ├── /:slug                  │   ├── /:id/edit
│   │   └── /learn              │   └── /:id/chapters
│   └── /category/:category     │
└── /my-courses
```

### 4.2 首页课程卡片

**位置：** Hero 组件顶部 Banner 区域

**设计要点：**
- 保持现有 OpenSpecCourseCard 风格
- 紫色渐变背景
- 显示课程标题、描述、特性标签
- 显示学习进度（针对已报名用户）
- CTA 按钮：未报名显示"开始学习"，已报名显示"继续学习"

### 4.3 课程列表页 (`/courses`)

**布局：** 左侧筛选 + 右侧卡片网格

**筛选条件：**
- 课程分类（树形结构）
- 评分（4.0+、4.5+）
- 价格（免费、付费）
- 难度（入门、进阶、高级）
- 时长（<5 小时、5-10 小时、>10 小时）

**排序选项：**
- 🔥 热门（综合评分）
- 💎 推荐（编辑精选）
- 🆕 最新（发布时间）
- ⭐ 高评分

**卡片信息：**
- 封面图
- 课程标题（最多 2 行，超出省略）
- 课程描述（1 行，超出省略）
- 评分（星级 + 评价数）
- 讲师名称
- 统计数据：❤️ 点赞 | 👁 观看 | 📚 章节数
- CTA 按钮：立即学习

### 4.4 课程详情页 (`/courses/:slug`)

**页面结构：**
```
┌─────────────────────────────────────────────────┐
│  [封面图 Banner]                                 │
│  课程标题                                        │
│  课程描述                                        │
│  [评分] [讲师] [统计]                           │
│  [立即学习] [收藏] [分享]                       │
├─────────────────────────────────────────────────┤
│  Tab 导航：课程介绍 | 章节列表 | 评价 | 讲师    │
│  ─────────────────────────────────────────────  │
│  [Tab 内容区]                                    │
└─────────────────────────────────────────────────┘
```

### 4.5 课程学习页 (`/courses/:slug/learn`)

**复用现有 OpenSpecCourse 组件**

**需要调整：**
- 从单课程扩展为多课程支持
- 左侧章节导航支持多课程
- 学习进度追踪关联 course_id

### 4.6 后台课程管理 (`/admin/course`)

**Tab 结构：**
```
[课程列表] [章节管理] [测验管理] [资源管理] [统计]
```

**课程列表页：**
- 表格展示：封面、标题、分类、状态、统计数据、操作
- 支持筛选：状态、分类
- 支持搜索：标题、slug

**课程编辑器：**
- 基本信息编辑（标题、slug、分类、封面）
- 富文本编辑器（TipTap）描述
- OSS 上传集成（封面图、资源文件）
- 章节管理（拖拽排序、CRUD）
- 测验管理
- 资源管理

---

## 5. 技术选型

### 5.1 后端

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | FastAPI | 现有 |
| ORM | SQLAlchemy | 现有 |
| 数据库迁移 | Alembic | 新增 |
| 数据验证 | Pydantic | 现有 |

### 5.2 前端

| 组件 | 技术 | 说明 |
|------|------|------|
| 富文本编辑器 | TipTap | 现代、支持 Markdown 混合 |
| Markdown 渲染 | react-markdown | 课程详情/章节内容 |
| 代码高亮 | Prism.js / highlight.js | 代码块渲染 |
| 文件上传 | react-dropzone | OSS 上传 |
| 状态管理 | Zustand | 现有 |

### 5.3 OSS 集成

- 复用现有 oss2 SDK
- 新增课程资源目录：`courses/{course_id}/{chapter_id}/`

---

## 6. 数据迁移计划

### 6.1 阶段一：导出数据

```python
# 1. 导出当前 OpenSpec 课程内容
from app.models.openspec_course import CourseChapter, CourseQuiz, CourseResource

exported_data = {
    "course": {
        "title": "OpenSpec VibeCoding 课程",
        "slug": "openspec-vibecoding",
        "description": "从 AI 小白到 Spec 高手的进阶之路 | 故事驱动 × 互动学习 × 实战练习",
    },
    "chapters": []
}

for chapter in CourseChapter.query.order_by(CourseChapter.order).all():
    chapter_data = {
        "slug": chapter.slug,
        "title": chapter.title,
        "order": chapter.order,
        "content": chapter.content,
        "chapter_type": chapter.chapter_type,
        "video_url": chapter.video_url,
        "is_locked": chapter.is_locked,
    }
    # 导出关联的测验和资源
    # ...
    exported_data["chapters"].append(chapter_data)
```

### 6.2 阶段二：创建新数据

```python
# 2. 创建课程记录
course = Course(
    title="OpenSpec VibeCoding 课程",
    slug="openspec-vibecoding",
    description="从 AI 小白到 Spec 高手的进阶之路",
    cover_image="/images/courses/openspec-vibecoding.jpg",
    category_id=1,  # 编程分类
    status="published"
)
db.add(course)
db.commit()

# 3. 迁移章节
for chapter_data in exported_data["chapters"]:
    chapter = CourseChapter(
        course_id=course.id,
        **chapter_data
    )
    db.add(chapter)

# 4. 初始化统计数据
statistics = CourseStatistics(
    course_id=course.id,
    view_count=0,
    enroll_count=0,
    like_count=0,
    bookmark_count=0,
    review_count=0,
    avg_rating=0,
    completed_count=0
)
db.add(statistics)
db.commit()
```

### 6.3 阶段三：验证和清理

```python
# 验证数据完整性
# 1. 检查章节数量
# 2. 检查测验数据
# 3. 检查资源数据
# 4. 前端访问验证
```

---

## 7. 实现任务清单

### Phase 1: 数据库和模型 (4 任务)

- [ ] 1.1 创建数据库迁移脚本（新增 12 张表）
- [ ] 1.2 创建 SQLAlchemy 模型类
- [ ] 1.3 创建 Pydantic Schemas
- [ ] 1.4 编写数据迁移脚本（导出 → 导入）

### Phase 2: 后端 API (8 任务)

- [ ] 2.1 课程列表 API（含筛选/分页）
- [ ] 2.2 课程详情 API
- [ ] 2.3 课程分类 API
- [ ] 2.4 用户课程 API（报名/我的课程）
- [ ] 2.5 互动统计 API（点赞/收藏/浏览）
- [ ] 2.6 课程评价 API
- [ ] 2.7 课程管理 API（CRUD）
- [ ] 2.8 统计数据更新逻辑

### Phase 3: 前端页面 (8 任务)

- [ ] 3.1 课程列表页 `/courses`
- [ ] 3.2 课程详情页 `/courses/:slug`
- [ ] 3.3 课程学习页（复用扩展现有）
- [ ] 3.4 课程卡片组件
- [ ] 3.5 课程筛选侧边栏
- [ ] 3.6 首页课程入口卡片更新
- [ ] 3.7 我的课程页
- [ ] 3.8 课程评价组件

### Phase 4: 后台管理 (6 任务)

- [ ] 4.1 课程管理首页（列表/筛选）
- [ ] 4.2 课程编辑器（基本信息 + 封面上传）
- [ ] 4.3 富文本编辑器集成（TipTap + Markdown + 预览）
- [ ] 4.4 OSS 上传集成（图片/视频）
- [ ] 4.5 章节管理（复用现有组件）
- [ ] 4.6 统计数据展示

### Phase 5: 集成和测试 (4 任务)

- [ ] 5.1 数据迁移验证
- [ ] 5.2 API 集成测试
- [ ] 5.3 前端功能测试
- [ ] 5.4 浏览器兼容性测试

---

## 8. 成功标准

### 8.1 功能完整性

- ✅ 用户可以浏览课程列表
- ✅ 用户可以查看课程详情
- ✅ 用户可以报名课程并开始学习
- ✅ 用户可以点赞、收藏课程
- ✅ 用户可以提交评价
- ✅ 管理员可以创建/编辑/删除课程
- ✅ 管理员可以管理章节、测验、资源
- ✅ 支持富文本编辑和 OSS 上传

### 8.2 数据完整性

- ✅ 现有 OpenSpec VibeCoding 课程内容完整迁移
- ✅ 所有统计数据准确记录
- ✅ 用户学习进度不丢失

### 8.3 用户体验

- ✅ 页面加载流畅（<3 秒）
- ✅ 与现有页面风格一致
- ✅ 移动端响应式布局
- ✅ 无控制台错误

---

## 9. 风险和挑战

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据迁移失败 | 高 | 编写回滚脚本，备份原数据 |
| TipTap 集成复杂 | 中 | 预留足够时间，参考官方文档 |
| OSS 上传性能 | 中 | 使用分片上传，限制文件大小 |
| 统计数据一致性 | 中 | 使用事务，定期校验 |

---

## 10. 未来扩展

### 10.1 短期（下一阶段）

- 课程证书系统
- 学习成就/徽章
- 课程推荐算法

### 10.2 长期

- 讲师入驻系统
- 付费课程支持
- 课程讨论区
- 直播课程
- 学习小组

---

**设计批准:** 已批准
**下一步:** 调用 writing-plans 创建详细实现计划
