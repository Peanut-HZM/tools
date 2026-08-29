# Agent Harness Phase 3 — Plan 1D: Checkpoint 时间旅行设计文档

**日期**：2026-08-29
**状态**：已批准（待实现）
**参考**：`docs/superpowers/specs/2026-08-28-agent-harness-design.md` §7.8、§5.7

## 1. 目标

在 Agent Harness 已有 Phase 1 轻量 Checkpoint（`SessionCheckpoint` 表 + `messages_ref` 指针）的基础上，扩展为完整的"快照 + 分支 + 合并"时间旅行能力：

- **完整状态快照**：每次 checkpoint 写入完整消息列表（`messages_snapshot` JSONB），支持任意时刻状态还原
- **多分支管理**：从任意 checkpoint 创建新分支，主分支 + 实验分支并存
- **Pick-from 合并**：用户从多个分支勾选 checkpoint 创建合并分支，避免自动合并的语义混乱
- **时间旅行 UI**：分支树 + checkpoint 列表 + 回滚/分支/合并操作

**不做的**（YAGNI）：
- ❌ 消息级自动三路合并（LLM 输出不像代码）
- ❌ 物理删除 checkpoint（detach 而非删除）
- ❌ 编辑 detached checkpoint（只读）
- ❌ Checkpoint diff 视图（LLM 输出差异无意义）

## 2. 核心决策

| 维度 | 决策 | 理由 |
|------|------|------|
| 使用场景 | 全部（快照 + 分支 + 合并） | 用户明确选择最完整方案 |
| 快照存储 | 完整快照（JSONB） | 回溯快、逻辑简单、独立查询 |
| 合并语义 | Pick-from（多父合并） | 避免自动合并冲突；用户控制 |
| 分支粒度 | Branch 是 checkpoint 的链，Branch 单独成表 | UI 能高效查询分支列表 + head 指针 |
| Session 改造 | Session 不直接写 checkpoint，由 Runtime 显式调用 CheckpointService | 单一职责、Session 瘦身 |
| 写入时机 | after_user / before_tool / after_tool（保留 Phase 1 三个时机） | 现有调用点不动，仅替换实现 |
| Detach 语义 | rollback 不物理删除，标记 `is_head=FALSE`，默认 list 过滤 | 保留完整历史、可恢复 |
| 关闭开关 | `HARNESS_CHECKPOINT_ENABLED=0` 退化为 Phase 1 行为 | 关闭无副作用 |

## 3. 架构总览

```
                  ┌────────────────────────┐
                  │   Conversation (主线)    │ ← head_checkpoint_id 指向当前分支末端
                  └────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │       Branch（分支）                  │  ← 一棵 Git-like DAG
        │  - branch_id: 同分支串联              │
        │  - parent_checkpoint_id: 父节点       │
        │  - merge_parents: 多父合并时为数组     │
        └─────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │       SessionCheckpoint              │  ← 完整快照
        │  - messages_snapshot: JSONB (全部消息) │
        │  - agent_state: JSONB                 │
        │  - checkpoint_kind: auto/manual/...   │
        │  - merge_parents: 多父合并             │
        └─────────────────────────────────────┘
```

**核心抽象**：
- **Branch** = 同一组串联 checkpoint 的有向链（DAG 中的链）
- **Checkpoint** = 一次完整状态快照（含 messages_snapshot）
- **Merge Commit** = 特殊 checkpoint，`merge_parents` 字段含 2+ 个父 checkpoint_id
- **Head** = Conversation 的"当前活跃" checkpoint

**核心操作**：
1. **写入 checkpoint**：Runtime 在 after_user_message / before_tool / after_tool 自动写入
2. **回滚**：将 head 改到某个 checkpoint，旧 head 标记 detached（不删除）
3. **分支**：从任意 checkpoint 创建新分支，新分支第一个 checkpoint 的 `parent_checkpoint_id` 指向源
4. **合并 (Pick-from)**：选 2+ 分支的 checkpoint 创建 merge commit，新分支从 merge commit 开始
5. **时间旅行**：UI 展示分支树，可点击任意 checkpoint "查看那一刻"

## 4. 数据模型

### 4.1 现有表扩展

**`conversations`** 扩展：
```sql
ALTER TABLE conversations
  ADD COLUMN head_checkpoint_id UUID NULL
    REFERENCES session_checkpoints(id) ON DELETE SET NULL,
  ADD COLUMN main_branch_id UUID NULL;
```

