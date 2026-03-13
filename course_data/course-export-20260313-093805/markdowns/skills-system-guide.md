---
slug: skills-system-guide
title: 第 4 章：Skill 系统 - 提升 AI 编程效率的利器
order: 4
chapter_type: story
is_locked: false
required_quiz_slug: quiz-skills-system-guide
---

## 故事：一次"偷懒"的发现

那是一个周三的下午，我正在为一个重复性的任务头疼...

### 事情的起因

当时我已经按照 Rules 配置好了所有规范：
- 代码用 TypeScript
- 回复用中文
- 要有注释和类型定义

但每次开发新功能时，我还是要重复同样的对话：

```
我：帮我设计一个用户登录功能
AI：好的，我来帮你。请问：
     1. 需要支持哪些登录方式？
     2. 是否需要记住登录状态？
     3. 错误处理有什么要求？
     ...
```

**每次！都要！重新！沟通！** 😫

### 转折点

直到有一天，我在一个开源项目的 README 里看到了一行奇怪的命令：

```bash
/brainstorming 设计一个用户认证系统
```

我很好奇，这是什么？

### 第一次尝试

抱着试一试的心态，我也输入了：

```
/brainstorming 我想设计一个用户登录功能，支持邮箱和密码，需要记住登录状态
```

这次，AI 的回应完全不一样了：

```
好的，我来帮你探索这个需求。让我们从几个维度分析：

## 需求分析

### 核心功能
1. 邮箱 + 密码登录
2. 记住登录状态（持久化会话）

### 需要澄清的问题
1. 是否需要第三方登录（Google/GitHub）？
2. 会话有效期多久？
3. 是否需要多设备登录？

### 技术建议
- 使用 JWT + Refresh Token 方案
- 前端使用 Zustand 管理认证状态
- 后端需要实现 token 刷新机制
```

**哇！** 这不仅仅是回答问题，这是一个完整的**需求探索流程**！ 🤯

### 发现新大陆

继续探索后，我发现这叫做 **Skill**（技能），它不是简单的对话，而是：

> **预定义的专业工作流**

就像给 AI 装备了"专业工具"，让它从"通用助手"变成"领域专家"。

---

## 什么是 Skills？

### 核心定义

**Skills（技能）** 是预定义的工作流和自动化能力，用于扩展 AI 在特定领域的专业能力。

### 与 Rules 的核心区别

这是最容易混淆的地方，让我们用类比来理解：

| 维度 | Rules（规则） | Skills（技能） |
|------|---------------|----------------|
| **定位** | 约束规范 | 能力扩展 |
| **触发方式** | 自动应用 | 主动调用 |
| **内容** | 行为准则 | 工作流程 |
| **持久性** | 配置文件 | 临时调用 |
| **类比** | 公司规章制度 | 专业工具/培训 |

### 类比理解

想象你在经营一家公司：

**Rules = 公司规章制度**
- "所有文件必须用中文书写"
- "代码必须有注释"
- "回复客户要礼貌"

这些是**约束行为规范**，自动适用于所有员工。

**Skills = 专业工具/培训**
- "市场调研工具箱"
- "财务分析培训"
- "设计规范手册"

这些是**扩展专业能力**，需要时主动使用。

### 实际例子对比

**使用 Rules：**
```yaml
# .clinerules 配置
- 所有代码使用 TypeScript
- 回复使用中文
- 代码要有详细注释
```
→ 每次对话都自动应用这些规范

**使用 Skills：**
```bash
/brainstorming 设计用户认证系统
/writing-plans 实现登录功能
```
→ 主动调用特定工作流

---

## Skills 如何使用？

### 基础语法

```bash
/skill-name 任务描述
```

### 调用示例

**1. 需求探索**
```bash
/brainstorming 我想设计一个用户管理系统
```

**2. 创建计划**
```bash
/writing-plans 实现用户登录功能
```

**3. 代码审查**
```bash
/simplify 审查这段代码的质量
```

### 带参数调用

某些技能支持参数：

```bash
# 指定变更名称
/openspec-new-change add-user-auth

# 指定设计目标
/ui-ux-pro-max plan: SaaS 后台仪表盘
```

### 多技能协作

复杂任务可以组合使用多个技能：

```bash
# 1. 探索需求
/brainstorming 设计用户认证系统

# 2. 创建计划
/writing-plans 根据上面的讨论创建实现计划

# 3. 启动变更
/openspec-new-change add-auth-system

# 4. 实现 UI
/frontend-design 实现登录页面

# 5. 代码审查
/simplify 审查认证模块的代码
```

