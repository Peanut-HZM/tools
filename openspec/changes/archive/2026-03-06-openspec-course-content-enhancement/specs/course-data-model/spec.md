## ADDED Requirements

### Requirement: 课程数据模型
系统 MUST 支持课程相关的数据模型，包括章节、测验、题目、选项、资源、用户进度。

#### Scenario: 创建章节数据
- **WHEN** 系统初始化课程数据
- **THEN** 创建 CourseChapter 表，包含 slug、title、order、content、chapter_type 等字段

#### Scenario: 创建测验数据
- **WHEN** 系统初始化测验数据
- **THEN** 创建 CourseQuiz、CourseQuizQuestion、CourseQuizOption 表，支持关联章节

#### Scenario: 创建进度数据
- **WHEN** 用户开始学习课程
- **THEN** 创建 UserCourseProgress 记录，追踪用户学习状态
