"""
Task 5.1 — ImageGenService + ImageGenHistoryService 单元测试

覆盖范围（12 个用例）：
  1. test_generate_text2img_success — 成功路径
  2. test_generate_with_polish — 提示词润色
  3. test_generate_dify_failure_releases_quota — Dify 失败释放配额
  4. test_generate_timeout_releases_quota — 超时释放配额
  5. test_generate_cancelled_releases_quota — 取消释放配额
  6. test_generate_no_quota_raises — 无配额抛异常
  7. test_generate_service_degraded_raises — 降级拒绝请求
  8. test_generate_img2img_uploads_reference — img2img 上传参考图
  9. test_generate_inpaint_uploads_reference_and_mask — inpaint 上传参考图+蒙版
  10. test_history_service_crud — 历史记录增删改查
  11. test_history_cleanup_before_by_date — 按日期清理
  12. test_history_cleanup_by_unused_for_n_days — 按未访问天数清理
"""

from __future__ import annotations

import asyncio
import sys
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image_generation_models import ImageGenHistory
from app.core.exceptions import DifyError, QuotaExceeded, ServiceDegraded
from app.services.dify_client import DifyRunResult

# 确保 backend 目录在 sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.image_generation_service import ImageGenService, GenerationResult
from app.services.image_gen_history_service import ImageGenHistoryService
from app.utils.image_gen_constants import (
    OPERATION_TEXT2IMG,
    OPERATION_IMG2IMG,
    OPERATION_INPAINT,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_CANCELLED,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_dify_client():
    """模拟 DifyClient"""
    client = MagicMock()
    client.run_text2img = AsyncMock()
    client.run_img2img = AsyncMock()
    client.run_inpaint = AsyncMock()
    client.run_upload_edit = AsyncMock()
    return client


@pytest.fixture
def mock_oss_svc():
    """
    模拟 OSS 服务。

    跟踪 upload_file 调用；sign_url 返回可预测的签名 URL。
    """
    svc = MagicMock()
    svc.upload_file = MagicMock(return_value="ok")
    # sign_url 返回可预测的 URL，便于断言
    svc.sign_url = MagicMock(side_effect=lambda method, key, expires: f"https://oss.example.com/{key}?expires={expires}")
    svc.download_file = MagicMock(return_value=b"")
    return svc


@pytest.fixture
def mock_quota_svc():
    """模拟配额服务（已迁移到 LLMQuotaService 的 reservation_id 模式）"""
    svc = MagicMock()
    # check_and_reserve 返回 reservation_id，供 record_usage/rollback 使用
    svc.check_and_reserve = MagicMock(return_value="test-reservation-id")
    svc.record_usage = MagicMock()
    svc.rollback = MagicMock()
    return svc


@pytest.fixture
def mock_degradation_svc():
    """模拟降级服务"""
    svc = MagicMock()
    svc.is_degraded = MagicMock(return_value=False)
    svc.record_failure = MagicMock()
    svc.reset_failure_count = MagicMock()
    return svc


@pytest.fixture
def mock_prompt_polisher():
    """模拟提示词润色器"""
    polisher = AsyncMock()
    polisher.polish = AsyncMock(side_effect=lambda prompt: f"[polished] {prompt}")
    return polisher


@pytest.fixture
def history_svc(db_session, mock_oss_svc):
    """真实的 ImageGenHistoryService（基于 SQLite）"""
    return ImageGenHistoryService(db=db_session, oss_svc=mock_oss_svc)


def _make_dify_result(n: int = 1) -> DifyRunResult:
    """生成模拟的 DifyRunResult"""
    return DifyRunResult(
        image_urls=[f"https://dify.example.com/img_{i}.png" for i in range(n)],
        model_used="test-model-v1",
        raw_response={"status": "succeeded"},
        elapsed_seconds=2.5,
    )


def _make_uid() -> str:
    """生成测试用 user_id"""
    return str(uuid.uuid4())


def _build_service(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc=None,
    mock_prompt_polisher=None,
) -> ImageGenService:
    """构建 ImageGenService 实例"""
    return ImageGenService(
        db=db_session,
        dify_client=mock_dify_client,
        quota_svc=mock_quota_svc,
        oss_svc=mock_oss_svc,
        history_svc=history_svc,
        degradation_svc=mock_degradation_svc,
        prompt_polisher=mock_prompt_polisher,
    )


# ============================================================
# 辅助：mock httpx 下载（避免真实 HTTP 请求）
# ============================================================

class _FakeResp:
    """模拟 httpx 响应"""
    def __init__(self, content: bytes = b"\x89PNG\r\n\x1a\nfake-image"):
        self.content = content
        self.status_code = 200

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    """模拟 httpx.AsyncClient 上下文管理器"""
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url, **kwargs):
        return _FakeResp()


