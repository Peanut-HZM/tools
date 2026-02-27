# SpecFlow Lab - 学习分享演示平台需求文档

> **文档版本**: v1.0  
> **最后更新**: 2024-02-13  
> **状态**: ✅ 需求已完善  
> **文档类型**: Product Requirements Document (PRD)  
> **遵循标准**: PRD Best Practices + EARS Requirements Syntax

---

## 文档目录

1. [执行摘要](#零执行摘要)
2. [问题陈述](#一问题陈述)
3. [目标与成功指标](#二目标与成功指标)
4. [项目概述与愿景](#三项目概述与愿景)
5. [用户角色与用户故事](#四用户角色与用户故事)
6. [功能需求详述 (EARS格式)](#五功能需求详述ears格式)
7. [范围界定](#六范围界定)
8. [UI/UX 设计规范](#七uiux-设计规范)
9. [数据模型与API设计](#八数据模型与api设计)
10. [非功能需求](#九非功能需求)
11. [技术考虑](#十技术考虑)
12. [测试策略](#十一测试策略)
13. [风险与缓解策略](#十二风险与缓解策略)
14. [项目规划与里程碑](#十三项目规划与里程碑)
15. [依赖与假设](#十四依赖与假设)
16. [附件与参考资料](#十五附件与参考资料)

---

# 零、执行摘要

## 0.1 项目一句话描述

**SpecFlow Lab** 是一个专门用于技术分享、培训和Workshop的动画演示平台，让演讲者能够用可视化、互动的方式展示抽象的技术概念和工作流程。

## 0.2 核心价值主张

> **让技术分享从"枯燥的PPT"升级为"沉浸式的动画演示"**

传统技术分享依赖PPT和现场编码，存在以下痛点：
- ❌ PPT难以展示代码演进过程
- ❌ 现场编码风险高、容易出错
- ❌ 抽象概念难以理解
- ❌ 每次分享都需要重新准备材料

SpecFlow Lab 通过**可视化动画演示**解决这些问题，让演讲者能够：
- ✅ 用动画展示复杂的工作流程
- ✅ 预录代码演进过程，零风险演示
- ✅ 用可视化方式呈现抽象概念
- ✅ 创建可复用的演示场景库

## 0.3 关键成功因素

| 成功因素 | 描述 | 衡量标准 |
|----------|------|----------|
| 动画流畅性 | 60fps流畅动画，无卡顿 | 用户反馈满意度 > 90% |
| 易用性 | 10分钟内创建第一个演示 | 新用户上手时间 < 10分钟 |
| 可复用性 | 场景模板化，快速定制 | 平均场景创建时间 < 30分钟 |
| 演讲体验 | 控制台与Player实时同步 | 延迟 < 500ms |

## 0.4 目标受众

- **主要用户**: 技术演讲者、培训讲师、开发者倡导者
- **次要用户**: 内容创作者、产品经理、技术写作者
- **预期市场规模**: 技术社区分享者 10万+，企业内训师 5万+

---

# 一、问题陈述

## 1.1 当前痛点分析

### 🔴 痛点1：传统演示方式效果差

**现状**: 
技术演讲者主要使用PPT或现场编码来分享技术内容。

**问题**:
- PPT是静态的，无法展示动态的工作流程
- 代码截图无法展示演进过程
- 观众难以建立从需求到代码的完整认知链路

**影响**: 
观众理解度低，分享效果打折扣，技术概念传播效率低。

### 🔴 痛点2：现场编码演示风险高

**现状**: 
很多演讲者选择现场Live Coding来增加互动性。

**问题**:
- 环境配置问题导致演示失败
- 代码 typo 导致调试时间过长
- 紧张导致操作失误
- 时间控制困难

**影响**: 
演讲者压力大，演示质量不稳定，容易出现尴尬场面。

### 🔴 痛点3：内容准备成本高

**现状**: 
每次技术分享都需要从头准备演示材料。

**问题**:
- PPT制作耗时（平均4-8小时）
- 代码示例需要反复验证
- 动画效果制作成本高
- 难以复用已有内容

**影响**: 
分享频率受限，优质内容产出慢，知识传播效率低。

### 🔴 痛点4：抽象概念难以表达

**现状**: 
技术概念（如架构设计、算法流程、工作流）很难用语言描述清楚。

**问题**:
- 文字描述晦涩难懂
- 静态图表信息量有限
- 缺少渐进式展示手段

**影响**: 
观众难以深入理解，学习效果差，技术门槛难以降低。

## 1.2 目标用户画像

### 用户画像1：技术大会演讲者 "架构师 Alex"

- **年龄**: 32岁
- **职位**: 互联网公司架构师
- **场景**: 每季度参加1-2次技术大会演讲
- **痛点**: 需要展示复杂的系统架构演进，PPT难以表达
- **期望**: 用动画直观展示架构变化和代码演进

### 用户画像2：企业内训师 "讲师 Lisa"

- **年龄**: 28岁
- **职位**: 技术培训师
- **场景**: 每周进行新员工技术培训
- **痛点**: 培训内容重复但材料难以复用，学员参与度低
- **期望**: 创建标准化培训课程，支持互动演示

### 用户画像3：开发者布道师 "布道师 David"

- **年龄**: 35岁
- **职位**: 技术公司开发者关系负责人
- **场景**: 负责推广公司的开源项目和技术产品
- **痛点**: 产品功能复杂，难以在短时间内演示清楚
- **期望**: 快速创建吸引人的产品演示

---

# 二、目标与成功指标

## 2.1 产品目标

### 目标1：打造技术分享新标准

**描述**: 
成为技术分享领域首选的演示工具，替代传统PPT在代码展示场景的地位。

**成功指标**:
- 月活跃用户 (MAU) 达到 10,000+
- 用户留存率 (7日) > 40%
- NPS (净推荐值) > 50

### 目标2：降低演示内容制作门槛

**描述**: 
让技术演讲者能够在30分钟内创建高质量的技术演示场景。

**成功指标**:
- 新用户首次创建场景时间 < 30分钟
- 场景创建完成率 > 70%
- 用户满意度 > 4.5/5

### 目标3：构建演示场景生态系统

**描述**: 
建立可复用的演示场景库，让用户能够共享和使用社区模板。

**成功指标**:
- 平台场景总数 > 1,000个
- 模板复用次数 > 10,000次
- 社区贡献者 > 500人

## 2.2 业务目标

### 收入目标（未来阶段）

| 阶段 | 时间 | 目标 | 商业模式 |
|------|------|------|----------|
| MVP | 0-6个月 | 验证产品价值 | 免费公测 |
| 增长期 | 6-12个月 | 10,000用户 | 免费 + 增值服务 |
| 商业化 | 12-24个月 | 月收入 $10K+ | 订阅制 + 企业服务 |

### 用户增长目标

```
Month 1-3:   种子用户 500人（技术社区KOL）
Month 4-6:   公测用户 3,000人
Month 7-12:  活跃用户 10,000人
Year 2:      注册用户 50,000人
```

## 2.3 成功指标框架

### HEART 框架指标

| 维度 | 指标 | 目标值 | 测量方式 |
|------|------|--------|----------|
| **Happiness** | 用户满意度 | > 4.5/5 | 应用内调研 |
| **Engagement** | 每周创建场景数 | > 2个/用户 | 数据分析 |
| **Adoption** | 新用户首次创建率 | > 60% | 漏斗分析 |
| **Retention** | 7日留存率 | > 40% | 用户行为分析 |
| **Task Success** | 场景创建完成率 | > 70% | 任务完成分析 |

### 北极星指标

**核心指标**: 每周成功播放的演示场次

**原因**: 
- 直接反映产品核心价值（帮助用户成功分享）
- 综合体现用户活跃度、内容质量和产品稳定性
- 与产品目标高度一致

---

# 三、项目概述与愿景

这不是普通技术分享，而是：

• 概念科普
• 工程方法论
• Live Coding
• 动画产品演示

最终效果：
观众离开时能够：

1. 理解 Spec-Driven Development
2. 知道 Spec‑Kit vs OpenSpec 区别
3. 看到 AI 从需求 → 代码的全过程
4. 回去可以自己复现

建议总时长：90 分钟

---

# 二、演讲结构（精确到分钟）

## Part 1 — 破冰（10 min）

开场问题：

“谁让 AI 直接写过生产代码？”
“谁被 AI 改坏过项目？”

展示对比动画（PPT）：

传统 AI 编程：
Prompt → Code → Chaos

Spec Driven：
Prompt → Spec → Design → Tasks → Code

核心金句：
👉 AI 不是不会写代码，而是不理解需求。

---

# Part 2 — 什么是 Spec‑Driven Development（15 min）

## 一句话解释

Spec = 机器可读的需求文档

AI 不应该直接写代码，而应该：

像工程团队一样工作：

Product Manager → Architect → Tech Lead → Developer

Spec 就是 AI 的 Product Manager。

## 标准 Spec 结构

```
Background
Goals
Non‑Goals
User Stories
Acceptance Criteria
Risks
```

强调：
Spec 是 **可执行文档**。

---

# Part 3 — Spec‑Kit vs OpenSpec（核心 20min）

## 一、核心关系（最重要一页）

类比：

OpenSpec = HTTP 协议
Spec‑Kit = 浏览器

OpenSpec 定义：
• spec 应该长什么样
• 文件结构
• 工作流标准

Spec‑Kit 提供：
• 命令
• 模板
• 自动化工作流

## 二、深度对比表

| 维度            | Spec‑Kit     | OpenSpec  |
| ------------- | ------------ | --------- |
| 类型            | 工具实现         | 开放标准      |
| 是否可直接使用       | ✔            | ✖         |
| 是否提供 CLI / 命令 | ✔            | ✖         |
| 是否绑定 IDE      | 常见于 OpenCode | 与工具无关     |
| 作用层级          | 执行层          | 规范层       |
| 类比            | SpringBoot   | Java 语言规范 |

金句：
👉 OpenSpec 让 AI 知道写什么
👉 Spec‑Kit 让 AI 知道怎么做

---

# Part 4 — Live Workflow Demo（15 min）

现场演示：OpenCode

输入命令：

```
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.implement
```

演示生成目录：

```
.spec/features/login-lock/
   spec.md
   plan.md
   tasks.md
```

重点讲解：
AI 在“读文档再写代码”。

---

# Part 5 — 动画 Demo 系统（高潮 20min）

这是本分享的最大亮点。

目标：
让观众“看见”AI 的思考流程。

项目名：

SpecFlow Visualizer

---

# 三、Demo 系统详细设计

## 页面布局

三栏布局：

左侧：流程步骤导航
中间：动画舞台
右侧：解释面板

```
┌────────┬──────────────┬───────────┐
│ Steps  │   Animation   │ Explain   │
└────────┴──────────────┴───────────┘
```

---

# 四、五个动画阶段（逐帧设计）

## Stage 1 — Requirement

画面：
一个需求卡片缓慢浮现

内容：
"Lock account after 5 failed logins"

动画：
• Fade in
• 轻微浮动

讲解词：
"一切从需求开始"

---

## Stage 2 — Spec 生成

动画：
需求卡片 → 变形成 Markdown 文档

逐行打字：

```
## Goals
## User Stories
## Acceptance Criteria
```

讲解词：
"AI 首先写规格，而不是代码"

---

## Stage 3 — Design

动画：
文档分裂成架构节点：

AuthService
UserDB
LockService
AdminAPI

节点用线连接。

讲解词：
"然后 AI 设计系统如何实现"

---

## Stage 4 — Tasks

动画：
节点掉落 → 变成 Checklist

```
☐ Add DB field
☐ Update login service
☐ Add tests
```

逐个勾选。

讲解词：
"再拆分为工程任务"

---

## Stage 5 — Code

动画：
VSCode 窗口出现
代码逐行打印：

```
if (failedAttempts >= 5) {
  lockAccount(user)
}
```

讲解词：
"最后才写代码"

---

# 五、交互设计

顶部按钮：

Start Demo
Next Step
Auto Play
Reset

支持自动播放。

---

# 六、技术实现方案

使用：

React
Tailwind
Framer Motion
TypeScript

组件结构：

```
App
 ├─ StepSidebar
 ├─ StageCanvas
 │   ├─ RequirementStage
 │   ├─ SpecStage
 │   ├─ DesignStage
 │   ├─ TasksStage
 │   └─ CodeStage
 └─ ExplanationPanel
```

状态机：

```
step = 0..4
```

---

# 七、每个 Stage 的实现要点

## RequirementStage

• motion.div fade + float

## SpecStage

• 打字机效果
• Markdown 渲染

## DesignStage

• 节点 spring 动画
• SVG 连线

## TasksStage

• checklist 勾选动画

## CodeStage

• 代码逐行打印动画

---

# 八、分享收尾金句

1️⃣ Prompt 是玩具，Spec 才是工程
2️⃣ AI 不会取代开发者，但会取代不使用流程的开发者
3️⃣ Spec‑Driven Development = AI 时代的 DevOps

---

# 九、从 Demo 升级为长期演示平台（关键）

用户新目标：
不做 PPT → 做一个可复用的“演示平台”

平台名称建议：

SpecFlow Lab

定位：
一个专门用于 **技术分享 / 培训 / Workshop / Demo** 的演示系统。

以后每次分享只需要：
新增一个 Demo Scenario 即可。

---

# 十、平台总体架构设计

我们不做一次性 Demo，而做一个：

Spec Demo CMS 平台

包含：

• 演示场景管理
• 动画播放引擎
• 演讲者控制台
• 资料沉淀
• 多分享复用

系统分为 3 个子系统：

```
SpecFlow Lab
 ├─ Demo Player（观众展示）
 ├─ Speaker Console（演讲控制台）
 └─ Scenario CMS（内容管理）
```

---

# 十一、核心能力设计

## 1️⃣ Demo Player（全屏展示）

用于投屏演示。

功能：

• 全屏动画播放
• 步骤切换
• 自动播放
• 高亮当前步骤
• 支持代码动画

分享时只打开这个页面。

## 2️⃣ Speaker Console（讲师控制台）

讲师手机或副屏使用。

功能：

• 下一步 / 上一步
• 自动播放
• 查看讲解词
• 查看计时
• 切换场景

这相当于 PPT 遥控器。

## 3️⃣ Scenario CMS（最重要）

用于保存每次分享内容。

你以后只需要创建新 Scenario。

Scenario 包含：

• 标题
• 描述
• 步骤列表
• 每步动画类型
• 每步讲解词
• 示例代码
• 相关链接

---

# 十二、Scenario 数据模型设计

这是平台核心。

```
Scenario
  id
  title
  description
  steps[]
```

Step 数据结构：

```
Step {
  title
  type
  narration
  content
  duration
}
```

Step 类型枚举：

```
requirement
spec
design
tasks
code
architecture
comparison
custom
```

以后任何分享都可以复用。

---

# 十三、数据库设计（轻量版）

初期用 JSON 即可：

```
/scenarios
   spec-intro.json
   migration-demo.json
   testing-demo.json
```

后期可升级：

PostgreSQL

---

# 十四、前端系统架构

技术栈：

Next.js + React + Tailwind + Framer Motion

页面：

```
/
  演示列表
/player/[scenario]
/console/[scenario]
/admin
```

---

# 十五、播放器核心组件

```
PlayerPage
 ├─ StepTimeline
 ├─ AnimationStage
 ├─ NarrationPanel
```

动画引擎组件：

```
AnimationRenderer
  switch(step.type)
     requirement → RequirementAnim
     spec        → SpecAnim
     design      → GraphAnim
     tasks       → TaskAnim
     code        → CodeAnim
```

这是整个系统的核心抽象。

---

# 十六、第一批内置 Demo 场景规划

发布时建议自带 3 个 Scenario：

### 1️⃣ Spec Intro（当前分享）

Spec-Kit vs OpenSpec

### 2️⃣ Legacy Migration

旧系统迁移流程

### 3️⃣ Bug Fix Workflow

Spec 驱动修 Bug

以后可以持续增加。

---

# 十七、开发阶段规划

## Phase 1（本周）

完成 MVP：

• Demo Player
• Scenario JSON
• SpecFlow 动画

## Phase 2

• Speaker Console
• 多场景管理

## Phase 3

• Admin CMS
• 分享资料沉淀

---

# 下一步真正开发

下一步：开始生成

👉 SpecFlow Lab 前端项目完整代码结构

---

# 五、功能需求详述 (EARS格式)

> **EARS 说明**: Easy Approach to Requirements Syntax  
> 使用标准化格式定义需求，确保可测试性和无歧义性

## 5.1 Demo Player 功能需求

### FR-DP-001: 步骤导航

**优先级**: Must Have  
**类别**: Core Playback

**描述**: 
系统应支持在演示步骤之间前进、后退和跳转，确保演讲者可以灵活控制演示进度。

#### 接受标准 (EARS格式)

**AC-1: 下一步导航 (Event-Driven)**
```
WHEN 用户点击"下一步"按钮或按下右箭头键，
THEN the Demo Player SHALL 前进到下一个步骤
AND 播放该步骤的进入动画
```

**测试验证**:
- [ ] 单元测试: 点击按钮触发步骤切换
- [ ] E2E测试: 键盘快捷键响应

---

**AC-2: 上一步导航 (Event-Driven)**
```
WHEN 用户点击"上一步"按钮或按下左箭头键，
THEN the Demo Player SHALL 回退到上一个步骤
AND 播放该步骤的进入动画
```

**测试验证**:
- [ ] 单元测试: 回退功能逻辑
- [ ] E2E测试: 边界情况（第一步时禁用）

---

**AC-3: 步骤跳转 (Event-Driven)**
```
WHEN 用户在步骤预览面板中点击特定步骤，
THEN the Demo Player SHALL 直接跳转到该步骤
AND 更新当前进度指示器
```

**测试验证**:
- [ ] 集成测试: 跳转后状态一致性

---

### FR-DP-002: 自动播放

**优先级**: Must Have  
**类别**: Core Playback

**描述**: 
支持按设定时间自动切换步骤，适用于无人值守展示或视频录制。

#### 接受标准 (EARS格式)

**AC-1: 自动播放启动 (Event-Driven)**
```
WHEN 用户点击"自动播放"按钮，
THEN the Demo Player SHALL 开始按预设时长自动播放步骤
AND 在步骤间自动过渡
```

**AC-2: 自动播放速度控制 (State-Driven)**
```
WHILE 自动播放正在进行，
THEN the Demo Player SHALL 支持0.5x、1x、1.5x、2x四种播放速度
AND 速度切换实时生效不影响当前步骤
```

**AC-3: 自动播放暂停 (Event-Driven)**
```
WHEN 用户点击"暂停"按钮或按下空格键，
THEN the Demo Player SHALL 暂停当前动画和自动播放计时
AND 显示"继续"按钮
```

---

### FR-DP-003: 动画展示

**优先级**: Must Have  
**类别**: Animation

#### 接受标准 (EARS格式)

**AC-1: 需求卡片动画 (State-Driven)**
```
WHEN 系统展示"requirement"类型步骤，
THEN the Demo Player SHALL 以fade-in + float动画展示需求卡片
AND 动画时长为800ms
AND 帧率不低于60fps
```

**AC-2: Spec文档打字机效果 (State-Driven)**
```
WHEN 系统展示"spec"类型步骤，
THEN the Demo Player SHALL 以打字机效果逐行显示Markdown内容
AND 支持调整打字速度（每字符30-100ms可配置）
AND 支持语法高亮
```

**AC-3: 架构图动画 (State-Driven)**
```
WHEN 系统展示"design"类型步骤，
THEN the Demo Player SHALL 依次动画展示节点
AND 自动绘制节点间的连线（draw动画）
AND 支持点击节点高亮显示详情
```

**AC-4: 代码展示动画 (State-Driven)**
```
WHEN 系统展示"code"类型步骤，
THEN the Demo Player SHALL 逐行高亮显示代码
AND 支持语法高亮（基于代码语言）
AND 支持关键行强调显示
```

---

### FR-DP-004: 全屏与响应式

**优先级**: Must Have  
**类别**: UI/UX

#### 接受标准 (EARS格式)

**AC-1: 全屏模式 (Event-Driven)**
```
WHEN 用户点击全屏按钮或按下'F'键，
THEN the Demo Player SHALL 进入浏览器全屏模式
AND 隐藏浏览器UI元素
AND 保持所有控制功能可用
```

**AC-2: 响应式布局 (State-Driven)**
```
WHILE 浏览器窗口大小发生变化，
THEN the Demo Player SHALL 自动调整布局
AND 保持核心内容可见
AND 触发布局切换断点：
    - 桌面：>1024px（三栏布局）
    - 平板：768-1024px（两栏布局）
    - 手机：<768px（单栏布局）
```

---

## 5.2 Speaker Console 功能需求

### FR-SC-001: 远程控制

**优先级**: Must Have  
**类别**: Speaker Tools

**描述**: 
演讲者可以通过独立的控制台页面远程控制Demo Player，支持手机、平板等副屏设备。

#### 接受标准 (EARS格式)

**AC-1: 实时同步 (State-Driven)**
```
WHILE 演讲者通过控制台操作，
THEN the Speaker Console SHALL 与Demo Player保持实时同步
AND 操作延迟不超过500ms
AND 显示连接状态指示器
```

**AC-2: 连接断开处理 (Unwanted Behavior)**
```
IF 控制台与Player之间的连接断开，
THEN the system SHALL 显示离线状态
AND 尝试自动重连（最多5次，间隔2秒）
AND 重连成功后恢复同步
```

---

### FR-SC-002: 演讲辅助

**优先级**: Should Have  
**类别**: Speaker Tools

#### 接受标准 (EARS格式)

**AC-1: 讲解词显示 (State-Driven)**
```
WHILE 演示正在进行，
THEN the Speaker Console SHALL 显示当前步骤的讲解词
AND 字体大小支持调整（14-24px）
AND 显示下一步的预览
```

**AC-2: 计时器功能 (State-Driven)**
```
WHEN 演示开始播放，
THEN the Speaker Console SHALL 显示已用时间
AND 支持设置目标时长倒计时
AND 超时后显示视觉提醒
```

---

## 5.3 Scenario CMS 功能需求

### FR-CMS-001: 场景管理

**优先级**: Must Have  
**类别**: Content Management

#### 接受标准 (EARS格式)

**AC-1: 创建场景 (Event-Driven)**
```
WHEN 用户填写场景标题和描述并点击"创建"，
THEN the Scenario CMS SHALL 创建新场景
AND 分配唯一ID和slug
AND 自动重定向到场景编辑器
AND 整个过程在3秒内完成
```

**AC-2: 场景模板 (Event-Driven)**
```
WHEN 用户选择"从模板创建"，
THEN the Scenario CMS SHALL 显示可用模板列表
AND 创建时复制模板的所有步骤和设置
AND 支持用户自定义修改
```

**AC-3: 场景导入导出 (Event-Driven)**
```
WHEN 用户选择"导出演示"，
THEN the Scenario CMS SHALL 生成JSON格式的场景文件
AND 包含所有步骤内容和配置
AND 支持导入时恢复完整场景
```

---

### FR-CMS-002: 步骤编辑

**优先级**: Must Have  
**类别**: Content Management

#### 接受标准 (EARS格式)

**AC-1: 添加步骤 (Event-Driven)**
```
WHEN 用户点击"添加步骤"并选择步骤类型，
THEN the Scenario CMS SHALL 在场景末尾添加新步骤
AND 自动分配递增的顺序号
AND 打开步骤编辑器
```

**AC-2: 步骤排序 (Event-Driven)**
```
WHEN 用户拖拽步骤到新位置，
THEN the Scenario CMS SHALL 更新步骤顺序
AND 重新分配顺序号
AND 实时更新预览
```

**AC-3: 实时预览 (State-Driven)**
```
WHILE 用户编辑步骤内容，
THEN the Scenario CMS SHALL 实时显示预览
AND 延迟不超过500ms
AND 支持全屏预览模式
```

---

### FR-CMS-003: 内容编辑

**优先级**: Must Have  
**类别**: Content Management

#### 接受标准 (EARS格式)

**AC-1: Markdown编辑 (State-Driven)**
```
WHEN 用户编辑Markdown内容，
THEN the Scenario CMS SHALL 提供实时预览
AND 支持语法高亮
AND 支持常用快捷键（Ctrl+B加粗等）
```

**AC-2: 代码片段管理 (Event-Driven)**
```
WHEN 用户添加代码类型步骤，
THEN the Scenario CMS SHALL 提供代码编辑器
AND 支持30+种编程语言的语法高亮
AND 支持代码格式化
```

---

## 5.4 用户认证与权限

### FR-AUTH-001: 用户认证

**优先级**: Must Have  
**类别**: Authentication

#### 接受标准 (EARS格式)

**AC-1: 用户注册 (Event-Driven)**
```
WHEN 用户提供有效的邮箱、用户名和密码并提交注册，
THEN the system SHALL 创建用户账户
AND 发送验证邮件
AND 返回JWT访问令牌
```

**AC-2: 用户登录 (Event-Driven)**
```
WHEN 用户提供正确的用户名和密码，
THEN the system SHALL 验证凭据
AND 生成JWT令牌
AND 设置HTTPOnly Cookie
```

**AC-3: 会话管理 (State-Driven)**
```
WHILE 用户已登录，
THEN the system SHALL 维护会话状态
AND 访问令牌有效期为1小时
AND 支持使用刷新令牌续期
```

---

### FR-AUTH-002: 权限控制

**优先级**: Should Have  
**类别**: Authorization

#### 接受标准 (EARS格式)

**AC-1: 场景访问控制 (State-Driven)**
```
WHEN 用户尝试访问场景，
THEN the system SHALL 检查用户权限：
    - IF 场景为public，THEN 允许所有用户访问
    - IF 场景为private，THEN 仅允许作者访问
    - IF 场景为unlisted，THEN 允许知道链接的用户访问
```

**AC-2: 编辑权限 (State-Driven)**
```
WHEN 用户尝试编辑场景，
THEN the system SHALL 验证用户身份
AND 仅允许作者或具有编辑权限的协作者修改
```

---

# 六、范围界定

## 6.1 In Scope (范围内)

### P0 - MVP必须包含

| 功能模块 | 具体功能 | 说明 |
|----------|----------|------|
| **Demo Player** | 步骤播放、自动播放、全屏模式 | 核心展示功能 |
| **动画系统** | 5种基础动画类型（需求、Spec、设计、任务、代码） | 核心动画效果 |
| **场景管理** | 创建、编辑、删除场景 | 基础内容管理 |
| **步骤编辑** | 添加、删除、排序步骤 | 基础编辑功能 |
| **用户认证** | 注册、登录、JWT认证 | 基础身份管理 |
| **响应式UI** | 桌面、平板、手机适配 | 多设备支持 |

### P1 - 重要功能

| 功能模块 | 具体功能 | 说明 |
|----------|----------|------|
| **Speaker Console** | 远程控制、讲解词提示 | 演讲辅助工具 |
| **实时同步** | 控制台与Player同步 | WebSocket通信 |
| **模板系统** | 内置模板、模板复用 | 提升创建效率 |
| **导入导出** | JSON格式场景导入导出 | 数据可移植性 |
| **预览功能** | 单步预览、完整播放预览 | 内容验证 |

### P2 - 增值功能

| 功能模块 | 具体功能 | 说明 |
|----------|----------|------|
| **协作功能** | 多用户编辑、评论反馈 | 团队协作 |
| **版本历史** | 场景版本管理、回滚 | 内容安全 |
| **搜索筛选** | 场景搜索、标签筛选 | 内容发现 |
| **分析统计** | 播放统计、用户行为分析 | 数据洞察 |
| **社区功能** | 场景分享、点赞、收藏 | 社区建设 |

## 6.2 Out of Scope (范围外)

| 功能 | 排除原因 | 未来考虑 |
|------|----------|----------|
| **视频导出** | 技术复杂度高，需要渲染引擎 | Phase 3考虑 |
| **AI内容生成** | 超出当前范围，依赖外部API | Phase 3考虑 |
| **离线桌面应用** | 开发成本高，先验证Web版 | 根据用户反馈决定 |
| **移动原生App** | PWA可满足需求 | 用户规模扩大后 |
| **企业SSO集成** | 企业版功能 | 商业化阶段 |
| **高级权限管理** | 基础RBAC足够MVP | 协作功能完善后 |
| **多语言支持** | 先做中文市场验证 | Phase 2 |
| **插件系统** | 架构复杂度高 | 平台成熟后 |

## 6.3 技术约束

| 约束类型 | 具体约束 | 影响 |
|----------|----------|------|
| **浏览器支持** | Chrome 90+, Firefox 88+, Safari 14+ | 不兼容IE/旧版浏览器 |
| **网络要求** | 需要互联网连接 | 不支持完全离线使用 |
| **设备性能** | 需要支持WebGL的设备 | 低端设备动画性能受限 |
| **存储限制** | 浏览器本地存储限制 | 大型场景需要服务器存储 |

---

# 附录A：用户角色与用户故事

## A.1 用户角色定义

### 👤 角色1：技术演讲者 (Tech Speaker)

**角色描述**：
- 技术团队负责人、架构师、资深开发者
- 经常需要在公司内部、技术社区或大会上进行技术分享
- 希望用更具吸引力和互动性的方式展示技术概念

**核心痛点**：
- 传统PPT演示枯燥，难以展示代码演进过程
- 现场编码演示风险高，容易出错
- 难以让观众理解抽象的技术概念
- 每次分享都需要重新准备大量材料

**使用场景**：
- 技术大会 keynote 演讲
- 公司内部技术培训
- 开源项目推广演示
- 技术博客视频录制

---

### 👤 角色2：培训讲师 (Training Instructor)

**角色描述**：
- 企业内训师、技术培训机构的讲师
- 负责新员工技术培训或技能提升课程
- 需要系统性地传授技术知识和最佳实践

**核心痛点**：
- 培训内容难以复用，每次都要重新准备
- 学员参与度低，难以保持注意力
- 难以衡量学员对复杂概念的理解程度
- 培训材料更新维护成本高

**使用场景**：
- 新员工入职技术培训
- 框架/工具使用培训
- 代码审查规范培训
- 敏捷开发流程培训

---

### 👤 角色3：开发者倡导者 (Developer Advocate)

**角色描述**：
- 技术公司的布道师、社区经理
- 负责推广公司的技术产品或开源项目
- 需要创建吸引人的演示内容来展示产品特性

**核心痛点**：
- 产品功能复杂，难以在短时间演示清楚
- 需要为不同受众定制演示内容
- 演示效果难以量化和持续优化
- 缺乏标准化的演示模板

**使用场景**：
- 产品发布会演示
- 开发者大会展台演示
- 技术直播/网络研讨会
- 销售支持材料制作

---

### 👤 角色4：内容创作者 (Content Creator)

**角色描述**：
- 技术博主、YouTube/哔哩哔哩UP主
- 制作技术教程、代码解析视频
- 追求高质量的内容呈现效果

**核心痛点**：
- 视频制作周期长，动画效果制作成本高
- 代码展示不够生动，观众容易流失
- 难以保持内容的一致性和专业性
- 后期修改成本高昂

**使用场景**：
- 技术概念讲解视频
- 代码实战教程
- 开源项目介绍
- 编程技巧分享

---

## A.2 用户故事

### 📖 故事1：演讲者快速准备分享

**作为** 技术演讲者  
**我希望** 能够快速创建一个Spec-Driven Development的技术分享演示  
**以便** 在下周的技术大会上展示AI编程的最新方法论

**验收标准**：
- [ ] 能在10分钟内创建一个新的演示场景
- [ ] 可以选择内置模板快速开始
- [ ] 支持导入现有的Markdown文档自动生成演示
- [ ] 可以预览整个演示流程
- [ ] 支持导出演示配置文件以便复用

---

### 📖 故事2：讲师进行互动式培训

**作为** 培训讲师  
**我希望** 在培训过程中能够控制演示节奏并与学员互动  
**以便** 确保学员跟上思路并理解关键概念

**验收标准**：
- [ ] 讲师可以通过控制台控制演示前进/后退
- [ ] 支持暂停在特定步骤进行讲解
- [ ] 可以查看当前步骤的讲解词提示
- [ ] 支持实时标注和高亮关键内容
- [ ] 学员可以通过二维码同步观看

---

### 📖 故事3：复用和定制演示场景

**作为** 开发者倡导者  
**我希望** 能够复用已有的演示场景并进行定制  
**以便** 为不同的产品发布快速创建定制演示

**验收标准**：
- [ ] 可以复制现有的演示场景作为模板
- [ ] 支持修改步骤内容、动画效果和讲解词
- [ ] 可以调整步骤顺序和时长
- [ ] 支持添加/删除步骤
- [ ] 可以预览定制后的效果

---

### 📖 故事4：录制高质量技术视频

**作为** 内容创作者  
**我希望** 能够录制流畅的演示动画并导出视频  
**以便** 上传到视频平台作为技术教程

**验收标准**：
- [ ] 支持自动播放模式，无需手动控制
- [ ] 可以设置每个步骤的停留时长
- [ ] 支持导出为MP4或其他视频格式（未来版本）
- [ ] 演示过程流畅，动画无卡顿
- [ ] 支持4K分辨率输出（未来版本）

---

### 📖 故事5：团队协作创建演示

**作为** 技术团队负责人  
**我希望** 团队成员可以协作创建和完善演示内容  
**以便** 确保演示内容的准确性和专业性

**验收标准**：
- [ ] 支持多用户编辑同一个演示场景
- [ ] 有版本历史记录和回滚功能
- [ ] 支持评论和反馈
- [ ] 可以设置不同成员的权限（查看/编辑/管理）
- [ ] 支持演示场景的分享链接

---

# 附录B：功能需求详述

## B.1 Demo Player 详细功能

### B.1.1 核心播放功能

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| DP-001 | 步骤导航 | P0 | 支持在演示步骤之间前进/后退 | - 点击下一步/上一步按钮切换步骤<br>- 支持键盘左右箭头快捷键<br>- 显示当前步骤进度 |
| DP-002 | 自动播放 | P0 | 按设定时间自动切换步骤 | - 可开启/关闭自动播放<br>- 支持设置全局播放速度<br>- 支持为每个步骤设置停留时长 |
| DP-003 | 全屏模式 | P0 | 演示页面支持全屏显示 | - 点击全屏按钮进入全屏<br>- 按ESC退出全屏<br>- 全屏下保持所有控制功能 |
| DP-004 | 步骤预览 | P1 | 显示所有步骤的缩略图导航 | - 侧边栏显示步骤列表<br>- 点击缩略图跳转到对应步骤<br>- 显示步骤标题和类型图标 |
| DP-005 | 进度指示 | P1 | 显示当前演示进度 | - 顶部或底部显示进度条<br>- 显示当前步骤/总步骤数<br>- 已完成步骤有不同视觉标记 |

### B.1.2 动画展示功能

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| DP-101 | 需求卡片动画 | P0 | 展示需求信息的淡入浮动动画 | - 卡片从下方淡入<br>- 轻微上下浮动效果<br>- 支持自定义卡片样式 |
| DP-102 | Spec文档动画 | P0 | Markdown文档的打字机效果展示 | - 逐行或逐字符显示<br>- 支持语法高亮<br>- 可调整打字速度 |
| DP-103 | 架构图动画 | P0 | 节点和连线的动态展示 | - 节点依次出现<br>- 连线自动绘制动画<br>- 支持节点交互高亮 |
| DP-104 | 任务清单动画 | P0 | 任务项的勾选动画 | - 任务项依次出现<br>- 勾选时有完成动画<br>- 支持子任务嵌套 |
| DP-105 | 代码展示动画 | P0 | 代码的逐行打印效果 | - 逐行高亮显示<br>- 支持语法高亮<br>- 关键代码片段可强调 |
| DP-106 | 对比展示 | P1 | 左右分栏的对比动画 | - 支持Before/After对比<br>- 中间滑块可拖动<br>- 同步动画展示 |

### B.1.3 交互控制功能

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| DP-201 | 播放控制 | P0 | 播放/暂停/重置控制 | - 底部控制栏提供按钮<br>- 支持空格键播放/暂停<br>- 重置回到初始状态 |
| DP-202 | 速度控制 | P1 | 调整动画播放速度 | - 提供0.5x/1x/1.5x/2x选项<br>- 实时生效<br>- 持久化用户选择 |
| DP-203 | 讲解词显示 | P1 | 显示当前步骤的讲解文本 | - 可展开/收起讲解面板<br>- 支持演讲者笔记视图<br>- 字体大小可调 |
| DP-204 | 快捷键支持 | P1 | 丰富的键盘快捷键 | - 方向键：导航<br>- 空格：播放/暂停<br>- F：全屏<br>- ESC：退出全屏 |

---

## B.2 Speaker Console 详细功能

### B.2.1 远程控制功能

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| SC-001 | 同步控制 | P0 | 与Demo Player实时同步 | - 操作立即反映到Player<br>- 显示连接状态<br>- 断线自动重连 |
| SC-002 | 步骤控制 | P0 | 前进/后退/跳转到指定步骤 | - 大按钮便于快速操作<br>- 显示步骤缩略图<br>- 支持直接跳转到任意步骤 |
| SC-003 | 自动播放控制 | P1 | 控制自动播放的启停 | - 一键开启/关闭<br>- 显示当前播放状态<br>- 支持暂停在特定步骤 |

### B.2.2 演讲辅助功能

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| SC-101 | 讲解词提示 | P0 | 显示当前步骤的讲解文本 | - 大字体便于阅读<br>- 显示下一页的提示<br>- 支持上下滚动 |
| SC-102 | 计时器 | P1 | 显示演讲已用时间和剩余时间 | - 正计时和倒计时模式<br>- 可设置目标时长<br>- 超时提醒 |
| SC-103 | 激光笔 | P2 | 在Player上显示指示点 | - 触摸/鼠标控制<br>- 高亮显示关键内容<br>- 多种指示样式 |
| SC-104 | 标注工具 | P2 | 在演示画面上做临时标注 | - 画笔/箭头/文字标注<br>- 一键清除<br>- 不同颜色选择 |

### B.2.3 场景管理功能

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| SC-201 | 场景切换 | P1 | 快速切换到其他演示场景 | - 场景列表展示<br>- 一键切换<br>- 切换前确认提示 |
| SC-202 | 场景预览 | P1 | 预览场景的所有步骤 | - 步骤缩略图网格<br>- 点击跳转到该步骤<br>- 显示步骤总览 |
| SC-203 | 收藏场景 | P2 | 标记常用的演示场景 | - 收藏/取消收藏<br>- 收藏场景优先显示<br>- 快速访问收藏列表 |

---

## B.3 Scenario CMS 详细功能

### B.3.1 场景管理

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| CMS-001 | 创建场景 | P0 | 创建新的演示场景 | - 填写标题、描述<br>- 选择模板<br>- 设置封面图 |
| CMS-002 | 编辑场景 | P0 | 修改场景的基本信息 | - 修改标题/描述<br>- 更换封面<br>- 设置标签分类 |
| CMS-003 | 删除场景 | P0 | 删除演示场景 | - 二次确认<br>- 软删除可恢复<br>- 批量删除支持 |
| CMS-004 | 复制场景 | P1 | 复制现有场景作为模板 | - 完整复制所有步骤<br>- 支持重命名<br>- 复制后自动进入编辑 |
| CMS-005 | 导入/导出 | P1 | 导入外部场景或导出当前场景 | - JSON格式导入导出<br>- 拖拽上传<br>- 导出包含完整资源 |
| CMS-006 | 场景搜索 | P1 | 搜索和筛选场景 | - 关键词搜索<br>- 按标签筛选<br>- 排序功能 |

### B.3.2 步骤编辑器

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| CMS-101 | 添加步骤 | P0 | 向场景中添加新步骤 | - 选择步骤类型<br>- 设置步骤标题<br>- 自动分配序号 |
| CMS-102 | 编辑步骤 | P0 | 修改步骤的内容和属性 | - 编辑标题/内容<br>- 修改动画参数<br>- 设置停留时长 |
| CMS-103 | 删除步骤 | P0 | 删除场景中的步骤 | - 二次确认<br>- 序号自动调整<br>- 支持撤销 |
| CMS-104 | 排序步骤 | P1 | 调整步骤的顺序 | - 拖拽排序<br>- 上移/下移按钮<br>- 实时预览新顺序 |
| CMS-105 | 步骤类型切换 | P1 | 更改步骤的动画类型 | - 下拉选择类型<br>- 保留可复用的内容<br>- 预览新类型效果 |
| CMS-106 | 批量编辑 | P2 | 批量修改多个步骤的属性 | - 多选步骤<br>- 批量修改时长<br>- 批量删除 |

### B.3.3 内容编辑

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| CMS-201 | Markdown编辑 | P0 | 富文本/Markdown编辑器 | - 实时预览<br>- 语法高亮<br>- 支持代码块 |
| CMS-202 | 可视化编辑 | P1 | 所见即所得的编辑模式 | - 拖拽组件<br>- 属性面板<br>- 实时预览 |
| CMS-203 | 代码片段管理 | P1 | 管理和插入代码示例 | - 代码编辑器集成<br>- 语法高亮<br>- 代码库管理 |
| CMS-204 | 多媒体插入 | P2 | 插入图片、视频等资源 | - 本地上传<br>- URL引用<br>- 资源库选择 |
| CMS-205 | 变量支持 | P2 | 使用变量动态替换内容 | - 定义变量<br>- 在内容中引用<br>- 批量替换 |

### B.3.4 预览和测试

| 功能ID | 功能名称 | 优先级 | 详细描述 | 验收标准 |
|--------|----------|--------|----------|----------|
| CMS-301 | 实时预览 | P0 | 编辑时实时预览效果 | - 分屏预览<br>- 实时更新<br>- 支持全屏预览 |
| CMS-302 | 单步预览 | P1 | 预览单个步骤的效果 | - 独立预览窗口<br>- 可重复播放<br>- 调整参数实时生效 |
| CMS-303 | 完整播放 | P1 | 从头开始播放整个场景 | - 新窗口播放<br>- 完整体验<br>- 支持暂停和调试 |
| CMS-304 | 响应式预览 | P2 | 预览不同屏幕尺寸的效果 | - 设备尺寸切换<br>- 横竖屏切换<br>- 分辨率选择 |

---

# 附录C：UI/UX 设计规范

## C.1 设计原则

### 核心设计理念

1. **内容优先**：动画和视觉效果服务于内容展示，不喧宾夺主
2. **沉浸体验**：全屏演示时提供影院级观看体验
3. **简洁直观**：界面元素简洁，操作逻辑清晰
4. **专业感**：体现技术分享的严谨和专业

### 设计关键词

- 科技感
- 专业性
- 流畅性
- 沉浸感
- 现代感

---

## C.2 色彩系统

### 主色调

| 颜色名称 | 色值 | 用途 |
|----------|------|------|
| Primary | `#2563EB` | 主按钮、链接、强调色 |
| Primary Dark | `#1D4ED8` | 悬停状态 |
| Primary Light | `#3B82F6` | 激活状态 |

### 背景色

| 颜色名称 | 色值 | 用途 |
|----------|------|------|
| Background | `#0F172A` | 深色主背景 |
| Surface | `#1E293B` | 卡片、面板背景 |
| Elevated | `#334155` | 悬浮层、边框 |

### 文字色

| 颜色名称 | 色值 | 用途 |
|----------|------|------|
| Text Primary | `#F8FAFC` | 主要文字 |
| Text Secondary | `#94A3B8` | 次要文字、描述 |
| Text Muted | `#64748B` | 禁用、提示文字 |

### 功能色

| 颜色名称 | 色值 | 用途 |
|----------|------|------|
| Success | `#10B981` | 成功状态 |
| Warning | `#F59E0B` | 警告状态 |
| Error | `#EF4444` | 错误状态 |
| Info | `#06B6D4` | 信息提示 |

### 渐变方案

```
Hero渐变: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)
背景渐变: linear-gradient(180deg, #0F172A 0%, #1E293B 100%)
卡片光晕: radial-gradient(circle, rgba(37,99,235,0.15) 0%, transparent 70%)
```

---

## C.3 排版系统

### 字体栈

```css
/* 中文优先 */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;

/* 代码字体 */
font-family: 'Fira Code', 'JetBrains Mono', 'Source Code Pro', monospace;
```

### 字号规范

| 级别 | 桌面端 | 移动端 | 行高 | 字重 | 用途 |
|------|--------|--------|------|------|------|
| Display | 48px | 32px | 1.2 | 700 | 场景标题 |
| H1 | 36px | 24px | 1.3 | 600 | 步骤标题 |
| H2 | 24px | 20px | 1.4 | 600 | 小节标题 |
| H3 | 20px | 18px | 1.4 | 500 | 卡片标题 |
| Body | 16px | 14px | 1.6 | 400 | 正文内容 |
| Small | 14px | 12px | 1.5 | 400 | 辅助文字 |
| Caption | 12px | 11px | 1.4 | 400 | 标签、提示 |

### 代码展示

| 元素 | 字号 | 行高 | 用途 |
|------|------|------|------|
| 代码块 | 14px | 1.8 | 代码展示区域 |
| 行内代码 | 0.9em | inherit | 行内代码片段 |
| 代码注释 | 12px | 1.6 | 代码注释 |

---

## C.4 间距系统

### 基础单位

基础单位：4px

| Token | 值 | 用途 |
|-------|------|------|
| space-1 | 4px | 图标间距 |
| space-2 | 8px | 紧凑间距 |
| space-3 | 12px | 小间距 |
| space-4 | 16px | 默认间距 |
| space-6 | 24px | 组件间距 |
| space-8 | 32px | 区块间距 |
| space-12 | 48px | 大区块间距 |
| space-16 | 64px | 页面间距 |

### 布局规范

```
Player页面：
- 内容区边距: 64px (桌面) / 24px (移动)
- 步骤面板宽度: 280px
- 讲解面板宽度: 320px
- 动画区域最小高度: 60vh

CMS页面：
- 侧边栏宽度: 240px
- 编辑器边距: 32px
- 预览区边距: 24px
```

---

## C.5 圆角与阴影

### 圆角规范

| Token | 值 | 用途 |
|-------|------|------|
| radius-sm | 4px | 按钮、输入框 |
| radius-md | 8px | 卡片、小面板 |
| radius-lg | 12px | 大卡片、模态框 |
| radius-xl | 16px | 容器、页面 |
| radius-full | 9999px | 标签、头像 |

### 阴影规范

```css
/* 卡片阴影 */
shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)

/* 悬浮阴影 */
shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)

/* 模态阴影 */
shadow-modal: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3)

/* 光晕效果 */
shadow-glow: 0 0 20px rgba(37, 99, 235, 0.3)
```

---

## C.6 动画规范

### 缓动函数

```css
/* 标准缓动 */
ease-default: cubic-bezier(0.4, 0, 0.2, 1)

/* 进入缓动 */
ease-enter: cubic-bezier(0, 0, 0.2, 1)

/* 退出缓动 */
ease-exit: cubic-bezier(0.4, 0, 1, 1)

/* 弹性缓动 */
ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55)

/* 弹簧缓动 */
ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275)
```

### 时长规范

| 类型 | 时长 | 用途 |
|------|------|------|
| Fast | 150ms | 悬停、微小交互 |
| Normal | 300ms | 默认过渡 |
| Slow | 500ms | 较大状态变化 |
| Demo | 800-1500ms | 演示动画 |

### 动画类型

| 动画 | 时长 | 缓动 | 说明 |
|------|------|------|------|
| Fade In | 300ms | ease-enter | 淡入 |
| Fade Out | 200ms | ease-exit | 淡出 |
| Slide Up | 400ms | ease-spring | 从下方滑入 |
| Scale | 300ms | ease-bounce | 缩放动画 |
| Typewriter | 50ms/char | linear | 打字机效果 |
| Draw Line | 1000ms | ease-default | 线条绘制 |

---

## C.7 组件规范

### 按钮

**主要按钮 (Primary)**
```
背景: #2563EB
文字: #FFFFFF
圆角: 8px
内边距: 12px 24px
字体: 16px, weight 500
悬停: 背景 #1D4ED8, 上移 -2px
禁用: 背景 #334155, 透明度 0.5
```

**次要按钮 (Secondary)**
```
背景: transparent
边框: 1px solid #334155
文字: #F8FAFC
圆角: 8px
内边距: 12px 24px
悬停: 背景 rgba(255,255,255,0.05)
```

**图标按钮**
```
尺寸: 40px x 40px
圆角: 8px
背景: transparent
悬停: 背景 rgba(255,255,255,0.1)
图标: 20px
```

### 卡片

**场景卡片**
```
背景: #1E293B
圆角: 12px
内边距: 0 (图片区域) + 24px (内容区)
阴影: shadow-card
悬停: shadow-hover, 上移 -4px
```

**步骤卡片**
```
背景: #1E293B
圆角: 8px
内边距: 16px
边框: 1px solid transparent
激活: 边框 #2563EB, shadow-glow
```

### 输入框

**文本输入**
```
背景: #0F172A
边框: 1px solid #334155
圆角: 8px
内边距: 12px 16px
字体: 16px
聚焦: 边框 #2563EB, shadow-glow
占位符: #64748B
```

**文本域**
```
最小高度: 120px
其他同文本输入
```

---

# 附录D：数据模型与API设计

## D.1 数据模型

### D.1.1 场景 (Scenario)

```typescript
interface Scenario {
  id: string;                    // 唯一标识符
  slug: string;                  // URL友好标识
  title: string;                 // 场景标题
  description: string;           // 场景描述
  coverImage?: string;           // 封面图片URL
  tags: string[];                // 标签列表
  category: string;              // 分类
  author: User;                  // 作者信息
  status: 'draft' | 'published' | 'archived';
  visibility: 'public' | 'private' | 'unlisted';
  steps: Step[];                 // 步骤列表
  settings: ScenarioSettings;    // 场景设置
  metadata: ScenarioMetadata;    // 元数据
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

interface ScenarioSettings {
  defaultStepDuration: number;   // 默认步骤时长(秒)
  autoPlay: boolean;             // 是否默认自动播放
  loop: boolean;                 // 是否循环播放
  transitionEffect: TransitionType;
  theme: 'dark' | 'light' | 'auto';
  codeTheme: string;             // 代码主题
}

interface ScenarioMetadata {
  viewCount: number;
  playCount: number;
  likeCount: number;
  estimatedDuration: number;     // 预估总时长
  difficulty: 'beginner' | 'intermediate' | 'advanced';
}
```

### D.1.2 步骤 (Step)

```typescript
interface Step {
  id: string;
  order: number;                 // 步骤顺序
  title: string;                 // 步骤标题
  type: StepType;                // 步骤类型
  content: StepContent;          // 步骤内容
  narration: string;             // 讲解词
  duration: number;              // 停留时长(秒)
  transition: TransitionConfig;  // 过渡动画配置
  settings: StepSettings;        // 步骤设置
}

type StepType = 
  | 'requirement'    // 需求展示
  | 'spec'          // 规格文档
  | 'design'        // 架构设计
  | 'tasks'         // 任务清单
  | 'code'          // 代码展示
  | 'architecture'  // 架构图
  | 'comparison'    // 对比展示
  | 'custom';       // 自定义

interface StepContent {
  // 根据type有不同的结构
}

// 需求类型内容
interface RequirementContent extends StepContent {
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  tags?: string[];
}

// Spec类型内容
interface SpecContent extends StepContent {
  markdown: string;
  highlightLines?: number[];
  sections?: string[];  // 要展示的部分
}

// 设计类型内容
interface DesignContent extends StepContent {
  nodes: DesignNode[];
  connections: Connection[];
  layout: 'tree' | 'flow' | 'radial';
}

interface DesignNode {
  id: string;
  label: string;
  type: 'service' | 'database' | 'api' | 'component' | 'external';
  description?: string;
  position?: { x: number; y: number };
}

interface Connection {
  from: string;
  to: string;
  label?: string;
  type: 'solid' | 'dashed' | 'dotted';
}

// 任务类型内容
interface TasksContent extends StepContent {
  tasks: TaskItem[];
  showProgress: boolean;
}

interface TaskItem {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in-progress' | 'completed';
  subtasks?: TaskItem[];
}

// 代码类型内容
interface CodeContent extends StepContent {
  language: string;
  code: string;
  fileName?: string;
  highlightLines?: number[];
  lineNumbers: boolean;
  revealMode: 'all' | 'typewriter' | 'highlight';
}

interface TransitionConfig {
  type: TransitionType;
  duration: number;
  easing: string;
}

type TransitionType = 
  | 'fade'
  | 'slide-left'
  | 'slide-right'
  | 'slide-up'
  | 'slide-down'
  | 'scale'
  | 'none';

interface StepSettings {
  autoAdvance: boolean;
  skippable: boolean;
  allowInteraction: boolean;
}
```

### D.1.3 用户 (User)

```typescript
interface User {
  id: string;
  username: string;
  email: string;
  displayName: string;
  avatar?: string;
  bio?: string;
  role: 'viewer' | 'creator' | 'admin';
  preferences: UserPreferences;
  createdAt: Date;
}

interface UserPreferences {
  theme: 'dark' | 'light' | 'auto';
  language: string;
  defaultCodeTheme: string;
  autoPlay: boolean;
  defaultSpeed: number;
}
```

### D.1.4 会话 (Session)

```typescript
interface PresentationSession {
  id: string;
  scenarioId: string;
  hostId: string;
  status: 'waiting' | 'playing' | 'paused' | 'ended';
  currentStep: number;
  viewers: Viewer[];
  createdAt: Date;
  startedAt?: Date;
  endedAt?: Date;
}

interface Viewer {
  id: string;
  name?: string;
  joinedAt: Date;
  lastPing: Date;
}
```

---

## D.2 API 设计

### D.2.1 场景管理 API

```yaml
# 场景列表
GET /api/scenarios
Query:
  - page: number (default: 1)
  - limit: number (default: 20)
  - category: string
  - tag: string
  - search: string
  - sort: 'newest' | 'popular' | 'name'
Response:
  - data: Scenario[]
  - total: number
  - page: number
  - pages: number

# 获取单个场景
GET /api/scenarios/:id
Response:
  - scenario: Scenario

# 创建场景
POST /api/scenarios
Body:
  - title: string (required)
  - description: string
  - category: string
  - tags: string[]
  - template?: string
Response:
  - scenario: Scenario

# 更新场景
PUT /api/scenarios/:id
Body:
  - title?: string
  - description?: string
  - category?: string
  - tags?: string[]
  - coverImage?: string
  - settings?: ScenarioSettings
Response:
  - scenario: Scenario

# 删除场景
DELETE /api/scenarios/:id
Response:
  - success: boolean

# 复制场景
POST /api/scenarios/:id/duplicate
Body:
  - newTitle?: string
Response:
  - scenario: Scenario

# 导出场景
GET /api/scenarios/:id/export
Response:
  - downloadUrl: string

# 导入场景
POST /api/scenarios/import
Body:
  - file: File
Response:
  - scenario: Scenario
```

### D.2.2 步骤管理 API

```yaml
# 添加步骤
POST /api/scenarios/:id/steps
Body:
  - title: string
  - type: StepType
  - order?: number
Response:
  - step: Step

# 更新步骤
PUT /api/scenarios/:id/steps/:stepId
Body:
  - title?: string
  - type?: StepType
  - content?: StepContent
  - narration?: string
  - duration?: number
  - transition?: TransitionConfig
  - settings?: StepSettings
Response:
  - step: Step

# 删除步骤
DELETE /api/scenarios/:id/steps/:stepId
Response:
  - success: boolean

# 重排步骤
PUT /api/scenarios/:id/steps/reorder
Body:
  - stepIds: string[]  // 新的顺序
Response:
  - steps: Step[]

# 批量更新步骤
PUT /api/scenarios/:id/steps/batch
Body:
  - steps: Partial<Step>[]
Response:
  - steps: Step[]
```

### D.2.3 播放控制 API

```yaml
# 创建播放会话
POST /api/sessions
Body:
  - scenarioId: string
Response:
  - session: PresentationSession
  - playerUrl: string
  - consoleUrl: string

# 获取会话状态
GET /api/sessions/:id
Response:
  - session: PresentationSession

# 更新播放状态
PUT /api/sessions/:id/state
Body:
  - status: 'playing' | 'paused'
  - currentStep: number
Response:
  - session: PresentationSession

# 前进到下一步
POST /api/sessions/:id/next
Response:
  - currentStep: number

# 后退到上一步
POST /api/sessions/:id/prev
Response:
  - currentStep: number

# 跳转到指定步骤
POST /api/sessions/:id/goto
Body:
  - stepIndex: number
Response:
  - currentStep: number

# 结束会话
DELETE /api/sessions/:id
Response:
  - success: boolean

# 加入观看
POST /api/sessions/:id/join
Body:
  - name?: string
Response:
  - viewerToken: string
```

### D.2.4 资源管理 API

```yaml
# 上传资源
POST /api/assets/upload
Body:
  - file: File
  - type: 'image' | 'video' | 'audio'
Response:
  - asset: Asset

# 获取资源列表
GET /api/assets
Query:
  - type?: string
  - page?: number
  - limit?: number
Response:
  - assets: Asset[]
  - total: number

# 删除资源
DELETE /api/assets/:id
Response:
  - success: boolean
```

### D.2.5 用户 API

```yaml
# 获取当前用户
GET /api/user/me
Response:
  - user: User

# 更新用户信息
PUT /api/user/me
Body:
  - displayName?: string
  - bio?: string
  - avatar?: string
  - preferences?: UserPreferences
Response:
  - user: User

# 获取用户的场景
GET /api/user/scenarios
Query:
  - page?: number
  - limit?: number
Response:
  - scenarios: Scenario[]
  - total: number

# 获取收藏的场景
GET /api/user/favorites
Response:
  - scenarios: Scenario[]

# 添加收藏
POST /api/user/favorites
Body:
  - scenarioId: string
Response:
  - success: boolean

# 取消收藏
DELETE /api/user/favorites/:scenarioId
Response:
  - success: boolean
```

---

# 附录E：非功能需求

## E.1 性能要求

### 加载性能

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 首屏加载时间 | < 2s | 从输入URL到首屏渲染完成 |
| 可交互时间 (TTI) | < 3s | 页面可响应用户操作 |
| 场景列表加载 | < 1s | 场景列表首屏数据加载 |
| 场景详情加载 | < 1.5s | 单个场景完整数据加载 |

### 运行时性能

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 动画帧率 | 60fps | 所有动画保持流畅 |
| 内存占用 | < 200MB | 单页面运行时内存 |
| 步骤切换延迟 | < 100ms | 步骤切换的响应时间 |
| 编辑器响应 | < 50ms | 输入到预览更新的延迟 |

### 并发性能

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 同时播放会话 | 50+ | 单实例支持的最大并发会话 |
| 观看人数上限 | 100/会话 | 单个会话的最大观看人数 |
| 数据同步延迟 | < 500ms | 控制台操作到Player的同步 |

---

## E.2 兼容性要求

### 浏览器支持

| 浏览器 | 最低版本 | 支持级别 |
|--------|----------|----------|
| Chrome | 90+ | 完全支持 |
| Firefox | 88+ | 完全支持 |
| Safari | 14+ | 完全支持 |
| Edge | 90+ | 完全支持 |
| 微信内置 | 最新 | 基础支持 |

### 设备支持

| 设备类型 | 分辨率 | 支持级别 |
|----------|--------|----------|
| 桌面 | 1920x1080+ | 完全支持 |
| 笔记本 | 1366x768+ | 完全支持 |
| 平板 | 768x1024+ | 完全支持 |
| 手机 | 375x667+ | 基础支持 |

### 网络要求

| 场景 | 带宽要求 | 延迟要求 |
|------|----------|----------|
| 观看演示 | 1Mbps | < 200ms |
| 控制台控制 | 500Kbps | < 100ms |
| 编辑场景 | 2Mbps | < 150ms |

---

## E.3 安全要求

### 数据安全

- **传输加密**：所有API通信使用HTTPS
- **存储加密**：敏感数据（如用户令牌）加密存储
- **数据验证**：所有用户输入进行严格验证和转义
- **XSS防护**：实施CSP策略，防止跨站脚本攻击
- **CSRF防护**：实施CSRF Token机制

### 访问控制

- **身份认证**：JWT Token认证机制
- **权限控制**：基于角色的访问控制（RBAC）
- **资源隔离**：用户只能访问自己的资源
- **会话管理**：会话超时和自动登出

### 隐私保护

- **数据最小化**：只收集必要的数据
- **用户同意**：明确的数据使用同意机制
- **数据导出**：支持用户导出自己的数据
- **数据删除**：支持完全删除用户数据

---

## E.4 可用性要求

### 可用性目标

- **系统可用性**：99.9%（年度停机时间 < 8.76小时）
- **计划维护**：提前24小时通知，维护窗口 < 2小时
- **故障恢复**：RTO < 1小时，RPO < 5分钟

### 降级策略

- **离线模式**：编辑器支持离线编辑，联网后同步
- **缓存策略**：静态资源长期缓存，数据智能缓存
- **降级展示**：网络异常时显示友好提示

---

# 附录F：测试策略

## F.1 测试层级

### 单元测试

- **覆盖率目标**：> 80%
- **测试范围**：工具函数、组件逻辑、状态管理
- **工具**：Jest + React Testing Library

### 集成测试

- **测试范围**：组件交互、API集成、路由跳转
- **重点场景**：
  - 场景创建流程
  - 步骤编辑流程
  - 播放控制流程

### E2E测试

- **测试范围**：完整用户流程
- **关键路径**：
  - 创建场景 → 编辑步骤 → 预览 → 播放
  - 注册 → 创建 → 分享 → 观看
- **工具**：Playwright

## F.2 测试用例示例

### 场景播放测试

```gherkin
Feature: 场景播放
  
  Scenario: 用户播放演示场景
    Given 用户已打开演示页面
    When 用户点击播放按钮
    Then 演示开始从第一步播放
    And 显示当前步骤的动画
    And 讲解面板显示对应讲解词

  Scenario: 用户控制播放进度
    Given 演示正在播放中
    When 用户点击下一步按钮
    Then 演示前进到下一步骤
    And 播放新步骤的动画

  Scenario: 用户暂停演示
    Given 演示正在播放中
    When 用户点击暂停按钮
    Then 当前动画暂停
    And 显示继续按钮
```

### 场景编辑测试

```gherkin
Feature: 场景编辑
  
  Scenario: 用户创建新场景
    Given 用户已登录
    When 用户点击"创建场景"按钮
    And 填写场景标题和描述
    And 点击保存
    Then 新场景创建成功
    And 自动进入场景编辑页面

  Scenario: 用户添加步骤
    Given 用户在场景编辑页面
    When 用户点击"添加步骤"
    And 选择步骤类型为"代码"
    And 填写代码内容
    And 点击保存
    Then 新步骤添加到场景中
    And 实时预览显示代码效果
```

## F.3 验收标准

### MVP验收清单

- [ ] 可以创建、编辑、删除演示场景
- [ ] 支持所有5种步骤类型的创建和展示
- [ ] 播放器支持播放控制和自动播放
- [ ] 步骤切换动画流畅
- [ ] 控制台可以远程控制播放
- [ ] 响应式布局适配不同设备
- [ ] 代码编辑器支持语法高亮
- [ ] 用户认证和授权功能正常

### 发布标准

- [ ] 所有P0功能完成并通过测试
- [ ] 性能指标达标
- [ ] 主流浏览器兼容性测试通过
- [ ] 无严重Bug（P0/P1级别）
- [ ] 文档完整（用户文档、API文档）
- [ ] 安全审查通过

---

# 附录G：项目规划与里程碑

## G.1 开发阶段

### Phase 1: MVP核心功能（4-6周）

**目标**：完成基础播放和编辑功能

| 周次 | 任务 | 产出 |
|------|------|------|
| W1 | 项目初始化、基础架构 | 项目框架、CI/CD |
| W2 | 场景管理、步骤编辑器 | CMS基础功能 |
| W3 | Demo Player核心 | 5种动画类型实现 |
| W4 | 播放控制、自动播放 | Player完整功能 |
| W5 | 用户系统、认证授权 | 登录/注册功能 |
| W6 | 集成测试、Bug修复 | MVP可用版本 |

**交付物**：
- 可创建和播放演示场景
- 5种基础动画类型
- 用户认证系统

---

### Phase 2: 演讲功能（3-4周）

**目标**：完成演讲者控制台和远程控制

| 周次 | 任务 | 产出 |
|------|------|------|
| W1 | WebSocket服务 | 实时通信基础 |
| W2 | Speaker Console UI | 控制台界面 |
| W3 | 远程控制集成 | 控制同步功能 |
| W4 | 演讲辅助功能 | 计时器、讲解词 |

**交付物**：
- Speaker Console完整功能
- 手机/平板远程控制
- 演讲辅助工具

---

### Phase 3: 内容生态（4-5周）

**目标**：丰富内容管理和分享功能

| 周次 | 任务 | 产出 |
|------|------|------|
| W1 | 场景模板系统 | 内置模板库 |
| W2 | 导入/导出功能 | JSON/YAML支持 |
| W3 | 社区功能 | 分享、收藏、评论 |
| W4 | 搜索和推荐 | 内容发现功能 |
| W5 | 分析和统计 | 使用数据报表 |

**交付物**：
- 模板系统
- 社区分享功能
- 数据分析面板

---

### Phase 4: 高级功能（持续迭代）

- 视频录制和导出
- AI辅助内容生成
- 多语言支持
- 插件系统
- 企业级功能

---

## G.2 技术债务规划

| 优先级 | 债务项 | 计划解决时间 |
|--------|--------|--------------|
| P0 | 单元测试覆盖 | Phase 1 |
| P0 | E2E测试框架 | Phase 1 |
| P1 | 性能优化 | Phase 2 |
| P1 | 错误监控系统 | Phase 2 |
| P2 | 国际化框架 | Phase 3 |
| P2 | 文档自动化 | Phase 3 |

---

## G.3 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 动画性能问题 | 中 | 高 | 早期原型验证，使用Framer Motion最佳实践 |
| WebSocket稳定性 | 中 | 高 | 实现降级方案，支持轮询 |
| 跨浏览器兼容 | 低 | 中 | 持续集成中运行兼容性测试 |
| 需求变更 | 高 | 中 | 敏捷开发，短迭代周期 |
| 第三方依赖问题 | 低 | 中 | 选择成熟库，准备替代方案 |

---

# 十二、风险与缓解策略

## 12.1 技术风险

### 风险1：动画性能不达标

**风险描述**: 
复杂的动画效果在某些设备上可能出现卡顿，影响用户体验。

**可能性**: 中  
**影响程度**: 高

**缓解策略**:
1. **早期原型验证** - Phase 1第一周完成动画性能原型测试
2. **性能预算** - 设定明确的性能指标（60fps，内存<200MB）
3. **渐进增强** - 低端设备提供简化动画选项
4. **性能监控** - 集成性能监控工具，实时追踪帧率

**应急预案**:
- 如果Framer Motion性能不达标，考虑使用GSAP或原生Canvas
- 提供"性能模式"开关，用户可禁用复杂动画

---

### 风险2：WebSocket实时同步不稳定

**风险描述**: 
控制台与Player之间的实时通信可能出现延迟或断开。

**可能性**: 中  
**影响程度**: 高

**缓解策略**:
1. **降级方案** - 实现HTTP轮询作为WebSocket的降级方案
2. **重连机制** - 自动重连，最多5次，间隔指数增长
3. **状态同步** - 定期状态校验，确保一致性
4. **本地缓存** - 关键操作本地缓存，网络恢复后同步

**应急预案**:
- 如果WebSocket不稳定，默认使用HTTP轮询模式
- 提供"离线模式"，支持单机演示

---

### 风险3：浏览器兼容性问题

**风险描述**: 
不同浏览器对动画API和WebSocket支持程度不同。

**可能性**: 低  
**影响程度**: 中

**缓解策略**:
1. **特性检测** - 使用Modernizr检测浏览器特性
2. **Polyfill** - 为旧浏览器提供Polyfill
3. **优雅降级** - 不支持的功能提供替代方案
4. **CI/CD测试** - 持续集成中运行跨浏览器测试

**应急预案**:
- 定义明确的浏览器支持列表
- 对不支持的浏览器显示友好提示

---

## 12.2 产品风险

### 风险4：用户接受度不足

**风险描述**: 
目标用户可能不愿意改变现有的PPT演示习惯。

**可能性**: 中  
**影响程度**: 高

**缓解策略**:
1. **降低门槛** - 提供PPT导入功能，平滑过渡
2. **模板丰富** - 提供大量开箱即用的场景模板
3. **案例展示** - 展示成功的使用案例和效果对比
4. **早期反馈** - MVP阶段邀请种子用户深度参与

**应急预案**:
- 如果接受度低，考虑转型为PPT插件而非独立平台
- 增加更多与PPT的集成功能

---

### 风险5：内容生态建设缓慢

**风险描述**: 
用户创建的场景数量不足，平台内容匮乏。

**可能性**: 中  
**影响程度**: 中

**缓解策略**:
1. **种子内容** - 团队自己创建20+高质量场景
2. **激励机制** - 积分、徽章、排行榜等激励用户贡献
3. **社区运营** - 建立Discord/微信群，促进交流
4. **内容合作** - 与技术KOL合作，产出优质内容

**应急预案**:
- 如果UGC不足，转为PGC模式，团队主导内容生产
- 降低内容创建门槛，支持一键克隆和修改

---

## 12.3 业务风险

### 风险6：竞争产品出现

**风险描述**: 
大型平台（如Canva、Figma）可能推出类似功能。

**可能性**: 中  
**影响程度**: 中

**缓解策略**:
1. **差异化定位** - 专注技术分享场景，做深做透
2. **社区壁垒** - 建设活跃的社区和生态系统
3. **快速迭代** - 保持快速的产品迭代节奏
4. **技术深度** - 在代码展示、技术动画方面建立技术壁垒

**应急预案**:
- 如果被大厂跟进，考虑被收购或转型为插件
- 专注企业服务市场，避开消费级竞争

---

### 风险7：商业化困难

**风险描述**: 
用户习惯免费工具，付费转化率低。

**可能性**: 中  
**影响程度**: 中

**缓解策略**:
1. **价值证明** - 通过数据展示使用前后效果对比
2. **分层定价** - 免费版+专业版+企业版
3. **B2B策略** - 重点服务企业培训市场
4. **增值服务** - 提供场景定制、培训等增值服务

**应急预案**:
- 如果C端付费率低，转向纯B2B模式
- 提供API和SDK，通过技术授权盈利

---

## 12.4 风险矩阵

| 风险 | 可能性 | 影响 | 风险等级 | 状态 |
|------|--------|------|----------|------|
| 动画性能问题 | 中 | 高 | 🔴 高 | 监控中 |
| WebSocket不稳定 | 中 | 高 | 🔴 高 | 监控中 |
| 用户接受度不足 | 中 | 高 | 🔴 高 | 预防中 |
| 浏览器兼容性 | 低 | 中 | 🟡 中 | 可控 |
| 内容生态缓慢 | 中 | 中 | 🟡 中 | 预防中 |
| 竞争产品出现 | 中 | 中 | 🟡 中 | 观察中 |
| 商业化困难 | 中 | 中 | 🟡 中 | 规划中 |

---

# 十三、项目规划与里程碑

*（原有内容保留，见附录G）*

---

# 十四、依赖与假设

## 14.1 技术依赖

### 外部依赖

| 依赖项 | 用途 | 风险等级 | 备选方案 |
|--------|------|----------|----------|
| **Framer Motion** | 动画引擎 | 低 | GSAP, React Spring |
| **Next.js** | 前端框架 | 低 | Remix, Gatsby |
| **Tailwind CSS** | 样式框架 | 低 | Chakra UI, MUI |
| **Socket.io** | WebSocket通信 | 中 | 原生WebSocket, HTTP轮询 |
| **Prisma** | ORM | 低 | TypeORM, Sequelize |
| **PostgreSQL** | 数据库 | 低 | MySQL, MongoDB |
| **Redis** | 缓存/会话 | 低 | Memcached |
| **Auth0/Firebase Auth** | 认证服务 | 中 | 自建认证系统 |
| **Vercel/Netlify** | 托管平台 | 低 | AWS, GCP |

### 第三方服务

| 服务 | 用途 | 成本估算 | 必要性 |
|------|------|----------|--------|
| **Vercel Pro** | 前端托管 | $20/月 | 必须 |
| **Railway/Render** | 后端托管 | $50/月 | 必须 |
| **Supabase** | 数据库托管 | $25/月 | 必须 |
| **Upstash Redis** | Redis托管 | $10/月 | 必须 |
| **Sentry** | 错误监控 | $26/月 | 建议 |
| **Plausible** | 分析统计 | $9/月 | 建议 |

---

## 14.2 业务依赖

### 关键假设

| 假设 | 验证方式 | 如果假设不成立 |
|------|----------|----------------|
| 技术演讲者有演示工具升级需求 | 用户调研、MVP反馈 | 转向B2B培训市场 |
| 用户愿意为动画演示付费 | 定价测试、转化率分析 | 改为免费+企业服务 |
| 社区愿意贡献场景模板 | UGC激励测试 | 转为PGC模式 |
| 技术分享市场持续增长 | 行业报告、趋势分析 | 缩小目标市场 |

### 外部因素

| 因素 | 影响 | 监控指标 |
|------|------|----------|
| **浏览器技术演进** | WebGL、WebAssembly支持改善 | 新API采用率 |
| **远程办公趋势** | 在线培训需求增加 | 企业客户增长 |
| **AI编程工具普及** | Spec-Driven Development需求增加 | 相关搜索量 |
| **技术大会恢复** | 线下演讲需求增加 | 大会数量、参会人数 |

---

## 14.3 团队依赖

### 角色需求

| 角色 | 需求时间 | 职责 | 当前状态 |
|------|----------|------|----------|
| **前端工程师** | Phase 1 | React/Next.js开发 | ✅ 已到位 |
| **后端工程师** | Phase 1 | API开发、数据库设计 | ✅ 已到位 |
| **UI/UX设计师** | Phase 1 | 界面设计、动画设计 | ⚠️ 兼职支持 |
| **产品经理** | Phase 1-2 | 需求管理、用户调研 | ✅ 已到位 |
| **动画设计师** | Phase 2 | 动画效果设计 | ❌ 待招聘 |
| **DevOps工程师** | Phase 2 | CI/CD、运维 | ⚠️ 外包支持 |
| **社区运营** | Phase 3 | 用户运营、内容运营 | ❌ 待招聘 |

---

# 十五、附件与参考资料

## 15.1 参考文档

### 技术参考

- [Framer Motion 文档](https://www.framer.com/motion/)
- [Next.js 文档](https://nextjs.org/docs)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Socket.io 文档](https://socket.io/docs/v4/)
- [React Best Practices](https://react.dev/learn)

### 设计参考

- [Material Design 动画指南](https://m3.material.io/styles/motion/overview)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [WCAG 2.1 无障碍指南](https://www.w3.org/WAI/WCAG21/quickref/)

### 产品参考

- [Canva](https://www.canva.com/) - 设计工具标杆
- [Figma](https://www.figma.com/) - 协作设计工具
- [Loom](https://www.loom.com/) - 视频录制分享
- [Excalidraw](https://excalidraw.com/) - 手绘风格图表

## 15.2 模板与工具

### 内置演示模板（MVP）

| 模板名称 | 描述 | 步骤数 | 适用场景 |
|----------|------|--------|----------|
| **Spec-Driven Intro** | Spec-Driven Development概念介绍 | 5 | 技术分享 |
| **API Design Flow** | RESTful API设计流程 | 6 | 开发培训 |
| **Code Review Best Practices** | 代码审查最佳实践 | 4 | 团队培训 |
| **Microservice Migration** | 单体应用到微服务迁移 | 7 | 架构分享 |
| **Testing Strategy** | 测试策略制定流程 | 5 | 质量培训 |

### 设计资源

- **图标库**: FontAwesome 6.4.0, Heroicons
- **字体**: Inter (英文), Noto Sans SC (中文)
- **代码字体**: Fira Code, JetBrains Mono
- **配色方案**: 深色主题设计系统

## 15.3 术语表

| 术语 | 英文 | 定义 |
|------|------|------|
| **演示场景** | Scenario | 一个完整的演示内容，包含多个步骤 |
| **步骤** | Step | 演示中的一个环节，有特定类型和动画 |
| **Demo Player** | Player | 用于播放演示的组件 |
| **Speaker Console** | Console | 演讲者使用的控制面板 |
| **Spec-Driven** | Spec-Driven | 规格驱动开发方法 |
| **EARS** | EARS | Easy Approach to Requirements Syntax，需求语法标准 |
| **P0/P1/P2** | Priority | 需求优先级，P0为最高 |
| **MVP** | MVP | Minimum Viable Product，最小可行产品 |

## 15.4 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v0.1 | 2024-01-15 | 初始版本，课程方案 | 产品团队 |
| v0.5 | 2024-01-30 | 升级为演示平台概念 | 产品团队 |
| v1.0 | 2024-02-13 | **重构为完整PRD**：添加执行摘要、EARS需求、范围界定、风险分析、依赖假设等章节 | AI Agent |

---

**文档结束**

---

## 文档使用指南

### 如何使用本文档

1. **设计阶段**: 参考 UI/UX 设计规范章节
2. **开发阶段**: 参考 EARS格式的功能需求章节
3. **测试阶段**: 参考 测试策略章节
4. **项目管理**: 参考 项目规划与里程碑章节
5. **风险评估**: 参考 风险与缓解策略章节

### 文档维护

- **更新频率**: 每两周评审一次，或在重大变更时更新
- **维护责任人**: 产品经理
- **审批流程**: 技术负责人审核技术章节，设计负责人审核UI章节

### 反馈渠道

如有疑问或建议，请通过以下方式反馈：
- 在GitHub Issues中创建文档改进建议
- 在团队Slack #product频道讨论
- 直接联系产品经理

---

*本文档由 PRD Generator Skill 和 Requirements Analyst Skill 辅助生成*  
*遵循 PRD Best Practices 和 EARS Requirements Syntax 标准*  
*持续更新，确保与开发进度保持同步*
