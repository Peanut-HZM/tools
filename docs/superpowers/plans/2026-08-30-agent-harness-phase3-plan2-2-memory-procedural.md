# P2-② Memory procedural（Agent 技能系统）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Agent 增加程序性记忆（命名技能）：LLM 可沉淀/读取/删除技能，system prompt 注入技能索引（渐进披露），用户可通过 REST API 与前端管理。

**Architecture:** 新表 `agent_procedural_memory`（(agent_id, user_id, name) 唯一）+ `SkillService` CRUD + 3 个 BuiltinTool（`agent.memory_procedural_enabled` 门控）+ runtime 注入 `<procedural_memory>` 索引块 + REST API + 前端 SkillsViewer。无向量检索（索引直接进 prompt）。

**Tech Stack:** Python 3.10 / FastAPI / SQLAlchemy + Alembic / React 18 + TypeScript

## Global Constraints

- 所有代码注释使用中文；关键节点有日志（AGENTS.md）
- 零破坏：新列有默认值；已有 memory 行为不变；`is_available` 查询失败保守返回 False
- (agent_id, user_id) 严格隔离；未授权 REST 返回 401（沿用 harness_memories 模式）
- 验证命令：`cd backend && .venv/Scripts/python -m pytest tests/harness -x -q`；前端 `npm run build` + `npx tsc --noEmit`
- 每 Task 独立 commit（TDD）

---

### Task 1: ORM 模型 + Agent 列 + migration

**Files:**
- Create: `backend/app/models/agent_procedural_memory.py`
- Modify: `backend/app/models/agent.py`（memory_long_term_enabled 旁加 1 列）
- Create: `backend/alembic/versions/20260830b_memory_procedural.py`
- Test: `backend/tests/harness/test_models.py`（追加）

**Interfaces:**
- Produces: `AgentProceduralMemory`（字段见 spec §2.2；`UniqueConstraint("agent_id","user_id","name", name="uq_procedural_agent_user_name")`）；`Agent.memory_procedural_enabled: Boolean default False`；migration `20260830b`（down_revision `"20260830a"`）

- [ ] **Step 1: 写失败测试**

`test_models.py` 末尾追加：

```python
def test_agent_procedural_memory_model():
    """P2-②: agent_procedural_memory 表应可存取技能记录"""
    from app.models.agent_procedural_memory import AgentProceduralMemory

    skill = AgentProceduralMemory(
        agent_id=_uuid.UUID("00000000-0000-0000-0000-000000000002"),
        user_id=_uuid.UUID("00000000-0000-0000-0000-000000000003"),
        name="deploy_check",
        trigger="用户要求部署前检查",
        content="1. 跑测试 2. 检查环境变量",
    )
    assert skill.importance == 0.5
    assert skill.use_count == 0
    assert skill.is_enabled is True
    test_db.add(skill)
    test_db.commit()
    loaded = test_db.query(AgentProceduralMemory).filter_by(name="deploy_check").first()
    assert loaded is not None
    assert loaded.trigger == "用户要求部署前检查"


def test_agent_memory_procedural_enabled_default():
    """P2-②: Agent.memory_procedural_enabled 默认 False"""
    from app.models.agent import Agent

    agent = Agent(id=_uuid.uuid4(), name="a", slug=f"a-{_uuid.uuid4().hex[:8]}", created_by="u")
    assert bool(getattr(agent, "memory_procedural_enabled", False)) is False
```

