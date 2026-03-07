# 课程学习平台实现计划

**基于设计文档:** docs/plans/2026-03-07-course-platform-design.md
**创建日期:** 2026-03-07
**预计工作量:** 30 个任务，分 5 个阶段

---

## 阶段 1: 数据库和模型 (预计 2-3 小时)

### 任务 1.1: 创建数据库迁移脚本

**文件:** `backend/alembic/versions/xxxx_add_course_platform_tables.py`

**工作内容:**
1. 创建 12 张新表的迁移脚本
2. 表列表：
   - courses (课程主表)
   - course_categories (课程分类)
   - course_chapters (课程章节)
   - course_quizzes (课程测验)
   - course_quiz_questions (测验题目)
   - course_quiz_options (测验选项)
   - course_resources (课程资源)
   - course_enrollments (用户课程关联)
   - course_progress (学习进度)
   - course_interactions (课程互动)
   - course_reviews (课程评价)
   - course_statistics (课程统计)

**验收标准:**
- [ ] 迁移脚本能成功执行
- [ ] 所有表结构正确创建
- [ ] 外键约束正确设置
- [ ] 索引正确创建

---

### 任务 1.2: 创建 SQLAlchemy 模型类

**文件:** `backend/app/models/course_platform.py`

**工作内容:**
1. 为 12 张表创建 SQLAlchemy 模型
2. 定义表关系（relationship）
3. 添加常用查询方法

**模型列表:**
- Course
- CourseCategory
- CourseChapter
- CourseQuiz
- CourseQuizQuestion
- CourseQuizOption
- CourseResource
- CourseEnrollment
- CourseProgress
- CourseInteraction
- CourseReview
- CourseStatistics

**验收标准:**
- [ ] 所有模型类正确定义
- [ ] 表关系正确配置
- [ ] 能正常进行 CRUD 操作

---

### 任务 1.3: 创建 Pydantic Schemas

**文件:** `backend/app/schemas/course_platform.py`

**工作内容:**
1. 为每个模型创建 Base、Create、Update、Response  schema
2. 添加字段验证器
3. 处理嵌套响应（如课程详情包含章节列表）

**Schema 示例:**
```python
class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str
    cover_image: Optional[str] = None
    category_id: Optional[int] = None
    price: Decimal = Field(default=0, ge=0)
    status: str = Field(default="draft")

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int
    statistics: Optional[CourseStatisticsResponse] = None
    chapters: List[CourseChapterResponse] = []

    class Config:
        from_attributes = True
```

**验收标准:**
- [ ] 所有 Schema 正确定义
- [ ] 验证逻辑正确
- [ ] 支持嵌套响应

---

### 任务 1.4: 编写数据迁移脚本

**文件:** `backend/scripts/migrate_openspec_course.py`

**工作内容:**
1. 导出当前 OpenSpec VibeCoding 课程数据
2. 导入到新创建的表中
3. 初始化统计数据
4. 验证数据完整性

**迁移步骤:**
```python
# 1. 读取旧表数据
chapters = session.query(CourseChapter).all()

# 2. 创建新课程
course = Course(
    title="OpenSpec VibeCoding 课程",
    slug="openspec-vibecoding",
    ...
)

# 3. 迁移章节
for old_chapter in chapters:
    new_chapter = CourseChapter(
        course_id=course.id,
        title=old_chapter.title,
        content=old_chapter.content,
        ...
    )

# 4. 初始化统计
statistics = CourseStatistics(course_id=course.id)
```

**验收标准:**
- [ ] 脚本执行无错误
- [ ] 5 个章节完整迁移
- [ ] 测验数据完整迁移
- [ ] 资源数据完整迁移
- [ ] 统计数据初始化完成

---

## 阶段 2: 后端 API (预计 6-8 小时)

### 任务 2.1: 课程列表 API

**文件:** `backend/app/routes/course_platform.py`

**端点:** `GET /api/courses`

**功能:**
- 支持分页
- 支持分类筛选
- 支持搜索
- 支持排序（热门/最新/高评分）

**请求示例:**
```
GET /api/courses?category=programming&sort=hot&page=1&limit=12
```

