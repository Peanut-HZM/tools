---
slug: tools-comparison
title: 第 6 章：工具对比 - OpenSpec vs Spec-Kit vs Superpowers
order: 6
chapter_type: story
is_locked: true
required_quiz_slug: quiz-tools-comparison
---

## 全景视角：三大 Spec 驱动工具深度对比

在深入学习了 OpenSpec 之后，让我们退后一步，用全景视角看看整个 AI 编程辅助工具领域。

本章将深入分析三个主流工具：**OpenSpec**、**Spec-Kit** 和 **Superpowers**。所有信息基于 GitHub 仓库源码分析，确保准确可靠。

---

## 1. 三大工具全景图

### 1.1 核心定位对比

| 维度 | OpenSpec | Spec-Kit | Superpowers |
|------|----------|----------|-------------|
| **开发者** | Fission AI | GitHub | 个人开发者 (obra) |
| **GitHub Stars** | 29.8k+ | 76.1k+ | 78.9k+ |
| **语言** | TypeScript (98.7%) | Python (74.8%) | Shell (54.8%) / JavaScript (32.1%) |
| **包管理器** | npm/pnpm/yarn/bun | uv (Python) | 插件市场/手动安装 |
| **核心理念** | fluid not rigid, iterative not waterfall | 规格即真理，代码服务于规格 | 技能驱动的完整开发工作流 |
| **适用场景** | 现有代码演进（Brownfield） | 新项目/现有项目均可 | Cursor 用户的完整开发流程 |
| **学习曲线** | 低 - 中等 | 中等 - 高 | 中等 |

### 1.2 安装方式对比

| 工具 | 安装命令 | 初始化 | 配置文件 |
|------|----------|--------|----------|
| **OpenSpec** | `npm install -g @fission-ai/openspec@latest` | `openspec init` | `openspec/config.yaml` |
| **Spec-Kit** | `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git` | `specify init . --ai cursor` | `.specify/memory/constitution.md` |
| **Superpowers** | Cursor 内：`/add-plugin superpowers` | 自动激活 | `~/.cursor/skills/superpowers/` |

### 1.3 快速选择指南

```
你需要什么？
│
├─ 快速迭代 + 多工具支持
│  └─> OpenSpec（灵活，支持 20+ AI 工具）
│
├─ 企业级规范 + 严格流程
│  └─> Spec-Kit（GitHub 官方，模板驱动）
│
├─ 高度自动化 + Cursor 深度集成
│  └─> Superpowers（技能自动触发，零配置）
│
└─ 不确定
   └─> OpenSpec（平衡灵活性和结构性）
```

---

## 2. OpenSpec 深度解析

### 2.1 安装与初始化

**安装步骤：**

```bash
# 使用 npm 全局安装
npm install -g @fission-ai/openspec@latest

# 验证安装
openspec --version

# 在项目目录初始化
cd your-project
openspec init
```

**初始化后生成的文件结构：**

```
your-project/
├── openspec/
│   ├── changes/              # 变更存储目录
│   │   ├── add-dark-mode/    # 具体变更
│   │   │   ├── proposal.md   # 变更提案
│   │   │   ├── specs/        # 规格说明
│   │   │   ├── design.md     # 设计方案
│   │   │   └── tasks.md      # 任务清单
│   │   └── archive/          # 已归档变更
│   └── config.yaml           # 配置文件
└── AGENTS.md                 # AI 助手指令
```

### 2.2 核心命令（Slash Commands）

**默认快速路径（core profile）：**

| 命令 | 用途 | 示例 |
|------|------|------|
| `/opsx:propose` | 创建变更并生成规划文档 | `/opsx:propose add-jwt-auth` |
| `/opsx:explore` | 探索问题空间，澄清需求 | `/opsx:explore authentication options` |
| `/opsx:apply` | 实现任务 | `/opsx:apply add-jwt-auth` |
| `/opsx:archive` | 归档已完成的变更 | `/opsx:archive add-jwt-auth` |

**扩展工作流命令（需配置启用）：**

