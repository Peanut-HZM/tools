"""CcusageInvoker 单元测试"""
from unittest.mock import patch

import pytest

from app.utils import ccusage_invoker
from app.utils.ccusage_invoker import CcusageError, ErrorCode, find_node


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
