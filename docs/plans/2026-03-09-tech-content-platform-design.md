# 技术分析内容平台设计文档

**创建日期**: 2026-03-09
**状态**: 已批准

## 概述

将首页"教学课程"定位调整为"技术分析"，打造面向公司内部和社交平台的技术内容分享平台。内容类型包括技术深度分析、技术分享回顾、项目案例分析。

## 目标

1. 首页技术分享卡片展示技术分析内容，而非教学课程
2. 内容列表和详情页采用现代化的技术博客风格（参考 Medium/掘金）
3. 所有展示内容为真实有效的数据，支持从现有课程数据迁移
4. 确保现有数据不丢失，通过 `content_type` 字段区分内容类型

## 数据模型设计

### 扩展现有 Course 表

在现有 `courses` 表基础上新增字段，不创建新表：

```python
# backend/app/models/course_platform.py

class Course(Base):
    # ... 现有字段 ...

    # 新增字段
    content_type = Column(String(20), default="analysis", comment="内容类型：analysis(技术分析)/sharing(技术分享)/case_study(项目案例)")
    author = Column(String(100), comment="作者")
    reading_time = Column(Integer, default=0, comment="阅读时长（分钟）")
    tags = Column(Text, comment="标签（JSON 数组）")
```

### 内容类型定义

| 类型 | 值 | 说明 | 标签配色 |
|------|-----|------|----------|
| 技术深度分析 | `analysis` | 技术趋势、架构决策、工程实践分析 | bg-blue-500/20 text-blue-400 |
| 技术分享回顾 | `sharing` | 内部分享会记录、视频、PPT | bg-green-500/20 text-green-400 |
| 项目案例分析 | `case_study` | 真实项目的完整技术分析 | bg-purple-500/20 text-purple-400 |

### 章节类型扩展

在现有 `chapter_type` 基础上扩展：
- 现有：`story`, `lesson`, `quiz-only`, `code`, `video`
- 新增：`section` (文章章节), `slides` (PPT 演示)

## API 设计

### 新增端点

```
GET  /api/v1/tech-contents              # 获取技术分析内容列表
GET  /api/v1/tech-contents/{slug}       # 获取技术内容详情
GET  /api/v1/tech-contents/types        # 获取内容类型列表
POST /api/v1/admin/tech-contents        # 创建技术内容 (Admin)
PUT  /api/v1/admin/tech-contents/{id}   # 更新技术内容 (Admin)
DELETE /api/v1/admin/tech-contents/{id} # 删除技术内容 (Admin)
```

### 响应格式

```json
// GET /api/v1/tech-contents 响应
{
  "contents": [
    {
      "id": 1,
      "slug": "openspec-vibecoding-practice",
      "content_type": "analysis",
      "title": "OpenSpec VibeCoding 实践指南",
      "description": "本文深入分析 VibeCoding 在企业级开发中的最佳实践...",
      "cover_image": "https://...",
      "author": "张三",
      "reading_time": 5,
      "tags": ["AI 编程", "OpenSpec", "工程实践"],
      "published_at": "2026-03-09T10:00:00Z",
      "views": 1234,
      "likes": 56
    }
  ],
  "total": 10,
  "page": 1,
  "limit": 10
}
```

## UI 组件设计

### 首页卡片组件 (TechContentCard)

```typescript
interface TechContentCardProps {
  id: number;
  coverImage?: string;      // 封面图 URL
  contentType: 'analysis' | 'sharing' | 'case_study';
  tags: string[];           // 标签列表
  title: string;            // 标题
  description: string;      // 描述
  author?: string;          // 作者
  readingTime: number;      // 阅读时长（分钟）
  publishedAt: string;      // 发布时间
  views?: number;           // 阅读数
  likes?: number;           // 点赞数
}
```

### 卡片布局

