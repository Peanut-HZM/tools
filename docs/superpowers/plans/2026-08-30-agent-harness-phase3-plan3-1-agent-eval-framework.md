# P3-⑨ Agent 评估框架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 评估闭环：admin 提交用例集 → 逐 case 生成回答 + LLM Judge 打分 → run/case 落库 → 列表/详情查询 → 前端评估弹窗。

**Architecture:** 两张新表（`agent_eval_runs` / `agent_eval_cases`）+ `EvalService(db, bridge)`（bridge=LLMFunctionBridge，测试注入 Fake）；回答与 judge 都走 `bridge.generate(messages, tools=[])` 读 `text_part`；单 case 失败不阻断。

**Tech Stack:** Python 3.10 / FastAPI / React 18

## Global Constraints

中文注释+日志；migration `20260830d` 幂等（down_revision `20260830c`）；judge JSON 解析失败降级 score=0；API 仅 admin；每 Task TDD + 退出码门控提交；验证 `pytest tests/harness -x -q`、前端 build+tsc。

---

### Task 1: 模型 + migration

**Files:** Create `backend/app/models/agent_eval.py`（AgentEvalRun / AgentEvalCase，字段见 spec §2；run 的 agent_id/user_id 为 UUID 无 FK）；Create `backend/alembic/versions/20260830d_agent_eval.py`；Modify `tests/harness/conftest.py`（import 注册）；Test `test_models.py` 追加建表+默认值用例（flush 后断言，参照 ② 的写法）。

- [ ] 写失败测试 → FAIL → 实现 → PASS → commit `"feat(harness): agent eval run/case models"`

### Task 2: EvalService

**Files:** Create `backend/app/services/harness/eval_service.py`；Create `backend/tests/harness/test_eval_service.py`

**Interfaces（Produces）:**
- `EvalService(db, bridge)`；`async run_eval(agent, user_id: uuid.UUID, name: str, cases: list[dict], judge_threshold: float = 0.7) -> AgentEvalRun`
- 回答调用：`await self._bridge.generate(messages=[{"role":"system","content":agent.system_prompt},{"role":"user","content":case_input}], tools=[])` → `resp.text_part`
- Judge prompt（中文，要求仅输出 JSON）：系统="你是评估员…"，用户含 input/expected/actual；解析 `json.loads` + 首个 `{...}` 正则兜底；score clamp [0,1]
- 聚合：`passed_cases = count(score >= threshold 且 status=="success")`；`avg_score = mean(全部 case score)`；`total_duration_ms`
- 单 case bridge 抛错 → case(status="error", score=0, judge_reasoning=异常类型名)，继续
- run 级异常 → status="failed" + error 字段（异常类型名），re-raise 交由路由转 500？不 re-raise：返回 failed run（路由按状态返回 200）

**测试（Fake bridge 可编程返回序列）：** 全通过用例聚合；judge 非 JSON 降级；单 case 抛错不阻断；threshold 边界（score==0.7 计入 passed）

- [ ] TDD → commit `"feat(harness): EvalService with LLM judge scoring"`

### Task 3: API

**Files:** Modify `backend/app/api/routes/agents.py`（3 端点 + `EvalCaseCreate`/`EvalRunCreate` schema；require_admin）；Create `backend/tests/harness/test_agent_eval_api.py`

**端点：**
- `POST /api/v1/admin/agents/{agent_id}/evals`：body `{name, cases: [{input(≥1), expected(≥1)}], judge_threshold?}`；构造 `OrderedLLMGateway(db)` + `LLMFunctionBridge` → run_eval；同步返回 run 摘要（201）
- `GET /api/v1/admin/agents/{agent_id}/evals`：run 列表（created_at desc）
- `GET /api/v1/admin/agent-evals/{run_id}`：run + cases 明细；404

**测试：** 形状断言（patch EvalService.run_eval 为 Fake 避免 LLM 依赖——路由层测试 monkeypatch `app.api.routes.agents.EvalService`）；admin 门控 403；404。

- [ ] TDD → commit `"feat(harness): agent eval API endpoints"`

### Task 4: 前端

**Files:** Modify `frontend/src/services/agentApi.ts`（`runAgentEval / listAgentEvals / getAgentEval` 3 方法 + 类型）；Modify `frontend/src/components/Admin/AgentManagement.tsx`（行操作"评估"按钮 + 弹窗：name、cases JSON textarea、运行结果——通过率/均分/case 列表）

- [ ] 实现 → `npx tsc --noEmit` + `npm run build` 门控 → commit `"feat(frontend): agent eval dialog"`

### Task 5: 回归 + 收尾

- [ ] `pytest tests/harness -q` 全绿 → spec 状态改已实现 → commit `"docs(harness): mark P3-⑨ agent eval framework as implemented"`

## 验收标准

pytest 全绿（Fake bridge 覆盖聚合/降级/隔离分支）；API 门控正确；前端 build 通过、评估弹窗可发起并展示结果。
