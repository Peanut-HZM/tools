"""
Task 5.1 — ImageGenHistoryService（历史记录 CRUD + 保留策略）

职责：
  - 增删改查 image_gen_history 记录
  - cleanup_before：供保留策略定时任务调用，按条件清理旧记录
  - update_last_accessed：前端查看图片时刷新访问时间
  - get_result_url：为 result_oss_key 生成新的签名 URL（1 小时有效期）
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.models.image_generation_models import ImageGenHistory
from app.utils.image_gen_constants import (
    OSS_PREFIX_RESULT,
    SIGNED_URL_EXPIRES_RESULT,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_CANCELLED,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    """当前 UTC 时间（带 timezone）"""
    return datetime.now(timezone.utc)


def _gen_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class ImageGenHistoryService:
    """
    图像生成历史服务。

    所有写操作通过传入的 db session 执行，事务由调用方（ImageGenService）控制。
    """

    def __init__(self, db: Session, oss_svc: Any = None):
        """
        初始化。

        Args:
            db: SQLAlchemy session
            oss_svc: OSS 服务实例，用于生成签名 URL。None 时 get_result_url 返回空串。
        """
        self.db = db
        self._oss_svc = oss_svc

    # ------------------------------------------------------------------
    # 创建记录
    # ------------------------------------------------------------------

    def create_record(
        self,
        user_id: str,
        operation: str,
        status: str,
        result_oss_key: str = "",
        prompt: Optional[str] = None,
        params: Optional[dict] = None,
        reference_oss_key: Optional[str] = None,
        mask_oss_key: Optional[str] = None,
        model_used: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        conversation_id: Optional[str] = None,
    ) -> ImageGenHistory:
        """
        创建一条历史记录。

        Args:
            user_id: 用户 ID
            operation: 操作类型 (text2img / img2img / inpaint / upload_edit)
            status: 状态 (success / failed / cancelled)
            result_oss_key: 结果图 OSS key（失败/取消时为空串）
            prompt: 提示词
            params: 操作参数 JSON（size, n, style, strength, model_preference 等）
            reference_oss_key: 参考图 OSS key
            mask_oss_key: 蒙版图 OSS key
            model_used: 实际使用的模型
            error_message: 错误信息（失败时）
            duration_ms: 耗时（毫秒）
            conversation_id: 关联的多轮对话 ID（对话生成时写入）
        """
        record = ImageGenHistory(
            id=_gen_uuid(),
            user_id=user_id,
            operation=operation,
            status=status,
            result_oss_key=result_oss_key,
            prompt=prompt,
            params=params,
            reference_oss_key=reference_oss_key,
            mask_oss_key=mask_oss_key,
            model_used=model_used,
            error_message=error_message,
            duration_ms=duration_ms,
            conversation_id=conversation_id,
        )
        self.db.add(record)
        # 立即 flush 以便调用方拿到 id（事务尚未 commit）
        self.db.flush()
        logger.debug(
            "历史记录已创建: id=%s user=%s op=%s status=%s",
            record.id, user_id, operation, status,
        )
        return record

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_record(self, user_id: str, history_id: str) -> Optional[ImageGenHistory]:
        """
        获取单条记录（仅返回未删除的）。

        Args:
            user_id: 用户 ID（安全校验 — 不能跨用户查看）
            history_id: 历史记录 ID
        """
        return (
            self.db.query(ImageGenHistory)
            .filter(
                ImageGenHistory.id == history_id,
                ImageGenHistory.user_id == user_id,
                ImageGenHistory.is_deleted == False,  # noqa: E712
            )
            .first()
        )

    def list_records(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        operation: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ImageGenHistory]:
        """
        分页列出用户的历史记录（仅未删除的）。

        Args:
            user_id: 用户 ID
            skip: 跳过条数
            limit: 每页条数
            operation: 按操作类型筛选（可选）
            status: 按状态筛选（可选）
        """
        q = (
            self.db.query(ImageGenHistory)
            .filter(
                ImageGenHistory.user_id == user_id,
                ImageGenHistory.is_deleted == False,  # noqa: E712
            )
        )
        if operation is not None:
            q = q.filter(ImageGenHistory.operation == operation)
        if status is not None:
            q = q.filter(ImageGenHistory.status == status)

        return (
            q.order_by(ImageGenHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # 软删除
    # ------------------------------------------------------------------

    def soft_delete(self, user_id: str, history_id: str) -> bool:
        """
        软删除一条记录（设置 is_deleted=True）。

        返回是否成功删除（记录不存在或已删除时返回 False）。
        """
        record = (
            self.db.query(ImageGenHistory)
            .filter(
                ImageGenHistory.id == history_id,
                ImageGenHistory.user_id == user_id,
                ImageGenHistory.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if record is None:
            return False
        record.is_deleted = True
        self.db.flush()
        logger.debug("历史记录软删除: id=%s user=%s", history_id, user_id)
        return True

    # ------------------------------------------------------------------
    # 保留策略
    # ------------------------------------------------------------------

    def cleanup_before(
        self,
        cutoff: datetime,
        mode: str = "by_date",
        dry_run: bool = False,
    ) -> int:
        """
        按条件清理旧记录，返回删除数量。

        Args:
            cutoff: 截止时间（created_at 或 last_accessed_at 早于此值的记录将被删除）
            mode:
              - "by_date"：按 created_at < cutoff 删除
              - "unused_for_n_days"：按 last_accessed_at < cutoff 删除
                （last_accessed_at 为 NULL 时以 created_at 代替）
            dry_run: 仅统计不实际删除
        """
        q = self.db.query(ImageGenHistory)

        if mode == "by_date":
            q = q.filter(ImageGenHistory.created_at < cutoff)
        elif mode == "unused_for_n_days":
            # last_accessed_at 为 NULL 时用 created_at 代替
            from sqlalchemy import or_, and_
            q = q.filter(
                or_(
                    ImageGenHistory.last_accessed_at < cutoff,
                    and_(
                        ImageGenHistory.last_accessed_at.is_(None),
                        ImageGenHistory.created_at < cutoff,
                    ),
                )
            )
        else:
            logger.warning("未知的 cleanup mode: %s，跳过", mode)
            return 0

        count = q.count()
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            self.db.flush()
            logger.info("保留策略清理: mode=%s cutoff=%s 删除 %d 条", mode, cutoff, count)

        return count

    # ------------------------------------------------------------------
    # 访问时间更新
    # ------------------------------------------------------------------

    def update_last_accessed(self, history_id: str) -> None:
        """刷新 last_accessed_at 为当前时间。"""
        record = (
            self.db.query(ImageGenHistory)
            .filter(ImageGenHistory.id == history_id)
            .first()
        )
        if record is not None:
            record.last_accessed_at = _now_utc()
            self.db.flush()

    # ------------------------------------------------------------------
    # 签名 URL
    # ------------------------------------------------------------------

    def get_result_url(self, history: ImageGenHistory) -> str:
        """
        为历史记录的 result_oss_key 生成新的签名 URL（1 小时有效期）。

        result_oss_key 为空串或 oss_svc 为 None 时返回空串。
        """
        if not history.result_oss_key or self._oss_svc is None:
            return ""
        try:
            return self._oss_svc.sign_url("GET", history.result_oss_key, SIGNED_URL_EXPIRES_RESULT)
        except Exception:
            logger.error(
                "生成签名 URL 失败: key=%s", history.result_oss_key, exc_info=True,
            )
            return ""
