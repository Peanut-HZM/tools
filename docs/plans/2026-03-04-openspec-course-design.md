# OpenSpec VibeCoding 互动课程设计文档

**创建日期:** 2026-03-04
**更新日期:** 2026-03-08
**作者:** VibeCoding 推广团队
**版本:** 3.0 - 与实际实现对齐

---

## 项目概述

### 目标
通过故事驱动的互动方式，让公司同事快速掌握 OpenSpec 编程，理解 VibeCoding 和 SpecCoding 的最佳实践。

### 课程定位
- **主题:** OpenSpec 入门和深入使用，以及与 spec-kit 的区别对比
- **形式:** 网页 + 视频的混合式互动课程
- **风格:** 生动、幽默、富有互动性
- **入口:** 在工具箱首页增加醒目的课程入口卡片

### 实际实现架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenSpec 课程系统架构                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  前端 (React)                    后端 (FastAPI)                  │
│  ──────────                      ────────────                   │
│                                                                 │
│  /tools/openspec-course    →     /api/openspec-course           │
│                                                                 │
│  组件：                          路由：                          │
│  • OpenSpecCourse.tsx           • openspec_course.py            │
│  • ChapterNavigation.tsx        • course_platform.py            │
│  • ChapterContent.tsx           • course_platform_admin.py      │
│  • QuizView.tsx                                                     │
│  • SpecEditor.tsx               服务：                          │
│  • ProgressBar.tsx              • openspec_course_service.py    │
│  • OpenSpecCourseCard.tsx                                           │
│                                                                 │
│  数据库 (SQLite - pm_agent.db)                                   │
│  ─────────────────────────────                                   │
│  • course_chapters (章节表)                                      │
│  • course_quizzes (测验表)                                       │
│  • course_quiz_questions (题目表)                                 │
│  • course_quiz_options (选项表)                                   │
│  • course_resources (资源表)                                     │
│  • course_enrollments (报名表的)                                  │
│  • course_progress (学习进度表)                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 核心理念
本课程不仅要教会用户如何使用 OpenSpec，更要传达一种**渐进式 AI 协作**的思维方式：

1. **初级阶段：** 详细指令，明确沟通 - 告诉 AI 每个细节
2. **中级阶段：** 使用 Rules，规范行为 - 建立协作默契
3. **高级阶段：** Spec 驱动，自主判断 - AI 自主理解上下文

### 学习路径设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenSpec 学习路径                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  第一阶段          第二阶段          第三阶段          第四阶段   │
│  ──────          ──────          ──────          ──────       │
│                                                                 │
│  🤔             📋             🚀             ⚡              │
│  谨慎使用        发现规则        进阶工具        自主判断        │
│  AI 小白          Rules 拯救       OpenSpec       高手阶段        │
│                                                                 │
│  • 详细指令       • 建立规范       • Spec 驱动      • 上下文理解   │
│  • 复制代码       • 约束行为       • 技能包         • 自主判断     │
│  • 反复确认       • 质量提升       • 效率提升       • 最小沟通     │
│                                                                 │
│  ↓                ↓                ↓                ↓           │
│                                                                 │
│  沟通成本：高      沟通成本：中      沟通成本：低      沟通成本：极低  │
│  AI 准确率：60%    AI 准确率：80%    AI 准确率：90%    AI 准确率：95%+ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 课程章节结构（实际实现）

### 章节类型定义

系统支持 5 种章节类型，通过 `chapter_type` 字段区分：

| 类型 | chapter_type | 用途 | 示例 |
|------|-------------|------|------|
| **story** | `story` | 故事驱动，引入场景 | "最初的我 - 谨慎使用 AI" |
| **lesson** | `lesson` | 课程内容，知识点讲解 | "详细沟通的必要性" |
| **quiz-only** | `quiz-only` | 纯测验章节 | "阶段测试" |
| **code** | `code` | 代码实战 | "实战 Spec 编辑" |
| **video** | `video` | 视频教学 | "视频讲解" |

### 实际课程内容（已实现）

课程共 5 个主章节：

