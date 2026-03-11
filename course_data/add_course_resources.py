"""
OpenSpec VibeCoding 实践指南课程优化 - 补充第 4-5 章内容

完成剩余章节的内容、测验和资源：
- 第 4 章：OpenSpec 核心概念和技能详解
- 第 5 章：三大工具对比和迁移指南
"""

import json
from datetime import datetime

# 读取已有的优化数据
with open('/Users/huazhongmin/IdeaProjects/tools/course_data/course-export-optimized-v1.json', 'r', encoding='utf-8') as f:
    course_data = json.load(f)

# ============ 第 4 章：OpenSpec 核心概念 ============
chapter4_content = """## 发现新大陆：OpenSpec！

在我掌握了 rules 之后，我又发现了一个更强大的工具——**OpenSpec**。

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
openspec new change <change-name> --schema <schema-name>
```

**示例**：
```bash
# 创建一个添加用户认证功能的变更
openspec new change add-user-auth

# 使用自定义 schema
openspec new change add-payment --schema payment-feature
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

**动手试试**：下一章我们会对比三大主流 AI 编程工具！"""

chapter4 = {
    "slug": "openspec-core",
    "title": "第四章：进阶工具 - OpenSpec & Superpowers 🚀",
    "order": 4,
    "content": chapter4_content,
    "chapter_type": "code",
    "video_url": None,
    "is_locked": True,
    "required_quiz_slug": "quiz-4-1",
    "quizzes": [
        {
            "slug": "quiz-4-1",
            "title": "OpenSpec 技能测验",
            "passing_score": 60,
            "questions": [
                {
                    "question_text": "OpenSpec 的核心理念是什么？",
                    "question_type": "single",
                    "correct_answer": "1",
                    "explanation": "OpenSpec 的核心理念是 Spec-Driven（规格驱动）、Change-Based（变更驱动）、Artifact-Driven（工件驱动）。",
                    "order": 0,
                    "options": [
                        {"option_text": "快速编码，尽快交付", "option_index": 0},
                        {"option_text": "Spec-Driven、Change-Based、Artifact-Driven", "option_index": 1},
                        {"option_text": "测试驱动开发", "option_index": 2},
                        {"option_text": "敏捷开发", "option_index": 3}
                    ]
                },
                {
                    "question_text": "以下哪些场景适合使用 explore 模式？（多选）",
                    "question_type": "multiple",
                    "correct_answer": "0,1,3",
                    "explanation": "explore 模式适用于探索问题空间、收集需求和分析技术方案，不适合紧急修复。",
                    "order": 1,
                    "options": [
                        {"option_text": "探索问题空间", "option_index": 0},
                        {"option_text": "收集需求", "option_index": 1},
                        {"option_text": "紧急 bug 修复", "option_index": 2},
                        {"option_text": "分析技术方案", "option_index": 3}
                    ]
                },
                {
                    "question_text": "以下哪个技能用于快速向前推进变更，自动创建所有工件？",
                    "question_type": "single",
                    "correct_answer": "2",
                    "explanation": "openspec-ff-change 用于快速推进变更，自动生成所有工件。",
                    "order": 2,
                    "options": [
                        {"option_text": "openspec-new-change", "option_index": 0},
                        {"option_text": "openspec-continue-change", "option_index": 1},
                        {"option_text": "openspec-ff-change", "option_index": 2},
                        {"option_text": "openspec-apply-change", "option_index": 3}
                    ]
                },
                {
                    "question_text": "当你想要开始实现代码时，应该使用哪个技能？",
                    "question_type": "single",
                    "correct_answer": "3",
                    "explanation": "openspec-apply-change 用于应用变更，开始实现代码。",
                    "order": 3,
                    "options": [
                        {"option_text": "openspec-new-change", "option_index": 0},
                        {"option_text": "openspec-explore", "option_index": 1},
                        {"option_text": "openspec-verify-change", "option_index": 2},
                        {"option_text": "openspec-apply-change", "option_index": 3}
                    ]
                },
                {
                    "question_text": "OpenSpec 工作流的正确顺序是什么？",
                    "question_type": "single",
                    "correct_answer": "1",
                    "explanation": "OpenSpec 的正确工作流是 Proposal → Design → Specs → Tasks → Implementation。",
                    "order": 4,
                    "options": [
                        {"option_text": "Design → Proposal → Tasks → Specs → Implementation", "option_index": 0},
                        {"option_text": "Proposal → Design → Specs → Tasks → Implementation", "option_index": 1},
                        {"option_text": "Tasks → Specs → Design → Proposal → Implementation", "option_index": 2},
                        {"option_text": "Implementation → Tasks → Specs → Design → Proposal", "option_index": 3}
                    ]
                }
            ]
        }
    ],
    "resources": [
        {
            "resource_type": "cheatsheet",
            "title": "OpenSpec 技能速查表",
            "content": "## OpenSpec 技能速查表\n\n### openspec-new-change\n- **用途**：创建新的变更\n- **适用场景**：新功能开发、bug 修复、代码重构\n- **命令**：`openspec new change <change-name>`\n\n### openspec-explore\n- **用途**：探索模式，思考和分析\n- **适用场景**：探索问题空间、收集需求、分析技术方案\n- **命令**：`openspec explore --change <change-name>`\n\n### openspec-continue-change\n- **用途**：继续变更，创建下一个工件\n- **适用场景**：完成 proposal 后继续创建 design\n- **命令**：`openspec continue change <change-name>`\n\n### openspec-ff-change\n- **用途**：快速推进变更，自动创建所有工件\n- **适用场景**：快速原型、熟悉的任务、时间紧迫\n- **命令**：`openspec ff change <change-name>`\n\n### openspec-apply-change\n- **用途**：应用变更，开始实现\n- **适用场景**：工件准备就绪，开始编写代码\n- **命令**：`openspec apply change <change-name>`\n\n### openspec-archive-change\n- **用途**：归档完成的变更\n- **适用场景**：变更已完成，清理工作区\n- **命令**：`openspec archive change <change-name>`\n\n### openspec-verify-change\n- **用途**：验证变更实现\n- **适用场景**：实现完成后，确保符合规格\n- **命令**：`openspec verify change <change-name>`",
            "extra_data": {"cheatsheet_type": "openspec_skills"}
        },
        {
            "resource_type": "template",
            "title": "OpenSpec 完整工作流示例",
            "content": "## OpenSpec 完整工作流示例\n\n### 场景：添加用户认证功能\n\n#### 步骤 1：创建新变更\n```bash\nopenspec new change add-user-auth\n```\n\n#### 步骤 2：查看变更状态\n```bash\nopenspec status --change add-user-auth\n```\n输出：\n```\nChange: add-user-auth\nStatus: 0/4 artifacts complete\n\nArtifacts:\n- [ ] proposal (ready)\n- [ ] design (waiting)\n- [ ] specs (waiting)\n- [ ] tasks (waiting)\n```\n\n#### 步骤 3：获取 Proposal 指令\n```bash\nopenspec instructions proposal --change add-user-auth\n```\n\n#### 步骤 4：创建 Proposal\n编辑 `openspec/changes/add-user-auth/proposal.md`：\n```markdown\n# Proposal: Add User Authentication\n\n## Why\n\n为什么要做这个变更？解决什么问题？\n\n## What Changes\n\n具体要做什么改动？\n\n## Capabilities\n\n新增哪些能力？\n\n## Impact\n\n预期带来什么影响？\n```\n\n#### 步骤 5：继续创建 Design\n```bash\nopenspec continue change add-user-auth\n```\n\n#### 步骤 6：创建 Specs\n```bash\nopenspec continue change add-user-auth\n```\n\n#### 步骤 7：创建 Tasks\n```bash\nopenspec continue change add-user-auth\n```\n\n#### 步骤 8：应用变更\n```bash\nopenspec apply change add-user-auth\n```\n\n#### 步骤 9：验证实现\n```bash\nopenspec verify change add-user-auth\n```\n\n#### 步骤 10：归档变更\n```bash\nopenspec archive change add-user-auth\n```",
            "extra_data": {"template_type": "workflow_example"}
        },
        {
            "resource_type": "template",
            "title": "Spec 模板合集",
            "content": "## Spec 模板合集\n\n### Proposal 模板\n\n```markdown\n# Proposal: [变更名称]\n\n## Why\n\n为什么要做这个变更？解决什么问题？\n\n## What Changes\n\n具体要做什么改动？\n\n## Capabilities\n\n新增哪些能力？\n\n## Impact\n\n预期带来什么影响？\n```\n\n### Design 模板\n\n```markdown\n# Design: [变更名称]\n\n## Context\n\n当前背景和现状。\n\n## Goals\n\n目标和范围。\n\n## Decisions\n\n关键决策和权衡考虑。\n\n## Risks\n\n潜在风险和应对方案。\n```\n\n### Spec 模板\n\n```markdown\n# Spec: [规格名称]\n\n## Requirements\n\n- Requirement 1\n- Requirement 2\n\n## Scenarios\n\n### Scenario: [场景名称]\n- WHEN [条件]\n- THEN [结果]\n```\n\n### Tasks 模板\n\n```markdown\n# Tasks: [变更名称]\n\n## Task 1: [任务名称]\n\n**Files:**\n- Create: `path/to/file.py`\n- Modify: `path/to/file.py:10-20`\n\n**Steps:**\n1. [步骤 1]\n2. [步骤 2]\n3. [步骤 3]\n```\n\n### Rules 模板\n\n```markdown\n# AI 助手行为规范\n\n## [类别名称]\n\n1. **规则 1**：规则内容\n2. **规则 2**：规则内容\n```",
            "extra_data": {"template_type": "spec_templates"}
        }
    ]
}

