# OpenSpec VibeCoding 互动课程设计文档

**创建日期:** 2026-03-04
**作者:** VibeCoding 推广团队
**版本:** 1.0

---

## 项目概述

### 目标
通过故事驱动的互动方式，让公司同事快速掌握 OpenSpec 编程，理解 VibeCoding 和 SpecCoding 的最佳实践。

### 课程定位
- **主题:** OpenSpec 入门和深入使用，以及与 spec-kit 的区别对比
- **形式:** 网页 + 视频的混合式互动课程
- **风格:** 生动、幽默、富有互动性
- **入口:** 在工具箱首页增加醒目的课程入口

---

## 故事驱动的课程结构

### 第一章："最初的我" - 谨慎使用 AI 😰
**内容:**
- 刚开始使用 AI 编程时的谨慎心态
- 什么都要描述得很清楚
- 要改的代码都会复制引用到对话中
- 心理活动：生怕 AI 理解错了

**交互元素:**
- 代码示例：展示早期"啰嗦"的 prompt 写法
- 视频嵌入：讲述初体验的趣事

### 第二章："遇到问题" - AI 乱改代码的困扰 🤯
**内容:**
- AI 经常乱改代码，超出修改范围
- 改的东西不符合要求
- 觉得 AI 很傻很笨
- 逐渐失去信心

**交互元素:**
- 对比演示：期望的修改 vs AI 实际修改
- 互动测验：识别"AI 乱改"的常见场景

### 第三章："发现规则" - rules 的拯救 🎉
**内容:**
- 发现可以使用 rules 规范开发
- 一开始觉得惊艳很好用
- 代码质量明显提升
- 建立信心

**交互元素:**
- 代码示例：展示有效的 rules 配置
- 对比演示：有 rules 前后的 AI 输出对比

### 第四章："进阶工具" - OpenSpec/Superpowers 🚀
**内容:**
- 进一步使用 OpenSpec
- 使用 spec-kit
- 使用 superpowers 等技能
- 开发效率大幅提升

**交互元素:**
- 代码示例：OpenSpec spec 文件示例
- 在线尝试区：简易 spec 编辑器
- 视频嵌入：展示完整工作流

### 第五章："对比思考" - 为什么选择 OpenSpec ⚖️
**内容:**
- OpenSpec vs spec-kit 详细对比
- 各自的优势和适用场景
- 推荐的学习路径
- VibeCoding 最佳实践总结

**交互元素:**
- 对比表格：功能、易用性、扩展性对比
- 互动测验：选择合适的工具场景
- 最终测验：综合测试学习成果

---

## 功能需求

### 1. 课程展示系统
| 功能 | 描述 |
|------|------|
| 章节导航 | 左侧显示章节列表，支持点击跳转 |
| 内容渲染 | 支持 Markdown、代码高亮、视频嵌入 |
| 进度追踪 | 显示每章的学习进度（未开始/进行中/已完成） |
| 锁章机制 | 需要通过测验才能解锁下一章 |

### 2. 互动测验系统
| 功能 | 描述 |
|------|------|
| 题型支持 | 单选题、多选题、判断题 |
| 即时反馈 | 答题后立即显示正确/错误及解析 |
| 分数记录 | 记录每次测验的分数和用时 |
| 重试机制 | 答错可以重试，取最高分 |

### 3. 代码示例展示
| 功能 | 描述 |
|------|------|
| 语法高亮 | 支持 TypeScript、JSON、Markdown 等 |
| 一键复制 | 点击按钮复制代码到剪贴板 |
| 对比视图 | 并排展示 Before/After 代码 |

### 4. 在线尝试区
| 功能 | 描述 |
|------|------|
| 简化的 spec 编辑器 | 提供基础模板，用户可编辑 |
| 实时预览 | 预览 spec 的效果 |
| 示例库 | 提供多个示例供参考 |

### 5. 视频嵌入
| 功能 | 描述 |
|------|------|
| 视频播放器 | 支持本地视频或外链（B 站/YouTube） |
| 断点续播 | 记录上次播放位置 |
| 字幕支持 | 支持中文字幕 |

---

## 数据模型设计

### Chapter (课程章节)
```python
class Chapter(BaseModel):
    id: int
    title: str                    # 章节标题
    slug: str                     # 章节标识符
    order: int                    # 章节顺序
    content: str                  # 章节内容 (Markdown)
    chapter_type: str             # 类型：story/code/quiz/video
    video_url: Optional[str]      # 视频链接
    is_locked: bool               # 是否锁定
    required_quiz_id: Optional[int]  # 解锁所需的测验 ID
    created_at: datetime
    updated_at: datetime
```

### Quiz (测验题目)
```python
class Quiz(BaseModel):
    id: int
    chapter_id: int               # 所属章节
    title: str                    # 测验标题
    questions: List[QuizQuestion] # 题目列表
    passing_score: int            # 及格分数 (百分比)
    created_at: datetime
    updated_at: datetime

class QuizQuestion(BaseModel):
    id: int
    question_text: str            # 题目内容
    question_type: str            # single/multiple/true_false
    options: List[QuizOption]     # 选项
    correct_answer: List[int]     # 正确答案索引
    explanation: str              # 答案解析

class QuizOption(BaseModel):
    id: int
    option_text: str              # 选项内容
    option_index: int             # 选项索引 (A/B/C/D)
```

