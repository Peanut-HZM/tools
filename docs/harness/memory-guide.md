# Agent 长期记忆开发指南

> Phase 2 Plan-2 / memory_long_term BuiltinTool

## 概述

`memory_read` / `memory_write` BuiltinTool 为 Agent 提供按 `(agent_id, user_id)` 隔离的长期 KV 存储。LLM 可在多轮对话之间"记住"用户偏好、历史决策、上下文状态等结构化信息。

核心特性：

| 特性 | 说明 |
|------|------|
| **强隔离** | 每条记录都属于某个 `(agent_id, user_id)` 命名空间，跨 user / 跨 agent 不可见 |
| **Agent 级开关** | `Agent.memory_long_term_enabled=False` 时工具对 LLM 不可见 |
| **可配置上限** | `Agent.memory_long_term_config.max_entries` 控制每命名空间最大条目数（默认 100） |
| **UPSERT 语义** | 写入相同 key 自动覆盖，不重复计数 |
| **防御性输入处理** | key 自动剥离控制字符，value 校验可序列化性与大小（≤10KB） |

参考 spec：`docs/superpowers/specs/2026-08-29-agent-harness-phase2-design.md §6`。

## 架构

```
agent_memory_long_term（DB）
├── id (UUID PK)
├── agent_id (UUID FK → agents.id, ON DELETE CASCADE)
├── user_id (UUID, 无 FK)
├── key (VARCHAR 200)
├── value (JSONB, default '{}')
├── summary (TEXT, nullable)
├── created_at / updated_at (TIMESTAMP)
└── UNIQUE(agent_id, user_id, key)
    INDEX(agent_id, user_id)

                    ┌─────────────────────────────┐
   LLM tool call → │ MemoryReadTool              │
                    │  ├─ 按 key 查询（精确）      │
                    │  └─ 不传 key 列出全部        │
                    └────────────┬────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────┐
                    │ MemoryWriteTool             │
                    │  ├─ 参数校验 + 控制字符剥离   │
                    │  ├─ value JSON 序列化校验    │
                    │  ├─ UPSERT（按 agent+user+key）│
                    │  └─ 检查 max_entries（仅新建）│
                    └────────────┬────────────────┘
                                 │
                                 ▼
                       agent_memory_long_term

可用性控制：ToolContext.agent_id → Agent.memory_long_term_enabled
```

## 启用步骤

### 1. 在 Admin 后台启用

进入 **Admin → Agent 配置**，编辑目标 Agent，勾选「启用长期记忆」：

```
☑ 启用长期记忆 (memory_long_term_enabled)
memory_long_term_config: {"max_entries": 50}    # 可选，覆盖默认 100
```

### 2. 验证注册（开发期）

```python
from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tools.memory_read import MemoryReadTool
from app.services.harness.tools.memory_write import MemoryWriteTool

registry = ToolRegistry(db=db)
registry.register_builtin(MemoryReadTool())
registry.register_builtin(MemoryWriteTool())
assert "memory_read" in registry._builtin
assert "memory_write" in registry._builtin
```

注册点位于 `backend/app/api/routes/chat_stream.py`（每次新会话自动注册到 ToolRegistry）。

### 3. LLM 调用

启用后，LLM 会自动看到两个工具的 function schema：

```json
{
  "name": "memory_read",
  "description": "从当前 Agent 的长期记忆中读取条目...",
  "parameters": {
    "type": "object",
    "properties": {
      "key": {"type": "string", "maxLength": 200}
    }
  }
}

{
  "name": "memory_write",
  "description": "向当前 Agent 的长期记忆写入或更新一条记录...",
  "parameters": {
    "type": "object",
    "required": ["key", "value"],
    "properties": {
      "key": {"type": "string", "maxLength": 200},
      "value": {"type": "object"},
      "summary": {"type": "string", "maxLength": 500}
    }
  }
}
```

## 工具行为详解

### `memory_read`

| 场景 | 参数 | 返回 |
|------|------|------|
| 精确读取（存在） | `{"key": "preference.language"}` | `{key, value, summary, updated_at}` |
| 精确读取（不存在） | `{"key": "missing.key"}` | `{key: "missing.key", value: null, summary: null, updated_at: null}` |
| 列出全部 | `{}` | `{records: [...], count: N}`（按 `updated_at` 倒序） |

