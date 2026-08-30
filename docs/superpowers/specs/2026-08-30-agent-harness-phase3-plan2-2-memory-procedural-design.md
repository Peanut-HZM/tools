# P2-② Memory procedural（Agent 技能系统）设计文档

**日期**：2026-08-30
**Phase**：3-Plan-2-2（对应原 P2 列表第 6 项 "Memory procedural（Agent 技能系统）"）
**状态**：设计完成（自主决策模式）
**对应规划 ID**：Phase 3 设计文档 §11.4 P2 列表第 6 项；plan1b 设计文档注明"Procedural Memory → Phase 3 后续 plan"

---

## 1. 背景与目标

### 1.1 背景

现有记忆体系（Phase 2 Plan-2 + Phase 3 Plan-1B）覆盖两类：
- **短期记忆**：会话消息策略（full / sliding_window）
- **长期记忆**：`agent_memory_long_term` KV 存储 + pgvector 向量检索，注入 system prompt

缺失第三类：**程序性记忆（procedural memory，MemGPT 术语）**——Agent 在交互中沉淀的"做事方法"（工作步骤、操作流程、用户偏好格式），以命名技能形式积累与复用。KV 记忆存"事实"，技能存"怎么做"；两者生命周期与使用方式不同（技能有名字唯一性、启用开关、使用计数）。

### 1.2 目标

Agent（在 `memory_procedural_enabled=True` 时）可以：
1. **沉淀技能**：把被验证有效的操作流程存为命名技能（LLM 调 `skill_save`）
2. **发现技能**：system prompt 注入轻量技能索引（名称 + 触发条件），LLM 按需 `skill_read` 加载完整内容（渐进披露，不浪费 token）
3. **管理技能**：用户通过 REST API / 前端查看、新增、删除技能

### 1.3 非目标

- 不做技能的向量自动匹配注入（技能索引直接进 prompt，规模小、确定性高；向量匹配留候选续作）
- 不做跨 Agent / 全局技能共享（沿用 (agent_id, user_id) 隔离模型）
- 不做技能版本历史 / 审计
- 不做技能市场（与 P2-④ Agent 市场合并考虑）

---

## 2. 架构总览

### 2.1 组件布局

```
backend/app/
├── models/
│   ├── agent.py                      # + memory_procedural_enabled 列
│   └── agent_procedural_memory.py    # 新增：技能 ORM
├── services/harness/
│   ├── skill_service.py              # 新增：技能 CRUD 服务
│   ├── agent_runtime.py              # + 技能索引注入 system prompt
│   └── tools/
│       ├── skill_save.py             # 新增 BuiltinTool
│       ├── skill_read.py             # 新增 BuiltinTool
│       └── skill_delete.py           # 新增 BuiltinTool
├── api/routes/
│   └── harness_skills.py             # 新增：技能 REST API
└── alembic/versions/
    └── 20260830b_memory_procedural.py

frontend/src/
├── api/harnessSkillsApi.ts           # 新增
└── components/Harness/SkillsViewer.tsx  # 新增（镜像 MemoryViewer）
```

### 2.2 数据模型

新表 `agent_procedural_memory`：

| 列 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| agent_id | UUID FK agents CASCADE | 与 agent_memories 同构 |
| user_id | UUID（无 FK，与现状一致） | 按 (agent, user) 隔离 |
| name | String(100) | 技能名（LLM 调用凭据），UniqueConstraint(agent_id, user_id, name) |
| trigger | Text | 何时使用该技能（进入索引供 LLM 判断） |
| content | Text | 技能完整内容（步骤/规则，skill_read 时返回） |
| importance | Float default 0.5 | 预留排序用 |
| use_count | Integer default 0 | skill_read 完整读取次数 |
| is_enabled | Boolean default True | 禁用后不进索引、不可读 |
| created_at / updated_at | DateTime | DB 默认值维护 |

`agents` 表新增 1 列：`memory_procedural_enabled` Boolean，default False（零破坏）。

### 2.3 运行时数据流

```
[system prompt 组装（agent_runtime）]
    │ agent.memory_procedural_enabled=True
    ▼
SkillService.list_enabled(agent_id, user_id)
    │ → 空：不注入任何块
    │ → 非空：注入
    ▼
<procedural_memory>
你可以使用以下技能（skill）。当任务匹配某技能的触发条件时，
调用 skill_read(name=...) 获取完整步骤后遵循执行：
- deploy_check: 部署前检查清单 (使用次数: 3)
- weekly_report: 周报格式与流程 (使用次数: 1)
</procedural_memory>

[LLM 决策匹配 → skill_read(name)]
    │
    ├─ 返回 {name, trigger, content, use_count}
    └─ use_count += 1（读即计数）
```

### 2.4 工具行为定义

