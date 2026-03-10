# OpenSpec VibeCoding 实践指南课程优化设计文档

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 优化现有课程 (#4) 的内容，着重介绍 Rules、OpenSpec 核心概念和技能系统，打造面向有经验开发者的实战指南。

**Architecture:** 保持现有 5 章结构，逐章优化内容，增加 Rules 详解、OpenSpec 技能系统详解、实战案例、测验和资源。

**Tech Stack:**
- 课程数据：JSON 格式（`course-export-*.json`）
- 导入方式：通过 `/api/openspec-course/import` API
- 内容格式：Markdown（支持语法高亮、表格、列表）

---

## 课程内容设计

### 第 1 章：最初的我 - 谨慎使用 AI 😰

**章节类型**: story

**核心内容**:
1. 故事化开场：AI 编程新手的真实心态
2. 技术背景：为什么 AI 需要详细沟通（LLM 工作原理简介）
3. 沟通模板：前端/后端修改的完整 checklist
4. 对比案例：错误指令 vs 正确指令

**新增资源**:
- `frontend-prompt-checklist.md` - 前端修改沟通模板
- `backend-prompt-checklist.md` - 后端修改沟通模板

**新增测验** (3 题):
1. 单选：初次使用 AI 编程的正确心态
2. 多选：哪些信息是修改前端组件时必须提供的
3. 场景：选择最佳 Prompt 指令

---

### 第 2 章：遇到问题 - AI 乱改代码的困扰 🤯

**章节类型**: story

**核心内容**:
1. 经典翻车场景合集（3-4 个真实案例）
2. 问题根源分析：
   - 缺少 Rules 约束
   - 需求描述模糊
   - 上下文缺失
   - AI 过度理解
3. 引出 Rules 的必要性

**新增资源**:
- `common-ai-problems-checklist.md` - AI 编程常见问题诊断清单

**新增测验** (3 题):
1. 多选：AI 乱改代码的可能原因
2. 场景分析：识别问题根源
3. 选择：最佳应对策略

---

### 第 3 章：发现规则 - rules 的拯救 🎉

**章节类型**: code

**核心内容**:
1. **Rules 概念详解**:
   - 什么是 Rules
   - Rules 为什么有效
   - Rules 如何工作（AI 理解机制）
2. **Rules 编写指南**:
   - 基本结构（Markdown 格式）
   - 语法规范
   - 最佳实践（具体、可执行、有优先级）
3. **实战案例**:
   - 通用 Rules 示例
   - 前端 Rules 示例
   - 后端 Rules 示例
   - 全栈项目 Rules 示例
4. **效果对比**:
   - 使用 Rules 前：AI 输出示例
   - 使用 Rules 后：AI 输出示例

**新增资源**:
- `rules-templates/` - Rules 模板库
  - `general-rules.md` - 通用规则
  - `frontend-rules.md` - 前端规则
  - `backend-rules.md` - 后端规则
- `rules-writing-checklist.md` - Rules 编写检查清单

**新增测验** (4 题):
1. 单选：Rules 的核心作用
2. 多选：好的 Rules 应该具备的特点
3. 分析：识别 Rules 中的问题
4. 实战：编写一条有效的 Rules

---

### 第 4 章：进阶工具 - OpenSpec & Superpowers 🚀

**章节类型**: code

**核心内容**:

#### Part 1: OpenSpec 核心概念
1. **Change（变更）的概念**:
   - 什么是 Change
   - Change 的生命周期
   - Change 与 Git 分支的区别
2. **Artifact（产物）的类型和作用**:
   - Proposal（提案）
   - Design（设计）
   - Spec（规范）
   - Tasks（任务）
3. **Spec-Driven 工作流的优势**:
   - 先思考再行动
   - 文档化决策
   - 可追溯变更历史

#### Part 2: 技能系统详解

每个技能包含：用途、适用场景、使用方法、实际案例、配合技能

1. **openspec-new-change** - 创建新变更
   - 用途：启动结构化的开发流程
   - 适用场景：新功能、复杂 bug 修复、代码重构
   - 命令：`openspec new change "<name>"`
   - 参数：`--schema <name>`（可选）
   - 案例：创建 `add-user-auth` 变更

2. **openspec-explore** - 探索模式
   - 用途：思考伙伴，探索想法、调查问题、澄清需求
   - 适用场景：需求不明确、面临多个方案、stuck 时
   - 重要：**不写代码**，只用于思考和捕获想法
   - 案例：探索认证方案（JWT vs Session vs OAuth）

3. **openspec-continue-change** - 继续变更
   - 用途：创建下一个 artifact
   - 产物顺序：proposal → specs/ → design → tasks
   - 案例：完成 proposal 后继续创建设计

4. **openspec-ff-change** - 快速创建
   - 用途：快速跳过所有 artifact 的创建
   - 适用场景：需求明确、时间紧张、有清晰思路
   - 案例：快速创建 `fix-login-bug` 变更的所有产物

5. **openspec-apply-change** - 实现任务
   - 用途：按照 tasks.md 逐一完成开发工作
   - 工作流程：读取任务 → 识别未完成 → 逐一实现
   - 案例：实现 `add-user-auth` 变更的所有任务

6. **openspec-archive-change** - 归档变更
   - 用途：归档已完成的变更
   - 前置条件：所有任务已完成
   - 案例：归档 `add-user-auth` 变更

7. **openspec-verify-change** - 验证变更
   - 用途：验证实现是否完整正确
   - 案例：归档前验证 `add-user-auth`

#### Part 3: 完整工作流示例

```
1. 需求不明确 → openspec-explore
2. 需求明确后 → openspec-new-change 或 openspec-ff-change
3. 创建产物 → openspec-continue-change（如需要）
4. 实现任务 → openspec-apply-change
5. 验证结果 → openspec-verify-change
6. 归档变更 → openspec-archive-change
```

**新增资源**:
- `openspec-skill-cheatsheet.md` - OpenSpec 技能速查表
- `proposal-template.md` - Proposal 模板
- `spec-template.md` - Spec 模板
- `design-template.md` - Design 模板
- `tasks-template.md` - Tasks 模板
- `complete-workflow-example.md` - 完整实战案例（从 new 到 archive）

**新增测验** (5 题):
1. 单选：OpenSpec 的核心理念
2. 多选：哪些场景适合使用 explore 模式
3. 匹配：技能与用途配对
4. 场景：选择正确的技能
5. 排序：正确的工作流顺序

---

### 第 5 章：对比思考 - 三大工具对比 ⚖️

**章节类型**: video

**核心内容**:
1. 完整对比表（保持现有内容）
2. 新增对比维度：
   - 学习成本（时间投入）
   - 社区支持（文档、示例、问题解答）
   - 扩展性（自定义能力）
   - 中文友好度
3. 工具选择决策树（保持现有内容）
4. 新增：迁移指南
   - 从 spec-kit 迁移到 OpenSpec
   - 从 Superpowers 迁移到 OpenSpec

**新增资源**:
- `tool-selection-decision-tree.pdf` - 工具选择决策树（可打印）
- `migration-guide.md` - 迁移指南

---

## 数据结构

### 课程数据 JSON 结构

```json
{
  "version": "1.0",
  "course_id": 4,
  "course_title": "OpenSpec VibeCoding 实践指南",
  "chapters": [
    {
      "slug": "intro-vibe-coding",
      "title": "第一章：最初的我 - 谨慎使用 AI 😰",
      "order": 1,
      "content": "...",
      "chapter_type": "story",
      "is_locked": false,
      "required_quiz_slug": "quiz-1-1",
      "quizzes": [...],
      "resources": [...]
    },
    // ... 其他章节
  ]
}
```

### 测验数据结构

```json
{
  "slug": "quiz-1-1",
  "title": "VibeCoding 入门测验",
  "passing_score": 60,
  "questions": [
    {
      "question_text": "...",
      "question_type": "single|mature",
      "correct_answer": "0,1,2",
      "explanation": "...",
      "order": 0,
      "options": [
        {
          "option_text": "...",
          "option_index": 0
        }
      ]
    }
  ]
}
```

### 资源数据结构

```json
{
  "resource_type": "template|code_sample|checklist|guide",
  "title": "...",
  "content": "...",
  "extra_data": {
    "template": "...",
    "download_url": "..."
  }
}
```

---

## 实施步骤

### 步骤 1: 准备阶段
1. 备份现有课程数据
2. 创建变更目录
3. 收集参考资料（现有技能文件、Spec 文件）

### 步骤 2: 内容创作
1. 逐章编写新内容
2. 创建测验题目
3. 创建资源文件

### 步骤 3: 验证阶段
1. 检查内容准确性
2. 验证测验答案
3. 预览导入效果

### 步骤 4: 导入阶段
1. 通过 API 预览导入
2. 确认导入结果
3. 执行导入

### 步骤 5: 验证阶段
1. 访问课程详情页面
2. 检查章节内容
3. 测试测验功能

---

## 成功标准

1. **内容完整性**: 5 章内容全部优化完成
2. **技术准确性**: OpenSpec 概念和技能描述准确
3. **实战导向**: 每章包含至少 1 个实战案例
4. **测验覆盖**: 每章至少 3 道测验题
5. **资源丰富**: 每章至少 2 个配套资源
6. **导入成功**: 能通过 API 成功导入到数据库

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 内容过多 | 课程过于冗长 | 保持中等深度，进阶内容放入延伸阅读 |
| 技术细节错误 | 误导学习者 | 参考官方文档和现有技能文件 |
| 导入失败 | 数据格式不兼容 | 先预览导入，确认无误再执行 |
| 测验太难 | 学习者挫败感 | 设置合理及格分数 (60%)，提供详细解析 |

---

## 时间估算

| 阶段 | 预计时间 |
|------|----------|
| 内容创作 | 4-6 小时 |
| 测验和资源 | 2-3 小时 |
| 验证和导入 | 1 小时 |
| **总计** | **7-10 小时** |

---

## 后续优化

1. 添加视频教程（第 4、5 章）
2. 增加实战练习项目
3. 添加学习者反馈收集
4. 定期更新 OpenSpec 新技能内容
