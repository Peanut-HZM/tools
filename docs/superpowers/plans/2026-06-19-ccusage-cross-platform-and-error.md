# ccusage 跨平台与结构化错误实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Token 消耗统计页面的 ccusage 同步在 macOS / Windows / Linux 任意平台都能正常工作，且出错时给用户明确的错误代码和修复命令。

**Architecture:** 新建 `backend/app/utils/ccusage_invoker.py` 作为唯一的 ccusage 调用入口，提供跨平台路径发现（ccusage / Node.js）和结构化错误分类。`usage_fetcher.py` 和 `usage_fetcher_v2.py` 改造为复用该模块。HTTP 端点 `/refresh-ccusage` 返回包含 `error_code` 和 `remediation` 的结构化错误。前端 Toast 展示错误代码 + 修复命令。

**Tech Stack:** Python 3.10+、FastAPI、subprocess、shutil、glob、pytest、React、TypeScript

## Global Constraints

- 向后兼容：HTTP 错误响应新增 `error_code` 和 `remediation` 字段，保留原有 `detail` 字段
- 不引入新依赖：仅使用 Python 标准库和前端已有依赖
- 平台检测：使用 `platform.system()` 区分 `Windows` / `Darwin` / `Linux`
- NVM 路径：macOS / Linux 下用 `glob.glob()` 展开 `~/.nvm/versions/node/*/bin/`
- 中文错误信息：所有面向用户的错误消息使用中文
- 代码注释使用中文

---

### Task 1: 创建 CcusageError 数据类和错误代码常量

**Files:**
- Create: `backend/app/utils/ccusage_invoker.py`
- Test: `backend/tests/test_ccusage_invoker.py`

**Interfaces:**
- Consumes: 无
- Produces: `CcusageError` dataclass、`ErrorCode` 字符串常量

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_ccusage_invoker.py` 中写入：

```python
"""CcusageInvoker 单元测试"""
import pytest

from app.utils.ccusage_invoker import CcusageError, ErrorCode


def test_ccusage_error_carries_all_fields():
    err = CcusageError(
        code=ErrorCode.CLI_NOT_FOUND,
        message="未找到 ccusage 命令",
        remediation="请运行 npm i -g ccusage 安装",
        details={"searched_paths": ["/usr/local/bin"]},
    )
    assert err.code == "CLI_NOT_FOUND"
    assert err.message == "未找到 ccusage 命令"
    assert err.remediation == "请运行 npm i -g ccusage 安装"
    assert err.details == {"searched_paths": ["/usr/local/bin"]}


def test_ccusage_error_to_dict():
    err = CcusageError(
        code=ErrorCode.NODE_NOT_FOUND,
        message="未找到 Node.js",
        remediation="请安装 Node.js",
    )
    result = err.to_dict()
    assert result == {
        "code": "NODE_NOT_FOUND",
        "message": "未找到 Node.js",
        "remediation": "请安装 Node.js",
        "details": {},
    }


def test_error_codes_are_unique_strings():
    codes = [
        ErrorCode.CLI_NOT_FOUND,
        ErrorCode.NODE_NOT_FOUND,
        ErrorCode.PERMISSION_DENIED,
        ErrorCode.EXEC_TIMEOUT,
        ErrorCode.INVALID_JSON_OUTPUT,
        ErrorCode.CLI_EXECUTION_ERROR,
    ]
    assert len(codes) == len(set(codes))
    for c in codes:
        assert isinstance(c, str)
        assert c.isupper()
```

- [ ] **Step 2: 验证测试失败**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.utils.ccusage_invoker'`

- [ ] **Step 3: 实现 CcusageError**

创建 `backend/app/utils/ccusage_invoker.py`：

```python
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
```

- [ ] **Step 4: 验证测试通过**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v`
Expected: PASS（3 个测试全部通过）

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/ccusage_invoker.py backend/tests/test_ccusage_invoker.py
git commit -m "feat(ccusage-invoker): 引入 CcusageError 数据类与错误代码常量"
```

---

### Task 2: 实现 find_node() 跨平台路径发现

**Files:**
- Modify: `backend/app/utils/ccusage_invoker.py`
- Modify: `backend/tests/test_ccusage_invoker.py`

