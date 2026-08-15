"""
采集引擎 - asyncio 后台任务，每 30s 采集所有启用服务器（本机 psutil / 远程 SSH 脚本）
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import psutil

from app.services.monitor import alert_engine
from app.services.monitor.metric_repo import insert_metric
from app.services.monitor.script import BASH_SCRIPT, parse_script_output
from app.services.monitor.server_service import MonitorServerService
from app.services.monitor.ssh_client import pool, SSHCommandError

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 30  # 秒


async def run_command(server, command, timeout=10):
    """远程执行命令（测试可替换）"""
    return await pool.run_command(server, command, timeout)


def update_status(server_id, status, last_error, last_seen_at):
    """更新服务器采集状态（测试可替换）"""
    return MonitorServerService.update_status(server_id, status, last_error, last_seen_at)


def alert_evaluate(server, metrics):
    """告警评估入口（测试可替换）"""
    return alert_engine.evaluate(server, metrics)


def local_metrics() -> Dict:
    """采集本机指标（复用 psutil 与 system_monitor_service）"""
    from app.services.system_monitor_service import get_resource_usage

    net_before = psutil.net_io_counters()
    io_before = psutil.disk_io_counters()
    t0 = time.monotonic()
    usage = get_resource_usage()  # 内部会阻塞约 0.5s 计算 CPU 百分比
    t1 = time.monotonic()
    dt = max(0.1, t1 - t0)
    net_after = psutil.net_io_counters()
    io_after = psutil.disk_io_counters()

    mem = usage["memory"]
    swap = usage["swap"]
    disk = usage["disk"]
    try:
        load_avg = list(psutil.getloadavg())
    except OSError:
        load_avg = [0.0, 0.0, 0.0]

    return {
        "cpu_percent": float(usage["cpu"]["percent"]),
        "cpu_per_core": [float(x) for x in usage["cpu"]["per_cpu"]],
        "load_avg": load_avg,
        "mem_total": int(mem["total"]),
        "mem_used": int(mem["used"]),
        "mem_percent": float(mem["percent"]),
        "swap_total": int(swap["total"]),
        "swap_used": int(swap["used"]),
        "swap_percent": float(swap["percent"]),
        "disk_total": int(disk["total"]),
        "disk_used": int(disk["used"]),
        "disk_percent": float(disk["percent"]),
        "net_recv_rate": max(0.0, (net_after.bytes_recv - net_before.bytes_recv) / dt),
        "net_sent_rate": max(0.0, (net_after.bytes_sent - net_before.bytes_sent) / dt),
        "disk_read_rate": max(0.0, (io_after.read_bytes - io_before.read_bytes) / dt) if io_after and io_before else 0.0,
        "disk_write_rate": max(0.0, (io_after.write_bytes - io_before.write_bytes) / dt) if io_after and io_before else 0.0,
        "process_count": len(psutil.pids()),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


class MonitorCollector:
    """采集引擎：后台循环 + 手动采集"""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ---------- 生命周期 ----------

    async def start(self) -> None:
        """启动后台采集任务"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("监控采集引擎已启动")

    async def stop(self) -> None:
        """停止后台采集任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        pool.close_all()
        logger.info("监控采集引擎已停止")

    async def _loop(self) -> None:
        """后台循环：按全局间隔执行采集周期"""
        while self._running:
            interval = max(10, MonitorServerService.get_global_interval())
            cycle_start = time.monotonic()
            try:
                await self.collect_all()
            except Exception as e:
                logger.error("采集周期异常: %s", str(e), exc_info=True)
            elapsed = time.monotonic() - cycle_start
            await asyncio.sleep(max(1.0, interval - elapsed))

    # ---------- 采集 ----------

    async def collect_all(self, servers: Optional[List[Dict]] = None) -> int:
        """采集一批服务器，返回成功数；单台失败隔离"""
        if servers is None:
            try:
                servers = MonitorServerService.get_enabled_servers()
            except Exception as e:
                logger.error("加载监控服务器失败: %s", str(e))
                return 0
        if not servers:
            return 0
        sem = asyncio.Semaphore(5)
        results = await asyncio.gather(
            *[self._guarded(sem, s) for s in servers],
            return_exceptions=True,
        )
        success = sum(1 for r in results if isinstance(r, dict))
        await asyncio.to_thread(pool.close_idle_connections)
        logger.info("采集周期完成: 共 %d 台，成功 %d 台", len(servers), success)
        return success

    async def _guarded(self, sem: asyncio.Semaphore, server: Dict):
        async with sem:
            return await self.collect_server(server)

    async def collect_server(self, server: Dict) -> Optional[Dict]:
        """采集单台服务器：本机 psutil / 远程 SSH 脚本，成功写入并触发告警评估"""
        server_id = server.get("id")
        try:
            if server.get("server_type") == "local":
                metrics = await asyncio.to_thread(local_metrics)
            else:
                raw = await run_command(server, BASH_SCRIPT, timeout=10)
                metrics = parse_script_output(raw)
                if metrics is None:
                    raise ValueError("采集脚本输出解析失败")
            insert_metric(server_id, metrics)
            update_status(server_id, "online", None, datetime.now())
            # 告警评估放在写入之后，独立 try 防止告警异常影响采集状态
            try:
                alert_evaluate(server, metrics)
            except Exception as e:
                logger.error("告警评估失败: server=%s 错误=%s", server_id, str(e))
            return metrics
        except Exception as e:
            logger.warning("服务器采集失败: id=%s name=%s 错误=%s", server_id, server.get("name"), str(e))
            try:
                update_status(server_id, "offline", str(e)[:200], None)
            except Exception:
                pass
            return None

    async def collect_now(self, server_id: str, user_id: str) -> Optional[Dict]:
        """手动触发采集（重试按钮），不阻塞后台循环"""
        try:
            server = MonitorServerService.get_server(user_id, server_id)
        except Exception as e:
            logger.error("手动采集加载服务器失败: %s", str(e))
            return None
        if not server:
            return None
        return await self.collect_server(server)


monitor_collector = MonitorCollector()