`records[]` 中每个元素结构：

```json
{
  "key": "preference.language",
  "value": {"preferred": "zh-CN"},
  "summary": "用户语言偏好",
  "updated_at": "2026-08-29T12:34:56+00:00"
}
```

### `memory_write`

| 场景 | 行为 | 返回 |
|------|------|------|
| 新 key + 未达上限 | INSERT | `{action: "created", key}` |
| 已存在 key | UPDATE（不计数） | `{action: "updated", key}` |
| 达 `max_entries` 上限且写新 key | 拒绝 | `{success: false, error_message: "记忆条目已达上限（X 条），..."}` |

校验顺序（短路返回首个错误）：

1. `args` 是 dict
2. `key` / `value` 必填
3. `key` 类型是 str，去空白后非空，长度 ≤200
4. 控制字符剥离（`\x00-\x1F`、`\x7F-\x9F`）
5. `value` 类型是 dict
6. `summary` 类型是 str（>500 字符静默截断到 500）
7. `value` JSON 可序列化
8. `value` 序列化后字节数 ≤10240（10KB）

## 限制与边界

| 项 | 值 | 来源 / 备注 |
|------|----|------|
| `key` 长度 | ≤200 字符 | `AgentMemoryLongTerm.key VARCHAR(200)` |
| `key` 控制字符 | 自动剥离 | 防注入 / 不可见字符污染 |
| `value` 大小 | ≤10KB（JSON 序列化后） | `_MAX_VALUE_BYTES = 10 * 1024` |
| `summary` 长度 | ≤500 字符（超长静默截断） | `_MAX_SUMMARY_LENGTH = 500` |
| 每命名空间条目数 | 默认 100，可由 `memory_long_term_config.max_entries` 调整 | `_DEFAULT_MAX_ENTRIES = 100` |
| 跨命名空间隔离 | 严格（user_id + agent_id 双维度） | SQLAlchemy filter |

并发说明：

- UPSERT 在 SQLite 测试库下通过 ORM `commit()` 实现；
- 生产 PostgreSQL 下 `(agent_id, user_id, key)` 唯一约束保证并发安全；
- max_entries 检查在事务内，理论上存在 TOCTOU 窗口（两请求并发都看到 99 条都通过检查）。
  Phase 3 可考虑改用 `INSERT ... ON CONFLICT` + 触发器或在 DB 层加 check。

## 前端渲染

`MemoryRenderer`（`frontend/src/components/Chat/ToolRenderers/MemoryRenderer.tsx`）自动渲染两种工具的调用结果：

- **顶部 badge**：显示「读取记忆」或「写入记忆」
- **memory_read 单条**：JSON `<pre>` 渲染 value，附带 summary 和更新时间
- **memory_read 列表**：显示总条数 + 前 20 条 key 列表（超过 20 条显示「还有 N 条」折叠提示）
- **memory_write**：显示 action badge（created=绿、updated=黄）和写入的 key
- **失败状态**：红色错误信息

渲染走 `ToolCallRenderer` 的 builtin 注册表，无需手动接线。

## 扩展示例

### 示例 1：让 Agent 记住用户偏好

系统提示词加入：

```
你可以通过 memory_write 工具记录用户的偏好设置（如语言、主题、常用工具）。
后续对话中通过 memory_read 主动查询，避免重复询问。
```

LLM 调用序列：

```
User:  我喜欢用深色主题
LLM  → memory_write(key="ui.theme", value={"mode": "dark"}, summary="用户偏好深色主题")
LLM  → 已为您记住深色主题偏好

User:  我现在打开编辑器
LLM  → memory_read(key="ui.theme")
LLM  → 检测到您偏好深色主题，正在打开深色编辑器
```

### 示例 2：阶段计划持久化

```python
# LLM 写入当前阶段计划
memory_write(key="task.current_step", value={"step": 3, "next": "..."})

# 下一轮
memory_read(key="task.current_step")  # 恢复上下文
```

### 示例 3：未来扩展点

Phase 3 可基于 `agent_memory_long_term` 扩展：