**响应示例:**
```json
{
  "courses": [
    {
      "id": 1,
      "slug": "openspec-vibecoding",
      "title": "OpenSpec VibeCoding 课程",
      "cover_image": "...",
      "statistics": {
        "view_count": 89200,
        "like_count": 12500,
        "avg_rating": 4.9
      }
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 12
}
```

**验收标准:**
- [ ] 分页正常工作
- [ ] 筛选功能正常
- [ ] 排序功能正常
- [ ] 响应性能良好（<200ms）

---

### 任务 2.2: 课程详情 API

**端点:** `GET /api/courses/:slug`

**功能:**
- 获取课程完整信息
- 包含章节列表
- 包含统计数据
- 记录浏览次数

**响应内容:**
- 课程基本信息
- 分类信息
- 统计数据
- 章节列表（不含详细内容）
- 讲师信息（预留）

**验收标准:**
- [ ] 能正确返回课程详情
- [ ] 浏览次数正确累加
- [ ] 章节列表按顺序排列

---

### 任务 2.3: 课程分类 API

**端点:** `GET /api/course-categories`

**功能:**
- 获取所有分类（树形结构）
- 支持按 slug 筛选

**验收标准:**
- [ ] 返回树形分类结构
- [ ] 支持多级分类

---

### 任务 2.4: 用户课程 API

**端点:**
- `POST /api/courses/:id/enroll` - 报名课程
- `GET /api/my-courses` - 我的课程

**功能:**
- 用户报名课程
- 获取用户已报名的课程列表
- 显示学习进度

**验收标准:**
- [ ] 报名功能正常
- [ ] 重复报名处理
- [ ] 进度信息正确

---

### 任务 2.5: 互动统计 API

**端点:**
- `POST /api/courses/:id/like` - 点赞
- `POST /api/courses/:id/bookmark` - 收藏
- `GET /api/courses/:id/statistics` - 统计数据

**功能:**
- 用户点赞/取消点赞
- 用户收藏/取消收藏
- 获取课程统计数据
- 防止重复点赞/收藏

**验收标准:**
- [ ] 点赞功能正常
- [ ] 收藏功能正常
- [ ] 统计数据实时更新

---

### 任务 2.6: 课程评价 API

**端点:**
- `GET /api/courses/:id/reviews` - 获取评价
- `POST /api/courses/:id/reviews` - 提交评价

**功能:**
- 分页获取评价列表
- 用户提交评价（评分 + 评论）
- 每个用户只能评价一次
- 计算平均评分

**验收标准:**
- [ ] 评价列表分页正常
- [ ] 提交评价功能正常
- [ ] 平均评分正确计算

---

### 任务 2.7: 课程管理 API

**端点:**
- `GET /api/admin/courses` - 课程列表
- `POST /api/admin/courses` - 创建课程
- `PUT /api/admin/courses/:id` - 更新课程
- `DELETE /api/admin/courses/:id` - 删除课程
- `POST /api/admin/courses/:id/publish` - 发布课程

**功能:**
- 管理员 CRUD 操作
- 课程发布/下架
- 权限验证

**验收标准:**
- [ ] 所有 CRUD 操作正常
- [ ] 权限验证生效
- [ ] 发布状态正确切换

---

### 任务 2.8: 统计数据更新逻辑

**文件:** `backend/app/services/course_statistics_service.py`

**功能:**
- 浏览计数更新
- 点赞计数更新
- 收藏计数更新
- 报名人数更新
- 评价计数和平均分更新
- 完成人数更新

**验收标准:**
- [ ] 统计数据准确
- [ ] 使用事务保证一致性
- [ ] 性能良好

---

## 阶段 3: 前端页面 (预计 8-10 小时)

### 任务 3.1: 课程列表页

**文件:** `frontend/src/pages/CoursesPage.tsx`

**路由:** `/courses`

**组件结构:**
```
CoursesPage
├── PageHeader (页面标题 + 搜索框)
├── CourseLayout
│   ├── FilterSidebar (筛选侧边栏)
│   └── CourseGrid (课程卡片网格)
│       └── CourseCard (课程卡片)
```

**筛选条件:**
- 课程分类
- 价格范围
- 评分范围
- 难度级别
- 时长范围

**验收标准:**
- [ ] 页面布局正确
- [ ] 筛选功能正常
- [ ] 卡片显示正确
- [ ] 响应式布局

---

### 任务 3.2: 课程详情页

