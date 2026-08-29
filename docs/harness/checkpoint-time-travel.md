# Checkpoint 时间旅行

> Phase 3-Plan-1D

Checkpoint 时间旅行让 ProductManagerAgent 的多轮对话像 git 一样可回溯、可分支、可合并。每轮 LLM 交互完成后，Agent Runtime 自动写入一个完整快照（checkpoint），并组成一条默认主线（branch）。用户可以在时间旅行面板查看历史、回滚任意一步、从任一历史点创建分支、或跨分支 Pick-from 合并。

参考 spec：`docs/superpowers/specs/2026-08-29-agent-harness-phase3-plan1d-checkpoint-time-travel-design.md §6`。

## 概念

| 术语 | 说明 |
|------|------|
| **Checkpoint** | 单次状态快照。包含完整 `messages_snapshot`（到该步为止的全部消息）、`agent_state`（scratch_state）、`step_index` / `phase` / `checkpoint_kind` 等元数据。 |
| **Branch** | 分支。一组按 `created_at` 串联的 checkpoint，每个 checkpoint 标记 `is_head` 指向当前活跃 head。每个 conversation 至少有一条「主线」（由 runtime 自动创建）。 |
| **Rollback** | 回滚。将 `conversation.head_checkpoint_id` 改到某个 checkpoint，旧 head 标记为 `is_head=False`（**detached**，但物理数据保留）。之后继续产生的 checkpoint 仍挂在新 head 所在的分支下。 |
| **Branch from** | 创建分支。从某个 checkpoint 复制其 `messages_snapshot` / `agent_state` 作为新分支的起点。新分支的 `parent_branch_id` 当前不记录（已知限制）。 |
| **Merge** | Pick-from 合并。用户从多个分支勾选 checkpoint，service 按勾选顺序拼接 `messages_snapshot`（按 `msg.id` 去重，保留最后出现），创建新分支 + merge commit（`checkpoint_kind="merge_commit"`，`merge_parents` 字段记录所有被合并的 checkpoint id）。 |

## 启用 / 配置

### 数据库迁移（首次部署）

迁移文件：`backend/alembic/versions/20260829c_checkpoint_time_travel.py`

```bash
# 在 PostgreSQL 上运行迁移（链 head: 20260829c）
cd backend
python -m alembic upgrade 20260829c

# 回填历史 checkpoint 的完整 messages 快照（best-effort）
python -m scripts.backfill_checkpoint_snapshots
```

迁移内容：

- `conversations` 表新增 `head_checkpoint_id` (FK → session_checkpoints) 和 `main_branch_id` (FK → branches, ON DELETE SET NULL)
- `session_checkpoints` 表新增 `branch_id` (FK → branches) / `parent_checkpoint_id` / `checkpoint_kind` / `label` / `merge_parents` / `is_head`，`messages_snapshot` 改为 JSONB 完整快照
- 新增 `branches` 表（id / conversation_id / name / parent_branch_id / head_checkpoint_id / is_archived / created_at / closed_at）
- 幂等 FK 约束 + 自动回填：每个 conversation 创「主线」branch；孤儿 checkpoint 指回主线

### 计划中的环境变量（尚未强制生效）

以下 env vars 已在 `backend/.env.example` 标注但**当前 P1D 版本不强制读取**（CheckpointService / Runtime 始终开启写入）。引入后用于运维开关：

| 环境变量 | 默认 | 说明 |
|---------|------|------|
| `HARNESS_CHECKPOINT_ENABLED` | `1` | 全局开关。设为 `0` 时 runtime 不写 checkpoint（**planned**，未实施） |
| `HARNESS_CHECKPOINT_MAX_PER_BRANCH` | `500` | 单分支 checkpoint 数量上限，超限触发 LRU 截断（**planned**，未实施） |

当前行为：所有 ProductManagerAgent 对话自动写入 checkpoint（best-effort，写入失败不中断主循环）。

## 使用场景

### 1. 查看时间旅行面板

在 ProductManagerAgent 对话页面，点击右上「时间旅行」按钮（Clock 图标）打开 TimelinePanel：

