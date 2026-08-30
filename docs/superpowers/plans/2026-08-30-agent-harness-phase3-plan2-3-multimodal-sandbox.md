# P2-③ 多模态沙箱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agent 获得工作区文件读写与受控代码执行能力（file_read / file_write / file_list / code_execute），路径限制在 per-(agent,user) 工作区内，默认关闭、admin 逐 Agent 开启。

**Architecture:** WorkspaceService 负责路径安全（resolve + is_relative_to）与读写截断；code_execute 用 `sys.executable -I` 子进程（cwd=工作区、超时 kill、输出截断）；四个 BuiltinTool 复用 `_check_procedural_enabled` 同构门控（读 `Agent.sandbox_enabled`）。

**Tech Stack:** Python 3.10（pathlib / subprocess）/ React 18 + TypeScript

## Global Constraints

- 中文注释 + 关键日志；零破坏（新列 default False，已有行为不变）
- 安全边界：单文件 1MB、输出 10KB、超时 ≤30s、file_list ≤200 条；路径逃逸一律拒绝
- 验证：`pytest tests/harness -x -q`；前端 `npm run build` + `npx tsc --noEmit`
- 每 Task 独立 commit（TDD）

---

### Task 1: Agent.sandbox_enabled 列 + migration

**Files:** Modify `backend/app/models/agent.py`（memory_procedural_enabled 后加 `sandbox_enabled = Column(Boolean, default=False)`，注释 P2-③）；Create `backend/alembic/versions/20260830c_sandbox_enabled.py`（revision `20260830c`，down_revision `20260830b`，幂等 `ALTER TABLE agents ADD COLUMN IF NOT EXISTS sandbox_enabled BOOLEAN DEFAULT FALSE`）；Modify `backend/app/api/routes/agents.py`（白名单加 `"sandbox_enabled"`、序列化加 `"sandbox_enabled": getattr(agent, "sandbox_enabled", False) or False`）；Test `test_models.py` 追加列默认值用例（参照 `test_agent_memory_procedural_enabled_default`，flush 后断言）。

- [ ] Step 1 写失败测试 → Step 2 确认 FAIL → Step 3 实现（模型+migration+白名单+序列化）→ Step 4 `pytest tests/harness/test_models.py tests/harness/test_admin_agents_api.py -q` PASS → Step 5 `git commit -m "feat(harness): agent sandbox_enabled column"`

### Task 2: WorkspaceService

**Files:** Create `backend/app/services/harness/workspace.py`；Create `backend/tests/harness/test_workspace_service.py`

**Interfaces（Produces，Task 3 依赖）:**
- `WorkspaceService(root: Path | None = None)`（root 缺省 `env WORKSPACE_ROOT` 或 `<backend>/data/agent_workspaces`）
- `workspace_dir(agent_id: str, user_id: str) -> Path`（目录不存在则 mkdir parents）
- `safe_resolve(agent_id, user_id, relative_path: str) -> Path`（join 后 resolve；逃逸抛 `PathEscapeError`）
- `read_file(agent_id, user_id, path, max_bytes=65536) -> tuple[str, bool]`（返回 (内容, 是否截断)；不存在/二进制抛 `WorkspaceFileError`）
- `write_file(agent_id, user_id, path, content, mode="overwrite") -> dict`（返回 {path, size_bytes}；>1MB 抛 `WorkspaceFileError`）
- `list_files(agent_id, user_id, path="") -> list[dict]`（rglob，返回 {path(相对), size_bytes}，上限 200）
- 异常类：`PathEscapeError(Exception)`、`WorkspaceFileError(Exception)`

**测试用例：** 逃逸拒绝（`../x`、绝对路径 `C:\Windows`、`a/../../b`）、读写 roundtrip、append、超限截断标注、1MB 拒写、list 上限与相对路径格式、自动建父目录、隔离（同 agent 不同 user 不可见）。

- [ ] Step 1 写失败测试 → Step 2 FAIL → Step 3 实现 → Step 4 PASS → Step 5 commit `"feat(harness): WorkspaceService with path sandboxing"`

### Task 3: 四个工具

**Files:** Create `backend/app/services/harness/tools/file_read.py` / `file_write.py` / `file_list.py` / `code_execute.py`（均 import `skill_save.py` 的 `_to_uuid` 模式并新建 `_check_sandbox_enabled(ctx)`，查询 `Agent.sandbox_enabled`，与 `_check_procedural_enabled` 同构）；Modify `backend/app/api/routes/chat_stream.py`（注册 4 个）；Create `backend/tests/harness/test_file_tools.py` + `test_code_execute_tool.py`

**工具要点：**
- `file_read`：`parameters: {path(必填), max_bytes(≤1MB)}`；WorkspaceService 异常→error；返回 `ToolResult.json({path, content, truncated, size_bytes})`
- `file_write`：`{path, content, mode(overwrite|append)}`；非法 mode→error；返回 `{path, size_bytes, mode}`
- `file_list`：`{path?}`；返回 `{files: [...], count}`
- `code_execute`：`{code(必填), language(仅"python"), timeout_seconds(1-30 默认15)}`；执行：

```python
        import subprocess, sys
        ws = WorkspaceService()
        workdir = ws.workspace_dir(agent_uuid_hex, user_uuid_hex)  # 用 uuid 字符串，不含路径分隔
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=str(workdir), capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout_seconds,
            )
            return ToolResult.json({
                "stdout": _truncate(proc.stdout), "stderr": _truncate(proc.stderr),
                "exit_code": proc.returncode, "timed_out": False,
            })
        except subprocess.TimeoutExpired as e:
            return ToolResult.json({
                "stdout": _truncate(e.stdout or ""), "stderr": _truncate(e.stderr or ""),
                "exit_code": None, "timed_out": True,
            })
```

- `_truncate(s)`：10KB 截断 + 尾注 `[truncated]`
- **测试用例：** file 三工具全分支（含门控 False 时 `is_available` False）；code_execute：`print("hi")` 正常、`raise SystemExit(3)` 非零退出码、`time.sleep(10)` timeout=1 超时 `timed_out=True`、代码 `open("note.txt","w").write(...)` 后工作区文件存在（cwd 生效）、stdout 超 10KB 截断、门控

- [ ] Step 1 写失败测试 → Step 2 FAIL → Step 3 实现 → Step 4 PASS → Step 5 commit `"feat(harness): file_read/write/list + code_execute sandbox tools"`

### Task 4: 前端开关

**Files:** Modify `frontend/src/services/agentApi.ts`（AgentHarnessView/Update 加 `sandbox_enabled`）；Modify `frontend/src/components/Admin/AgentManagement.tsx`（镜像 memoryProceduralEnabled：state/提交/回填/checkbox"启用代码沙箱（文件与代码执行）"）

- [ ] Step 1 实现 → Step 2 `npx tsc --noEmit`（改动文件无错）+ `npm run build` PASS → Step 3 commit `"feat(frontend): agent sandbox toggle"`

### Task 5: 全量回归 + 收尾

- [ ] `pytest tests/harness -q` 全绿 → spec 状态改 `已实现（2026-08-30；...）` → commit `"docs(harness): mark P2-③ multimodal sandbox as implemented"`

## 验收标准

1. 路径逃逸用例全部拒绝；超时/截断/门控测试通过；既有测试零回归
2. 前端 build + tsc 通过；admin 可开关 sandbox
3. migration `20260830c` 幂等