| 命令 | 用途 | 使用场景 |
|------|------|----------|
| `/opsx:new` | 创建新的变更框架 | 需要逐步控制每个文档 |
| `/opsx:continue` | 创建下一个依赖文档 | 增量式文档创建 |
| `/opsx:ff` | 快速创建所有文档 | 需求明确时快速推进 |
| `/opsx:verify` | 验证实现是否符合规格 | 归档前的质量检查 |
| `/opsx:sync` | 同步增量规格到主规格 | 多变更并行时 |
| `/opsx:bulk-archive` | 批量归档多个变更 | 清理多个已完成变更 |

### 2.3 典型工作流

**快速路径（推荐）：**

```
1. /opsx:propose add-user-auth
   → 创建 proposal.md, specs/, design.md, tasks.md

2. /opsx:apply
   → 实现 tasks.md 中的所有任务

3. /opsx:verify
   → 验证实现完整性、正确性、一致性

4. /opsx:archive
   → 归档到 archive/YYYY-MM-DD-add-user-auth/
```

**扩展路径（复杂变更）：**

```
1. /opsx:explore
   → 探索问题，澄清需求

2. /opsx:new add-user-auth
   → 创建变更框架

3. /opsx:continue
   → 创建 proposal.md

4. /opsx:continue
   → 创建 specs/

5. /opsx:continue
   → 创建 design.md

6. /opsx:continue
   → 创建 tasks.md

7. /opsx:apply
   → 实现功能

8. /opsx:verify
   → 验证

9. /opsx:archive
   → 归档
```

### 2.4 实现逻辑

**核心架构：**

1. **文件系统存储**：所有规格以 Markdown 文件存储，无需数据库
2. **依赖图管理**：artifact 之间有明确的依赖关系（proposal → specs → design → tasks）
3. **AI 指令注入**：通过 `AGENTS.md` 和 skill 文件指导 AI 行为
4. **增量规格**：支持 delta specs，允许在归档前更新主规格

**数据流：**

```
用户指令 → Slash Command → 读取依赖文件 → 创建/更新 artifact → 写入文件系统
                                                              ↓
AI 编辑器读取 artifact → 生成代码 → 用户验证 → 归档
```

### 2.5 优势与局限

**优势：**
- ✅ 轻量级，易于上手
- ✅ Brownfield 优先，适合现有项目
- ✅ 灵活的两种工作流（快速/扩展）
- ✅ 支持 20+ AI 工具
- ✅ 匿名遥测（可关闭）

**局限：**
- ❌ 需要 Node.js 环境
- ❌ 扩展工作流需要额外配置
- ❌ 文档相对简略

---

## 3. Spec-Kit 深度解析

### 3.1 安装与初始化

**安装步骤：**

```bash
# 方法 1：持久化安装（推荐）
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# 方法 2：一次性使用
uvx --from git+https://github.com/github/spec-kit.git specify init my-project

# 验证安装
specify check
```

**初始化项目：**

```bash
# 在当前目录初始化（推荐）
cd your-project
specify init . --ai cursor

# 或创建新项目
specify init my-project --ai cursor

# 强制合并到非空目录
specify init . --force --ai cursor
```

**初始化后生成的文件结构：**

```
your-project/
├── .specify/
│   ├── memory/
│   │   └── constitution.md        # 项目宪法（核心原则）
│   ├── scripts/
│   │   ├── check-prerequisites.sh
│   │   ├── common.sh
│   │   ├── create-new-feature.sh
│   │   ├── setup-plan.sh
│   │   └── update-claude-md.sh
│   ├── specs/
│   │   └── 001-create-taskify/    # 特性编号目录
│   │       ├── spec.md            # 功能规格
│   │       ├── plan.md            # 实现计划
│   │       ├── data-model.md      # 数据模型
│   │       ├── contracts/         # API 契约
│   │       ├── tasks.md           # 任务清单
│   │       └── quickstart.md      # 快速启动指南
│   └── templates/
│       ├── spec-template.md
│       ├── plan-template.md
│       └── tasks-template.md
└── AGENTS.md                       # AI 助手指令
```

### 3.2 核心命令（Slash Commands）

**核心工作流命令：**

| 命令 | 用途 | 示例 |
|------|------|------|
| `/speckit.constitution` | 创建/更新项目宪法 | `/speckit.constitution 创建代码质量规范` |
| `/speckit.specify` | 定义功能需求 | `/speckit.specify 实现实时聊天系统` |
| `/speckit.plan` | 创建技术实现计划 | `/speckit.plan 使用 WebSocket 和 PostgreSQL` |
| `/speckit.tasks` | 生成可执行任务清单 | `/speckit.tasks` |
| `/speckit.implement` | 执行所有任务 | `/speckit.implement` |