```
第一章：📖 "最初的我" - 谨慎使用 AI (story)
  ├── 1.1 故事引入
  ├── 1.2 详细沟通的必要性
  ├── 1.3 前端修改沟通模板
  ├── 1.4 后端接口沟通模板
  └── 1.5 完整示例

第二章：🤯 "遇到问题" - AI 乱改代码的困扰 (story)
  ├── 2.1 AI 乱改代码的场景
  └── 2.2 对比演示

第三章：🎉 "发现规则" - rules 的拯救 (lesson)
  ├── 3.1 Rules 介绍
  └── 3.2 对比演示

第四章：🚀 "进阶工具" - OpenSpec & Superpowers (lesson)
  ├── 4.1 OpenSpec 是什么
  ├── 4.2 OpenSpec 技能详解
  └── 4.3 Spec 文件示例

第五章：⚖️ "对比思考" - 工具对比与最佳实践 (lesson)
  ├── 5.1 三大工具对比
  ├── 5.2 决策树
  └── 5.3 互动测验
```

---

## 技术架构（实际实现）

### 前端架构

**技术栈:**
- React 18 + TypeScript
- Tailwind CSS
- React Router DOM
- ReactMarkdown (Markdown 渲染)
- react-syntax-highlighter (代码高亮)
- Axios (HTTP 请求)

**目录结构:**
```
frontend/src/
├── components/
│   └── Tools/
│       ├── OpenSpecCourse.tsx              # 主页面组件
│       ├── OpenSpecCourse/
│       │   ├── OpenSpecCourseCard.tsx      # 首页入口卡片
│       │   ├── ChapterNavigation.tsx       # 章节导航（左侧）
│       │   ├── ChapterContent.tsx          # 章节内容展示
│       │   ├── QuizView.tsx                # 测验界面
│       │   ├── SpecEditor.tsx              # Spec 编辑器
│       │   └── ProgressBar.tsx             # 进度条组件
│       └── ...
├── services/
│   └── openspecCourse.ts                   # API 服务层
└── types/
```

**组件职责:**

| 组件 | 职责 |
|------|------|
| `OpenSpecCourse.tsx` | 主页面，管理章节加载、进度追踪、路由控制 |
| `OpenSpecCourseCard.tsx` | 首页入口卡片，展示课程信息和进度 |
| `ChapterNavigation.tsx` | 左侧章节列表导航，显示锁章状态 |
| `ChapterContent.tsx` | 章节内容渲染，支持 Markdown、代码高亮、视频嵌入 |
| `QuizView.tsx` | 测验界面，支持单选/多选、即时反馈、答案解析 |
| `SpecEditor.tsx` | Spec 编辑器，在线尝试写 Spec |
| `ProgressBar.tsx` | 学习进度展示 |

### 后端架构

**技术栈:**
- FastAPI (Python 3.10+)
- SQLAlchemy (ORM)
- Pydantic (数据验证)
- SQLite/PostgreSQL

**目录结构:**
```
backend/app/
├── models/
│   ├── openspec_course.py     # 课程数据模型定义
│   └── course_platform.py     # 通用课程平台模型
├── schemas/
│   ├── openspec_course.py     # Pydantic Schemas
│   └── course_platform.py     # 通用课程平台 Schemas
├── routes/
│   ├── openspec_course.py     # OpenSpec 课程 API
│   ├── course_platform.py     # 通用课程平台 API
│   └── course_platform_admin.py  # 管理端 API
└── services/
    └── openspec_course_service.py  # 业务逻辑层
```

**API 接口:**