- 左列：分支树（主线高亮，archived 半透明）
- 右列：当前分支的 checkpoint 时间线（HEAD 标记）
- 底部操作按钮：回滚 / 创建分支 / Pick-from 合并

### 2. 回滚到某步

1. 在时间旅行面板点击目标 checkpoint 卡片
2. 点击「回滚到此」按钮
3. 在二次确认弹窗勾选确认 → 确认提交
4. 服务端将 `conversation.head_checkpoint_id` 改到该 checkpoint，旧 head 标记 `is_head=False`（detached）
5. 后续 LLM 交互继续在新 head 所在的分支下追加

**注意**：rollback 不物理删除任何 checkpoint 数据，detached 的 checkpoint 通过 `include_detached=true` 查询参数可见。

### 3. 从 checkpoint 创建分支

1. 点击源 checkpoint 卡片
2. 点击「从此创建分支」按钮
3. 输入分支名（1-100 字符）+ 选择是否复制 messages（默认是）
4. 服务端创建新 Branch（`parent_branch_id=null`）+ 首个 `branch_point` checkpoint，复制 source 的 `messages_snapshot` / `agent_state`

### 4. Pick-from 合并

1. 在多个分支分别打开（**当前 UI 限制**：仅展示 active branch 的 checkpoint，需手动切换分支——见已知限制）
2. 点击 checkpoint 卡片上的「加入合并选择」
3. 点击「合并」打开合并对话框
4. 在弹窗内**至少勾选 2 个** checkpoint + 输入新分支名
5. 提交后服务端按勾选顺序拼接 `messages_snapshot`（按 `msg.id` 去重），创建新分支 + `merge_commit` checkpoint

## 数据流（写入时机）

`AgentRuntime._write_checkpoint(phase)` 在三个时机 best-effort 写入：

| 时机 | phase | 用途 |
|------|-------|------|
| `after_user_message` | `user_message` | 锁定用户输入之后的快照起点 |
| `before_tool` | `before_tool` | 工具调用前的完整消息列表（重放起点） |
| `after_tool` | `after_tool` | 工具结果追加后的状态 |

写入流程：

```
session.append_*  →  runtime._write_checkpoint(phase)
                  →  CheckpointService.write_checkpoint(...)
                  →  SessionCheckpoint(messages_snapshot=[...], agent_state={...}, ...)
                  →  db.commit()  (异常被吞掉不中断主循环)
```

`_ensure_main_branch()` 懒加载创建「主线」Branch，回写到 `conversation.main_branch_id`。

## API 速查

