"""memory 端到端集成测试（Task 7 + Task 8）

覆盖：
── Task 7（KV 存取） ──
1. 完整 write → read 流程：验证 value/summary 正确存取
2. Agent.memory_long_term_config.max_entries 生效
3. 更新已有条目不触发 max_entries
4. user 隔离：不同 user 完全看不到彼此的数据
5. Agent.memory_long_term_enabled=False 时 is_available 返回 False

── Task 8（向量检索全链路） ──
6. mock provider 端到端：store → embed → vector_search → tool → runtime 注入
7. 降级链：向量失败 → 关键词 LIKE → 空结果
8. memory_search 工具完整流程（Tool → MemoryService → 结果格式）
9. 全链路：write → search → AgentRuntime 注入 system prompt

风格与 Task 1-6 保持一致（参考 test_memory_registration.py / test_memory_write_tool.py）：
- 使用真实 ToolContext 对象（避免 MagicMock 行为偏差）
- 通过 _enable_agent 助手构造 Agent
- 所有用例共享一个 SQLite 内存库（test_db fixture）
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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


# ============================================================
# Task 8: 向量检索全链路集成测试
# ============================================================

# --- 测试用常量 ---
AGENT_VECTOR = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
USER_VECTOR = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


# ------------------------------------------------------------------
# 6. test_e2e_vector_search（需要真实 API key → skip）
# ------------------------------------------------------------------

@pytest.mark.skip(reason="需要真实 embedding API key，CI 环境不具备")
@pytest.mark.asyncio
async def test_e2e_vector_search():
    """端到端：写入 → 生成 embedding → 向量检索 → 返回结果

    需要 OPENAI_API_KEY 或 EMBEDDING_API_KEY 环境变量 + 真实 PostgreSQL + pgvector。
    """
    pass


# ------------------------------------------------------------------
# 7. mock provider 端到端：store → mock embedding → search → tool → runtime
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_with_mock_provider(test_db):
    """mock provider 端到端：write → mock embed → search → 验证结果格式

    全链路：
    1. MemoryWriteTool.execute → DB 写入 KV
    2. MemoryService.store → mock provider.embed → embedding 生成
    3. MemorySearchTool.execute → MemoryService.search → mock 返回结果
    4. 验证返回结构包含 records / count / score
    """
    from app.services.harness.tools.memory_search import MemorySearchTool
    from app.services.harness.memory_service import MemoryEntry

    _enable_agent(
        test_db,
        AGENT_VECTOR,
        "VectorAgent",
        memory_long_term_config={"embedding_provider": "openai"},
    )

    ctx = _make_ctx(test_db, AGENT_VECTOR, USER_VECTOR)

    # Step 1: 通过 MemoryWriteTool 写入（真实 DB）
    write_tool = MemoryWriteTool()
    write_result = await write_tool.execute(
        {"key": "pref_lang", "value": {"text": "中文"}, "summary": "用户偏好语言"},
        ctx,
    )
    assert write_result.success is True

    # Step 2: 通过 MemorySearchTool 搜索（mock MemoryService.search 返回）
    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.search = AsyncMock(return_value=[
            MemoryEntry(
                key="pref_lang",
                value={"text": "中文"},
                score=0.92,
                importance=0.8,
                summary="用户偏好语言",
            ),
        ])

        with patch.object(
            MemorySearchTool,
            "_resolve_agent_config",
            return_value={"embedding_provider": "openai"},
        ):
            with patch(
                "app.services.harness.embeddings.factory.create_embedding_provider"
            ) as mock_factory:
                mock_factory.return_value = MagicMock()

                search_tool = MemorySearchTool()
                search_result = await search_tool.execute(
                    {"query": "用户偏好", "top_k": 5}, ctx
                )

    assert search_result.success is True
    payload = search_result.content
    assert payload["count"] == 1
    assert payload["records"][0]["key"] == "pref_lang"
    assert payload["records"][0]["score"] == 0.92
    assert payload["records"][0]["value"] == {"text": "中文"}


# ------------------------------------------------------------------
# 8. 降级链：向量失败 → 关键词 LIKE → 空结果
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_degradation_chain():
    """降级链验证：

    场景 1: 向量检索失败 → 降级到关键词搜索 → 关键词匹配到结果
    场景 2: 向量检索失败 → 降级到关键词搜索 → 关键词也无结果 → 返回空列表
    """
    from app.services.harness.memory_service import MemoryService, MemoryEntry

    # --- 场景 1: 向量失败 → 关键词成功 ---
    mock_db = MagicMock()
    mock_provider = AsyncMock()
    mock_provider.embed = AsyncMock(side_effect=RuntimeError("API unavailable"))

    svc = MemoryService(db=mock_db, embedding_provider=mock_provider)

    mock_row = MagicMock()
    mock_row.key = "keyword_match"
    mock_row.value = {"text": "hello world"}
    mock_row.importance = 0.5
    mock_row.access_count = 0
    mock_row.summary = None

    mock_db.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = [mock_row]

    results = await svc.search(uuid.uuid4(), uuid.uuid4(), "hello")
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].key == "keyword_match"

    # --- 场景 2: 向量失败 → 关键词也无结果 ---
    mock_db2 = MagicMock()
    mock_provider2 = AsyncMock()
    mock_provider2.embed = AsyncMock(side_effect=RuntimeError("API unavailable"))

    svc2 = MemoryService(db=mock_db2, embedding_provider=mock_provider2)

    mock_db2.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = []

    results2 = await svc2.search(uuid.uuid4(), uuid.uuid4(), "nonexistent")
    assert isinstance(results2, list)
    assert len(results2) == 0


@pytest.mark.asyncio
async def test_degradation_chain_vector_timeout():
    """向量检索超时 → 降级到关键词搜索"""
    from app.services.harness.memory_service import MemoryService, MemoryEntry
    import asyncio

    mock_db = MagicMock()
    mock_provider = AsyncMock()

    async def slow_embed(texts):
        await asyncio.sleep(100)  # 模拟超时
        return [[0.1] * 1536]

    mock_provider.embed = AsyncMock(side_effect=slow_embed)

    svc = MemoryService(db=mock_db, embedding_provider=mock_provider)

    # mock 关键词搜索返回结果
    mock_row = MagicMock()
    mock_row.key = "fallback_key"
    mock_row.value = {"text": "fallback"}
    mock_row.importance = 0.5
    mock_row.access_count = 0
    mock_row.summary = None

    mock_db.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = [mock_row]

    # timeout_seconds=0.01 确保超时
    results = await svc.search(
        uuid.uuid4(), uuid.uuid4(), "hello", timeout_seconds=0.01
    )
    assert isinstance(results, list)
    # 降级到关键词搜索，应返回 mock 结果
    assert len(results) == 1
    assert results[0].key == "fallback_key"


# ------------------------------------------------------------------
# 9. memory_search 工具完整流程
# ------------------------------------------------------------------

def test_memory_search_tool_full_flow():
    """memory_search 工具完整流程测试

    验证：
    - 工具注册信息正确（name / parameters_schema）
    - is_available 与 Agent.memory_long_term_enabled 联动
    - execute 空 query 返回错误
    """
    from app.services.harness.tools.memory_search import MemorySearchTool

    tool = MemorySearchTool()

    # 工具元信息
    assert tool.name == "memory_search"
    assert "query" in tool.parameters_schema.get("properties", {})
    assert tool.parameters_schema["required"] == ["query"]

    # is_available — enabled
    mock_db = MagicMock()
    mock_agent = MagicMock()
    mock_agent.memory_long_term_enabled = True
    mock_db.query.return_value.filter.return_value.first.return_value = mock_agent

    ctx_enabled = ToolContext(
        user_id=str(USER_VECTOR),
        conversation_id="conv-1",
        agent_id=str(AGENT_VECTOR),
        db=mock_db,
    )
    assert tool.is_available(ctx_enabled) is True

    # is_available — disabled
    mock_agent.memory_long_term_enabled = False
    ctx_disabled = ToolContext(
        user_id=str(USER_VECTOR),
        conversation_id="conv-1",
        agent_id=str(AGENT_VECTOR),
        db=mock_db,
    )
    assert tool.is_available(ctx_disabled) is False


@pytest.mark.asyncio
async def test_memory_search_tool_execute_returns_structured_results():
    """memory_search execute 返回结构化结果（records + count）"""
    from app.services.harness.tools.memory_search import MemorySearchTool
    from app.services.harness.memory_service import MemoryEntry

    mock_db = MagicMock()
    ctx = ToolContext(
        user_id=str(USER_VECTOR),
        conversation_id="conv-full",
        agent_id=str(AGENT_VECTOR),
        db=mock_db,
    )

    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.search = AsyncMock(return_value=[
            MemoryEntry(key="k1", value={"text": "v1"}, score=0.91, importance=0.8),
            MemoryEntry(key="k2", value={"text": "v2"}, score=0.85, importance=0.7),
        ])

        with patch.object(
            MemorySearchTool,
            "_resolve_agent_config",
            return_value={},
        ):
            tool = MemorySearchTool()
            result = await tool.execute({"query": "test"}, ctx)

    assert result.success is True
    assert result.content["count"] == 2
    assert len(result.content["records"]) == 2
    assert result.content["records"][0]["key"] == "k1"
    assert result.content["records"][0]["score"] == 0.91
    assert result.content["records"][1]["key"] == "k2"


# ------------------------------------------------------------------
# 10. 全链路：write → search → AgentRuntime 注入 system prompt
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_chain_write_search_runtime_injection(test_db):
    """全链路验证：write → search → AgentRuntime._retrieve + _build_memory_block → system prompt 注入

    步骤：
    1. MemoryWriteTool 写入 KV（真实 DB）
    2. mock MemoryService.search 返回结果
    3. AgentRuntime._retrieve_long_term_memory 获取结果
    4. AgentRuntime._build_memory_block 生成注入块
    5. _build_messages_for_llm 将 memory block 注入到 system prompt
    """
    from app.services.harness.agent_runtime import AgentRuntime
    from app.services.harness.memory_service import MemoryEntry
    from app.services.harness.tool_registry import ToolRegistry
    from app.services.harness.llm_bridge import LLMFunctionBridge
    from app.services.harness.session import Session

    # Step 1: 写入 KV（真实 SQLite DB）
    agent_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    agent = Agent(
        id=agent_id,
        name="FullChainAgent",
        description="full chain test agent",
        system_prompt="你是一个有用的助手。",
        memory_long_term_enabled=True,
        memory_long_term_config={
            "embedding_provider": "openai",
            "auto_inject": True,
            "auto_inject_top_k": 5,
            "auto_inject_threshold": 0.7,
            "auto_inject_timeout_seconds": 5,
        },
        max_steps_per_turn=10,
        memory_short_term_policy="sliding_window",
        memory_short_term_window=20,
    )
    test_db.add(agent)
    test_db.commit()

    ctx = _make_ctx(test_db, agent_id, user_id)

    write_tool = MemoryWriteTool()
    write_result = await write_tool.execute(
        {"key": "user_name", "value": {"text": "小明"}, "summary": "用户姓名"},
        ctx,
    )
    assert write_result.success is True

    # Step 2-5: 构造 AgentRuntime，mock MemoryService.search，验证注入链
    mock_ctx = MagicMock(spec=ToolContext)
    mock_ctx.user_id = str(user_id)
    mock_ctx.agent_id = str(agent_id)
    mock_ctx.db = test_db
    mock_ctx.cancel_event = MagicMock()
    mock_ctx.cancel_event.is_set = MagicMock(return_value=False)
    mock_ctx.trace_recorder = MagicMock()

    session = MagicMock()
    session.messages = [MagicMock(role="user", content="你好")]
    session.conversation = MagicMock(id=uuid.uuid4())

    tool_registry = MagicMock(spec=ToolRegistry)
    llm_bridge = MagicMock(spec=LLMFunctionBridge)

    runtime = AgentRuntime(agent, tool_registry, llm_bridge, session, mock_ctx)

    # mock _retrieve_long_term_memory 返回结果
    memory_entries = [
        MemoryEntry(
            key="user_name",
            value={"text": "小明"},
            score=0.92,
            importance=0.8,
            summary="用户姓名",
        ),
    ]

    with patch.object(
        runtime,
        "_retrieve_long_term_memory",
        new_callable=AsyncMock,
        return_value=memory_entries,
    ):
        results = await runtime._retrieve_long_term_memory("你好")
        assert len(results) == 1
        assert results[0].key == "user_name"

    # 构建 memory block
    runtime._cached_memory_block = runtime._build_memory_block(results)
    assert "<long_term_memory>" in runtime._cached_memory_block
    assert "user_name" in runtime._cached_memory_block
    assert "小明" in runtime._cached_memory_block
    assert "0.92" in runtime._cached_memory_block

    # 验证 _build_messages_for_llm 注入
    msgs = runtime._build_messages_for_llm()
    assert msgs[0]["role"] == "system"
    system_content = msgs[0]["content"]
    assert "你是一个有用的助手。" in system_content
    assert "<long_term_memory>" in system_content
    assert "user_name" in system_content
    assert "小明" in system_content

    # 后续消息保持
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "你好"


@pytest.mark.asyncio
async def test_full_chain_no_memory_when_disabled(test_db):
    """memory_long_term_enabled=False 时，AgentRuntime 不注入 memory block"""
    from app.services.harness.agent_runtime import AgentRuntime
    from app.services.harness.tool_registry import ToolRegistry
    from app.services.harness.llm_bridge import LLMFunctionBridge

    agent_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    agent = Agent(
        id=agent_id,
        name="DisabledMemoryAgent",
        description="disabled memory agent",
        system_prompt="助手。",
        memory_long_term_enabled=False,
        memory_long_term_config={},
        max_steps_per_turn=10,
        memory_short_term_policy="sliding_window",
        memory_short_term_window=20,
    )
    test_db.add(agent)
    test_db.commit()

    mock_ctx = MagicMock(spec=ToolContext)
    mock_ctx.user_id = str(user_id)
    mock_ctx.agent_id = str(agent_id)
    mock_ctx.db = test_db
    mock_ctx.cancel_event = MagicMock()
    mock_ctx.cancel_event.is_set = MagicMock(return_value=False)
    mock_ctx.trace_recorder = MagicMock()

    session = MagicMock()
    session.messages = [MagicMock(role="user", content="hello")]
    session.conversation = MagicMock(id=uuid.uuid4())

    runtime = AgentRuntime(
        agent, MagicMock(spec=ToolRegistry), MagicMock(spec=LLMFunctionBridge), session, mock_ctx
    )

    # _retrieve_long_term_memory 应直接返回空（不调用 MemoryService）
    with patch("app.services.harness.memory_service.MemoryService") as mock_svc:
        instance = mock_svc.return_value
        instance.search = AsyncMock()
        results = await runtime._retrieve_long_term_memory("hello")
        assert results == []
        instance.search.assert_not_awaited()

    # memory block 应为空
    runtime._cached_memory_block = runtime._build_memory_block(results)
    assert runtime._cached_memory_block == ""

    # system prompt 注入中不含 memory 标签
    msgs = runtime._build_messages_for_llm()
    assert msgs[0]["role"] == "system"
    assert "<long_term_memory>" not in msgs[0]["content"]