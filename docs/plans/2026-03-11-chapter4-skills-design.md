# 第四章设计文档：Skill 系统 - 提升 AI 编程效率的利器

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建第四章内容，介绍 Skill 的概念、用法、与 Rules 的区别，并推荐实用的技能工具。

**Architecture:** 延续课程的故事驱动风格，从开发者实际痛点出发，逐步引入 Skill 概念，通过对比 Rules 帮助理解，最后推荐实用技能工具。

**Tech Stack:** Markdown 文档，故事驱动内容，包含测验和资源文件。

---

## 内容大纲

### 4.1 故事：从 Rules 到 Skills 的进化

- 主角在使用 Rules 时的新困惑
- 发现 repetitive tasks 依然耗时
- 遇到 Skills 概念的契机

### 4.2 什么是 Skills？

- **定义**：Skills 是预定义的工作流和自动化能力
- **与 Rules 的核心区别**：
  - Rules = 行为规范（约束 AI 如何响应）
  - Skills = 能力扩展（赋予 AI 特定工作流）
- **类比理解**：
  - Rules 像是公司规章制度
  - Skills 像是专业工具或培训

### 4.3 Skills 的核心特点

| 特点 | Rules | Skills |
|------|-------|--------|
| **定位** | 约束规范 | 能力扩展 |
| **触发方式** | 自动应用 | 主动调用 |
| **内容** | 行为准则 | 工作流程 |
| **示例** | "用中文回复" | "brainstorming:探索需求" |

### 4.4 Skills 如何使用？

#### 基础用法

```bash
# 在对话中直接调用
/brainstorming 我想设计一个新功能...
/writing-plans 根据需求创建实现计划
```

#### 参数传递

```bash
# 带参数的技能调用
/openspec-new-change add-user-auth
/ui-ux-pro-max plan: 设计登录页面
```

### 4.5 面向前端开发者的实用 Skills

#### 1. ui-ux-pro-max
- **用途**：UI/UX 设计指导
- **适用场景**：设计页面、选择配色、字体搭配
- **示例调用**：
  ```bash
  /ui-ux-pro-max plan: SaaS 后台仪表盘
  ```

#### 2. frontend-design
- **用途**：生成高质量前端代码
- **适用场景**：创建组件、页面、仪表板
- **示例调用**：
  ```bash
  /frontend-design 实现一个带筛选的用户列表
  ```

#### 3. vercel-react-best-practices
- **用途**：React 性能优化
- **适用场景**：编写 React 组件、优化渲染
- **示例调用**：
  ```bash
  /vercel-react-best-practices 检查这个组件
  ```

### 4.6 面向后端开发者的实用 Skills

#### 1. writing-plans
- **用途**：创建详细实现计划
- **适用场景**：复杂功能开发、重构任务
- **示例调用**：
  ```bash
  /writing-plans 实现用户认证系统
  ```

#### 2. openspec-* 系列
- **用途**：Spec-Driven 开发工作流
- **适用场景**：规范化开发、团队协作
- **示例调用**：
  ```bash
  /openspec-new-change add-api-endpoint
  /opsx:ff 快速创建变更
  ```

#### 3. simplify
- **用途**：代码质量审查与优化
- **适用场景**：代码审查、重构优化
- **示例调用**：
  ```bash
  /simplify 审查这段代码
  ```

### 4.7 Skills 的最佳实践

#### DO's ✅
- 明确调用技能名称
- 提供清晰的任务描述
- 结合具体场景选择技能
- 允许多技能协作

#### DON'Ts ❌
- 不要同时调用多个冲突的技能
- 不要在简单任务上使用复杂技能
- 不要忘记技能也有适用范围

### 4.8 实战案例

#### 案例 1：开发一个新功能
```
1. /brainstorming 探索需求
2. /writing-plans 创建实现计划
3. /openspec-new-change 启动变更
4. /frontend-design 实现 UI
5. /simplify 代码审查
```

#### 案例 2：优化现有页面
```
1. /ui-ux-pro-max 获取设计建议
2. /vercel-react-best-practices 检查性能
3. /frontend-design 实现优化
```

### 4.9 小结与展望

- Skills 是效率工具，不是万能药
- 选择合适的技能解决合适的问题
- 结合 Rules 形成完整的工作流

---

## 测验设计

### 测验目标
- 理解 Skills 与 Rules 的核心区别
- 掌握 Skills 的基础用法
- 能根据场景选择合适的技能

### 问题设计（5 题）

1. **单选题**：Skills 和 Rules 的核心区别是什么？
   - 考察点：概念理解

2. **多选题**：以下哪些场景适合使用 Skills？
   - 考察点：应用场景识别

3. **单选题**：前端开发者设计页面时，首选哪个技能？
   - 考察点：技能选择

4. **单选题**：开发复杂功能时，应该先调用哪个技能？
   - 考察点：工作流程理解

5. **多选题**：以下哪些是 Skills 的正确使用方式？
   - 考察点：最佳实践

---

## 资源文件

### 资源 1：Skills 快速参考卡
- 常用技能列表
- 调用语法
- 适用场景速查

### 资源 2：Skills 与 Rules 对比表
- 详细对比表格
- 使用建议
- 常见误区

---

## 章节元数据

```json
{
  "slug": "skills-system-guide",
  "title": "第 4 章：Skill 系统 - 提升 AI 编程效率的利器",
  "order": 4,
  "chapter_type": "story",
  "required_quiz_slug": "quiz-4-1"
}
```

---

## 验证清单

- [ ] 内容风格与前面章节一致（故事驱动）
- [ ] Skills 与 Rules 的区别清晰易懂
- [ ] 推荐的技能工具实用且有针对性
- [ ] 测验题能有效检验学习效果
- [ ] 资源文件有实际参考价值
