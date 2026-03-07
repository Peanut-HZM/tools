# course-data-model Specification

## Purpose
TBD - created by archiving change openspec-course-content-enhancement. Update Purpose after archive.
## Requirements
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

### Requirement: Course Platform Database Tables

The system shall create 12 new database tables for the course platform.

#### Scenario
Database tables for courses, chapters, quizzes, enrollments, progress, interactions, reviews, and statistics.

#### Acceptance Criteria
- [x] All tables are created via Alembic migration
- [x] Foreign key constraints are properly set
- [x] Indexes are created for frequently queried columns

### Requirement: SQLAlchemy Models

The system shall create SQLAlchemy model classes for all 12 tables.

#### Scenario
ORM models for database operations.

#### Acceptance Criteria
- [x] All model classes are properly defined
- [x] Table relationships are correctly configured
- [x] CRUD operations work correctly

### Requirement: Pydantic Schemas

The system shall create Pydantic schemas for request/response validation.

#### Scenario
Request and response validation schemas.

#### Acceptance Criteria
- [x] Base Create, Update, Response schemas for each model
- [x] Nested response support for related data
- [x] Validation logic is correct

### Requirement: Data Migration

The system shall migrate existing OpenSpec VibeCoding course data to new tables.

#### Scenario
Migrate 5 chapters, quizzes, and resources to new schema.

#### Acceptance Criteria
- [x] 5 chapters migrated completely
- [x] Quiz data migrated completely
- [x] Resource data migrated completely
- [x] Statistics initialized correctly

