"""
Task 6.1 — 图像生成用户 API 路由

端点：
  POST /image-generation/generate         — 生成图像（multipart）
  POST /image-generation/polish-prompt    — 润色提示词（Phase 8 占位）
  GET  /image-generation/history          — 历史列表（分页）
  GET  /image-generation/history/{id}     — 历史详情 + 更新访问时间
  DELETE /image-generation/history/{id}   — 软删除历史
  GET  /image-generation/quota/me         — 当前用户配额
  GET  /image-generation/result/{id}      — 刷新签名 URL + 更新访问时间
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.exceptions import DifyError, QuotaExceeded, ServiceDegraded
from app.models.base import get_db
from app.services.dify_client import DifyClient
from app.services.dify_config_service import DifyConfigService
from app.services.image_gen.backends import BackendNotConfiguredError
from app.services.image_gen_history_service import ImageGenHistoryService
from app.services.llm_quota_service import LLMQuotaService
from app.services.image_generation_service import ImageGenService
from app.services.oss_service import OssService
from app.utils.image_gen_constants import (
    MAX_N_IMAGES,
    VALID_EDIT_TYPES,
    VALID_OPERATIONS,
    VALID_SIZES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-generation", tags=["image-generation"])


# ============================================================
# 依赖注入工厂
# ============================================================

def _get_oss_service() -> OssService:
    """获取 OssService 单例（项目全局共享）"""
    return OssService()


def get_history_service(
    db: Session = Depends(get_db),
) -> ImageGenHistoryService:
    """组装 ImageGenHistoryService（用于不需要完整 ImageGenService 的端点）"""
    return ImageGenHistoryService(db=db, oss_svc=_get_oss_service())


def get_quota_service(
    db: Session = Depends(get_db),
) -> LLMQuotaService:
    """组装 LLMQuotaService（通用配额服务）"""
    return LLMQuotaService(db=db)


def get_image_gen_service(
    db: Session = Depends(get_db),
) -> ImageGenService:
    """
    组装 ImageGenService + 所有依赖。

    degradation_svc / prompt_polisher 在 Phase 8/9 才会注入，
    目前传 None（service 内部已处理）。
    """
    config_svc = DifyConfigService(db=db)
    dify_client = DifyClient(config_svc=config_svc)
    quota_svc = LLMQuotaService(db=db)
    history_svc = ImageGenHistoryService(db=db, oss_svc=_get_oss_service())
    oss_svc = _get_oss_service()
    return ImageGenService(
        db=db,
        dify_client=dify_client,
        quota_svc=quota_svc,
        oss_svc=oss_svc,
        history_svc=history_svc,
        degradation_svc=None,   # Phase 9
        prompt_polisher=None,   # Phase 8
    )


# ============================================================
# 工具函数
# ============================================================

def _extract_user_id(current_user) -> str:
    """从 get_current_user 返回的 dict 中提取 user_id"""
    # get_current_user 返回 {"id": ..., "username": ..., "role": ...}
    if isinstance(current_user, dict):
        return current_user["id"]
    # 兼容：如果返回的是字符串
    return str(current_user)


def _validate_operation(operation: str) -> None:
    """校验操作类型"""
    if operation not in VALID_OPERATIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_operation",
                "message": f"operation 必须为 {sorted(VALID_OPERATIONS)} 之一",
                "valid_operations": sorted(VALID_OPERATIONS),
            },
        )


def _validate_size(size: str) -> None:
    """校验尺寸"""
    if size not in VALID_SIZES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_size",
                "message": f"size 必须为 {sorted(VALID_SIZES)} 之一",
                "valid_sizes": sorted(VALID_SIZES),
            },
        )


def _validate_edit_type(operation: str, edit_type: Optional[str]) -> None:
    """upload_edit 操作必须提供合法的 edit_type"""
    if operation == "upload_edit":
        if edit_type is None or edit_type not in VALID_EDIT_TYPES:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_edit_type",
                    "message": f"operation=upload_edit 时 edit_type 必须为 {sorted(VALID_EDIT_TYPES)} 之一",
                    "valid_edit_types": sorted(VALID_EDIT_TYPES),
                },
            )


def _validate_n(n: int) -> None:
    """校验生成数量"""
    if n < 1 or n > MAX_N_IMAGES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_n",
                "message": f"n 必须为 1 ~ {MAX_N_IMAGES}",
            },
        )


async def _read_upload_file(upload: Optional[UploadFile]) -> Optional[bytes]:
    """读取 UploadFile 内容，返回 bytes；None 时返回 None"""
    if upload is None:
        return None
    content = await upload.read()
    # 校验 content-type 为 image/*
    ct = upload.content_type or ""
    if not ct.startswith("image/"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_file_type",
                "message": f"上传文件必须为 image/* 类型，当前为: {ct!r}",
            },
        )
    return content


# ============================================================
# 异常 → HTTP 映射
# ============================================================

def _map_service_exception(exc: Exception) -> HTTPException:
    """将 service 层异常映射为 HTTP 异常"""
    if isinstance(exc, QuotaExceeded):
        return HTTPException(
            status_code=429,
            detail={"error": "quota_exceeded", "reason": exc.reason},
        )
    if isinstance(exc, DifyError):
        return HTTPException(
            status_code=502,
            detail={"error": "dify_error", "kind": exc.kind, "message": exc.message},
        )
    if isinstance(exc, ServiceDegraded):
        return HTTPException(
            status_code=503,
            detail={"error": "service_degraded", "message": exc.message},
        )
    # 兜底
    return HTTPException(status_code=500, detail={"error": "internal_error", "message": str(exc)})


# ============================================================
# 端点
# ============================================================

@router.post("/generate")
async def generate(
    operation: str = Form(...),
    prompt: str = Form(...),
    size: str = Form("1024x1024"),
    n: int = Form(1),
    style: Optional[str] = Form(None),
    strength: float = Form(0.6),
    model_preference: str = Form("auto"),
    polish_prompt: bool = Form(False),
    reference_image: Optional[UploadFile] = File(None),
    mask_image: Optional[UploadFile] = File(None),
    edit_type: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    svc: ImageGenService = Depends(get_image_gen_service),
):
    """
    生成图像（multipart/form-data）。

    成功返回 {history_id, image_urls, model_used, duration_ms, operation, prompt}。
    """
    user_id = _extract_user_id(current_user)

    # 参数校验
    _validate_operation(operation)
    _validate_size(size)
    _validate_n(n)
    _validate_edit_type(operation, edit_type)

    # 读取上传文件
    try:
        ref_bytes = await _read_upload_file(reference_image)
        mask_bytes = await _read_upload_file(mask_image)
    except HTTPException:
        raise

    # 调用 service
    try:
        result = await svc.generate(
            user_id=user_id,
            operation=operation,
            prompt=prompt,
            reference_image_bytes=ref_bytes,
            mask_bytes=mask_bytes,
            edit_type=edit_type,
            size=size,
            n=n,
            style=style,
            strength=strength,
            model_preference=model_preference,
            polish_prompt=polish_prompt,
        )
    except (QuotaExceeded, DifyError, ServiceDegraded) as exc:
        raise _map_service_exception(exc)

    return {
        "history_id": result.history_id,
        "image_urls": result.image_urls,
        "model_used": result.model_used,
        "duration_ms": result.duration_ms,
        "operation": result.operation,
        "prompt": result.prompt,
    }


@router.post("/chat")
async def chat(
    operation: str = Form(...),
    prompt: str = Form(...),
    backend: str = Form("selfdev"),
    conversation_id: Optional[str] = Form(None),
    size: str = Form("1024x1024"),
    n: int = Form(1),
    style: Optional[str] = Form(None),
    strength: float = Form(0.6),
    model_preference: str = Form("auto"),
    edit_type: Optional[str] = Form(None),
    reference_image: Optional[UploadFile] = File(None),
    mask_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    svc: ImageGenService = Depends(get_image_gen_service),
):
    """
    多轮对话入口（multipart/form-data）。

    追问时返回 status=asking；
    生成完成时返回 status=generated + image_urls + backend。

    新增（Task 24）：
      - backend Form 参数，默认 selfdev
      - 通过 chat_generate_dispatch_with_quota 分发
    """
    user_id_str = _extract_user_id(current_user)
    # chat_generate_dispatch_with_quota 接收 uuid.UUID；
    # JWT sub 通常已是 UUID 字符串；测试场景用普通字符串则用 uuid5 兜底，保证幂等
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        user_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id_str))

    # 参数校验
    _validate_operation(operation)
    _validate_size(size)
    _validate_n(n)
    _validate_edit_type(operation, edit_type)

    # 读取上传文件
    ref_bytes = await _read_upload_file(reference_image)
    mask_bytes = await _read_upload_file(mask_image)

    # 调用 with-quota dispatch（Task 23：quota reserve / dispatch / commit-release 都在 service 内）
    try:
        result = await svc.chat_generate_dispatch_with_quota(
            backend=backend,
            user_id=user_id,
            operation=operation,
            query=prompt,
            conversation_id=conversation_id,
            reference_image=ref_bytes,
            mask_image=mask_bytes,
            size=size,
            n=n,
            strength=strength,
            edit_type=edit_type,
        )
    except BackendNotConfiguredError as exc:
        # 后端未注册 → 503
        raise HTTPException(status_code=503, detail=str(exc))
    except (QuotaExceeded, DifyError, ServiceDegraded) as exc:
        raise _map_service_exception(exc)

    response = {
        "conversation_id": result.conversation_id,
        "answer": result.answer_text,
        "model_used": result.model_used,
        "backend": result.backend,
        "status": "generated" if result.image_urls else "asking",
    }
    if result.image_urls:
        response["image_urls"] = result.image_urls

    return response


@router.post("/polish-prompt")
async def polish_prompt(
    prompt: str = Form(...),
    operation: str = Form("text2img"),
    current_user: dict = Depends(get_current_user),
):
    """
    润色提示词（Phase 8 占位）。

    当前实现：直接返回原始 prompt，was_polished=False。
    Phase 8 会替换为 PromptPolisher 的真实实现。
    """
    return {"polished_prompt": prompt, "was_polished": False}


@router.get("/history")
async def list_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    operation: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    history_svc: ImageGenHistoryService = Depends(get_history_service),
):
    """分页列出当前用户的历史记录。"""
    user_id = _extract_user_id(current_user)

    # 可选：校验 operation
    if operation is not None:
        _validate_operation(operation)

    records = history_svc.list_records(user_id=user_id, skip=skip, limit=limit, operation=operation)
    return {
        "items": [_serialize_history(r, history_svc) for r in records],
        "skip": skip,
        "limit": limit,
        "count": len(records),
    }


@router.get("/history/{history_id}")
async def get_history(
    history_id: str,
    current_user: dict = Depends(get_current_user),
    history_svc: ImageGenHistoryService = Depends(get_history_service),
):
    """
    获取单条历史记录详情，同时刷新 last_accessed_at。
    """
    user_id = _extract_user_id(current_user)

    record = history_svc.get_record(user_id=user_id, history_id=history_id)
    if record is None:
        # 区分：记录不存在 vs 记录属于其他用户
        # 用一次不限 user_id 的查询判断
        from app.models.image_generation_models import ImageGenHistory
        any_record = (
            history_svc.db.query(ImageGenHistory)
            .filter(ImageGenHistory.id == history_id, ImageGenHistory.is_deleted == False)  # noqa: E712
            .first()
        )
        if any_record is not None and any_record.user_id != user_id:
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "该记录不属于当前用户"})
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "历史记录不存在"})

    # 刷新访问时间
    history_svc.update_last_accessed(history_id=record.id)

    return _serialize_history(record, history_svc)


@router.delete("/history/{history_id}")
async def delete_history(
    history_id: str,
    current_user: dict = Depends(get_current_user),
    history_svc: ImageGenHistoryService = Depends(get_history_service),
):
    """软删除一条历史记录。"""
    user_id = _extract_user_id(current_user)

    success = history_svc.soft_delete(user_id=user_id, history_id=history_id)
    if not success:
        # 区分 403 / 404
        from app.models.image_generation_models import ImageGenHistory
        any_record = (
            history_svc.db.query(ImageGenHistory)
            .filter(ImageGenHistory.id == history_id, ImageGenHistory.is_deleted == False)  # noqa: E712
            .first()
        )
        if any_record is not None and any_record.user_id != user_id:
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "该记录不属于当前用户"})
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "历史记录不存在"})

    return {"success": True, "history_id": history_id}


@router.get("/quota/me")
async def get_my_quota(
    current_user: dict = Depends(get_current_user),
    quota_svc: LLMQuotaService = Depends(get_quota_service),
):
    """查看当前用户的图像生成配额。"""
    user_id = _extract_user_id(current_user)

    quota = quota_svc.get_user_quota(user_id=user_id)
    if quota is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "用户无配额记录"})

    # QuotaInfo 是 dataclass，直接 asdict 即可
    data = asdict(quota)
    # datetime 序列化为 ISO 字符串（容错：session 被污染时 valid_from/valid_until 可能是列键字符串）
    for key in ("valid_from", "valid_until"):
        v = data.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            # 列键字符串（如 'llm_user_quota_valid_from'）直接置为 None
            if v.replace("_", "").isalnum():
                data[key] = None
                continue
            # 已经是 ISO 格式字符串
            data[key] = v
            continue
        try:
            data[key] = v.isoformat()
        except (AttributeError, TypeError):
            data[key] = None
    return data


@router.get("/result/{history_id}")
async def get_result(
    history_id: str,
    current_user: dict = Depends(get_current_user),
    history_svc: ImageGenHistoryService = Depends(get_history_service),
):
    """
    获取历史记录的结果图签名 URL（1 小时有效期），同时刷新 last_accessed_at。
    """
    user_id = _extract_user_id(current_user)

    record = history_svc.get_record(user_id=user_id, history_id=history_id)
    if record is None:
        from app.models.image_generation_models import ImageGenHistory
        any_record = (
            history_svc.db.query(ImageGenHistory)
            .filter(ImageGenHistory.id == history_id, ImageGenHistory.is_deleted == False)  # noqa: E712
            .first()
        )
        if any_record is not None and any_record.user_id != user_id:
            raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "该记录不属于当前用户"})
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "历史记录不存在"})

    # 刷新签名 URL
    result_url = history_svc.get_result_url(record)
    # 刷新访问时间
    history_svc.update_last_accessed(history_id=record.id)

    return {
        "history_id": record.id,
        "result_url": result_url,
        "status": record.status,
    }


# ============================================================
# 序列化辅助
# ============================================================

def _serialize_history(record, history_svc: ImageGenHistoryService) -> dict:
    """将 ImageGenHistory ORM 对象序列化为 dict"""
    data = {
        "id": record.id,
        "user_id": record.user_id,
        "operation": record.operation,
        "prompt": record.prompt,
        "params": record.params,
        "reference_oss_key": record.reference_oss_key,
        "mask_oss_key": record.mask_oss_key,
        "result_oss_key": record.result_oss_key,
        "result_width": record.result_width,
        "result_height": record.result_height,
        "model_used": record.model_used,
        "status": record.status,
        "error_message": record.error_message,
        "duration_ms": record.duration_ms,
        "is_deleted": record.is_deleted,
        "last_accessed_at": record.last_accessed_at.isoformat() if record.last_accessed_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
    return data
