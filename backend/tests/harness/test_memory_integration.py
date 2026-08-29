"""memory 端到端集成测试（Task 7）

覆盖：
1. 完整 write → read 流程：验证 value/summary 正确存取
2. Agent.memory_long_term_config.max_entries 生效
3. 更新已有条目不触发 max_entries
4. user 隔离：不同 user 完全看不到彼此的数据
5. Agent.memory_long_term_enabled=False 时 is_available 返回 False

风格与 Task 1-6 保持一致（参考 test_memory_registration.py / test_memory_write_tool.py）：
- 使用真实 ToolContext 对象（避免 MagicMock 行为偏差）
- 通过 _enable_agent 助手构造 Agent
- 所有用例共享一个 SQLite 内存库（test_db fixture）
"""
import uuid

import pytest

from app.models.agent import Agent
from app.models.agent_memory import AgentMemoryLongTerm
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.memory_read import MemoryReadTool
from app.services.harness.tools.memory_write import MemoryWriteTool


# === 测试用常量（避免 magic uuid） ===
AGENT_INTEGRATION = uuid.UUID("77777777-7777-7777-7777-777777777777")
AGENT_SHARED = uuid.UUID("88888888-8888-8888-8888-888888888888")
AGENT_DISABLED = uuid.UUID("99999999-9999-9999-9999-999999999999")
USER_INTEGRATION = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_1 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_2 = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _make_ctx(db, agent_id, user_id):
    """构造包含真实 db session 的 ToolContext"""
    return ToolContext(
        user_id=str(user_id),
        conversation_id="conv-integration",
        agent_id=str(agent_id),
        db=db,
    )


def _enable_agent(db, agent_id, name, memory_long_term_config=None):
    """插入一个 memory_long_term_enabled=True 的 Agent"""
    agent = Agent(
        id=agent_id,
        name=name,
        description="integration test agent",
        system_prompt="sys",
        memory_long_term_enabled=True,
        memory_long_term_config=(
            memory_long_term_config if memory_long_term_config is not None else {}
        ),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _disable_agent(db, agent_id, name="disabled"):
    """插入一个 memory_long_term_enabled=False 的 Agent"""
    agent = Agent(
        id=agent_id,
        name=name,
        description="integration test agent (disabled)",
        system_prompt="sys",
        memory_long_term_enabled=False,
        memory_long_term_config={},
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


# ============================================================
# 1. 完整 write → read 流程
# ============================================================

@pytest.mark.asyncio
async def test_full_read_write_flow(test_db):
    """完整读写流程：write 写入 → read 读出，value / summary 一致"""
    _enable_agent(test_db, AGENT_INTEGRATION, "MemoryAgent")

    ctx = _make_ctx(test_db, AGENT_INTEGRATION, USER_INTEGRATION)
    write_tool = MemoryWriteTool()
    read_tool = MemoryReadTool()

    # 1. 写入
    write_result = await write_tool.execute(
        {
            "key": "user.favorites.colors",
            "value": {"primary": "blue", "secondary": "green"},
            "summary": "用户喜欢的颜色",
        },
        ctx,
    )
    assert write_result.success is True
    assert write_result.content["action"] == "created"
    assert write_result.content["key"] == "user.favorites.colors"

    # 2. 按 key 读取，验证 value 和 summary 都正确
    read_result = await read_tool.execute(
        {"key": "user.favorites.colors"},
        ctx,
    )
    assert read_result.success is True
    assert read_result.content["key"] == "user.favorites.colors"
    assert read_result.content["value"]["primary"] == "blue"
    assert read_result.content["value"]["secondary"] == "green"
    assert read_result.content["summary"] == "用户喜欢的颜色"
    assert read_result.content.get("updated_at")  # 非空时间戳

    # 3. 不传 key 读取列表：应能取回刚写入的条目
    # 返回格式：{"records": [...], "count": N}
    list_result = await read_tool.execute({}, ctx)
    assert list_result.success is True
    assert isinstance(list_result.content, dict)
    assert list_result.content["count"] == 1
    assert len(list_result.content["records"]) == 1
    record = list_result.content["records"][0]
    assert record["key"] == "user.favorites.colors"
    assert record["value"]["primary"] == "blue"
    assert record["summary"] == "用户喜欢的颜色"


# ============================================================
# 2. Agent.memory_long_term_config.max_entries 生效
# ============================================================

@pytest.mark.asyncio
async def test_max_entries_from_agent_config(test_db):
    """Agent.memory_long_term_config.max_entries 设置为 3 时，写入第 4 条被拒"""
    # max_entries=3 的 Agent
    _enable_agent(
        test_db,
        AGENT_INTEGRATION,
        "MemoryAgent",
        memory_long_term_config={"max_entries": 3},
    )

    ctx = _make_ctx(test_db, AGENT_INTEGRATION, USER_INTEGRATION)
    write_tool = MemoryWriteTool()

    # 前 3 条写入成功
    for i in range(3):
        r = await write_tool.execute({"key": f"k{i}", "value": {"i": i}}, ctx)
        assert r.success is True, f"第 {i + 1} 条应成功：{r.error_message}"
        assert r.content["action"] == "created"

    # 第 4 条被拒（提示包含配置值 "3"）
    r = await write_tool.execute({"key": "k_new", "value": {"i": 99}}, ctx)
    assert r.success is False
    assert "3" in (r.error_message or ""), (
        f"错误信息应提及配置值 3，实际：{r.error_message}"
    )

    # 验证 DB 中只有 3 条
    cnt = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_INTEGRATION,
            AgentMemoryLongTerm.user_id == USER_INTEGRATION,
        )
        .count()
    )
    assert cnt == 3, f"DB 中应为 3 条，实际 {cnt}"


