## Context

OpenSpec 课程后台管理功能已实现，但课程内容匮乏。需要基于现有的数据模型和 API，丰富课程内容，让学员能够系统学习 OpenSpec 的使用方法和最佳实践。

**当前状态：**
- 后端：数据模型和 API 已实现（routes/openspec_course.py, services/openspec_course_service.py）
- 前端：课程展示页面框架已存在（OpenSpecCourse.tsx 及相关组件）
- 管理后台：课程管理功能已实现（CourseManagement 组件）
- 课程内容：仅有基础章节数据，缺少详细内容

**约束条件：**
- 需要保持与现有 API 的兼容性
- 课程内容需要存储在数据库中，支持后台管理
- 前端组件需要适配新的数据结构

## Goals / Non-Goals

**Goals:**
- 丰富课程内容，添加详细的 OpenSpec 技能说明
- 添加三大工具（OpenSpec、spec-kit、Superpowers）的对比内容
- 完善第一章，说明初级阶段与 AI 沟通的细节
- 初始化课程数据到数据库

**Non-Goals:**
- 不修改现有的数据模型结构
- 不修改现有的 API 接口
- 不修改管理后台功能
- 不添加新的功能特性

## Decisions

### 决策 1：内容存储方式
**选择：** 将详细课程内容存储在数据库的章节 content 字段中（Markdown 格式）

**备选方案：**
- 方案 A：使用外部 Markdown 文件，通过 API 加载
- 方案 B：硬编码在前端组件中

**理由：**
- 使用数据库存储支持后台管理，便于后续更新
- Markdown 格式支持丰富的内容展示（代码块、表格、列表）
- 与现有数据模型兼容，无需修改

### 决策 2：前端内容渲染
**选择：** 使用 ReactMarkdown 组件渲染章节内容

**备选方案：**
- 方案 A：使用 dangerouslySetInnerHTML
- 方案 B：自定义 Markdown 解析器

**理由：**
- ReactMarkdown 安全性高，自动过滤危险的 HTML
- 支持自定义组件样式，可适配课程主题
- 社区成熟，维护活跃

### 决策 3：课程内容结构
**选择：** 按照设计文档的章节结构组织内容（共 5 章）

**章节安排：**
1. 第一章：最初的我 - 谨慎使用 AI（详细沟通模板）
2. 第二章：遇到问题 - AI 乱改代码的困扰
3. 第三章：发现规则 - rules 的拯救
4. 第四章：进阶工具 - OpenSpec & Superpowers（技能详解）
5. 第五章：对比思考 - 工具对比与最佳实践

## Risks / Trade-offs

**风险 1：内容过长影响加载性能**
→ 缓解：章节内容分页加载，使用懒加载策略

**风险 2：Markdown 渲染样式不一致**
→ 缓解：使用统一的 prose 样式，自定义 Markdown 组件样式

**风险 3：测验数据初始化复杂**
→ 缓解：使用初始化脚本批量创建测验数据

## Migration Plan

### 部署步骤
1. 运行数据库初始化脚本（init_openspec_course.py）
2. 验证课程内容数据是否正确加载
3. 前端验证课程展示页面是否正常

### 回滚策略
- 如出现问题，可删除数据库中的课程数据
- 使用 SQL: `DELETE FROM openspec_course_chapters;`

## Open Questions

- 是否需要添加视频内容？（待确定视频来源和存储方式）
- 是否需要支持用户评论功能？（可作为后续迭代）
