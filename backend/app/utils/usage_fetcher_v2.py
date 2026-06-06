"""ccusage 统一数据源调用层（v2）。"""
import logging
import os
import shutil
from typing import Optional

from app.utils.usage_fetcher import (
    _get_from_cache,
    _run_cmd,
    _set_cache,
    _DESKTOP_MODE,
)

logger = logging.getLogger(__name__)


class UsageFetcherV2:
    """ccusage 统一数据源调用层"""

    _ccusage_path: Optional[str] = None

    @staticmethod
    def _find_ccusage() -> Optional[str]:
        """查找 ccusage 命令路径，支持 PATH 和已知路径兜底。"""
        if UsageFetcherV2._ccusage_path is not None:
            return UsageFetcherV2._ccusage_path

        # 1. 尝试 PATH 查找
        path = shutil.which("ccusage")
        if path and os.path.exists(path):
            UsageFetcherV2._ccusage_path = path
            logger.info(f"[ccusage-v2] 找到 ccusage: {path}")
            return path

        # 2. 尝试已知路径（Windows npm 全局安装常见位置）
        known_paths = [
            os.path.expanduser(r"~\AppData\Roaming\npm\ccusage.cmd"),
            os.path.expanduser(r"~\AppData\Roaming\npm\ccusage.ps1"),
            os.path.expanduser(r"~\AppData\Roaming\npm\ccusage"),
            os.path.expanduser(r"~\AppData\Local\pnpm\ccusage.cmd"),
            os.path.expanduser(r"~\AppData\Local\pnpm\ccusage"),
            "/usr/local/bin/ccusage",
            "/usr/bin/ccusage",
        ]
        for p in known_paths:
            if os.path.exists(p):
                UsageFetcherV2._ccusage_path = p
                logger.info(f"[ccusage-v2] 在已知路径找到 ccusage: {p}")
                return p

        logger.warning(f"[ccusage-v2] 未找到 ccusage。PATH 片段: {os.environ.get('PATH', '')[:300]}")
        return None

    @staticmethod
    def fetch_ccusage_daily(since: str, until: str) -> dict:
        """调用 ccusage daily --json 返回所有 agent 的当日聚合 + modelBreakdowns"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if UsageFetcherV2._find_ccusage() is None:
            return {"error": "CLI 未安装: ccusage（请先 npm i -g ccusage）"}

        ccusage_path = UsageFetcherV2._find_ccusage()
        if ccusage_path is None:
            return {"error": "CLI 未安装: ccusage（请先 npm i -g ccusage）"}

        cache_key = f"ccusage-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = [
            ccusage_path, "daily",
            "--json",
            f"--since={since}",
            f"--until={until}",
            "--offline",
        ]
        result = _run_cmd(cmd, timeout=180)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def fetch_ccusage_agent_daily(agent: str, since: str, until: str) -> dict:
        """调用 ccusage <agent> daily --json 返回指定 agent 的每日聚合 + modelsUsed"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        ccusage_path = UsageFetcherV2._find_ccusage()
        if ccusage_path is None:
            return {"error": "CLI 未安装: ccusage"}

        cache_key = f"ccusage-{agent}-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = [
            ccusage_path, agent, "daily",
            "--json",
            f"--since={since}",
            f"--until={until}",
            "--offline",
        ]
        result = _run_cmd(cmd, timeout=120)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result