# ============================================================
# 3. 更新已有条目不触发 max_entries
# ============================================================

@pytest.mark.asyncio
async def test_update_does_not_trigger_max_entries(test_db):
    """已有 key 再次写入 → action=updated，不计数也不抛错"""
    _enable_agent(
        test_db,
        AGENT_INTEGRATION,
        "MemoryAgent",
        memory_long_term_config={"max_entries": 2},
    )

    ctx = _make_ctx(test_db, AGENT_INTEGRATION, USER_INTEGRATION)
    write_tool = MemoryWriteTool()
    read_tool = MemoryReadTool()

    # 先写入 1 条
    r = await write_tool.execute({"key": "k0", "value": {"v": 1}}, ctx)
    assert r.success is True
    assert r.content["action"] == "created"

    # 再写一条（达到 max_entries=2 上限）
    r = await write_tool.execute({"key": "k1", "value": {"v": 1}}, ctx)
    assert r.success is True
    assert r.content["action"] == "created"

    # 此时再新增第 3 条应被拒
    r = await write_tool.execute({"key": "k2", "value": {"v": 1}}, ctx)
    assert r.success is False, "新增第 3 条应被 max_entries=2 拒绝"

    # 但更新已有 key 应允许（不触发 max_entries）
    r = await write_tool.execute({"key": "k0", "value": {"v": 2}}, ctx)
    assert r.success is True, f"更新已有 key 应允许：{r.error_message}"
    assert r.content["action"] == "updated"

    # 读取确认 value 已更新
    r = await read_tool.execute({"key": "k0"}, ctx)
    assert r.success is True
    assert r.content["value"] == {"v": 2}, f"k0 value 应为 {{v: 2}}，实际：{r.content}"

    # 仍能更新第二条（同样不触发限制）
    r = await write_tool.execute({"key": "k1", "value": {"v": 99}}, ctx)
    assert r.success is True
    assert r.content["action"] == "updated"


# ============================================================
# 4. user 隔离：user-1 写入的数据 user-2 完全读不到
# ============================================================

@pytest.mark.asyncio
async def test_user_isolation_end_to_end(test_db):
    """不同 user 的数据完全隔离：user-1 写、user-2 读不到"""
    # 共用同一 Agent（验证隔离完全按 user_id 切分）
    _enable_agent(test_db, AGENT_SHARED, "SharedAgent")

    ctx_u1 = _make_ctx(test_db, AGENT_SHARED, USER_1)
    ctx_u2 = _make_ctx(test_db, AGENT_SHARED, USER_2)

    write_tool = MemoryWriteTool()
    read_tool = MemoryReadTool()

    # user-1 写入一条记忆
    r = await write_tool.execute(
        {"key": "secret", "value": {"from": "user-1"}, "summary": "user-1 的秘密"},
        ctx_u1,
    )
    assert r.success is True

    # user-2 按相同 key 读取：value 应为 null
    r = await read_tool.execute({"key": "secret"}, ctx_u2)
    assert r.success is True
    assert r.content is not None
    assert r.content.get("value") is None, (
        f"user-2 不应看到 user-1 的数据，实际：{r.content}"
    )

    # user-2 列表查询：应为空（实际返回 {records: [], count: 0}）
    r = await read_tool.execute({}, ctx_u2)
    assert r.success is True
    assert r.content == {"records": [], "count": 0}, (
        f"user-2 列表应为空，实际：{r.content}"
    )

    # user-1 仍能看到自己的数据
    r = await read_tool.execute({"key": "secret"}, ctx_u1)
    assert r.success is True
    assert r.content["value"] == {"from": "user-1"}

    # user-2 写入同名 key 不影响 user-1 的记录
    r = await write_tool.execute(
        {"key": "secret", "value": {"from": "user-2"}},
        ctx_u2,
    )
    assert r.success is True

    # user-1 的原数据未变
    r = await read_tool.execute({"key": "secret"}, ctx_u1)
    assert r.content["value"] == {"from": "user-1"}

    # user-2 现在有自己的记录
    r = await read_tool.execute({"key": "secret"}, ctx_u2)
    assert r.content["value"] == {"from": "user-2"}

    # DB 中应该有 2 条（不同 user_id）
    cnt = (
        test_db.query(AgentMemoryLongTerm)
        .filter(
            AgentMemoryLongTerm.agent_id == AGENT_SHARED,
            AgentMemoryLongTerm.key == "secret",
        )
        .count()
    )
    assert cnt == 2


# ============================================================
# 5. Agent.memory_long_term_enabled=False → 工具不可用
# ============================================================

@pytest.mark.asyncio
async def test_disabled_agent_tools_unavailable(test_db):
    """Agent.memory_long_term_enabled=False 时，is_available 必须返回 False"""
    _disable_agent(test_db, AGENT_DISABLED, "DisabledAgent")

    ctx = _make_ctx(test_db, AGENT_DISABLED, USER_INTEGRATION)

    # is_available 应返回 False（两个工具均不可用）
    assert MemoryReadTool().is_available(ctx) is False
    assert MemoryWriteTool().is_available(ctx) is False

    # 即使绕过 is_available 直接 execute，agent 仍是 disabled 状态
    # 写入操作不应写入任何数据（disabled agent 没有写入权限约束在 is_available，
    # 此处仅验证 is_available 的行为；任务定义聚焦在 disabled agent 工具不可用）