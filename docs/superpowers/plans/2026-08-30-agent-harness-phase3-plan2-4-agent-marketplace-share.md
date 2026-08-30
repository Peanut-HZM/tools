# P2-④ Agent 市场 / 分享 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** visibility 语义落地（聊天入口校验）+ 市场 API（public 目录 + fork）+ 分享 API（admin 导出/导入 bundle）+ 前端市场页与 AgentManagement visibility/导出导入 UI。

**Architecture:** 零新表零新列——复用 `agents.visibility/owner_id` 与 `agent_tools`。marketplace.py 新路由文件；export/import 挂 agents.py；chat_stream.py 加 `_can_use_agent` 校验。fork = 深拷贝 agent 核心字段 + tool_bindings。

**Tech Stack:** Python 3.10 / FastAPI / React 18 + TypeScript

## Global Constraints

- 中文注释 + 关键日志；零 schema 变更（无 migration）
- fork 只拷 spec §2.3 字段子集 + bindings；永不拷贝用户数据（memory/checkpoints/traces）
- export 仅剥离 spec 列出的字段；parameter_overrides 原样保留（admin-only，文档明示勿外传）
- 验证：`pytest tests/harness -x -q`；前端 `npm run build` + `npx tsc --noEmit`；每 Task 独立 commit（TDD，提交以 pytest 退出码门控）

---

### Task 1: 聊天入口可见性校验

**Files:** Modify `backend/app/api/routes/chat_stream.py`（Agent 加载后校验）；Create `backend/tests/harness/test_chat_visibility.py`

**Interfaces:** Produces 模块级函数 `_can_use_agent(agent, user: dict) -> bool`（private → owner 或 admin；public/unlisted → True；owner_id 为 None 的 private agent 仅 admin 可用）

**测试用例：** private+owner 可用 / private+admin 可用 / private+他人 403（直接测函数 + 路由级一条：TestClient POST chat_stream 用他人 user → 403）；public 任何人 True；owner_id=None+普通用户 False

- [ ] Step 1 写失败测试 → Step 2 FAIL → Step 3 实现（`_can_use_agent` + 加载后 `if not _can_use_agent(agent, current_user): raise HTTPException(403, "该 Agent 为私有，无权使用")`）→ Step 4 pytest 退出码门控 PASS → Step 5 commit `"fix(harness): enforce agent visibility at chat entry"`

### Task 2: 市场 API（目录 + fork）

**Files:** Create `backend/app/api/routes/marketplace.py`（router prefix `/api/v1/marketplace`）；Modify `backend/app/main.py`（挂载）；Create `backend/tests/harness/test_marketplace.py`

**Interfaces（Produces）:**
- `GET /api/v1/marketplace/agents?skip=0&limit=50`：`visibility=="public" and is_active`，按 updated_at desc；返回 `{"records": [{id,name,description,icon,icon_color,category,updated_at}], "count": n}`
- `POST /api/v1/marketplace/agents/{id}/fork`：201 返回新 agent 摘要 `{id, name, visibility, owner_id}`；非 public 403；不存在 404
- fork 深拷贝字段（与 export bundle 的 agent 子集一致）+ `tool_bindings` 全量（tool_id/parameter_overrides/priority/is_enabled）

**测试用例：** 目录仅 public+active（private/unlisted/isActive=False 不出现）；fork 字段与 bindings 断言（新 id、name+"（副本）"、owner=当前用户、visibility=private、is_default=False）；fork private 403；fork 后原 agent bindings 数不变；未登录 401（get_current_user 不覆盖时依赖实现——用覆盖 None 用户模拟 401 可省，改测 admin/普通用户均可访问）

- [ ] Step 1 写失败测试 → Step 2 FAIL → Step 3 实现 → Step 4 门控 PASS → Step 5 commit `"feat(harness): marketplace catalog + fork API"`

### Task 3: 导出/导入 API

**Files:** Modify `backend/app/api/routes/agents.py`（2 端点，require_admin）；Create `backend/tests/harness/test_agent_export_import.py`

**Interfaces（Produces）:**
- `POST /api/v1/harness/agents/{id}/export`：200 返回 bundle JSON（`{"format_version": 1, "exported_at": iso, "agent": {...剥离后字段}, "tool_bindings": [{tool_name, parameter_overrides, priority, is_enabled}]}`）
- `POST /api/v1/harness/agents/import`：body=bundle；201 返回 `{"agent": {...摘要}, "warnings": [...]}`；`format_version != 1` → 400
- 导出 agent 字段白名单：`name, description, system_prompt, icon, icon_color, category, welcome_message, handoff_instruction, generation_params, memory_short_term_policy, memory_short_term_window, max_steps_per_turn, error_strategy, max_retries, memory_procedural_enabled, sandbox_enabled, memory_long_term_enabled, memory_long_term_config`
- import：`AgentManagementService.create_agent`（或直接 ORM 构造：owner=当前 admin、visibility="private"、is_default=False、slug=`{name}-{uuid4().hex[:8]}` 若 slug 列存在）；bindings 按 `Tool.name` 匹配，缺失 → warnings

**测试用例：** export bundle 无 id/owner_id/visibility/时间戳字段；import 重建（字段一致、bindings 重挂、tool 缺失进 warnings、name 冲突自动后缀）；非 admin 403；坏版本 400

- [ ] Step 1 写失败测试 → Step 2 FAIL → Step 3 实现 → Step 4 门控 PASS → Step 5 commit `"feat(harness): agent export/import bundle API"`

### Task 4: 前端（市场页 + AgentManagement）

**Files:** Create `frontend/src/api/marketplaceApi.ts`（list/fork，仿 harnessSkillsApi 风格）；Create `frontend/src/pages/MarketplacePage.tsx`（卡片列表 + fork 按钮 + 成功提示）；Modify `frontend/src/App.tsx`（`/marketplace` 路由 + Layout 内导航入口——若 Layout 有导航配置文件则同步加项）；Modify `frontend/src/components/Admin/AgentManagement.tsx`（visibility select（public/private/unlisted，默认 public）+ 导出按钮（下载 JSON）+ 导入按钮（file input → POST））

- [ ] Step 1 实现 → Step 2 `npx tsc --noEmit`（改动文件无错）+ `npm run build` 门控 PASS → Step 3 commit `"feat(frontend): marketplace page + agent share UI"`

### Task 5: 全量回归 + 收尾

- [ ] `pytest tests/harness -q` 全绿 → spec 状态改 `已实现（2026-08-30；...）` → commit `"docs(harness): mark P2-④ agent marketplace/share as implemented"`

## 验收标准

1. private agent 他人聊天 403；市场仅 public；fork 副本语义正确；export/import roundtrip 保留核心字段
2. 既有测试零回归；前端 build + tsc 通过
