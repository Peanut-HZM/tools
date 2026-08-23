"""
图像生成工具 - 内存态降级服务

跟踪连续失败次数，达到阈值时触发"降级"（拒绝后续请求一段时间）。
- 内存状态：`_failure_count`, `_degraded_until` — 不持久化（项目单进程 uvicorn，线程安全即可）。
- 配置持久化：`ImageGenDegradationConfig`（DB 单行表，admin 可调）。
- 设计要点：
  * `record_success` 只重置失败计数，不解除正在进行的降级（避免偶发成功打断保护窗口）。
  * `reset` 为管理员手动解除降级入口。
  * `enabled=False` 时整个降级机制不生效（admin 临时关闭用）。
"""

import threading
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.image_generation_models import ImageGenDegradationConfig

logger = logging.getLogger(__name__)


class DegradationService:
    """内存态降级服务 — 跟踪连续失败次数并在达到阈值时触发降级。"""

    def __init__(self, db: Session):
        self._db = db
        self._lock = threading.Lock()  # 并发安全（单进程多线程场景）
        self._failure_count = 0
        self._degraded_until: Optional[datetime] = None

    # ------------------------------------------------------------------
    # 配置读写
    # ------------------------------------------------------------------

    def _get_config(self) -> ImageGenDegradationConfig:
        """读取 DB 配置（单行表）。不存在则创建默认配置。"""
        config = self._db.query(ImageGenDegradationConfig).first()
        if not config:
            config = ImageGenDegradationConfig(
                enabled=True,
                failure_threshold=3,
                degrade_duration_seconds=300,
                updated_by="system",
            )
            self._db.add(config)
            self._db.commit()
            self._db.refresh(config)
            logger.info("[image-gen-degradation] 已创建默认降级配置")
        return config

    def get_config(self) -> ImageGenDegradationConfig:
        """对外暴露的配置读取入口。"""
        return self._get_config()

    def update_config(
        self,
        failure_threshold: Optional[int] = None,
        degrade_duration_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
        updated_by: Optional[str] = None,
    ) -> ImageGenDegradationConfig:
        """更新降级配置（admin 接口调用）。"""
        config = self._get_config()
        if failure_threshold is not None:
            config.failure_threshold = failure_threshold
        if degrade_duration_seconds is not None:
            config.degrade_duration_seconds = degrade_duration_seconds
        if enabled is not None:
            config.enabled = enabled
        if updated_by is not None:
            config.updated_by = updated_by
        # 触发 SQLAlchemy 的 onupdate / 手动写 updated_at
        config.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(config)
        logger.info(
            f"[image-gen-degradation] 配置已更新: threshold={config.failure_threshold}, "
            f"duration={config.degrade_duration_seconds}s, enabled={config.enabled}"
        )
        return config

    # ------------------------------------------------------------------
    # 核心降级逻辑
    # ------------------------------------------------------------------

    def is_degraded(self) -> bool:
        """
        当前是否处于降级状态。
        - `enabled=False`：永远返回 False（降级功能被关闭）。
        - 已降级但时间已到：自动解除并返回 False。
        """
        with self._lock:
            # 功能被关闭 → 视为未降级
            config = self._get_config()
            if not config.enabled:
                # 顺便清理状态，避免反复进入降级分支
                self._degraded_until = None
                self._failure_count = 0
                return False

            if self._degraded_until is None:
                return False

            now = datetime.now(timezone.utc)
            # 兼容：若 _degraded_until 是 naive datetime，视为 UTC
            until = self._degraded_until
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)

            if now >= until:
                # 降级窗口到期 → 自动解除
                self._degraded_until = None
                self._failure_count = 0
                logger.info("[image-gen-degradation] 降级窗口到期，自动解除")
                return False
            return True

    def record_failure(self) -> None:
        """
        记录一次失败。连续失败达到阈值时触发降级。
        `enabled=False` 时不触发降级（计数也不累积，避免开关切换后状态错乱）。
        """
        with self._lock:
            config = self._get_config()
            if not config.enabled:
                # 功能关闭：不累积计数
                return

            self._failure_count += 1

            if self._failure_count >= config.failure_threshold:
                self._degraded_until = datetime.now(timezone.utc) + timedelta(
                    seconds=config.degrade_duration_seconds
                )
                logger.warning(
                    f"[image-gen-degradation] 连续失败 {self._failure_count} 次 "
                    f"(阈值 {config.failure_threshold})，"
                    f"降级 {config.degrade_duration_seconds} 秒，"
                    f"直至 {self._degraded_until.isoformat()}"
                )

    def record_success(self) -> None:
        """
        记录一次成功。重置 failure_count，但不解除正在进行的降级。
        设计理由：一次成功说明当前可用，但不应打断已触发的保护窗口。
        """
        with self._lock:
            self._failure_count = 0

    def reset(self) -> None:
        """
        手动解除降级（admin 操作）。
        同时清零 failure_count 与 _degraded_until。
        """
        with self._lock:
            self._degraded_until = None
            self._failure_count = 0
            logger.info("[image-gen-degradation] 管理员手动重置降级状态")

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """
        返回当前降级状态（admin 接口使用）。
        """
        config = self._get_config()
        with self._lock:
            degraded = False
            if config.enabled and self._degraded_until is not None:
                now = datetime.now(timezone.utc)
                until = self._degraded_until
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                degraded = now < until

            return {
                "degraded": degraded,
                "enabled": config.enabled,
                "degraded_until": (
                    self._degraded_until.isoformat() if self._degraded_until else None
                ),
                "failure_count": self._failure_count,
                "failure_threshold": config.failure_threshold,
                "degrade_duration_seconds": config.degrade_duration_seconds,
            }
