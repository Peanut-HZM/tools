"""测试 ChatRunResult dataclass"""
from app.services.dify_client import ChatRunResult


def test_chat_result_default_fields():
    """测试默认字段值（image_urls / model_used / polish_prompt 应有合理默认值）"""
    result = ChatRunResult(
        conversation_id="conv-1",
        answer="你想用什么风格？",
    )
    assert result.conversation_id == "conv-1"
    assert result.answer == "你想用什么风格？"
    assert result.image_urls == []
    assert result.model_used == ""
    assert result.polish_prompt == ""


def test_chat_result_full():
    """测试完整字段赋值"""
    result = ChatRunResult(
        conversation_id="conv-2",
        answer="生成完成",
        image_urls=["https://x.com/a.png"],
        model_used="qwen-image-v1",
        polish_prompt="A cat in space",
        raw_response={"x": 1},
    )
    assert result.image_urls == ["https://x.com/a.png"]
    assert result.model_used == "qwen-image-v1"
    assert result.polish_prompt == "A cat in space"
    assert result.raw_response == {"x": 1}
