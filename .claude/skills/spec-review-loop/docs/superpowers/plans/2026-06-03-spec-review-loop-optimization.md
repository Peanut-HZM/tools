# spec-review-loop 技能优化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `spec-review-loop` 技能重构为「通用核心 + 技术栈插件」分层架构，并引入持久化发现台账、三态裁决、正面白名单，解决发现范围不准、循环终止不稳定、清单未执行、修改边界模糊四个痛点。

**Architecture:** 这是一个 skill-authoring（Markdown 文档）任务，不涉及可运行代码，因此无单元测试框架。每个任务的「验证」步骤改为对文件内容做结构/一致性检查（grep 关键标记、确认无残留旧内容），「提交」步骤标记为可选——本目录当前不是 git 仓库，且全局规则禁止自动提交，需用户明确指令后再执行。

**Tech Stack:** Markdown 技能文件（`SKILL.md` + `references/*.md`），通过 grep/文件读取做验证。

**约定（所有任务通用）：**
- 工作根目录：`/Users/huazhongmin/.agents/skills/spec-review-loop`
- 所有写入/对话/注释用中文，技术术语保留英文。
- 「提交」步骤为可选：仅当用户明确说「提交」且目录已是 git 仓库时执行；否则跳过。
- 每个任务完成后做该任务的内容验证，再进入下一个任务。

---

## 文件结构（落地后）

```
spec-review-loop/
├── SKILL.md                          # 重写：语言无关核心（发现→台账→循环→报告→边界）
├── references/
│   ├── checklist-core.md             # 新建：维度3(SQL)、维度4(设计完整性)，语言无关
│   ├── checklist-java-spring.md      # 新建：维度1、2，Java/Spring/MyBatis 专属（原清单迁移）
│   └── stack-detection.md            # 新建：技术栈识别规则 + 降级策略
└── (删除) references/review-checklist.md   # 内容已拆分迁移
```

职责划分：
- `SKILL.md`：流程编排，不含任何特定语言检查项。
- `checklist-core.md`：通用审查项（维度 3、4）。
- `checklist-java-spring.md`：Java 栈插件（维度 1、2）。
- `stack-detection.md`：决定加载哪个插件，未命中时降级。

---

## 任务依赖顺序

Task 1（核心清单）→ Task 2（Java 插件）→ Task 3（栈识别）→ Task 4（重写 SKILL.md）→ Task 5（删除旧文件）→ Task 6（整体一致性自检）。

Task 1-3 创建新插件文件，互不依赖具体顺序但建议按编号；Task 4 引用前三者文件名，须在其后；Task 5 在 Task 1、2 确认内容已迁移后执行。

---

### Task 1: 创建通用核心清单 checklist-core.md

**Files:**
- Create: `references/checklist-core.md`
- Reference: `references/review-checklist.md`（维度 3、4 内容来源）

- [ ] **Step 1: 创建 references/checklist-core.md，写入维度 3、4 的语言无关清单**

将原 `review-checklist.md` 的维度 3、维度 4 全部表格迁入，去除 Java 专属措辞（如「MyBatis」改为「ORM/数据访问层」），保留 SQL 幂等与设计完整性的全部检查项。文件内容：

````markdown
# 审查检查清单 · 通用核心

本文件供 spec-review-loop 技能逐项对照审查。维度 3、4 与具体后端语言无关，所有项目均适用。

---

## 维度 3：SQL 幂等性与数据安全

### 3.1 DDL 幂等性

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| CREATE TABLE 幂等 | 检查是否有 IF NOT EXISTS | 直接 CREATE TABLE 导致重复执行报错 | 添加 IF NOT EXISTS |
| ALTER TABLE 幂等 | 检查 ADD/DROP COLUMN 是否有 IF EXISTS/IF NOT EXISTS | 重复 ALTER 报错 | 添加条件判断 |
| DROP 语句 | 搜索 DROP 关键字 | 存在 DROP TABLE/DROP DATABASE | 移除或改为安全删除 |
| TRUNCATE 语句 | 搜索 TRUNCATE 关键字 | 存在 TRUNCATE TABLE | 移除或改为 DELETE WITH 条件 |