```
# 章节管理
GET    /api/openspec-course/chapters              # 获取所有章节
GET    /api/openspec-course/chapters/{id}         # 获取章节详情
POST   /api/openspec-course/chapters              # 创建章节 (Admin)
PUT    /api/openspec-course/chapters/{id}         # 更新章节 (Admin)
DELETE /api/openspec-course/chapters/{id}         # 删除章节 (Admin)
PUT    /api/openspec-course/chapters/reorder      # 批量更新顺序 (Admin)

# 测验管理
GET    /api/openspec-course/quizzes/{chapter_id}  # 获取章节测验
POST   /api/openspec-course/quizzes/{quiz_id}/submit  # 提交测验
POST   /api/openspec-course/quizzes               # 创建测验 (Admin)
PUT    /api/openspec-course/quizzes/{quiz_id}     # 更新测验 (Admin)
DELETE /api/openspec-course/quizzes/{quiz_id}     # 删除测验 (Admin)

# 进度管理
GET    /api/openspec-course/progress              # 获取用户进度
GET    /api/openspec-course/progress/chapter/{id} # 获取章节进度
PUT    /api/openspec-course/progress/chapter/{id} # 更新进度

# 资源管理
GET    /api/openspec-course/resources/chapter/{id} # 获取章节资源
GET    /api/openspec-course/resources/{id}         # 获取资源详情
POST   /api/openspec-course/resources              # 创建资源 (Admin)
PUT    /api/openspec-course/resources/{id}         # 更新资源 (Admin)
DELETE /api/openspec-course/resources/{id}         # 删除资源 (Admin)
```

### 数据库设计（实际实现）

**数据库:** SQLite (`backend/pm_agent.db`)

**核心表结构:**

```sql
-- 课程章节表
CREATE TABLE course_chapters (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- 章节标识符（用于 URL）
    title VARCHAR(200) NOT NULL,        -- 章节标题
    "order" INTEGER DEFAULT 0,          -- 章节顺序
    content TEXT NOT NULL,              -- 章节内容（Markdown）
    chapter_type VARCHAR(50) DEFAULT 'story',  -- story/lesson/quiz-only/code/video
    video_url VARCHAR(500),             -- 视频链接
    is_locked BOOLEAN DEFAULT 0,        -- 是否锁定
    duration_minutes INTEGER DEFAULT 0, -- 学习时长（分钟）
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- 课程测验表
CREATE TABLE course_quizzes (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    passing_score INTEGER DEFAULT 60,  -- 及格分数 (0-100)
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(chapter_id) REFERENCES course_chapters(id) ON DELETE CASCADE
);

-- 测验题目表
CREATE TABLE course_quiz_questions (
    id INTEGER PRIMARY KEY,
    quiz_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'single',  -- single/multiple
    correct_answer VARCHAR(100) NOT NULL,  -- 逗号分隔的选项索引
    explanation TEXT,  -- 答案解析
    "order" INTEGER DEFAULT 0,
    created_at DATETIME,
    FOREIGN KEY(quiz_id) REFERENCES course_quizzes(id) ON DELETE CASCADE
);

-- 测验选项表
CREATE TABLE course_quiz_options (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    option_index INTEGER NOT NULL,  -- 0=A, 1=B, 2=C, 3=D
    created_at DATETIME,
    FOREIGN KEY(question_id) REFERENCES course_quiz_questions(id) ON DELETE CASCADE
);

-- 课程资源表
CREATE TABLE course_resources (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL,
    resource_type VARCHAR(50) NOT NULL,  -- code/contrast/video/template
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    extra_data JSON,  -- 额外元数据
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(chapter_id) REFERENCES course_chapters(id) ON DELETE CASCADE
);

-- 学习进度表
CREATE TABLE course_progress (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    chapter_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'not_started',  -- not_started/in_progress/completed
    quiz_score FLOAT,  -- 测验分数 (0-100)
    quiz_passed BOOLEAN DEFAULT 0,
    completed_at DATETIME,
    video_progress INTEGER DEFAULT 0,  -- 视频进度（秒）
    created_at DATETIME,
    updated_at DATETIME,
    UNIQUE(user_id, chapter_id),
    FOREIGN KEY(chapter_id) REFERENCES course_chapters(id) ON DELETE CASCADE
);
```

---

## 数据模型（Pydantic Schemas）

### 章节相关 Schema

