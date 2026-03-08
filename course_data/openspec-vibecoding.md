# OpenSpec VibeCoding 课程数据

> 导出时间：2026-03-08 23:46:47

---

## 章节：intro-vibe-coding

```yaml
order: 1
title: 第一章：最初的我 - 谨慎使用 AI 😰
chapter_type: story
is_locked: false
```

## 内容

## 故事开始...

还记得第一次接触 AI 编程时的我，心里充满了忐忑和不安。

### 我的心态

- 😰 **生怕 AI 理解错了**：每个需求都要写超级详细
- 📝 **复制粘贴所有代码**：要让 AI 改代码？先把整段代码贴给它
- 🤔 **反复确认**：AI 生成的代码真的要逐行检查

### 为什么需要详细沟通？

在初级阶段，AI 没有上下文理解能力，需要用户提供完整的信息：

**❌ 糟糕的指令：**
```
"帮我改一下登录页面"
```

**✅ 好的指令：**
```
我需要修改前端登录页面，具体如下：
1. 前端组件：frontend/src/components/Auth/LoginPage.tsx
2. 修改内容：在表单底部添加"记住我"复选框
3. 样式要求：使用 Tailwind CSS，复选框右侧对齐，文字为灰色
4. 后端接口：POST /api/v1/auth/login
5. 入参示例：{"email": "user@example.com", "password": "123456", "remember": true}
6. 出参示例：{"token": "eyJhbGc...", "expiresIn": 86400}
7. 需要同时修改类型定义：frontend/src/types/auth.ts
```

### 前端修改沟通模板

修改前端组件时，需要说明的信息：

| 信息类别 | 说明内容 | 示例 |
|----------|----------|------|
| **目标组件** | 要修改的文件路径 | `frontend/src/components/Header/Header.tsx` |
| **容器/区域** | 具体修改的位置 | "Header 组件右侧，用户头像按钮旁边" |
| **样式变更** | CSS/Tailwind 类名 | "添加 `ml-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded`" |
| **功能逻辑** | 交互行为 | "点击后跳转到 /settings 页面，使用 useNavigate hook" |
| **调用接口** | 后端 API | "调用 GET /api/v1/user/profile 获取用户信息" |
| **入参示例** | 请求参数 | `{"userId": 123, "includeDetails": true}` |
| **出参示例** | 响应数据 | `{"id": 123, "name": "张三", "email": "..."}` |
| **类型定义** | TypeScript 类型 | "需要更新 `frontend/src/types/user.ts` 中的 User 接口" |

### 当时我的 Prompt 示例

```
请帮我写一个 Python 函数，功能是：
1. 接收一个字符串参数
2. 判断这个字符串是否是合法的邮箱地址
3. 如果是邮箱返回 True，否则返回 False
4. 需要使用正则表达式
5. 要考虑各种边界情况
6. 要添加详细的注释
7. 要写单元测试
```

### 现在回想起来

当时的我虽然谨慎，但这种使用方式效率真的很低... 😅

**但这是每个人的必经之路！** 所以不要觉得自己笨，大家都是这样过来的。

---

**下一章**：我们会遇到什么问题？AI 为什么会让我头疼？敬请期待！


## 测验：VibeCoding 入门测验

```yaml
passing_score: 60
```

### 题目 1

```yaml
question_type: single
correct_answer: 2
explanation: 清晰简洁的指令配合必要上下文是最高效的沟通方式。
```

**题目内容：** 初次使用 AI 编程时，以下哪种做法是正确的？

- A) 越详细越好，把所有想到的都写上去
- B) 越简单越好，AI 应该能理解我的意图
- C) 清晰简洁的指令，配合必要的上下文
- D) 直接让 AI 猜我想要什么

### 题目 2

```yaml
question_type: single
correct_answer: 1
explanation: 提供上下文、期望和约束条件，AI 更容易理解需求。
```

**题目内容：** 以下哪种 Prompt 方式更容易获得好结果？

- A) 帮我写个函数
- B) 用 Python 写一个验证邮箱的函数，需要考虑边界情况，添加注释
- C) 写代码，要能用的
- D) 你看着写吧，反正你要帮我写好

---

## 资源：Prompt 模板示例

```yaml
resource_type: code_sample
```

这是一个好的 Prompt 模板示例，展示了如何清晰地描述需求。

---

## 章节：ai-problems

```yaml
order: 2
title: 第二章：遇到问题 - AI 乱改代码的困扰 🤯
chapter_type: story
is_locked: true
```

## 内容

## 问题出现了...

随着使用 AI 的频率增加，问题也随之而来。

### 经典场景

#### 场景 1：修改一个函数，结果改了十个文件

```
我：请帮我修改 login 函数的密码验证逻辑

AI：好的，我修改了以下内容：
- ✅ 修改了 login 函数
- ✅ 修改了 user 模型
- ✅ 修改了数据库迁移文件
- ✅ 修改了前端登录页面
- ✅ 修改了 API 文档
- ✅ ...（还有 20 个文件）
```

**我**：？？？我只是想改个密码验证啊！

#### 场景 2：理解错了需求