**可选质量增强命令：**

| 命令 | 用途 | 使用场景 |
|------|------|----------|
| `/speckit.clarify` | 澄清未明确的规格 | 在 plan 之前减少返工 |
| `/speckit.analyze` | 跨文档一致性分析 | tasks 完成后，implement 前 |
| `/speckit.checklist` | 生成自定义检查清单 | 验证需求完整性 |

### 3.3 典型工作流

**完整 Spec-Driven 流程：**

```
1. /speckit.constitution
   → 创建项目核心原则（代码质量、测试标准、性能要求）

2. /speckit.specify
   → 自动创建分支（如 001-real-time-chat）
   → 生成 specs/001-real-time-chat/spec.md
   → 包含用户故事、验收标准、非功能需求

3. /speckit.clarify（可选但推荐）
   → 识别规格中的模糊点
   → 添加 Clarifications 章节

4. /speckit.plan
   → 读取 spec.md
   → 生成 plan.md（技术栈、架构决策）
   → 创建 data-model.md, contracts/, research.md

5. /speckit.analyze（可选）
   → 跨文档一致性检查
   → 识别遗漏的需求

6. /speckit.tasks
   → 从 plan.md, contracts/生成 tasks.md
   → 标记可并行任务 [P]
   → 定义任务依赖关系

7. /speckit.implement
   → 按任务清单执行
   → 更新任务状态 [x]
   → 生成代码和测试
```

### 3.4 实现逻辑

**核心架构：**

1. **宪法驱动**：`.specify/memory/constitution.md` 定义不可变的核心原则
2. **模板约束**：spec/plan/tasks 模板引导 LLM 产出高质量文档
3. **分支管理**：每个特性自动创建 Git 分支
4. **双向追溯**：需求 → 计划 → 任务 → 代码的完整追溯链

**宪法执行机制示例：**

```markdown
# 项目宪法示例

## Article I: Library-First Principle
每个功能必须首先是独立库

## Article III: Test-First Imperative
禁止在测试之前编写实现代码

## Article VII: Simplicity
- 最多 3 个项目
- 禁止过度设计
```

**模板引导机制：**

```markdown
# Spec 模板的关键约束

- ✅ 聚焦 WHAT 和 WHY
- ❌ 避免 HOW（不涉及技术栈）
- [NEEDS CLARIFICATION] 标记所有不确定性
- 自检清单确保完整性
```

### 3.5 优势与局限

**优势：**
- ✅ GitHub 官方支持，生态强大
- ✅ 完整的宪法驱动架构
- ✅ 模板约束保证文档质量
- ✅ 支持多种 AI 助手（20+）
- ✅ 强制测试优先（TDD）

**局限：**
- ❌ 需要 Python/uv 环境
- ❌ 学习曲线较陡
- ❌ 文档量大，初期投入高
- ❌ Cursor 集成存在问题（2025 年 10 月报告）

---

## 4. Superpowers 深度解析

### 4.1 安装与初始化

**安装步骤（Cursor 插件市场 - 推荐）：**

```text
# 在 Cursor Agent 聊天窗口执行
/add-plugin superpowers

# 或搜索"superpowers"安装
```

**验证安装：**

```text
# 开始新会话，询问应该触发技能的问题
"help me plan this feature"
"let's debug this issue"

# 如果安装成功，AI 会自动调用相应的 superpowers 技能
```

**手动安装（备选）：**

```bash
# 创建技能目录
mkdir -p ~/.cursor/skills
cd ~/.cursor/skills

# 克隆仓库
git clone https://github.com/obra/superpowers.git

# 创建引导规则
cat > ~/.cursor/rules/superpowers-bootstrap.mdc << 'EOF'
# Superpowers Bootstrap

When responding to tasks, check if any Superpowers skill applies, even with just a 1% probability.

Available skills are located in ~/.cursor/skills/superpowers/

Before responding, read relevant skill files to understand available workflows.
EOF
```

**安装后生成的文件结构：**

