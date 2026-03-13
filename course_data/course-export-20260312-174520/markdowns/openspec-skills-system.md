---
slug: openspec-skills-system
title: 第 5 章：OpenSpec 技能系统 - Spec-Driven 开发实践
order: 5
chapter_type: code
is_locked: true
required_quiz_slug: quiz-openspec-skills-system
---

## 发现新大陆：OpenSpec！

在我掌握了 skill 之后，我又发现了一个更强大的工具——**OpenSpec**。

### 什么是 OpenSpec？

OpenSpec 是一个基于 Spec-Driven 的开发方法论，它提供了一套完整的技能系统来规范 AI 的编程行为。

**核心理念**：

1. **Spec-Driven（规格驱动）**：先写清楚规格，再开始实现
2. **Change-Based（变更驱动）**：每个变更都是独立的单元
3. **Artifact-Driven（工件驱动）**：通过创建工件来推进开发

### OpenSpec 的核心概念

#### 1. Change（变更）

Change 是 OpenSpec 中的基本单位，代表一个独立的开发任务。

```
openspec/changes/
└── add-user-auth/          # 一个 Change
    ├── proposal.md         # 提案
    ├── design.md           # 设计
    ├── specs/              # 规格
    │   └── auth-spec/
    │       └── spec.md
    └── tasks.md            # 任务清单
```

#### 2. Artifact（工件）

Artifact 是 OpenSpec 中创建的文档或文件，包括：

| 工件类型 | 用途 | 内容 |
|----------|------|------|
| **Proposal** | 提案 | 为什么要做、做什么、预期影响 |
| **Design** | 设计 | 技术方案、权衡考虑、风险评估 |
| **Spec** | 规格 | 详细的功能规格和场景 |
| **Tasks** | 任务 | 具体的实现步骤清单 |

#### 3. Spec-Driven Workflow

OpenSpec 的工作流程：

```
Proposal → Design → Specs → Tasks → Implementation
```

每个阶段都有明确的目标和输出。

### OpenSpec 技能系统

OpenSpec 提供了一套强大的技能（Skills），每个技能对应一个特定的操作：

#### 1. openspec-new-change

**用途**：创建新的变更

**适用场景**：
- 开始一个新功能开发
- 修复一个 bug
- 进行代码重构

**常用命令**：
```bash
openspec new change <change-name>
```

**示例**：
```bash
# 创建一个添加用户认证功能的变更
openspec new change add-user-auth
```

#### 2. openspec-explore

**用途**：探索模式，用于思考和分析

**适用场景**：
- 探索问题空间
- 收集需求
- 分析技术方案

**常用命令**：
```bash
openspec explore
openspec explore --change <change-name>
```

**示例**：
```bash
# 探索用户认证方案
openspec explore --change add-user-auth
```

#### 3. openspec-continue-change

**用途**：继续一个变更，创建下一个工件

**适用场景**：
- 完成 proposal 后继续创建 design
- 完成 design 后继续创建 specs

**常用命令**：
```bash
openspec continue change <change-name>
```

**示例**：
```bash
# 继续 add-user-auth 变更，创建下一个工件
openspec continue change add-user-auth
```

#### 4. openspec-ff-change

**用途**：快速向前推进变更，自动创建所有工件

**适用场景**：
- 快速原型开发
- 熟悉的任务类型
- 时间紧迫时

**常用命令**：
```bash
openspec ff change <change-name>
```

**示例**：
```bash
# 快速推进变更，自动生成所有工件
openspec ff change add-simple-feature
```

#### 5. openspec-apply-change

**用途**：应用变更，开始实现

**适用场景**：
- 所有工件准备就绪
- 开始编写代码

**常用命令**：
```bash
openspec apply change <change-name>
```

**示例**：
```bash
# 应用变更，开始实现
openspec apply change add-user-auth
```

#### 6. openspec-archive-change

**用途**：归档完成的变更

**适用场景**：
- 变更已完成
- 清理工作区

**常用命令**：
```bash
openspec archive change <change-name>
```

**示例**：
```bash
# 归档已完成的变更
openspec archive change add-user-auth
```