所有 checkpoint 端点位于 `/api/v1/harness/conversations/{conversation_id}` 前缀下。**所有端点强制 JWT 鉴权 + 租户隔离**（user 只能访问自己的 conversation；branch / checkpoint 归属校验防 IDOR）。

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/branches` | 列出会话的所有分支（含 archived） |
| `POST` | `/branches` | 从某个 checkpoint 创建新分支 |
| `GET` | `/branches/{branch_id}` | 获取分支详情 |
| `PATCH` | `/branches/{branch_id}` | 改名 / 归档分支（body 模型 `UpdateBranchRequest`） |
| `DELETE` | `/branches/{branch_id}` | 删除分支（checkpoint 物理保留） |
| `GET` | `/branches/{branch_id}/checkpoints` | 列出分支 checkpoint（query `include_detached` 控制是否含 detached） |
| `GET` | `/checkpoints/{checkpoint_id}` | 获取单个 checkpoint 完整快照 |
| `POST` | `/checkpoints` | 手动写入 checkpoint（body 模型 `WriteCheckpointRequest`，懒加载创建主分支） |
| `POST` | `/checkpoints/{checkpoint_id}/rollback` | 回滚到该 checkpoint |
| `POST` | `/branches/{branch_id}/merge` | Pick-from 合并（body 模型 `MergeRequest`，至少 2 个 checkpoint） |

### 关键端点入参 / 出参形状

**`POST /branches`** — 创建分支

请求 body：

```json
{
  "source_checkpoint_id": "uuid",
  "name": "实验分支",
  "start_with_messages": true
}
```

响应（201）：

```json
{
  "branch": {
    "id": "uuid",
    "conversation_id": "uuid",
    "name": "实验分支",
    "parent_branch_id": null,
    "head_checkpoint_id": "uuid",
    "is_archived": false,
    "created_at": "2026-08-29T12:34:56+00:00",
    "closed_at": null
  },
  "first_checkpoint": { ... CheckpointResponse ... }
}
```

**`POST /checkpoints`** — 手动写入

请求 body：

```json
{
  "step_index": 5,
  "phase": "manual",
  "messages": [ { "id": "msg-1", "sender_type": "user", "role": "user", "content": "..." } ],
  "scratch_state": { "key": "value" },
  "label": "可选 label"
}
```

字段限制：`messages` 数量 ≤200（Pydantic Field），单条 `content` ≤32000 字符，`scratch_state` 序列化字节 ≤65536。超限分别返回 422 / 400。

**`POST /checkpoints/{id}/rollback`** — 回滚

响应（200）：

```json
{
  "conversation_head_checkpoint_id": "uuid",
  "detached_checkpoint_count": 2,
  "target_checkpoint": { ... CheckpointResponse ... }
}
```

**`POST /branches/{branch_id}/merge`** — 合并

请求 body：

```json
{
  "picked_checkpoint_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "new_branch_name": "合并结果"
}
```

响应（201）：

```json
{
  "branch": { ... BranchResponse ... },
  "merge_commit": { ... CheckpointResponse ..., "merge_parents": ["uuid-1", "uuid-2", "uuid-3"] }
}
```

错误响应：

- `400` — 业务错误（如 rollback 目标不属于该 conv、merge 不足 2 个 checkpoint）
- `404` — 资源不存在或不属于当前 user（**不泄漏存在性**，统一返回"会话不存在" / "分支不存在" / "checkpoint 不存在"）
- `422` — Pydantic 校验失败（messages 数量超限 / content 超长等）

## 调试技巧

### 1. 直接查看某 conversation 的所有 checkpoint

```python
from app.models.harness_models import SessionCheckpoint

cps = db.query(SessionCheckpoint).filter(
    SessionCheckpoint.conversation_id == "<conv-uuid>",
).order_by(SessionCheckpoint.created_at).all()

for cp in cps:
    head = " [HEAD]" if cp.is_head else (" (detached)" if not cp.is_head else "")
    print(f"step={cp.step_index} phase={cp.phase} kind={cp.checkpoint_kind}{head}")
```

### 2. 手动触发回滚

```python
from app.services.harness.checkpoint_service import CheckpointService

cs = CheckpointService(db)
target, detached_n = cs.rollback(
    conversation_id="<conv-uuid>",
    target_checkpoint_id="<cp-uuid>",
)
print(f"回滚到 {target.id}, detached {detached_n} 个 checkpoint")
```

### 3. 查找 detached checkpoint

```python
from app.models.harness_models import SessionCheckpoint

detached = db.query(SessionCheckpoint).filter(
    SessionCheckpoint.branch_id == "<branch-uuid>",
    SessionCheckpoint.is_head.is_(False),
).all()
```

或在 API：`GET /branches/{id}/checkpoints?include_detached=true`

### 4. 通过 REST API 在外部触发（Postman / curl）

```bash
# 列分支
curl -H "Authorization: Bearer <jwt>" \
  http://localhost:19092/api/v1/harness/conversations/<conv-id>/branches

# 回滚
curl -X POST -H "Authorization: Bearer <jwt>" \
  http://localhost:19092/api/v1/harness/conversations/<conv-id>/checkpoints/<cp-id>/rollback
