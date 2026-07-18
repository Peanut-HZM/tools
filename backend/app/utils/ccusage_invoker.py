"""
Author: Peanut
Created: 2026-06-19
Purpose: 统一的 ccusage CLI 调用器，提供跨平台路径发现和结构化错误。
"""
from __future__ import annotations

import glob
import json
import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ErrorCode:
    """ccusage 调用错误的统一编码"""

    CLI_NOT_FOUND = "CLI_NOT_FOUND"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    EXEC_TIMEOUT = "EXEC_TIMEOUT"
    INVALID_JSON_OUTPUT = "INVALID_JSON_OUTPUT"
    CLI_EXECUTION_ERROR = "CLI_EXECUTION_ERROR"


@dataclass
class CcusageError:
    """ccusage 调用的结构化错误"""

    code: str
    message: str
    remediation: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
            "details": self.details,
        }


# 模块级缓存
_ccusage_path: Optional[str] = None
_node_path: Optional[str] = None
_cli_path_cache: dict[str, Optional[str]] = {}


def _expand_user(path: str) -> str:
    """跨平台展开 ~ 路径"""
    return os.path.expanduser(path)


def _node_search_paths() -> list[str]:
    """根据当前操作系统返回 node 候选路径列表"""
    system = platform.system()
    home = _expand_user("~")

    if system == "Windows":
        return [
            r"C:\Program Files\nodejs\node.exe",
            r"C:\Program Files (x86)\nodejs\node.exe",
            os.path.join(home, "AppData", "Roaming", "nvm", "current", "node.exe"),
        ]

    # macOS / Linux
    paths = [
        "/usr/local/bin/node",
        "/usr/bin/node",
        os.path.join(home, ".npm-global", "bin", "node"),
    ]
    if system == "Darwin":
        paths.append("/opt/homebrew/bin/node")
    # NVM 多版本目录（glob 展开）
    paths.extend(sorted(glob.glob(os.path.join(home, ".nvm", "versions", "node", "*", "bin", "node"))))
    return paths


def find_node() -> Optional[str]:
    """查找 Node.js 可执行文件路径；未找到返回 None"""
    global _node_path
    if _node_path is not None:
        return _node_path

    # 优先使用 PATH 中的 node
    which_result = shutil.which("node")
    if which_result and os.path.exists(which_result):
        _node_path = which_result
        logger.info("[ccusage-invoker] 从 PATH 找到 node: %s", which_result)
        return _node_path

    for p in _node_search_paths():
        if os.path.exists(p):
            _node_path = p
            logger.info("[ccusage-invoker] 找到 node: %s", p)
            return _node_path

    logger.warning("[ccusage-invoker] 未找到 node。系统: %s", platform.system())
    return None


def _ccusage_search_paths() -> list[str]:
    """根据当前操作系统返回 ccusage 候选路径列表"""
    system = platform.system()
    home = _expand_user("~")

    if system == "Windows":
        return [
            os.path.join(home, "AppData", "Roaming", "npm", "ccusage.cmd"),
            os.path.join(home, "AppData", "Roaming", "npm", "ccusage.ps1"),
            os.path.join(home, "AppData", "Roaming", "npm", "ccusage"),
            os.path.join(home, "AppData", "Local", "pnpm", "ccusage.cmd"),
            os.path.join(home, "AppData", "Local", "pnpm", "ccusage"),
            r"C:\Program Files\nodejs\ccusage.cmd",
        ]

    paths = [
        "/usr/local/bin/ccusage",
        "/usr/bin/ccusage",
        os.path.join(home, ".npm-global", "bin", "ccusage"),
    ]
    if system == "Darwin":
        paths.insert(0, "/opt/homebrew/bin/ccusage")
        paths.append(os.path.join(home, "Library", "pnpm", "ccusage"))
    elif system == "Linux":
        paths.append(os.path.join(home, ".local", "share", "pnpm", "ccusage"))

    # NVM 多版本目录
    paths.extend(sorted(glob.glob(os.path.join(home, ".nvm", "versions", "node", "*", "bin", "ccusage"))))
    return paths


def find_ccusage() -> Optional[str]:
    """查找 ccusage 可执行文件路径；未找到返回 None"""
    global _ccusage_path
    if _ccusage_path is not None:
        return _ccusage_path

    # 优先使用 PATH 中的 ccusage
    which_result = shutil.which("ccusage")
    if which_result and os.path.exists(which_result):
        _ccusage_path = which_result
        logger.info("[ccusage-invoker] 从 PATH 找到 ccusage: %s", which_result)
        return _ccusage_path

    for p in _ccusage_search_paths():
        if os.path.exists(p):
            _ccusage_path = p
            logger.info("[ccusage-invoker] 找到 ccusage: %s", p)
            return _ccusage_path

    logger.warning(
        "[ccusage-invoker] 未找到 ccusage。系统: %s，PATH 片段: %s",
        platform.system(),
        os.environ.get("PATH", "")[:200],
    )
    return None


