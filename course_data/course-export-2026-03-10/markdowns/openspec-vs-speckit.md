---
slug: openspec-vs-speckit
title: 第五章：对比思考 - 三大工具对比 ⚖️
order: 5
chapter_type: video
is_locked: true
---

## 三大工具全方位对比！
GitHub 有 spec-kit，Claude 有 Superpowers (brainstorming)，它们和 OpenSpec 有什么区别？
### 完整对比表
| 对比维度 | OpenSpec | spec-kit | Superpowers (brainstorming) |
|----------|----------|----------|----------------------------|
| **定位** | Spec 驱动的结构化开发方法论 | GitHub 官方的 Spec 工具包 | 头脑风暴与设计探索技能 |
| **目标用户** | 追求高效 AI 协作的团队 | GitHub 重度用户、企业团队 | 需要设计先行的项目 |
| **学习曲线** | 🟢 平缓（中文友好） | 🟡 中等（英文文档） | 🟢 低（对话式交互） |
| **适用场景** | 功能开发、需求实现 | 大型项目、企业级规范 | 需求探索、设计讨论 |
| **工作流** | new→explore→continue→apply→archive | propose→spec→design→build | explore→design→approve→plan |
| **AI 协作深度** | 🔥 深度集成（技能系统） | 🔌 插件模式 | 🤖 原生 AI 对话 |
### 工具选择决策树
```
需求是否清晰？
│
├── 否 ──→ Superpowers (brainstorming) 探索
│          │
│          ▼
│       明确需求后
│
├── 是，复杂功能 ──→ OpenSpec
│                   ├── 需求明确？→ /opsx:ff (快速创建)
│                   └── 需要讨论？→ /opsx:new + continue
│
└── 是，简单修改 ──→ 直接用 AI 对话
```
### 如何结合使用三个工具
**推荐的工作流：**
```
第一阶段              第二阶段              第三阶段
─────────            ─────────            ─────────
Superpowers    →     OpenSpec       →     编码实现
(探索需求)            (创建规范)            (apply)
     │                   │
     │                   ▼
     │              创建 Spec
     │                   │
     ▼                   ▼
 探索清楚后          逐一实现任务
```
**实际案例：开发用户认证系统**
1. **阶段 1：使用 Superpowers 探索（需求不明确）**
   - 分析认证方案（JWT vs Session vs OAuth）
   - 比较各方案优劣
   - 产出：design doc（设计文档）
2. **阶段 2：使用 OpenSpec 创建规范（需求明确后）**
   - `/opsx:new add-user-auth`
   - 创建 proposal.md、specs/、design.md、tasks.md
3. **阶段 3：使用 OpenSpec Apply 实现**
   - `/opsx:apply add-user-auth`
   - 逐一完成任务
### 各工具的最佳实践时刻
**OpenSpec 适合：**
- ✅ "我们要开发一个新的仪表盘功能"
- ✅ "需要重构用户模块，提升可维护性"
- ✅ "这个 bug 需要系统性修复"
**spec-kit 适合：**
- ✅ "这是一个开源项目，需要社区讨论"
- ✅ "我们要写一个 RFC，征求团队意见"
- ✅ "需要与企业 GitHub 工作流集成"
**Superpowers 适合：**
- ✅ "我有一个想法，但不确定是否可行"
- ✅ "这个项目应该怎么架构？"
- ✅ "方案 A 和方案 B 哪个更好？"
### 总结
> **重要的不是选择哪个工具，而是掌握 Spec-Driven 的思维方式。**
无论选择哪个工具，核心都是：
1. **先思考，再行动** - 不要冲动编码
2. **文档化** - 把想法写下来
3. **结构化** - 分解复杂问题
4. **可迭代** - 允许修改和完善
**我们的建议：**
| 你的情况 | 推荐工具 |
|----------|----------|
| 国内团队，中文环境 | OpenSpec |
| GitHub 重度用户 | spec-kit |
| 需求不明确，需要探索 | Superpowers |
| 复杂功能开发 | OpenSpec |
| 简单修改 | 直接用 AI 对话 |
---
## 🎉 恭喜你完成课程！
现在你已经掌握了：
- ✅ VibeCoding 的核心理念
- ✅ Rules 的使用方法
- ✅ OpenSpec 的基础知识
- ✅ Spec 文件的编写技巧
- ✅ 三大工具的选择策略
**开始你的 VibeCoding 之旅吧！** 🚀
---