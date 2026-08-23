"""
Task 7.1 — 图像生成管理 API 路由

端点（spec §7.2，共 14 个）：
  # 用户配额管理 (5)
  GET    /admin/image-generation/users                     # 分页 + 搜索有配额用户
  POST   /admin/image-generation/users/{user_id}/grant     # 分配/更新配额
  DELETE /admin/image-generation/users/{user_id}/quota     # 撤销配额
  POST   /admin/image-generation/users/{user_id}/reset     # 重置计数器
  GET    /admin/image-generation/quota/{user_id}           # 用户配额详情

  # Dify 配置 (3)
  GET    /admin/image-generation/config                    # 配置视图（mask key）
  PUT    /admin/image-generation/config                    # 部分更新
  POST   /admin/image-generation/config/test               # 连通性测试

  # 降级管理 (3) — Phase 9
  GET    /admin/image-generation/degradation
  PUT    /admin/image-generation/degradation
  POST   /admin/image-generation/degradation/reset

  # 保留策略 (3) — Phase 10
  GET    /admin/image-generation/retention
  PUT    /admin/image-generation/retention
  POST   /admin/image-generation/retention/trigger

  # 统计 (1)
  GET    /admin/image-generation/stats

鉴权：复用项目已有 get_admin_user 依赖。

可选服务：DegradationService / OssRetentionService 在 Phase 9/10 才有实现；
当前依赖工厂返回 None，相关端点直接返回 HTTP 503 "service not yet enabled"。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

# 复用项目已有依赖
from app.routes.admin import get_admin_user
from app.models.auth_models import UserResponse
from app.models.base import get_db
from app.models.image_generation_models import ImageGenHistory
from app.services.dify_client import DifyClient
from app.services.dify_config_service import DifyConfigService
from app.services.image_gen_quota_service import ImageGenQuotaService
from app.utils.image_gen_constants import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_SUCCESS,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/image-generation",
    tags=["admin-image-generation"],
)


# ============================================================
# 依赖注入工厂
# ============================================================

def get_dify_config_service(
    db: Session = Depends(get_db),
) -> DifyConfigService:
    """组装 DifyConfigService"""
    return DifyConfigService(db=db)


def get_image_gen_quota_service(
    db: Session = Depends(get_db),
) -> ImageGenQuotaService:
    """组装 ImageGenQuotaService"""
    return ImageGenQuotaService(db=db)


def get_dify_client(
    config_svc: DifyConfigService = Depends(get_dify_config_service),
) -> DifyClient:
    """组装 DifyClient"""
    return DifyClient(config_svc=config_svc)


def get_degradation_service() -> Optional[Any]:
    """
    降级服务（Phase 9 才会注入实际实现）。
    当前返回 None，相关端点返回 503。
    """
    return None


def get_oss_retention_service() -> Optional[Any]:
    """
    OSS 保留策略服务（Phase 10 才会注入实际实现）。
    当前返回 None，相关端点返回 503。
    """
    return None


# ============================================================
# Pydantic 请求体（严格 allow-list 防注入）
# ============================================================

class GrantQuotaRequest(BaseModel):
    """分配/更新配额请求体（extra="forbid" 防止未知字段绕过校验）"""
    daily_limit: int = Field(..., ge=0, le=10000)
    monthly_limit: int = Field(..., ge=0, le=300000)
    valid_from: Optional[datetime] = Field(None, description="生效开始时间")
    valid_until: Optional[datetime] = Field(None, description="生效结束时间")
    notes: Optional[str] = Field(None, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _check_validity_range(self) -> "GrantQuotaRequest":
        """确保 valid_from 早于 valid_until（都为 None 时不校验）"""
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be earlier than valid_until")
        return self


# workflow id 允许的字符：字母数字 + _ -
_WORKFLOW_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"


class UpdateDifyConfigRequest(BaseModel):
    """
    Dify 配置部分更新请求体。

    - extra="forbid"：拒绝未知字段，防止攻击者传入任意 key 写入数据库
    - api_url 暂时只做长度限制（SSRF 完整校验在后续 hardening 任务，spec §7.2 备注）
    - app_api_key 长度限制 10~200
    - workflow_id 仅允许字母数字 + 下划线 + 中划线
    """
    api_url: Optional[str] = Field(None, max_length=500)
    app_api_key: Optional[str] = Field(None, min_length=10, max_length=200)
    text2img_workflow_id: Optional[str] = Field(None, pattern=_WORKFLOW_ID_PATTERN)
    img2img_workflow_id: Optional[str] = Field(None, pattern=_WORKFLOW_ID_PATTERN)
    inpaint_workflow_id: Optional[str] = Field(None, pattern=_WORKFLOW_ID_PATTERN)
    upload_edit_workflow_id: Optional[str] = Field(None, pattern=_WORKFLOW_ID_PATTERN)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)

    model_config = ConfigDict(extra="forbid")


# allow-list：Pydantic 字段名 → DifyConfigService 内部 key 名
# 这一层映射保证只有"已知安全字段"能写入数据库
_UPDATE_CONFIG_FIELD_MAP: Dict[str, str] = {
    "api_url": "api_url",
    "app_api_key": "app_api_key",
    "text2img_workflow_id": "workflow_text2img",
    "img2img_workflow_id": "workflow_img2img",
    "inpaint_workflow_id": "workflow_inpaint",
    "upload_edit_workflow_id": "workflow_upload_edit",
    "timeout_seconds": "default_timeout",
}


class DegradationConfigUpdateRequest(BaseModel):
    """降级配置更新请求体（当前为占位，Phase 9 启用）"""
    enabled: Optional[bool] = None
    failure_threshold: Optional[int] = Field(None, ge=1, le=100)
    degrade_duration_seconds: Optional[int] = Field(None, ge=10, le=86400)

    model_config = ConfigDict(extra="forbid")


class RetentionConfigUpdateRequest(BaseModel):
    """保留策略配置更新请求体（当前为占位，Phase 10 启用）"""
    mode: Optional[str] = Field(None, pattern="^(keep_forever|delete_after_n_days|delete_if_unused_for_n_days)$")
    n_days: Optional[int] = Field(None, ge=1, le=3650)
    cleanup_cron: Optional[str] = Field(None, max_length=64)

    model_config = ConfigDict(extra="forbid")


# ============================================================
# 工具：sanitize Dify 连通性测试返回的错误信息
# ============================================================

_DANGEROUS_PATTERNS = [
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),  # 防止 API key 泄露
    re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),   # 防止内部 IP 泄露
    re.compile(r"(?:[A-Za-z]:)?[\\/][\w.\-/]+\.\w{2,4}"),  # 文件路径
    re.compile(r"Traceback\s*\(most recent call last\)", re.IGNORECASE),  # stack trace
    re.compile(r"line\s+\d+", re.IGNORECASE),  # "line 42" 等行号
    re.compile(r"\bFile\s+\"[^\"]+\"", re.IGNORECASE),  # 'File "..."'
]


def _sanitize_connection_error(raw: str) -> str:
    """
    将原始异常消息清理为面向管理员的友好提示。

    规则：
      - 不暴露 stack trace、文件路径、IP、Authorization header
      - 用 kind 级别描述，例如 "connection refused" / "timeout" / "dns failure"
    """
    if not raw:
        return "connection failed: unknown"

    lowered = raw.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return "connection failed: timeout"
    if "refused" in lowered:
        return "connection failed: connection_refused"
    if "resolve" in lowered or "name or service" in lowered or "dns" in lowered:
        return "connection failed: dns_failure"
    if "ssl" in lowered or "certificate" in lowered:
        return "connection failed: tls_error"

    # 兜底：去掉危险字段 + 截断到 200 字符
    sanitized = raw
    for pat in _DANGEROUS_PATTERNS:
        sanitized = pat.sub("[redacted]", sanitized)
    return f"connection failed: {sanitized[:200]}"


def _serialize_quota(q) -> Dict[str, Any]:
    """将 QuotaInfo 序列化为 JSON 友好 dict"""
    return {
        "user_id": q.user_id,
        "daily_limit": q.daily_limit,
        "daily_used": q.daily_used,
        "daily_remaining": q.daily_remaining,
        "monthly_limit": q.monthly_limit,
        "monthly_used": q.monthly_used,
        "monthly_remaining": q.monthly_remaining,
        "valid_from": q.valid_from.isoformat() if q.valid_from else None,
        "valid_until": q.valid_until.isoformat() if q.valid_until else None,
        "is_valid": q.is_valid,
        "granted_by": q.granted_by,
        "notes": q.notes,
    }


# ============================================================
# 用户配额管理端点 (5)
# ============================================================

@router.get("/users")
async def list_quota_users(
    skip: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    search: Optional[str] = Query(None, description="按 user_id 模糊匹配"),
    admin_user: UserResponse = Depends(get_admin_user),
    quota_svc: ImageGenQuotaService = Depends(get_image_gen_quota_service),
):
    """有配额用户列表（分页 + 搜索）"""
    items = quota_svc.list_users(skip=skip, limit=limit, search=search)
    total = quota_svc.count_users(search=search)
    return {
        "items": [_serialize_quota(q) for q in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/users/{user_id}/grant")
async def grant_quota(
    user_id: str,
    body: GrantQuotaRequest,
    admin_user: UserResponse = Depends(get_admin_user),
    quota_svc: ImageGenQuotaService = Depends(get_image_gen_quota_service),
):
    """
    分配/更新配额 + 有效期。

    - 复用已有记录：保留已用计数器，仅更新管理员字段
    - 不存在则创建新行
    """
    quota = quota_svc.grant(
        user_id=user_id,
        daily_limit=body.daily_limit,
        monthly_limit=body.monthly_limit,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        granted_by=admin_user.user_id,
        notes=body.notes,
    )
    logger.info(
        "[admin-image-gen] 管理员 %s 分配配额 user=%s daily=%d monthly=%d",
        admin_user.user_id, user_id, body.daily_limit, body.monthly_limit,
    )
    return _serialize_quota(quota)


@router.delete("/users/{user_id}/quota")
async def revoke_quota(
    user_id: str,
    admin_user: UserResponse = Depends(get_admin_user),
    quota_svc: ImageGenQuotaService = Depends(get_image_gen_quota_service),
):
    """撤销配额（删除记录）"""
    quota_svc.revoke(user_id)
    logger.info(
        "[admin-image-gen] 管理员 %s 撤销配额 user=%s",
        admin_user.user_id, user_id,
    )
    return {"success": True, "user_id": user_id}


@router.post("/users/{user_id}/reset")
async def reset_counters(
    user_id: str,
    admin_user: UserResponse = Depends(get_admin_user),
    quota_svc: ImageGenQuotaService = Depends(get_image_gen_quota_service),
):
    """把 daily_used / monthly_used 归零"""
    quota_svc.reset_counters(user_id)
    logger.info(
        "[admin-image-gen] 管理员 %s 重置计数器 user=%s",
        admin_user.user_id, user_id,
    )
    return {"success": True, "user_id": user_id}


@router.get("/quota/{user_id}")
async def get_user_quota(
    user_id: str,
    admin_user: UserResponse = Depends(get_admin_user),
    quota_svc: ImageGenQuotaService = Depends(get_image_gen_quota_service),
):
    """查看指定用户的配额信息"""
    quota = quota_svc.get_user_quota(user_id)
    if quota is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "用户无配额记录"},
        )
    return _serialize_quota(quota)


# ============================================================
# Dify 配置端点 (3)
# ============================================================

@router.get("/config")
async def get_dify_config(
    admin_user: UserResponse = Depends(get_admin_user),
    config_svc: DifyConfigService = Depends(get_dify_config_service),
):
    """
    返回 Dify 配置视图。

    API key 不会以明文返回；仅返回是否已设置的标志位。
    """
    return config_svc.get_config_view()


@router.put("/config")
async def update_dify_config(
    body: UpdateDifyConfigRequest,
    admin_user: UserResponse = Depends(get_admin_user),
    config_svc: DifyConfigService = Depends(get_dify_config_service),
):
    """
    部分更新 Dify 配置。

    只接受白名单内的字段（extra="forbid" + 显式字段映射），
    防止攻击者通过未知字段写入数据库。
    """
    # 只取 Pydantic 已显式定义的字段（exclude_unset 跳过未传字段）
    raw_updates = body.model_dump(exclude_unset=True)

    # 映射到 DifyConfigService 内部 key 名
    service_updates: Dict[str, Any] = {}
    for field_name, value in raw_updates.items():
        service_key = _UPDATE_CONFIG_FIELD_MAP.get(field_name)
        if service_key is None:
            # 理论上 extra="forbid" 已拦截；此处做防御性双保险
            continue
        service_updates[service_key] = value

    if service_updates:
        config_svc.update_config(partial=service_updates, updated_by=admin_user.user_id)

    logger.info(
        "[admin-image-gen] 管理员 %s 更新 Dify 配置 keys=%s",
        admin_user.user_id, list(service_updates.keys()),
    )
    # 返回最新视图（mask key）
    return config_svc.get_config_view()


@router.post("/config/test")
async def test_dify_connection(
    admin_user: UserResponse = Depends(get_admin_user),
    dify_client: DifyClient = Depends(get_dify_client),
):
    """
    测试与 Dify 的连通性。

    返回示例：
      {"success": true,  "message": "连接成功"}
      {"success": false, "message": "connection failed: timeout"}

    错误信息经过 sanitize，不暴露 stack trace / API key / IP / 文件路径。
    """
    try:
        ok, message = await dify_client.test_connection()
    except Exception as e:
        # 理论上 DifyClient.test_connection 已捕获所有异常；
        # 此处作为兜底，防止 DifyClient 实现变更时泄露异常细节
        logger.exception("[admin-image-gen] Dify 连通性测试异常")
        return {"success": False, "message": _sanitize_connection_error(str(e))}

    if not ok:
        message = _sanitize_connection_error(message)

    logger.info(
        "[admin-image-gen] 管理员 %s 测试 Dify 连通性 ok=%s",
        admin_user.user_id, ok,
    )
    return {"success": ok, "message": message}


# ============================================================
# 降级管理端点 (3) — Phase 9 占位
# ============================================================

@router.get("/degradation")
async def get_degradation(
    admin_user: UserResponse = Depends(get_admin_user),
    degradation_svc: Optional[Any] = Depends(get_degradation_service),
):
    """查询降级状态与配置（Phase 9 启用）"""
    if degradation_svc is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "service_not_enabled", "message": "降级服务尚未启用（Phase 9 之后可用）"},
        )
    return degradation_svc.get_status()


@router.put("/degradation")
async def update_degradation(
    body: DegradationConfigUpdateRequest,
    admin_user: UserResponse = Depends(get_admin_user),
    degradation_svc: Optional[Any] = Depends(get_degradation_service),
):
    """更新降级配置（Phase 9 启用）"""
    if degradation_svc is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "service_not_enabled", "message": "降级服务尚未启用（Phase 9 之后可用）"},
        )
    updates = body.model_dump(exclude_unset=True)
    degradation_svc.update_config(updates)
    return degradation_svc.get_status()


@router.post("/degradation/reset")
async def reset_degradation(
    admin_user: UserResponse = Depends(get_admin_user),
    degradation_svc: Optional[Any] = Depends(get_degradation_service),
):
    """手动解除降级状态（Phase 9 启用）"""
    if degradation_svc is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "service_not_enabled", "message": "降级服务尚未启用（Phase 9 之后可用）"},
        )
    degradation_svc.reset()
    return {"success": True}


# ============================================================
# 保留策略端点 (3) — Phase 10 占位
# ============================================================

@router.get("/retention")
async def get_retention(
    admin_user: UserResponse = Depends(get_admin_user),
    retention_svc: Optional[Any] = Depends(get_oss_retention_service),
):
    """查询 OSS 保留策略配置（Phase 10 启用）"""
    if retention_svc is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "service_not_enabled", "message": "保留策略服务尚未启用（Phase 10 之后可用）"},
        )
    return retention_svc.get_config()


@router.put("/retention")
async def update_retention(
    body: RetentionConfigUpdateRequest,
    admin_user: UserResponse = Depends(get_admin_user),
    retention_svc: Optional[Any] = Depends(get_oss_retention_service),
):
    """更新保留策略配置（Phase 10 启用）"""
    if retention_svc is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "service_not_enabled", "message": "保留策略服务尚未启用（Phase 10 之后可用）"},
        )
    updates = body.model_dump(exclude_unset=True)
    retention_svc.update_config(updates)
    return retention_svc.get_config()


@router.post("/retention/trigger")
async def trigger_retention(
    admin_user: UserResponse = Depends(get_admin_user),
    retention_svc: Optional[Any] = Depends(get_oss_retention_service),
):
    """手动触发清理（Phase 10 启用）"""
    if retention_svc is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "service_not_enabled", "message": "保留策略服务尚未启用（Phase 10 之后可用）"},
        )
    retention_svc.run_cleanup()
    return {"success": True}


# ============================================================
# 统计端点 (1)
# ============================================================

@router.get("/stats")
async def get_stats(
    days: int = Query(7, ge=1, le=90, description="统计窗口天数"),
    admin_user: UserResponse = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    聚合最近 N 天的图像生成统计。

    返回字段：
      - total_calls: 总调用量
      - success_calls: 成功调用
      - failed_calls: 失败 + 取消
      - success_rate: 成功率（0~1，总调用为 0 时返回 0）
      - model_distribution: 按 model_used 分组的调用次数
      - daily_calls: 按日期分组的调用次数
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    base = db.query(ImageGenHistory).filter(ImageGenHistory.created_at >= cutoff)

    # 总调用
    total = base.count()

    # 成功调用
    success_calls = base.filter(ImageGenHistory.status == STATUS_SUCCESS).count()

    # 失败 + 取消
    failed_calls = base.filter(
        ImageGenHistory.status.in_([STATUS_FAILED, STATUS_CANCELLED])
    ).count()

    # 模型分布：按 model_used 分组（NULL 归类为 "unknown"）
    model_rows = (
        db.query(ImageGenHistory.model_used, func.count(ImageGenHistory.id))
        .filter(ImageGenHistory.created_at >= cutoff)
        .group_by(ImageGenHistory.model_used)
        .all()
    )
    model_distribution = [
        {"model": (m if m else "unknown"), "count": int(c)}
        for m, c in model_rows
    ]

    # 日调用：按日期分组（PostgreSQL：func.date；SQLite 兼容用 func.date）
    daily_rows = (
        db.query(func.date(ImageGenHistory.created_at), func.count(ImageGenHistory.id))
        .filter(ImageGenHistory.created_at >= cutoff)
        .group_by(func.date(ImageGenHistory.created_at))
        .order_by(func.date(ImageGenHistory.created_at))
        .all()
    )
    daily_calls = [
        {"date": str(d), "count": int(c)}
        for d, c in daily_rows
    ]

    success_rate = (success_calls / total) if total > 0 else 0.0

    return {
        "days": days,
        "total_calls": total,
        "success_calls": success_calls,
        "failed_calls": failed_calls,
        "success_rate": round(success_rate, 4),
        "model_distribution": model_distribution,
        "daily_calls": daily_calls,
    }