### 3.2 DML 幂等性

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 种子数据幂等 | 检查 INSERT 语句是否有冲突处理 | 纯 INSERT 导致重复执行主键冲突 | 添加 ON DUPLICATE KEY UPDATE 或改为先删后插 |
| INSERT 字段列表 | 检查 INSERT 是否显式声明字段列表 | INSERT INTO t VALUES(...) 无字段列表 | 添加显式字段列表 |
| 无条件 DELETE/UPDATE | 检查 WHERE 子句是否存在 | DELETE/UPDATE 无 WHERE 条件 | 添加 WHERE 条件 |
| 默认值 | 检查新增 NOT NULL 字段是否有 DEFAULT | 新增 NOT NULL 字段无默认值 | 设置合理 DEFAULT 值 |
| 执行顺序依赖 | 检查多条 SQL 之间是否有隐式顺序依赖 | SQL 依赖前一条的执行结果 | 添加注释标注执行顺序 |

### 3.3 数据安全

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 外键约束 | 检查新增外键是否影响现有数据 | 外键引用的父表数据不存在 | 先确保父表数据存在或使用 SET NULL |
| 数据迁移 | 检查是否有数据迁移 SQL | 迁移 SQL 不可逆 | 添加回滚 SQL |

---

## 维度 4：设计完整性与一致性

### 4.1 文档一致性

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 设计文档与实现计划对齐 | 对比设计文档的功能点与实现计划的步骤 | 设计有 5 个功能点但计划只有 4 个步骤 | 补充遗漏步骤 |
| 多文档间矛盾 | 对比同一功能的多份设计文档 | 两份文档对同一字段类型描述不同 | 统一为最新版本 |
| 占位符 | 搜索 TBD、TODO、FIXME、XXX | 存在未填写的占位符 | 填写具体内容或删除 |
| 模糊需求 | 检查"等"、"相关"、"适当"等模糊词 | 需求描述含糊 | 明确量化或举例说明 |

### 4.2 实现完整性

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 步骤可执行 | 检查每个实现步骤是否有具体操作 | 步骤描述过于抽象 | 拆分为具体操作步骤 |
| 边界条件 | 检查是否覆盖空值、越界、并发等场景 | 只描述正常流程 | 补充异常场景处理 |
| 前后端契约 | 对比 Request/Response 字段与前端接口定义 | 字段名或类型不一致 | 对齐前后端契约 |
| 回滚方案 | 检查是否有回滚或降级策略 | 无回滚方案 | 补充回滚 SQL 或降级逻辑 |
| 异常处理 | 检查是否描述异常处理策略 | 缺少异常处理说明 | 补充异常场景和处理方式 |
````

- [ ] **Step 2: 验证文件已创建且含维度 3、4 关键项**

Run: `grep -c "维度 3\|维度 4\|IF NOT EXISTS\|ON DUPLICATE KEY\|回滚" references/checklist-core.md`
Expected: 输出 ≥ 5（关键标记齐全）

- [ ] **Step 3: 验证未残留 Java 专属词**

Run: `grep -n "MyBatis\|LambdaQueryWrapper\|Controller" references/checklist-core.md || echo "OK-无Java专属词"`
Expected: 输出 `OK-无Java专属词`

- [ ] **Step 4: 提交（可选）**

```bash
# 仅当用户要求提交且为 git 仓库时执行
git add references/checklist-core.md
git commit -m "feat: 新增通用核心审查清单（维度3、4）"
```

---

### Task 2: 创建 Java 栈插件 checklist-java-spring.md

**Files:**
- Create: `references/checklist-java-spring.md`
- Reference: `references/review-checklist.md`（维度 1、2 内容来源）

- [ ] **Step 1: 创建 references/checklist-java-spring.md，原样迁入维度 1、2 全部检查项**

将原 `review-checklist.md` 的维度 1、维度 2 表格一字不改迁入（保留全部 Java/Spring/MyBatis 项），仅在文件头标注其为 Java 栈插件。文件内容：

