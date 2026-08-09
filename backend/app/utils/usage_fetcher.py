"""CLI 子进程调用封装，统一三种数据源（ccusage / opencode-usage / ccusage-opencode）"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from app.utils.ccusage_invoker import run_ccusage, run_generic_cli

# 桌面模式检测
_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"

logger = logging.getLogger(__name__)

# 3 月为界
OPCODE_CUTOFF = datetime(2026, 3, 1)

# 简单内存缓存
_cache = {}
_CACHE_TTL = 300  # 5 分钟


def _get_from_cache(key: str) -> Optional[dict]:
    cached = _cache.get(key)
    if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]
    _cache.pop(key, None)
    return None


def _set_cache(key: str, data: dict) -> None:
    _cache[key] = {"ts": time.time(), "data": data}


class UsageFetcher:
    """统一封装三种数据源的 CLI 调用"""

    @staticmethod
    def fetch_claude(
        report_type: str = "daily",
        since: Optional[str] = None,
        until: Optional[str] = None,
        breakdown: bool = False,
    ) -> dict:
        """调用 ccusage 获取 Claude Code token 统计"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        cache_key = f"claude:{report_type}:{since}:{until}:{breakdown}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        args = [report_type, "--json", "--offline"]
        if since:
            args += ["--since", since]
        if until:
            args += ["--until", until]
        if breakdown:
            args.append("--breakdown")

        result = run_ccusage(args, timeout=180)
        if result["ok"]:
            data = result["data"]
            _set_cache(cache_key, data)
            return data
        else:
            error = result["error"]
            return {"error": f"{error.code}: {error.message}"}

    @staticmethod
    def fetch_opencode(
        days: int = 30,
        by: Optional[str] = None,
    ) -> dict:
        """根据查询范围智能选择数据源，跨越3月时合并两个工具"""
        since_date = datetime.now() - timedelta(days=days)
        now = datetime.now()

        if since_date >= OPCODE_CUTOFF:
            return UsageFetcher._fetch_opencode_current(days, by)
        if now < OPCODE_CUTOFF:
            return UsageFetcher._fetch_opencode_legacy(days)
        return UsageFetcher._fetch_opencode_merged(days, by)

    @staticmethod
    def _fetch_opencode_merged(days: int, by: Optional[str] = None) -> dict:
        """同时调用 opencode-usage 和 ccusage-opencode，按日期智能合并
        合并原则：
        1. 优先使用 opencode-usage 数据（较新，数据更完整）
        2. 用 ccusage-opencode 补充缺失的日期
        """
        current_result = UsageFetcher._fetch_opencode_current(days, by)
        legacy_result = UsageFetcher._fetch_opencode_legacy(days)

        if "error" in current_result and "error" in legacy_result:
            return {
                "error": f"opencode-usage: {current_result['error']}; ccusage-opencode: {legacy_result['error']}"
            }

        current_entries = (
            current_result.get("rows", []) if "error" not in current_result else []
        )
        legacy_entries = (
            legacy_result.get("daily", []) if "error" not in legacy_result else []
        )

        def _get_date(entry: dict) -> str:
            return entry.get("date") or entry.get("label") or ""

        merged: dict[str, dict] = {}

        # Step 1: 先把所有 opencode-usage 数据放入合并结果
        for entry in current_entries:
            d = _get_date(entry)
            if d:
                merged[d] = entry

        # Step 2: 获取 opencode-usage 已经有的日期
        current_dates = set(merged.keys())

        # Step 3: 补充 ccusage-opencode 中有但 opencode-usage 没有的日期
        for entry in legacy_entries:
            d = _get_date(entry)
            if d and d not in current_dates:
                merged[d] = entry

        sorted_entries = sorted(merged.values(), key=_get_date)
        return {"daily": sorted_entries}

    @staticmethod
    def _fetch_opencode_current(days: int, by: Optional[str] = None) -> dict:
        """调用 opencode-usage 获取 3 月后数据"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        cache_key = f"opencode-current:{days}:{by}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        args = ["run", "--json", f"--days={days}"]
        if by:
            args.append(f"--by={by}")
        else:
            args.append("--by=model")

        result = run_generic_cli("opencode-usage", args, timeout=180)
        if result["ok"]:
            data = result["data"]
            _set_cache(cache_key, data)
            return data
        else:
            error = result["error"]
            return {"error": f"{error.code}: {error.message}"}

    @staticmethod
    def _fetch_opencode_legacy(days: int) -> dict:
        """调用 ccusage-opencode 获取 3 月前数据"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        cache_key = f"opencode-legacy:{days}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        args = ["daily", "--json"]
        result = run_generic_cli("ccusage-opencode", args, timeout=120)
        if result["ok"]:
            data = result["data"]
            _set_cache(cache_key, data)
            return data
        else:
            error = result["error"]
            return {"error": f"{error.code}: {error.message}"}