---

## 面向前端开发者的实用 Skills

### 1. ui-ux-pro-max 🎨

**用途**：UI/UX 设计指导

**适用场景**：
- 设计新页面/组件
- 选择配色方案
- 字体搭配建议
- 响应式布局指导

**调用示例**：
```bash
/ui-ux-pro-max plan: SaaS 后台仪表盘
```

**返回内容**：
- 推荐的 UI 风格（如玻璃态、极简主义）
- 配色方案（含色值）
- 字体搭配建议
- 布局和组件指导

### 2. frontend-design 🏗️

**用途**：生成高质量前端代码

**适用场景**：
- 创建 React/Vue 组件
- 实现页面布局
- 仪表板设计
- 响应式调整

**调用示例**：
```bash
/frontend-design 实现一个带筛选和分页的用户列表
```

**返回内容**：
- 完整的组件代码
- TypeScript 类型定义
- Tailwind CSS 样式
- 交互逻辑实现

### 3. vercel-react-best-practices ⚡

**用途**：React 性能优化

**适用场景**：
- 检查组件性能
- 优化渲染逻辑
- Bundle 优化建议
- Next.js 最佳实践

**调用示例**：
```bash
/vercel-react-best-practices 检查这个组件是否有性能问题
```

---

## 面向后端开发者的实用 Skills

### 1. writing-plans 📋

**用途**：创建详细实现计划

**适用场景**：
- 复杂功能开发
- 系统重构
- API 设计
- 数据库迁移

**调用示例**：
```bash
/writing-plans 实现用户认证系统
```

**返回内容**：
- 分任务的详细计划
- 每个任务的文件路径
- 完整的代码示例
- 测试步骤和验证命令

### 2. openspec-* 系列 🔄

**用途**：Spec-Driven 开发工作流

**核心技能**：
| 技能 | 用途 |
|------|------|
| `/openspec-new-change` | 启动新变更 |
| `/opsx:ff` | 快速创建变更（跳过中间步骤） |
| `/opsx:apply` | 实现变更任务 |
| `/opsx:continue` | 继续下一个任务 |
| `/opsx:verify` | 验证实现是否正确 |
| `/opsx:archive` | 归档完成的变更 |

**调用示例**：
```bash
/openspec-new-change add-user-api
```

**返回内容**：
- 变更目录结构
- 待创建的 artifacts
- 每个 artifact 的指令

### 3. simplify 🔍

**用途**：代码质量审查与优化

**适用场景**：
- 代码审查
- 重构优化
- 发现潜在问题
- 提升代码质量

**调用示例**：
```bash
/simplify 审查这段认证代码
```

**返回内容**：
- 代码质量评估
- 可优化的点
- 具体修改建议
- 重构后的代码

---

## 最佳实践

### ✅ DO's（推荐做法）

1. **明确调用技能名称**
   ```bash
   /brainstorming 我想...  # ✅ 好
   帮我...                 # ❌ 没有调用技能
   ```

2. **提供清晰的任务描述**
   ```bash
   /writing-plans 实现用户登录，支持邮箱密码和 JWT  # ✅ 具体
   /writing-plans 做个登录                          # ❌ 模糊
   ```

3. **结合具体场景选择技能**
   - 需求不明确 → `/brainstorming`
   - 需要计划 → `/writing-plans`
   - UI 设计 → `/ui-ux-pro-max`
   - 代码审查 → `/simplify`

4. **允许多技能协作**
   ```bash
   # 完整工作流
   /brainstorming → /writing-plans → /openspec-new-change
   ```

### ❌ DON'Ts（避免做法）

1. **不要同时调用多个冲突的技能**
   ```bash
   # ❌ 不要这样
   /brainstorming /writing-plans 同时执行
   ```

2. **不要在简单任务上使用复杂技能**
   ```bash
   # ❌ 杀鸡用牛刀
   /writing-plans 帮我写个 hello world 函数
   ```

3. **不要忘记技能也有适用范围**
   ```bash
   # ❌ 用错场景
   /ui-ux-pro-max 帮我设计数据库 schema
   ```

---

## 实战案例

### 案例 1：开发一个新功能

**场景**：需要实现用户认证系统

**工作流**：