```python
class ChapterBase(BaseModel):
    slug: str  # 章节标识符（唯一，用于 URL）
    title: str  # 章节标题
    order: int  # 章节顺序
    content: str  # 章节内容（Markdown）
    chapter_type: str  # story/lesson/quiz-only/code/video
    video_url: Optional[str]
    is_locked: bool
    required_quiz_id: Optional[int]

class ChapterResponse(ChapterBase):
    id: int
    created_at: datetime
    updated_at: datetime

class ChapterDetailResponse(ChapterResponse):
    quiz: Optional[QuizResponse]
    resources: List[ResourceResponse]
    user_progress: Optional[UserProgressResponse]
```

### 测验相关 Schema

```python
class QuizOptionResponse(BaseModel):
    id: int
    option_text: str
    option_index: int  # 0=A, 1=B...

class QuizQuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str  # single/multiple
    correct_answer: str  # 逗号分隔
    explanation: Optional[str]
    options: List[QuizOptionResponse]

class QuizResponse(BaseModel):
    id: int
    chapter_id: int
    title: str
    passing_score: int
    questions: List[QuizQuestionResponse]

class QuizResult(BaseModel):
    quiz_id: int
    total_questions: int
    correct_count: int
    score: float
    passed: bool
    details: List[Dict[str, Any]]
```

### 进度相关 Schema

```python
class UserProgressResponse(BaseModel):
    id: Optional[int]
    user_id: str
    chapter_id: int
    status: str  # not_started/in_progress/completed
    quiz_score: Optional[float]
    quiz_passed: bool
    completed_at: Optional[datetime]
    video_progress: int

class CourseProgressSummary(BaseModel):
    total_chapters: int
    completed_chapters: int
    progress_percentage: float
    chapters: List[UserProgressResponse]
```

---

## 前端组件详细设计

### OpenSpecCourse 主组件

**职责:**
- 加载章节列表和进度
- 管理当前选中的章节
- 处理测验完成后的进度更新
- 控制子组件显示（内容/测验/编辑器）

**状态管理:**
```typescript
const [chapters, setChapters] = useState<Chapter[]>([]);
const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null);
const [currentChapterId, setCurrentChapterId] = useState<number | null>(null);
const [progress, setProgress] = useState<UserProgress[]>([]);
const [showQuiz, setShowQuiz] = useState(false);
const [showSpecEditor, setShowSpecEditor] = useState(false);
```

### ChapterNavigation 组件

**功能:**
- 左侧章节列表展示
- 锁章状态显示（🔒 图标）
- 完成状态显示（✅ 图标）
- 点击切换章节

**视觉设计:**
```
┌─────────────────────────┐
│ 📖 第一章：最初的我      │ ← 当前章节（高亮）
│ ✅ 已完成               │
├─────────────────────────┤
│ 📖 第二章：遇到问题      │ ← 已完成
│ ✅ 已完成               │
├─────────────────────────┤
│ 📖 第三章：发现规则      │ ← 进行中
│ 🔄 进行中               │
├─────────────────────────┤
│ 🔒 第四章：进阶工具      │ ← 锁定
│ 需要通过第三章测验       │
└─────────────────────────┘
```

### ChapterContent 组件

**功能:**
- Markdown 内容渲染（ReactMarkdown）
- 代码高亮（react-syntax-highlighter）
- 视频嵌入（如果有 video_url）
- 资源列表展示
- 操作按钮（下一章、开始测验、打开编辑器）

**Markdown 自定义样式:**
```typescript
components={{
  h1: ({node, ...props}) => <h1 className="text-3xl font-bold text-white mb-4" {...props} />,
  h2: ({node, ...props}) => <h2 className="text-2xl font-bold text-white mb-3" {...props} />,
  p: ({node, ...props}) => <p className="text-white/80 leading-relaxed mb-4" {...props} />,
  code: ({node, inline, ...props}) => { /* 代码高亮 */ },
  // ... 其他自定义样式
}}
```

### QuizView 组件

**功能:**
- 测验题目展示
- 单选/多选支持
- 即时判题反馈
- 答案解析展示
- 重试机制