| 工具 | 参数 | 行为 |
|---|---|---|
| `skill_save` | name(必填≤100), trigger(必填), content(必填), importance(可选 0-1) | 按 name UPSERT；更新时保留 use_count |
| `skill_read` | name(可选) | 传 name：返回完整内容 + use_count+1（禁用技能返回 error）；不传：返回启用技能索引 [{name, trigger, use_count}] |
| `skill_delete` | name(必填) | 删除；不存在返回 error |

可用性门控：`is_available` 查询 `agent.memory_procedural_enabled`（与 memory_read 同模式，查询失败保守返回 False）。

---

## 3. 关键设计

### 3.1 为什么索引注入而非向量检索

技能数量级为个位到十位，name+trigger 索引每条 ~30 token，直接注入成本可忽略且**确定可见**（LLM 每轮都知道有哪些技能可用）。向量检索引入延迟、阈值调参和漏召回风险，收益为负——YAGNI。技能数增长后（>50）再考虑分层索引。

### 3.2 隔离模型

沿用长期记忆的 (agent_id, user_id) 二元隔离：技能是"这个用户教会这个 Agent 的方法"，不跨用户共享（安全默认），不跨 Agent 共享（避免技能语义漂移）。

### 3.3 REST API

`/api/v1/harness/agents/{agent_id}/skills`（鉴权与 harness_memories 同模式）：

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | `` | 列出当前用户对该 Agent 的全部技能（含禁用） |
| POST | `` | 创建/更新技能 {name, trigger, content, importance?} |
| DELETE | `/{name}` | 删除技能 |

### 3.4 错误处理表

| 场景 | 行为 |
|---|---|
| 未启用 procedural 的 Agent 调用技能工具 | 工具不在可用列表（is_available=False），LLM 看不到 |
| skill_save 重名 | UPSERT 覆盖（trigger/content/importance 更新，use_count 保留） |
| skill_read 禁用技能 | ToolResult.error("技能已禁用") |
| system prompt 注入查询失败 | best-effort：warning 日志 + 不注入（不阻塞对话，与长期记忆同策略） |
| 技能索引过大（>20 条） | 注入前按 updated_at 截断前 20 条 + 提示语"仅显示最近使用的技能" |

---

## 4. 测试策略

### 4.1 后端单元测试

| 文件 | 用例 |
|---|---|
| `test_skill_service.py` | save 新建/UPSERT（use_count 保留）/get/list_enabled 过滤禁用/delete/increment_use_count |
| `test_skill_tools.py` | 三个工具：参数校验（缺 name/超长）、门控（未启用不可用）、save/read/delete 全分支、use_count 递增 |
| `test_runtime_skills.py` | runtime：enabled 且有技能 → system prompt 含 `<procedural_memory>` 索引；未启用/空技能 → 不注入；>20 条截断 |
| `test_harness_skills_api.py` | REST：list/create/delete/未授权 401/跨用户隔离 |
| `test_models.py` 追加 | 新 ORM 列与约束 |

### 4.2 集成回归

- 现有 memory 相关测试全部保持通过（零行为变化）
- migration 幂等（IF NOT EXISTS 模式）

### 4.3 前端

- `npm run build` + `npx tsc --noEmit`（本次改动文件无错误）
- SkillsViewer 测试（镜像 MemoryViewer.test.tsx 模式：渲染列表/删除调用 API）

---

## 5. 已知限制 / 不做清单

| 不做 | 留给 |
|---|---|
| 技能向量自动匹配注入 | 技能数 >50 时再评估 |
| 跨 Agent/全局技能库 | 候选续作（需权限模型设计） |
| 技能版本历史 | 不做 |
| LLM 自动沉淀（对话结束自动总结技能） | 候选续作（涉及额外 LLM 调用成本） |

---

## 6. 决策记录

### 6.1 为什么独立表而非 KV 加前缀

技能有独立生命周期字段（name 唯一约束、is_enabled、use_count），塞进 KV 的 JSONB value 里无法用 DB 约束保证一致性，且查询模式完全不同（索引注入 vs 向量检索）。独立表 = 清晰边界。

### 6.2 为什么 skill_read 即计数

use_count 是技能价值的直接信号（前端排序 + 未来清理依据）。skill_read 是唯一消费完整内容的路径，读即用，无需独立 invoke 语义。

---

## 7. 参考 / 相关

- `backend/app/services/harness/memory_service.py` / `tools/memory_read.py` —— 隔离与门控模式来源
- `backend/app/services/harness/agent_runtime.py:363-417` —— system prompt 注入模式来源
- `docs/superpowers/specs/2026-08-29-agent-harness-phase3-plan1b-memory-vector-design.md` —— 长期记忆向量检索（本期不复用其 embedding 链路）
