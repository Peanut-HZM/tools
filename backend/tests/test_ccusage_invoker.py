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