**交互流程:**
```
1. 用户选择答案 → 2. 提交答案 → 3. 显示结果
                                    │
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
               通过 ✅                          失败 ❌
                    │                               │
                    ↓                               ↓
               更新进度为完成                   显示重试按钮
               解锁下一章                       允许重新答题
```

---

## 服务层实现

### openspecCourse.ts API 服务

```typescript
// 获取所有章节列表
export const getChapters = async (): Promise<Chapter[]> => {
  const response = await axios.get(`${API_BASE_URL}/chapters`);
  return response.data.chapters;
};

// 获取章节详情（包含测验、资源、进度）
export const getChapterDetail = async (chapterId: number): Promise<ChapterDetail> => {
  const response = await axios.get(`${API_BASE_URL}/chapters/${chapterId}`);
  return response.data;
};

// 提交测验答案
export const submitQuiz = async (
  quizId: number,
  answers: Record<number, number[]>
): Promise<QuizResult> => {
  const response = await axios.post(`${API_BASE_URL}/quizzes/${quizId}/submit`, {
    answers,
  });
  return response.data;
};

// 获取用户进度汇总
export const getCourseProgress = async (): Promise<CourseProgressSummary> => {
  const response = await axios.get(`${API_BASE_URL}/progress`);
  return response.data;
};

// 更新章节进度
export const updateChapterProgress = async (
  chapterId: number,
  data: Partial<UserProgress>
): Promise<UserProgress> => {
  const response = await axios.put(`${API_BASE_URL}/progress/chapter/${chapterId}`, data);
  return response.data;
};
```

### openspec_course_service.py 业务逻辑

**核心方法:**

```python
class OpenSpecCourseService:
    def __init__(self, db: Session):
        self.db = db

    # 章节管理
    def get_chapters(self) -> List[OpenSpecCourseChapter]
    def get_chapter_by_id(self, chapter_id: int) -> Optional[...]
    def get_chapter_by_slug(self, slug: str) -> Optional[...]
    def create_chapter(self, chapter: ChapterCreate) -> OpenSpecCourseChapter
    def update_chapter(self, chapter_id: int, chapter: ChapterUpdate) -> Optional[...]
    def delete_chapter(self, chapter_id: int) -> bool
    def reorder_chapters(self, request: ChapterReorderRequest) -> bool

    # 测验管理
    def get_quiz_by_chapter_id(self, chapter_id: int) -> Optional[OpenSpecCourseQuiz]
    def get_quiz_questions(self, quiz_id: int) -> List[Dict]
    def create_quiz(self, quiz: QuizCreate) -> OpenSpecCourseQuiz
    def submit_quiz(self, quiz_id: int, user_id: str, answers: Dict) -> QuizResult

    # 进度管理
    def get_user_progress(self, user_id: str, chapter_id: int) -> Optional[...]
    def create_or_update_progress(self, user_id: str, chapter_id: int, progress: UserProgressUpdate) -> [...]
    def get_course_progress_summary(self, user_id: str) -> Dict[str, Any]

    # 资源管理
    def get_resources_by_chapter_id(self, chapter_id: int) -> List[...]
    def create_resource(self, resource: ResourceCreate) -> OpenSpecCourseResource
```

---

## 用户学习流程

### 完整学习路径

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户学习流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 首页入口 → 2. 课程主页 → 3. 选择章节 → 4. 学习内容          │
│      │            │             │             │                │
│      │            │             │             │                │
│      ▼            ▼             ▼             ▼                │
│  ┌────────┐  ┌────────┐   ┌────────┐   ┌────────┐            │
│  │ 课程   │  │ 显示   │   │ 左侧   │   │ 阅读   │            │
│  │ 卡片   │→ │ 章节   │→ │ 导航   │→ │ 内容   │            │
│  │        │  │ 列表   │   │ 列表   │   │        │            │
│  └────────┘  └────────┘   └────────┘   └────────┘            │
│                                           │                    │
│                                           ▼                    │
│                                    ┌────────────┐              │
│                                    │ 完成测验？ │              │
│                                    └─────┬──────┘              │
│                                          │                      │
│                    ┌─────────────────────┼─────────────────┐   │
│                    │                     │                 │   │
│                    ▼                     ▼                 │   │
│               ┌────────┐          ┌────────────┐          │   │
│               │ 是     │          │ 否         │          │   │
│               │ 提交   │          │ 继续下一章 │          │   │
│               │ 测验   │          │            │          │   │
│               └───┬────┘          └────────────┘          │   │
│                   │                                         │   │
│                   ▼                                         │   │
│            ┌──────────────┐                                │   │
│            │  通过？      │                                │   │
│            └───┬──────┬───┘                                │   │
│                │      │                                     │   │
│         通过 ✅│      │❌ 失败                               │   │
│                │      │                                     │   │
│                ▼      ▼                                     │   │
│           ┌────────┐ ┌────────┐                             │   │
│           │ 更新   │ │ 重试   │                             │   │
│           │ 进度   │ │ 测验   │                             │   │
│           └────────┘ └────────┘                             │   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 锁章机制

