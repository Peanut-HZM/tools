---
slug: tools-comparison
title: 第 6 章：工具对比 - OpenSpec vs Spec-Kit vs Superpowers
order: 6
chapter_type: story
is_locked: true
required_quiz_slug: quiz-tools-comparison
---

## 全景视角：OpenSpec vs Spec-Kit vs Superpowers

在深入学习了 OpenSpec 之后，让我们退后一步，用全景视角看看整个 AI 编程辅助工具领域。

本章将深入分析三个主流工具：**OpenSpec**、**Spec-Kit** 和 **Superpowers**。所有信息基于 GitHub 仓库源码分析，确保准确可靠。

### 三大工具全景图

| 维度 | OpenSpec | Spec-Kit | Superpowers |
|------|----------|----------|-------------|
| **仓库** | [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) | [github/spec-kit](https://github.com/github/spec-kit) | [obra/superpowers](https://github.com/obra/superpowers) |
| **定位** | 规格驱动的 AI 协作开发框架 | GitHub 官方规格开发工具包 | Claude 技能系统增强框架 |
| **核心理念** | Fluid not rigid, 迭代式规格驱动 | Spec-Driven Development (SDD) | Skill-based autonomous development |
| **安装方式** | `npm install -g @fission-ai/openspec` | `uv tool install specify-cli` | 插件市场安装 |
| **AI 集成** | 20+ 工具 (Claude Code, Cursor, Windsurf) | Claude Code 为主 | Claude Desktop 官方插件 |
| **工作流** | OPSX (artifact 驱动，自由迭代) | 线性阶段 (specify → plan → tasks) | 技能自动触发，子代理工作流 |
| **核心命令** | `/opsx:propose`, `/opsx:apply` | `/speckit.specify`, `/speckit.plan` | 自动触发 |
| **项目结构** | `openspec/changes/<name>/` | `specs/<branch-name>/` | `.claude-plugin/skills/` |
| **语言** | TypeScript/JavaScript | Python (CLI) | JavaScript/TypeScript |

### 快速选择指南

```
你需要什么？
│
├─ 快速迭代 + 多工具支持
│  └─> OpenSpec（灵活，支持 20+ AI 工具）
│
├─ 企业级规范 + 严格流程
│  └─> Spec-Kit（GitHub 官方，模板驱动）
│
├─ 高度自动化 + Claude 深度集成
│  └─> Superpowers（技能自动触发）
│
└─ 不确定
   └─> OpenSpec（平衡灵活性和结构性）
```

---

## OpenSpec 深度解析

### 项目结构

```
openspec/
├── changes/              # 变更目录
│   ├── add-dark-mode/    # 单个变更
│   │   ├── .openspec.yaml  # 元数据
│   │   ├── proposal.md     # 为什么做、做什么
│   │   ├── specs/          # 详细规格
│   │   │   └── ui-spec/spec.md
│   │   ├── design.md       # 技术方案
│   │   └── tasks.md        # 实现清单
├── specs/                # 主规格目录 (可复用规格)
└── config.yaml           # 项目配置
```

### OPSX 工作流命令

**Core Profile (默认)**：

| 命令 | 用途 | 示例 |
|------|------|------|
| `/opsx:propose` | 创建变更并生成规划 artifacts | `/opsx:propose add-dark-mode` |
| `/opsx:explore` | 探索模式，思考和分析 | `/opsx:explore 如何处理移动端认证` |
| `/opsx:apply` | 实现 tasks.md 中的任务 | `/opsx:apply` |
| `/opsx:archive` | 归档完成的变更 | `/opsx:archive add-dark-mode` |

**Expanded Profile (扩展)**：

| 命令 | 用途 | 示例 |
|------|------|------|
| `/opsx:new` | 创建变更脚手架 | `/opsx:new add-feature` |
| `/opsx:continue` | 逐个创建 artifacts | `/opsx:continue` |
| `/opsx:ff` | 一次性创建所有 artifacts | `/opsx:ff` |
| `/opsx:verify` | 验证实现是否符合 artifacts | `/opsx:verify` |
| `/opsx:sync` | 同步 delta specs 到主规格 | `/opsx:sync` |

### 配置系统

项目配置 (`openspec/config.yaml`)：

```yaml
schema: spec-driven

context: |
  Tech stack: TypeScript, React, Node.js
  API conventions: RESTful, JSON responses
  Testing: Vitest for unit tests

rules:
  proposal:
    - Include rollback plan
    - Identify affected teams
  specs:
    - Use Given/When/Then format
```

### 核心特点

1. **Artifact 驱动**：每个 artifact (proposal, specs, design, tasks) 都有独立模板
2. **自由迭代**：不强制线性流程，可随时更新任何 artifact
3. **配置注入**：context 和 rules 自动注入到所有 artifacts
4. **Schema 系统**：支持自定义 workflow schemas

### 适用场景

✅ 需要快速迭代和个人/小团队项目
✅ 希望在 AI 协作中保持灵活性
✅ 需要支持多种 AI 工具

---

## Spec-Kit 深度解析

### 项目结构

```
project/
├── specs/
│   ├── 001-chat-system/    # 功能编号目录
│   │   ├── spec.md         # 功能规格
│   │   ├── plan.md         # 实现计划
│   │   ├── data-model.md   # 数据模型
│   │   ├── contracts/      # API 契约
│   │   │   ├── events.md   # WebSocket 事件
│   │   │   └── endpoints.md # REST 端点
│   │   ├── quickstart.md   # 快速验证指南
│   │   └── tasks.md        # 任务清单
│   └── 002-xxx/
├── templates/              # 模板目录
│   ├── feature-spec.md
│   ├── plan.md
│   └── tasks.md
└── extensions/             # VSCode 扩展
```

### Spec-Driven 开发流程

```
1. /speckit.specify <feature>  → 创建规格分支和 spec.md
2. /speckit.plan <tech-stack>  → 生成 plan.md, data-model.md, contracts/
3. /speckit.tasks              → 从 plan 生成 tasks.md
4. AI 实现任务 → 代码生成
5. 验证和合并
```

### 核心命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `specify init` | 初始化项目 | `specify init . --ai claude` |
| `/speckit.specify` | 创建功能规格 | `/speckit.specify 实时聊天系统` |
| `/speckit.plan` | 生成实现计划 | `/speckit.plan WebSocket + PostgreSQL` |
| `/speckit.tasks` | 生成任务清单 | `/speckit.tasks` |

### 核心理念

Spec-Kit 实现了 **Specification-Driven Development (SDD)**：

> "Specifications don't serve code—code serves specifications."

核心思想：
- **规格即代码**：规格是可执行的，直接生成实现
- **模板驱动**：所有规格使用统一模板，保证一致性
- **分支管理**：每个功能独立分支，便于审查和合并
- **研究代理**：自动调研技术选型和最佳实践

### 适用场景

✅ 企业级项目，需要严格规格审查
✅ 多团队协作，需要统一规范
✅ 长期维护项目，需要规格与代码同步

---

## Superpowers 深度解析

### 项目结构

```
superpowers/
├── skills/                 # 技能库
│   ├── brainstorming/      # 头脑风暴
│   ├── writing-plans/      # 编写计划
│   ├── test-driven-development/ # TDD
│   ├── systematic-debugging/    # 系统调试
│   └── subagent-driven-development/ # 子代理开发
├── commands/               # 命令处理
├── lib/                    # 核心逻辑
├── agents/                 # AI Agent 配置
└── hooks/                  # 事件钩子
```

### 技能触发机制

```
用户输入 → 意图识别 → 自动触发对应技能 → 执行 → 结果

示例：
用户："帮我规划这个功能"
  → 触发 brainstorming 技能
  → 提出澄清问题
  → 生成设计方案
  → 保存到 docs/plans/
```

### 核心技能库

| 技能 | 触发条件 | 功能 |
|------|----------|------|
| `brainstorming` | 设计讨论前 | 探索需求，提出方案，生成设计文档 |
| `writing-plans` | 设计确认后 | 分解任务，编写详细实现计划 |
| `test-driven-development` | 编写代码时 | RED-GREEN-REFACTOR 循环 |
| `subagent-driven-development` | 任务执行时 | 分发子代理，两阶段审查 |
| `systematic-debugging` | 调试时 | 四阶段根因分析 |
| `requesting-code-review` | 提交前 | 代码审查清单 |

### 安装方式

**Claude Code 官方市场**：
```bash
/plugin install superpowers@claude-plugins-official
```

**Claude Code 市场**：
```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### 核心特点

1. **自动触发**：无需手动调用，根据上下文自动激活
2. **子代理工作流**：分发任务到多个子代理并行执行
3. **两阶段审查**：规范合规性审查 + 代码质量审查
4. **TDD 强制**：必须先写失败测试，再写实现代码

### 适用场景

✅ 个人开发者追求高度自动化
✅ 深度使用 Claude Desktop/Claude Code
✅ 希望最小化手动配置

---

## 实际使用场景对比

### 场景 1：个人项目快速开发

**需求**：快速构建一个个人博客系统

| 工具 | 优势 | 劣势 |
|------|------|------|
| **OpenSpec** | 灵活迭代，可随时调整方向 | 需要手动管理 artifacts |
| **Spec-Kit** | 文档完整，便于后续维护 | 流程较重，前期投入多 |
| **Superpowers** | 自动触发，零配置 | 依赖 Claude，定制性弱 |

**推荐**：Superpowers 或 OpenSpec

---

### 场景 2：小团队协作开发

**需求**：5 人团队开发 SaaS 产品

| 工具 | 优势 | 劣势 |
|------|------|------|
| **OpenSpec** | 支持多工具，协作友好 | 需要团队学习成本 |
| **Spec-Kit** | 统一规范，审查流程 | 灵活性不足 |
| **Superpowers** | 自动化高 | 团队协作支持弱 |

**推荐**：OpenSpec

---

### 场景 3：企业级项目开发

**需求**：20+ 人团队，严格合规要求

| 工具 | 优势 | 劣势 |
|------|------|------|
| **OpenSpec** | 平衡灵活和结构 | 企业特性不如 Spec-Kit |
| **Spec-Kit** | GitHub 官方，企业级支持 | 学习曲线陡 |
| **Superpowers** | 不适合大型团队 | 缺乏企业特性 |

**推荐**：Spec-Kit

---

## 工具组合使用策略

### 推荐组合

**组合 1：OpenSpec + Superpowers**

```
规格管理：OpenSpec (proposal, specs, design, tasks)
开发辅助：Superpowers 技能 (TDD, debugging, code-review)
```

**组合 2：Spec-Kit + OpenSpec**

```
规格创建：Spec-Kit (specify, plan, tasks)
迭代更新：OpenSpec (自由迭代，灵活更新)
```

### 不推荐组合

❌ **Superpowers + Spec-Kit**：工作流冲突，自动触发 vs 线性流程

### 迁移指南

#### 从 Rules 迁移到 OpenSpec

```bash
# 步骤 1：创建迁移变更
openspec new change migrate-rules

# 步骤 2：将 rules 转换为 specs
# - 通用规则 → 通用 specs
# - 项目规则 → 项目 specs

# 步骤 3：逐步采用 Spec 流程
openspec apply change migrate-rules
```

#### 从对话驱动迁移到 OpenSpec

1. 开始记录变更意图
2. 每次变更前写简短 proposal
3. 复杂变更编写 design 和 specs

---

## 我的建议

根据实际经验和源码分析：

1. **个人小项目**：Superpowers（自动化）或 OpenSpec（灵活）
2. **工作项目**：OpenSpec（平衡性最好）
3. **团队协作**：OpenSpec 或 Spec-Kit（根据团队规模）
4. **企业项目**：Spec-Kit（严格流程）

### 学习路径

```
对话驱动 → Rules → Superpowers → OpenSpec → Spec-Kit
（入门）   （基础）  （自动化）   （进阶）    （专家）
```

### 核心原则

> **工具是手段，不是目的。**

选择工具的核心原则：
1. **匹配项目规模**：小项目轻量，大项目规范
2. **匹配团队能力**：考虑学习成本和接受度
3. **匹配开发节奏**：快速迭代 vs 严格审查
4. **可演进性**：从小项目开始，随项目增长演进

---

**总结**：三大工具各有优势，没有绝对的最好，只有最适合。关键是理解它们的核心理念和适用场景，然后根据项目需求做出明智选择。

---

## 测验：三大工具对比测验

**及格分数**: 60


### 问题 1

以下哪个工具使用技能自动触发机制？
- [ ] OpenSpec
- [ ] Spec-Kit
- [x] Superpowers
- [ ] 以上都是

**答案**: 2
**解析**: Superpowers 使用技能自动触发机制，根据上下文自动激活对应技能。


### 问题 2

OpenSpec 的核心工作流 OPSX 的特点是什么？
- [ ] 线性阶段，严格流程
- [x] Artifact 驱动，自由迭代
- [ ] 完全自动化，无需手动操作
- [ ] 仅支持单一 AI 工具

**答案**: 1
**解析**: OPSX 是 Artifact 驱动，支持自由迭代，不强制线性流程。


### 问题 3

Spec-Kit 的核心理念是什么？
- [ ] Fluid not rigid
- [x] Specification-Driven Development
- [ ] Skill-based autonomous development
- [ ] Code first, spec later

**答案**: 1
**解析**: Spec-Kit 实现 Spec-Driven Development (SDD)，规格是可执行的，直接生成实现。


### 问题 4

对于 20+ 人的企业级团队，哪个工具最合适？
- [ ] OpenSpec
- [x] Spec-Kit
- [ ] Superpowers
- [ ] 都可以

**答案**: 1
**解析**: Spec-Kit 提供严格的企业级流程和统一规范，适合大型团队。


### 问题 5

以下哪些是推荐的工具组合？（多选）
- [x] OpenSpec + Superpowers
- [x] Spec-Kit + OpenSpec
- [ ] Superpowers + Spec-Kit
- [ ] 所有组合都推荐

**答案**: 0,1
**解析**: OpenSpec+Superpowers 和 Spec-Kit+OpenSpec 是推荐组合，Superpowers+Spec-Kit 工作流冲突不推荐。


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
 │  └─> Superpowers（自动化）或 OpenSpec（灵活）
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
/speckit.specify <feature>
/speckit.plan <tech-stack>
/speckit.tasks
```

### Superpowers 命令

```bash
# Claude Code 安装
/plugin install superpowers@claude-plugins-official

# 或市场安装
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace

# 技能自动触发（无需手动调用）
- brainstorming
- writing-plans
- test-driven-development
- systematic-debugging
- subagent-driven-development
```

**元数据**:
```json
{
  "cheatsheet_type": "commands"
}
```