**文件:** `frontend/src/pages/CourseDetailPage.tsx`

**路由:** `/courses/:slug`

**组件结构:**
```
CourseDetailPage
├── CourseBanner (封面图 + 基本信息)
├── CourseTabs (Tab 导航)
│   ├── CourseIntro (课程介绍)
│   ├── CourseChapters (章节列表)
│   ├── CourseReviews (评价)
│   └── CourseInstructor (讲师)
└── EnrollmentBar (报名栏 - 固定在底部)
```

**验收标准:**
- [ ] 页面布局正确
- [ ] Tab 切换正常
- [ ] 报名功能正常
- [ ] 分享功能正常

---

### 任务 3.3: 课程学习页

**文件:** 复用扩展现有 `frontend/src/components/Tools/OpenSpecCourse/`

**改动:**
- 支持多课程（从单课程扩展）
- 路由改为 `/courses/:slug/learn`
- API 调用适配新的课程平台

**验收标准:**
- [ ] 现有功能保留
- [ ] 支持多课程切换
- [ ] 学习进度正确追踪

---

### 任务 3.4: 课程卡片组件

**文件:** `frontend/src/components/Courses/CourseCard.tsx`

**设计:**
- 与首页工具卡片风格一致
- 显示：封面图、标题、描述、评分、讲师、统计
- 悬停效果
- 点击跳转详情

**验收标准:**
- [ ] 样式与工具卡片一致
- [ ] 响应式布局
- [ ] 悬停效果流畅

---

### 任务 3.5: 课程筛选侧边栏

**文件:** `frontend/src/components/Courses/FilterSidebar.tsx`

**功能:**
- 分类树形选择
- 价格范围滑块
- 评分星级选择
- 难度选择
- 时长范围

**验收标准:**
- [ ] 所有筛选条件可用
- [ ] 多选项支持
- [ ] 筛选结果实时更新

---

### 任务 3.6: 首页课程入口卡片

**文件:** `frontend/src/components/Tools/OpenSpecCourse/OpenSpecCourseCard.tsx`

**改动:**
- 保持现有设计
- 点击跳转到课程列表页或学习页
- 已报名用户显示进度

**验收标准:**
- [ ] 点击跳转正确
- [ ] 进度显示正确

---

### 任务 3.7: 我的课程页

**文件:** `frontend/src/pages/MyCoursesPage.tsx`

**路由:** `/my-courses`

**功能:**
- 显示用户已报名的课程
- 显示每门课程的学习进度
- 快速继续学习

**验收标准:**
- [ ] 课程列表正确
- [ ] 进度显示正确
- [ ] 继续学习功能正常

---

### 任务 3.8: 课程评价组件

**文件:** `frontend/src/components/Courses/CourseReviews.tsx`

**功能:**
- 评价列表展示
- 评分星级显示
- 提交评价表单
- 分页加载

**验收标准:**
- [ ] 评价展示正确
- [ ] 提交评价功能正常
- [ ] 分页加载正常

---

## 阶段 4: 后台管理 (预计 6-8 小时)

### 任务 4.1: 课程管理首页

**文件:** `frontend/src/components/Admin/CourseManagement/CourseList.tsx`

**功能:**
- 课程列表展示
- 搜索功能
- 状态筛选
- 分类筛选
- 操作按钮（编辑/删除/发布）

**验收标准:**
- [ ] 列表展示正确
- [ ] 筛选功能正常
- [ ] 操作按钮有效

---

### 任务 4.2: 课程编辑器

**文件:** `frontend/src/components/Admin/CourseManagement/CourseEditor.tsx`

**功能:**
- 基本信息编辑
- 封面图上传
- 分类选择
- 课程状态切换

**验收标准:**
- [ ] 表单验证正确
- [ ] 保存功能正常
- [ ] 封面图预览

---

### 任务 4.3: 富文本编辑器集成

**文件:** `frontend/src/components/Common/RichTextEditor.tsx`

**技术栈:** TipTap

**功能:**
- Markdown 支持
- 富文本编辑
- 实时预览
- 代码块高亮

**依赖:**
```json
{
  "@tiptap/react": "^2.0.0",
  "@tiptap/starter-kit": "^2.0.0",
  "@tiptap/extension-code-block-lowlight": "^2.0.0",
  "highlight.js": "^11.0.0"
}
```