````markdown
# 审查检查清单 · Java / Spring 栈插件

本文件为 spec-review-loop 的技术栈插件，仅在项目识别为 Java/Spring 时加载，覆盖维度 1、2。

---

## 维度 1：项目规范符合性

### 1.1 CLAUDE.md / AGENTS.md 规范遵守

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| Controller 无业务逻辑 | 检查 Controller 方法体是否包含 if/for/计算逻辑 | Controller 中直接做数据转换、条件判断 | 将逻辑移至 Service 层 |
| request/response 封装 | 检查 Controller 入参是否使用 Request 对象 | 直接传 entity 或基本类型参数 | 创建 Request/Response DTO |
| String 接收 Long | 检查 Request/Response 中主键字段类型 | 使用 Long 类型接收主键 | 改为 String 类型，Service 层转换 |
| 路径命名驼峰 | 检查 @GetMapping/@PostMapping 的 value 属性 | 使用下划线分隔或为空 | 改为驼峰命名，显式指定 value |
| LambdaQueryWrapper | 检查 Mapper 调用是否使用 Lambda 链式 | 使用字符串字段名构造条件 | 改为 Lambda 表达式引用 |
| 避免循环中 DB 操作 | 检查 for/while 循环内是否有 Mapper 调用 | 循环内逐条 insert/update | 改为批量操作 |
| 类级+方法级注释 | 检查类和方法是否有中文注释 | 缺少 @author 或方法说明 | 补充注释 |
| 日志中文 | 检查 log.info/error 的消息文本 | 日志使用英文描述 | 改为中文描述 |
| import 导包 | 检查代码中是否有全限定名称引用 | 如 `com.xxx.SomeClass` 直接使用 | 添加 import 语句 |
| @Schema 注解 | 检查 Request/Response 字段是否有 @Schema | 字段缺少 API 文档注解 | 补充 @Schema 注解 |
| 枚举不作为字段类型 | 检查 entity/request/response 中是否有枚举字段 | 使用枚举类作为 DTO 字段 | 改为 String/Integer |

### 1.2 接口设计规范

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| Mapping 注解显式 value | 检查 @GetMapping/@PostMapping 是否指定 value | 使用空注解 @GetMapping() | 显式指定 value 属性 |
| 禁止 @PathVariable | 检查是否使用 @PathVariable | 路径参数使用 /{id} 格式 | 改为 @RequestParam |
| Result 返回类型 | 检查 Controller 返回类型是否为 Result | 直接返回业务对象 | 包裹为 Result |
| @Tag/@Operation 注解 | 检查 Controller 和方法是否有 Swagger 注解 | 缺少 API 分组和操作说明 | 补充注解 |

---

## 维度 2：现有功能安全性

### 2.1 业务逻辑影响

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 新增代码影响现有流程 | 对比修改前后的方法调用链 | 新增条件分支改变原有执行路径 | 确保新增逻辑仅在新增条件下触发 |
| 接口路径冲突 | 搜索同模块 Controller 的 Mapping 注解值 | 新接口路径与已有接口重复 | 修改路径或合并接口 |
| 公共方法签名变更 | 检查修改方法的参数列表和返回类型 | 增加参数或修改返回类型 | 保持向后兼容，新增重载方法 |
| Bean 注入冲突 | 检查同类型 Bean 是否有多个实现 | 新增同类型 Bean 导致注入歧义 | 使用 @Qualifier 或 @Primary |
| Mapper XML 影响 | 检查修改的 SQL 片段是否被其他方法引用 | 修改共用 SQL 片段影响其他调用方 | 新增独立 SQL 片段 |
| N+1 查询 | 检查循环内是否有单条查询调用 | 循环内调用 getById | 改为批量查询 |

### 2.2 配置影响

| 检查项 | 检查方法 | 常见问题 | 修复建议 |
|--------|----------|----------|----------|
| 新增配置影响其他模块 | 检查新增配置项的作用范围 | 全局配置影响所有模块 | 缩小配置作用范围 |
| 循环中调用远程接口 | 检查 for/while 内是否有 feign/http 调用 | 循环内逐条调用远程服务 | 改为批量接口或并行调用 |
````