```bash
# Step 1: 探索需求
/brainstorming 我想实现用户认证系统，支持邮箱登录和 JWT

# Step 2: 创建实现计划
/writing-plans 根据上面的需求创建详细的实现计划

# Step 3: 启动变更
/openspec-new-change add-auth-system

# Step 4: 实现 UI 组件
/frontend-design 实现登录页面和注册页面

# Step 5: 代码审查
/simplify 审查认证模块的代码质量
```

**预期结果**：
- 需求清晰明确
- 计划详细可执行
- 代码规范统一
- 质量有保障

### 案例 2：优化现有页面

**场景**：仪表盘页面加载慢，需要优化

**工作流**：

```bash
# Step 1: 获取设计建议
/ui-ux-pro-max 优化这个仪表盘的加载体验

# Step 2: 检查性能问题
/vercel-react-best-practices 检查组件性能问题

# Step 3: 实现优化
/frontend-design 实现骨架屏和懒加载
```

**预期结果**：
- 加载体验改善
- 渲染性能提升
- 用户体验优化

### 案例 3：API 开发标准化

**场景**：团队需要统一的 API 开发流程

**工作流**：

```bash
# Step 1: 启动变更（使用 fast-forward 模式）
/opsx:ff add-user-crud-api

# Step 2: 应用变更
/opsx:apply add-user-crud-api

# Step 3: 验证实现
/opsx:verify add-user-crud-api
```

**预期结果**：
- 开发流程标准化
- 代码风格统一
- 文档自动生成

---

## 小结与展望

### 核心要点

1. **Skills vs Rules**
   - Rules = 约束规范（自动应用）
   - Skills = 能力扩展（主动调用）

2. **Skills 的价值**
   - 提供结构化工作流
   - 扩展专业领域能力
   - 减少重复沟通

3. **使用原则**
   - 明确调用技能名称
   - 选择适合场景的技能
   - 避免过度使用

### 进阶学习

本章介绍的是 Skills 的基础概念和常用技能。在后续章节中，我们会深入探讨：

- **第 5 章**：OpenSpec 技能系统详解（Spec-Driven 开发实践）
- **第 6 章**：三大工具对比（Rules vs OpenSpec vs 对话驱动）

### 下一步行动

1. **尝试调用一个技能**：选一个你当前需要的技能，现在就试试
2. **观察效果**：对比使用技能前后的差异
3. **形成习惯**：把常用技能加入你的工作流

---

**下一章**：我们会深入 OpenSpec 技能系统，了解 Spec-Driven 开发的完整实践！


---

## 测验：Skill 系统测验

**及格分数**: 60


### 问题 1

【场景】对比两种工作流程：

流程 A（无 Skills）：
用户：帮我设计一个用户登录功能
AI：好的，请问需要支持哪些登录方式？
用户：邮箱和密码
AI：需要记住登录状态吗？
用户：需要
AI：错误处理有什么要求？
用户：...（来回沟通 10 轮）

流程 B（使用 Skills）：
用户：/brainstorming 设计一个用户登录功能，支持邮箱和密码，需要记住登录状态
AI：好的，我来帮你探索这个需求。让我们从几个维度分析：
1. 认证流程设计
2. 安全性考虑
3. 会话管理
...（一次性输出完整分析）

问题：流程 B 的优势是什么？
- [ ] 流程 B 更省时间，因为 AI 回答更快
- [x] Skills 通过预设框架让 AI 一次性输出结构化分析，避免重复沟通
- [ ] 流程 A 太笨了，AI 学不会
- [ ] 流程 B 看起来更高级

**答案**: 1
**解析**: Skills 通过预设的框架和流程，让 AI 一次性输出结构化、全面的分析，避免了重复沟通。这是 Skill 系统的核心价值。


### 问题 2

【诊断】前端开发者设计新页面时，以下技能调用顺序哪个是正确的？
- [ ] /implement → /design → /write-prd → /brainstorming
- [x] /brainstorming → /write-prd → /design → /implement
- [ ] /design → /implement → /brainstorming → /write-prd
- [ ] 顺序不重要，可以随意调用

**答案**: 1
**解析**: 正确的顺序是：/brainstorming（探索需求）→ /write-prd（定义需求）→ /design（技术方案）→ /implement（实现）。这个顺序符合软件开发的自然流程。


### 问题 3

【决策】开发复杂功能时，正确的技能调用策略是？
- [ ] 直接/implement，效率最高
- [ ] 只用/brainstorming，其他不重要
- [x] 按流程逐步推进：探索→定义→设计→实现
- [ ] 所有技能一起调用，让 AI 自己决定

