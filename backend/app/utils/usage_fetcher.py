"""CLI 子进程调用封装，统一三种数据源（ccusage / opencode-usage / ccusage-opencode）"""

import json
import logging
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional

# 桌面模式检测
_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"

# CLI 工具从用户主目录查找数据（跨平台兼容）
try:
    import pwd
    _uid = os.getuid()
    USER_HOME = pwd.getpwuid(_uid).pw_dir if _uid > 0 else os.path.expanduser("~")
except (ImportError, AttributeError):
    # Windows 平台不支持 pwd 和 os.getuid()
    USER_HOME = os.path.expanduser("~")

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


def _run_cmd(cmd: list[str], timeout: int = 60) -> dict:
    """执行 CLI 命令并解析 JSON 输出"""
    try:
        env = os.environ.copy()
        env["HOME"] = USER_HOME

        # Windows 下确保 Node.js 在 PATH 中（ccusage 等 CLI 依赖 node 运行时）
        if platform.system() == "Windows":
            node_dirs = [
                r"C:\Program Files\nodejs",
                r"C:\Program Files (x86)\nodejs",
                os.path.expanduser(r"~\AppData\Roaming\nvm\current"),
            ]
            node_path = shutil.which("node")
            if node_path:
                node_dirs.append(os.path.dirname(node_path))
            existing_path = env.get("PATH", "")
            env["PATH"] = ";".join(node_dirs) + ";" + existing_path

        # Windows 下已使用完整路径，不需要 shell=True
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=USER_HOME,
            env=env,
        )
        if result.returncode != 0:
            err = result.stderr.strip()[:500] or "CLI 执行失败"
            # 忽略 bun 协议错误（opencode-usage 使用 bun 运行时）
            if "bun:" in err or "ERR_UNSUPPORTED_ESM_URL_SCHEME" in err:
                logger.warning("opencode-usage 需要 bun 运行时，当前环境不支持: %s", err[:200])
                return {"error": "opencode-usage 需要 bun 运行时，当前环境不支持"}
            logger.error("CLI failed: %s -> %s", " ".join(cmd), err)
            return {"error": err}

        output = result.stdout.strip()
        # 尝试找到真正的 JSON 起始位置（跳过日志行中的 [ 或 {）
        json_index = -1
        i = 0
        while i < len(output):
            ch = output[i]
            if ch in ("{", "["):
                # 验证从这里开始是否能解析为有效 JSON
                try:
                    json.loads(output[i:])
                    json_index = i
                    break
                except json.JSONDecodeError:
                    # 不是有效的 JSON 起始，继续向后搜索
                    pass
            i += 1

        if json_index == -1:
            logger.error(f"CLI 输出中没有找到 JSON: stdout[:500]={output[:500]}")
            return {"error": "未找到 JSON 输出"}

        parsed = json.loads(output[json_index:])

        return parsed
    except subprocess.TimeoutExpired:
        return {"error": f"CLI 执行超时（> {timeout}s）"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {str(e)}"}
    except FileNotFoundError:
        return {"error": f"CLI 未安装: {cmd[0]}"}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}"}


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

        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage"}

        cache_key = f"claude:{report_type}:{since}:{until}:{breakdown}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # Windows 下使用完整路径运行 node + index.js
        if platform.system() == "Windows":
            node_exe = shutil.which("node.exe") or shutil.which("node") or "node"
            ccusage_path = os.path.expanduser(
                "~/AppData/Roaming/npm/node_modules/ccusage/dist/index.js"
            )
            cmd = [node_exe, ccusage_path, report_type, "--json", "--offline"]
        else:
            cmd = ["ccusage", report_type, "--json", "--offline"]
        if since:
            cmd += ["--since", since]
        if until:
            cmd += ["--until", until]
        if breakdown:
            cmd.append("--breakdown")

        result = _run_cmd(cmd, timeout=180)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

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

        if shutil.which("opencode-usage") is None:
            return {"error": "CLI 未安装: opencode-usage"}

        cache_key = f"opencode-current:{days}:{by}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # Windows 下使用完整路径运行 node + index.js
        if platform.system() == "Windows":
            node_exe = shutil.which("node.exe") or shutil.which("node") or "node"
            opencode_usage_path = os.path.expanduser(
                "~/AppData/Roaming/npm/node_modules/opencode-usage/dist/index.js"
            )
            cmd = [node_exe, opencode_usage_path, "run", "--json", f"--days={days}"]
        else:
            cmd = ["opencode-usage", "run", "--json", f"--days={days}"]
        if by:
            cmd.append(f"--by={by}")
        else:
            cmd.append("--by=model")

        result = _run_cmd(cmd, timeout=180)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def _fetch_opencode_legacy(days: int) -> dict:
        """调用 ccusage-opencode 获取 3 月前数据"""
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if shutil.which("ccusage-opencode") is None:
            return {
                "error": "CLI 未安装: ccusage-opencode（请先 npm i -g @ccusage/opencode）"
            }

        cache_key = f"opencode-legacy:{days}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # Windows 下使用完整路径运行 node + index.js
        if platform.system() == "Windows":
            node_exe = shutil.which("node.exe") or shutil.which("node") or "node"
            ccusage_opencode_path = os.path.expanduser(
                "~/AppData/Roaming/npm/node_modules/@ccusage/opencode/dist/index.js"
            )
            cmd = [node_exe, ccusage_opencode_path, "daily", "--json"]
        else:
            cmd = ["ccusage-opencode", "daily", "--json"]
        result = _run_cmd(cmd, timeout=120)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

