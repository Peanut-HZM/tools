"""memory 工具注册测试（Task 4）

覆盖：
- MemoryReadTool / MemoryWriteTool 可注册到 ToolRegistry
- Agent.memory_long_term_enabled=True 时 is_available 返回 True
- Agent.memory_long_term_enabled=False 时 is_available 返回 False
- memory_read / memory_write 出现在 function schemas 中
"""
import uuid

import pytest

from app.models.agent import Agent
from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tools.memory_read import MemoryReadTool
from app.services.harness.tools.memory_write import MemoryWriteTool


# 测试用常量（避免 magic uuid）
AGENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USER_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _make_ctx(db, agent_id, user_id):
    """构造包含真实 db session 的 ToolContext。"""
    from app.services.harness.tool_protocol import ToolContext

    return ToolContext(
        user_id=str(user_id),
        conversation_id="conv-1",
        agent_id=str(agent_id),
        db=db,
    )


def _add_agent(db, agent_id, memory_long_term_enabled):
    """插入一个指定 memory_long_term_enabled 的 Agent。"""
    agent = Agent(
        id=agent_id,
        name="memory-test-agent",
        description="agent for memory registration test",
        system_prompt="sys",
        memory_long_term_enabled=memory_long_term_enabled,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


# ============================================================
# 1. 注册
# ============================================================

def test_register_tools(test_db):
    """MemoryReadTool / MemoryWriteTool 可注册到 ToolRegistry。"""
    registry = ToolRegistry(db=test_db)
    read_tool = MemoryReadTool()
    write_tool = MemoryWriteTool()

    registry.register_builtin(read_tool)
    registry.register_builtin(write_tool)

    assert "memory_read" in registry._builtin
    assert "memory_write" in registry._builtin
    assert registry._builtin["memory_read"] is read_tool
    assert registry._builtin["memory_write"] is write_tool


# ============================================================
# 2. 可用性 — enabled
# ============================================================

def test_available_when_enabled(test_db):
    """Agent.memory_long_term_enabled=True 时，memory 工具均可用。"""
    _add_agent(test_db, AGENT_ID, memory_long_term_enabled=True)

    ctx = _make_ctx(test_db, AGENT_ID, USER_ID)

    assert MemoryReadTool().is_available(ctx) is True
    assert MemoryWriteTool().is_available(ctx) is True


# ============================================================
# 3. 可用性 — disabled
# ============================================================

def test_unavailable_when_disabled(test_db):
    """Agent.memory_long_term_enabled=False 时，memory 工具均不可用。"""
    _add_agent(test_db, AGENT_ID, memory_long_term_enabled=False)

    ctx = _make_ctx(test_db, AGENT_ID, USER_ID)

    assert MemoryReadTool().is_available(ctx) is False
    assert MemoryWriteTool().is_available(ctx) is False


# ============================================================
# 4. function schemas
# ============================================================

def test_memory_tools_in_function_schemas(test_db):
    """memory_read / memory_write 出现在 function schemas 中。"""
    registry = ToolRegistry(db=test_db)
    read_tool = MemoryReadTool()
    write_tool = MemoryWriteTool()
    registry.register_builtin(read_tool)
    registry.register_builtin(write_tool)

    schemas = registry.to_function_schemas([read_tool, write_tool])
    names = {s["name"] for s in schemas}
    assert "memory_read" in names
    assert "memory_write" in names
