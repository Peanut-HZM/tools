"""memory_read BuiltinTool 测试（Task 2）

覆盖：
1. schema 完整（name / display_name / key 参数）
2. 按 key 精确读取存在的记录
3. key 不存在时返回 value=null
4. 不传 key 返回该命名空间全部记录（按 updated_at desc）
5. user 隔离（不同 user 的同名 key 互不可见）
6. agent 隔离（不同 agent 的同名 key 互不可见）
7. key 非字符串拒绝
8. key 长度超限拒绝（>200 字符）
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.agent import Agent
from app.models.agent_memory import AgentMemoryLongTerm
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.memory_read import MemoryReadTool


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


def _enable_agent(db, agent_id, name="agent"):
    """插入一个 memory_long_term_enabled=True 的 Agent"""
    agent = Agent(
        id=agent_id,
        name=name,
        description="test agent",
        system_prompt="sys",
        memory_long_term_enabled=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _add_memory(db, agent_id, user_id, key, value, summary=None):
    """写入一条长期记忆"""
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

def test_memory_read_schema():
    """工具元信息 + schema 完整"""
    tool = MemoryReadTool()
    assert tool.name == "memory_read"
    assert tool.display_name == "读取长期记忆"
    assert tool.description  # 非空
    assert tool.parameters_schema["type"] == "object"

    props = tool.parameters_schema["properties"]
    assert "key" in props
    # key 是可选的
    assert "key" not in tool.parameters_schema.get("required", [])

    # key 字段长度限制
    assert props["key"]["maxLength"] == 200


# ============================================================
# 2. 按 key 读取存在的记录
# ============================================================

@pytest.mark.asyncio
async def test_read_existing_key_returns_value(test_db):
    """按 key 精确读取存在的记录"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    _add_memory(
        test_db, AGENT_A, USER_A, "favorite_color",
        {"color": "blue"}, summary="用户最喜欢蓝色",
    )

    tool = MemoryReadTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    result = await tool.execute({"key": "favorite_color"}, ctx)
    assert result.success is True
    assert result.content_type == "json"

    payload = result.content
    assert payload["key"] == "favorite_color"
    assert payload["value"] == {"color": "blue"}
    assert payload["summary"] == "用户最喜欢蓝色"
    assert payload["updated_at"] is not None


# ============================================================
# 3. key 不存在 → value=null
# ============================================================

@pytest.mark.asyncio
async def test_read_missing_key_returns_value_null(test_db):
    """key 不存在时返回 {key, value: null}，不报错"""
    _enable_agent(test_db, AGENT_A, "agent-A")

    tool = MemoryReadTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    result = await tool.execute({"key": "nonexistent"}, ctx)
    assert result.success is True

    payload = result.content
    assert payload["key"] == "nonexistent"
    assert payload["value"] is None
    assert payload["summary"] is None
    assert payload["updated_at"] is None


# ============================================================
# 4. 不传 key 返回全部（按 updated_at desc）
# ============================================================

@pytest.mark.asyncio
async def test_list_all_records_sorted_by_updated_at_desc(test_db):
    """不传 key 返回当前 (agent, user) 命名空间全部记录，updated_at desc"""
    import time

    _enable_agent(test_db, AGENT_A, "agent-A")

    # SQLite 时间戳精度为秒，两次写入至少间隔 1.05s 才能产生可观察差异
    _add_memory(test_db, AGENT_A, USER_A, "k1", {"v": 1})
    time.sleep(1.05)
    _add_memory(test_db, AGENT_A, USER_A, "k2", {"v": 2})
    time.sleep(1.05)
    _add_memory(test_db, AGENT_A, USER_A, "k3", {"v": 3})

    tool = MemoryReadTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    result = await tool.execute({}, ctx)
    assert result.success is True

    records = result.content["records"]
    assert len(records) == 3
    assert result.content["count"] == 3

    # updated_at desc：最新写入的 k3 在最前
    keys = [r["key"] for r in records]
    assert keys[0] == "k3"
    assert keys[-1] == "k1"

    # 每条记录字段完整
    for r in records:
        assert "key" in r
        assert "value" in r
        assert "summary" in r
        assert "updated_at" in r


