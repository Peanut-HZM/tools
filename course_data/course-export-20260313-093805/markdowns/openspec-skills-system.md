---
slug: openspec-skills-system
title: 第 5 章：OpenSpec 技能系统 - Spec-Driven 开发实践
order: 5
chapter_type: code
is_locked: true
required_quiz_slug: quiz-openspec-skills-system
---

## 发现新大陆：OpenSpec！

在我掌握了 Rules 之后，新的问题又出现了...

### 新的挑战

即使有了 Rules，我仍然面临这些问题：

| 问题 | 场景 | 痛点 |
|------|------|------|
| **需求不清晰** | AI 经常理解错需求，实现偏离目标 | 反复沟通，浪费时间 |
| **上下文丢失** | 长对话后 AI 忘记之前的约定 | 需要反复重申要求 |
| **变更混乱** | 多个功能同时开发，代码改动混在一起 | 难以追溯，难以回滚 |
| **缺乏文档** | 实现完成后不知道当时为什么这样设计 | 后续维护困难 |

直到我发现了 **OpenSpec** —— 一个改变我开发方式的 Spec-Driven 框架。

---

## 1. OpenSpec 是什么？

### 核心理念

OpenSpec 是一个基于 **Spec-Driven（规格驱动）** 的开发方法论，由 Fission AI 开发，旨在让 AI 辅助编程更加可预测和高效。

**三大核心理念**：

```
→ fluid not rigid        (灵活而非僵化)
→ iterative not waterfall (迭代而非瀑布)
→ easy not complex       (简单而非复杂)
```

### OpenSpec vs 传统开发

| 传统开发 | OpenSpec 开发 |
|----------|---------------|
| 需求在聊天记录中 | 需求在结构化文档中 |
| AI 直接写代码 | AI 先写规格，再实现 |
| 变更难以追溯 | 每个变更独立管理 |
| 文档滞后于代码 | 文档驱动代码实现 |

### OpenSpec 的核心价值

1. **Agree before you build（实现前先达成共识）**
   - 人类和 AI 在写代码前就规格达成一致
   - 避免"我以为你想要..."的情况

2. **Stay organized（保持组织性）**
   - 每个变更都有独立的文件夹
   - 包含 Proposal、Specs、Design、Tasks

3. **Work fluidly（灵活工作）**
   - 没有僵化的阶段限制
   - 可以随时更新任何文档

4. **Use your tools（使用你的工具）**
   - 支持 20+ AI 助手
   - 通过 Slash Commands 集成

---

## 2. Spec-Driven 工作原理

### 什么是 Spec-Driven？

**Spec-Driven（规格驱动）** 是一种开发方法，核心流程是：

```
Proposal（提案） → Design（设计） → Specs（规格） → Tasks（任务） → Implementation（实现）
```

每个阶段都有明确的输入和输出：

