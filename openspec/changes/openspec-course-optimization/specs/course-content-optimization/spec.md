# 能力规格：课程内容优化

## ADDED Requirements

### Requirement: 第 1 章内容 - 最初的我 - 谨慎使用 AI 😰

课程第 1 章应包含以下内容：

1. **故事化开场**：AI 编程新手的真实心态和经历
2. **技术背景**：为什么 AI 需要详细沟通（LLM 工作原理简介）
3. **沟通模板**：前端/后端修改的完整 checklist
4. **对比案例**：错误指令 vs 正确指令的实际案例

内容应使用 Markdown 格式，包含至少 3 个实际代码示例。

#### Scenario: 学习者阅读第 1 章
- **WHEN** 学习者阅读第 1 章内容
- **THEN** 能看到故事化的开场、技术背景解释、沟通模板和对比案例

### Requirement: 第 2 章内容 - 遇到问题 - AI 乱改代码的困扰 🤯

课程第 2 章应包含以下内容：

1. **经典翻车场景合集**：3-4 个真实案例（修改一个函数改十个文件、理解错需求等）
2. **问题根源分析**：缺少 Rules 约束、需求描述模糊、上下文缺失、AI 过度理解
3. **引出 Rules 的必要性**：为第 3 章做铺垫

内容应使用 Markdown 格式，包含对话式案例和问题分析表格。

#### Scenario: 学习者阅读第 2 章
- **WHEN** 学习者阅读第 2 章内容
- **THEN** 能识别 AI 编程中常见的问题场景及其根源

### Requirement: 第 3 章内容 - 发现规则 - rules 的拯救 🎉

课程第 3 章应包含以下内容：

1. **Rules 概念详解**：
   - 什么是 Rules（定义、形式、作用）
   - Rules 为什么有效（AI 理解机制）
   - Rules 如何工作（约束 AI 行为的原理）

2. **Rules 编写指南**：
   - 基本结构（Markdown 格式）
   - 语法规范（清晰的指令、可执行的要求）
   - 最佳实践（具体、可执行、有优先级）

3. **实战案例**：
   - 通用 Rules 示例
   - 前端 Rules 示例
   - 后端 Rules 示例
   - 全栈项目 Rules 示例

4. **效果对比**：
   - 使用 Rules 前：AI 输出示例
   - 使用 Rules 后：AI 输出示例

#### Scenario: 学习者阅读第 3 章
- **WHEN** 学习者阅读第 3 章内容
- **THEN** 能理解 Rules 的概念、编写方法，并能参考实战案例编写自己的 Rules

### Requirement: 第 4 章内容 - 进阶工具 - OpenSpec & Superpowers 🚀

课程第 4 章应包含以下内容：

1. **OpenSpec 核心概念**：
   - Change（变更）的概念和生命周期
   - Artifact（产物）的类型和作用（Proposal、Design、Spec、Tasks）
   - Spec-Driven 工作流的优势

2. **技能系统详解**（每个技能包含用途、适用场景、使用方法、实际案例、配合技能）：
   - `openspec-new-change` - 创建新变更
   - `openspec-explore` - 探索模式
   - `openspec-continue-change` - 继续变更
   - `openspec-ff-change` - 快速创建
   - `openspec-apply-change` - 实现任务
   - `openspec-archive-change` - 归档变更
   - `openspec-verify-change` - 验证变更

3. **完整工作流示例**：
   ```
   需求不明确 → openspec-explore
   需求明确后 → openspec-new-change 或 openspec-ff-change
   创建产物 → openspec-continue-change（如需要）
   实现任务 → openspec-apply-change
   验证结果 → openspec-verify-change
   归档变更 → openspec-archive-change
   ```

#### Scenario: 学习者阅读第 4 章
- **WHEN** 学习者阅读第 4 章内容
- **THEN** 能理解 OpenSpec 的核心概念，掌握每个技能的用途和使用方法，了解完整工作流

### Requirement: 第 5 章内容 - 对比思考 - 三大工具对比 ⚖️

课程第 5 章应包含以下内容：

1. **完整对比表**：OpenSpec vs spec-kit vs Superpowers (brainstorming)
   - 定位、目标用户、学习曲线、适用场景、工作流、AI 协作深度

2. **新增对比维度**：
   - 学习成本（时间投入）
   - 社区支持（文档、示例、问题解答）
   - 扩展性（自定义能力）
   - 中文友好度

3. **工具选择决策树**：根据需求清晰度、功能复杂度选择合适工具

4. **迁移指南**：
   - 从 spec-kit 迁移到 OpenSpec
   - 从 Superpowers 迁移到 OpenSpec

#### Scenario: 学习者阅读第 5 章
- **WHEN** 学习者阅读第 5 章内容
- **THEN** 能理解三大工具的区别，根据自身情况选择合适的工具
