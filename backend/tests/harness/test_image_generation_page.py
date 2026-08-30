"""图像生成页面后端测试（seed 端点 + SSE 转发 + 附件持久化）"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

USER_ID = str(uuid.uuid4())


@pytest.fixture
def env():
    from app.models.agent import Agent  # noqa: F401
    import app.models.harness_models  # noqa: F401
    from app.models.base import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


@pytest.fixture
def client(env):
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": USER_ID}
    yield TestClient(app)
    app.dependency_overrides.clear()


# ===========================================================================
# Seed 端点
# ===========================================================================


def test_image_gen_agent_seed_idempotent(client, env):
    """两次调用返回同一 agent，且属性正确（public / slug）"""
    from app.models.agent import Agent

    r1 = client.get("/api/v1/tools/image-generation/agent")
    assert r1.status_code == 200, r1.text
    body1 = r1.json()

    r2 = client.get("/api/v1/tools/image-generation/agent")
    body2 = r2.json()
    assert body1["agent_id"] == body2["agent_id"]

    agent = env.query(Agent).filter(Agent.id == uuid.UUID(body1["agent_id"])).first()
    assert agent is not None
    assert agent.slug == "image-generation-assistant"
    assert agent.visibility == "public"
    assert agent.is_active is True
    # system_prompt 强制多轮意图探究
    assert "禁止调用" in agent.system_prompt or "不要" in agent.system_prompt
    assert "image_gen" in agent.system_prompt


def test_image_gen_agent_seed_reactivates_disabled(client, env):
    """已存在但被禁用的种子 agent → 重新激活，不新建"""
    from app.models.agent import Agent
    from app.services.image_gen_agent import ensure_image_gen_agent

    first = ensure_image_gen_agent(env)
    first.is_active = False
    env.commit()

    again = ensure_image_gen_agent(env)
    assert again.id == first.id
    assert again.is_active is True
    assert env.query(Agent).count() == 1


# ===========================================================================
# chat_stream SSE 转发 tool 事件 + done 附件持久化
# ===========================================================================


@pytest.mark.asyncio
async def test_chat_stream_forwards_tool_events(env):
    """runtime 的 tool_call_start / tool_result 事件应被转发到 SSE"""
    # 构造 runtime.run 依次产出：tool_call_start → tool_result → done
    from app.services.harness.events import Event
    from app.services.harness.tool_protocol import Attachment, ToolCall, ToolResult

    fake_events = [
        Event.tool_call_start(ToolCall(id="t1", name="image_gen", arguments={"prompt": "猫"})),
        Event.tool_result(
            ToolCall(id="t1", name="image_gen", arguments={"prompt": "猫"}),
            ToolResult.json({"image_urls": ["https://x/a.png"]}),
        ),
        Event.done("图生成好了", usage={"total_tokens": 10}),
    ]

    async def _fake_run(user_message):
        for e in fake_events:
            yield e

    with patch("app.api.routes.chat_stream.AgentRuntime") as mock_rt_cls:
        rt_instance = MagicMock()
        rt_instance.run = _fake_run
        mock_rt_cls.return_value = rt_instance
        sse_text = await _drive_chat_stream(env)

    assert '"type": "tool_call_start"' in sse_text or '"type":"tool_call_start"' in sse_text
    assert '"type": "tool_result"' in sse_text or '"type":"tool_result"' in sse_text
    assert "image_gen" in sse_text
    # done 消息携带 attachments（本例无图片附件 → 空列表也应有字段）
    assert "attachments" in sse_text


async def _drive_chat_stream(env) -> str:
    """辅助：驱动 chat_stream SSE 并收集全部文本

    真实会话行 + mock quota 服务（避免真实配额检查）。
    """
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from app.models.conversation import Conversation
    from app.models.agent import Agent

    # chat_stream 无 agent_id 时回退 default agent——需要存在一个
    agent = Agent(name="default", description="", system_prompt="be helpful")
    agent.is_default = True
    env.add(agent)
    env.commit()

    conv = Conversation(user_id=USER_ID, title="t")
    env.add(conv)
    env.commit()
    env.refresh(conv)

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": USER_ID}
    try:
        with patch("app.api.routes.chat_stream.LLMQuotaService") as mock_quota_cls:
            quota_inst = MagicMock()
            quota_inst.check_and_reserve = MagicMock(return_value="res-1")
            quota_inst.record_usage = MagicMock()
            quota_inst.rollback = MagicMock()
            mock_quota_cls.return_value = quota_inst
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/conversations/{conv.id}/chat/stream",
                json={"content": "画一只猫"},
            )
            return resp.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_stream_persists_image_attachments(env):
    """image_gen 成功的 tool_result 的 attachments 应写入 done 的 agent 消息"""
    from app.services.harness.events import Event
    from app.services.harness.tool_protocol import Attachment, ToolCall, ToolResult

    attachments = [{"type": "image", "url": "https://x/cat.png", "name": "cat.png", "mime_type": "image/png"}]
    fake_events = [
        Event.tool_call_start(ToolCall(id="t1", name="image_gen", arguments={"prompt": "猫"})),
        Event.tool_result(
            ToolCall(id="t1", name="image_gen", arguments={"prompt": "猫"}),
            ToolResult.json(
                {"image_urls": ["https://x/cat.png"]},
                attachments=[Attachment(**a) for a in attachments],
            ),
        ),
        Event.done("已生成", usage={"total_tokens": 10}),
    ]

    async def _fake_run(user_message):
        for e in fake_events:
            yield e

    with patch("app.api.routes.chat_stream.AgentRuntime") as mock_rt_cls:
        rt_instance = MagicMock()
        rt_instance.run = _fake_run
        mock_rt_cls.return_value = rt_instance
        sse_text = await _drive_chat_stream(env)

    assert "https://x/cat.png" in sse_text
    # done 事件的 data.attachments 含该图片
    for line in sse_text.split("\n"):
        if line.startswith("data: ") and '"type": "done"' in line or '"type":"done"' in line:
            payload = json.loads(line[6:])
            atts = payload["data"].get("attachments") or []
            assert any(a["url"] == "https://x/cat.png" for a in atts)
            break


def test_message_to_dict_includes_attachments(env):
    """_message_to_dict 应透出 attachments 字段"""
    from app.api.routes.conversations import _message_to_dict
    from app.models.message import Message

    msg = Message(conversation_id=uuid.uuid4(), sender_type="agent", content="hi")
    msg.attachments = [{"type": "image", "url": "https://x/a.png"}]
    d = _message_to_dict(msg)
    assert d["attachments"] == [{"type": "image", "url": "https://x/a.png"}]


# ===========================================================================
# 会话创建支持 agent_id（conversations.agent_id NOT NULL 环境下的修复）
# ===========================================================================


def test_create_conversation_with_agent_id(client, env):
    """POST /conversations 带 agent_id → 落库"""
    from app.models.agent import Agent
    from app.models.conversation import Conversation

    agent = Agent(name="conv-agent", description="", system_prompt="x")
    env.add(agent)
    env.commit()
    env.refresh(agent)

    r = client.post(
        "/api/v1/conversations",
        json={"title": "t-agent", "agent_id": str(agent.id)},
    )
    assert r.status_code == 201, r.text
    conv = env.query(Conversation).filter_by(title="t-agent").first()
    assert conv is not None
    assert str(conv.agent_id) == str(agent.id)


def test_create_conversation_defaults_to_default_agent(client, env):
    """不带 agent_id → 回落默认 Agent（NOT NULL 约束兼容）"""
    from app.models.agent import Agent
    from app.models.conversation import Conversation

    agent = Agent(name="def-agent", description="", system_prompt="x")
    agent.is_default = True
    env.add(agent)
    env.commit()

    r = client.post("/api/v1/conversations", json={"title": "t-def"})
    assert r.status_code == 201, r.text
    conv = env.query(Conversation).filter_by(title="t-def").first()
    assert conv is not None
    assert conv.agent_id is not None


# ===========================================================================
# ctx.agent 绑定（image_gen 工具靠它解析图像模型链）
# ===========================================================================


@pytest.mark.asyncio
async def test_chat_stream_sets_ctx_agent(env):
    """chat_stream 构造 ToolContext 时必须绑定 agent（image_gen 依赖）"""
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from app.models.agent import Agent
    from app.models.conversation import Conversation
    from unittest.mock import patch

    agent = Agent(name="ctx-agent", description="", system_prompt="x")
    agent.is_default = True
    env.add(agent)
    env.commit()
    conv = Conversation(user_id=USER_ID, title="ctx", agent_id=agent.id)
    env.add(conv)
    env.commit()
    env.refresh(conv)

    captured = {}

    class FakeRT:
        def __init__(self, agent_arg, tool_registry, llm_bridge, session, ctx):
            captured["agent"] = agent_arg
            captured["ctx"] = ctx

        async def run(self, user_message):
            from app.services.harness.events import Event

            yield Event.done("ok", usage={"total_tokens": 1})

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": USER_ID}
    try:
        with patch("app.api.routes.chat_stream.AgentRuntime", FakeRT), patch(
            "app.api.routes.chat_stream.LLMQuotaService"
        ) as mq:
            qi = MagicMock()
            qi.check_and_reserve.return_value = "r"
            mq.return_value = qi
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/conversations/{conv.id}/chat/stream",
                json={"content": "hi"},
            )
            assert resp.status_code == 200, resp.text
    finally:
        app.dependency_overrides.clear()

    assert captured["ctx"].agent is captured["agent"], "ctx.agent 未绑定"


@pytest.mark.asyncio
async def test_chat_stream_prefers_conversation_agent(env):
    """请求未指定 agent_id 时，应使用会话绑定的 Agent（而非默认）"""
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from app.models.agent import Agent
    from app.models.conversation import Conversation
    from unittest.mock import patch

    bound = Agent(name="bound-agent", description="", system_prompt="BOUND")
    env.add(bound)
    env.commit()
    conv = Conversation(user_id=USER_ID, title="ca", agent_id=bound.id)
    env.add(conv)
    env.commit()
    env.refresh(conv)

    captured = {}

    class FakeRT:
        def __init__(self, agent_arg, *a, **kw):
            captured["agent"] = agent_arg

        async def run(self, user_message):
            from app.services.harness.events import Event

            yield Event.done("ok", usage={"total_tokens": 1})

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": USER_ID}
    try:
        with patch("app.api.routes.chat_stream.AgentRuntime", FakeRT), patch(
            "app.api.routes.chat_stream.LLMQuotaService"
        ) as mq:
            qi = MagicMock()
            qi.check_and_reserve.return_value = "r"
            mq.return_value = qi
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/conversations/{conv.id}/chat/stream",
                json={"content": "hi"},  # 不带 agent_id
            )
            assert resp.status_code == 200, resp.text
    finally:
        app.dependency_overrides.clear()

    assert str(captured["agent"].id) == str(bound.id)


# ===========================================================================
# v2: 图片转存 OSS（upload_bytes + chat_stream 注入）
# ===========================================================================


def test_oss_service_has_upload_bytes():
    """OssService 应提供 upload_bytes（provider 依赖的字节上传接口）"""
    from app.services.oss_service import OssService

    assert hasattr(OssService, "upload_bytes")


def test_upload_bytes_delegates_to_upload_file():
    """upload_bytes 包装 upload_file（BytesIO + size + uploaded_by=image-gen）"""
    import io

    from app.services.oss_service import OssService

    svc = OssService.__new__(OssService)  # 跳过 __init__ 的存储初始化
    captured = {}

    def fake_upload_file(object_name, data, size, content_type, uploaded_by="system", metadata=None):
        captured["object_name"] = object_name
        captured["data"] = data.read()
        captured["size"] = size
        captured["content_type"] = content_type
        captured["uploaded_by"] = uploaded_by
        return "https://oss.example.com/" + object_name

    svc.upload_file = fake_upload_file
    url = svc.upload_bytes("image-gen/abc.png", b"PNGDATA", "image/png")

    assert url == "https://oss.example.com/image-gen/abc.png"
    assert captured["object_name"] == "image-gen/abc.png"
    assert captured["data"] == b"PNGDATA"
    assert captured["size"] == 7
    assert captured["content_type"] == "image/png"
    assert captured["uploaded_by"] == "image-gen"


def test_upload_bytes_returns_none_on_storage_failure():
    """存储不可用（upload_file 返回 None）→ upload_bytes 返回 None（调用方降级）"""
    from app.services.oss_service import OssService

    svc = OssService.__new__(OssService)
    svc.upload_file = lambda *a, **kw: None
    assert svc.upload_bytes("image-gen/x.png", b"data", "image/png") is None


def test_chat_stream_injects_oss_service(env):
    """chat_stream 的 ToolContext 应注入 oss_service 单例"""
    from app.main import app
    from app.api.dependencies import get_db, get_current_user
    from app.models.agent import Agent
    from app.models.conversation import Conversation
    from unittest.mock import patch

    agent = Agent(name="oss-agent", description="", system_prompt="x")
    agent.is_default = True
    env.add(agent)
    env.commit()
    conv = Conversation(user_id=USER_ID, title="oss", agent_id=agent.id)
    env.add(conv)
    env.commit()
    env.refresh(conv)

    captured = {}

    class FakeRT:
        def __init__(self, agent_arg, tool_registry, llm_bridge, session, ctx):
            captured["ctx"] = ctx

        async def run(self, user_message):
            from app.services.harness.events import Event

            yield Event.done("ok", usage={"total_tokens": 1})

    def _override_db():
        yield env

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "user", "id": USER_ID}
    try:
        with patch("app.api.routes.chat_stream.AgentRuntime", FakeRT), patch(
            "app.api.routes.chat_stream.LLMQuotaService"
        ) as mq:
            qi = MagicMock()
            qi.check_and_reserve.return_value = "r"
            mq.return_value = qi
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/conversations/{conv.id}/chat/stream",
                json={"content": "hi"},
            )
            assert resp.status_code == 200, resp.text
    finally:
        app.dependency_overrides.clear()

    from app.services.oss_service import oss_service as oss_singleton

    assert captured["ctx"].oss_service is oss_singleton
