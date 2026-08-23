"""测试 chat_generate：编排 chat_* + OSS + 历史写入"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.image_generation_service import ImageGenService
from app.services.dify_client import ChatRunResult


@pytest.fixture
def fake_components():
    return {
        "db": MagicMock(),
        "dify_client": MagicMock(),
        "quota_svc": MagicMock(),
        "oss_svc": MagicMock(),
        "history_svc": MagicMock(),
    }


@pytest.mark.asyncio
async def test_chat_generate_asking_no_quota_deduct(fake_components):
    """追问不生成时，不扣配额，不写历史"""
    fake_components["dify_client"].chat_text2img = AsyncMock(
        return_value=ChatRunResult(
            conversation_id="conv-1",
            answer="你想要什么风格？",
        )
    )

    svc = ImageGenService(
        db=fake_components["db"],
        dify_client=fake_components["dify_client"],
        quota_svc=fake_components["quota_svc"],
        oss_svc=fake_components["oss_svc"],
        history_svc=fake_components["history_svc"],
    )
    result = await svc.chat_generate(
        user_id="u1",
        operation="text2img",
        prompt="一只猫",
        conversation_id=None,
        params={"size": "1024x1024", "n": 1, "style": "auto", "model_preference": "auto"},
        reference_bytes=None,
        mask_bytes=None,
        edit_type=None,
    )

    assert result.answer == "你想要什么风格？"
    assert result.image_urls == []
    # 不应扣配额
    fake_components["quota_svc"].check_and_reserve.assert_not_called()
    # 不应写历史
    fake_components["history_svc"].create_record.assert_not_called()


@pytest.mark.asyncio
async def test_chat_generate_triggers_quota_and_history(fake_components):
    """<<GENERATE>> 触发时扣配额、写历史（带 conversation_id）"""
    fake_components["dify_client"].chat_text2img = AsyncMock(
        return_value=ChatRunResult(
            conversation_id="conv-2",
            answer="生成完成 <<GENERATE>>",
            image_urls=["https://x.com/a.png"],
            model_used="qwen-image-v1",
        )
    )
    fake_components["quota_svc"].check_and_reserve = MagicMock()
    fake_components["history_svc"].create_record = MagicMock(return_value=MagicMock(id="hist-1"))
    fake_components["oss_svc"].upload_file = MagicMock()
    fake_components["oss_svc"].sign_url = MagicMock(return_value="https://oss/signed.png")
    fake_components["db"].commit = MagicMock()

    svc = ImageGenService(**fake_components)
    # patch _upload_to_oss + _download_image 简化
    svc._upload_to_oss = MagicMock(side_effect=["ref-key", "result-key"])
    svc._download_image = AsyncMock(return_value=b"img-bytes")

    result = await svc.chat_generate(
        user_id="u1",
        operation="text2img",
        prompt="猫",
        conversation_id="conv-1",
        params={"size": "1024x1024", "n": 1, "style": "auto", "model_preference": "auto"},
        reference_bytes=None,
        mask_bytes=None,
        edit_type=None,
    )

    fake_components["quota_svc"].check_and_reserve.assert_called_once()
    create_kwargs = fake_components["history_svc"].create_record.call_args.kwargs
    assert create_kwargs["conversation_id"] == "conv-2"  # 历史记录带 conversation_id
