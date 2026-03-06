# Spec: 课程平台核心功能

**变更:** course-platform-implementation
**创建日期:** 2026-03-07
**状态:** 草稿

---

## 1. 概述

本 Spec 定义课程学习平台的核心功能需求，包括课程展示、报名、互动等功能。

---

## 2. 功能需求

### 2.1 课程列表功能

**ID:** COURSE-LIST-001

**描述:** 用户可以浏览和筛选课程列表

**需求:**
- MUST 支持分页显示课程
- MUST 支持按分类筛选
- MUST 支持搜索关键词
- MUST 支持多种排序方式（热门/最新/高评分）
- MUST 显示课程卡片（封面、标题、评分、统计数据）

**API:**
```
GET /api/courses
Query: category, search, sort, page, limit
```

---

### 2.2 课程详情功能

**ID:** COURSE-DETAIL-001

**描述:** 用户可以查看课程详细信息

**需求:**
- MUST 显示课程完整信息（标题、描述、封面、讲师）
- MUST 显示章节列表
- MUST 显示统计数据（浏览、点赞、收藏、评价）
- MUST 记录浏览次数
- MUST 支持报名课程

**API:**
```
GET /api/courses/:slug
POST /api/courses/:id/enroll
```

---

### 2.3 课程互动功能

**ID:** COURSE-INTERACTION-001

**描述:** 用户可以与课程互动

**需求:**
- MUST 支持点赞课程
- MUST 支持收藏课程
- MUST 防止重复点赞/收藏
- MUST 实时更新统计数据

**API:**
```
POST /api/courses/:id/like
POST /api/courses/:id/bookmark
GET /api/courses/:id/statistics
```

---

### 2.4 课程评价功能

**ID:** COURSE-REVIEW-001

**描述:** 用户可以提交和查看课程评价

**需求:**
- MUST 支持评分（1-5 星）
- MUST 支持文字评论
- MUST 每个用户只能评价一次
- MUST 计算并显示平均评分
- MUST 分页显示评价列表

**API:**
```
GET /api/courses/:id/reviews
POST /api/courses/:id/reviews
```

---

### 2.5 我的课程功能

**ID:** MY-COURSES-001

**描述:** 用户可以查看已报名的课程

**需求:**
- MUST 显示用户已报名的课程列表
- MUST 显示每门课程的学习进度
- MUST 支持快速继续学习

**API:**
```
GET /api/my-courses
```

---

## 3. 数据需求

### 3.1 课程主表 (courses)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 课程 ID |
| title | VARCHAR(200) | NOT NULL | 课程标题 |
| slug | VARCHAR(100) | UNIQUE | 课程标识符 |
| description | TEXT | NOT NULL | 课程描述 |
| cover_image | VARCHAR(500) | NULL | 封面图 |
| category_id | BIGINT | FK | 分类 ID |
| price | DECIMAL | DEFAULT 0 | 价格 |
| status | VARCHAR(20) | DEFAULT 'draft' | 状态 |

---

### 3.2 课程统计表 (course_statistics)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 统计 ID |
| course_id | BIGINT | UNIQUE | 课程 ID |
| view_count | BIGINT | DEFAULT 0 | 浏览次数 |
| like_count | BIGINT | DEFAULT 0 | 点赞数 |
| bookmark_count | BIGINT | DEFAULT 0 | 收藏数 |
| review_count | BIGINT | DEFAULT 0 | 评价数 |
| avg_rating | FLOAT | DEFAULT 0 | 平均评分 |
| completed_count | BIGINT | DEFAULT 0 | 完成人数 |

---

## 4. 非功能需求

### 4.1 性能

- 课程列表 API 响应时间 < 200ms
- 课程详情 API 响应时间 < 300ms
- 页面加载时间 < 3 秒

### 4.2 数据一致性

- 统计数据必须使用事务保证一致性
- 定期校验统计数据准确性

### 4.3 用户体验

- 与现有页面风格一致
- 响应式布局
- 无控制台错误

---

## 5. 验收标准

### 5.1 功能验收

- [ ] 用户可以浏览课程列表
- [ ] 用户可以查看课程详情
- [ ] 用户可以报名课程
- [ ] 用户可以点赞、收藏课程
- [ ] 用户可以提交评价
- [ ] 用户可以查看我的课程

### 5.2 数据验收

- [ ] 现有 OpenSpec 课程内容完整迁移
- [ ] 统计数据准确记录

---

**审批:**
- [ ] 产品审批
- [ ] 技术审批