**`session_checkpoints`** 大改（保留 + 新增）：
```sql
ALTER TABLE session_checkpoints
  ADD COLUMN branch_id UUID NOT NULL DEFAULT gen_random_uuid(),
  ADD COLUMN parent_checkpoint_id UUID NULL
    REFERENCES session_checkpoints(id) ON DELETE SET NULL,
  ADD COLUMN messages_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN checkpoint_kind VARCHAR(20) NOT NULL DEFAULT 'auto',
  ADD COLUMN label VARCHAR(100) NULL,
  ADD COLUMN merge_parents JSONB NULL,
  ADD COLUMN is_head BOOLEAN NOT NULL DEFAULT FALSE;
```

**迁移注意**：
- 现有 checkpoint 的 `messages_snapshot` 回填：从 messages 表按 `conversation_id` + `sent_at <= checkpoint.created_at` 查询复制
- 回填脚本：单独任务（类似 `memory_backfill.py` 模式）
- 回填前 checkpoint 仍按 `messages_ref` 工作（兼容）

### 4.2 新增表

**`branches`**：
```sql
CREATE TABLE branches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  parent_branch_id UUID NULL REFERENCES branches(id),
  head_checkpoint_id UUID NULL REFERENCES session_checkpoints(id),
  is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_branches_conv ON branches(conversation_id);
```

**说明**：
- 分支表与 checkpoint 表是 1:N（一分支多 checkpoint）
- `head_checkpoint_id` 冗余到 branch 表，避免每次遍历找末端
- 主分支命名为 `"主线"`，UI 默认展开

## 5. 服务层

### 5.1 新增 `CheckpointService`

**位置**：`backend/app/services/harness/checkpoint_service.py`

**职责**：写入 checkpoint / 查询 / 回滚 / 分支 / 合并（单一职责）

### 5.2 接口签名

```python
class CheckpointService:
    def __init__(self, db: Session):
        self.db = db

    # ---- 写入 ----
    async def write_checkpoint(
        self,
        conversation_id: UUID,
        step_index: int,
        phase: str,                        # after_user_message / before_tool / after_tool
        messages: List[Message],           # 完整消息列表
        scratch_state: Dict[str, Any],
        branch_id: UUID,                   # 写入到哪个分支
        parent_checkpoint_id: Optional[UUID] = None,
        checkpoint_kind: str = "auto",
        label: Optional[str] = None,
    ) -> SessionCheckpoint:
        """写一条 checkpoint（完整快照）。"""

    # ---- 查询 ----
    async def list_branches(self, conversation_id: UUID) -> List[Branch]:
        """列出会话的所有分支（含 main + archived）。"""

    async def list_checkpoints(
        self,
        branch_id: UUID,
        include_detached: bool = False,
    ) -> List[SessionCheckpoint]:
        """列出一个分支的所有 checkpoint（DAG 顺序）。"""

    async def get_checkpoint(self, checkpoint_id: UUID) -> SessionCheckpoint:
        """获取单个 checkpoint（含 messages_snapshot）。"""

    # ---- 操作 ----
    async def rollback(
        self,
        conversation_id: UUID,
        target_checkpoint_id: UUID,
    ) -> SessionCheckpoint:
        """回滚到某个 checkpoint。"""

    async def branch_from(
        self,
        conversation_id: UUID,
        source_checkpoint_id: UUID,
        branch_name: str,
    ) -> Tuple[Branch, SessionCheckpoint]:
        """从某个 checkpoint 创建新分支。"""

    async def merge_branches(
        self,
        conversation_id: UUID,
        picked_checkpoint_ids: List[UUID],
        new_branch_name: str,
    ) -> Tuple[Branch, SessionCheckpoint]:
        """Pick-from 合并。"""
```

### 5.3 设计要点

- **不修改 Session 类**：Session 只管内存消息 + persist，由 Runtime 显式调用 CheckpointService
- **不重复存储消息内容**：`messages_snapshot` 存 Message dict（content + tool_calls + role + metadata）
- **detach 语义**：被回滚跳过的 checkpoint 不物理删除，`is_head=FALSE`，通过 `include_detached=False` 默认过滤
- **合并原子性**：merge 操作单事务，picked checkpoints 顺序按用户选择写入新分支

## 6. REST API

### 6.1 端点列表