```
我：把这个按钮改成蓝色

AI：好的，我把整个页面的主题色都改成了蓝色
```

**我**：...

### 当时的感受

> "这个 AI 怎么这么笨啊！"
> "它能不能只听我的话，不要自作主张？"
> "每次都要花大量时间 review 它改的代码..."

### 转折点

就在我快要放弃的时候，我发现了一个神器...

---

**下一章**：rules 是如何拯救我的！


## 测验：AI 问题识别测验

```yaml
passing_score: 60
```

### 题目 1

```yaml
question_type: multiple
correct_answer: 0,1,2
explanation: 以上三个选项都是常见原因。
```

**题目内容：** AI 经常乱改代码，可能的原因是什么？（多选）

- A) 没有明确的 Rules 约束
- B) 需求描述不够清晰
- C) AI 过度理解了需求
- D) 电脑配置不够好

### 题目 2

```yaml
question_type: single
correct_answer: 1
explanation: 使用 Rules 明确约束 AI 的行为是最有效的解决方案。
```

**题目内容：** 当你发现 AI 改了不该改的文件时，应该怎么做？

- A) 放弃使用 AI，太难用了
- B) 使用 Rules 明确告诉 AI 只修改指定文件
- C) 每次都手动改回来
- D) 把 AI 骂一顿

---

---

## 章节：discover-rules

```yaml
order: 3
title: 第三章：发现规则 - rules 的拯救 🎉
chapter_type: code
is_locked: true
```

## 内容

## 柳暗花明！

当我发现 rules 的时候，感觉就像发现了新大陆！

### 什么是 Rules？

Rules 是一组规则文件，用来规范 AI 的行为。它告诉 AI：

- ✅ **应该做什么**
- ❌ **不应该做什么**
- 📋 **如何思考和行动**

### 我的第一条 Rules

```markdown
# AI 助手行为规范

## 代码修改原则
1. **最小化修改**：只修改我明确要求修改的部分
2. **不要擅自添加**：不要添加我未要求的功能
3. **保持原有风格**：保持代码的原有风格和格式
4. **说明变更**：修改前先告诉我改了哪里

## 代码质量要求
1. 添加必要的注释
2. 遵循项目的代码规范
3. 考虑边界情况
```

### 使用 Rules 后的变化

| 之前 | 之后 |
|------|------|
| AI 乱改一堆代码 | 只改我要求的地方 ✅ |
| 需要大量 review | 改动清晰，快速 review ✅ |
| 经常要反复修正 | 第一次就做对 ✅ |
| 感觉 AI 很笨 | 感觉 AI 变聪明了 ✅ |

### 实战示例

**Before (没有 rules)**:
```
用户：修改 login 函数的密码验证
AI：改了 50 个文件，包括一些不该改的...
```

**After (有 rules)**:
```
用户：修改 login 函数的密码验证
AI：好的，我只修改了 login 函数中的密码验证逻辑，变更如下：
- 第 10 行：添加了密码长度检查
- 第 15 行：添加了特殊字符检查
```

---

**动手试试**：下一章我们会学习更强大的工具！


## 测验：Rules 使用测验

```yaml
passing_score: 80
```

### 题目 1

```yaml
question_type: single
correct_answer: 2
explanation: Rules 的核心作用是规范 AI 的行为模式。
```

**题目内容：** Rules 的主要作用是什么？

- A) 让代码运行更快
- B) 自动生成代码
- C) 规范 AI 的行为模式
- D) 美化代码格式

### 题目 2

```yaml
question_type: multiple
correct_answer: 0,1,3
explanation: 代码规范、沟通偏好、项目约束都是 Rules 的内容，但业务逻辑不应该放在 Rules 中。
```

**题目内容：** 以下哪些内容适合放入 Rules？（多选）

- A) 代码风格和规范
- B) 具体的业务逻辑
- C) 今天的天气
- D) 沟通方式和偏好

---

## 资源：Rules 模板

```yaml
resource_type: template
```

可以直接使用的 Rules 模板，包含常用规范。

---

## 章节：advanced-tools

```yaml
order: 4
title: "第四章：进阶工具 - OpenSpec & Superpowers 🚀"
chapter_type: code
is_locked: true
```

## 内容

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

```yaml
# user-login.spec
feature: 用户登录
description: 用户可以通过邮箱和密码登录系统

requirements:
  - 用户输入邮箱和密码
  - 验证邮箱格式
  - 验证密码正确性
  - 登录成功返回 token
  - 失败显示错误信息

constraints:
  - 密码至少 8 位
  - token 有效期 24 小时
  - 支持记住登录状态

api:
  - POST /api/v1/auth/login
    request:
      email: string (required)
      password: string (required, min: 8)
      remember: boolean (optional)
    response:
      token: string
      expiresIn: number
      user: UserDTO
```

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


## 资源：Spec 文件示例

```yaml
resource_type: code_sample
```

完整的 Spec 文件示例，包含功能需求和技术约束。

---

## 章节：openspec-vs-speckit

```yaml
order: 5
title: 第五章：对比思考 - 三大工具对比 ⚖️
chapter_type: video
is_locked: true
```

## 内容

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