course_data["chapters"].append(chapter4)
print("第 4 章完成...")

# ============ 第 5 章：三大工具对比 ============
chapter5_content = """## 全景视角：三大工具对比

在深入学习了 OpenSpec 之后，让我们退后一步，看看整个 AI 编程工具的全景图。

### 三大主流工具

目前主流的 AI 编程辅助工具有三大类：

| 工具类型 | 代表 | 特点 |
|----------|------|------|
| **Rules 驱动** | Claude Rules, Cursor Rules | 通过规则文件约束 AI 行为 |
| **Spec 驱动** | OpenSpec, Superpowers | 通过规格文档指导开发 |
| **对话驱动** | GitHub Copilot Chat, Cursor Chat | 通过自然语言对话 |

### 详细对比

#### 1. Rules 驱动

**代表工具**：Claude Rules, Cursor Rules

**工作原理**：
- 在项目根目录创建 `.cursorrules` 或 `.clinerules` 文件
- AI 在每次回应前读取规则
- 规则作为系统提示的一部分

**优点**：
- ✅ 简单易用，上手快
- ✅ 轻量级，不增加额外流程
- ✅ 适合小型项目和个人使用

**缺点**：
- ❌ 缺乏结构化的开发流程
- ❌ 难以管理大型复杂项目
- ❌ 规则之间可能冲突

**适用场景**：
- 个人项目
- 快速原型
- 简单修改和维护

#### 2. Spec 驱动

**代表工具**：OpenSpec, Superpowers

**工作原理**：
- 创建结构化的规格文档（Proposal, Design, Spec, Tasks）
- AI 按照规格逐步实现
- 每个变更都有完整的记录

**优点**：
- ✅ 结构化的开发流程
- ✅ 适合大型复杂项目
- ✅ 变更可追溯、可复用
- ✅ 团队协作友好

**缺点**：
- ❌ 学习曲线较陡
- ❌ 前期投入时间较多
- ❌ 对小型项目可能过重

**适用场景**：
- 企业级应用
- 团队协作项目
- 需要长期维护的项目

#### 3. 对话驱动

**代表工具**：GitHub Copilot Chat, Cursor Chat

**工作原理**：
- 通过自然语言对话与 AI 交互
- 实时获取代码建议和解释
- 上下文感知的对话

**优点**：
- ✅ 最自然的使用方式
- ✅ 即时反馈
- ✅ 学习成本低

**缺点**：
- ❌ 缺乏长期记忆
- ❌ 难以追踪变更历史
- ❌ 依赖用户的 prompt 能力

**适用场景**：
- 快速问答
- 代码解释
- 学习和探索

### 选择决策树

```
你需要什么？
│
├─ 快速修改/简单任务
│  └─> Rules 驱动（轻量、快速）
│
├─ 大型项目/团队协作
│  └─> Spec 驱动（结构化、可追溯）
│
├─ 学习/探索/问答
│  └─> 对话驱动（自然、即时）
│
└─ 不确定
   └─> 先用 Rules，复杂了再上 Spec
```

### 迁移指南

#### 从 Rules 迁移到 OpenSpec

如果你已经在用 Rules，想要升级到 OpenSpec：

**步骤 1：评估当前状态**
- 梳理现有的 rules 文件
- 识别哪些规则可以保留

**步骤 2：创建第一个 Change**
```bash
openspec new change migrate-rules
```

**步骤 3：将 rules 转换为 specs**
- 将通用规则放入通用 specs
- 将项目特定规则放入项目 specs

**步骤 4：逐步采用 Spec 流程**
- 从简单的变更开始
- 熟悉 Proposal → Design → Specs → Tasks 流程

#### 从对话驱动迁移到 OpenSpec

**步骤 1：开始记录变更**
- 即使是简单的对话，也记录变更意图

**步骤 2：学习写 Proposal**
- 每次变更前写一个简短的 proposal

**步骤 3：逐步引入 Design 和 Specs**
- 对于复杂变更，编写 design 和 specs

### 我的建议

根据我的经验：

1. **个人小项目**：Rules 就够用了
2. **工作项目**：强烈建议使用 OpenSpec
3. **团队协作**：必须用 OpenSpec 或类似工具
4. **学习阶段**：可以先从对话开始，然后学 Rules，最后掌握 OpenSpec

### 工具组合使用

实际上，你不需要三选一。最佳实践是**组合使用**：

```
日常对话（快速问答）
    ↓
Rules（约束 AI 行为）
    ↓
OpenSpec（管理复杂变更）
```

**我的日常配置**：

- **基础**：配置项目 rules，约束 AI 基本行为
- **复杂任务**：使用 OpenSpec 管理变更
- **快速问答**：直接用对话模式

---

**恭喜完成课程！** 现在你已经掌握了 AI 编程的核心方法论和工具。接下来就是实践、实践、再实践！"""

