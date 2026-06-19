"""
Author: Peanut
Created: 2026-06-19
Purpose: 统一的 ccusage CLI 调用器，提供跨平台路径发现和结构化错误。
"""
from __future__ import annotations

import glob
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