def build_cmd(args: list[str]) -> list[str]:
    """根据当前平台构造 ccusage 执行命令。

    Windows 下 .cmd / .ps1 文件需要通过 node 直接调用 JS 入口，绕开 .cmd 内部
    的 node 解析（service 进程 PATH 经常不含 Node.js）。
    """
    ccusage_path = find_ccusage()
    if ccusage_path is None:
        return []

    # Windows 下 .cmd / .ps1 改用 node 直接调用
    if os.name == "nt" and ccusage_path.lower().endswith((".cmd", ".ps1")):
        node_path = find_node()
        if not node_path:
            return []
        npm_dir = os.path.dirname(ccusage_path)
        js_path = os.path.join(npm_dir, "node_modules", "ccusage", "dist", "cli.js")
        if not os.path.exists(js_path):
            return []
        return [node_path, js_path] + list(args)

    return [ccusage_path] + list(args)


def _make_cli_not_found_error(searched: list[str] | None = None) -> CcusageError:
    return CcusageError(
        code=ErrorCode.CLI_NOT_FOUND,
        message="未找到 ccusage 命令",
        remediation="请运行 `npm i -g ccusage` 安装 ccusage",
        details={"searched_paths": (searched or [])[:5]},
    )


def _make_node_not_found_error() -> CcusageError:
    return CcusageError(
        code=ErrorCode.NODE_NOT_FOUND,
        message="未找到 Node.js，ccusage 依赖 node 运行时",
        remediation="请先安装 Node.js: https://nodejs.org",
        details={"platform": platform.system()},
    )


def _sanitize_env(env: dict) -> tuple[dict, list[tuple[str, str]]]:
    """净化环境变量字典，确保所有值都是字符串。

    Python 3.9+ 的 subprocess.run 严格要求 env 值都是字符串类型。
    Linux 服务器的 systemd/Docker 可能注入 bytes/None/int 等非字符串值，
    此函数负责清洗这些异常值，并返回被跳过的 key 列表供日志记录。

    Returns:
        (sanitized_env, skipped_keys) — sanitized_env 是只含 str 值的 dict，
        skipped_keys 是 [(key, type_description), ...] 列表。
    """
    sanitized = {}
    skipped_keys = []
    for key, value in env.items():
        if value is None:
            skipped_keys.append((key, "None"))
            continue
        if isinstance(value, bytes):
            try:
                sanitized[key] = value.decode("utf-8", errors="replace")
            except Exception:
                skipped_keys.append((key, f"{type(value).__name__}"))
                continue
        elif not isinstance(value, str):
            try:
                sanitized[key] = str(value)
            except Exception:
                skipped_keys.append((key, f"{type(value).__name__}"))
                continue
        else:
            sanitized[key] = value
    return sanitized, skipped_keys


