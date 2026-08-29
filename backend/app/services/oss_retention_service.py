"""OSS 保留策略服务：根据配置清理过期的图像生成 OSS 文件。"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.image_generation_models import (
    ImageGenRetentionConfig,
    ImageGenHistory,
)

# 内联保留策略常量（原 image_gen_constants.py 已随 Dify 旧实现删除）
RETENTION_MODE_KEEP_FOREVER = "keep_forever"
RETENTION_MODE_DELETE_AFTER_N_DAYS = "delete_after_n_days"
RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS = "delete_if_unused_for_n_days"

logger = logging.getLogger(__name__)

# 兼容 brief 中描述的模式别名，映射到项目内实际常量
MODE_BY_DATE = RETENTION_MODE_DELETE_AFTER_N_DAYS        # "delete_after_n_days"
MODE_BY_UNUSED = RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS  # "delete_if_unused_for_n_days"
MODE_KEEP_FOREVER = RETENTION_MODE_KEEP_FOREVER          # "keep_forever"


class OssRetentionService:
    """OSS 文件保留策略服务。

    根据 DB 中的 ``ImageGenRetentionConfig`` 配置，查询过期的 ``ImageGenHistory``
    记录，删除对应的 OSS 文件并将 DB 记录标记为 ``is_deleted=True``。
    """

    def __init__(self, db: Session, oss_svc):
        """
        Args:
            db: SQLAlchemy 数据库会话
            oss_svc: 项目 OssService 实例（提供 ``delete_file(key)`` 方法）
        """
        self._db = db
        self._oss_svc = oss_svc

    # ------------------------------------------------------------------
    # 配置管理
    # ------------------------------------------------------------------

    def _get_config(self) -> ImageGenRetentionConfig:
        """获取配置；不存在时自动创建默认配置。"""
        config = self._db.query(ImageGenRetentionConfig).first()
        if not config:
            config = ImageGenRetentionConfig(
                mode=RETENTION_MODE_KEEP_FOREVER,
                n_days=30,
                cleanup_cron="0 3 * * *",
                enabled=True,
            )
            self._db.add(config)
            self._db.commit()
            self._db.refresh(config)
        return config

    def get_config(self) -> ImageGenRetentionConfig:
        """返回当前保留策略配置。"""
        return self._get_config()

    def update_config(
        self,
        mode: Optional[str] = None,
        retention_days: Optional[int] = None,
        cron_expression: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> ImageGenRetentionConfig:
        """更新保留策略配置。未提供的字段保持不变。

        参数名沿用 brief 约定，内部映射到实际 DB 列名：
            - retention_days → n_days
            - cron_expression → cleanup_cron
        """
        config = self._get_config()
        if mode is not None:
            config.mode = mode
        if retention_days is not None:
            config.n_days = retention_days
        if cron_expression is not None:
            config.cleanup_cron = cron_expression
        if enabled is not None:
            config.enabled = enabled
        self._db.commit()
        self._db.refresh(config)
        return config

    # ------------------------------------------------------------------
    # 清理逻辑
    # ------------------------------------------------------------------

    def run_cleanup(self) -> dict:
        """执行一次清理。

        返回摘要字典：
            - deleted_count: 成功删除的记录数
            - failed_count:  OSS 删除失败的记录数
            - skipped:       是否跳过清理（disabled / keep_forever / 未知模式）
            - mode:          当前配置的模式
            - retention_days: 当前配置的保留天数
            - cutoff:        截止时间的 ISO 格式字符串（跳过时为 None）
        """
        config = self._get_config()

        # 未启用清理
        if not config.enabled:
            logger.info("[image-gen-retention] 清理已禁用，跳过")
            return {
                "deleted_count": 0,
                "failed_count": 0,
                "skipped": True,
                "reason": "disabled",
                "mode": config.mode,
                "retention_days": config.n_days,
                "cutoff": None,
            }

        # keep_forever 模式：不清理任何文件
        if config.mode == RETENTION_MODE_KEEP_FOREVER:
            logger.info("[image-gen-retention] 模式为 keep_forever，跳过清理")
            return {
                "deleted_count": 0,
                "failed_count": 0,
                "skipped": True,
                "reason": "keep_forever",
                "mode": config.mode,
                "retention_days": config.n_days,
                "cutoff": None,
            }

        cutoff = datetime.utcnow() - timedelta(days=config.n_days)

        # 按创建时间查询过期记录
        if config.mode == RETENTION_MODE_DELETE_AFTER_N_DAYS:
            records = (
                self._db.query(ImageGenHistory)
                .filter(
                    ImageGenHistory.created_at < cutoff,
                    ImageGenHistory.is_deleted == False,  # noqa: E712
                )
                .all()
            )
        # 按最后访问时间查询过期记录
        elif config.mode == RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS:
            records = (
                self._db.query(ImageGenHistory)
                .filter(
                    ImageGenHistory.last_accessed_at < cutoff,
                    ImageGenHistory.is_deleted == False,  # noqa: E712
                )
                .all()
            )
        else:
            logger.warning(f"[image-gen-retention] 未知模式: {config.mode}")
            return {
                "deleted_count": 0,
                "failed_count": 0,
                "skipped": True,
                "reason": "unknown_mode",
                "mode": config.mode,
                "retention_days": config.n_days,
                "cutoff": None,
            }

        deleted_count = 0
        failed_count = 0

        for record in records:
            try:
                # 1. 删除 OSS 文件（若存在）
                if record.result_oss_key:
                    delete_ok = self._oss_svc.delete_file(record.result_oss_key)
                    if not delete_ok:
                        raise RuntimeError(
                            f"OSS delete_file 返回 False: {record.result_oss_key}"
                        )
                # 2. 标记 DB 记录为已删除
                record.is_deleted = True
                deleted_count += 1
            except Exception as e:
                logger.warning(
                    f"[image-gen-retention] 删除记录 {record.id} 失败: {e}"
                )
                failed_count += 1

        self._db.commit()
        logger.info(
            f"[image-gen-retention] 清理完成：{deleted_count} 成功，{failed_count} 失败"
        )
        return {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "skipped": False,
            "mode": config.mode,
            "retention_days": config.n_days,
            "cutoff": cutoff.isoformat(),
        }