前缀：`/api/v1/harness/conversations/{conversation_id}/`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/branches` | 列出所有分支 |
| POST | `/branches` | 创建新分支（from source checkpoint） |
| GET | `/branches/{branch_id}` | 单分支详情 |
| PATCH | `/branches/{branch_id}` | 改名 / 归档 |
| DELETE | `/branches/{branch_id}` | 删除分支（checkpoint 保留） |
| GET | `/branches/{branch_id}/checkpoints` | 列出分支 checkpoint |
| GET | `/checkpoints/{checkpoint_id}` | 单个 checkpoint（含 messages_snapshot） |
| POST | `/checkpoints` | 手动写入 checkpoint |
| POST | `/checkpoints/{checkpoint_id}/rollback` | 回滚到该 checkpoint |
| POST | `/branches/{branch_id}/merge` | Pick-from 合并 |

### 6.2 关键端点契约

**创建分支** `POST /branches`：
```json
// Request
{
  "source_checkpoint_id": "uuid",
  "name": "GPT-4 实验",
  "start_with_messages": true
}

// Response 201
{
  "branch": { "id": "uuid", "name": "...", "head_checkpoint_id": "uuid" },
  "first_checkpoint": { "id": "uuid", "parent_checkpoint_id": "uuid", ... }
}
```

**Pick-from 合并** `POST /branches/{branch_id}/merge`：
```json
// Request
{
  "picked_checkpoint_ids": ["uuid-A-1", "uuid-B-2", "uuid-A-3"],
  "new_branch_name": "合并 v1"
}

// Response 201
{
  "branch": { "id": "uuid", "name": "合并 v1" },
  "merge_commit": {
    "id": "uuid",
    "merge_parents": ["uuid-A-1", "uuid-B-2", "uuid-A-3"],
    "messages_snapshot": [...]
  }
}
```

**回滚** `POST /checkpoints/{checkpoint_id}/rollback`：
```json
// Response 200
{
  "conversation_head_checkpoint_id": "uuid",
  "detached_checkpoint_count": 3,
  "target_checkpoint": { ... }
}
```

### 6.3 鉴权与隔离

- 所有端点需登录（`get_current_user`）
- Tenancy 隔离：`WHERE user_id = current_user["id"]`
- 不暴露：直接 SQL 修改 / 修改 detached / 物理删除

## 7. Runtime 集成

### 7.1 现有调用点（保留）

Phase 1 在 3 个时机调用 `_write_checkpoint`：
- `after_user_message`
- `before_tool`
- `after_tool`

### 7.2 升级方案

**位置**：`backend/app/services/harness/agent_runtime.py`

**改造点**：
1. 把现有的 `Session.write_checkpoint()` 调用替换为 `CheckpointService.write_checkpoint()`
2. Session 类不再直接写 DB（瘦身后只管内存消息 + persist）
3. Runtime 持有当前 `branch_id`（来自 Conversation.main_branch_id）
4. 每次写入时传递完整 `messages`（来自 `session.messages`）

### 7.3 写入频率 vs 性能权衡

每个 turn 写入 3-5 个 checkpoint（1 user + N×2 tool + 1 final）。

**性能影响估算**：
- 单次 JSONB 写入 ~5KB（消息列表），PostgreSQL JSONB 写 ~1-2ms
- 单 turn 多 ~10ms 开销（5 个 checkpoint）
- **结论**：可接受，无需异步化

### 7.4 Session 类变化

**`Session.write_checkpoint()` 移除**，Session 只剩：
- `messages`（内存）
- `scratch_state`（内存）
- `persist(db)` / `apersist(db)`（DB 写入）

## 8. 前端 UI

### 8.1 新增组件

**位置**：`frontend/src/components/Harness/TimeTravel/`

```
TimeTravel/
├── TimelinePanel.tsx
├── BranchTree.tsx
├── CheckpointCard.tsx
├── BranchBadge.tsx
├── MergePickerDialog.tsx
├── RollbackConfirmDialog.tsx
├── BranchCreateDialog.tsx
└── api/
    └── checkpointsApi.ts
```

### 8.2 主面板布局

挂在 ProductManagerAgent 工具页面右侧（侧边栏）。

### 8.3 关键交互

- 点击 checkpoint 卡片 → 弹窗预览 messages_snapshot（只读）
- 「回滚到此」→ RollbackConfirmDialog
- 「从此创建分支」→ BranchCreateDialog
- 「加入合并选择」→ 加入 pickedCheckpointIds
- Detached checkpoint 预览模式 + 「回到当前 head」按钮

## 9. 配置

### 9.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HARNESS_CHECKPOINT_ENABLED` | `1` | 全局开关（`0` = 关闭所有 checkpoint 写入） |
| `HARNESS_CHECKPOINT_MAX_PER_BRANCH` | `500` | 单分支最多保留 checkpoint 数 |
| `HARNESS_CHECKPOINT_AUTO_LABEL_MAX_LEN` | `50` | 自动 checkpoint label 长度上限 |

