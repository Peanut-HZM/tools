# 能力规格：课程资源扩展

## ADDED Requirements

### Requirement: 第 1 章资源 - 沟通模板

第 1 章应包含以下资源：

1. **前端修改沟通模板** (`frontend-prompt-checklist.md`)
   - 目标组件：文件路径
   - 容器/区域：具体修改位置
   - 样式变更：CSS/Tailwind 类名
   - 功能逻辑：交互行为
   - 调用接口：后端 API
   - 入参示例/出参示例
   - 类型定义：TypeScript 类型

2. **后端修改沟通模板** (`backend-prompt-checklist.md`)
   - 目标接口/函数
   - 功能变更
   - 数据模型变更
   - 错误处理
   - 日志记录
   - 测试要求

#### Scenario: 学习者使用第 1 章资源
- **WHEN** 学习者需要修改代码时
- **THEN** 能参考沟通模板编写清晰的指令

### Requirement: 第 2 章资源 - 问题诊断清单

第 2 章应包含以下资源：

1. **AI 编程常见问题诊断清单** (`common-ai-problems-checklist.md`)
   - 问题 1：AI 乱改代码
     - 可能原因
     - 解决方案
   - 问题 2：AI 理解错需求
     - 可能原因
     - 解决方案
   - 问题 3：AI 输出质量不稳定
     - 可能原因
     - 解决方案

#### Scenario: 学习者使用第 2 章资源
- **WHEN** 学习者遇到 AI 编程问题时
- **THEN** 能通过诊断清单定位问题并找到解决方案

### Requirement: 第 3 章资源 - Rules 模板库

第 3 章应包含以下资源：

1. **Rules 模板库** (`rules-templates/`)
   - `general-rules.md` - 通用规则（最小化修改、保持原有风格等）
   - `frontend-rules.md` - 前端规则（组件修改、样式变更等）
   - `backend-rules.md` - 后端规则（API 修改、数据处理等）

2. **Rules 编写检查清单** (`rules-writing-checklist.md`)
   - 是否具体明确
   - 是否可执行
   - 是否有优先级
   - 是否覆盖常见场景

#### Scenario: 学习者使用第 3 章资源
- **WHEN** 学习者需要编写 Rules 时
- **THEN** 能参考模板库和检查清单编写有效的 Rules

### Requirement: 第 4 章资源 - OpenSpec 技能资源

第 4 章应包含以下资源：

1. **OpenSpec 技能速查表** (`openspec-skill-cheatsheet.md`)
   - 每个技能的用途
   - 适用场景
   - 常用命令
   - 配合技能

2. **Spec 模板** (`templates/`)
   - `proposal-template.md` - Proposal 模板
   - `spec-template.md` - Spec 模板
   - `design-template.md` - Design 模板
   - `tasks-template.md` - Tasks 模板

3. **完整实战案例** (`complete-workflow-example.md`)
   - 从 new 到 archive 的全流程
   - 每个步骤的说明和输出
   - 常见问题和解决方案

#### Scenario: 学习者使用第 4 章资源
- **WHEN** 学习者需要使用 OpenSpec 时
- **THEN** 能参考速查表、模板和实战案例完成项目

### Requirement: 第 5 章资源 - 工具选择资源

第 5 章应包含以下资源：

1. **工具选择决策树** (`tool-selection-decision-tree.pdf`)
   - 可打印的 PDF 版本
   - 可视化的决策流程

2. **迁移指南** (`migration-guide.md`)
   - 从 spec-kit 迁移到 OpenSpec 的步骤
   - 从 Superpowers 迁移到 OpenSpec 的步骤
   - 常见问题和解决方案

#### Scenario: 学习者使用第 5 章资源
- **WHEN** 学习者需要选择或迁移工具时
- **THEN** 能参考决策树和迁移指南做出正确决策