- [ ] **Step 2: 验证文件含维度 1、2 与 Java 关键项**

Run: `grep -c "维度 1\|维度 2\|LambdaQueryWrapper\|Bean 注入\|N+1" references/checklist-java-spring.md`
Expected: 输出 ≥ 4

- [ ] **Step 3: 验证两份清单合计覆盖原文件全部 4 个维度**

Run: `grep -h "^## 维度" references/checklist-core.md references/checklist-java-spring.md | sort`
Expected: 列出「维度 1」「维度 2」「维度 3」「维度 4」共 4 行

- [ ] **Step 4: 提交（可选）**

```bash
git add references/checklist-java-spring.md
git commit -m "feat: 新增 Java/Spring 栈审查插件（维度1、2）"
```

---

### Task 3: 创建技术栈识别规则 stack-detection.md

**Files:**
- Create: `references/stack-detection.md`

- [ ] **Step 1: 创建 references/stack-detection.md，写入识别规则与降级策略**

文件内容：

````markdown
# 技术栈识别规则

spec-review-loop 启动时按本规则识别项目技术栈，决定加载哪个栈插件。维度 3、4 的通用核心清单（`checklist-core.md`）始终加载。

## 识别规则

| 特征文件 | 判定栈 | 加载插件 |
|----------|--------|----------|
| `pom.xml` / `build.gradle` / `build.gradle.kts` | Java/Spring | `checklist-java-spring.md` |
| `package.json`（含 vue/react 依赖） | 前端 | `checklist-frontend.md`（暂未提供，缺失时降级） |
| `pyproject.toml` / `requirements.txt` | Python | `checklist-python.md`（暂未提供，缺失时降级） |

## 加载逻辑

1. 在项目根目录检测上述特征文件（可用 `git rev-parse --show-toplevel` 定位根目录，非 git 项目用当前工作目录）。
2. 命中多个特征时，加载所有命中的栈插件。
3. 命中的栈插件文件不存在时，视为未命中该栈。
4. 未命中任何栈插件时，仅执行通用核心清单（维度 3、4），并在报告中提示：
   > 未识别到技术栈插件，仅执行通用审查（维度 3、4）。维度 1、2 标记为 N/A。
5. 维度 1、2 在无栈插件时整体标记为 ⊘ N/A。

## 扩展方式

新增技术栈支持：新建 `checklist-<stack>.md`，并在本文件「识别规则」表新增一行。无需修改 `SKILL.md`。
````

- [ ] **Step 2: 验证文件含识别规则与降级提示**

Run: `grep -c "pom.xml\|checklist-java-spring\|未识别到技术栈\|N/A" references/stack-detection.md`
Expected: 输出 ≥ 3

- [ ] **Step 3: 提交（可选）**

```bash
git add references/stack-detection.md
git commit -m "feat: 新增技术栈识别规则与降级策略"
```

---

### Task 4: 重写 SKILL.md（语言无关核心流程）

**Files:**
- Modify: `SKILL.md`（整体重写）

- [ ] **Step 1: 整体重写 SKILL.md**

用以下内容完整替换 `SKILL.md`：

````markdown
---
name: spec-review-loop
description: 循环审查设计文档与实现方案。用户要求"审查方案/审查设计/循环审查"或调用 /spec-review-loop 时使用：自动发现当前对话创建的设计文档、计划文档、openspec 变更、SQL 和代码 diff，建立持久化发现台账，按通用核心维度（SQL 幂等、设计完整性）加适用技术栈插件维度（项目规范、功能安全）多轮循环审查并补充完善。每轮对清单逐项三态裁决（通过/发现/不适用），发现必带文件行号证据写入台账；连续 2 轮无新发现时停止；可直接修改限于白名单内，白名单外先报告后确认。输出含总体结论与待确认项的审查报告。确保不改变其他正常业务逻辑，SQL 可重复执行且不影响现有数据。
---