chapter5 = {
    "slug": "tools-comparison",
    "title": "第五章：对比思考 - 三大工具对比 ⚖️",
    "order": 5,
    "content": chapter5_content,
    "chapter_type": "story",
    "video_url": None,
    "is_locked": True,
    "required_quiz_slug": "quiz-5-1",
    "quizzes": [
        {
            "slug": "quiz-5-1",
            "title": "工具选择测验",
            "passing_score": 60,
            "questions": [
                {
                    "question_text": "以下哪些是主流的 AI 编程工具类型？（多选）",
                    "question_type": "multiple",
                    "correct_answer": "0,1,2",
                    "explanation": "Rules 驱动、Spec 驱动、对话驱动是三大主流 AI 编程工具类型。",
                    "order": 0,
                    "options": [
                        {"option_text": "Rules 驱动", "option_index": 0},
                        {"option_text": "Spec 驱动", "option_index": 1},
                        {"option_text": "对话驱动", "option_index": 2},
                        {"option_text": "测试驱动", "option_index": 3}
                    ]
                },
                {
                    "question_text": "如果你的项目是个人小项目，需求简单快速，应该选择哪种工具类型？",
                    "question_type": "single",
                    "correct_answer": "0",
                    "explanation": "Rules 驱动简单易用，上手快，适合个人小项目。",
                    "order": 1,
                    "options": [
                        {"option_text": "Rules 驱动", "option_index": 0},
                        {"option_text": "Spec 驱动", "option_index": 1},
                        {"option_text": "对话驱动", "option_index": 2},
                        {"option_text": "都需要", "option_index": 3}
                    ]
                },
                {
                    "question_text": "对于企业级大型团队协作项目，哪种工具类型最合适？",
                    "question_type": "single",
                    "correct_answer": "1",
                    "explanation": "Spec 驱动提供结构化的开发流程，适合大型复杂项目和团队协作。",
                    "order": 2,
                    "options": [
                        {"option_text": "Rules 驱动", "option_index": 0},
                        {"option_text": "Spec 驱动", "option_index": 1},
                        {"option_text": "对话驱动", "option_index": 2},
                        {"option_text": "都不合适", "option_index": 3}
                    ]
                }
            ]
        }
    ],
    "resources": [
        {
            "resource_type": "guide",
            "title": "工具选择决策树",
            "content": "## 工具选择决策树\n\n### 决策流程\n\n```\n开始\n │\n ↓\n你的项目是什么类型？\n │\n ├─ 个人小项目/快速原型\n │  └─> Rules 驱动\n │     - 配置简单\n │     - 快速上手\n │     - 轻量级\n │\n ├─ 企业级应用/团队协作\n │  └─> Spec 驱动\n │     - 结构化流程\n │     - 变更可追溯\n │     - 团队协作友好\n │\n ├─ 学习探索/快速问答\n │  └─> 对话驱动\n │     - 自然交互\n │     - 即时反馈\n │     - 学习成本低\n │\n └─ 不确定/混合型\n    └─> 组合使用\n       - Rules 为基础\n       - Spec 管理复杂变更\n       - 对话用于问答\n```\n\n### 快速决策表\n\n| 项目类型 | 团队规模 | 推荐工具 | 理由 |\n|----------|----------|----------|------|\n| 个人项目 | 1 人 | Rules | 轻量快速 |\n| 创业公司 | 2-10 人 | Rules+Spec | 平衡灵活和结构 |\n| 企业项目 | 10+ 人 | Spec | 协作和追溯 |\n| 开源项目 | 分布式 | Spec | 文档化和协作 |\n| 学习项目 | 1 人 | 对话 | 学习和探索 |\n\n### 迁移路径\n\n```\n对话驱动 → Rules → Spec\n（入门）   （进阶） （专家）\n```\n\n### 常见场景\n\n**场景 1**：我想快速修改一个函数\n→ Rules 驱动（直接在 rules 中约束）\n\n**场景 2**：我要开发一个新功能\n→ Spec 驱动（创建 change，按流程推进）\n\n**场景 3**：我想了解某段代码\n→ 对话驱动（直接问 AI）",
            "extra_data": {"guide_type": "decision_tree"}
        },
        {
            "resource_type": "guide",
            "title": "从 Rules 迁移到 OpenSpec 指南",
            "content": "## 从 Rules 迁移到 OpenSpec 指南\n\n### 为什么迁移？\n\n从 Rules 迁移到 OpenSpec 的原因：\n\n- ✅ 项目规模增长，需要更结构化的管理\n- ✅ 团队协作需求增加\n- ✅ 需要变更追溯和文档化\n- ✅ 提高开发效率和质量\n\n### 迁移步骤\n\n#### 步骤 1：评估当前状态\n\n梳理现有的 rules 文件：\n```bash\n# 列出所有 rules 文件\nfind . -name \"*.rules\" -o -name \".*rules\"\n```\n\n分类规则：\n- 通用规则（可保留）\n- 项目特定规则（转换为 specs）\n- 过时规则（废弃）\n\n#### 步骤 2：创建第一个 Change\n\n```bash\n# 创建迁移变更\nopenspec new change migrate-rules-to-spec\n\n# 创建 proposal\nopenspec instructions proposal --change migrate-rules-to-spec\n```\n\n#### 步骤 3：转换规则为 Specs\n\n将 rules 转换为 specs 的示例：\n\n**原 Rules 文件**：\n```markdown\n# Coding Rules\n\n1. 最小化修改\n2. 保持原有风格\n3. 添加必要的注释\n```\n\n**转换后 Spec**：\n```markdown\n# Spec: Code Modification Guidelines\n\n## Requirements\n\n### Requirement: Minimal Changes\n- AI should only modify explicitly requested code\n- Avoid unnecessary refactoring\n\n### Requirement: Style Consistency\n- Maintain existing code style\n- Follow project conventions\n```\n\n#### 步骤 4：逐步采用 Spec 流程\n\n从小变更开始：\n\n```bash\n# 1. 创建小变更\nopenspec new change small-feature\n\n# 2. 按流程推进\nopenspec continue change small-feature  # Design\nopenspec continue change small-feature  # Specs\nopenspec continue change small-feature  # Tasks\n\n# 3. 应用变更\nopenspec apply change small-feature\n```\n\n### 常见问题\n\n**Q：迁移需要多长时间？**\nA：取决于项目规模，通常 1-2 周可以完成基础迁移。\n\n**Q：旧的 rules 还要保留吗？**\nA：建议保留作为参考，但逐步过渡到 specs。\n\n**Q：团队如何适应新流程？**\nA：从小变更开始，逐步增加复杂度，提供培训。\n\n### 最佳实践\n\n1. **渐进式迁移**：不要一次性全部转换\n2. **保留历史**：旧 rules 归档保留\n3. **培训团队**：确保团队成员理解 Spec 流程\n4. **持续改进**：根据实践调整 specs",
            "extra_data": {"guide_type": "migration"}
        }
    ]
}

course_data["chapters"].append(chapter5)
print("第 5 章完成...")

# 更新统计数据
course_data["export_stats"] = {
    "chapters_count": 5,
    "quizzes_count": 5,
    "questions_count": 18,
    "options_count": 72,
    "resources_count": 12
}

# 保存完整的优化课程数据
output_file = '/Users/huazhongmin/IdeaProjects/tools/course_data/course-export-optimized-v2.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(course_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 优化完成！课程数据已保存到：{output_file}")
print(f"\n统计数据:")
print(f"  - 章节数：{course_data['export_stats']['chapters_count']}")
print(f"  - 测验数：{course_data['export_stats']['quizzes_count']}")
print(f"  - 题目数：{course_data['export_stats']['questions_count']}")
print(f"  - 选项数：{course_data['export_stats']['options_count']}")
print(f"  - 资源数：{course_data['export_stats']['resources_count']}")
