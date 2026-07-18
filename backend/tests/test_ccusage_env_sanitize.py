"""_sanitize_env 单元测试"""
from app.utils.ccusage_invoker import _sanitize_env


class TestSanitizeEnv:
    """验证 _sanitize_env 对各类非字符串值的处理"""

    def test_all_strings_passed_through(self):
        """全字符串 env 原样返回，skipped_keys 为空"""
        env = {"PATH": "/usr/bin", "HOME": "/home/user", "LANG": "en_US.UTF-8"}
        result, skipped = _sanitize_env(env)
        assert result == env
        assert skipped == []

    def test_none_value_is_skipped(self):
        """None 值被跳过，不进入结果 dict"""
        env = {"PATH": "/usr/bin", "BAD": None}
        result, skipped = _sanitize_env(env)
        assert "BAD" not in result
        assert result["PATH"] == "/usr/bin"
        assert ("BAD", "None") in skipped

    def test_bytes_value_is_decoded(self):
        """bytes 值用 utf-8 解码"""
        env = {"PATH": b"/usr/bin", "HOME": "/home/user"}
        result, skipped = _sanitize_env(env)
        assert result["PATH"] == "/usr/bin"
        assert result["HOME"] == "/home/user"
        assert skipped == []

    def test_bytes_with_non_utf8_uses_replace(self):
        """含非 UTF-8 字节的 bytes 用 replace 模式解码"""
        env = {"BAD": b"\xff\xfe"}
        result, skipped = _sanitize_env(env)
        assert result["BAD"] == "��"
        assert skipped == []

    def test_int_value_is_converted(self):
        """int 值被 str() 转换"""
        env = {"PORT": 8080, "PATH": "/usr/bin"}
        result, skipped = _sanitize_env(env)
        assert result["PORT"] == "8080"
        assert result["PATH"] == "/usr/bin"
        assert skipped == []

    def test_float_value_is_converted(self):
        """float 值被 str() 转换"""
        env = {"RATE": 3.14}
        result, skipped = _sanitize_env(env)
        assert result["RATE"] == "3.14"
        assert skipped == []

    def test_bool_value_is_converted(self):
        """bool 值被 str() 转换"""
        env = {"DEBUG": True, "VERBOSE": False}
        result, skipped = _sanitize_env(env)
        assert result["DEBUG"] == "True"
        assert result["VERBOSE"] == "False"
        assert skipped == []

    def test_empty_env(self):
        """空 dict 返回空 dict"""
        result, skipped = _sanitize_env({})
        assert result == {}
        assert skipped == []

    def test_mixed_types(self):
        """混合多种类型，验证各自处理"""
        env = {
            "STR": "ok",
            "NONE": None,
            "BYTES": b"bytes_val",
            "INT": 42,
            "FLOAT": 2.5,
            "BOOL": True,
        }
        result, skipped = _sanitize_env(env)
        assert result["STR"] == "ok"
        assert result["BYTES"] == "bytes_val"
        assert result["INT"] == "42"
        assert result["FLOAT"] == "2.5"
        assert result["BOOL"] == "True"
        assert "NONE" not in result
        assert len(skipped) == 1
        assert skipped[0] == ("NONE", "None")