# Spec Review Loop

## 概述

对当前对话中创建的设计文档、计划文档、openspec 变更、SQL 文件、代码 diff 进行多轮循环审查。流程语言无关：通用核心维度（SQL 幂等性、设计完整性）始终执行；项目规范、功能安全维度按识别到的技术栈加载对应插件。审查全程由一份持久化「发现台账」驱动，确保发现可去重、终止可判定、清单被逐项执行、修改边界明确。

## 技术栈识别与插件加载

启动时按 `references/stack-detection.md` 识别项目技术栈：

- 始终加载通用核心清单 `references/checklist-core.md`（维度 3、4）。
- 命中技术栈时加载对应插件（如 Java/Spring → `references/checklist-java-spring.md`，提供维度 1、2）。
- 未命中任何栈插件时，仅执行维度 3、4，维度 1、2 整体标记为 ⊘ N/A，并在报告中提示降级。

## 输入发现

按以下来源扫描待审查内容，**优先级从高到低**：

1. **git 变更**：`git status` / `git diff` 中新增或修改的文档、SQL、代码（最可靠）
2. **对话上下文**：从对话历史中提取 brainstorming/writing-plans 输出的文件路径
3. **按日期扫描兜底**：
   - `docs/plans/`、`docs/superpowers/specs/` 中日期为今天或昨天的 `*design*.md`、`*implementation-plan*.md`
   - `openspec/changes/` 未归档的变更目录及其文件
   - `openspec/specs/` 被修改的规格文件
   - `sql/` 中新增或修改的 SQL 文件

**发现优先级**：git 变更与对话上下文中明确创建的文件优先于按日期扫描发现的文件。重叠时以高优先级来源为准。

扫描后，**先建立台账并把「待审清单」写入，停下让用户确认增删，确认后才开始审查**。

如果未发现任何待审查内容，输出"未发现待审查内容"并退出。

## 发现台账

审查开始时在 `docs/reviews/YYYY-MM-DD-<topic>-review.md` 创建台账文件（目录不存在则自动创建；用户偏好位置可覆盖）。整个循环读写它。

台账结构：

```markdown
# 审查台账：<topic>  (YYYY-MM-DD)

## 待审清单（启动时确认）
- [x] docs/plans/2026-06-03-xxx-design.md
- [x] sql/V20260603__add_user.sql

## 发现表
| ID  | 维度 | 严重 | 文件:行 | 问题 | 状态 | 发现轮次 |
|-----|------|------|---------|------|------|----------|
| F01 | 3-SQL | 高 | V20260603:12 | CREATE TABLE 无 IF NOT EXISTS | 已修复 | 1 |
| F02 | 4-设计 | 中 | design.md:40 | 回滚方案缺失 | 待确认 | 1 |

## 轮次日志
- 第1轮：新增 F01、F02；修复 F01；连续无发现计数 = 0
- 第2轮：新增 0；F02 待用户确认；连续无发现计数 = 1
- 第3轮：新增 0；连续无发现计数 = 2 → 达到终止条件，审查结束
```

发现条目固定字段：ID（F01…，全程不变）、维度（1/2/3/4）、严重（高/中/低）、文件:行（证据，⚠️ 项必填）、问题、状态（待修复/已修复/待确认/已忽略）、发现轮次。

## 审查维度

每轮按维度 1→2→3→4 逐项裁决。维度 1、2 来自技术栈插件；维度 3、4 来自通用核心。详细检查项见对应清单文件。

- **维度 1：项目规范符合性**（栈插件）
- **维度 2：现有功能安全性**（栈插件）
- **维度 3：SQL 幂等性与数据安全**（核心，`checklist-core.md`）
- **维度 4：设计完整性与一致性**（核心，`checklist-core.md`）

## 三态裁决

清单每个检查项必须落一个判定：

- ✅ **通过**：检查了，无问题。
- ⚠️ **发现**：有问题 → **必须附 `文件:行号` 证据**，并写入台账发现表。无证据的"感觉有问题"不允许写入。
- ⊘ **N/A**：本次无相关内容（如本次未改动 SQL，则维度 3 整体 N/A）。

