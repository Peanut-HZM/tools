"""memory_write BuiltinTool 测试（Task 3）

覆盖：
1. schema 完整（含必填字段 key/value，可选 summary）
2. 写入新条目（action=created）
3. UPSERT 已有条目（不重复创建，action=updated）
4. value 非 dict 拒绝
5. 缺少必填参数（key 或 value）拒绝
6. key 超长拒绝（>200 字符）
7. value > 10KB 拒绝（边界）
8. 触发 max_entries 限制（默认 100 条）
9. 更新已有条目不触发 max_entries
10. user 隔离（不同 user 的同名 key 不互相覆盖）
"""
import uuid

import pytest

from app.models.agent import Agent
from app.models.agent_memory import AgentMemoryLongTerm
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.memory_write import MemoryWriteTool


# === 测试用常量（避免 magic uuid） ===
AGENT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_B = uuid.UUID("11111111-1111-1111-1111-111111111112")
USER_A = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_B = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _make_ctx(db, agent_id, user_id):
    """构造包含真实 db session 的 ToolContext"""
    ctx = ToolContext(
        user_id=str(user_id),
        conversation_id="conv-1",
        agent_id=str(agent_id),
        db=db,
    )
    return ctx


def _enable_agent(db, agent_id, name="agent", config=None):
    """插入一个 memory_long_term_enabled=True 的 Agent"""
    agent = Agent(
        id=agent_id,
        name=name,
        description="test agent",
        system_prompt="sys",
        memory_long_term_enabled=True,
        memory_long_term_config=(config if config is not None else {}),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _add_memory(db, agent_id, user_id, key, value, summary=None):
    """写入一条长期记忆（直接 ORM）"""
    record = AgentMemoryLongTerm(
        agent_id=agent_id,
        user_id=user_id,
        key=key,
        value=value,
        summary=summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ============================================================
# 1. schema 完整
# ============================================================

def test_memory_write_schema():
    """工具元信息 + schema 完整（含必填字段、可选 summary）"""
    tool = MemoryWriteTool()
    assert tool.name == "memory_write"
    assert tool.display_name == "写入长期记忆"
    assert tool.description  # 非空

    schema = tool.parameters_schema
    assert schema["type"] == "object"

    # 必填字段：key + value
    required = schema.get("required", [])
    assert "key" in required
    assert "value" in required
    assert "summary" not in required  # 可选

    # properties 完整
    props = schema["properties"]
    assert "key" in props
    assert "value" in props
    assert "summary" in props

    # value 必须是 object
    assert props["value"]["type"] == "object"

    # 长度限制
    assert props["key"]["maxLength"] == 200
    assert props["summary"]["maxLength"] == 500


# ============================================================
# 2. 写入新条目
# ============================================================

@pytest.mark.asyncio
async def test_write_new_entry_creates_record(test_db):
    """写入新 key → 创建记录（action=created）"""
    _enable_agent(test_db, AGENT_A, "agent-A")

    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    result = await tool.execute(
        {"key": "preference.language", "value": {"preferred": "zh-CN"}},
        ctx,
    )
    assert result.success is True
    assert result.content_type == "json"
    assert result.content["action"] == "created"
    assert result.content["key"] == "preference.language"

    # 验证 DB 中确实有一条记录
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == "preference.language",
        )
        .first()
    )
    assert record is not None
    assert record.value == {"preferred": "zh-CN"}


# ============================================================
# 3. UPSERT 已有条目
# ============================================================

@pytest.mark.asyncio
async def test_write_upserts_existing_key(test_db):
    """相同 key → 更新已有记录（不重复创建，action=updated）"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    _add_memory(
        test_db, AGENT_A, USER_A, "k",
        {"v": 1}, summary="初始摘要",
    )

    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    result = await tool.execute(
        {"key": "k", "value": {"v": 2}, "summary": "更新摘要"},
        ctx,
    )
    assert result.success is True
    assert result.content["action"] == "updated"

    # 验证仍只有一条记录，value/summary 已更新
    records = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == "k",
        )
        .all()
    )
    assert len(records) == 1
    assert records[0].value == {"v": 2}
    assert records[0].summary == "更新摘要"


# ============================================================
# 4. value 非 dict 拒绝
# ============================================================

@pytest.mark.asyncio
async def test_write_rejects_non_dict_value(test_db):
    """value 不是 dict 必须拒绝（string/list/int/null 都拒绝）"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    for bad_value in [
        "not-a-dict",
        ["list", "not", "dict"],
        123,
        1.5,
        True,
        None,
    ]:
        result = await tool.execute({"key": "k", "value": bad_value}, ctx)
        assert result.success is False, f"value={bad_value!r} 应被拒绝"
        assert (
            "value" in (result.error_message or "")
            or "对象" in (result.error_message or "")
            or "JSON" in (result.error_message or "")
        )


# ============================================================
# 5. 缺少必填参数拒绝
# ============================================================