```
~/.cursor/skills/superpowers/
├── skills/                     # 技能库
│   ├── brainstorming/
│   │   └── SKILL.md           # 头脑风暴技能
│   ├── writing-plans/
│   │   └── SKILL.md           # 编写计划技能
│   ├── test-driven-development/
│   │   └── SKILL.md           # TDD 技能
│   ├── systematic-debugging/
│   │   └── SKILL.md           # 系统化调试
│   ├── using-git-worktrees/
│   │   └── SKILL.md           # Git 并行开发
│   └── ...（共 15+ 技能）
├── hooks/                      # 自动触发钩子
│   └── superpowers-hook.md
├── commands/                   # 自定义命令
└── docs/                       # 文档
```

### 4.2 核心技能库

**测试类技能：**

| 技能 | 用途 | 触发时机 |
|------|------|----------|
| `test-driven-development` | RED-GREEN-REFACTOR 循环 | 实现任何功能前 |
| `verification-before-completion` | 验证修复有效性 | 声明任务完成前 |

**调试类技能：**

| 技能 | 用途 | 工作流 |
|------|------|--------|
| `systematic-debugging` | 4 阶段根本原因分析 | 1. 重现 → 2. 缩小 → 3. 分析 → 4. 验证 |

**协作类技能：**

| 技能 | 用途 | 输出 |
|------|------|------|
| `brainstorming` | 需求探索和设计细化 | 设计文档（保存到 docs/plans/） |
| `writing-plans` | 详细实现计划 | tasks.md（2-5 分钟粒度的任务） |
| `executing-plans` | 批量执行任务 | 带检查点的批处理 |
| `dispatching-parallel-agents` | 并子代理工作流 | 多个子代理并行执行 |
| `requesting-code-review` | 代码审查 | 问题严重性分级报告 |
| `using-git-worktrees` | 并行开发分支 | 隔离的 Git worktree |
| `finishing-a-development-branch` | 分支合并决策 | merge/PR/keep/discard 选项 |

**元技能：**

| 技能 | 用途 |
|------|------|
| `writing-skills` | 创建新技能的指南 |
| `using-superpowers` | 技能系统介绍 |

### 4.3 典型工作流

**完整 Superpowers 流程：**

```
1. 头脑风暴阶段
   → brainstorming 技能自动激活
   → AI 提问澄清需求
   → 提出 2-3 种方案对比
   → 输出设计文档 docs/plans/YYYY-MM-DD-topic.md
   → 等待用户批准

2. Git 工作区创建
   → using-git-worktrees 激活
   → 创建独立分支
   → 运行项目设置
   → 验证测试基线

3. 计划编写
   → writing-plans 激活
   → 拆解为 2-5 分钟粒度的任务
   → 每个任务包含：文件路径、完整代码、验证步骤

4. 任务执行
   → subagent-driven-development 激活
   → 为每个任务分派新鲜子代理
   → 两阶段审查（规格符合性 → 代码质量）
   → 或批处理执行（带人工检查点）

5. 测试驱动实现
   → test-driven-development 强制执行
   → RED: 写失败测试
   → GREEN: 写最少代码通过测试
   → REFACTOR: 重构代码
   → 删除测试前写的代码

6. 代码审查
   → requesting-code-review 激活
   → 对照计划审查
   → 按严重性报告问题
   → 关键问题阻塞进度

7. 分支完成
   → finishing-a-development-branch 激活
   → 验证所有测试通过
   → 提供选项：merge/PR/keep/discard
   → 清理 worktree
```

### 4.4 实现逻辑

**核心架构：**

1. **技能触发机制**：AI 在响应前检查是否有适用技能（即使只有 1% 可能性）
2. **强制工作流**：技能不是建议，是强制执行的流程
3. **子代理系统**：为每个任务创建新鲜子代理，避免上下文污染
4. **自动文档**：设计文档、计划文档自动生成并保存

**技能检查流程：**

```
用户消息 → 技能适用性检查（1% 概率即触发）
         ↓
    找到适用技能？
         ↓
    是 → 读取技能文件 → 遵循技能工作流
         ↓
    否 → 正常响应
```

**TDD 强制执行：**

```markdown
# test-driven-development 技能规则

1. 禁止在测试前写实现代码
2. 必须先写失败测试（RED）
3. 测试必须得到用户批准
4. 然后写最少代码通过（GREEN）
5. 最后重构（REFACTOR）
6. 删除所有测试前写的代码
```

### 4.5 优势与局限