**验收标准:**
- [ ] 编辑器正常加载
- [ ] Markdown 语法支持
- [ ] 预览功能正常
- [ ] 代码高亮正常

---

### 任务 4.4: OSS 上传集成

**文件:** `frontend/src/components/Common/OssUploader.tsx`

**功能:**
- 拖拽上传
- 图片预览
- 视频上传
- 进度显示
- 文件类型限制

**验收标准:**
- [ ] 上传功能正常
- [ ] 进度显示正确
- [ ] 文件类型验证

---

### 任务 4.5: 章节管理

**文件:** 复用扩展现有组件

**功能:**
- 章节列表
- 章节编辑
- 拖拽排序
- 批量操作

**验收标准:**
- [ ] 复用现有组件
- [ ] 支持多课程

---

### 任务 4.6: 统计数据展示

**文件:** `frontend/src/components/Admin/CourseManagement/CourseStatistics.tsx`

**功能:**
- 课程统计数据展示
- 图表可视化
- 趋势分析

**验收标准:**
- [ ] 数据展示正确
- [ ] 图表清晰

---

## 阶段 5: 集成和测试 (预计 2-3 小时)

### 任务 5.1: 数据迁移验证

**工作内容:**
1. 执行数据迁移脚本
2. 验证导出的数据完整
3. 验证导入的数据完整
4. 验证统计数据

**验收标准:**
- [ ] 5 个章节完整
- [ ] 测验题目完整
- [ ] 资源完整
- [ ] 统计数据正确

---

### 任务 5.2: API 集成测试

**文件:** `backend/tests/test_course_platform.py`

**测试内容:**
- 课程列表 API
- 课程详情 API
- 报名 API
- 互动 API
- 评价 API
- 管理 API

**验收标准:**
- [ ] 所有测试通过
- [ ] 覆盖率>80%

---

### 任务 5.3: 前端功能测试

**测试内容:**
- 课程列表页
- 课程详情页
- 课程学习页
- 我的课程页
- 后台管理页

**验收标准:**
- [ ] 所有页面能正常访问
- [ ] 功能正常工作
- [ ] 无控制台错误

---

### 任务 5.4: 浏览器兼容性测试

**测试浏览器:**
- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

**验收标准:**
- [ ] 所有主流浏览器正常
- [ ] 响应式布局正常
- [ ] 移动端适配良好

---

## 任务依赖关系

```
阶段 1 (数据库)
├── 1.1 ─┬─> 1.2 ─┬─> 1.3
│        │        └─> 1.4
│        │
阶段 2 (API)
├── 2.1 (依赖 1.2, 1.3)
├── 2.2 (依赖 1.2, 1.3)
├── 2.3 (依赖 1.2, 1.3)
├── 2.4 (依赖 1.2, 1.3)
├── 2.5 (依赖 1.2, 1.3)
├── 2.6 (依赖 1.2, 1.3)
├── 2.7 (依赖 1.2, 1.3)
└── 2.8 (依赖 1.2, 1.3)
│
阶段 3 (前端)
├── 3.1 (依赖 2.1)
├── 3.2 (依赖 2.2)
├── 3.3 (依赖 2.2)
├── 3.4 (依赖 2.1)
├── 3.5 (依赖 2.1)
├── 3.6 (依赖 2.2)
├── 3.7 (依赖 2.4)
└── 3.8 (依赖 2.6)
│
阶段 4 (后台)
├── 4.1 (依赖 2.7)
├── 4.2 (依赖 2.7)
├── 4.3 (独立)
├── 4.4 (独立)
├── 4.5 (依赖 1.4)
└── 4.6 (依赖 2.8)
│
阶段 5 (测试)
├── 5.1 (依赖 1.4)
├── 5.2 (依赖 阶段 2)
├── 5.3 (依赖 阶段 3)
└── 5.4 (依赖 阶段 3)
```

---

## 开始实现

建议按以下顺序开始：

1. **首先完成阶段 1** - 数据库是基础
2. **然后完成阶段 2 的核心 API** - 课程列表、详情 API
3. **同时开始阶段 3 的组件开发** - 课程卡片、列表页
4. **前后端联调**
5. **最后完成后台管理和测试**

---

**下一步:** 开始实现阶段 1 - 任务 1.1 创建数据库迁移脚本
