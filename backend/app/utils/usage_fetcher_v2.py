"""
Author: Peanut
Created: 2026-06-19
Purpose: ccusage 统一数据源调用层（v2），基于 ccusage_invoker 实现跨平台支持。
"""
import logging
import os
from typing import Optional

from app.utils.usage_fetcher import (
    _get_from_cache,
    _set_cache,
    _DESKTOP_MODE,
)
from app.utils.ccusage_invoker import (
    ErrorCode,
    find_ccusage,
    run_ccusage,
)

logger = logging.getLogger(__name__)


def _err_to_dict(err) -> dict:
    """CcusageError 转 HTTP 错误响应（保持向后兼容的 detail 字段）"""
    d = err.to_dict()
    return {"error": d["message"], "error_code": d["code"], "remediation": d["remediation"], "details": d["details"]}


class UsageFetcherV2:
    """ccusage 统一数据源调用层"""

    _ccusage_path: Optional[str] = None

    @staticmethod
    def _find_ccusage() -> Optional[str]:
        """查找 ccusage 命令路径"""
        return find_ccusage()

    @staticmethod
    def fetch_ccusage_daily(since: str, until: str) -> dict:
        """调用 ccusage daily --json 返回所有 agent 的当日聚合 + modelBreakdowns"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if find_ccusage() is None:
            return {"error": "CLI 未安装: ccusage（请先 npm i -g ccusage）", "error_code": ErrorCode.CLI_NOT_FOUND, "remediation": "请运行 `npm i -g ccusage` 安装 ccusage"}

        cache_key = f"ccusage-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        result = run_ccusage(
            ["daily", "--json", f"--since={since}", f"--until={until}", "--offline"],
            timeout=180,
        )
        if result["ok"]:
            _set_cache(cache_key, result["data"])
            return result["data"]
        return _err_to_dict(result["error"])

    @staticmethod
    def fetch_ccusage_agent_daily(agent: str, since: str, until: str) -> dict:
        """调用 ccusage <agent> daily --json 返回指定 agent 的每日聚合 + modelsUsed"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if find_ccusage() is None:
            return {"error": "CLI 未安装: ccusage", "error_code": ErrorCode.CLI_NOT_FOUND, "remediation": "请运行 `npm i -g ccusage` 安装 ccusage"}

        cache_key = f"ccusage-{agent}-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        result = run_ccusage(
            [agent, "daily", "--json", f"--since={since}", f"--until={until}", "--offline"],
            timeout=120,
        )
        if result["ok"]:
            _set_cache(cache_key, result["data"])
            return result["data"]
        return _err_to_dict(result["error"])