**答案**: 2
**解析**: 对于复杂功能，应该按照 Skill 系统设计的流程逐步推进：探索→定义→设计→实现。每个阶段都有其特定价值，跳过任何阶段都可能导致问题。


---

## 资源


### Skills 与 Rules 对比表

**类型**: template

# Skills vs Rules 对比表

## 核心区别

| 维度 | Rules | Skills |
|------|-------|--------|
| **定位** | 约束规范 | 能力扩展 |
| **触发方式** | 自动应用 | 主动调用 |
| **内容** | 行为准则 | 工作流程 |
| **持久性** | 配置文件 | 临时调用 |
| **示例** | "用中文回复" | "/brainstorming ..." |

## 使用场景对比

| 场景 | 推荐方式 | 原因 |
|------|----------|------|
| 统一回复语言 | Rules | 全局适用，无需每次指定 |
| 代码风格规范 | Rules | 约束所有输出格式 |
| 需求探索 | Skills | 需要结构化工作流 |
| 实现计划 | Skills | 需要多步骤分析 |
| UI 设计 | Skills | 需要专业设计知识 |
| 代码审查 | Skills | 需要系统化检查 |

## 配合使用示例

```bash
# Rules 配置（.clinerules）
- 所有代码必须使用 TypeScript
- 回复使用中文
- 代码要有注释

# 对话中调用 Skills
/brainstorming 我想实现用户认证功能
/writing-plans 根据需求创建详细计划
```

## 常见误区

| 误区 | 正确做法 |
|------|----------|
| Rules 和 Skills 混为一谈 | 理解它们是不同概念 |
| 所有事都用 Rules 解决 | 复杂任务使用 Skills |
| 所有事都调用 Skills | 简单规则配置到 Rules |
| 同时调用多个冲突技能 | 一次专注于一个技能 |

## 决策树

```
需要 AI 做什么？
│
├─ 约束行为规范？
│  └─ 使用 Rules（配置到.clinerules）
│
└─ 完成特定任务？
   │
   ├─ 简单问答？
   │  └─ 直接对话，不需要 Skills
   │
   └─ 复杂工作流？
      └─ 使用 Skills（主动调用）
         ├─ 需求探索 → /brainstorming
         ├─ 创建计划 → /writing-plans
         ├─ UI 设计 → /ui-ux-pro-max
         ├─ 前端开发 → /frontend-design
         ├─ 代码审查 → /simplify
         └─ 规范开发 → /openspec-new-change
```


### Skills 快速参考卡

**类型**: template

# Skills 快速参考卡

## 通用技能

| 技能名称 | 用途 | 调用示例 |
|----------|------|----------|
| brainstorming | 探索需求、设计思路 | `/brainstorming 我想设计...` |
| writing-plans | 创建实现计划 | `/writing-plans 实现用户认证` |
| simplify | 代码审查优化 | `/simplify 审查这段代码` |

## 前端技能

| 技能名称 | 用途 | 调用示例 |
|----------|------|----------|
| ui-ux-pro-max | UI/UX 设计指导 | `/ui-ux-pro-max plan: SaaS 仪表盘` |
| frontend-design | 生成前端代码 | `/frontend-design 实现用户列表` |
| vercel-react-best-practices | React 性能优化 | `/vercel-react-best-practices 检查组件` |

## 后端技能

| 技能名称 | 用途 | 调用示例 |
|----------|------|----------|
| openspec-new-change | 启动新变更 | `/openspec-new-change add-api` |
| opsx:ff | 快速创建变更 | `/opsx:ff add-feature` |
| opsx:apply | 实现变更任务 | `/opsx:apply change-name` |
| opsx:continue | 继续下一个任务 | `/opsx:continue change-name` |
| opsx:verify | 验证实现 | `/opsx:verify change-name` |
| opsx:archive | 归档变更 | `/opsx:archive change-name` |

## 调用语法

```bash
# 基础调用
/skill-name 任务描述

# 带参数调用
/skill-name param:value 任务描述

# 多技能协作
1. /brainstorming 探索需求
2. /writing-plans 创建计划
3. /openspec-new-change 启动变更
4. /frontend-design 实现 UI
5. /simplify 代码审查
```

## 最佳实践

### ✅ DO's
- 明确调用技能名称
- 提供清晰的任务描述
- 结合具体场景选择技能
- 允许多技能协作

### ❌ DON'Ts
- 不要同时调用冲突的技能
- 不要在简单任务上使用复杂技能
- 不要忘记技能也有适用范围
