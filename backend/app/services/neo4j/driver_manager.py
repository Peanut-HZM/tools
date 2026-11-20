"""AsyncDriver 缓存管理。

每个连接 id 缓存一个 AsyncDriver，闲置 TTL（默认 300s）自动回收；
进程退出 / FastAPI lifespan shutdown 时统一 close_all；
连接删除时同步 close_driver 释放资源。
日志永不打印密码与完整 bolt uri 凭据段。
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 默认闲置回收时间：5 分钟
DEFAULT_TTL_SECONDS = 300


class DriverManager:
    """连接级 AsyncDriver 缓存（内存字典，非线程安全，仅事件循环内使用）。"""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._ttl = ttl_seconds
        # conn_id -> (driver, last_used_epoch)
        self._drivers: Dict[str, Tuple[object, float]] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: Optional[asyncio.Task] = None

    async def get_driver(self, conn_id: str, uri: str, username: str, password: str):
        """获取（或创建）连接对应的 AsyncDriver，并刷新 last_used。"""
        async with self._lock:
            entry = self._drivers.get(conn_id)
            if entry is not None:
                driver, _ = entry
                self._drivers[conn_id] = (driver, time.monotonic())
                return driver

            # 延迟导入：neo4j 包由 Task 5 统一纳入依赖，此处保持可测试
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                uri,
                auth=(username, password),
                connection_timeout=5,
                connection_acquisition_timeout=10,
                notifications_disabled_categories=["UNRECOGNIZED", "UNSUPPORTED", "PERFORMANCE"],
            )
            self._drivers[conn_id] = (driver, time.monotonic())
            self._start_reaper()
            # 日志只打印 uri 的 host:port 段，不打印凭据
            safe_uri = uri.split("@")[-1]
            logger.info("Neo4j driver 已创建: conn=%s uri=%s", conn_id, safe_uri)
            return driver

    async def close_driver(self, conn_id: str) -> None:
        """关闭并移除指定连接的 driver（连接删除 / 更新凭据时调用）。"""
        async with self._lock:
            entry = self._drivers.pop(conn_id, None)
        if entry is not None:
            driver, _ = entry
            try:
                await driver.close()
                logger.info("Neo4j driver 已关闭: conn=%s", conn_id)
            except Exception as exc:  # noqa: BLE001 - close 失败不阻断业务流程
                logger.warning("Neo4j driver 关闭异常: conn=%s err=%s", conn_id, type(exc).__name__)

    async def close_all(self) -> None:
        """关闭全部缓存的 driver（lifespan shutdown / 测试清理）。"""
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
            self._reaper_task = None

        async with self._lock:
            entries = list(self._drivers.items())
            self._drivers.clear()
        for conn_id, (driver, _) in entries:
            try:
                await driver.close()
                logger.info("Neo4j driver 已关闭: conn=%s", conn_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Neo4j driver 关闭异常: conn=%s err=%s", conn_id, type(exc).__name__)

    def _start_reaper(self) -> None:
        """启动闲置回收后台任务（幂等）。"""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reaper_loop())

    async def _reaper_loop(self) -> None:
        """每 60s 扫一遍，回收闲置超过 TTL 的 driver。"""
        try:
            while True:
                await asyncio.sleep(60)
                now = time.monotonic()
                async with self._lock:
                    stale = [
                        conn_id
                        for conn_id, (_, last_used) in self._drivers.items()
                        if now - last_used > self._ttl
                    ]
                for conn_id in stale:
                    logger.info("Neo4j driver 闲置超时回收: conn=%s", conn_id)
                    await self.close_driver(conn_id)
        except asyncio.CancelledError:
            pass


# 全局单例：路由层与 lifespan shutdown 共用
driver_manager = DriverManager()