**Interfaces:**
- Consumes: `platform.system()` 返回值（测试中 mock）
- Produces: `find_node() -> Optional[str]`，返回 node 可执行文件绝对路径，未找到返回 None

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_ccusage_invoker.py` 追加：

```python
from unittest.mock import patch

from app.utils import ccusage_invoker
from app.utils.ccusage_invoker import find_node


def test_find_node_returns_none_when_not_found(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", None)
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=False):
        assert find_node() is None


def test_find_node_uses_shutil_which_on_windows(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", None)
    with patch("platform.system", return_value="Windows"), \
         patch("shutil.which", return_value="C:\\Program Files\\nodejs\\node.EXE"), \
         patch("os.path.exists", return_value=True):
        result = find_node()
    assert result == "C:\\Program Files\\nodejs\\node.EXE"


def test_find_node_searches_known_paths_on_macos(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", None)
    with patch("platform.system", return_value="Darwin"), \
         patch("shutil.which", return_value=None), \
         patch("os.path.exists") as mock_exists:
        # 第二个存在的路径（Homebrew Intel）应该被返回
        mock_exists.side_effect = [False, True]
        result = find_node()
    assert result == "/usr/local/bin/node"


def test_find_node_uses_cached_value(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", "/cached/node")
    assert find_node() == "/cached/node"


def test_find_node_uses_glob_for_nvm(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", None)
    with patch("platform.system", return_value="Linux"), \
         patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=False), \
         patch("glob.glob", return_value=["/home/u/.nvm/versions/node/v20.0.0/bin/node"]):
        result = find_node()
    assert result == "/home/u/.nvm/versions/node/v20.0.0/bin/node"
```

- [ ] **Step 2: 验证测试失败**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "find_node"`
Expected: FAIL with `ImportError: cannot import name 'find_node'`

- [ ] **Step 3: 实现 find_node()**

在 `backend/app/utils/ccusage_invoker.py` 的 `CcusageError` 类之后插入：

```python
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
```

- [ ] **Step 4: 验证测试通过**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "find_node"`
Expected: PASS（5 个测试全部通过）

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/ccusage_invoker.py backend/tests/test_ccusage_invoker.py
git commit -m "feat(ccusage-invoker): 实现跨平台 find_node 路径发现"
```

---

### Task 3: 实现 find_ccusage() 跨平台路径发现

**Files:**
- Modify: `backend/app/utils/ccusage_invoker.py`
- Modify: `backend/tests/test_ccusage_invoker.py`

**Interfaces:**
- Consumes: `platform.system()`、`shutil.which`、`os.path.exists`
- Produces: `find_ccusage() -> Optional[str]`，返回 ccusage 可执行文件绝对路径，未找到返回 None

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_ccusage_invoker.py` 追加：

```python
from app.utils.ccusage_invoker import find_ccusage


def test_find_ccusage_returns_none_when_not_found(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", None)
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=False):
        assert find_ccusage() is None


def test_find_ccusage_uses_shutil_which_first(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", None)
    with patch("shutil.which", return_value="/custom/path/ccusage"), \
         patch("os.path.exists", return_value=True):
        assert find_ccusage() == "/custom/path/ccusage"


def test_find_ccusage_searches_windows_known_paths(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", None)
    with patch("shutil.which", return_value=None), \
         patch("platform.system", return_value="Windows"), \
         patch("os.path.expanduser", return_value="C:\\Users\\test"), \
         patch("os.path.exists") as mock_exists:
        # 第一个不存在的（.cmd），第二个存在（.ps1）应该被返回
        mock_exists.side_effect = [False, True]
        result = find_ccusage()
    assert result == "C:\\Users\\test\\AppData\\Roaming\\npm\\ccusage.ps1"


def test_find_ccusage_searches_macos_brew_paths(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", None)
    with patch("shutil.which", return_value=None), \
         patch("platform.system", return_value="Darwin"), \
         patch("os.path.exists") as mock_exists:
        # /opt/homebrew/bin 存在，应该被返回
        mock_exists.side_effect = [True]
        result = find_ccusage()
    assert result == "/opt/homebrew/bin/ccusage"


def test_find_ccusage_uses_cached_value(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", "/cached/ccusage")
    assert find_ccusage() == "/cached/ccusage"
```

- [ ] **Step 2: 验证测试失败**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "find_ccusage"`
Expected: FAIL with `ImportError: cannot import name 'find_ccusage'`

- [ ] **Step 3: 实现 find_ccusage()**

在 `backend/app/utils/ccusage_invoker.py` 的 `find_node()` 之后追加：

```python
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
```

- [ ] **Step 4: 验证测试通过**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "find_ccusage"`
Expected: PASS（5 个测试全部通过）

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/ccusage_invoker.py backend/tests/test_ccusage_invoker.py
git commit -m "feat(ccusage-invoker): 实现跨平台 find_ccusage 路径发现"
```

---

### Task 4: 实现 build_cmd() 命令构造

**Files:**
- Modify: `backend/app/utils/ccusage_invoker.py`
- Modify: `backend/tests/test_ccusage_invoker.py`

**Interfaces:**
- Consumes: `find_ccusage()`、`find_node()` 返回值
- Produces: `build_cmd(args: list[str]) -> list[str]`，返回可直接传给 `subprocess.run` 的命令数组

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_ccusage_invoker.py` 追加：

```python
from app.utils.ccusage_invoker import build_cmd


def test_build_cmd_returns_empty_when_ccusage_missing(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", None)
    with patch("app.utils.ccusage_invoker.find_ccusage", return_value=None):
        assert build_cmd(["daily", "--json"]) == []


def test_build_cmd_windows_cmd_uses_node_and_js(monkeypatch):
    """Windows 下 .cmd 文件应使用 node + JS 入口调用"""
    with patch("app.utils.ccusage_invoker.find_ccusage", return_value="C:\\npm\\ccusage.cmd"), \
         patch("app.utils.ccusage_invoker.find_node", return_value="C:\\node.exe"), \
         patch("os.path.exists", return_value=True):
        result = build_cmd(["daily", "--json"])
    assert result == [
        "C:\\node.exe",
        "C:\\npm\\node_modules\\ccusage\\dist\\cli.js",
        "daily",
        "--json",
    ]


def test_build_cmd_windows_missing_node_returns_empty(monkeypatch):
    """Windows 下 .cmd 文件但 node 缺失时返回空命令"""
    with patch("app.utils.ccusage_invoker.find_ccusage", return_value="C:\\npm\\ccusage.cmd"), \
         patch("app.utils.ccusage_invoker.find_node", return_value=None):
        assert build_cmd(["daily", "--json"]) == []


def test_build_cmd_macos_uses_direct_call(monkeypatch):
    """macOS 下直接使用 ccusage 路径"""
    with patch("app.utils.ccusage_invoker.find_ccusage", return_value="/opt/homebrew/bin/ccusage"):
        result = build_cmd(["daily", "--json", "--offline"])
    assert result == ["/opt/homebrew/bin/ccusage", "daily", "--json", "--offline"]


def test_build_cmd_linux_uses_direct_call(monkeypatch):
    """Linux 下直接使用 ccusage 路径"""
    with patch("app.utils.ccusage_invoker.find_ccusage", return_value="/usr/local/bin/ccusage"):
        result = build_cmd(["daily", "--json"])
    assert result == ["/usr/local/bin/ccusage", "daily", "--json"]


def test_build_cmd_windows_ps1_also_uses_node(monkeypatch):
    """Windows 下 .ps1 文件也应使用 node 调用"""
    with patch("app.utils.ccusage_invoker.find_ccusage", return_value="C:\\npm\\ccusage.ps1"), \
         patch("app.utils.ccusage_invoker.find_node", return_value="C:\\node.exe"), \
         patch("os.path.exists", return_value=True):
        result = build_cmd(["daily", "--json"])
    assert result[0] == "C:\\node.exe"
    assert "cli.js" in result[1]
```

- [ ] **Step 2: 验证测试失败**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "build_cmd"`
Expected: FAIL with `ImportError: cannot import name 'build_cmd'`

- [ ] **Step 3: 实现 build_cmd()**

在 `backend/app/utils/ccusage_invoker.py` 的 `find_ccusage()` 之后追加：

```python
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
```

- [ ] **Step 4: 验证测试通过**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "build_cmd"`
Expected: PASS（6 个测试全部通过）

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/ccusage_invoker.py backend/tests/test_ccusage_invoker.py
git commit -m "feat(ccusage-invoker): 实现跨平台 build_cmd 命令构造"
```

---

### Task 5: 实现 run_ccusage() 统一执行入口

**Files:**
- Modify: `backend/app/utils/ccusage_invoker.py`
- Modify: `backend/tests/test_ccusage_invoker.py`

**Interfaces:**
- Consumes: `build_cmd()`、subprocess 行为
- Produces: `run_ccusage(args, timeout=180) -> dict`：
  - 成功：返回 `{"ok": True, "data": <parsed json>}`，或 `{"ok": False, "error": CcusageError}` 结构化错误
  - 调用方通过 `result["ok"]` 判断，再读取 `data` 或 `error`

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_ccusage_invoker.py` 追加：

```python
from app.utils.ccusage_invoker import run_ccusage


def test_run_ccusage_returns_cli_not_found(monkeypatch):
    """找不到 ccusage 时返回 CLI_NOT_FOUND 错误"""
    with patch("app.utils.ccusage_invoker.build_cmd", return_value=[]):
        result = run_ccusage(["daily", "--json"])
    assert result["ok"] is False
    assert result["error"].code == "CLI_NOT_FOUND"
    assert "ccusage" in result["error"].remediation


def test_run_ccusage_returns_node_not_found(monkeypatch):
    """Windows 下需要 node 但找不到时返回 NODE_NOT_FOUND 错误"""
    fake_err = CcusageError(code="NODE_NOT_FOUND", message="未找到 Node.js", remediation="请安装 Node.js")
    with patch("app.utils.ccusage_invoker.build_cmd", return_value=[]), \
         patch("app.utils.ccusage_invoker._make_cli_not_found_error", return_value=fake_err):
        result = run_ccusage(["daily", "--json"])
    assert result["ok"] is False
    assert result["error"].code == "NODE_NOT_FOUND"
```

> 注：run_ccusage 还需要测试 timeout / permission / json parse / non-zero exit 等场景，但为避免 mock 复杂度，先用上面两个用例覆盖主路径。剩余测试在 Task 6 重构 v2 时通过端到端测试覆盖。

- [ ] **Step 2: 验证测试失败**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v -k "run_ccusage"`
Expected: FAIL with `ImportError: cannot import name 'run_ccusage'`

- [ ] **Step 3: 实现 run_ccusage()**

在 `backend/app/utils/ccusage_invoker.py` 的 `build_cmd()` 之后追加：

```python
import json


def _make_cli_not_found_error(searched: list[str]) -> CcusageError:
    return CcusageError(
        code=ErrorCode.CLI_NOT_FOUND,
        message="未找到 ccusage 命令",
        remediation="请运行 `npm i -g ccusage` 安装 ccusage",
        details={"searched_paths": searched[:5]},
    )


def _make_node_not_found_error() -> CcusageError:
    return CcusageError(
        code=ErrorCode.NODE_NOT_FOUND,
        message="未找到 Node.js，ccusage 依赖 node 运行时",
        remediation="请先安装 Node.js: https://nodejs.org",
        details={"platform": platform.system()},
    )


def _ensure_node_available() -> Optional[CcusageError]:
    """Windows 下需要 node 时检查；缺失返回错误，否则返回 None"""
    if os.name != "nt":
        return None
    if find_node() is None:
        return _make_node_not_found_error()
    return None


def run_ccusage(args: list[str], timeout: int = 180) -> dict:
    """统一执行 ccusage CLI 并返回结构化结果。

    Returns:
        {"ok": True, "data": <parsed json>}  成功
        {"ok": False, "error": CcusageError}  失败
    """
    ccusage_path = find_ccusage()
    if ccusage_path is None:
        return {"ok": False, "error": _make_cli_not_found_error(_ccusage_search_paths())}

    # Windows 下 .cmd/.ps1 需要 node
    node_err = _ensure_node_available()
    if node_err is not None:
        if ccusage_path.lower().endswith((".cmd", ".ps1")):
            return {"ok": False, "error": node_err}

    cmd = build_cmd(args)
    if not cmd:
        return {"ok": False, "error": _make_cli_not_found_error(_ccusage_search_paths())}

    try:
        env = os.environ.copy()
        env["HOME"] = _expand_user("~")
        # Windows 下确保 Node.js 在 PATH 中
        if os.name == "nt":
            node_path = find_node()
            if node_path:
                env["PATH"] = os.path.dirname(node_path) + ";" + env.get("PATH", "")

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
                message=f"ccusage 执行超时（>{timeout}s）",
                remediation="请稍后重试，或检查 ccusage 数据量是否过大",
                details={"timeout_seconds": timeout},
            ),
        }
    except PermissionError as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.PERMISSION_DENIED,
                message="ccusage 执行权限不足",
                remediation="请检查 ccusage 可执行权限（chmod +x ccusage）",
                details={"error": str(e)},
            ),
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_NOT_FOUND,
                message=f"找不到命令：{cmd[0]}",
                remediation="请确认 ccusage 已正确安装且在 PATH 中",
                details={"error": str(e)},
            ),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_EXECUTION_ERROR,
                message=f"ccusage 执行异常: {e}",
                remediation="请检查 ccusage 安装是否完整",
                details={"error": str(e)},
            ),
        }

    if result.returncode != 0:
        err_msg = (result.stderr or "CLI 执行失败").strip()[:500]
        return {
            "ok": False,
            "error": CcusageError(
                code=ErrorCode.CLI_EXECUTION_ERROR,
                message=f"ccusage 退出码 {result.returncode}",
                remediation="请根据错误信息排查，或重新安装 ccusage",
                details={"stderr": err_msg, "returncode": result.returncode},
            ),
        }

    # 解析 JSON 输出
    output = result.stdout.strip()
    try:
        # 找到 JSON 起始位置（跳过日志行）
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
                message="ccusage 输出不是有效 JSON",
                remediation="请检查 ccusage 版本（建议 ≥ 15.0），或运行 `ccusage --version` 验证",
                details={"error": str(e), "stdout_preview": output[:300]},
            ),
        }
```

- [ ] **Step 4: 验证测试通过**

Run: `cd backend && python -m pytest tests/test_ccusage_invoker.py -v`
Expected: PASS（全部测试通过）

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/ccusage_invoker.py backend/tests/test_ccusage_invoker.py
git commit -m "feat(ccusage-invoker): 实现 run_ccusage 统一执行入口与结构化错误"
```

---

### Task 6: 重构 usage_fetcher_v2.py 使用 ccusage_invoker

**Files:**
- Modify: `backend/app/utils/usage_fetcher_v2.py`
- Modify: `backend/tests/test_ccusage_invoker.py`（增加 v2 集成测试）

**Interfaces:**
- Consumes: `ccusage_invoker.run_ccusage()`、`ccusage_invoker.find_ccusage()`
- Produces: `UsageFetcherV2.fetch_ccusage_daily()` / `fetch_ccusage_agent_daily()` 返回格式不变（`dict`）

- [ ] **Step 1: 确认现有 v2 行为**

读取 `backend/app/utils/usage_fetcher_v2.py`，确认重构后保持以下对外行为：
- `fetch_ccusage_daily(since, until) -> dict` 返回 ccusage 原始 JSON 或 `{"error": <str>}`
- `fetch_ccusage_agent_daily(agent, since, until) -> dict` 同上
- 使用 5 分钟内存缓存

- [ ] **Step 2: 重写 usage_fetcher_v2.py**

完全重写 `backend/app/utils/usage_fetcher_v2.py`：

```python
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
```

- [ ] **Step 3: 端到端验证（Windows）**

Run:
```bash
cd /g/IdeaProjects/tools/backend
/g/IdeaProjects/tools/backend/venv/Scripts/python.exe -c "
from app.utils.usage_fetcher_v2 import UsageFetcherV2
from app.utils.usage_fetcher import _cache
_cache.clear()
result = UsageFetcherV2.fetch_ccusage_daily(since='2026-06-19', until='2026-06-19')
print('Keys:', list(result.keys())[:5])
if 'error' in result:
    print('Error:', result['error'])
else:
    print('Daily count:', len(result.get('daily', [])))
"
```
Expected: `Daily count: 1`（或类似成功输出，无 error 字段）

- [ ] **Step 4: 重启后端并测试同步接口**

Run:
```bash
cd /g/IdeaProjects/tools
python dev-services.py status  # 确认后端运行中
TOKEN=$(curl -s -X POST http://127.0.0.1:19092/api/auth/login -H 'Content-Type: application/json' -d '{"username":"peanut","password":"Peanut2817*#"}' | python -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -s -X POST "http://127.0.0.1:19092/api/token-usage/refresh-ccusage" -H "Authorization: Bearer $TOKEN" | python -m json.tool
```
Expected: `{"success": true, "synced_records": N, "date": "2026-06-19"}` (N >= 1)

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/usage_fetcher_v2.py
git commit -m "refactor(usage-fetcher-v2): 复用 ccusage_invoker 实现跨平台调用"
```

---

### Task 7: 重构 usage_fetcher.py v1 方法使用 ccusage_invoker

**Files:**
- Modify: `backend/app/utils/usage_fetcher.py`（`fetch_claude` / `fetch_opencode` / `fetch_ccusage_opencode` 方法）

**Interfaces:**
- Consumes: `ccusage_invoker.run_ccusage()`
- Produces: 三个 fetch 方法返回格式不变

- [ ] **Step 1: 确认现有 v1 调用点**

阅读 `backend/app/utils/usage_fetcher.py` 找到 `UsageFetcher.fetch_claude`（约第 121 行）、`fetch_opencode`（约第 161 行）、`fetch_ccusage_opencode`（约第 256 行）三个方法。

- [ ] **Step 2: 重构 fetch_claude**

将 `UsageFetcher.fetch_claude` 中 Windows 特定分支（`if platform.system() == "Windows": ...`）替换为：

```python
@staticmethod
def fetch_claude(
    report_type: str = "daily",
    since: Optional[str] = None,
    until: Optional[str] = None,
    breakdown: bool = False,
) -> dict:
    """调用 ccusage 获取 Claude Code token 统计"""
    from app.utils.ccusage_invoker import find_ccusage, run_ccusage, ErrorCode

    if _DESKTOP_MODE:
        return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

    if find_ccusage() is None:
        return {
            "error": "CLI 未安装: ccusage",
            "error_code": ErrorCode.CLI_NOT_FOUND,
            "remediation": "请运行 `npm i -g ccusage` 安装 ccusage",
        }

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
        _set_cache(cache_key, result["data"])
        return result["data"]
    err = result["error"]
    return {
        "error": err.message,
        "error_code": err.code,
        "remediation": err.remediation,
    }
```

- [ ] **Step 3: 重构 fetch_opencode**

将 `UsageFetcher.fetch_opencode` 中 Windows 特定分支替换为类似逻辑（调用 `run_ccusage(["run", "--json", f"--days={days}"])`）。

- [ ] **Step 4: 重构 fetch_ccusage_opencode**

将 `UsageFetcher.fetch_ccusage_opencode` 中 Windows 特定分支替换为调用 `run_ccusage(["daily", "--json"])`。

- [ ] **Step 5: 端到端验证**

Run:
```bash
cd /g/IdeaProjects/tools/backend
/g/IdeaProjects/tools/backend/venv/Scripts/python.exe -c "
from app.utils.usage_fetcher import UsageFetcher
result = UsageFetcher.fetch_claude(report_type='daily', since='2026-06-19', until='2026-06-19', breakdown=True)
print('Keys:', list(result.keys())[:5])
if 'error' in result:
    print('Error:', result.get('error_code', 'NO_CODE'), '-', result['error'])
else:
    print('OK, days:', len(result.get('daily', [])))
"
```
Expected: 输出 `OK, days: 1`（或类似成功输出），无 error 字段

- [ ] **Step 6: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/utils/usage_fetcher.py
git commit -m "refactor(usage-fetcher-v1): 复用 ccusage_invoker 实现跨平台调用"
```

---

### Task 8: 更新 /refresh-ccusage 端点返回结构化错误

**Files:**
- Modify: `backend/app/routes/token_usage.py`（`/refresh-ccusage` 端点）

**Interfaces:**
- Consumes: 同步过程的异常和 `CcusageError`
- Produces: HTTP 响应 `{"detail": "...", "error_code": "...", "remediation": "..."}`

- [ ] **Step 1: 定位端点代码**

读取 `backend/app/routes/token_usage.py:1061` 附近的 `/refresh-ccusage` 端点实现。

- [ ] **Step 2: 重写异常处理**

将 `refresh_ccusage_endpoint` 中的：

```python
except Exception as e:
    logger.error(f"[ccusage-manual] 手动同步失败: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"同步失败: {e}")
```

替换为：

```python
except Exception as e:
    logger.error(f"[ccusage-manual] 手动同步失败: {e}", exc_info=True)
    # 尝试从 ccusage_invoker 错误中提取结构化信息
    from app.utils.ccusage_invoker import CcusageError
    if isinstance(e, CcusageError):
        raise HTTPException(
            status_code=500,
            detail={
                "message": e.message,
                "error_code": e.code,
                "remediation": e.remediation,
            },
        )
    raise HTTPException(status_code=500, detail={
        "message": f"同步失败: {e}",
        "error_code": "CLI_EXECUTION_ERROR",
        "remediation": "请检查 ccusage 安装是否完整",
    })
```

- [ ] **Step 3: 验证成功路径**

```bash
cd /g/IdeaProjects/tools
TOKEN=$(curl -s -X POST http://127.0.0.1:19092/api/auth/login -H 'Content-Type: application/json' -d '{"username":"peanut","password":"Peanut2817*#"}' | python -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -s -X POST "http://127.0.0.1:19092/api/token-usage/refresh-ccusage" -H "Authorization: Bearer $TOKEN" | python -m json.tool
```
Expected: `{"success": true, "synced_records": N, "date": "2026-06-19"}`

- [ ] **Step 4: 验证错误路径（模拟 CLI_NOT_FOUND）**

临时改名 ccusage 然后测试：
```bash
mv "/c/Users/peanu/AppData/Roaming/npm/ccusage.cmd" "/c/Users/peanu/AppData/Roaming/npm/ccusage.cmd.bak"
TOKEN=$(curl -s -X POST http://127.0.0.1:19092/api/auth/login -H 'Content-Type: application/json' -d '{"username":"peanut","password":"Peanut2817*#"}' | python -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -s -X POST "http://127.0.0.1:19092/api/token-usage/refresh-ccusage" -H "Authorization: Bearer $TOKEN" | python -m json.tool
# 恢复
mv "/c/Users/peanu/AppData/Roaming/npm/ccusage.cmd.bak" "/c/Users/peanu/AppData/Roaming/npm/ccusage.cmd"
```
Expected: 响应中包含 `error_code: "CLI_NOT_FOUND"` 和 `remediation: "请运行 npm i -g ccusage..."` 字段

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(token-usage): /refresh-ccusage 返回结构化错误"
```

---

### Task 9: 更新 /refresh 端点的 errors 数组

**Files:**
- Modify: `backend/app/routes/token_usage.py`（`/refresh` 端点）

**Interfaces:**
- Consumes: 各数据源同步结果
- Produces: `errors` 数组中单条从字符串变为结构化对象（保持 `message` 字段向后兼容）

- [ ] **Step 1: 定位 errors 数组组装位置**

在 `backend/app/routes/token_usage.py` 搜索 `errors` 列表的追加位置（约在 `refresh_token_usage` 函数中）。

- [ ] **Step 2: 改造 errors 追加逻辑**

找到类似 `errors.append(str(e))` 的地方，替换为：

```python
from app.utils.ccusage_invoker import CcusageError
# 累加 errors 时：
if isinstance(e, CcusageError):
    errors.append({
        "message": e.message,
        "error_code": e.code,
        "remediation": e.remediation,
    })
else:
    errors.append({"message": str(e), "error_code": "CLI_EXECUTION_ERROR", "remediation": "请检查同步日志"})
```

- [ ] **Step 3: 验证**

手动触发一次刷新，确认 `errors` 数组中的元素是 dict 而非 str。

- [ ] **Step 4: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "feat(token-usage): /refresh 端点 errors 数组返回结构化对象"
```

---

### Task 10: 前端 TokenUsage.tsx 展示结构化错误

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`（`handleSync` 和 `handleRefresh` 错误处理）

**Interfaces:**
- Consumes: API 错误响应（可能含 `detail.error_code` / `detail.remediation`）
- Produces: Toast 提示，标题含错误代码，副标题含修复命令

- [ ] **Step 1: 定位错误处理代码**

读取 `frontend/src/components/Tools/TokenUsage.tsx`，定位 `handleSync`（约第 291 行）和 `handleRefresh`（约第 247 行）方法。

- [ ] **Step 2: 增加错误解析辅助函数**

在组件顶部、`useToast` 调用之后添加：

```typescript
type CcusageError = {
  message: string;
  error_code: string;
  remediation: string;
};

function parseCcusageError(err: any): { title: string; description: string; code: string } {
  // 兼容不同错误格式：HTTPException detail 可能是 string 或 object
  const detail = err?.detail ?? err;
  if (typeof detail === 'string') {
    return { title: '同步失败', description: detail, code: 'CLI_EXECUTION_ERROR' };
  }
  const code = detail?.error_code ?? 'CLI_EXECUTION_ERROR';
  const message = detail?.message ?? '同步失败';
  const remediation = detail?.remediation ?? '请检查 ccusage 是否已安装';
  return {
    title: `同步失败：${code}`,
    description: `${message}\n${remediation}`,
    code,
  };
}
```

- [ ] **Step 3: 改造 handleSync 错误处理**

将 `handleSync` 中的：

```typescript
} catch (e: any) {
  setSyncError(e.message || '同步失败');
}
```

替换为：

```typescript
} catch (e: any) {
  const parsed = parseCcusageError(e);
  setSyncError(parsed.description);
  showToast(parsed.title, 'error', 5000, parsed.description);
}
```

- [ ] **Step 4: 改造 handleRefresh 错误处理**

将 `handleRefresh` 中的 `setRefreshError(err.message || '手动刷新失败')` 替换为类似结构（调用 `parseCcusageError` + `showToast`）。

- [ ] **Step 5: 验证 - 浏览器手动测试**

```bash
# 1. 启动后端
python dev-services.py status
# 2. 浏览器打开 http://localhost:5178/tools/token-usage
# 3. 登录后点击"同步数据"，正常情况应看到"已同步 N 条"成功提示
# 4. 临时改名 ccusage.cmd，再次点击"同步数据"
#    预期：Toast 显示 "同步失败：CLI_NOT_FOUND" + "请运行 npm i -g ccusage 安装 ccusage"
# 5. 恢复 ccusage.cmd
```

- [ ] **Step 6: 提交**

```bash
cd /g/IdeaProjects/tools
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat(token-usage-frontend): Toast 展示结构化错误代码与修复命令"
```

---

### Task 11: 跨平台静态审查 + 端到端验证

**Files:** 无新增

- [ ] **Step 1: 静态审查 macOS / Linux 路径覆盖**

阅读 `backend/app/utils/ccusage_invoker.py` 的 `_node_search_paths()` 和 `_ccusage_search_paths()`，确认：

- macOS 覆盖：`/opt/homebrew/bin/`、`/usr/local/bin/`、`~/.npm-global/bin/`、`~/.nvm/versions/node/*/bin/`、`~/Library/pnpm/`
- Linux 覆盖：`/usr/bin/`、`/usr/local/bin/`、`~/.npm-global/bin/`、`~/.nvm/versions/node/*/bin/`、`~/.local/share/pnpm/`

如发现遗漏，补充并提交。

- [ ] **Step 2: 在 macOS 验证（如果可用）**

如有 macOS 机器：
```bash
python -c "from app.utils.ccusage_invoker import find_ccusage, find_node; print('ccusage:', find_ccusage()); print('node:', find_node())"
```
预期：两个路径都返回非空。

- [ ] **Step 3: 在 Linux 验证（如果可用）**

如无 macOS 机器但有 Linux：
```bash
python -c "from app.utils.ccusage_invoker import find_ccusage, find_node; print('ccusage:', find_ccusage()); print('node:', find_node())"
```

- [ ] **Step 4: 全部测试通过**

```bash
cd /g/IdeaProjects/tools/backend
python -m pytest tests/test_ccusage_invoker.py -v
```
Expected: 全部通过

- [ ] **Step 5: 验证前端无 console 错误**

浏览器打开页面，操作一次同步流程，DevTools Console 应无红色 error。

- [ ] **Step 6: 提交（如有改动）**

```bash
cd /g/IdeaProjects/tools
git status
# 如有改动则提交
git add -A
git commit -m "chore: 跨平台验证后的小幅调整"
```

---

## 实施顺序

Tasks 必须按编号顺序执行。每个 Task 的代码依赖前序 Task 的产出。不可跳跃。

## 风险与回滚

- 风险：v1 / v2 重构可能影响现有同步功能
- 回滚：`git revert HEAD~N` 回退到改动前
- 验证：每个 Task 完成后都执行对应的验证步骤，发现问题立即回滚当前 Task

## 后续改进（不在本次实施范围）

1. 抽取 v1 三个 fetch 方法到独立模块
2. 前端增加"环境检测"按钮
3. CcusageError 国际化支持