```
章节锁定逻辑：
1. is_locked = true 的章节，用户无法访问
2. required_quiz_id 指向的测验通过后，章节解锁
3. 用户完成前一章后，下一章自动解锁（可选配置）

解锁流程：
┌─────────────┐
│ 用户访问章节 │
└──────┬──────┘
       │
       ▼
┌─────────────┐     是     ┌─────────────┐
│ is_locked?  │ ──────────→│ 拒绝访问    │
└──────┬──────┘           └─────────────┘
       │ 否
       ▼
┌─────────────────┐
│ required_quiz?  │
└──────┬──────────┘
       │
   ┌───┴───┐
   │       │
   是      否
   │       │
   ▼       ▼
┌─────┐ ┌───────┐
│ 检查 │ │ 允许  │
│ 通过 │ │ 访问  │
└──┬──┘ └───────┘
   │
┌──┴──┐
│通过？│
└──┬──┘
   │
┌──┴──┐    ┌───────┐    ┌───────┐
│ 是  │    │  否   │    │ 未考  │
└──┬──┘    └───┬───┘    └───┬───┘
   │          │            │
   ▼          ▼            ▼
┌──────┐  ┌──────────┐ ┌────────┐
│ 允许 │  │ 提示去考 │  │ 提示去 │
│ 访问 │  │ 前一章   │  │ 考试   │
└──────┘  └──────────┘ └────────┘
```

---

## 数据初始化

### 初始化脚本位置

数据库初始化脚本位于 `backend/app/db/init_db_tool.sql`，但当前课程数据需要手动插入。

### 初始化数据示例

```sql
-- 插入示例章节数据
INSERT INTO course_chapters (course_id, slug, title, "order", content, chapter_type, video_url, is_locked, duration_minutes)
VALUES
(1, 'intro-ai-beginner', '第一章：最初的我 - 谨慎使用 AI', 0,
 '# 第一章：最初的我 - 谨慎使用 AI\n\n刚开始使用 AI 编程时的谨慎心态...',
 'story', NULL, 0, 15),

(1, 'encounter-problems', '第二章：遇到问题 - AI 乱改代码', 1,
 '# 第二章：遇到问题 - AI 乱改代码的困扰\n\nAI 经常乱改代码，超出修改范围...',
 'story', NULL, 0, 15),

(1, 'discover-rules', '第三章：发现规则 - rules 的拯救', 2,
 '# 第三章：发现规则 - rules 的拯救\n\n发现可以使用 rules 规范开发...',
 'lesson', NULL, 0, 20),

(1, 'advanced-tools', '第四章：进阶工具 - OpenSpec', 3,
 '# 第四章：进阶工具 - OpenSpec & Superpowers\n\nOpenSpec 是一个基于 Spec 的开发方法论...',
 'lesson', NULL, 1, 25),  -- is_locked=1，需要解锁

(1, 'comparison', '第五章：对比思考 - 工具对比', 4,
 '# 第五章：对比思考 - 工具对比与最佳实践\n\n理解 OpenSpec、spec-kit、superpowers 的定位差异...',
 'lesson', NULL, 1, 20);  -- is_locked=1，需要解锁
```

