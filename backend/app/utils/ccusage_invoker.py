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