### 9.2 默认行为

| 场景 | 行为 |
|------|------|
| 新 conversation | 自动创建 "主线" branch，写入 checkpoint |
| 每个 tool 调用 | 写 before_tool + after_tool 两个 checkpoint |
| 用户消息 | 写 after_user_message checkpoint |
| 自动 label | `step{N} {phase} {timestamp}` |
| 关闭开关 | checkpoint 表不写入，UI 显示"时间旅行功能未启用" |

## 10. 测试策略

### 10.1 单元测试（`backend/tests/harness/`）

| 模块 | 覆盖点 |
|------|--------|
| `test_checkpoint_service.py` | write / list / rollback / branch_from / merge_branches |
| `test_branch_model.py` | branch CRUD + cascade 删除 |
| `test_session_checkpoint_extended.py` | messages_snapshot 序列化 / detach 标记 |
| `test_rollback.py` | head 更新 + is_head 切换 |
| `test_branch_from.py` | parent_checkpoint_id 指向 + messages 复制 |
| `test_merge.py` | merge_parents 数组 + 多父 messages 拼接 |
| `test_detach_isolation.py` | 默认不包含 / include_detached=True 时包含 |

### 10.2 集成测试

| 测试 | 覆盖 |
|------|------|
| `test_runtime_writes_checkpoints.py` | Runtime 完整 turn 的 checkpoint 写入时机和数量 |
| `test_api_checkpoints.py` | REST API 端点 + 鉴权 + 租户隔离 |
| `test_backfill.py` | 旧 checkpoint 的 messages_snapshot 回填 |

### 10.3 前端测试（`frontend/src/components/Harness/TimeTravel/__tests__/`）

| 测试 | 覆盖 |
|------|------|
| `TimelinePanel.test.tsx` | 分支列表 + checkpoint 卡片渲染 |
| `BranchTree.test.tsx` | 分支树渲染 + 点击 |
| `RollbackConfirmDialog.test.tsx` | 确认 / 取消 |
| `MergePickerDialog.test.tsx` | checkbox 勾选 + 校验 |
| `BranchCreateDialog.test.tsx` | 表单校验 |
| `checkpointsApi.test.ts` | API 封装 |

### 10.4 端到端测试

- 跑一个 5-turn agent 对话 → 时间旅行面板显示完整 checkpoint
- 回滚 step 5 → step 3 → 后续 turn 从 step 3 继续
- 分支：从 step 3 创建 "实验" → 新分支独立运行
- 合并：选主线 step 3 + 实验 step 5 → 创建合并分支

## 11. 迁移与回填

### 11.1 Alembic 迁移

任务 T1 包含：
- conversations 表 ALTER
- session_checkpoints 表 ALTER
- branches 表 CREATE
- 索引创建

### 11.2 回填脚本

独立 Python 脚本（类似 `memory_backfill.py`）：
- 遍历 session_checkpoints 中 messages_snapshot 为空的旧记录
- 从 messages 表按 conversation_id + sent_at 顺序查询，组装 messages_snapshot
- 单事务批量更新 + 进度日志

### 11.3 兼容期

- 旧 checkpoint 回填前仍按 messages_ref 工作
- 回填完成后新写入走完整快照
- 回填脚本幂等，可重复运行

## 12. 实施任务拆分（预估 7 个）

| 任务 | 内容 | 工作量 |
|------|------|--------|
| T1 | 数据模型 + Alembic 迁移 + 回填脚本 | 1-2 天 |
| T2 | CheckpointService + 单元测试 | 1-2 天 |
| T3 | Runtime 集成 + 集成测试 | 1 天 |
| T4 | REST API + 测试 | 1-2 天 |
| T5 | 前端 API 封装 + 类型 | 0.5 天 |
| T6 | 前端 UI 组件 + 测试 | 2-3 天 |
| T7 | 端到端验证 + 文档 | 1 天 |

## 13. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 存储增长（完整快照 O(N×M)） | 中 | 单分支限额 500，超出自动 detach 旧 auto checkpoint |
| 迁移风险（messages_snapshot 回填失败） | 高 | 回填脚本幂等 + 进度日志 + 失败可重试 + 回填前兼容 messages_ref |
| Runtime 性能（每 turn 多 ~10ms） | 低 | 当前规模可接受；后续如需可批量 checkpoint |
| UI 复杂度（分支树 + 合并选择器） | 中 | 复用 GitGraph 组件库（如 react-flow）简化开发 |
| Session 改造影响其他模块 | 低 | Session 仅移除 write_checkpoint，其他 API 不变 |