注意：以文件内既有的 import/fixture 风格为准（`test_db` fixture、`_uuid` 别名若不存在则 `import uuid as _uuid`）。

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_models.py -k procedural -v`
Expected: FAIL（ModuleNotFoundError / AttributeError）

- [ ] **Step 3: 创建模型**

新建 `backend/app/models/agent_procedural_memory.py`：

```python
"""Agent 程序性记忆（技能）ORM 模型

P2-② Memory procedural
技能 = Agent 沉淀的命名操作流程（怎么做事），区别于长期记忆的事实 KV。
(agent_id, user_id, name) 唯一。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime,
    ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class AgentProceduralMemory(Base):
    """Agent 程序性记忆（技能）"""

    __tablename__ = "agent_procedural_memory"
    __table_args__ = (
        UniqueConstraint("agent_id", "user_id", "name", name="uq_procedural_agent_user_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    # user_id 暂不加 FK：与 agent_memory_long_term 同构（users.id 类型不匹配）
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    trigger = Column(Text, nullable=False)   # 何时使用（进索引供 LLM 判断）
    content = Column(Text, nullable=False)   # 完整步骤/规则（skill_read 返回）
    importance = Column(Float, nullable=False, default=0.5, server_default="0.5")
    use_count = Column(Integer, nullable=False, default=0, server_default="0")
    is_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self):
        return f"<AgentProceduralMemory {self.name} agent={self.agent_id}>"
```

`backend/app/models/agent.py` 在 `memory_long_term_config` 后加：

```python
    # P2-②: 程序性记忆（技能系统）开关
    memory_procedural_enabled = Column(Boolean, default=False)
```

- [ ] **Step 4: 创建 migration**

新建 `backend/alembic/versions/20260830b_memory_procedural.py`（幂等 SQL 模式）：

```python
"""P2-② Memory procedural — agent_procedural_memory 表 + agents 新列

迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260830b"
down_revision = "20260830a"  # 接 P2-①c command_json 迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_procedural_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            name VARCHAR(100) NOT NULL,
            trigger TEXT NOT NULL,
            content TEXT NOT NULL,
            importance FLOAT NOT NULL DEFAULT 0.5,
            use_count INTEGER NOT NULL DEFAULT 0,
            is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_procedural_agent_user_name UNIQUE (agent_id, user_id, name)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_procedural_agent_user ON agent_procedural_memory (agent_id, user_id)")
    op.execute(
        """
        ALTER TABLE agents
        ADD COLUMN IF NOT EXISTS memory_procedural_enabled BOOLEAN DEFAULT FALSE
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS agent_procedural_memory")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS memory_procedural_enabled")
```

- [ ] **Step 5: 测试通过 + Commit**

Run: `cd backend && .venv/Scripts/python -m pytest tests/harness/test_models.py -q` → PASS

```bash
git add backend/app/models/agent_procedural_memory.py backend/app/models/agent.py backend/alembic/versions/20260830b_memory_procedural.py backend/tests/harness/test_models.py
git commit -m "feat(harness): agent procedural memory model + agent toggle column"
```

---

### Task 2: SkillService

**Files:**
- Create: `backend/app/services/harness/skill_service.py`
- Create: `backend/tests/harness/test_skill_service.py`

**Interfaces:**
- Produces:
  - `SkillService(db)`；全部方法 agent_id/user_id 为 `uuid.UUID`
  - `async save(agent_id, user_id, name, trigger, content, importance=0.5) -> AgentProceduralMemory`（UPSERT by name，use_count 保留）
  - `async get(agent_id, user_id, name) -> AgentProceduralMemory | None`
  - `async list_enabled(agent_id, user_id) -> list[AgentProceduralMemory]`（按 updated_at desc，上限 20）
  - `async list_all(agent_id, user_id) -> list[AgentProceduralMemory]`（含禁用，管理用）
  - `async delete(agent_id, user_id, name) -> bool`
  - `async increment_use_count(agent_id, user_id, name) -> None`（best-effort，异常只记日志）

- [ ] **Step 1: 写失败测试**

```python
"""SkillService 单元测试（P2-②）"""
import uuid

import pytest

from app.services.harness.skill_service import SkillService

AID = uuid.UUID("00000000-0000-0000-0000-000000000002")
UID = uuid.UUID("00000000-0000-0000-0000-000000000003")
UID2 = uuid.UUID("00000000-0000-0000-0000-000000000004")


@pytest.mark.asyncio
async def test_save_creates(test_db):
    svc = SkillService(test_db)
    s = await svc.save(AID, UID, "s1", "触发条件", "步骤")
    assert s.name == "s1"
    assert s.use_count == 0


@pytest.mark.asyncio
async def test_save_upsert_preserves_use_count(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "s1", "旧触发", "旧内容")
    await svc.increment_use_count(AID, UID, "s1")
    await svc.save(AID, UID, "s1", "新触发", "新内容", importance=0.9)
    s = await svc.get(AID, UID, "s1")
    assert s.trigger == "新触发"
    assert s.importance == 0.9
    assert s.use_count == 1  # UPSERT 保留使用计数


@pytest.mark.asyncio
async def test_isolation_by_agent_and_user(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "s1", "t", "c")
    assert await svc.get(AID, UID2, "s1") is None
    assert await svc.delete(AID, UID2, "s1") is False


@pytest.mark.asyncio
async def test_list_enabled_filters_disabled(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "on", "t", "c")
    off = await svc.save(AID, UID, "off", "t", "c")
    off.is_enabled = False
    test_db.commit()
    names = [s.name for s in await svc.list_enabled(AID, UID)]
    assert names == ["on"]


@pytest.mark.asyncio
async def test_list_enabled_cap_20(test_db):
    svc = SkillService(test_db)
    for i in range(25):
        await svc.save(AID, UID, f"s{i}", "t", "c")
    assert len(await svc.list_enabled(AID, UID)) == 20
    assert len(await svc.list_all(AID, UID)) == 25


@pytest.mark.asyncio
async def test_delete(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "s1", "t", "c")
    assert await svc.delete(AID, UID, "s1") is True
    assert await svc.get(AID, UID, "s1") is None
```

- [ ] **Step 2: 确认失败** → `pytest tests/harness/test_skill_service.py -v`（ModuleNotFoundError）

- [ ] **Step 3: 实现 SkillService**

```python
"""SkillService — 程序性记忆（技能）CRUD

P2-② Memory procedural
无向量检索：技能索引直接注入 system prompt（见 spec §3.1）。
"""
import logging
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

# 索引注入上限（spec §3.4：超过按 updated_at 截断）
_MAX_INDEX_SIZE = 20


class SkillService:
    """技能服务：save/get/list/delete + 使用计数"""

    def __init__(self, db: DBSession):
        self._db = db

    async def save(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        trigger: str,
        content: str,
        importance: float = 0.5,
    ):
        """按 name UPSERT 技能（use_count 保留）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory

        row = (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
                AgentProceduralMemory.name == name,
            )
            .first()
        )
        if row:
            row.trigger = trigger
            row.content = content
            row.importance = importance
        else:
            row = AgentProceduralMemory(
                agent_id=agent_id,
                user_id=user_id,
                name=name,
                trigger=trigger,
                content=content,
                importance=importance,
            )
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    async def get(self, agent_id, user_id, name: str):
        from app.models.agent_procedural_memory import AgentProceduralMemory
        return (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
                AgentProceduralMemory.name == name,
            )
            .first()
        )

    async def list_enabled(self, agent_id, user_id) -> List:
        """启用技能（updated_at 倒序，上限 _MAX_INDEX_SIZE）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory
        return (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
                AgentProceduralMemory.is_enabled == True,  # noqa: E712
            )
            .order_by(AgentProceduralMemory.updated_at.desc())
            .limit(_MAX_INDEX_SIZE)
            .all()
        )

    async def list_all(self, agent_id, user_id) -> List:
        """全部技能（含禁用，管理用）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory
        return (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
            )
            .order_by(AgentProceduralMemory.updated_at.desc())
            .all()
        )

    async def delete(self, agent_id, user_id, name: str) -> bool:
        row = await self.get(agent_id, user_id, name)
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    async def increment_use_count(self, agent_id, user_id, name: str) -> None:
        """读即计数（best-effort，失败不阻塞对话）"""
        try:
            row = await self.get(agent_id, user_id, name)
            if row:
                row.use_count = (row.use_count or 0) + 1
                self._db.commit()
        except Exception as e:
            logger.warning("increment_use_count 失败: %s", type(e).__name__)