**优势：**
- ✅ 零配置，即插即用
- ✅ 与 Cursor 深度集成
- ✅ 完整的技能库（15+ 技能）
- ✅ 强制 TDD 和代码审查
- ✅ 子代理并行执行
- ✅ 自动文档保存

**局限：**
- ❌ 仅限 Cursor 使用
- ❌ 技能触发有时不稳定（2026 年 3 月报告）
- ❌ 个人开发者维护，支持有限
- ❌ 技能更新可能导致行为变化

---

## 5. 三大工具横向对比

### 5.1 安装复杂度

| 工具 | 步骤数 | 依赖 | 配置难度 |
|------|--------|------|----------|
| **OpenSpec** | 3 步 | Node.js 20+ | 低 |
| **Spec-Kit** | 3 步 | Python 3.11+, uv | 中 |
| **Superpowers** | 1 步 | Cursor IDE | 极低 |

### 5.2 学习曲线

| 工具 | 上手时间 | 精通时间 | 文档质量 |
|------|----------|----------|----------|
| **OpenSpec** | 30 分钟 | 2 小时 | 良好 |
| **Spec-Kit** | 2 小时 | 8 小时 | 优秀 |
| **Superpowers** | 15 分钟 | 4 小时 | 良好 |

### 5.3 适用场景

| 场景 | 推荐工具 | 理由 |
|------|----------|------|
| **Cursor 用户，快速启动** | Superpowers | 零配置，即插即用 |
| **现有项目演进** | OpenSpec | Brownfield 优先，轻量级 |
| **企业级项目，需要严格规范** | Spec-Kit | 宪法驱动，模板约束强 |
| **团队并行开发** | OpenSpec / Superpowers | 都支持 Git 分支隔离 |
| **强制 TDD** | Superpowers | 强制执行 RED-GREEN-REFACTOR |
| **多 AI 工具环境** | OpenSpec / Spec-Kit | 支持 20+ 工具 |

### 5.4 命令对比速查表

| 阶段 | OpenSpec | Spec-Kit | Superpowers |
|------|----------|----------|-------------|
| **需求探索** | `/opsx:explore` | `/speckit.specify` | `brainstorming`（自动） |
| **创建规格** | `/opsx:propose` | `/speckit.specify` | `brainstorming` → 设计文档 |
| **技术计划** | `/opsx:ff` 或 `/opsx:continue` | `/speckit.plan` | `writing-plans`（自动） |
| **任务生成** | `/opsx:continue` | `/speckit.tasks` | `writing-plans` 输出 |
| **实现代码** | `/opsx:apply` | `/speckit.implement` | `subagent-driven-development` |
| **测试** | 无强制 | 宪法强制 | `test-driven-development` 强制 |
| **代码审查** | `/opsx:verify` | `/speckit.analyze` | `requesting-code-review` |
| **归档** | `/opsx:archive` | Git 分支合并 | `finishing-a-development-branch` |

---

## 6. 实战建议

### 6.1 选择指南

**选择 OpenSpec，如果你：**
- ✅ 已有现有项目需要演进
- ✅ 希望快速上手，低学习成本
- ✅ 使用多种 AI 工具（Claude Code, Cursor, Windsurf 等）
- ✅ 需要灵活的两种工作流

**选择 Spec-Kit，如果你：**
- ✅ 从零开始新项目
- ✅ 需要严格的项目治理（宪法驱动）
- ✅ 团队开发，需要一致性保证
- ✅ 愿意投入时间学习完整流程

**选择 Superpowers，如果你：**
- ✅ 使用 Cursor 作为主要 IDE
- ✅ 希望零配置，即插即用
- ✅ 强制 TDD 和代码审查
- ✅ 需要子代理并行执行

### 6.2 组合使用策略

**策略 A：OpenSpec + Superpowers**
- OpenSpec 管理规格文档
- Superpowers 执行实现（TDD、审查）

**策略 B：Spec-Kit + OpenSpec**
- Spec-Kit 创建规格和计划
- OpenSpec 管理变更和归档

**策略 C：仅 Superpowers**
- 全部使用 Superpowers 技能
- 适合个人开发者快速迭代

---

## 7. 常见问题（FAQ）

### Q1: 三个工具可以同时使用吗？