| 扩展 | 实现思路 |
|------|----------|
| 向量检索 | 增加 `embedding vector(1536)` 列 + pgvector 索引，提供 `memory_search` 工具 |
| TTL | 加 `expires_at TIMESTAMP`，工具读取时过滤过期条目 |
| 标签 | 现有 `value` 即可承载；如需独立索引可加 `tags TEXT[]` 列 |
| 全文搜索 | `tsvector` 列 + GIN 索引，配合 `memory_search(keyword=...)` |

## 调试技巧

### 1. 直接查看某用户的记忆条目

```python
from app.models.agent_memory import AgentMemoryLongTerm

records = db.query(AgentMemoryLongTerm).filter(
    AgentMemoryLongTerm.agent_id == "<agent-uuid>",
    AgentMemoryLongTerm.user_id == "<user-uuid>",
).order_by(AgentMemoryLongTerm.updated_at.desc()).all()

for r in records:
    print(f"{r.key}: {r.value} ({r.summary}) [{r.updated_at}]")
```

### 2. 清空某命名空间

```python
db.query(AgentMemoryLongTerm).filter(
    AgentMemoryLongTerm.agent_id == "<agent-uuid>",
    AgentMemoryLongTerm.user_id == "<user-uuid>",
).delete()
db.commit()
```

### 3. 检查某个 Agent 是否启用了 memory

```python
from app.models.agent import Agent

agent = db.query(Agent).filter(Agent.id == "<agent-uuid>").first()
print(agent.memory_long_term_enabled)
print(agent.memory_long_term_config)  # 例如 {"max_entries": 50}
```

### 4. 工具未出现在 LLM function schemas 中？

排查路径：

1. `Agent.memory_long_term_enabled` 是否为 True？
2. `backend/app/api/routes/chat_stream.py` 是否注册了 `MemoryReadTool` / `MemoryWriteTool`？
3. `ToolRegistry.to_function_schemas()` 返回的 list 中是否有 `memory_read` / `memory_write`？
4. `MemoryReadTool.is_available(ctx)` / `MemoryWriteTool.is_available(ctx)` 是否返回 True？

### 5. 写入失败排查

工具返回 `success=False` 时检查 `error_message`：

| 错误信息片段 | 原因 |
|------|------|
| `缺少必填参数 key 和 value` | args 缺字段 |
| `key 必须为字符串` / `key 不能为空` / `key 长度超过限制` | key 类型 / 长度问题 |
| `value 必须是 JSON 对象` | value 不是 dict |
| `value 无法序列化为 JSON` | value 含 set / 自定义对象等不可序列化对象 |
| `value 大小不得超过 10KB` | 序列化后超过 10240 字节 |
| `记忆条目已达上限（X 条）` | 新建条目超出 `max_entries` |

### 6. 测试用 fixture 模板

```python
import uuid
import pytest

from app.models.agent import Agent
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.memory_write import MemoryWriteTool

@pytest.fixture
def enabled_agent(test_db):
    agent = Agent(
        id=uuid.UUID("..."),
        name="TestAgent",
        description="...",
        system_prompt="sys",
        memory_long_term_enabled=True,
        memory_long_term_config={"max_entries": 10},
    )
    test_db.add(agent)
    test_db.commit()
    return agent

@pytest.fixture
def ctx(test_db, enabled_agent):
    return ToolContext(
        user_id="<user-uuid>",
        conversation_id="conv-test",
        agent_id=str(enabled_agent.id),
        db=test_db,
    )
```

## 相关文件

| 文件 | 职责 |
|------|------|
| `backend/app/models/agent_memory.py` | `AgentMemoryLongTerm` ORM |
| `backend/app/services/harness/tools/memory_read.py` | `MemoryReadTool` 实现 |
| `backend/app/services/harness/tools/memory_write.py` | `MemoryWriteTool` 实现 |
| `backend/app/api/routes/chat_stream.py` | 工具注册点 |
| `backend/app/api/routes/admin_tools.py` | admin 内置工具清单 |
| `backend/alembic/versions/20260829_agent_memory_long_term.py` | 建表 migration |
| `frontend/src/components/Chat/ToolRenderers/MemoryRenderer.tsx` | 前端渲染组件 |
| `backend/tests/harness/test_memory_integration.py` | 端到端集成测试（Task 7） |