import pytest
from app.utils.path_utils import is_sensitive_path, validate_any_path


def test_sensitive_path_detection():
    """测试敏感路径检测"""
    assert is_sensitive_path('/etc/shadow') is True
    assert is_sensitive_path('/etc/passwd') is True
    assert is_sensitive_path('/proc/123') is True
    assert is_sensitive_path('/sys/class') is True
    assert is_sensitive_path('/dev/null') is True
    assert is_sensitive_path('/home/user/docs') is False


def test_validate_any_path_valid():
    """测试有效路径验证"""
    is_valid, result = validate_any_path('/home/user/docs')
    assert is_valid is True
    assert '/home/user/docs' in result


def test_validate_any_path_traversal():
    """测试路径遍历防护"""
    is_valid, error = validate_any_path('../../etc/passwd')
    assert is_valid is False
    assert '遍历' in error


def test_validate_any_path_sensitive():
    """测试敏感路径拒绝"""
    is_valid, error = validate_any_path('/etc/shadow')
    assert is_valid is False
    assert '敏感' in error


def test_validate_any_path_empty():
    """测试空路径拒绝"""
    is_valid, error = validate_any_path('')
    assert is_valid is False
    assert '不能为空' in error


def test_validate_any_path_relative():
    """测试相对路径解析"""
    import os
    is_valid, result = validate_any_path('docs')
    assert is_valid is True
    # 相对路径应该被解析为绝对路径
    assert os.path.isabs(result)