```

- [ ] **Step 4: 测试通过 + Commit**

```bash
git add backend/app/services/harness/skill_service.py backend/tests/harness/test_skill_service.py
git commit -m "feat(harness): SkillService CRUD with upsert and use counting"
```

---

### Task 3: 三个技能工具

**Files:**
- Create: `backend/app/services/harness/tools/skill_save.py`
- Create: `backend/app/services/harness/tools/skill_read.py`
- Create: `backend/app/services/harness/tools/skill_delete.py`
- Modify: `backend/app/api/routes/chat_stream.py`（注册 3 行）
- Test: `backend/tests/harness/test_skill_tools.py`

**Interfaces:**
- Consumes: Task 2 `SkillService`；`BuiltinTool` 基类（`app/services/harness/tools/base.py`，参照 `memory_read.py` 的 `_to_uuid`/`is_available` 模式）
- Produces: `SkillSaveTool` / `SkillReadTool` / `SkillDeleteTool`（name 分别为 `skill_save` / `skill_read` / `skill_delete`；`is_available` 读 `agent.memory_procedural_enabled`）

- [ ] **Step 1: 写失败测试**

```python
"""技能工具单元测试（P2-②）"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.services.harness.skill_service import SkillService
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.skill_delete import SkillDeleteTool
from app.services.harness.tools.skill_read import SkillReadTool
from app.services.harness.tools.skill_save import SkillSaveTool

AID = uuid.UUID("00000000-0000-0000-0000-000000000002")
UID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def _ctx(db, procedural_enabled=True):
    """构造 ToolContext + mock agent（门控字段）"""
    ctx = ToolContext(
        user_id=str(UID),
        conversation_id="c1",
        agent_id=str(AID),
        session=None,
        db=db,
        oss_service=None,
        llm_gateway=None,
        event_emitter=None,
        quota_service=None,
        trace_recorder=None,
        cancel_event=None,
    )
    agent = MagicMock()
    agent.memory_procedural_enabled = procedural_enabled
    # is_available 通过 ctx 不可达 agent，走 db 查询；这里直接 monkeypatch 查询
    return ctx, agent


@pytest.mark.asyncio
async def test_skill_save_and_read_roundtrip(test_db, monkeypatch):
    monkeypatch.setattr(
        SkillSaveTool, "is_available", lambda self, ctx: True, raising=False
    )
    monkeypatch.setattr(
        SkillReadTool, "is_available", lambda self, ctx: True, raising=False
    )
    save = SkillSaveTool()
    read = SkillReadTool()
    ctx, _ = _ctx(test_db)

    r = await save.execute(
        {"name": "deploy", "trigger": "部署前", "content": "1. 测试"},
        ctx,
    )
    assert r.success is True

    r2 = await read.execute({"name": "deploy"}, ctx)
    assert r2.success is True
    assert "1. 测试" in str(r2.content)


@pytest.mark.asyncio
async def test_skill_read_index_and_use_count(test_db, monkeypatch):
    monkeypatch.setattr(SkillSaveTool, "is_available", lambda self, ctx: True, raising=False)
    monkeypatch.setattr(SkillReadTool, "is_available", lambda self, ctx: True, raising=False)
    ctx, _ = _ctx(test_db)
    await SkillSaveTool().execute(
        {"name": "s", "trigger": "t", "content": "c"}, ctx
    )
    read = SkillReadTool()
    idx = await read.execute({}, ctx)
    assert idx.success is True
    assert idx.content["records"][0]["name"] == "s"
    # 读完整内容 → use_count 递增
    await read.execute({"name": "s"}, ctx)
    svc = SkillService(test_db)
    row = await svc.get(AID, UID, "s")
    assert row.use_count == 1


@pytest.mark.asyncio
async def test_skill_delete_missing(test_db, monkeypatch):
    monkeypatch.setattr(SkillDeleteTool, "is_available", lambda self, ctx: True, raising=False)
    ctx, _ = _ctx(test_db)
    r = await SkillDeleteTool().execute({"name": "nope"}, ctx)
    assert r.success is False


@pytest.mark.asyncio
async def test_skill_save_requires_name(test_db, monkeypatch):
    monkeypatch.setattr(SkillSaveTool, "is_available", lambda self, ctx: True, raising=False)
    ctx, _ = _ctx(test_db)
    r = await SkillSaveTool().execute({"trigger": "t", "content": "c"}, ctx)
    assert r.success is False
```

注意：`ToolContext` 构造参数以 `tool_protocol.py` 实际签名为准（先读该文件再定）；门控测试（未启用不可用）仿照 `test_memory_tools_enhanced.py` 中对 memory 工具门控的既有写法补一条 `test_skill_tools_gated_by_agent_flag`。

- [ ] **Step 2: 确认失败** → `pytest tests/harness/test_skill_tools.py -v`

- [ ] **Step 3: 实现三个工具**

三个文件均仿照 `memory_read.py` 结构：类属性（name/display_name/description/parameters_schema/returns_schema）、`is_available`（查询 `Agent.memory_procedural_enabled`，异常 False）、`execute`（`_to_uuid` 转换 → `SkillService` 调用 → `ToolResult.json`/`error`）。

`skill_save.py` 核心：

```python
class SkillSaveTool(BuiltinTool):
    name = "skill_save"
    display_name = "保存技能"
    description = (
        "把当前验证有效的操作流程/方法保存为命名技能，供以后复用。"
        "name 为简短英文/拼音标识，trigger 描述何时使用，content 为完整步骤。"
        "同名保存会更新已有技能（使用次数保留）。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "技能名（≤100 字符）", "maxLength": 100},
            "trigger": {"type": "string", "description": "何时使用该技能（触发条件）"},
            "content": {"type": "string", "description": "技能完整内容（步骤/规则）"},
            "importance": {"type": "number", "description": "重要度 0-1，默认 0.5"},
        },
        "required": ["name", "trigger", "content"],
    }

    async def execute(self, args, ctx):
        # 校验 name/trigger/content 非空、name 长度、importance 范围
        # svc.save(...) → ToolResult.json({"name": ..., "saved": True})
```

`skill_read.py`：无 name → `list_enabled` → `{"records": [{name, trigger, use_count}], "count": n}`；有 name → `get`（None → error；`is_enabled=False` → error"技能已禁用"）→ `increment_use_count` → `{"name", "trigger", "content", "use_count"}`。

`skill_delete.py`：`delete` 返回 False → `ToolResult.error("技能不存在")`。

`chat_stream.py` 在 `MemorySearchTool()` 注册后加：

```python
    # 注册技能工具（按 Agent.memory_procedural_enabled 控制可用性）
    tool_registry.register_builtin(SkillSaveTool())
    tool_registry.register_builtin(SkillReadTool())
    tool_registry.register_builtin(SkillDeleteTool())
```

- [ ] **Step 4: 测试通过 + Commit**

```bash
git add backend/app/services/harness/tools/skill_save.py backend/app/services/harness/tools/skill_read.py backend/app/services/harness/tools/skill_delete.py backend/app/api/routes/chat_stream.py backend/tests/harness/test_skill_tools.py
git commit -m "feat(harness): skill_save/read/delete builtin tools"
```

---

### Task 4: Runtime 技能索引注入

**Files:**
- Modify: `backend/app/services/harness/agent_runtime.py`
- Test: `backend/tests/harness/test_runtime_skills.py`

**Interfaces:**
- Consumes: Task 2 `SkillService.list_enabled`；runtime 既有 `_cached_memory_block` 模式（`agent_runtime.py:51` 初始化、`:83-89` 预取、`:348-350` 拼接）
- Produces: `self._cached_skill_block`（str，`<procedural_memory>...</procedural_memory>` 或空串）；system prompt 拼接顺序 = agent.system_prompt → memory_block → skill_block

- [ ] **Step 1: 写失败测试**

```python
"""Runtime 技能索引注入测试（P2-②）"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.services.harness.agent_runtime import AgentRuntime