```

### 5. 面板打不开 / checkpoint 不出现？

排查路径：

1. 该 conversation 是否为 ProductManagerAgent 的？（Checkpoint 写入只在 harness Runtime 中触发）
2. `Conversation.main_branch_id` 是否为非 null？（首次 checkpoint 写入时懒加载创建）
3. `SessionCheckpoint.branch_id` 是否指回主线 branch？（迁移后跑过 `backfill_checkpoint_snapshots` 吗？）
4. 前端 `TimelinePanel` 是否传入 `conversationId`？（`ProductManagerAgent.tsx` 中 `showTimeTravelPanel && conversationId` 双重门控）

## 已知限制

| 项 | 状态 | 说明 |
|----|------|------|
| `HARNESS_CHECKPOINT_ENABLED` / `HARNESS_CHECKPOINT_MAX_PER_BRANCH` 环境变量 | **未实施** | 当前 CheckpointService / Runtime 始终开启写入，无 env 读取。计划在 follow-up PR 引入。 |
| 跨分支合并 UI 体验 | **已知** | `MergePickerDialog` 当前仅展示 active branch 的 checkpoint，需手动切换分支选择。 |
| `merge_branches` 忽略 path `branch_id` | **已知** | merge 走 `conversation_id + picked_checkpoint_ids`，URL 中的 `branch_id` 仅占位，无业务影响。 |
| `_get_service` dead code | **parked** | `backend/app/api/routes/harness_checkpoints.py` 顶部定义的 helper 未被任何路由使用。 |
| `update_branch` / `write_checkpoint_manual` 路由层 `db.commit()` | **parked** | 应下沉到 service 层；目前 ORM 提交散落在 routes。 |
| `write_checkpoint_manual` 懒加载创建主分支在 route 层 | **parked** | 应下沉到 `CheckpointService`。 |
| `datetime.utcnow()` deprecated 使用 | **parked** | `update_branch` 关闭时用 `datetime.utcnow()`，Python 3.12+ 标记 deprecated，不影响功能。 |
| `ConfigDict(from_attributes=True)` 未使用 | **parked** | schemas 中声明但实际用 `_format_xxx` 手工序列化。 |
| `MergePickerDialog` 错误提示 | **已知** | onConfirm 抛错时仅复位 loading，无 toast 提示。 |
| `backend/app/database.py` 兼容 shim | **parked** | brief 测试要求 `from app.database import engine`，新增 3 行 shim。理想长期让 brief 测试统一 import `app.models.base`。 |
| 迁移测试需要 PostgreSQL | **环境限制** | `tests/alembic/test_checkpoint_migration.py` 在 SQLite 默认 DB 下失败（缺 PG 列）；需在 PG 上验证。 |

## 相关文件

| 文件 | 职责 |
|------|------|
| `backend/app/models/harness_models.py` | `Branch` / `SessionCheckpoint` ORM（含完整快照字段） |
| `backend/app/models/conversation.py` | `Conversation.head_checkpoint_id` / `main_branch_id` |
| `backend/app/services/harness/checkpoint_service.py` | CheckpointService（write / list / rollback / branch_from / merge_branches） |
| `backend/app/services/harness/agent_runtime.py` | Runtime 集成（`_write_checkpoint` × 3 时机 + `_ensure_main_branch`） |
| `backend/app/api/routes/harness_checkpoints.py` | 10 个 REST 端点（含鉴权 + 租户隔离） |
| `backend/app/api/schemas/harness_checkpoint.py` | Pydantic schemas（请求/响应/嵌套消息） |
| `backend/alembic/versions/20260829c_checkpoint_time_travel.py` | 建表 + FK + 回填迁移 |
| `backend/scripts/backfill_checkpoint_snapshots.py` | 历史 checkpoint 快照回填 CLI |
| `backend/app/main.py` | harness_checkpoints_router 注册 |
| `frontend/src/api/harnessCheckpointsApi.ts` | 10 个 API 封装函数 |
| `frontend/src/types/harnessCheckpoint.ts` | TypeScript 类型定义 |
| `frontend/src/components/Harness/TimeTravel/` | UI 组件（TimelinePanel / CheckpointCard / BranchTree / 3 个 Dialog） |
| `frontend/src/components/Tools/ProductManagerAgent.tsx` | TimelinePanel 集成入口 |
| `backend/tests/harness/test_checkpoint_service.py` | Service 单元测试 |
| `backend/tests/harness/test_runtime_checkpoints.py` | Runtime 集成测试 |
| `backend/tests/harness/test_api_checkpoints.py` | REST API + 鉴权 + 租户隔离测试 |