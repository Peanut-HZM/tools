# Spec: 课程平台数据模型

**变更:** course-platform-implementation
**创建日期:** 2026-03-07
**状态:** 草稿

---

## 1. 概述

本 Spec 定义课程学习平台的数据库模型设计。

---

## 2. 数据表列表

### 核心业务表 (7 张)

| 表名 | 说明 | 备注 |
|------|------|------|
| courses | 课程主表 | |
| course_categories | 课程分类表 | 支持树形结构 |
| course_chapters | 课程章节表 | 外键关联课程 |
| course_quizzes | 课程测验表 | 外键关联章节 |
| course_quiz_questions | 测验题目表 | |
| course_quiz_options | 测验选项表 | |
| course_resources | 课程资源表 | 支持 OSS 文件 |

### 用户交互表 (5 张)

| 表名 | 说明 | 备注 |
|------|------|------|
| course_enrollments | 用户课程关联表 | 唯一约束 (user_id, course_id) |
| course_progress | 学习进度表 | 唯一约束 (user_id, chapter_id) |
| course_interactions | 课程互动表 | 点赞/收藏/浏览 |
| course_reviews | 课程评价表 | |
| course_statistics | 课程统计表 | 唯一约束 course_id |

---

## 3. 表结构详情

### 3.1 courses - 课程主表

```sql
CREATE TABLE courses (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL COMMENT '课程标题',
    slug VARCHAR(100) UNIQUE NOT NULL COMMENT '课程标识符',
    description TEXT NOT NULL COMMENT '课程描述',
    cover_image VARCHAR(500) COMMENT '封面图 URL',
    category_id BIGINT COMMENT '分类 ID',
    instructor_id BIGINT COMMENT '讲师 ID',
    price DECIMAL(10,2) DEFAULT 0 COMMENT '价格',
    status VARCHAR(20) DEFAULT 'draft' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES course_categories(id)
);
```

### 3.2 course_categories - 课程分类表

```sql
CREATE TABLE course_categories (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '分类名称',
    slug VARCHAR(50) UNIQUE NOT NULL COMMENT '分类标识符',
    parent_id BIGINT COMMENT '父分类 ID',
    sort_order INT DEFAULT 0 COMMENT '排序',
    icon VARCHAR(50) COMMENT '图标',
    FOREIGN KEY (parent_id) REFERENCES course_categories(id)
);
```

### 3.3 course_chapters - 课程章节表

```sql
CREATE TABLE course_chapters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT NOT NULL COMMENT '课程 ID',
    slug VARCHAR(100) NOT NULL COMMENT '章节标识符',
    title VARCHAR(200) NOT NULL COMMENT '章节标题',
    `order` INT DEFAULT 0 COMMENT '章节顺序',
    content TEXT NOT NULL COMMENT '章节内容 (Markdown)',
    chapter_type VARCHAR(50) DEFAULT 'story' COMMENT '类型',
    video_url VARCHAR(500) COMMENT '视频链接',
    is_locked BOOLEAN DEFAULT FALSE COMMENT '是否锁定',
    duration_minutes INT DEFAULT 0 COMMENT '学习时长 (分钟)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

### 3.4 course_quizzes - 课程测验表

```sql
CREATE TABLE course_quizzes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    chapter_id BIGINT NOT NULL COMMENT '章节 ID',
    title VARCHAR(200) NOT NULL COMMENT '测验标题',
    passing_score INT DEFAULT 60 COMMENT '及格分数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES course_chapters(id) ON DELETE CASCADE
);
```

### 3.5 course_quiz_questions - 测验题目表

```sql
CREATE TABLE course_quiz_questions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    quiz_id BIGINT NOT NULL COMMENT '测验 ID',
    question_text TEXT NOT NULL COMMENT '题目内容',
    question_type VARCHAR(20) DEFAULT 'single' COMMENT '类型',
    correct_answer VARCHAR(100) NOT NULL COMMENT '正确答案',
    explanation TEXT COMMENT '答案解析',
    `order` INT DEFAULT 0 COMMENT '题目顺序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_id) REFERENCES course_quizzes(id) ON DELETE CASCADE
);
```

### 3.6 course_quiz_options - 测验选项表

```sql
CREATE TABLE course_quiz_options (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question_id BIGINT NOT NULL COMMENT '题目 ID',
    option_text TEXT NOT NULL COMMENT '选项内容',
    option_index INT NOT NULL COMMENT '选项索引',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES course_quiz_questions(id) ON DELETE CASCADE
);
```

### 3.7 course_resources - 课程资源表

```sql
CREATE TABLE course_resources (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    chapter_id BIGINT NOT NULL COMMENT '章节 ID',
    resource_type VARCHAR(50) NOT NULL COMMENT '资源类型',
    title VARCHAR(200) NOT NULL COMMENT '资源标题',
    content TEXT NOT NULL COMMENT '资源内容',
    file_url VARCHAR(500) COMMENT '文件 URL (OSS)',
    file_size BIGINT COMMENT '文件大小 (字节)',
    extra_data TEXT COMMENT '额外元数据 (JSON)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES course_chapters(id) ON DELETE CASCADE
);
```

### 3.8 course_enrollments - 用户课程关联表

```sql
CREATE TABLE course_enrollments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '用户 ID',
    course_id BIGINT NOT NULL COMMENT '课程 ID',
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '报名时间',
    completed_at TIMESTAMP COMMENT '完成时间',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
    progress_percent FLOAT DEFAULT 0 COMMENT '进度百分比',
    UNIQUE KEY uk_user_course (user_id, course_id),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