def _runtime(agent, db):
    """最小 runtime 构造（不跑 run()，只测块构建）"""
    ctx = MagicMock()
    ctx.db = db
    ctx.user_id = str(uuid.uuid4())
    rt = AgentRuntime.__new__(AgentRuntime)
    rt._current_agent = agent
    rt.ctx = ctx
    rt._cached_memory_block = ""
    rt._cached_skill_block = ""
    return rt


def _agent(procedural_enabled=True):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.memory_procedural_enabled = procedural_enabled
    a.system_prompt = "You are a test agent."
    return a


@pytest.mark.asyncio
async def test_skill_block_injected(test_db):
    from app.services.harness.skill_service import SkillService
    aid, uid = uuid.uuid4(), uuid.uuid4()
    await SkillService(test_db).save(aid, uid, "deploy", "部署前", "步骤")
    rt = _runtime(_agent(True), test_db)
    rt.ctx.user_id = str(uid)
    rt.ctx.agent_id = aid
    block = await rt._build_skill_block()
    assert "<procedural_memory>" in block
    assert "deploy" in block
    assert "skill_read" in block


@pytest.mark.asyncio
async def test_skill_block_empty_when_disabled(test_db):
    rt = _runtime(_agent(False), test_db)
    block = await rt._build_skill_block()
    assert block == ""