#### 7. openspec-verify-change

**用途**：验证变更实现

**适用场景**：
- 实现完成后
- 确保实现符合规格

**常用命令**：
```bash
openspec verify change <change-name>
```

**示例**：
```bash
# 验证变更实现是否符合规格
openspec verify change add-user-auth
```

### 完整工作流示例

下面是一个完整的 OpenSpec 工作流示例：

```bash
# 1. 创建新变更
openspec new change add-user-auth

# 2. 查看变更状态
openspec status --change add-user-auth

# 3. 获取 Proposal 指令
openspec instructions proposal --change add-user-auth

# 4. 创建 Proposal（手动编写）
# 编辑 openspec/changes/add-user-auth/proposal.md

# 5. 继续创建 Design
openspec continue change add-user-auth

# 6. 创建 Specs
openspec continue change add-user-auth

# 7. 创建 Tasks
openspec continue change add-user-auth

# 8. 应用变更（开始实现）
openspec apply change add-user-auth

# 9. 验证实现
openspec verify change add-user-auth

# 10. 归档变更
openspec archive change add-user-auth
```

### OpenSpec 带来的提升

使用 OpenSpec 后，我的开发效率有了显著提升：

| 指标 | 之前 | 使用 OpenSpec 后 | 提升 |
|------|------|-----------------|------|
| **需求理解时间** | 30 分钟 | 10 分钟 | ⬆️ 66% |
| **返工率** | 40% | 10% | ⬇️ 75% |
| **代码审查时间** | 45 分钟 | 15 分钟 | ⬆️ 66% |
| **整体交付速度** | 基准 | 2.5 倍 | ⬆️ 150% |

### 为什么 OpenSpec 有效？

1. **清晰的规格**：AI 确切知道要做什么
2. **结构化的流程**：每个阶段都有明确目标
3. **可追溯的变更**：每个变更都有完整记录
4. **可复用的模式**：成功的模式可以重复使用

---

**动手试试**：下一章我们会对比三大主流 AI 编程工具！

---

## 测验：OpenSpec 技能测验

**及格分数**: 60


### 问题 1

OpenSpec 的核心理念是什么？
- [ ] 快速编码，尽快交付
- [x] Spec-Driven、Change-Based、Artifact-Driven
- [ ] 测试驱动开发
- [ ] 敏捷开发

**答案**: 1
**解析**: OpenSpec 的核心理念是 Spec-Driven（规格驱动）、Change-Based（变更驱动）、Artifact-Driven（工件驱动）。


### 问题 2

以下哪些场景适合使用 explore 模式？（多选）
- [x] 探索问题空间
- [x] 收集需求
- [ ] 紧急 bug 修复
- [x] 分析技术方案

**答案**: 0,1,3
**解析**: explore 模式适用于探索问题空间、收集需求和分析技术方案，不适合紧急修复。


### 问题 3

以下哪个技能用于快速向前推进变更，自动创建所有工件？
- [ ] openspec-new-change
- [ ] openspec-continue-change
- [x] openspec-ff-change
- [ ] openspec-apply-change

**答案**: 2
**解析**: openspec-ff-change 用于快速推进变更，自动生成所有工件。


### 问题 4

当你想要开始实现代码时，应该使用哪个技能？
- [ ] openspec-new-change
- [ ] openspec-explore
- [ ] openspec-verify-change
- [x] openspec-apply-change

**答案**: 3
**解析**: openspec-apply-change 用于应用变更，开始实现代码。


### 问题 5

OpenSpec 工作流的正确顺序是什么？
- [ ] Design → Proposal → Tasks → Specs → Implementation
- [x] Proposal → Design → Specs → Tasks → Implementation
- [ ] Tasks → Specs → Design → Proposal → Implementation
- [ ] Implementation → Tasks → Specs → Design → Proposal

**答案**: 1
**解析**: OpenSpec 的正确工作流是 Proposal → Design → Specs → Tasks → Implementation。


---

## 资源


### Spec 模板合集

**类型**: template

## Spec 模板合集

### Proposal 模板