### UserProgress (用户进度)
```python
class UserProgress(BaseModel):
    id: int
    user_id: int                  # 用户 ID
    chapter_id: int               # 章节 ID
    status: str                   # not_started/in_progress/completed
    quiz_score: Optional[int]     # 测验分数
    quiz_passed: bool             # 测验是否通过
    completed_at: Optional[datetime]  # 完成时间
    video_progress: int           # 视频播放进度 (秒)
    created_at: datetime
    updated_at: datetime
```

### Resource (课程资源)
```python
class Resource(BaseModel):
    id: int
    chapter_id: int               # 所属章节
    resource_type: str            # code_sample/contrast/video/template
    title: str                    # 资源标题
    content: str                  # 资源内容
    metadata: dict                # 额外元数据
    created_at: datetime
    updated_at: datetime
```

---

## API 接口设计

### 课程相关
```
GET    /api/openspec-course/chapters          # 获取所有章节
GET    /api/openspec-course/chapters/{id}     # 获取单个章节详情
POST   /api/openspec-course/chapters          # 创建章节 (Admin)
PUT    /api/openspec-course/chapters/{id}     # 更新章节 (Admin)
DELETE /api/openspec-course/chapters/{id}     # 删除章节 (Admin)
```

### 测验相关
```
GET    /api/openspec-course/quizzes/{chapter_id}  # 获取章节测验
POST   /api/openspec-course/quizzes/submit        # 提交测验答案
GET    /api/openspec-course/quizzes/{id}/result   # 获取测验结果
```

### 进度相关
```
GET    /api/openspec-course/progress              # 获取用户进度
PUT    /api/openspec-course/progress/{chapter_id} # 更新进度
```

### 资源相关
```
GET    /api/openspec-course/resources/{chapter_id} # 获取章节资源
```

---

## 前端组件设计

### 页面结构
```
/OpenSpecCourse/
├── CourseHomepage.tsx          # 课程主页（入口）
├── ChapterView.tsx             # 章节内容展示
├── QuizView.tsx                # 测验界面
├── SpecEditor.tsx              # spec 编辑器
├── ProgressBar.tsx             # 进度条组件
└── ChapterNavigation.tsx       # 章节导航
```

### 入口设计
在首页 Hero 区域上方添加一个醒目的课程入口卡片：
- 大尺寸卡片，带有动画效果
- 包含课程标题和简介
- "开始学习" 按钮
- 显示课程进度（如果已开始学习）

---

## 技术实现

### 后端技术栈
- FastAPI (Python)
- SQLAlchemy (ORM)
- Pydantic (数据验证)
- JWT 认证

### 前端技术栈
- React 18 + TypeScript
- Tailwind CSS
- React Router
- CodeMirror (代码编辑器)
- React Player (视频播放)

### 数据库
- SQLite (开发环境)
- PostgreSQL/MySQL (生产环境)

---

## 项目结构

```
backend/
├── app/
│   ├── models/
│   │   └── openspec_course.py    # 数据模型定义
│   ├── routes/
│   │   └── openspec_course.py    # API 路由
│   ├── services/
│   │   └── openspec_course.py    # 业务逻辑
│   └── schemas/
│       └── openspec_course.py    # Pydantic 模型

frontend/
├── src/
│   ├── components/
│   │   └── OpenSpecCourse/
│   │       ├── CourseHomepage.tsx
│   │       ├── ChapterView.tsx
│   │       ├── QuizView.tsx
│   │       ├── SpecEditor.tsx
│   │       └── ...
│   ├── pages/
│   │   └── OpenSpecCourse.tsx
│   └── services/
│       └── openspecCourse.ts
```

---

## 时间估算

| 阶段 | 任务 | 估算时间 |
|------|------|----------|
| 1 | 后端数据模型和 API | 4-6 小时 |
| 2 | 前端页面框架和组件 | 6-8 小时 |
| 3 | 测验系统和进度追踪 | 3-4 小时 |
| 4 | Spec 编辑器集成 | 2-3 小时 |
| 5 | 视频嵌入和优化 | 1-2 小时 |
| 6 | 内容填充和测试 | 4-6 小时 |
| **总计** | | **20-29 小时** |

---

## 成功标准

1. ✅ 用户可以完整浏览所有章节内容
2. ✅ 测验系统正常工作，能够正确判分
3. ✅ 学习进度正确记录和显示
4. ✅ 代码示例可以正常复制
5. ✅ Spec 编辑器可以正常使用
6. ✅ 视频可以正常播放
7. ✅ 页面风格活泼有趣，符合宣讲需求

---

## 后续迭代

- [ ] 支持用户评论和讨论
- [ ] 添加学习排行榜
- [ ] 支持课程证书生成
- [ ] 多语言支持
- [ ] 更多互动游戏化元素