```

- [ ] **Step 2: 确认失败** → `AttributeError: _build_skill_block`

- [ ] **Step 3: 实现**

`agent_runtime.py` 三处改动（对齐既有 memory_block 模式）：

3.1 `__init__` 中 `self._cached_memory_block = ""` 后加 `self._cached_skill_block = ""`

3.2 `run()` 中 2b 预取段后加：

```python
        # 2c. 预取技能索引（best-effort，不阻塞主循环）
        try:
            self._cached_skill_block = await self._build_skill_block()
        except Exception as e:
            logger.warning("技能索引预取失败: %s", type(e).__name__)
            self._cached_skill_block = ""
```

3.3 新方法（放在 `_retrieve_long_term_memory` 旁）：

```python
    async def _build_skill_block(self) -> str:
        """构建技能索引注入块（渐进披露：索引进 prompt，内容按需 skill_read）

        - 未启用 / 无技能 / 查询失败 → 空串（不注入）
        - 索引上限 20 条由 SkillService.list_enabled 控制
        """
        if not getattr(self._current_agent, "memory_procedural_enabled", False):
            return ""
        agent_uuid = uuid.UUID(str(self._current_agent.id))
        user_uuid = uuid.UUID(str(self.ctx.user_id))

        from app.services.harness.skill_service import SkillService

        skills = SkillService(self.ctx.db).list_enabled(agent_uuid, user_uuid)
        # list_enabled 是 async → await
        rows = await skills if hasattr(skills, "__await__") else skills
        if not rows:
            return ""
        lines = [
            "<procedural_memory>",
            "你可以使用以下技能（skill）。当任务匹配某技能的触发条件时，"
            "调用 skill_read(name=...) 获取完整内容后遵循执行：",
        ]
        for s in rows:
            lines.append(f"- {s.name}: {s.trigger} (使用次数: {s.use_count})")
        lines.append("</procedural_memory>")
        return "\n".join(lines)
```

3.4 `_build_messages_for_llm` 中 memory_block 拼接后加：

```python
        skill_block = getattr(self, "_cached_skill_block", "")
        if isinstance(skill_block, str) and skill_block:
            system_parts.append(skill_block)
```

- [ ] **Step 4: 测试通过 + Commit**

```bash
git add backend/app/services/harness/agent_runtime.py backend/tests/harness/test_runtime_skills.py
git commit -m "feat(harness): inject procedural skill index into system prompt"
```

---

### Task 5: REST API（harness_skills.py）

**Files:**
- Create: `backend/app/api/routes/harness_skills.py`
- Modify: `backend/app/main.py`（include_router，2 行，仿 harness_memories 挂载点）
- Test: `backend/tests/harness/test_harness_skills_api.py`

**Interfaces:**
- Consumes: Task 2 SkillService；`get_db` / `get_current_user` 依赖
- Produces: `GET/POST /api/v1/harness/agents/{agent_id}/skills`、`DELETE .../skills/{name}`；响应 `{"records": [...], "count": n}`

- [ ] **Step 1: 写失败测试**

仿照 `test_admin_mcp_transports.py` 的 fixture 模式（SQLite StaticPool + dependency_overrides；`get_current_user` 覆盖为普通用户 `{"role": "user", "id": "<uuid>"}`）：

```python
"""技能 REST API 测试（P2-②）"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

AID = str(uuid.uuid4())
UID = str(uuid.uuid4())


@pytest.fixture
def client():
    from app.models.agent import Agent  # noqa: F401
    from app.models.agent_procedural_memory import AgentProceduralMemory  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    # agents 行（无 FK 校验需求也先建，保持数据完整）
    session = sessionmaker(bind=engine)()
    session.add(Agent(id=uuid.UUID(AID), name="a", slug="a-test", created_by="u"))
    session.commit()

    def _override_db():
        yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": UID}
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_create_list_delete_skill(client):
    # 创建
    r = client.post(
        f"/api/v1/harness/agents/{AID}/skills",
        json={"name": "deploy", "trigger": "部署前", "content": "1. 测试"},
    )
    assert r.status_code == 201, r.text
    # 列表
    r = client.get(f"/api/v1/harness/agents/{AID}/skills")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["records"][0]["name"] == "deploy"
    # 删除
    r = client.delete(f"/api/v1/harness/agents/{AID}/skills/deploy")
    assert r.status_code == 204
    r = client.get(f"/api/v1/harness/agents/{AID}/skills")
    assert r.json()["count"] == 0


def test_create_skill_validation(client):
    r = client.post(
        f"/api/v1/harness/agents/{AID}/skills",
        json={"name": "", "trigger": "t", "content": "c"},
    )
    assert r.status_code == 422
```

- [ ] **Step 2: 确认失败** → 404（路由不存在）

- [ ] **Step 3: 实现**

`harness_skills.py`（完全仿照 `harness_memories.py` 的鉴权与错误处理风格）：

```python
"""Agent 技能（程序性记忆）管理 API

