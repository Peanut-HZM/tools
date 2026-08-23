"""端到端测试：用户对话 3 轮后生成图片"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.dify_client import ChatRunResult


@pytest.fixture
def client():
    """TestClient + 通过 app.dependency_overrides 替换关键依赖。

    app.main 将 image_generation router 以 prefix='/api' 挂载，
    因此实际 URL 为 /api/image-generation/chat。
    FastAPI Depends() 在模块导入时已捕获依赖函数引用，
    必须用 app.dependency_overrides 才能替换（patch 模块属性无效）。
    """
    from app.routes import image_generation as img_gen_module
    from app.api.dependencies import get_current_user as real_get_current_user

    mock_svc = MagicMock()
    fake_user = {"id": "u1", "username": "t", "role": "user"}

    app.dependency_overrides[img_gen_module.get_image_gen_service] = lambda: mock_svc
    app.dependency_overrides[img_gen_module.get_current_user] = lambda: fake_user
    # 绕过真实 JWT 校验（image_generation 路由内部引用的也是这个）
    app.dependency_overrides[real_get_current_user] = lambda: fake_user

    return TestClient(app), mock_svc


def test_full_chat_flow_text2img(client):
    """完整流程：3 轮追问 → 第 3 轮生成图片"""
    test_client, mock_svc = client

    asking = ChatRunResult(conversation_id="conv-flow", answer="你想要什么风格？")
    asking2 = ChatRunResult(conversation_id="conv-flow", answer="在什么场景？")
    generated = ChatRunResult(
        conversation_id="conv-flow",
        answer="生成完成 <<GENERATE>>",
        image_urls=["https://x.com/a.png"],
        model_used="qwen-image-v1",
    )
    mock_svc.chat_generate = AsyncMock(side_effect=[asking, asking2, generated])

    # 轮次 1
    r1 = test_client.post("/api/image-generation/chat", data={
        "operation": "text2img", "prompt": "一只猫", "size": "1024x1024", "n": "1",
    })
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "asking"
    assert r1.json()["answer"] == "你想要什么风格？"

    # 轮次 2（带 conversation_id）
    r2 = test_client.post("/api/image-generation/chat", data={
        "operation": "text2img", "prompt": "卡通",
        "conversation_id": r1.json()["conversation_id"],
        "size": "1024x1024", "n": "1",
    })
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "asking"

    # 轮次 3（生图）
    r3 = test_client.post("/api/image-generation/chat", data={
        "operation": "text2img", "prompt": "在太空",
        "conversation_id": r1.json()["conversation_id"],
        "size": "1024x1024", "n": "1",
    })
    assert r3.status_code == 200, r3.text
    assert r3.json()["status"] == "generated"
    assert r3.json()["image_urls"] == ["https://x.com/a.png"]

    # 验证 service.chat_generate 被按顺序调用了 3 次
    assert mock_svc.chat_generate.call_count == 3