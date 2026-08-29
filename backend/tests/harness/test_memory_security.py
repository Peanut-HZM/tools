"""memory_write BuiltinTool 安全加固测试（Task 5）

覆盖：
1. test_key_strips_control_chars — key 中的控制字符被剥离
2. test_value_nested_dict_accepted — value 支持嵌套 dict/list 序列化
3. test_value_rejects_circular_or_unserializable — value 含不可序列化对象（如 set）被拒绝
4. test_value_size_boundary — value 恰好 10KB 接受，超 10KB 拒绝
5. test_sql_injection_in_key_safe — key 含 SQL 注入尝试时安全处理（写入成功 + 表未被删除）
"""
import uuid

import pytest

from app.models.agent import Agent
from app.models.agent_memory import AgentMemoryLongTerm
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.memory_write import MemoryWriteTool


# === 测试用常量（避免 magic uuid） ===
AGENT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_A = uuid.UUID("22222222-2222-2222-2222-222222222222")


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
        memory_long_term_config={},
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


# ============================================================
# 1. key 控制字符剥离
# ============================================================

@pytest.mark.asyncio
async def test_key_strips_control_chars(test_db):
    """key 中的控制字符（0x00-0x1F / 0x7F-0x9F）应被剥离

    SQLAlchemy/PostgreSQL 拒绝不可见字符作为主键的一部分。
    剥离后 key 是合法标识符，写入应成功。
    """
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 构造含控制字符的 key
    dirty_key = "user\x00pre\x07fer\x1Fence"
    result = await tool.execute(
        {"key": dirty_key, "value": {"lang": "zh-CN"}},
        ctx,
    )
    assert result.success is True, f"含控制字符的 key 应被剥离并接受: {result.error_message}"
    # 返回的 key 应是剥离后的形式
    assert result.content["key"] == "userpreference"
    assert "\x00" not in result.content["key"]
    assert "\x07" not in result.content["key"]
    assert "\x1f" not in result.content["key"]

    # 验证 DB 中实际存储的 key 也已剥离
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == "userpreference",
        )
        .first()
    )
    assert record is not None
    assert record.value == {"lang": "zh-CN"}

    # 全是控制字符的 key 剥离后为空 → 拒绝
    only_ctrl_key = "\x00\x07\x1f"
    result = await tool.execute(
        {"key": only_ctrl_key, "value": {"x": 1}},
        ctx,
    )
    assert result.success is False
    assert "不能为空" in (result.error_message or "")


# ============================================================
# 2. value 嵌套 dict/list 接受
# ============================================================

@pytest.mark.asyncio
async def test_value_nested_dict_accepted(test_db):
    """value 支持嵌套 dict + list 序列化"""
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    nested = {
        "a": {
            "b": [1, 2, 3],
            "c": "中文",
            "d": None,
            "e": True,
            "f": 3.14,
        }
    }
    result = await tool.execute({"key": "nested.value", "value": nested}, ctx)
    assert result.success is True, f"嵌套 dict 应接受: {result.error_message}"
    assert result.content["action"] == "created"

    # 验证回读
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == "nested.value",
        )
        .first()
    )
    assert record is not None
    assert record.value == nested


# ============================================================
# 3. value 不可序列化对象（如 set）拒绝
# ============================================================

@pytest.mark.asyncio
async def test_value_rejects_unserializable_value(test_db):
    """value 含不可 JSON 序列化的对象（set）必须被拒绝

    JSON 不支持 set，json.dumps 会抛 TypeError。
    当前实现捕获 TypeError/ValueError 并返回错误（不抛 500）。
    """
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    bad_value = {"bad": {1, 2, 3}}
    result = await tool.execute({"key": "bad.value", "value": bad_value}, ctx)
    assert result.success is False
    assert (
        "无法序列化" in (result.error_message or "")
        or "JSON" in (result.error_message or "")
        or "value" in (result.error_message or "")
    ), f"应返回可读错误信息: {result.error_message}"

    # 验证 DB 中没有写入该 key
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == "bad.value",
        )
        .first()
    )
    assert record is None, "失败的写入不应落库"


# ============================================================
# 4. value 大小边界
# ============================================================

@pytest.mark.asyncio
async def test_value_size_boundary(test_db):
    """value 序列化后恰好 10KB 接受；超 10KB 拒绝

    JSON 序列化 `{"data": "x" * N}` 长度为 N + 12 字节（包含 `{"data": "`、`x"...`、`"}`）。
    因此 10KB 严格边界为 N=10228（恰好 10240 字节），N=10229（10241 字节）被拒。
    """
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 边界 1：恰好 10KB（{"data": "x" * 10228} = 10240 字节）
    exact = {"data": "x" * 10228}
    result = await tool.execute({"key": "size.exact", "value": exact}, ctx)
    assert result.success is True, f"恰好 10KB 应接受: {result.error_message}"
    assert result.content["action"] == "created"

    # 边界 2：10KB + 1 字节（{"data": "x" * 10229} = 10241 字节）
    over = {"data": "x" * 10229}
    result = await tool.execute({"key": "size.over", "value": over}, ctx)
    assert result.success is False
    assert (
        "10KB" in (result.error_message or "")
        or "10240" in (result.error_message or "")
    )

    # 验证恰好 10KB 的记录存在
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(AgentMemoryLongTerm.key == "size.exact")
        .first()
    )
    assert record is not None


# ============================================================
# 5. SQL 注入尝试 key 安全处理
# ============================================================

@pytest.mark.asyncio
async def test_sql_injection_in_key_safe(test_db):
    """SQL 注入尝试 key 应安全处理（参数化查询使注入无效）

    即使传入类 SQL 注入 key，SQLAlchemy 参数化查询会将其作为普通字符串处理：
    - 写入应成功（key 作为字面量）
    - 表 agent_memory_long_term 应仍然存在
    - 没有执行 DROP TABLE 等破坏性语句
    """
    _enable_agent(test_db, AGENT_A, "agent-A")
    tool = MemoryWriteTool()
    ctx = _make_ctx(test_db, AGENT_A, USER_A)

    # 控制字符 + 引号都被剥离，所以注入字符不会被剥离（仅控制字符）
    # 用一个不含控制字符但有 SQL 关键字的 key
    injection_key = "k'; DROP TABLE agent_memory_long_term; --"
    result = await tool.execute(
        {"key": injection_key, "value": {"injected": True}},
        ctx,
    )
    assert result.success is True, (
        f"SQL 注入 key 应被参数化查询安全处理: {result.error_message}"
    )

    # 验证记录存在，且 key 完整保留（作为普通字符串）
    record = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
            AgentMemoryLongTerm.key == injection_key,
        )
        .first()
    )
    assert record is not None
    assert record.value == {"injected": True}

    # 关键：表依然存在，可以再次写入
    result2 = await tool.execute(
        {"key": "after_injection", "value": {"ok": True}},
        ctx,
    )
    assert result2.success is True, "表应仍然存在并接受新写入"

    # 总记录数：2 条（注入 key + after_injection）
    cnt = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_A,
            AgentMemoryLongTerm.user_id == USER_A,
        )
        .count()
    )
    assert cnt == 2

    # 控制字符 + SQL 关键字组合：剥离后只剩普通 key
    mixed_key = "evil\x00key'; DROP TABLE --"
    result3 = await tool.execute(
        {"key": mixed_key, "value": {"x": 1}},
        ctx,
    )
    assert result3.success is True
    assert "\x00" not in result3.content["key"]
    # 注入相关的引号和关键字保留（作为字面量）
    assert "evilkey" in result3.content["key"]