P2-② Memory procedural
- GET    /api/v1/harness/agents/{agent_id}/skills           列出全部技能（含禁用）
- POST   /api/v1/harness/agents/{agent_id}/skills           创建/更新技能
- DELETE /api/v1/harness/agents/{agent_id}/skills/{name}    删除技能
所有端点要求认证；按 (agent_id, current_user.id) 隔离。
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/harness/agents/{agent_id}/skills",
    tags=["harness-skills"],
)


class SkillCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    trigger: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    is_enabled: bool = True


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{field} 不是合法的 UUID")


def _serialize(row) -> dict:
    return {
        "name": row.name,
        "trigger": row.trigger,
        "content": row.content,
        "importance": row.importance,
        "use_count": row.use_count,
        "is_enabled": row.is_enabled,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
async def list_skills(agent_id: str, db: Session = Depends(get_db),
                      current_user: dict = Depends(get_current_user)):
    from app.services.harness.skill_service import SkillService

    svc = SkillService(db)
    records = await svc.list_all(
        _parse_uuid(agent_id, "agent_id"),
        _parse_uuid(str(current_user["id"]), "user_id"),
    )
    return {"records": [_serialize(r) for r in records], "count": len(records)}


@router.post("", status_code=201)
async def create_skill(agent_id: str, data: SkillCreateRequest,
                       db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    from app.services.harness.skill_service import SkillService

    svc = SkillService(db)
    row = await svc.save(
        _parse_uuid(agent_id, "agent_id"),
        _parse_uuid(str(current_user["id"]), "user_id"),
        data.name.strip(),
        data.trigger.strip(),
        data.content,
        importance=data.importance,
    )
    row.is_enabled = data.is_enabled
    db.commit()
    logger.info("技能已保存: agent=%s name=%s", agent_id, data.name)
    return _serialize(row)


@router.delete("/{name}", status_code=204)
async def delete_skill(agent_id: str, name: str,
                       db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    from app.services.harness.skill_service import SkillService

    svc = SkillService(db)
    ok = await svc.delete(
        _parse_uuid(agent_id, "agent_id"),
        _parse_uuid(str(current_user["id"]), "user_id"),
        name,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="技能不存在")
```

`app/main.py` 在 `harness_memories_router` 挂载后加：

```python
from app.api.routes.harness_skills import router as harness_skills_router  # noqa: E402
app.include_router(harness_skills_router)
```

- [ ] **Step 4: 测试通过 + Commit**

```bash
git add backend/app/api/routes/harness_skills.py backend/app/main.py backend/tests/harness/test_harness_skills_api.py
git commit -m "feat(harness): skills REST API for user-side management"
```

---

### Task 6: 前端（API 客户端 + SkillsViewer + 管理开关）

**Files:**
- Create: `frontend/src/api/harnessSkillsApi.ts`
- Create: `frontend/src/components/Harness/SkillsViewer.tsx`
- Modify: `frontend/src/components/Tools/ProductManagerAgent.tsx`（MemoryViewer 旁加 SkillsViewer Tab，仿现有 Tab 结构）
- Modify: `frontend/src/components/Admin/AgentManagement.tsx`（`memory_procedural_enabled` 开关，镜像 memoryLongTermEnabled 模式）

**Interfaces:**
- Consumes: Task 5 REST 契约
- Produces: `harnessSkillsApi.list/create/remove`；`SkillsViewer` 组件（props: `agentId: string`）

- [ ] **Step 1: API 客户端**（仿 `harnessMemoriesApi.ts`，含 authedFetch 与错误处理）：

```typescript
/**
 * Agent 技能（程序性记忆）API Client
 * P2-② Memory procedural
 * 对应后端 /api/v1/harness/agents/{agent_id}/skills 系列接口。
 */
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const HARNESS_API_BASE_URL = '/api/v1/harness';

export interface SkillEntry {
  name: string;
  trigger: string;
  content: string;
  importance: number;
  use_count: number;
  is_enabled: boolean;
  updated_at: string | null;
}

export const harnessSkillsApi = {
  async list(agentId: string): Promise<{ records: SkillEntry[]; count: number }> {
    const response = await authedFetch(
      `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/skills`,
      { headers: getAuthHeaders() },
    );
    if (!response.ok) throw new Error('加载技能失败');
    return response.json();
  },

  async create(
    agentId: string,
    data: { name: string; trigger: string; content: string },
  ): Promise<SkillEntry> {
    const response = await authedFetch(
      `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/skills`,
      {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      },
    );
    if (!response.ok) throw new Error('保存技能失败');
    return response.json();
  },

  async remove(agentId: string, name: string): Promise<void> {
    const response = await authedFetch(
      `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/skills/${encodeURIComponent(name)}`,
      { method: 'DELETE', headers: getAuthHeaders() },
    );
    if (!response.ok && response.status !== 204) throw new Error('删除技能失败');
  },
};
```

（`HARNESS_API_BASE_URL` 以 `harnessMemoriesApi.ts` 实际取值为准，保持一致。）

- [ ] **Step 2: SkillsViewer 组件**——镜像 `MemoryViewer.tsx`（列表 + 删除 + 新增表单 name/trigger/content），样式类复用其现有 Tailwind 类。

- [ ] **Step 3: 挂载与开关**——ProductManagerAgent 的 Tab 区仿 MemoryViewer 用法（`<SkillsViewer agentId={selectedAgentId} />`）；AgentManagement 仿 `memoryLongTermEnabled` 增加 `memoryProceduralEnabled` state + checkbox + 提交字段 `memory_procedural_enabled`。

- [ ] **Step 4: 构建验证 + Commit**

Run: `cd frontend && npm run build && npx tsc --noEmit`（本次改动文件无 TS 错误；`cursorCache.ts` 既有错误不在范围内）

```bash
git add frontend/src/api/harnessSkillsApi.ts frontend/src/components/Harness/SkillsViewer.tsx frontend/src/components/Tools/ProductManagerAgent.tsx frontend/src/components/Admin/AgentManagement.tsx
git commit -m "feat(frontend): skills viewer + procedural memory toggle"
```

---

### Task 7: 全量回归 + 验收收尾

- [ ] **Step 1:** `cd backend && .venv/Scripts/python -m pytest tests/harness -q` → 全绿（≥ 旧基线 658 + 新增）
- [ ] **Step 2:** spec 状态行改 `已实现（2026-08-30；验证：pytest ... passed / 前端 build + tsc 通过）`，提交：

```bash
git add docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-2-memory-procedural-design.md
git commit -m "docs(harness): mark P2-② memory procedural as implemented"
```

---

## 验收标准（对照 spec §4）

1. `pytest tests/harness` 全绿：service/tools/runtime/API/模型新用例 + 既有 memory 零回归
2. 前端 build + tsc 通过；SkillsViewer 可增删技能；AgentManagement 可开关 procedural
3. migration `20260830b` 幂等
4. system prompt 注入块仅在 enabled 且有技能时出现