```
┌─────────────────────────────────────┐
│  [封面图片]                          │
│  ┌─────────────────────────────────┐│
│  │  技术分析  项目案例              ││  ← 标签
│  └─────────────────────────────────┘│
│                                      │
│  OpenSpec VibeCoding 实践指南        │  ← 标题（2 行截断）
│                                      │
│  本文深入分析 VibeCoding 在企业级...  │  ← 描述（3 行截断）
│                                      │
│  ┌─────────────────────────────────┐│
│  │ [头像] 作者名  ·  5 min read    ││  ← 作者和阅读时长
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

### 内容列表页

**路由**: `/tech-contents`

**布局**:
- 顶部：页面标题 + 描述
- 筛选栏：内容类型筛选（全部/技术分析/技术分享/项目案例）
- 内容区：卡片网格（2-3 列）
- 底部：分页

### 内容详情页

**路由**: `/tech-contents/:slug`

**布局**:
- 面包屑导航
- 封面图（可选）
- 内容标签
- 标题
- 作者信息卡片（头像、作者名、发布时间、阅读时长）
- 正文内容（Markdown 渲染）
- 互动区（点赞、收藏、分享）
- 相关推荐

## 数据迁移方案

### 迁移原则

1. **不丢失现有数据**：现有课程内容保留
2. **向后兼容**：原有课程页面 (`/courses`) 继续可用
3. **渐进式迁移**：先迁移 OpenSpec VibeCoding 内容

### 迁移步骤

**步骤 1：数据库 Schema 变更**

```sql
-- 新增字段
ALTER TABLE courses ADD COLUMN content_type VARCHAR(20) DEFAULT 'analysis';
ALTER TABLE courses ADD COLUMN author VARCHAR(100);
ALTER TABLE courses ADD COLUMN reading_time INT DEFAULT 0;
ALTER TABLE courses ADD COLUMN tags TEXT;

-- 创建索引
CREATE INDEX idx_courses_content_type ON courses(content_type);
```

**步骤 2：迁移现有 OpenSpec 课程数据**

使用现有的导出脚本导出数据，然后转换：

```python
# scripts/migrate_to_tech_contents.py

# 1. 导出 OpenSpec 课程数据
# 2. 将 course 表数据映射到 content_type='analysis'
# 3. 设置 author、reading_time、tags 等字段
# 4. 导入到 courses 表
```

**步骤 3：更新前端**

- 新增 `/tech-contents` 路由和页面
- 新增 TechContentCard 组件
- 更新首页 Recommendations 组件展示技术内容

### 迁移后数据示例

| course_id | content_type | title | 说明 |
|-----------|--------------|-------|------|
| 1 | analysis | OpenSpec VibeCoding 实践指南 | 从原有课程迁移 |
| 2 | analysis | AI 编程效率提升实践 | 新增技术分析 |
| 3 | sharing | 团队内部分享：Spec 驱动开发 | 技术分享 |
| 4 | case_study | XX 系统重构案例分析 | 项目案例 |

## 前端路由设计

```
/tech-contents              // 技术分析内容列表页
/tech-contents?type=analysis  // 技术深度分析列表
/tech-contents?type=sharing   // 技术分享列表
/tech-contents?type=case      // 项目案例列表
/tech-contents/:slug          // 内容详情页
```

## 实施步骤

1. **后端数据模型扩展** - 修改 Course 模型，新增字段
2. **后端 API 开发** - 新增技术分析内容相关 API
3. **前端卡片组件** - 开发 TechContentCard 组件
4. **前端列表页** - 开发 `/tech-contents` 列表页
5. **前端详情页** - 开发内容详情页面
6. **数据迁移** - 迁移现有 OpenSpec 课程数据
7. **首页集成** - 更新首页 Recommendations 组件

## 验收标准

1. ✅ 首页展示技术分析内容卡片（非教学课程）
2. ✅ 卡片样式为现代化技术博客风格（封面图 + 标签 + 作者 + 阅读时长）
3. ✅ 内容列表页支持类型筛选和分页
4. ✅ 内容详情页支持 Markdown 渲染
5. ✅ 所有展示内容为真实有效的数据
6. ✅ 现有课程数据不丢失
7. ✅ 原有课程页面 (`/courses`) 继续可用

## 附录：现有数据迁移映射

### OpenSpec VibeCoding 课程 → 技术分析内容

| 原字段 | 新字段 | 映射说明 |
|--------|--------|----------|
| title | title | 保持不变，调整标题风格 |
| description | description | 保持不变 |
| cover_image | cover_image | 保持不变 |
| - | content_type | 设置为 `analysis` |
| - | author | 设置作者名 |
| - | reading_time | 根据章节内容计算 |
| - | tags | 从标题/描述提取关键词 |
| chapters | sections | chapter_type 映射为 section |