# ============================================================
# 1. text2img 成功路径
# ============================================================

@pytest.mark.asyncio
async def test_generate_text2img_success(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """
    text2img 成功：DifyClient 返回 1 张图。
    验证：
      - OSS upload_file 调用 1 次（仅结果图；text2img 无参考图）
      - DifyClient.run_text2img 参数正确
      - 配额 commit 被调用
      - 历史 status=success
    """
    dify_result = _make_dify_result(n=1)
    mock_dify_client.run_text2img.return_value = dify_result

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    with patch("httpx.AsyncClient", _FakeAsyncClient):
        result = await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="a cute cat",
            size="1024x1024",
            n=1,
            style="natural",
            model_preference="auto",
        )

    # 验证返回结构
    assert isinstance(result, GenerationResult)
    assert result.operation == OPERATION_TEXT2IMG
    assert result.prompt == "a cute cat"
    assert result.model_used == "test-model-v1"
    assert len(result.image_urls) == 1
    assert "image-gen/result/" in result.image_urls[0]
    assert result.duration_ms >= 0

    # DifyClient 参数正确
    mock_dify_client.run_text2img.assert_called_once_with(
        prompt="a cute cat",
        size="1024x1024",
        n=1,
        style="natural",
        model_preference="auto",
        user_id="test-user",
    )

    # OSS: text2img 无参考图 → 仅 1 次 upload（结果图）
    assert mock_oss_svc.upload_file.call_count == 1
    upload_call = mock_oss_svc.upload_file.call_args
    assert "image-gen/result/" in upload_call.kwargs["object_name"]

    # 配额 commit
    mock_quota_svc.check_and_reserve.assert_called_once_with(
        user_id="test-user", category="image", planned_tokens=0,
    )
    mock_quota_svc.record_usage.assert_called_once()
    mock_quota_svc.rollback.assert_not_called()

    # 降级计数重置
    mock_degradation_svc.reset_failure_count.assert_called_once()

    # 历史记录
    history = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.id == result.history_id,
    ).one()
    assert history.status == STATUS_SUCCESS
    assert history.user_id == "test-user"
    assert history.operation == OPERATION_TEXT2IMG
    assert history.prompt == "a cute cat"
    assert history.result_oss_key != ""
    assert history.model_used == "test-model-v1"


# ============================================================
# 2. 提示词润色
# ============================================================

@pytest.mark.asyncio
async def test_generate_with_polish(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
    mock_prompt_polisher,
):
    """polish_prompt=True + PromptPolisher → Dify 收到润色后的 prompt"""
    mock_dify_client.run_text2img.return_value = _make_dify_result()

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc, mock_prompt_polisher,
    )

    with patch("httpx.AsyncClient", _FakeAsyncClient):
        result = await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="a cute cat",
            polish_prompt=True,
        )

    # 润色器被调用
    mock_prompt_polisher.polish.assert_called_once_with("a cute cat")

    # Dify 收到润色后的 prompt
    call_kwargs = mock_dify_client.run_text2img.call_args.kwargs
    assert call_kwargs["prompt"] == "[polished] a cute cat"

    # 返回的 prompt 也是润色后的
    assert result.prompt == "[polished] a cute cat"


# ============================================================
# 3. Dify 失败释放配额
# ============================================================