| 阶段 | 输入 | 输出 | 目的 |
|------|------|------|------|
| **Proposal** | 想法/需求 | proposal.md | 说明为什么要做、做什么、预期影响 |
| **Design** | Proposal | design.md | 技术方案、权衡考虑、风险评估 |
| **Specs** | Design | specs/*.md | 详细的功能规格和场景 |
| **Tasks** | Specs | tasks.md | 具体的实现步骤清单 |
| **Implementation** | Tasks | 代码 | 按照任务清单实现功能 |

### Spec-Driven 的优势

**传统方式（Prompt-Driven）**：
```
用户："帮我加个登录功能"
AI：直接开始写代码
结果：代码可能不符合预期，需要反复修改
```

**Spec-Driven 方式**：
```
用户："帮我加个登录功能"
AI：先创建 Proposal → Design → Specs → Tasks
用户：确认规格
AI：再开始实现
结果：实现符合预期，返工率低
```

### Spec-Driven 为什么有效？

1. **清晰的规格**：AI 确切知道要做什么
2. **结构化的流程**：每个阶段都有明确目标
3. **可追溯的变更**：每个变更都有完整记录
4. **可复用的模式**：成功的模式可以重复使用

---

## 3. 安装与初始化

### 3.1 安装 OpenSpec

**前提条件**：Node.js 20.19.0 或更高版本

```bash
# 检查 Node.js 版本
node --version

# 使用 npm 安装（推荐）
npm install -g @fission-ai/openspec@latest

# 或使用 pnpm
pnpm add -g @fission-ai/openspec@latest

# 或使用 bun
bun add -g @fission-ai/openspec@latest

# 验证安装
openspec --version
```

### 3.2 项目初始化

安装完成后，在项目根目录运行：

```bash
cd your-project
openspec init
```

`openspec init` 会：
1. 创建 `openspec/` 目录结构
2. 生成 AI 助手指令文件（Skills）
3. 创建示例配置文件

### 3.3 启用扩展工作流命令

OpenSpec 默认使用 **core profile**，只包含基础命令：
- `/opsx:propose`
- `/opsx:explore`
- `/opsx:apply`
- `/opsx:archive`

**如需使用扩展命令**（`/opsx:new`、`/opsx:continue`、`/opsx:ff`、`/opsx:verify`、`/opsx:sync`、`/opsx:bulk-archive`、`/opsx:onboard`），需要手动启用：

```bash
# 步骤 1：配置 profile
openspec config profile

# 步骤 2：选择 workflows（展开工作流）
# 在交互式提示中选择 "workflows" 或自定义

# 步骤 3：更新项目
openspec update
```

更新后，AI 助手中会出现扩展命令的 skills 文件。

### 3.4 目录结构详解

```
your-project/
├── openspec/
│   ├── specs/              # 规格目录（系统的"源代码"）
│   │   ├── auth/           # 按领域组织
│   │   │   └── spec.md
│   │   ├── payments/
│   │   │   └── spec.md
│   │   └── ui/
│   │       └── spec.md
│   ├── changes/            # 变更目录（待实施的工作）
│   │   └── add-dark-mode/  # 每个变更一个文件夹
│   │       ├── proposal.md # 为什么要做、做什么
│   │       ├── design.md   # 技术方案
│   │       ├── tasks.md    # 实施清单
│   │       └── specs/      # Delta specs（变更的规格）
│   │           └── ui/
│   │               └── spec.md
│   ├── config.yaml         # 项目配置（可选）
│   └── schemas/            # 自定义 schema（可选）
│       └── my-workflow/
│           ├── schema.yaml
│           └── templates/
└── src/                    # 你的代码
```

**核心目录说明**：

| 目录 | 作用 | 说明 |
|------|------|------|
| `specs/` | 系统规格 | 描述系统当前行为的"源代码"，按领域组织 |
| `changes/` | 变更工作区 | 每个变更一个文件夹，完成后合并到 specs/ |
| `config.yaml` | 项目配置 | 可选，设置默认 schema、注入项目上下文 |
| `schemas/` | 自定义工作流 | 可选，定义团队专属的工作流 |

**Artifact 文件说明**：

| 文件 | 作用 | 内容 |
|------|------|------|
| `proposal.md` | 提案 | 为什么要做、做什么、预期影响 |
| `design.md` | 设计 | 技术方案、权衡考虑、架构决策 |
| `tasks.md` | 任务清单 | 实施步骤，带复选框 |
| `specs/` | Delta 规格 | 新增/修改/删除的规格 |

---

## 4. 核心命令详解

OpenSpec 提供了一套完整的技能系统（Skills），每个技能对应一个特定的操作。

### 4.1 openspec-new-change

**用途**：创建新的变更

**适用场景**：
- 开始一个新功能开发
- 修复一个 bug
- 进行代码重构

**命令语法**：
```bash
openspec new change <change-name>
openspec new change <change-name> --schema <schema-name>
```

**参数说明**：
| 参数 | 必填 | 说明 |
|------|------|------|
| `change-name` | 否 | 变更名称（推荐使用 kebab-case 格式） |
| `--schema` | 否 | 使用的 Schema 名称（默认从配置读取） |

**示例**：
```bash
# 创建一个添加用户认证功能的变更
openspec new change add-user-auth

# 使用自定义 schema
openspec new change add-payment --schema payment-feature
```

**创建后的目录结构**：
```
openspec/changes/add-user-auth/
└── .openspec.yaml    # 变更元数据
```

**使用技巧**：
- 使用描述性名称：`add-feature`、`fix-bug`、`refactor-module`
- 避免通用名称：`update`、`changes`、`wip`

---

### 4.2 openspec-explore

**用途**：探索模式，用于思考和分析

**适用场景**：
- 探索问题空间
- 收集需求
- 分析技术方案
- 调查代码库

**命令语法**：
```bash
openspec explore
openspec explore --change <change-name>
```

**示例**：
```bash
# 探索用户认证方案
openspec explore --change add-user-auth

# 探索：如何处理移动端的认证？
openspec explore

AI: 你想探索什么？

你：移动端认证应该如何处理？

AI: 让我调查一下当前的认证设置...
     [分析代码库]

     我看到 Web 端使用基于会话的认证。
     移动端有三种主要选择：

     1. JWT 令牌（无状态，可离线工作）
     2. OAuth2（如需第三方登录）
     3. 扩展现有会话（更简单，但需要连接）

     你的 API 已配置 CORS。哪种方案你更感兴趣？
```

**使用技巧**：
- 适用于需求不清晰或需要调查的场景
- 探索阶段不会创建任何文档
- 适合比较多种方案后再做决定
- 可以读取文件和搜索代码库

---

### 4.3 openspec-continue-change

**用途**：继续变更，创建下一个工件

**适用场景**：
- 完成 proposal 后继续创建 design
- 完成 design 后继续创建 specs
- 逐步创建工件，每次审查后再继续

**命令语法**：
```bash
openspec continue change <change-name>
```

**示例**：
```bash
# 继续 add-user-auth 变更
openspec continue change add-user-auth

AI: 变更：add-user-auth

     工件状态：
     ✓ proposal    (已完成)
     ◆ specs       (就绪)
     ◆ design      (就绪)
     ○ tasks       (阻塞 - 需要：specs)

     正在创建 specs...

     ✓ 创建了 openspec/changes/add-user-auth/specs/ui/spec.md

     现在可用：tasks
     运行 /openspec-continue-change 创建下一个工件。
```

**使用技巧**：
- 适用于想要审查每个工件后再继续的场景
- 适合复杂变更，需要精细控制
- 多个工件可能同时就绪
- 可以在继续前编辑已创建的工件

---

### 4.4 openspec-ff-change

**用途**：快速向前推进变更，自动创建所有工件

**适用场景**：
- 快速原型开发
- 熟悉的任务类型
- 时间紧迫时
- 需求明确的简单功能

**命令语法**：
```bash
openspec ff change <change-name>
```

**示例**：
```bash
# 快速推进变更
openspec ff change add-dark-mode

AI: 快速推进 add-dark-mode...

     ✓ 创建 proposal.md
     ✓ 创建 specs/ui/spec.md
     ✓ 创建 design.md
     ✓ 创建 tasks.md

     所有工件创建完成！
     准备实现。运行 /openspec-apply-change 开始。
```

**使用技巧**：
- 适用于对实现内容有清晰想法的场景
- 比 `/openspec-continue-change` 更快
- 创建后仍可编辑工件
- 适合中小型功能

---

### 4.5 openspec-apply-change

**用途**：应用变更，开始实现代码

**适用场景**：
- 所有工件准备就绪
- 开始编写代码
- 继续未完成的实现

**命令语法**：
```bash
openspec apply change <change-name>
```

**示例**：
```bash
# 应用变更
openspec apply change add-user-auth

AI: 正在实现 add-user-auth...

     读取 tasks.md:
     - [ ] 1.1 创建 ThemeContext
     - [ ] 1.2 添加 CSS 自定义属性
     - [ ] 1.3 实现 localStorage 持久化

     正在处理 1.1：创建 ThemeContext...
     [创建 src/context/ThemeContext.tsx]

     ✓ 1.1 完成

     正在处理 1.2：添加 CSS 自定义属性...
     [更新 src/styles/globals.css]

     ✓ 1.2 完成
     ...
```

**使用技巧**：
- 可以从中断处继续
- 通过指定变更名称支持并行变更
- 完成状态在 `tasks.md` 的复选框中跟踪

---

### 4.6 openspec-sync-change

**用途**：将变更的 Delta 规格同步到主规格目录

**适用场景**：
- 长期变更，希望在归档前将规格合并到主目录
- 多个并行变更需要更新后的基础规格
- 想单独预览/审查合并操作

**命令语法**：
```bash
openspec sync change <change-name>
```

**示例**：
```bash
# 同步 add-dark-mode 的 Delta 规格
openspec sync change add-dark-mode

AI: 正在同步 add-dark-mode 的 Delta 规格...

     读取：openspec/changes/add-dark-mode/specs/ui/spec.md
     目标：openspec/specs/ui/spec.md

     要应用的变更：
     ✓ ADDED: 主题选择需求（2 个场景）
     ✓ ADDED: 无障碍需求（1 个场景）

     合并中...
     ✓ openspec/specs/ui/spec.md 已更新

     变更保持活跃状态。运行 /openspec-archive-change 完成归档。
```

**何时手动使用**：

| 场景 | 是否需要同步 |
|------|----------|
| 长期变更，希望规格提前合并 | 是 |
| 多个并行变更需要更新基础规格 | 是 |
| 想单独预览合并操作 | 是 |
| 快速变更，直接归档 | 否（归档时会提示） |

**使用技巧**：
- 同步是智能合并，不是简单复制粘贴
- 可以向现有需求添加场景而不重复
- 同步后变更保持活跃状态（不会归档）
- 大多数用户不需要手动调用——归档时会提示

---

### 4.7 openspec-verify-change

**用途**：验证变更实现是否符合规格

**适用场景**：
- 实现完成后
- 确保实现符合规格
- 归档前检查

**命令语法**：
```bash
openspec verify change <change-name>
```

**验证维度**：
| 维度 | 验证内容 |
|------|----------|
| **Completeness（完整性）** | 所有任务完成、所有需求实现、场景覆盖 |
| **Correctness（正确性）** | 实现符合规格意图、边界情况处理 |
| **Coherence（一致性）** | 设计决策在代码中体现、模式一致 |

**示例**：
```bash
# 验证变更
openspec verify change add-dark-mode

AI: 验证 add-dark-mode...

     完整性
     ✓ tasks.md 中 8 个任务全部完成
     ✓ specs 中所有需求都有对应代码
     ⚠ "系统偏好检测" 场景没有测试覆盖

     正确性
     ✓ 实现符合规格意图
     ✓ 边界情况已处理
     ✓ 错误状态符合规格定义

     一致性
     ✓ 设计决策在代码结构中体现
     ✓ 命名约定与设计一致
     ⚠ 设计提到"CSS 变量"但实现使用 Tailwind 类

     总结
     ─────────────────────────────
     严重问题：0
     警告：2
     可以归档：是（带有警告）

     建议：
     1. 添加系统偏好检测测试
     2. 更新 design.md 反映 Tailwind 使用，或重构使用 CSS 变量
```

**使用技巧**：
- 归档前运行以尽早发现问题
- 警告不会阻止归档，但表示潜在问题
- 适合审查 AI 的工作后再提交

---

### 4.8 openspec-archive-change

**用途**：归档完成的变更

**适用场景**：
- 变更已完成
- 清理工作区
- 保留审计记录

**命令语法**：
```bash
openspec archive change <change-name>
```

**示例**：
```bash
# 归档变更
openspec archive change add-user-auth

AI: 正在归档 add-user-auth...

     工件状态：
     ✓ proposal.md 存在
     ✓ specs/ 存在
     ✓ design.md 存在
     ✓ tasks.md 存在 (8/8 任务完成)

     Delta specs：尚未同步
     → 现在同步？（推荐）

你：是

AI: ✓ 已同步 specs 到 openspec/specs/ui/spec.md
     ✓ 已移动到 openspec/changes/archive/2025-01-24-add-user-auth/

     变更归档成功。
```

**使用技巧**：
- 归档前建议运行 `/openspec-verify-change`
- 未完成的任务会警告但不会阻止归档
- 归档的变更会保留所有工件作为历史记录

---

### 4.9 openspec-onboard

**用途**：通过交互式教程引导完成完整的 OpenSpec 工作流

**适用场景**：
- 新用户学习 OpenSpec 工作流
- 想了解 OpenSpec 如何在实际项目中工作
- 团队培训

**命令语法**：
```bash
openspec onboard
```

**执行阶段**：
1. 欢迎和代码库分析
2. 寻找改进机会
3. 创建变更（`/openspec-new-change`）
4. 编写提案
5. 创建规格
6. 编写设计文档
7. 创建任务清单
8. 实施任务（`/openspec-apply-change`）
9. 验证实现
10. 归档变更
11. 总结和下一步

**示例**：
```bash
# 启动交互式教程
openspec onboard

AI: 欢迎使用 OpenSpec！

     我将带你完成完整的工作流，使用你实际的代码库。
     我们会找一个小的改进点，创建正式的变更，
     实现它，然后归档。

     让我扫描你的代码库寻找机会...

     [分析代码库]

     我找到了一些可以改进的地方：
     1. 为联系表单添加输入验证
     2. 改进认证流程的错误消息
     3. 为异步按钮添加加载状态

     你对哪个感兴趣？（或提出其他建议）
```

**使用技巧**：
- 最适合新用户学习工作流
- 使用真实代码，不是示例
- 创建真实的变更，可以保留或丢弃
- 完成需要 15-30 分钟

---

## 5. 完整工作流示例

### 场景：为网站添加暗色模式

让我们通过一个完整的示例来看看 OpenSpec 工作流：

#### 步骤 1：创建新变更

```bash
openspec new change add-dark-mode
```

输出：
```
创建了 openspec/changes/add-dark-mode/
Schema: spec-driven

准备创建：proposal
使用 /openspec-continue-change 创建，或 /openspec-ff-change 快速创建所有工件。
```

#### 步骤 2：查看变更状态

```bash
openspec status --change add-dark-mode
```

输出：
```
变更：add-dark-mode
状态：0/4 工件完成

工件：
- [ ] proposal（就绪）
- [ ] design（等待）
- [ ] specs（等待）
- [ ] tasks（等待）
```

#### 步骤 3：获取 Proposal 指令

```bash
openspec instructions proposal --change add-dark-mode
```

#### 步骤 4：创建 Proposal

编辑 `openspec/changes/add-dark-mode/proposal.md`：

```markdown
# Proposal: Add Dark Mode

## Why

用户反馈希望支持暗色模式，特别是在夜间使用场景。
暗色模式可以减少眼睛疲劳，提升用户体验。

## What Changes

1. 添加主题切换功能
2. 支持亮色/暗色两种模式
3. 记住用户偏好设置
4. 支持系统主题自动检测

## Capabilities

- 主题切换功能
- localStorage 持久化
- 系统主题检测
- 平滑过渡动画

## Impact

- 需要添加新的 CSS 变量
- 部分组件需要适配暗色主题
- 需要更新用户设置页面
```

#### 步骤 5：继续创建 Design

```bash
openspec continue change add-dark-mode
```

AI 会自动创建 `design.md`：

```markdown
# Design: Add Dark Mode

## Context

当前网站只有亮色主题，用户需要在夜间手动调节亮度。

## Goals

- 支持亮色/暗色主题切换
- 保持设计一致性
- 最小化性能影响

## Decisions

1. 使用 CSS 变量管理主题
2. 主题状态存储在 localStorage
3. 使用 React Context 管理主题状态

## Risks

- 部分第三方组件可能不支持主题切换
- 需要确保平滑过渡，避免闪烁
```

#### 步骤 6：创建 Specs

```bash
openspec continue change add-dark-mode
```

AI 会创建规格文件 `specs/ui/spec.md`：

```markdown
# Spec: UI Theme System

## Requirements

### 主题切换

- WHEN 用户点击主题切换按钮
- THEN 主题在亮色/暗色之间切换
- AND 用户偏好保存到 localStorage

### 系统主题检测

- WHEN 用户启用"跟随系统"
- THEN 自动检测系统主题
- AND 根据系统设置自动切换

## Scenarios

### Scenario: 首次访问
- WHEN 用户首次访问网站
- AND 未设置主题偏好
- THEN 使用系统主题

### Scenario: 切换主题
- WHEN 用户点击主题切换按钮
- THEN 立即切换主题
- AND 页面不刷新
```

#### 步骤 7：创建 Tasks

```bash
openspec continue change add-dark-mode
```

AI 会创建任务清单 `tasks.md`：

```markdown
# Tasks: Add Dark Mode

## Task 1: 创建主题上下文

**Files:**
- Create: `src/context/ThemeContext.tsx`

**Steps:**
1. 创建 ThemeContext
2. 添加 useTheme hook
3. 导出 ThemeProvider 组件

## Task 2: 添加 CSS 变量

**Files:**
- Modify: `src/styles/globals.css`

**Steps:**
1. 定义亮色主题变量
2. 定义暗色主题变量
3. 添加主题切换类

## Task 3: 实现 localStorage 持久化

**Files:**
- Modify: `src/context/ThemeContext.tsx`

**Steps:**
1. 读取 localStorage 中的主题设置
2. 保存主题切换到 localStorage
3. 处理初次访问场景

## Task 4: 添加主题切换按钮

**Files:**
- Create: `src/components/Theme/ThemeToggle.tsx`

**Steps:**
1. 创建切换按钮组件
2. 添加图标
3. 绑定点击事件
```

#### 步骤 8：应用变更

```bash
openspec apply change add-dark-mode
```

AI 会开始按照任务清单实现代码。

#### 步骤 9：验证实现

```bash
openspec verify change add-dark-mode
```

AI 会验证实现是否符合规格。

#### 步骤 10：归档变更

```bash
openspec archive change add-dark-mode
```

变更被移动到归档目录：
```
openspec/changes/archive/2025-01-24-add-dark-mode/
```

---

## 6. 应用场景

### 场景 1：新功能开发

**适用命令**：`openspec-new-change` → `openspec-ff-change` → `openspec-apply-change`

对于熟悉的功能类型，可以快速推进：

```bash
openspec new change add-user-profile
openspec ff change add-user-profile
openspec apply change add-user-profile
```

### 场景 2：复杂需求探索

**适用命令**：`openspec-explore` → `openspec-new-change` → ...

对于需求不清晰的场景，先探索再实现：

```bash
openspec explore "如何优化网站性能？"
# 探索后
openspec new change optimize-performance
```

### 场景 3：Bug 修复

**适用命令**：`openspec-new-change` → `openspec-apply-change`

对于简单的 bug 修复，可以简化流程：

```bash
openspec new change fix-login-error
openspec apply change fix-login-error
```

### 场景 4：代码重构

**适用命令**：`openspec-explore` → `openspec-new-change` → `openspec-ff-change` → `openspec-apply-change`

对于大型重构，先探索再实现：

```bash
openspec explore "如何重构认证模块？"
openspec new change refactor-auth
openspec ff change refactor-auth
openspec apply change refactor-auth
```

---

## 7. 最佳实践

### 命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| **变更名称** | kebab-case | `add-user-auth`、`fix-login-bug` |
| **功能名称** | descriptive | `add-dark-mode`、`add-search` |
| **Bug 修复** | fix-开头 | `fix-null-pointer`、`fix-cors-error` |
| **重构** | refactor-开头 | `refactor-auth-module` |

### 变更管理

1. **一个变更一个功能**：不要在一个变更中塞入多个功能
2. **及时归档**：完成一个变更就及时归档
3. **并行变更**：使用变更名称支持并行开发

### 文档质量

1. **Proposal**：清晰说明为什么要做、做什么
2. **Design**：记录关键决策和权衡考虑
3. **Specs**：使用场景化描述，包含 WHEN/THEN
4. **Tasks**：任务拆解到可执行的最小单元

### 效率技巧

| 场景 | 推荐命令 | 说明 |
|------|----------|------|
| 需求明确 | `openspec-ff-change` | 快速创建所有工件 |
| 需求模糊 | `openspec-explore` → `openspec-new-change` | 先探索再创建 |
| 复杂变更 | `openspec-continue-change` | 逐步审查每个工件 |
| 快速修复 | `openspec-new-change` → `openspec-apply-change` | 跳过文档直接实现 |

---

## OpenSpec 带来的提升

使用 OpenSpec 后，开发效率有了显著提升：

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

## 测验：OpenSpec 基础测验

**及格分数**: 60


### 问题 1

OpenSpec 的核心理念是什么？
- [ ] 快速编码，尽快交付
- [x] fluid not rigid, iterative not waterfall, easy not complex
- [ ] 测试驱动开发
- [ ] 敏捷开发

**答案**: 1
**解析**: OpenSpec 的核心理念是 fluid not rigid（灵活而非僵化）、iterative not waterfall（迭代而非瀑布）、easy not complex（简单而非复杂）。


### 问题 2

Spec-Driven 工作流的正确顺序是什么？
- [ ] Design → Proposal → Tasks → Implementation
- [ ] Tasks → Specs → Design → Implementation
- [x] Proposal → Design → Specs → Tasks → Implementation
- [ ] Implementation → Tasks → Specs → Design

**答案**: 2
**解析**: Spec-Driven 的正确流程是 Proposal → Design → Specs → Tasks → Implementation。


### 问题 3

以下哪些场景适合使用 openspec-explore 命令？（多选）
- [x] 探索问题空间
- [x] 收集需求
- [ ] 紧急 bug 修复
- [x] 分析技术方案

**答案**: 0,1,3
**解析**: explore 命令适用于探索问题空间、收集需求、分析技术方案，不适合紧急 bug 修复。


### 问题 4

当你想要快速创建所有工件（proposal、specs、design、tasks）时，应该使用哪个命令？
- [ ] openspec-apply-change
- [ ] openspec-new-change
- [ ] openspec-continue-change
- [x] openspec-ff-change

**答案**: 1
**解析**: openspec-ff-change 用于快速推进变更，一次性创建所有工件。


### 问题 5

openspec-verify-change 命令验证哪三个维度？（多选）
- [x] Completeness（完整性）
- [x] Correctness（正确性）
- [x] Coherence（一致性）
- [ ] Performance（性能）

**答案**: 0,1,2
**解析**: verify 命令验证 Completeness（完整性）、Correctness（正确性）、Coherence（一致性）三个维度。


### 问题 6

在 OpenSpec 中，变更名称的推荐命名格式是什么？
- [ ] camelCase
- [ ] PascalCase
- [x] kebab-case
- [ ] snake_case

**答案**: 2
**解析**: 变更名称推荐使用 kebab-case 格式，如 add-user-auth、fix-login-bug。


### 问题 7

当你开始实现代码时，应该使用哪个命令？
- [ ] openspec-verify-change
- [x] openspec-apply-change
- [ ] openspec-archive-change
- [ ] openspec-explore

**答案**: 1
**解析**: openspec-apply-change 用于应用变更，开始实现代码。


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
变更：add-user-auth
状态：0/4 工件完成

工件：
- [ ] proposal（就绪）
- [ ] design（等待）
- [ ] specs（等待）
- [ ] tasks（等待）
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
用户需要安全的认证机制来保护账户数据。

## What Changes
1. 添加登录/注册功能
2. 实现 JWT 令牌认证
3. 添加密码重置功能

## Capabilities
- 用户注册
- 用户登录
- 密码重置
- 令牌刷新

## Impact
- 需要添加用户表
- 需要实现邮件发送功能
- 前端需要添加认证页面
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


### OpenSpec 命令速查表

**类型**: template

## OpenSpec 命令速查表

### 创建和探索

| 命令 | 用途 | 适用场景 |
|------|------|----------|
| `openspec new change <name>` | 创建新变更 | 新功能、bug 修复、重构 |
| `openspec explore [topic]` | 探索模式 | 需求不明确、需要调查 |

### 工件创建

| 命令 | 用途 | 适用场景 |
|------|------|----------|
| `openspec continue change <name>` | 创建下一个工件 | 逐步审查、复杂变更 |
| `openspec ff change <name>` | 快速创建所有工件 | 需求明确、简单功能 |

### 实现和验证

| 命令 | 用途 | 适用场景 |
|------|------|----------|
| `openspec apply change <name>` | 实现变更 | 开始写代码 |
| `openspec verify change <name>` | 验证实现 | 归档前检查 |

### 归档

| 命令 | 用途 | 适用场景 |
|------|------|----------|
| `openspec archive change <name>` | 归档变更 | 完成变更 |
| `openspec bulk-archive` | 批量归档 | 多个完成变更 |

### 快速参考

```
# 标准流程
openspec new change <name>
openspec ff change <name>     # 或 openspec continue change <name>
openspec apply change <name>
openspec verify change <name>
openspec archive change <name>

# 探索流程
openspec explore <topic>
openspec new change <name>
...
```

**元数据**:
```json
{
  "cheatsheet_type": "openspec_commands"
}
```


### OpenSpec 官方文档链接

**类型**: reference

## OpenSpec 官方资源

### 核心文档

- **GitHub 仓库**: https://github.com/Fission-AI/OpenSpec
- **npm 包**: https://www.npmjs.com/package/@fission-ai/openspec
- **官方文档**: https://github.com/Fission-AI/OpenSpec/tree/main/docs

### 关键文档链接

- [Getting Started](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md) - 入门指南
- [Commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md) - 命令参考
- [CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md) - 命令行工具
- [Workflows](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md) - 工作流模式
- [Supported Tools](https://github.com/Fission-AI/OpenSpec/blob/main/docs/supported-tools.md) - 支持的 AI 工具

### 社区

- **Discord**: https://discord.gg/YctCnvvshC
- **X (Twitter)**: https://x.com/0xTab

**元数据**:
```json
{
  "resource_type": "links"
}
```
