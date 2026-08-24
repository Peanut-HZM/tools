"""
Task 28 — 自研图像生成路径端到端测试（M9）

完整流程覆盖：
  POST /api/image-generation/chat (backend=selfdev)
    -> ImageGenService.chat_generate_dispatch_with_quota
       -> quota.reserve
       -> chat_generate_dispatch(backend="selfdev")
          -> BackendRegistry.get("selfdev")
          -> SelfDevelopedBackend.run(ctx)
             -> ConversationRepository.load  (查历史)
             -> AgentOrchestrator.run
                -> OrderedLLMGateway.generate(category="chat") # 第一次：tool_call
                -> ToolExecutor.execute
                   -> OrderedLLMGateway.generate(category="image_gen") -> fake bytes
                   -> OssService.upload_file + sign_url -> fake URL
                -> OrderedLLMGateway.generate(category="chat") # 第二次：final
             -> ConversationRepository.save  (持久化消息)
       -> quota.commit + history.create_record

外部 API 全部 mock：
  - OrderedLLMGateway.generate 按 category 区分返回
  - OssService.upload_file / sign_url 返回伪 URL
  - quota / history 全部 MagicMock

验证：响应 200，resp.backend="selfdev"，resp.image_urls 非空，resp.answer 非空。
"""

from __future__ import annotations

import sys
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

# SQLite 无 JSONB，降级为 JSON（与 test_image_gen_conversation_model.py 同模式）
@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
    return "JSON"


# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.dependencies import get_current_user as real_get_current_user
from app.models.base import Base
# 显式导入，确保 ImageGenSelfDevConversation 表注册到 Base.metadata
from app.models.image_gen_conversation import ImageGenSelfDevConversation  # noqa: F401
from app.routes import image_generation as img_gen_module
from app.services.image_gen.agent_orchestrator import AgentOrchestrator
from app.services.image_gen.backends import BackendRegistry
from app.services.image_gen.conversation_repo import ConversationRepository
from app.services.image_gen.dify_backend import DifyBackend
from app.services.image_gen.selfdev_backend import SelfDevelopedBackend
from app.services.image_gen.tool_executor import ToolExecutor
from app.services.image_generation_service import ImageGenService


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def reset_registry():
    """每个用例前后清空 BackendRegistry，避免串数据"""
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB（包含 ImageGenSelfDevConversation 表）

    使用 StaticPool + check_same_thread=False 让同步 SQLAlchemy session
    能跨线程访问 — FastAPI 的同步 TestClient 在 portal/worker 线程上跑请求。
    """
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def fake_user():
    """模拟 get_current_user 返回值"""
    return {"id": "u1", "username": "tester", "role": "user"}


@pytest.fixture
def mock_oss_service():
    """Mock OssService：upload_file 返回 True，sign_url 返回伪签名 URL"""
    oss = MagicMock()
    oss.upload_file = MagicMock(return_value=True)
    oss.sign_url = MagicMock(return_value="https://signed-oss.example.com/fake-image.png")
    return oss


@pytest.fixture
def mock_quota():
    """Mock quota_svc — reserve/commit/release 全部 no-op"""
    mock = MagicMock()
    mock.check_and_reserve = MagicMock()
    mock.commit = MagicMock()
    mock.release = MagicMock()
    return mock


@pytest.fixture
def mock_history():
    """Mock history_svc — create_record 返回带 id 的 MagicMock"""
    mock = MagicMock()
    mock.create_record = MagicMock(return_value=MagicMock(id="hist-1"))
    return mock


@pytest.fixture
def mock_gateway():
    """
    Mock OrderedLLMGateway，按 category 区分返回：

      - category="chat": 第一次返回 tool_call，第二次返回最终回答
      - category="image_gen": 返回 [b"fake-png-bytes"]

    真实 OrderedLLMGateway 在 AgentOrchestrator 中调用时透传 tools，
    在 ToolExecutor 中调用时透传 operation/prompt/size/n 等参数，
    所以这里用 **kwargs 接收即可。
    """
    gateway = MagicMock()

    # 第一次 chat 调用：返回 generate_image tool_call
    first_chat = MagicMock()
    first_chat.content = None
    first_chat.tool_calls = [
        {
            "id": "call_e2e_1",
            "name": "generate_image",
            "arguments": {
                "operation": "text2img",
                "prompt": "a cat sitting on a mat",
                "size": "1024x1024",
                "n": 1,
            },
        }
    ]

    # 第二次 chat 调用：返回最终回答（无 tool_call）
    second_chat = MagicMock()
    second_chat.content = "图像已为您生成，请查收"
    second_chat.tool_calls = []

    call_log = {"calls": []}

    async def fake_generate(**kwargs):
        """根据 category 路由到不同 mock 返回值"""
        category = kwargs.get("category")
        call_log["calls"].append(kwargs)
        if category == "text":
            # 第一次 tool_call，第二次 final
            if len([c for c in call_log["calls"] if c.get("category") == "text"]) == 1:
                return first_chat
            return second_chat
        if category == "image_gen":
            # 返回伪图片字节列表
            return [b"\x89PNG\r\n\x1a\n" + b"fake-image-data"]
        # 其他分类（理论上 selfdev 流程不会触发）抛错
        raise ValueError(f"未 mock 的 category: {category}")

    gateway.generate = AsyncMock(side_effect=fake_generate)
    gateway._call_log = call_log
    return gateway


@pytest.fixture
def conv_repo(db_session):
    """真实 ConversationRepository（依赖 db_session 中的表）"""
    return ConversationRepository(db=db_session)


@pytest.fixture
def orchestrator(mock_gateway):
    """真实 AgentOrchestrator，注入 mock gateway"""
    return AgentOrchestrator(gateway=mock_gateway, max_iterations=5)


@pytest.fixture
def executor(mock_gateway, mock_oss_service):
    """真实 ToolExecutor，注入 mock gateway + mock OSS"""
    return ToolExecutor(gateway=mock_gateway, oss_svc=mock_oss_service)


@pytest.fixture
def registered_backends(orchestrator, executor, conv_repo):
    """注册 DifyBackend 和 SelfDevelopedBackend 到 BackendRegistry"""
    # DifyBackend 仅占位，实际请求 backend=selfdev 不会调用
    dify_client = MagicMock()
    dify_client.chat_text2img = AsyncMock(
        return_value=MagicMock(
            image_urls=["https://placeholder/dify.png"],
            answer="dify-answer",
            conversation_id="cid-dify",
            model_used="dify-model",
        )
    )
    dify_backend = DifyBackend(dify_client=dify_client, oss_svc=MagicMock())
    BackendRegistry.register("dify", dify_backend)

    # SelfDevelopedBackend 使用真实 orchestrator + executor + conv_repo
    selfdev_backend = SelfDevelopedBackend(
        orchestrator=orchestrator,
        executor=executor,
        conv_repo=conv_repo,
    )
    BackendRegistry.register("selfdev", selfdev_backend)

    return {
        "dify": dify_backend,
        "selfdev": selfdev_backend,
    }


@pytest.fixture
def client(db_session, mock_quota, mock_history, fake_user, registered_backends):
    """
    构建轻量 TestClient，覆盖依赖：
      - get_current_user → fake_user
      - get_image_gen_service → 真实 ImageGenService（依赖全 mock）

    使用独立的 FastAPI 子应用而非 app.main.app，避免 lifespan 副作用。
    """
    svc = ImageGenService(
        db=db_session,
        dify_client=MagicMock(),
        quota_svc=mock_quota,
        oss_svc=MagicMock(),
        history_svc=mock_history,
        degradation_svc=MagicMock(),
        prompt_polisher=MagicMock(),
    )

    app = FastAPI()
    app.include_router(img_gen_module.router, prefix="/api")

    app.dependency_overrides[img_gen_module.get_current_user] = lambda: fake_user
    app.dependency_overrides[img_gen_module.get_image_gen_service] = lambda: svc
    app.dependency_overrides[real_get_current_user] = lambda: fake_user

    return TestClient(app)


@pytest.fixture
def auth_headers():
    """测试用 auth headers（dependency_overrides 已绕过 JWT 校验）"""
    return {"Authorization": "Bearer fake-token-for-test"}


# ============================================================
# 主用例
# ============================================================

def test_full_selfdev_flow(client, auth_headers, mock_quota, mock_history, mock_gateway, mock_oss_service):
    """
    端到端：用户输入 → brain 决定生成 → image_gen → OSS → 返回签名 URL

    验证点：
      - HTTP 200
      - resp.backend == "selfdev"
      - resp.image_urls 至少包含一个签名 URL
      - resp.answer 是非空文本
      - resp.conversation_id 已生成
      - resp.status == "generated"
      - quota.check_and_reserve / commit 被调用；release 未调用（成功路径）
      - history.create_record 被调用，并传入 backend="selfdev"
      - OrderedLLMGateway.generate 被调用至少 2 次（chat x2 + image_gen x1）
      - OssService.upload_file + sign_url 各被调用至少 1 次
    """
    resp = client.post(
        "/api/image-generation/chat",
        data={
            "backend": "selfdev",
            "operation": "text2img",
            "prompt": "a cat sitting on a mat",
            "size": "1024x1024",
            "n": 1,
        },
        headers=auth_headers,
    )

    # 1. 响应基本字段
    assert resp.status_code == 200, f"unexpected status: {resp.status_code} body={resp.text}"
    body = resp.json()

    assert body["backend"] == "selfdev", f"backend 应为 selfdev，实际: {body.get('backend')}"
    assert body["status"] == "generated", f"status 应为 generated，实际: {body.get('status')}"
    assert isinstance(body.get("image_urls"), list) and len(body["image_urls"]) >= 1, (
        f"image_urls 应非空，实际: {body.get('image_urls')}"
    )
    # 签名 URL 应来自 mock_oss_service.sign_url
    assert body["image_urls"][0].startswith("https://signed-oss"), (
        f"image_urls[0] 应为签名 URL，实际: {body['image_urls'][0]}"
    )
    assert isinstance(body.get("answer"), str) and len(body["answer"]) > 0, (
        f"answer 应非空，实际: {body.get('answer')}"
    )
    assert isinstance(body.get("conversation_id"), str) and len(body["conversation_id"]) > 0, (
        f"conversation_id 应非空，实际: {body.get('conversation_id')}"
    )

    # 2. quota 流程：reserve + commit 都应被调用，release 不应被调用（成功路径）
    mock_quota.check_and_reserve.assert_called_once()
    mock_quota.commit.assert_called_once()
    mock_quota.release.assert_not_called()

    # 3. history 应被写入，且 backend="selfdev"
    mock_history.create_record.assert_called_once()
    call_kwargs = mock_history.create_record.call_args.kwargs
    assert call_kwargs.get("backend") == "selfdev", (
        f"history.create_record 应传入 backend=selfdev，实际: {call_kwargs.get('backend')}"
    )
    assert call_kwargs.get("status") == "success"
    assert call_kwargs.get("operation") == "text2img"
    assert call_kwargs.get("prompt") == "a cat sitting on a mat"

    # 4. OrderedLLMGateway.generate 调用次数与分类
    #    期望：chat x2 + image_gen x1 = 3 次
    chat_calls = [c for c in mock_gateway._call_log["calls"] if c.get("category") == "text"]
    image_gen_calls = [c for c in mock_gateway._call_log["calls"] if c.get("category") == "image_gen"]
    assert len(chat_calls) == 2, f"text 应被调用 2 次（tool_call + final），实际: {len(chat_calls)}"
    assert len(image_gen_calls) == 1, f"image_gen 应被调用 1 次，实际: {len(image_gen_calls)}"

    # 5. OSS 上传 + 签名 URL 应被调用
    assert mock_oss_service.upload_file.call_count >= 1, "OssService.upload_file 应被调用"
    assert mock_oss_service.sign_url.call_count >= 1, "OssService.sign_url 应被调用"

    # 6. chat 第一次调用应包含 tools 参数（generate_image 工具定义）
    first_chat = chat_calls[0]
    assert "tools" in first_chat, "第一次 chat 调用应传入 tools 参数"
    assert isinstance(first_chat["tools"], list) and len(first_chat["tools"]) >= 1
    tool_names = [t.get("function", {}).get("name") for t in first_chat["tools"]]
    assert "generate_image" in tool_names, (
        f"tools 应包含 generate_image，实际: {tool_names}"
    )


def test_selfdev_flow_with_existing_conversation(
    client, auth_headers, conv_repo, mock_gateway, mock_oss_service
):
    """
    端到端：复用已有对话 ID（第二轮）

    流程：先调用一次生成对话，再用相同 conversation_id 调用。
    第二次请求中，ConversationRepository.load 应返回上轮消息，
    AgentOrchestrator 收到的 messages 应包含历史。

    验证点：
      - 第二次响应仍为 generated
      - 第二次 chat 调用时 messages 数 > 1（包含历史消息）
    """
    # 第一次调用：建立对话
    first_resp = client.post(
        "/api/image-generation/chat",
        data={
            "backend": "selfdev",
            "operation": "text2img",
            "prompt": "first prompt",
        },
        headers=auth_headers,
    )
    assert first_resp.status_code == 200
    conversation_id = first_resp.json()["conversation_id"]

    # 重置 call_log 以观察第二次请求的调用情况
    mock_gateway._call_log["calls"].clear()

    # 第二次调用：复用 conversation_id
    second_resp = client.post(
        "/api/image-generation/chat",
        data={
            "backend": "selfdev",
            "operation": "text2img",
            "prompt": "second prompt",
            "conversation_id": conversation_id,
        },
        headers=auth_headers,
    )

    assert second_resp.status_code == 200, second_resp.text
    second_body = second_resp.json()
    assert second_body["conversation_id"] == conversation_id, (
        f"conversation_id 应复用，实际: {second_body['conversation_id']} vs {conversation_id}"
    )
    assert second_body["status"] == "generated"
    assert len(second_body["image_urls"]) >= 1

    # 第一次 chat 调用（带 history 上下文）的 messages 应 > 1
    chat_calls = [c for c in mock_gateway._call_log["calls"] if c.get("category") == "text"]
    assert len(chat_calls) >= 1
    first_chat = chat_calls[0]
    assert "messages" in first_chat
    # 期望 messages 中至少包含：system + 第一轮 assistant + 当前 user = 3 条
    assert len(first_chat["messages"]) >= 2, (
        f"复用对话时 messages 应包含历史，实际: {len(first_chat['messages'])}"
    )