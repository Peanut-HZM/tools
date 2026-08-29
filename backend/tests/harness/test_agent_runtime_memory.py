"""AgentRuntime 长期记忆自动注入测试

参考 Plan §Task 5: 验证 _retrieve_long_term_memory / _build_memory_block 行为，
以及 _build_messages_for_llm 注入 system prompt + memory block 的逻辑。
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.agent_runtime import AgentRuntime
from app.services.harness.memory_service import MemoryEntry
from app.services.harness.tool_protocol import ToolContext


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mock_agent():
    """构造支持长期记忆的 agent mock"""
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.name = "Memory Agent"
    agent.slug = "memory-agent"
    agent.is_active = True
    agent.memory_long_term_enabled = True
    agent.memory_long_term_config = {
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "auto_inject": True,
        "auto_inject_top_k": 5,
        "auto_inject_threshold": 0.7,
        "auto_inject_timeout_seconds": 5,
    }
    agent.system_prompt = "你是一个有用的助手。"
    agent.max_steps_per_turn = 10
    agent.memory_short_term_policy = "sliding_window"
    agent.memory_short_term_window = 20
    agent.input_guardrails = []
    agent.output_guardrails = []
    agent.error_strategy = "fallback_message"
    agent.can_handoff_to = []
    agent.default_model_id = "gpt-4"
    agent.fallback_model_ids = []
    agent.generation_params = {}
    agent.guardrail_on_violation = "block"
    return agent


@pytest.fixture
def runtime(mock_agent):
    """构造 AgentRuntime 实例"""
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = str(uuid.uuid4())
    ctx.agent_id = str(mock_agent.id)
    ctx.db = MagicMock()
    ctx.cancel_event = MagicMock()
    ctx.cancel_event.is_set = MagicMock(return_value=False)
    ctx.trace_recorder = MagicMock()
    ctx.trace_recorder.start_trace = MagicMock(return_value=MagicMock(id="trace-1"))
    ctx.trace_recorder.start_step = MagicMock()
    ctx.trace_recorder.end_step = MagicMock()
    ctx.trace_recorder.end_trace = MagicMock()

    session = MagicMock()
    session.messages = []
    session.conversation = MagicMock(id=uuid.uuid4())

    tool_registry = MagicMock()
    llm_bridge = MagicMock()

    return AgentRuntime(mock_agent, tool_registry, llm_bridge, session, ctx)


# ------------------------------------------------------------------
# _build_memory_block 测试
# ------------------------------------------------------------------

def test_build_memory_block_with_results(runtime):
    """有结果时生成 memory block"""
    entries = [
        MemoryEntry(key="pref_lang", value={"text": "中文"}, score=0.92, importance=0.8),
        MemoryEntry(key="name", value={"text": "小明"}, score=0.85, importance=0.7),
    ]
    block = runtime._build_memory_block(entries)
    assert "<long_term_memory>" in block
    assert "</long_term_memory>" in block
    assert "pref_lang" in block
    assert "name" in block
    assert "0.92" in block
    assert "中文" in block


def test_build_memory_block_empty(runtime):
    """空结果时返回空字符串"""
    block = runtime._build_memory_block([])
    assert block == ""


def test_build_memory_block_handles_non_dict_value(runtime):
    """非 dict value 时使用 JSON dump"""
    entries = [
        MemoryEntry(key="k", value=["a", "b"], score=0.5),
    ]
    block = runtime._build_memory_block(entries)
    assert "<long_term_memory>" in block
    assert "k" in block


# ------------------------------------------------------------------
# _retrieve_long_term_memory 测试
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_long_term_memory_success(runtime, mock_agent):
    """正常检索返回结果"""
    with patch("app.services.harness.memory_service.MemoryService") as mock_svc:
        instance = mock_svc.return_value
        instance.search = AsyncMock(return_value=[
            MemoryEntry(key="k1", value={"text": "v1"}, score=0.9)
        ])
        results = await runtime._retrieve_long_term_memory("你好")
        assert len(results) == 1
        assert results[0].key == "k1"


@pytest.mark.asyncio
async def test_retrieve_long_term_memory_disabled(runtime, mock_agent):
    """memory_long_term_enabled=False 时跳过（不调用 search）"""
    mock_agent.memory_long_term_enabled = False
    with patch("app.services.harness.memory_service.MemoryService") as mock_svc:
        instance = mock_svc.return_value
        instance.search = AsyncMock()
        results = await runtime._retrieve_long_term_memory("你好")
        assert results == []
        instance.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_retrieve_long_term_memory_auto_inject_disabled(runtime, mock_agent):
    """auto_inject=False 时跳过"""
    mock_agent.memory_long_term_config = {"auto_inject": False}
    with patch("app.services.harness.memory_service.MemoryService") as mock_svc:
        instance = mock_svc.return_value
        instance.search = AsyncMock()
        results = await runtime._retrieve_long_term_memory("你好")
        assert results == []
        instance.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_retrieve_long_term_memory_timeout(runtime):
    """search() 抛异常时返回空列表（best-effort）"""
    with patch("app.services.harness.memory_service.MemoryService") as mock_svc:
        instance = mock_svc.return_value
        instance.search = AsyncMock(side_effect=TimeoutError("vector search timeout"))
        results = await runtime._retrieve_long_term_memory("你好")
        assert results == []


@pytest.mark.asyncio
async def test_retrieve_long_term_memory_provider_failure(runtime, mock_agent):
    """embedding provider 创建失败时仍能降级（MemoryService 仍被实例化）"""
    mock_agent.memory_long_term_config = {
        "embedding_provider": "openai",
        "auto_inject": True,
    }
    with patch(
        "app.services.harness.embeddings.factory.create_embedding_provider",
        side_effect=ValueError("no api key"),
    ):
        with patch("app.services.harness.memory_service.MemoryService") as mock_svc:
            instance = mock_svc.return_value
            instance.search = AsyncMock(return_value=[
                MemoryEntry(key="k1", value={"text": "fallback"}, score=0.6)
            ])
            results = await runtime._retrieve_long_term_memory("你好")
            # 降级后仍然返回关键词搜索结果
            assert len(results) == 1


# ------------------------------------------------------------------
# _build_messages_for_llm 注入逻辑测试
# ------------------------------------------------------------------

def test_build_messages_for_llm_injects_system_prompt_and_memory(runtime, mock_agent):
    """_build_messages_for_llm 应在消息列表首部注入 system prompt + memory block"""
    # 准备 session.messages
    runtime.session.messages = [
        MagicMock(role="user", content="你好"),
        MagicMock(role="assistant", content="你好，有什么可以帮你的？"),
    ]

    # 模拟已预取的 memory block
    runtime._cached_memory_block = (
        "<long_term_memory>\n- [pref_lang]: 中文 (相关度: 0.92)\n</long_term_memory>"
    )

    msgs = runtime._build_messages_for_llm()

    # 第一条应该是 system
    assert msgs[0]["role"] == "system"
    # system content 应同时包含 agent.system_prompt 和 memory block
    assert "你是一个有用的助手。" in msgs[0]["content"]
    assert "<long_term_memory>" in msgs[0]["content"]
    assert "pref_lang" in msgs[0]["content"]
    # 后续消息保持不变
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"


def test_build_messages_for_llm_only_system_prompt(runtime, mock_agent):
    """无 memory block 时只注入 system prompt"""
    runtime.session.messages = [MagicMock(role="user", content="hello")]
    runtime._cached_memory_block = ""

    msgs = runtime._build_messages_for_llm()
    assert msgs[0]["role"] == "system"
    assert "你是一个有用的助手。" in msgs[0]["content"]
    assert "<long_term_memory>" not in msgs[0]["content"]


def test_build_messages_for_llm_only_memory_block(runtime, mock_agent):
    """system_prompt 为空但有 memory block 时，仅注入 memory block"""
    mock_agent.system_prompt = ""
    runtime.session.messages = [MagicMock(role="user", content="hello")]
    runtime._cached_memory_block = "<long_term_memory>\n- [k]: v\n</long_term_memory>"

    msgs = runtime._build_messages_for_llm()
    assert msgs[0]["role"] == "system"
    assert "<long_term_memory>" in msgs[0]["content"]
    # 仅有 memory block，没有多余的双换行
    assert msgs[0]["content"].startswith("<long_term_memory>")


def test_build_messages_for_llm_no_system_no_memory(runtime, mock_agent):
    """system_prompt 和 memory 都为空时，消息列表首位是 user"""
    mock_agent.system_prompt = ""
    runtime.session.messages = [MagicMock(role="user", content="hello")]
    runtime._cached_memory_block = ""

    msgs = runtime._build_messages_for_llm()
    # 没有 system 注入，首条是 user
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "hello"


def test_cached_memory_block_default_empty(runtime):
    """_cached_memory_block 实例属性默认值为空字符串"""
    assert runtime._cached_memory_block == ""