---

## 部署配置

### 前端部署

```bash
# 安装依赖
cd frontend
npm install

# 开发模式
npm run dev  # 启动于 http://localhost:5178

# 生产构建
npm run build
npm run preview
```

### 后端部署

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --port 19092

# 生产环境
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:19092
```

### CORS 配置

后端已配置 CORS，允许前端访问：

```python
# backend/app/config/config.py
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5178")
```

---

## 视频制作指南

### 视频结构建议

根据实际实现的课程内容，建议视频结构如下：

#### 第一部分：课程介绍（2-3 分钟）

**内容:**
- 课程目标：从 AI 小白到 Spec 高手
- 学习形式：故事驱动 + 互动测验
- 课程特色：实战编辑、视频讲解、锁章机制

**画面:**
- 首页课程入口卡片展示
- 课程主页整体布局
- 学习路径图

#### 第二部分：第一阶段 - 谨慎使用 AI（5-8 分钟）

**内容:**
- 故事引入：刚开始使用 AI 的心态
- 详细沟通模板演示
- 前端/后端修改沟通示例

**画面:**
- 第一章内容滚动展示
- 代码示例高亮显示
- 沟通模板表格展示

#### 第三部分：第二阶段 - 遇到问题（3-5 分钟）

**内容:**
- AI 乱改代码的场景
- 对比演示：期望 vs 实际

**画面:**
- 错误示例代码
- 对比视图

#### 第四部分：第三阶段 - Rules 拯救（5-8 分钟）

**内容:**
- Rules 介绍
- Rules 配置示例
- 效果对比

**画面:**
- Rules 文件内容
- 有/无 Rules 对比

#### 第五部分：第四阶段 - OpenSpec（10-15 分钟）

**内容:**
- OpenSpec 技能系统介绍
- 每个技能的用途
- Spec 文件示例

**画面:**
- 技能列表
- openspec-new-change 演示
- openspec-explore 对话示例
- Spec 编辑器演示

#### 第六部分：第五阶段 - 工具对比（5-8 分钟）

**内容:**
- OpenSpec vs spec-kit vs Superpowers
- 决策树
- 最佳实践

**画面:**
- 对比表格
- 决策树流程图
- 互动测验演示

### 录屏建议

1. **首页入口:** 展示课程卡片的动画效果和"开始学习"按钮
2. **章节导航:** 展示左侧章节列表、锁章状态、进度显示
3. **内容浏览:** 滚动展示 Markdown 内容、代码高亮
4. **互动测验:** 演示答题、提交、判题、解析全流程
5. **Spec 编辑器:** 演示在线编辑 Spec

---

## 后续迭代

- [ ] 支持用户评论和讨论
- [ ] 添加学习排行榜
- [ ] 支持课程证书生成
- [ ] 多语言支持
- [ ] 更多互动游戏化元素

---

## 附录：当前实现状态

### 已实现功能 ✅

| 功能 | 状态 |
|------|------|
| 章节列表展示 | ✅ 已实现 |
| 章节内容渲染（Markdown） | ✅ 已实现 |
| 代码高亮 | ✅ 已实现 |
| 章节导航 | ✅ 已实现 |
| 学习进度追踪 | ✅ 已实现 |
| 测验系统 | ✅ 已实现 |
| 锁章机制 | ✅ 已实现（基础） |
| 进度条组件 | ✅ 已实现 |
| Spec 编辑器 | ✅ 已实现（基础） |
| 首页入口卡片 | ✅ 已实现 |

### 待实现功能 🚧

| 功能 | 状态 |
|------|------|
| 视频嵌入播放 | 🚧 框架已实现，待填充视频 |
| 资源管理 | 🚧 API 已实现，待前端集成 |
| 完整锁章逻辑 | 🚧 基础已实现，待完善 |
| 互动游戏化元素 | 🚧 待实现 |

---

**文档版本:** 3.0
**最后更新:** 2026-03-08
**更新内容:** 根据实际实现调整，包括数据库结构、API 接口、前端组件、章节内容