### 3.9 course_progress - 学习进度表

```sql
CREATE TABLE course_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '用户 ID',
    chapter_id BIGINT NOT NULL COMMENT '章节 ID',
    status VARCHAR(20) DEFAULT 'not_started' COMMENT '状态',
    quiz_score FLOAT COMMENT '测验分数',
    quiz_passed BOOLEAN DEFAULT FALSE COMMENT '测验是否通过',
    video_progress INT DEFAULT 0 COMMENT '视频进度 (秒)',
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最后访问时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_chapter (user_id, chapter_id),
    FOREIGN KEY (chapter_id) REFERENCES course_chapters(id) ON DELETE CASCADE
);
```

### 3.10 course_interactions - 课程互动表

```sql
CREATE TABLE course_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '用户 ID',
    course_id BIGINT NOT NULL COMMENT '课程 ID',
    interaction_type VARCHAR(20) NOT NULL COMMENT '类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_course_type (course_id, interaction_type),
    INDEX idx_user_course (user_id, course_id),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

### 3.11 course_reviews - 课程评价表

```sql
CREATE TABLE course_reviews (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '用户 ID',
    course_id BIGINT NOT NULL COMMENT '课程 ID',
    rating INT NOT NULL COMMENT '评分 (1-5)',
    comment TEXT COMMENT '评论内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_course (course_id),
    INDEX idx_user (user_id),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

### 3.12 course_statistics - 课程统计表

```sql
CREATE TABLE course_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT UNIQUE NOT NULL COMMENT '课程 ID',
    view_count BIGINT DEFAULT 0 COMMENT '浏览次数',
    enroll_count BIGINT DEFAULT 0 COMMENT '报名人数',
    like_count BIGINT DEFAULT 0 COMMENT '点赞数',
    bookmark_count BIGINT DEFAULT 0 COMMENT '收藏数',
    review_count BIGINT DEFAULT 0 COMMENT '评价数',
    avg_rating FLOAT DEFAULT 0 COMMENT '平均评分',
    completed_count BIGINT DEFAULT 0 COMMENT '完成人数',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

---

## 4. 数据迁移

### 4.1 迁移现有 OpenSpec 课程数据

```python
# 1. 导出旧数据
old_chapters = session.query(CourseChapter).order_by(CourseChapter.order).all()

# 2. 创建新课程
course = Course(
    title="OpenSpec VibeCoding 课程",
    slug="openspec-vibecoding",
    description="从 AI 小白到 Spec 高手的进阶之路",
    status="published"
)

# 3. 迁移章节
for old in old_chapters:
    new = CourseChapter(
        course_id=course.id,
        slug=old.slug,
        title=old.title,
        order=old.order,
        content=old.content,
        chapter_type=old.chapter_type,
        video_url=old.video_url,
        is_locked=old.is_locked
    )

# 4. 初始化统计
CourseStatistics(course_id=course.id)
```

---

## 5. 验收标准

- [ ] 所有表结构正确创建
- [ ] 外键约束正确设置
- [ ] 索引正确创建
- [ ] 数据迁移脚本正常执行
- [ ] 现有数据完整迁移