@pytest.mark.asyncio
async def test_generate_dify_failure_releases_quota(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """DifyClient 抛 DifyError → quota.release() 被调用、历史 status=failed、错误冒泡"""
    mock_dify_client.run_text2img.side_effect = DifyError("工作流执行失败", kind="workflow_failed")

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    with pytest.raises(DifyError, match="工作流执行失败"):
        await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="test prompt",
        )

    # 配额释放
    mock_quota_svc.rollback.assert_called_once()
    mock_quota_svc.record_usage.assert_not_called()

    # 降级失败计数
    mock_degradation_svc.record_failure.assert_called_once()

    # 失败历史已写入
    history = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.user_id == "test-user",
        ImageGenHistory.status == STATUS_FAILED,
    ).one()
    assert "工作流执行失败" in history.error_message
    assert history.result_oss_key == ""


# ============================================================
# 4. 超时释放配额
# ============================================================

@pytest.mark.asyncio
async def test_generate_timeout_releases_quota(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """DifyClient 抛 timeout DifyError → 同失败路径"""
    mock_dify_client.run_text2img.side_effect = DifyError("Dify 工作流超时 (120s)", kind="timeout")

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    with pytest.raises(DifyError) as exc_info:
        await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="test prompt",
        )
    assert exc_info.value.kind == "timeout"

    mock_quota_svc.rollback.assert_called_once()
    mock_degradation_svc.record_failure.assert_called_once()

    history = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.user_id == "test-user",
        ImageGenHistory.status == STATUS_FAILED,
    ).one()
    assert "超时" in history.error_message
    assert history.result_oss_key == ""


# ============================================================
# 5. 取消释放配额
# ============================================================

@pytest.mark.asyncio
async def test_generate_cancelled_releases_quota(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """asyncio.CancelledError → 释放配额 + 历史 status=cancelled"""
    mock_dify_client.run_text2img.side_effect = asyncio.CancelledError()

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    with pytest.raises(asyncio.CancelledError):
        await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="test prompt",
        )

    mock_quota_svc.rollback.assert_called_once()
    mock_quota_svc.record_usage.assert_not_called()
    # 取消不记录降级失败
    mock_degradation_svc.record_failure.assert_not_called()

    history = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.user_id == "test-user",
        ImageGenHistory.status == STATUS_CANCELLED,
    ).one()
    assert history.result_oss_key == ""


# ============================================================
# 6. 无配额抛异常
# ============================================================

@pytest.mark.asyncio
async def test_generate_no_quota_raises(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """quota_svc.check_and_reserve 抛 QuotaExceeded → 历史未写入、错误冒泡"""
    mock_quota_svc.check_and_reserve.side_effect = QuotaExceeded("daily_limit_exceeded")

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    with pytest.raises(QuotaExceeded) as exc_info:
        await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="test prompt",
        )
    assert exc_info.value.reason == "daily_limit_exceeded"

    # 不应调 Dify
    mock_dify_client.run_text2img.assert_not_called()
    # 不应写历史（配额预留失败时不写历史）
    count = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.user_id == "test-user",
    ).count()
    assert count == 0


# ============================================================
# 7. 服务降级拒绝请求
# ============================================================

