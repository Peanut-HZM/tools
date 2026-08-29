"""增强版 memory 工具测试（Phase 3 Plan-1B / Task 4）

覆盖：
1. memory_write 写入时自动调用 MemoryService.store 生成 embedding
2. memory_search 返回检索结果（含 records/count 字段）
3. memory_search 空 query 返回错误
4. memory_search.is_available 与 Agent.memory_long_term_enabled 联动
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.memory_search import MemorySearchTool
from app.services.harness.tools.memory_write import MemoryWriteTool


# === 测试用常量 ===
AGENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USER_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _make_ctx(db=None, agent_id=None, user_id=None):
    """构造 ToolContext（可注入 mock db）"""
    return ToolContext(
        user_id=str(user_id or USER_ID),
        conversation_id="conv-search-test",
        agent_id=str(agent_id or AGENT_ID),
        db=db if db is not None else MagicMock(),
    )


# ============================================================
# 1. memory_write 增强 — 自动生成 embedding
# ============================================================

@pytest.mark.asyncio
async def test_memory_write_generates_embedding():
    """memory_write 写入时自动调用 MemoryService.store 生成 embedding。

    通过 mock MemoryService 验证：
    - MemoryService 实例被创建
    - MemoryService.store 被 await 调用
    - execute 返回 success=True
    """
    # mock DB：query.filter.first 返回 None（不存在记录 → 走 created 分支）
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    ctx = _make_ctx(db=mock_db)

    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.store = AsyncMock()

        # mock embedding provider 配置存在 → 走 embedding 分支
        with patch.object(
            MemoryWriteTool,
            "_resolve_agent_config",
            return_value={"embedding_provider": "openai"},
        ):
            with patch(
        "app.services.harness.embeddings.factory.create_embedding_provider"
    ) as mock_factory:
                mock_factory.return_value = MagicMock()

                tool = MemoryWriteTool()
                result = await tool.execute(
                    {
                        "key": "test_key",
                        "value": {"text": "hello"},
                        "importance": 0.8,
                    },
                    ctx,
                )

    # 验证返回成功
    assert result.success is True
    # 验证 MemoryService.store 被调用过一次
    assert mock_svc.store.call_count == 1
    # 验证 call 参数：包含 importance=0.8
    call_args = mock_svc.store.call_args
    # call_args.args 位置参数: (agent_uuid, user_uuid, key, value, importance)
    assert call_args.args[2] == "test_key"  # key
    assert call_args.args[3] == {"text": "hello"}  # value
    # importance 通过 keyword 或位置传，宽松断言
    assert call_args.kwargs.get("importance") == 0.8 or (
        len(call_args.args) > 4 and call_args.args[4] == 0.8
    )


@pytest.mark.asyncio
async def test_memory_write_embedding_failure_does_not_fail_write():
    """embedding 生成失败时，写入仍然成功（best-effort）"""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    ctx = _make_ctx(db=mock_db)

    # MemoryService.store 抛异常 → 应被捕获，不影响 KV 已保存的结果
    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.store = AsyncMock(side_effect=RuntimeError("API down"))

        with patch.object(
            MemoryWriteTool,
            "_resolve_agent_config",
            return_value={"embedding_provider": "openai"},
        ):
            with patch(
        "app.services.harness.embeddings.factory.create_embedding_provider"
    ) as mock_factory:
                mock_factory.return_value = MagicMock()

                tool = MemoryWriteTool()
                result = await tool.execute(
                    {"key": "k", "value": {"text": "v"}},
                    ctx,
                )

    # KV 已 commit，execute 应返回成功
    assert result.success is True
    assert result.content_type == "json"


@pytest.mark.asyncio
async def test_memory_write_no_embedding_provider_skips_embedding():
    """未配置 embedding_provider 时跳过 embedding 调用"""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    ctx = _make_ctx(db=mock_db)

    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.store = AsyncMock()

        with patch.object(
            MemoryWriteTool,
            "_resolve_agent_config",
            return_value={},  # 无 embedding_provider
        ):
            tool = MemoryWriteTool()
            result = await tool.execute(
                {"key": "k", "value": {"text": "v"}},
                ctx,
            )

    assert result.success is True
    # 未配置 embedding_provider → MemoryService.store 不应被调用
    mock_svc.store.assert_not_called()


# ============================================================
# 2. memory_search — 检索结果
# ============================================================

@pytest.mark.asyncio
async def test_memory_search_returns_results():
    """memory_search 正常返回检索结果（records + count）"""
    mock_db = MagicMock()

    ctx = _make_ctx(db=mock_db)

    # mock MemoryEntry
    mock_entry = MagicMock()
    mock_entry.key = "test_key"
    mock_entry.value = {"text": "hello"}
    mock_entry.score = 0.9123
    mock_entry.summary = None

    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.search = AsyncMock(return_value=[mock_entry])

        with patch.object(
            MemorySearchTool,
            "_resolve_agent_config",
            return_value={},  # 无 provider → MemoryService 走关键词
        ):
            tool = MemorySearchTool()
            result = await tool.execute({"query": "hello", "top_k": 5}, ctx)

    assert result.success is True
    assert result.content_type == "json"

    # 验证返回结构包含 records 和 count
    payload = result.content
    assert "records" in payload
    assert "count" in payload
    assert payload["count"] == 1
    assert len(payload["records"]) == 1

    record = payload["records"][0]
    assert record["key"] == "test_key"
    assert record["value"] == {"text": "hello"}
    # score 应该被四舍五入到 4 位小数
    assert record["score"] == 0.9123
    assert "summary" in record


@pytest.mark.asyncio
async def test_memory_search_empty_query_returns_error():
    """空 query 返回错误"""
    mock_db = MagicMock()
    ctx = _make_ctx(db=mock_db)

    tool = MemorySearchTool()

    # 空字符串
    result = await tool.execute({"query": ""}, ctx)
    assert result.success is False
    assert "query" in (result.error_message or "")

    # 纯空格
    result2 = await tool.execute({"query": "   "}, ctx2 := _make_ctx(db=mock_db))
    assert result2.success is False

    # 缺失 query 字段
    result3 = await tool.execute({}, ctx3 := _make_ctx(db=mock_db))
    assert result3.success is False

    # 非字符串类型
    result4 = await tool.execute({"query": 123}, ctx4 := _make_ctx(db=mock_db))
    assert result4.success is False


@pytest.mark.asyncio
async def test_memory_search_top_k_default():
    """未传 top_k 时使用默认值 5"""
    mock_db = MagicMock()
    ctx = _make_ctx(db=mock_db)

    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.search = AsyncMock(return_value=[])

        with patch.object(
            MemorySearchTool,
            "_resolve_agent_config",
            return_value={},
        ):
            tool = MemorySearchTool()
            result = await tool.execute({"query": "hello"}, ctx)

    assert result.success is True
    # 验证 MemoryService.search 被以 top_k=5 调用
    call_args = mock_svc.search.call_args
    assert call_args.kwargs.get("top_k") == 5


@pytest.mark.asyncio
async def test_memory_search_top_k_invalid_falls_back():
    """top_k 无效时回退为默认值 5"""
    mock_db = MagicMock()
    ctx = _make_ctx(db=mock_db)

    with patch(
        "app.services.harness.memory_service.MemoryService"
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.search = AsyncMock(return_value=[])

        with patch.object(
            MemorySearchTool,
            "_resolve_agent_config",
            return_value={},
        ):
            tool = MemorySearchTool()
            # top_k=0 → 应回退为 5
            result = await tool.execute({"query": "hi", "top_k": 0}, ctx)
            # top_k="5" 字符串 → 应回退为 5
            result2 = await tool.execute({"query": "hi", "top_k": "5"}, ctx)

    assert result.success is True
    assert result2.success is True
    # 两次调用都应使用默认 top_k=5
    assert mock_svc.search.call_args_list[0].kwargs.get("top_k") == 5
    assert mock_svc.search.call_args_list[1].kwargs.get("top_k") == 5


# ============================================================
# 3. memory_search.is_available
# ============================================================

def test_memory_search_is_available_when_enabled():
    """Agent.memory_long_term_enabled=True 时 memory_search 可用"""
    mock_db = MagicMock()

    # 构造 Agent mock
    mock_agent = MagicMock()
    mock_agent.memory_long_term_enabled = True

    # db.query(Agent).filter(...).first() → mock_agent
    mock_db.query.return_value.filter.return_value.first.return_value = mock_agent

    ctx = ToolContext(
        user_id=str(USER_ID),
        conversation_id="conv-1",
        agent_id=str(AGENT_ID),
        db=mock_db,
    )

    tool = MemorySearchTool()
    assert tool.is_available(ctx) is True


def test_memory_search_is_available_when_disabled():
    """Agent.memory_long_term_enabled=False 时 memory_search 不可用"""
    mock_db = MagicMock()

    mock_agent = MagicMock()
    mock_agent.memory_long_term_enabled = False

    mock_db.query.return_value.filter.return_value.first.return_value = mock_agent

    ctx = ToolContext(
        user_id=str(USER_ID),
        conversation_id="conv-1",
        agent_id=str(AGENT_ID),
        db=mock_db,
    )

    tool = MemorySearchTool()
    assert tool.is_available(ctx) is False


def test_memory_search_is_available_agent_not_found():
    """Agent 不存在时不可用"""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    ctx = ToolContext(
        user_id=str(USER_ID),
        conversation_id="conv-1",
        agent_id=str(AGENT_ID),
        db=mock_db,
    )

    tool = MemorySearchTool()
    assert tool.is_available(ctx) is False


def test_memory_search_is_available_missing_db():
    """ctx.db 缺失时不可用（保守拒绝）"""
    ctx = ToolContext(
        user_id=str(USER_ID),
        conversation_id="conv-1",
        agent_id=str(AGENT_ID),
        db=None,
    )

    tool = MemorySearchTool()
    assert tool.is_available(ctx) is False


def test_memory_search_is_available_invalid_agent_id():
    """agent_id 无效时不可用"""
    ctx = ToolContext(
        user_id=str(USER_ID),
        conversation_id="conv-1",
        agent_id="not-a-uuid",
        db=MagicMock(),
    )

    tool = MemorySearchTool()
    assert tool.is_available(ctx) is False