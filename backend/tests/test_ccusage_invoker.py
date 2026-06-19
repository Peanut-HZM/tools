"""CcusageInvoker 单元测试"""
from unittest.mock import patch

import pytest

from app.utils import ccusage_invoker
from app.utils.ccusage_invoker import CcusageError, ErrorCode, build_cmd, find_ccusage, find_node, run_ccusage


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
        # 第二个存在的路径（/usr/bin/node）应该被返回
        mock_exists.side_effect = [False, True]
        result = find_node()
    assert result == "/usr/bin/node"


def test_find_node_uses_cached_value(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", "/cached/node")
    assert find_node() == "/cached/node"


def test_find_node_uses_glob_for_nvm(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_node_path", None)

    def exists_side_effect(p):
        if ".nvm" in p:
            return True
        return False

    with patch("platform.system", return_value="Linux"), \
         patch("shutil.which", return_value=None), \
         patch("os.path.exists", side_effect=exists_side_effect), \
         patch("glob.glob", return_value=["/home/u/.nvm/versions/node/v20.0.0/bin/node"]):
        result = find_node()
    assert result == "/home/u/.nvm/versions/node/v20.0.0/bin/node"


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
        # 第一个不存在（.cmd），第二个存在（.ps1）
        mock_exists.side_effect = [False, True]
        result = find_ccusage()
    assert result == "C:\\Users\\test\\AppData\\Roaming\\npm\\ccusage.ps1"


def test_find_ccusage_searches_macos_brew_paths(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", None)
    with patch("shutil.which", return_value=None), \
         patch("platform.system", return_value="Darwin"), \
         patch("os.path.exists") as mock_exists:
        # /opt/homebrew/bin/ccusage 是 macOS 下第一个搜索路径
        mock_exists.side_effect = [True]
        result = find_ccusage()
    assert result == "/opt/homebrew/bin/ccusage"


def test_find_ccusage_uses_cached_value(monkeypatch):
    monkeypatch.setattr(ccusage_invoker, "_ccusage_path", "/cached/ccusage")
    assert find_ccusage() == "/cached/ccusage"


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
