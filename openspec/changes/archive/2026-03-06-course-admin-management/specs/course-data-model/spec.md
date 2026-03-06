## ADDED Requirements

### Requirement: 课程章节数据模型

系统使用关系型数据库存储课程章节数据，支持章节的层次结构和元数据。

#### Scenario: 章节数据存储
- **WHEN** 创建新章节时
- **THEN** 系统在 openspec_course_chapters 表中插入记录，包含 slug、title、content、chapter_type 等字段

#### Scenario: 章节关联测验
- **WHEN** 章节需要关联测验时
- **THEN** 系统通过 required_quiz_id 外键关联到 openspec_course_quizzes 表

### Requirement: 测验数据模型

系统使用三张表（测验、题目、选项）存储测验数据，支持单选和多选题型。

#### Scenario: 测验数据存储
- **WHEN** 创建新测验时
- **THEN** 系统在 openspec_course_quizzes 表中插入记录，关联到 chapter_id

#### Scenario: 题目数据存储
- **WHEN** 为测验添加题目时
- **THEN** 系统在 openspec_course_quiz_questions 表中插入记录，包含 question_text、question_type、correct_answer、explanation

#### Scenario: 选项数据存储
- **WHEN** 为题目添加选项时
- **THEN** 系统在 openspec_course_quiz_options 表中插入记录，包含 option_text、option_index

### Requirement: 课程资源数据模型

系统使用独立表存储课程资源，支持多种资源类型和扩展元数据。

#### Scenario: 资源数据存储
- **WHEN** 为章节添加资源时
- **THEN** 系统在 openspec_course_resources 表中插入记录，包含 resource_type、title、content、extra_data

#### Scenario: 资源元数据存储
- **WHEN** 资源需要额外元数据时
- **THEN** 系统将元数据序列化为 JSON 字符串存储在 extra_data 字段

### Requirement: 用户进度数据模型

系统记录用户对每个章节的学习进度，包括测验得分和视频播放进度。

#### Scenario: 进度数据存储
- **WHEN** 用户开始学习章节时
- **THEN** 系统在 openspec_user_progress 表中插入或更新记录，包含 status、quiz_score、quiz_passed、video_progress

#### Scenario: 进度记录唯一性
- **WHEN** 同一用户对同一章节多次学习时
- **THEN** 系统更新现有进度记录，不创建重复记录（通过 user_id 和 chapter_id 唯一约束）