显式区分「N/A 跳过」与「✅ 通过」。报告中只呈现 ⚠️ 发现项与 ⊘ 整体 N/A 的维度，✅ 项归并为「维度 X：N 项通过」，避免报告过长。

## 严重程度分级

- **高**：可能导致现有功能异常、数据丢失、SQL 不可重复执行。
- **中**：违反项目规范但不会导致功能异常。
- **低**：补充注释、完善文档等非功能性改进。

## 修改边界（正面白名单）

核心规则：**不在白名单内 = 高风险 = 先报告后确认。**

**可直接修改白名单（穷举）：**

- 补充注释、文档措辞、@Schema/@Tag 等纯文档性注解。
- 修正拼写、格式、缺失的 import。
- SQL 纯幂等性加固（不改数据语义）：补 `IF NOT EXISTS`/`IF EXISTS`、给种子 INSERT 补 `ON DUPLICATE KEY UPDATE`、补显式字段列表、补合理 `DEFAULT`。
- 填写文档中的 TBD/TODO 占位符（内容可从上下文 100% 明确推断时）。

**白名单外一律先确认：**

- 任何改变业务逻辑、执行路径、方法签名的修改。
- 删除/重写既有逻辑、架构性调整。
- 改动 `WHERE` 条件、涉及既有数据的 DML、外键约束。
- 任何无法从上下文 100% 确定意图的占位符填写。

## 循环流程

```
初始化：
  ├─ 识别技术栈，加载核心清单 + 适用栈插件
  ├─ 按优先级扫描发现待审查内容
  ├─ 创建台账，写入「待审清单」
  └─ 停下，让用户确认增删待审清单

第 N 轮：
  1. 重新读取台账 + 所有待审内容（含上一轮修改）
  2. 按维度 1→2→3→4 逐项裁决（✅/⚠️/⊘）
     - ⚠️ 项：查台账判重 → 新问题写入发现表（带文件:行号）
  3. 执行修改：
     - 白名单内 → 直接改，台账状态置「已修复」
     - 白名单外 → 报告，台账状态置「待确认」
  4. 写轮次日志：本轮新增 N 条、修复 M 条
  5. 判定：本轮新增 == 0 ? 连续无发现 +1 : 连续无发现清零

终止条件：连续 2 轮新增为 0
最大上限：10 轮（防止无限循环）
```

**去重规则**：本轮发现与台账已有条目同文件、同位置、同类问题时，视为重复，不写入、不计新发现数。

## 输出格式

审查结束后，由台账驱动输出报告：

```markdown
## 审查报告

### 总体结论
审查 N 轮，发现 Y 项，已修复 Z 项，待确认 W 项，其中 H 项高风险待决策。

### 各轮详情
**第 1 轮**（新增 A 项）
- [维度][严重] F01 问题描述 → 修复动作

### 待确认项（需用户决策）
- **F02**[中][维度4] 问题：回滚方案缺失（design.md:40）
  - 建议动作：补充回滚 SQL 段
  - 影响：仅文档变更，无运行时影响

### SQL 幂等性专项确认
- ✅/❌ 文件名：说明

### 现有功能安全性专项确认
- ✅/❌ 说明
```

用户可按 ID 逐条回复决策（如「F02 同意改 / F04 不改」）。

## Agent 行为约束

- 审查时只修改待审查文档本身及其关联代码文件，不修改其他无关文件。
- 白名单外的修改必须先征求用户确认再执行。
- 白名单内的修改可直接执行。

## 与现有技能的协作

- **brainstorming**：在其完成后独立调用，不嵌入其流程。
- **writing-plans**：审查范围包含其输出的实现计划文档。
- **skill-creator**：仅用于创建/修改本技能本身。

## 详细检查清单

- 通用核心（维度 3、4）：`references/checklist-core.md`
- Java/Spring 栈插件（维度 1、2）：`references/checklist-java-spring.md`
- 技术栈识别规则：`references/stack-detection.md`
````