**A**: 可以，但不推荐。每个工具都有自己的规格管理方式，同时使用会导致文档结构混乱。建议根据项目选择一个主工具。

### Q2: Cursor 中哪个工具最好用？

**A**: Superpowers 是 Cursor 原生插件，集成度最高。但 OpenSpec 和 Spec-Kit 也可以在 Cursor 中使用（通过 slash commands）。

### Q3: 迁移成本高吗？

**A**: 中等。三个工具都使用 Markdown 存储规格，手动迁移文档是可行的。但工作流和命令不同，需要重新学习。

### Q4: 企业环境推荐哪个？

**A**: Spec-Kit。宪法驱动和模板约束最适合团队一致性要求。

### Q5: 个人项目推荐哪个？

**A**: Superpowers（Cursor 用户）或 OpenSpec（其他 AI 工具用户）。

---

## 8. 总结

三大工具代表了 Spec-Driven Development 的三个方向：

1. **OpenSpec** - 轻量级、灵活、Brownfield 优先
2. **Spec-Kit** - 企业级、严格、宪法驱动
3. **Superpowers** - 技能化、自动化、Cursor 专用

选择哪个工具取决于：
- 你的 IDE 选择
- 项目类型（新项目 vs 现有项目）
- 团队规模
- 对规范严格程度的需求

但核心理念一致：**在写代码前先达成共识，规格驱动实现**。

---

## 动手实践

### 练习 1：安装对比

1. 在你的项目中分别安装三个工具
2. 记录每个工具的安装步骤数和时间
3. 对比生成的文件结构

### 练习 2：工作流体验

1. 使用 OpenSpec 创建一个小功能（如添加暗色模式）
2. 使用 Spec-Kit 创建同样的功能
3. 使用 Superpowers 创建同样的功能
4. 对比三个工具的输出质量和时间

### 练习 3：命令速查卡

创建你自己的命令速查卡，包含：
- 每个工具的 5 个最常用命令
- 命令的用途和示例
- 命令之间的对应关系

---

**下一章**：我们会总结整个 VibeCoding 实践指南，并提供持续学习的资源！

---

## 测验：三大工具对比测验

**及格分数**: 60


### 问题 1

【场景】某创业公司（5 人团队）正在开发 SaaS 产品，技术栈为 TypeScript + React + Node.js。团队需求：

1. 需要快速迭代，每两周一个版本
2. 团队成员 AI 工具偏好不同（有人用 Claude Code，有人用 Cursor）
3. 希望保持灵活性，随时调整需求
4. 需要一定的文档追溯能力

问题：以下哪个工具最适合这个团队？
- [x] OpenSpec - 平衡灵活性和结构性，支持多工具
- [ ] Spec-Kit - GitHub 官方，企业级支持
- [ ] Superpowers - 高度自动化，零配置
- [ ] 三个工具都适合，随意选择

**答案**: 0
**解析**: OpenSpec 最适合小团队：支持 20+ AI 工具（满足偏好差异），灵活迭代（适应快速变化），artifact 驱动（提供基本追溯）。Spec-Kit 流程过重，Superpowers 协作支持弱。


### 问题 2

【诊断】某团队使用 Spec-Kit 进行开发，以下哪个流程是正确的？
- [ ] 直接编写代码，然后补充规格文档
- [x] /speckit.specify → /speckit.plan → /speckit.tasks → 实现
- [ ] 先写测试，再写实现代码，最后写规格
- [ ] 根据上下文自动触发，无需手动调用命令

**答案**: 1
**解析**: Spec-Kit 采用线性 SDD 流程：specify（创建规格）→ plan（生成计划）→ tasks（生成任务）→ 实现。这个顺序体现了规格驱动开发的核心理念。


### 问题 3

【决策】企业级项目（20+ 人团队）需要严格的合规审查和统一规范，应该选择哪个工具？
- [ ] Superpowers - 自动化程度最高
- [ ] OpenSpec - 灵活性最好
- [x] Spec-Kit - 企业级流程和严格审查
- [ ] 三个工具混合使用 - 取长补短

**答案**: 2
**解析**: Spec-Kit 专为大型企业设计，提供严格流程和统一规范。宪法驱动和模板约束确保团队一致性。


### 问题 4

