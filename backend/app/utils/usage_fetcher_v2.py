"""ccusage 统一数据源调用层（v2）。"""
import logging
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

    @staticmethod
    def fetch_ccusage_daily(since: str, until: str) -> dict:
        """调用 ccusage daily --json 返回所有 agent 的当日聚合 + modelBreakdowns"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage（请先 npm i -g ccusage）"}

        cache_key = f"ccusage-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = [
            "ccusage", "daily",
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

        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage"}

        cache_key = f"ccusage-{agent}-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = [
            "ccusage", agent, "daily",
            "--json",
            f"--since={since}",
            f"--until={until}",
            "--offline",
        ]
        result = _run_cmd(cmd, timeout=120)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result
