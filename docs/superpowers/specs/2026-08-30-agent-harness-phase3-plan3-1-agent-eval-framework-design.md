# P3-⑨ Agent 评估框架 设计文档

**日期**：2026-08-30
**Phase**：3-Plan-3-1（对应原 P3 列表第 9 项 "Agent 评估框架"）
**状态**：已实现（2026-08-30；验证：pytest tests/harness 730 passed / 前端 build + tsc 通过）

---

## 1. 背景与目标

Agent 改动（system_prompt 调整、模型切换、工具增删）目前没有质量回归手段——只能人工聊天试。评估框架提供"用例集 → 跑 Agent → LLM Judge 打分 → 报告"的最小闭环。

**v1 范围**：评估 Agent 的核心回答质量（system_prompt + 模型生成路径）。工具编排行为评估（多步 ReAct 轨迹评测）是非目标。

## 2. 数据模型

| 表 | 字段 |
|---|---|
| `agent_eval_runs` | id PK, agent_id UUID（逻辑关联，不加 FK 以保持与 traces 同构）, user_id, name, status(pending/running/completed/failed), total_cases, passed_cases, avg_score Float, total_duration_ms, error Text, created_at, completed_at |
| `agent_eval_cases` | id PK, run_id FK CASCADE, input Text, expected Text, actual_output Text, score Float, judge_reasoning Text, latency_ms Int, status(success/error), created_at |

migration `20260830d`（down_revision `20260830c`，幂等）。

## 3. 核心流程

```
POST /api/v1/admin/agents/{agent_id}/evals        # admin
  body: {name, cases: [{input, expected}], judge_threshold?: 0.7}
    │
    ▼
EvalService.run_eval(agent, cases, threshold)
    │ 创建 run(status=running) + case rows(pending)
    ▼  对每个 case：
    ├─ 回答生成：LLM gateway（system=agent.system_prompt, user=input）
    ├─ LLM Judge：固定评审 prompt，要求 JSON {"score": 0-1, "reasoning": "..."}
    │    └─ 解析失败降级：score=0.0 + reasoning="judge 输出解析失败"
    └─ 更新 case（actual_output/score/reasoning/latency）
    ▼
聚合 passed_cases（score>=threshold）/ avg_score / status=completed → 返回 run 摘要

GET /api/v1/admin/agents/{agent_id}/evals        # run 列表
GET /api/v1/admin/agent-evals/{run_id}           # run 详情（含 cases）
```

- 单 case 失败不阻断整体（status=error、score=0，继续下一 case）
- run 级异常：status=failed + error 落库
- LLM 网关注入：`EvalService(db, llm_gateway)`——测试用 Fake gateway

## 4. 测试策略

| 用例 | 覆盖 |
|---|---|
| Fake gateway 返回固定答案+judge JSON | run/case 落库、passed/avg 聚合正确 |
| judge 返回非 JSON | 降级 score=0 + reasoning 标注 |
| 单 case LLM 抛错 | 该 case error，run 仍 completed |
| threshold 边界 | score==threshold 计入 passed |
| API | admin 门控 403；404；列表/详情形状 |

前端：AgentManagement 行操作加"评估"按钮 → 弹窗（name + cases JSON textarea + 运行）→ 结果展示（通过率/均分/case 明细）。

## 5. 不做清单

| 不做 | 留给 |
|---|---|
| 多步工具轨迹评测 | 候选续作 |
| 评测集持久化复用（独立 eval_set 表） | 候选续作 |
| 人工标注复核流程 | 不做 |
| 并发跑 case | YAGNI（串行足够） |

## 6. 决策记录

- **LLM Judge 而非精确匹配**：开放式回答无唯一正确答案，judge 0-1 分 + reasoning 是业界通行做法（ Ragas/DeepEval 同思路）
- **直接 gateway 而非完整 AgentRuntime**：runtime 依赖会话/工具/记忆栈，单 plan 内搭脚手架成本高；回答质量评估已覆盖主要回归面（prompt/模型），工具行为回归靠集成测试
