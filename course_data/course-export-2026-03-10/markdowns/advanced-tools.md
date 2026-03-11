---
slug: advanced-tools
title: 第四章：进阶工具 - OpenSpec & Superpowers 🚀
order: 4
chapter_type: code
is_locked: true
---

## 进入高手阶段！
掌握了 rules 之后，我开始探索更强大的工具。
### OpenSpec 是什么？
OpenSpec 是一个基于 Spec 的开发方法论，核心思想是：
1. **Spec First**：先写规范，再生成代码
2. **AI Native**：专为 AI 协作设计
3. **Iterative**：支持迭代和版本管理
4. **Skill-Based**：通过技能系统实现复杂任务
### OpenSpec 技能详解
#### 技能 1：openspec-new-change
**用途：** 创建一个新的变更（change），启动结构化的开发流程。
**什么时候使用：**
- ✅ 有一个新功能要开发
- ✅ 需要修复一个复杂的 bug
- ✅ 要进行代码重构
- ✅ 不确定具体实现方案，需要探索
**使用示例：**
```bash
# 创建一个名为 add-user-auth 的变更
openspec new change "add-user-auth"
```
#### 技能 2：openspec-explore（探索模式）
**用途：** 进入探索模式，作为思考伙伴帮助探索想法、调查问题、澄清需求。
**什么时候使用：**
- ✅ 需求不明确，需要澄清
- ✅ 面临多个技术方案，需要比较
- ✅ stuck 在某个问题上，需要灵感
**重要提醒：** 探索模式不写代码！只用于思考和捕获想法。
#### 技能 3：openspec-continue-change
**用途：** 继续一个进行中的变更，创建下一个所需的 artifact（产物）。
**产物创建顺序（spec-driven schema）：**
```
proposal.md → specs/<capability>/spec.md → design.md → tasks.md
```
#### 技能 4：openspec-ff-change（Fast-Forward）
**用途：** 快速跳过所有 artifact 的创建过程，一次性生成实现所需的所有产物。
**什么时候使用：**
- ✅ 需求明确，不需要逐步讨论
- ✅ 时间紧张，想跳过中间的确认步骤
- ✅ 已经有清晰的设计思路
#### 技能 5：openspec-apply-change
**用途：** 实现变更中的任务，按照 tasks.md 逐一完成开发工作。
**工作流程：**
```
1. 读取 tasks.md → 2. 识别未完成的任务 → 3. 逐一实现
```
#### 技能 6：openspec-archive-change
**用途：** 归档已完成的变更。
### Superpowers 技能包
Superpowers（brainstorming）是一套增强 AI 能力的技能系统：
- 🔍 **代码理解**：快速理解大型代码库
- 📝 **文档生成**：自动生成技术文档
- 🧪 **测试生成**：自动编写单元测试
- 🐛 **Bug 修复**：智能定位和修复问题
### Spec 文件示例
### 我的工作流
```
写 Spec → AI 生成代码 → Code Review → 通过？→ 合并
                                    ↓
                                  不通过 → 修改 Spec
```
### 效率对比
| 开发阶段 | 传统方式 | AI + OpenSpec |
|----------|----------|---------------|
| 需求分析 | 2 小时 | 30 分钟 |
| 代码实现 | 8 小时 | 2 小时 |
| 代码 Review | 2 小时 | 30 分钟 |
| 单元测试 | 4 小时 | 1 小时 |
| **总计** | **16 小时** | **4 小时** |
效率提升 **4 倍**！🚀
---
**最后一章**：OpenSpec vs spec-kit vs Superpowers 大对比！

---

## 资源


### Spec 文件示例

**类型**: code_sample



**元数据**:
```json
{
  "example": "user-login.spec"
}
```