@pytest.mark.asyncio
async def test_generate_service_degraded_raises(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """degradation_svc.is_degraded() = True → 抛 ServiceDegraded、不调用任何下游"""
    mock_degradation_svc.is_degraded.return_value = True

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    with pytest.raises(ServiceDegraded):
        await svc.generate(
            user_id="test-user",
            operation=OPERATION_TEXT2IMG,
            prompt="test prompt",
        )

    # 不应调任何下游
    mock_quota_svc.check_and_reserve.assert_not_called()
    mock_dify_client.run_text2img.assert_not_called()
    mock_oss_svc.upload_file.assert_not_called()


# ============================================================
# 8. img2img 上传参考图
# ============================================================

@pytest.mark.asyncio
async def test_generate_img2img_uploads_reference(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """reference_image_bytes 提供 → OSS 上传参考图 → 300s 签名 URL 传给 Dify"""
    mock_dify_client.run_img2img.return_value = _make_dify_result()

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    ref_bytes = b"\x89PNG\r\n\x1a\nreference-image-data"

    with patch("httpx.AsyncClient", _FakeAsyncClient):
        result = await svc.generate(
            user_id="test-user",
            operation=OPERATION_IMG2IMG,
            prompt="enhance this image",
            reference_image_bytes=ref_bytes,
            strength=0.7,
            size="1024x1024",
        )

    # OSS upload_file: 参考图 + 结果图 = 2 次
    assert mock_oss_svc.upload_file.call_count == 2

    # 第一次上传是参考图
    ref_call = mock_oss_svc.upload_file.call_args_list[0]
    assert "image-gen/ref/" in ref_call.kwargs["object_name"]

    # sign_url 被调用：参考图签名(300s) + 结果图签名(3600s)
    sign_calls = mock_oss_svc.sign_url.call_args_list
    # 第一次签名：参考图 300s
    assert sign_calls[0].args == ("GET", sign_calls[0].args[1], 300)
    assert "image-gen/ref/" in sign_calls[0].args[1]

    # DifyClient 收到签名后的参考图 URL
    call_kwargs = mock_dify_client.run_img2img.call_args.kwargs
    assert "https://oss.example.com/image-gen/ref/" in call_kwargs["reference_url"]
    assert call_kwargs["strength"] == 0.7

    # 历史中 reference_oss_key 不为空
    history = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.id == result.history_id,
    ).one()
    assert history.reference_oss_key is not None
    assert "image-gen/ref/" in history.reference_oss_key


# ============================================================
# 9. inpaint 上传参考图 + 蒙版
# ============================================================

@pytest.mark.asyncio
async def test_generate_inpaint_uploads_reference_and_mask(
    db_session,
    mock_dify_client,
    mock_quota_svc,
    mock_oss_svc,
    history_svc,
    mock_degradation_svc,
):
    """reference + mask 都上传 → 两个签名 URL 传给 Dify inpaint"""
    mock_dify_client.run_inpaint.return_value = _make_dify_result()

    svc = _build_service(
        db_session, mock_dify_client, mock_quota_svc, mock_oss_svc,
        history_svc, mock_degradation_svc,
    )

    ref_bytes = b"\x89PNG\r\n\x1a\nref"
    mask_bytes = b"\x89PNG\r\n\x1a\nmask"

    with patch("httpx.AsyncClient", _FakeAsyncClient):
        result = await svc.generate(
            user_id="test-user",
            operation=OPERATION_INPAINT,
            prompt="fill the gap",
            reference_image_bytes=ref_bytes,
            mask_bytes=mask_bytes,
            size="1024x1024",
        )

    # OSS upload: 参考图 + 蒙版 + 结果图 = 3 次
    assert mock_oss_svc.upload_file.call_count == 3

    # 前两次上传分别是参考图和蒙版
    ref_call = mock_oss_svc.upload_file.call_args_list[0]
    mask_call = mock_oss_svc.upload_file.call_args_list[1]
    assert "image-gen/ref/" in ref_call.kwargs["object_name"]
    assert "image-gen/mask/" in mask_call.kwargs["object_name"]

    # DifyClient 收到两个签名 URL
    call_kwargs = mock_dify_client.run_inpaint.call_args.kwargs
    assert "image-gen/ref/" in call_kwargs["image_url"]
    assert "image-gen/mask/" in call_kwargs["mask_url"]

    # 历史中两个 key 都有
    history = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.id == result.history_id,
    ).one()
    assert "image-gen/ref/" in history.reference_oss_key
    assert "image-gen/mask/" in history.mask_oss_key


# ============================================================
# 10. 历史记录 CRUD
# ============================================================