```markdown
# Proposal: [变更名称]

## Why

为什么要做这个变更？解决什么问题？

## What Changes

具体要做什么改动？

## Capabilities

新增哪些能力？

## Impact

预期带来什么影响？
```

### Design 模板

```markdown
# Design: [变更名称]

## Context

当前背景和现状。

## Goals

目标和范围。

## Decisions

关键决策和权衡考虑。

## Risks

潜在风险和应对方案。
```

### Spec 模板

```markdown
# Spec: [规格名称]

## Requirements

- Requirement 1
- Requirement 2

## Scenarios

### Scenario: [场景名称]
- WHEN [条件]
- THEN [结果]
```

### Tasks 模板

```markdown
# Tasks: [变更名称]

## Task 1: [任务名称]

**Files:**
- Create: `path/to/file.py`
- Modify: `path/to/file.py:10-20`

**Steps:**
1. [步骤 1]
2. [步骤 2]
3. [步骤 3]
```

### Rules 模板

```markdown
# AI 助手行为规范

## [类别名称]

1. **规则 1**：规则内容
2. **规则 2**：规则内容
```

**元数据**:
```json
{
  "template_type": "spec_templates"
}
```


### OpenSpec 完整工作流示例

**类型**: template

## OpenSpec 完整工作流示例

### 场景：添加用户认证功能

#### 步骤 1：创建新变更
```bash
openspec new change add-user-auth
```

#### 步骤 2：查看变更状态
```bash
openspec status --change add-user-auth
```
输出：
```
Change: add-user-auth
Status: 0/4 artifacts complete

Artifacts:
- [ ] proposal (ready)
- [ ] design (waiting)
- [ ] specs (waiting)
- [ ] tasks (waiting)
```

#### 步骤 3：获取 Proposal 指令
```bash
openspec instructions proposal --change add-user-auth
```

#### 步骤 4：创建 Proposal
编辑 `openspec/changes/add-user-auth/proposal.md`：
```markdown
# Proposal: Add User Authentication

## Why

为什么要做这个变更？解决什么问题？

## What Changes

具体要做什么改动？

## Capabilities

新增哪些能力？

## Impact

预期带来什么影响？
```

#### 步骤 5：继续创建 Design
```bash
openspec continue change add-user-auth
```

#### 步骤 6：创建 Specs
```bash
openspec continue change add-user-auth
```

#### 步骤 7：创建 Tasks
```bash
openspec continue change add-user-auth
```

#### 步骤 8：应用变更
```bash
openspec apply change add-user-auth
```

#### 步骤 9：验证实现
```bash
openspec verify change add-user-auth
```

#### 步骤 10：归档变更
```bash
openspec archive change add-user-auth
```

**元数据**:
```json
{
  "template_type": "workflow_example"
}
```


### OpenSpec 技能速查表

**类型**: template

## OpenSpec 技能速查表

### openspec-new-change
- **用途**：创建新的变更
- **适用场景**：新功能开发、bug 修复、代码重构
- **命令**：`openspec new change <change-name>`

### openspec-explore
- **用途**：探索模式，思考和分析
- **适用场景**：探索问题空间、收集需求、分析技术方案
- **命令**：`openspec explore --change <change-name>`

### openspec-continue-change
- **用途**：继续变更，创建下一个工件
- **适用场景**：完成 proposal 后继续创建 design
- **命令**：`openspec continue change <change-name>`

### openspec-ff-change
- **用途**：快速推进变更，自动创建所有工件
- **适用场景**：快速原型、熟悉的任务、时间紧迫
- **命令**：`openspec ff change <change-name>`

### openspec-apply-change
- **用途**：应用变更，开始实现
- **适用场景**：工件准备就绪，开始编写代码
- **命令**：`openspec apply change <change-name>`

### openspec-archive-change
- **用途**：归档完成的变更
- **适用场景**：变更已完成，清理工作区
- **命令**：`openspec archive change <change-name>`

### openspec-verify-change
- **用途**：验证变更实现
- **适用场景**：实现完成后，确保符合规格
- **命令**：`openspec verify change <change-name>`

**元数据**:
```json
{
  "cheatsheet_type": "openspec_skills"
}
```