- [ ] **Step 2: 验证 SKILL.md 含新机制关键段**

Run: `grep -c "发现台账\|三态裁决\|正面白名单\|技术栈识别\|连续 2 轮新增为 0" SKILL.md`
Expected: 输出 ≥ 4

- [ ] **Step 3: 验证 SKILL.md 不再内联具体清单表格（已外移）**

Run: `grep -c "| 检查项 |" SKILL.md || echo "OK-无内联清单表"`
Expected: 输出 `0` 或 `OK-无内联清单表`

- [ ] **Step 4: 验证 SKILL.md 正确引用三个清单文件**

Run: `grep -c "checklist-core.md\|checklist-java-spring.md\|stack-detection.md" SKILL.md`
Expected: 输出 ≥ 3

- [ ] **Step 5: 提交（可选）**

```bash
git add SKILL.md
git commit -m "refactor: 重写 SKILL.md 为分层核心流程（台账/三态裁决/白名单）"
```

---

### Task 5: 删除旧清单文件 review-checklist.md

**Files:**
- Delete: `references/review-checklist.md`

- [ ] **Step 1: 确认内容已迁移后删除旧文件**

先确认维度 1-4 已分别落在新文件中（Task 2 Step 3 已验证），再删除：

Run: `rm references/review-checklist.md && ls references/`
Expected: 列出 `checklist-core.md`、`checklist-java-spring.md`、`stack-detection.md`，无 `review-checklist.md`

- [ ] **Step 2: 全局确认无任何文件仍引用旧文件名**

Run: `grep -rn "review-checklist.md" . --include="*.md" || echo "OK-无残留引用"`
Expected: 输出 `OK-无残留引用`

- [ ] **Step 3: 提交（可选）**

```bash
git add -A
git commit -m "refactor: 删除已拆分迁移的旧清单 review-checklist.md"
```

---

### Task 6: 整体一致性自检

**Files:**
- Read-only 检查：全部 `*.md`

- [ ] **Step 1: 确认最终文件结构正确**

Run: `find . -name "*.md" -not -path "./docs/*" | sort`
Expected:
```
./SKILL.md
./references/checklist-core.md
./references/checklist-java-spring.md
./references/stack-detection.md
```

- [ ] **Step 2: 确认维度编号在各文件间一致（1、2 在 java 插件；3、4 在 core）**

Run: `grep -l "## 维度 1" references/*.md; grep -l "## 维度 3" references/*.md`
Expected: 第一条输出 `references/checklist-java-spring.md`，第二条输出 `references/checklist-core.md`

- [ ] **Step 3: 确认 SKILL.md description 与正文机制一致（台账/三态/白名单均在 description 提及）**

Run: `grep -c "台账\|三态\|白名单\|连续 2 轮" SKILL.md`
Expected: 输出 ≥ 4（description 与正文均覆盖）

- [ ] **Step 4: 确认无占位符残留**

Run: `grep -rn "TBD\|待补充\|FIXME\|XXX占位" SKILL.md references/*.md || echo "OK-无占位符"`
Expected: 输出 `OK-无占位符`

- [ ] **Step 5: 删除临时文件并提交（可选）**

```bash
rm -f docs/superpowers/plans/.gitkeep
# 仅当用户要求提交且为 git 仓库时执行
git add -A
git commit -m "chore: spec-review-loop 技能分层重构完成"
```

---

## 自检记录（计划编写者填写）

- **Spec 覆盖**：分层架构(Task 1-4)、台账(Task 4)、三态裁决(Task 4)、白名单(Task 4)、栈识别(Task 3)、删除旧文件(Task 5)、验收(Task 6) — Spec 各节均有对应任务。
- **占位符**：计划内 `<topic>`/`F01` 为模板符号，非未填项；无 TBD/TODO。
- **命名一致性**：`checklist-core.md`、`checklist-java-spring.md`、`stack-detection.md` 三个文件名在 Task 1-6 与 SKILL.md 引用中拼写一致。