def test_history_service_crud(db_session, mock_oss_svc):
    """create / get / list / soft_delete / update_last_accessed"""
    svc = ImageGenHistoryService(db=db_session, oss_svc=mock_oss_svc)
    uid = _make_uid()

    # 创建
    r1 = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="image-gen/result/abc.png", prompt="cat",
    )
    r2 = svc.create_record(
        user_id=uid, operation=OPERATION_IMG2IMG, status=STATUS_FAILED,
        result_oss_key="", prompt="dog", error_message="dify error",
    )
    db_session.commit()

    assert r1.id is not None
    assert r2.id is not None

    # 查询单条
    fetched = svc.get_record(uid, r1.id)
    assert fetched is not None
    assert fetched.prompt == "cat"
    assert fetched.status == STATUS_SUCCESS

    # 列表
    records = svc.list_records(uid, skip=0, limit=10)
    assert len(records) == 2

    # 按操作筛选
    records = svc.list_records(uid, skip=0, limit=10, operation=OPERATION_TEXT2IMG)
    assert len(records) == 1
    assert records[0].id == r1.id

    # 按状态筛选
    records = svc.list_records(uid, skip=0, limit=10, status=STATUS_FAILED)
    assert len(records) == 1
    assert records[0].id == r2.id

    # 软删除
    assert svc.soft_delete(uid, r1.id) is True
    db_session.commit()

    # 软删除后 list 不返回
    records = svc.list_records(uid, skip=0, limit=10)
    assert len(records) == 1
    assert records[0].id == r2.id

    # get_record 也找不到
    assert svc.get_record(uid, r1.id) is None

    # 重复软删除返回 False
    assert svc.soft_delete(uid, r1.id) is False

    # update_last_accessed
    svc.update_last_accessed(r2.id)
    db_session.commit()
    fetched2 = svc.get_record(uid, r2.id)
    assert fetched2.last_accessed_at is not None

    # get_result_url
    url = svc.get_result_url(fetched2)
    # r2 的 result_oss_key 为空串 → 返回空串
    assert url == ""

    # 给 r2 设一个 result_oss_key 再测
    r3 = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="image-gen/result/xyz.png",
    )
    db_session.commit()
    url = svc.get_result_url(r3)
    assert "image-gen/result/xyz.png" in url
    assert "expires=3600" in url


# ============================================================
# 11. 按日期清理
# ============================================================

def test_history_cleanup_before_by_date(db_session, mock_oss_svc):
    """cutoff 之前的记录被删"""
    svc = ImageGenHistoryService(db=db_session, oss_svc=mock_oss_svc)
    uid = _make_uid()

    # 手动创建不同时间的记录
    old = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="old.png",
    )
    # 手动修改 created_at
    old.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    db_session.flush()

    recent = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="recent.png",
    )
    db_session.commit()

    # cutoff = 2025-06-01 → 仅 old 被删
    cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
    deleted = svc.cleanup_before(cutoff, mode="by_date")
    db_session.commit()

    assert deleted == 1

    remaining = db_session.query(ImageGenHistory).filter(
        ImageGenHistory.user_id == uid,
    ).all()
    assert len(remaining) == 1
    assert remaining[0].id == recent.id


# ============================================================
# 12. 按未访问天数清理
# ============================================================

def test_history_cleanup_by_unused_for_n_days(db_session, mock_oss_svc):
    """last_accessed_at 早于 cutoff 的记录被删；NULL 时按 created_at 代替"""
    svc = ImageGenHistoryService(db=db_session, oss_svc=mock_oss_svc)
    uid = _make_uid()

    # 记录 A：last_accessed_at 很早 → 应被删
    a = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="a.png",
    )
    a.last_accessed_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    # 记录 B：last_accessed_at 最近 → 保留
    b = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="b.png",
    )
    b.last_accessed_at = datetime(2026, 8, 1, tzinfo=timezone.utc)

    # 记录 C：last_accessed_at 为 NULL，created_at 很早 → 应被删
    c = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="c.png",
    )
    c.last_accessed_at = None
    c.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    # 记录 D：last_accessed_at 为 NULL，created_at 最近 → 保留
    d = svc.create_record(
        user_id=uid, operation=OPERATION_TEXT2IMG, status=STATUS_SUCCESS,
        result_oss_key="d.png",
    )
    d.last_accessed_at = None
    # created_at 默认为 now，不需要修改

    db_session.commit()

    cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
    deleted = svc.cleanup_before(cutoff, mode="unused_for_n_days")
    db_session.commit()

    assert deleted == 2  # A 和 C

    remaining_ids = {
        r.id for r in db_session.query(ImageGenHistory).filter(
            ImageGenHistory.user_id == uid,
        ).all()
    }
    assert remaining_ids == {b.id, d.id}