def _execute_and_parse(cmd: list[str], cli_name: str, timeout: int) -> dict:
    """执行命令并解析 JSON 输出的通用 helper"""
    try:
        env = os.environ.copy()
        # 使用真实 HOME（config.py 会覆盖 HOME 为 CACHE_DIR，
        # 但 ccusage 等 CLI 工具依赖 HOME 读取 ~/.claude 等 agent 数据目录）
        try:
            from app.config.config import REAL_HOME
            env["HOME"] = REAL_HOME
        except Exception:
            env["HOME"] = _expand_user("~")
        if os.name == "nt":
            node_path = find_node()
            if node_path:
                env["PATH"] = os.path.dirname(node_path) + ";" + env.get("PATH", "")

        env, skipped_keys = _sanitize_env(env)
        if skipped_keys:
            logger.warning(
                "[ccusage-invoker] env 净化：跳过 %d 个非字符串值: %s",
                len(skipped_keys),
                ", ".join(f"{k}({t})" for k, t in skipped_keys),
            )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.EXEC_TIMEOUT,
                message=f"{cli_name} 执行超时（>{timeout}s）",
                remediation="请稍后重试",
                details={"timeout_seconds": timeout},
            ),
        }
    except PermissionError as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.PERMISSION_DENIED,
                message=f"{cli_name} 执行权限不足",
                remediation="请检查可执行权限",
                details={"error": str(e)},
            ),
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_NOT_FOUND,
                message=f"找不到命令：{cmd[0]}",
                remediation=f"请确认 {cli_name} 已正确安装",
                details={"error": str(e)},
            ),
        }
    except TypeError as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_EXECUTION_ERROR,
                message=f"{cli_name} 环境变量构造失败: {e}",
                remediation="请联系管理员检查服务器环境变量配置",
                details={"error": str(e), "env_keys_sample": list(env.keys())[:10]},
            ),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_EXECUTION_ERROR,
                message=f"{cli_name} 执行异常: {e}",
                remediation="请检查安装是否完整",
                details={"error": str(e)},
            ),
        }

    if result.returncode != 0:
        err_msg = (result.stderr or "CLI 执行失败").strip()[:500]
        if "bun:" in err_msg or "ERR_UNSUPPORTED_ESM_URL_SCHEME" in err_msg:
            return {
                "ok": False,
                "error": CcusageError(
                    code=ErrorCode.CLI_EXECUTION_ERROR,
                    message=f"{cli_name} 需要 bun 运行时，当前环境不支持",
                    remediation="请安装 bun: https://bun.sh",
                    details={"stderr": err_msg[:200]},
                ),
            }
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_EXECUTION_ERROR,
                message=f"{cli_name} 退出码 {result.returncode}",
                remediation="请根据错误信息排查",
                details={"stderr": err_msg, "returncode": result.returncode},
            ),
        }

    output = result.stdout.strip()
    try:
        start = -1
        for i, ch in enumerate(output):
            if ch in ("{", "["):
                try:
                    json.loads(output[i:])
                    start = i
                    break
                except json.JSONDecodeError:
                    continue
        if start == -1:
            raise json.JSONDecodeError("未找到 JSON 起始", output, 0)
        data = json.loads(output[start:])
        return {"ok": True, "data": data}
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.INVALID_JSON_OUTPUT,
                message=f"{cli_name} 输出不是有效 JSON",
                remediation="请检查版本或运行 --version 验证",
                details={"error": str(e), "stdout_preview": output[:300]},
            ),
        }


def run_generic_cli(cli_name: str, args: list[str], timeout: int = 180) -> dict:
    """通用 npm CLI 工具执行器。

    支持 ccusage / opencode-usage / ccusage-opencode 等通过 npm 全局安装的 CLI。
    跨平台处理 .cmd/.ps1 与 node 直接调用。

    Returns:
        {"ok": True, "data": <parsed json>}  成功
        {"ok": False, "error": CcusageError}  失败
    """
    cache_key = f"generic:{cli_name}"

    if cache_key not in _cli_path_cache:
        which_result = shutil.which(cli_name)
        if which_result and os.path.exists(which_result):
            _cli_path_cache[cache_key] = which_result
        else:
            _cli_path_cache[cache_key] = None

    cli_path = _cli_path_cache[cache_key]
    if cli_path is None:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_NOT_FOUND,
                message=f"未找到 {cli_name} 命令",
                remediation=f"请运行 `npm i -g {cli_name}` 安装",
            ),
        }

    cmd = _build_cli_cmd(cli_path, args)
    return _execute_and_parse(cmd, cli_name, timeout)


def _build_cli_cmd(cli_path: str, args: list[str]) -> list[str]:
    """为 CLI 工具构造执行命令，Windows 下尝试 node 直接调用 JS 入口"""
    if os.name == "nt" and cli_path.lower().endswith((".cmd", ".ps1")):
        node_path = find_node()
        if not node_path:
            return [cli_path] + list(args)
        npm_dir = os.path.dirname(cli_path)
        pkg_name = os.path.basename(cli_path).replace(".cmd", "").replace(".ps1", "")
        js_path = os.path.join(npm_dir, "node_modules", pkg_name, "dist", "cli.js")
        if not os.path.exists(js_path):
            js_path = os.path.join(npm_dir, "node_modules", pkg_name, "dist", "index.js")
        if not os.path.exists(js_path):
            return [cli_path] + list(args)
        return [node_path, js_path] + list(args)
    return [cli_path] + list(args)


def run_ccusage(args: list[str], timeout: int = 180) -> dict:
    """统一执行 ccusage CLI 并返回结构化结果。

    Returns:
        {"ok": True, "data": <parsed json>}  成功
        {"ok": False, "error": CcusageError}  失败
    """
    ccusage_path = find_ccusage()
    if ccusage_path is None:
        return {"ok": False, "error": _make_cli_not_found_error(_ccusage_search_paths())}

    cmd = build_cmd(args)
    if not cmd:
        return {"ok": False, "error": _make_cli_not_found_error(_ccusage_search_paths())}

    return _execute_and_parse(cmd, "ccusage", timeout)