# ============================================================
# 5. user 隔离
# ============================================================

@pytest.mark.asyncio
async def test_user_isolation(test_db):
    """不同 user 不能读取到对方的记录"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    _add_memory(test_db, AGENT_A, USER_A, "nickname", {"nick": "小蓝"})
    _add_memory(test_db, AGENT_A, USER_B, "nickname", {"nick": "小红"})

    tool = MemoryReadTool()

    # USER_A 看 USER_A 的
    ctx_a = _make_ctx(test_db, AGENT_A, USER_A)
    res_a = await tool.execute({"key": "nickname"}, ctx_a)
    assert res_a.success is True
    assert res_a.content["value"] == {"nick": "小蓝"}

    # USER_B 看 USER_B 的
    ctx_b = _make_ctx(test_db, AGENT_A, USER_B)
    res_b = await tool.execute({"key": "nickname"}, ctx_b)
    assert res_b.success is True
    assert res_b.content["value"] == {"nick": "小红"}

    # USER_A 列表模式应只看到 1 条
    res_list = await tool.execute({}, ctx_a)
    records = res_list.content["records"]
    assert len(records) == 1
    assert records[0]["value"] == {"nick": "小蓝"}


# ============================================================
# 6. agent 隔离
# ============================================================

@pytest.mark.asyncio
async def test_agent_isolation(test_db):
    """不同 agent 不能读取到对方的记录"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    _enable_agent(test_db, AGENT_B, "agent-B")
    _add_memory(test_db, AGENT_A, USER_A, "config", {"src": "A"})
    _add_memory(test_db, AGENT_B, USER_A, "config", {"src": "B"})

    tool = MemoryReadTool()

    ctx_a = _make_ctx(test_db, AGENT_A, USER_A)
    res_a = await tool.execute({"key": "config"}, ctx_a)
    assert res_a.content["value"] == {"src": "A"}

    ctx_b = _make_ctx(test_db, AGENT_B, USER_A)
    res_b = await tool.execute({"key": "config"}, ctx_b)
    assert res_b.content["value"] == {"src": "B"}

    # 列表模式：每个 agent 只看到自己的
    res_list_a = await tool.execute({}, ctx_a)
    assert len(res_list_a.content["records"]) == 1
    res_list_b = await tool.execute({}, ctx_b)
    assert len(res_list_b.content["records"]) == 1


# ============================================================
# 7. key 非字符串拒绝
# ============================================================

@pytest.mark.asyncio
async def test_non_string_key_rejected(test_db):
    """key 不是字符串时应被拒绝"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryReadTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    for bad_key in [123, 1.5, True, ["k"], {"x": 1}, None]:
        # None 等同于不传 key，走列表分支（合法）；其它类型必须拒绝
        if bad_key is None:
            result = await tool.execute({"key": None}, ctx)
            assert result.success is True
            assert "records" in result.content
            continue
        result = await tool.execute({"key": bad_key}, ctx)
        assert result.success is False
        assert "key" in (result.error_message or "") or "字符串" in (result.error_message or "")


# ============================================================
# 8. key 长度超限拒绝
# ============================================================

@pytest.mark.asyncio
async def test_key_too_long_rejected(test_db):
    """key 长度超过 200 字符应被拒绝"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryReadTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    long_key = "k" * 201
    result = await tool.execute({"key": long_key}, ctx)
    assert result.success is False
    assert "长度" in (result.error_message or "") or "200" in (result.error_message or "")

    # 边界：恰好 200 字符应被接受（key 不存在 → value=null）
    boundary_key = "k" * 200
    result_ok = await tool.execute({"key": boundary_key}, ctx)
    assert result_ok.success is True
    assert result_ok.content["value"] is None