【场景】在 Cursor 中开发个人项目，希望零配置快速启动，应该选择哪个工具？
- [ ] OpenSpec - 需要 npm 安装和初始化
- [x] Superpowers - Cursor 插件市场一键安装
- [ ] Spec-Kit - 需要 uv 安装和宪法配置
- [ ] 三个工具都不适合

**答案**: 1
**解析**: Superpowers 是 Cursor 原生插件，通过/add-plugin superpowers 一键安装，零配置，技能自动触发，最适合个人快速开发。


### 问题 5

【多选】以下哪些是 Superpowers 的核心技能？（多选）
- [x] brainstorming - 需求探索和设计细化
- [x] writing-plans - 详细实现计划
- [x] test-driven-development - RED-GREEN-REFACTOR 循环
- [x] systematic-debugging - 4 阶段根本原因分析

**答案**: 0,1,2,3
**解析**: brainstorming、writing-plans、test-driven-development、systematic-debugging 都是 Superpowers 的核心技能。所有选项都正确。


---

## 资源


### 工具选择决策树

**类型**: template

## 工具选择决策树

### 决策流程

```
开始
 │
 ↓
你的项目是什么类型？
 │
 ├─ 个人项目/快速原型
 │  └─> Superpowers（自动化）或 OpenSpec（灵活性）
 │
 ├─ 小团队（2-10 人）
 │  └─> OpenSpec（平衡性最好）
 │
 ├─ 大团队（10+ 人）/企业级
 │  └─> Spec-Kit（严格流程）
 │
 └─ 不确定
    └─> OpenSpec（最平衡的选择）
```

### 快速决策表

| 项目类型 | 团队规模 | 推荐工具 | 理由 |
|----------|----------|----------|------|
| 个人项目 | 1 人 | Superpowers/OpenSpec | 自动化或灵活性 |
| 创业公司 | 2-10 人 | OpenSpec | 平衡灵活和结构 |
| 企业项目 | 10+ 人 | Spec-Kit | 协作和追溯 |
| 开源项目 | 分布式 | OpenSpec | 多工具支持 |
| 学习项目 | 1 人 | Superpowers | 自动化学习 |

### 迁移路径

```
对话驱动 → Superpowers → OpenSpec → Spec-Kit
（入门）   （自动化）   （进阶）    （专家）
```

**元数据**:
```json
{
  "guide_type": "decision_tree"
}
```


### 三大工具核心命令速查表

**类型**: template

## 三大工具核心命令速查表

### OpenSpec 命令

```bash
# 初始化
npm install -g @fission-ai/openspec@latest
openspec init

# 创建变更（Core Profile）
/opsx:propose <change-name>
/opsx:explore <topic>
/opsx:apply
/opsx:archive

# 创建变更（Expanded Profile）
/opsx:new <change-name>
/opsx:continue
/opsx:ff
/opsx:verify
/opsx:sync
/opsx:bulk-archive
```

### Spec-Kit 命令

```bash
# 初始化
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify init . --ai claude

# 开发流程
/speckit.constitution
/speckit.specify <feature>
/speckit.plan <tech-stack>
/speckit.tasks
/speckit.implement
```

### Superpowers 命令

```bash
# Cursor 插件市场安装
/add-plugin superpowers

# 技能自动触发（无需手动调用）
- brainstorming
- writing-plans
- test-driven-development
- systematic-debugging
- using-git-worktrees
- requesting-code-review
- finishing-a-development-branch
```

**元数据**:
```json
{
  "cheatsheet_type": "commands"
}
```


### 三大工具官方资源链接

**类型**: reference

## OpenSpec 官方资源

- **GitHub 仓库**: https://github.com/Fission-AI/OpenSpec
- **npm 包**: https://www.npmjs.com/package/@fission-ai/openspec
- **官方文档**: https://github.com/Fission-AI/OpenSpec/tree/main/docs
- **Discord**: https://discord.gg/YctCnvvshC

## Spec-Kit 官方资源

- **GitHub 仓库**: https://github.com/github/spec-kit
- **官方文档**: https://github.github.io/spec-kit/
- **Specify CLI**: `uv tool install specify-cli`

## Superpowers 官方资源

- **GitHub 仓库**: https://github.com/obra/superpowers
- **安装指南**: https://github.com/obra/superpowers#installation
- **技能库**: ~/.cursor/skills/superpowers/

**元数据**:
```json
{
  "resource_type": "links"
}
```