@pytest.mark.asyncio
async def test_write_rejects_missing_required(test_db):
    """缺少 key 或 value 必须拒绝"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 缺 key
    result = await tool.execute({"value": {"v": 1}}, ctx)
    assert result.success is False

    # 缺 value
    result = await tool.execute({"key": "k"}, ctx)
    assert result.success is False

    # 全部缺失
    result = await tool.execute({}, ctx)
    assert result.success is False


# ============================================================
# 6. key 超长拒绝
# ============================================================

@pytest.mark.asyncio
async def test_write_rejects_overlong_key(test_db):
    """key 超过 200 字符应被拒绝"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    long_key = "k" * 201
    result = await tool.execute({"key": long_key, "value": {"v": 1}}, ctx)
    assert result.success is False
    assert "长度" in (result.error_message or "") or "200" in (result.error_message or "")


# ============================================================
# 7. value > 10KB 拒绝（边界）
# ============================================================

@pytest.mark.asyncio
async def test_write_rejects_oversized_value(test_db):
    """value 序列化后 > 10KB 拒绝；恰好 10KB 接受；超 1 字节拒绝

    JSON 序列化 `{"data": "x" * N}` 长度为 N + 12 字节（包含 `{"data": "`、`x"...`、`"}`）。
    因此 10KB 严格边界为 N=10228（恰好 10240 字节），N=10229（10241 字节）被拒。
    """
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 边界 1：恰好 10KB（{"data": "x" * 10228} = 10240 字节）
    exact = {"data": "x" * 10228}
    result = await tool.execute({"key": "k_exact", "value": exact}, ctx)
    assert result.success is True, f"恰好 10KB 应接受：{result.error_message}"
    # 清理
    test_db.query(AgentMemoryLongTerm).filter(
        AgentMemoryLongTerm.key == "k_exact"
    ).delete()
    test_db.commit()

    # 边界 2：10KB + 1 字节（{"data": "x" * 10229} = 10241 字节）
    over = {"data": "x" * 10229}
    result = await tool.execute({"key": "k_over", "value": over}, ctx)
    assert result.success is False
    assert "10KB" in (result.error_message or "") or "10240" in (result.error_message or "")

    # 极端：远大于 10KB
    huge = {"data": "x" * 50000}
    result = await tool.execute({"key": "k_huge", "value": huge}, ctx)
    assert result.success is False


# ============================================================
# 8. 触发 max_entries 限制（默认 100）
# ============================================================

@pytest.mark.asyncio
async def test_write_enforces_max_entries(test_db):
    """每 (agent, user) 默认 100 条；超过则拒绝新增（但允许更新已有）"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    # 提前插入 100 条
    for i in range(100):
        _add_memory(test_db, AGENT_A, USER_A, f"k{i}", {"i": i})

    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 第 101 条（新 key）必须被拒绝
    result = await tool.execute({"key": "k_new", "value": {"v": 1}}, ctx)
    assert result.success is False
    assert "100" in (result.error_message or "")

    # 验证没有写入
    cnt = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
        )
        .count()
    )
    assert cnt == 100


# ============================================================
# 9. 更新已有条目不触发 max_entries
# ============================================================

@pytest.mark.asyncio
async def test_update_existing_does_not_count_against_max(test_db):
    """在已有 100 条时再写入同一 key，应允许（不触发 max_entries）"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    for i in range(100):
        _add_memory(test_db, AGENT_A, USER_A, f"k{i}", {"i": i})

    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 更新 k0
    result = await tool.execute({"key": "k0", "value": {"updated": True}}, ctx)
    assert result.success is True
    assert result.content["action"] == "updated"

    # k0 的 value 已被更新
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == "k0",
        )
        .first()
    )
    assert record.value == {"updated": True}

    # 总数仍为 100
    cnt = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
        )
        .count()
    )
    assert cnt == 100


# ============================================================
# 10. user 隔离（不同 user 的同名 key 不互相覆盖）
# ============================================================

@pytest.mark.asyncio
async def test_write_isolated_by_user(test_db):
    """user-A 写 k 不应影响 user-B 的 k"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    _add_memory(
        test_db, AGENT_A, USER_B, "k",
        {"other": True}, summary="user-B 的数据",
    )

    tool = MemoryWriteTool()
    ctx_a = _make_ctx(test_db, AGENT_A, USER_A)

    # user-A 写入同名 key
    result = await tool.execute(
        {"key": "k", "value": {"mine": True}},
        ctx_a,
    )
    assert result.success is True

    # user-B 的记录未受影响
    record_b = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_B,
            AgentMemoryLongTerm.key == "k",
        )
        .first()
    )
    assert record_b is not None
    assert record_b.value == {"other": True}
    assert record_b.summary == "user-B 的数据"

    # 两条记录并存
    cnt = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.key == "k",
        )
        .count()
    )
    assert cnt == 2